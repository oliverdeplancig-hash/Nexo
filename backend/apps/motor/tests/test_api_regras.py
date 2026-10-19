"""API de regras do motor: cadastro, publicação versionada, simulação e arquivamento."""

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.motor.models import Regra, StatusRegra

pytestmark = pytest.mark.django_db
BASE = "/api/v1/motor/regras/"


@pytest.fixture
def gestor(usuarios):
    return usuarios["gestor"]


def _nova(cliente_gestor, **extra):
    dados = {
        "codigo": "DI-001",
        "titulo": "Diárias",
        "frases_exemplo": ["como solicitar diárias", "pedir diária de viagem"],
        "resposta": "Solicite as diárias com cinco dias de antecedência.",
        "etapas": [{"titulo": "Preencher o formulário"}],
        **extra,
    }
    return cliente_gestor.post(BASE, dados, format="json")


def test_cria_publica_versiona_e_simula(cliente, gestor):
    c = cliente(gestor)
    r = _nova(c)
    assert r.status_code == 201, r.json()
    regra_id = r.json()["id"]
    assert r.json()["status"] == StatusRegra.RASCUNHO

    # rascunho só entra na simulação quando pedido
    sem = c.post(f"{BASE}simular/", {"pergunta": "como solicitar diárias"}, format="json").json()
    assert sem["decisao"] != "responder"
    com = c.post(f"{BASE}simular/", {"pergunta": "como solicitar diárias", "incluir_rascunho": regra_id}, format="json")
    assert com.json()["decisao"] == "responder" and com.json()["regra"]["codigo"] == "DI-001"

    publicada = c.post(f"{BASE}{regra_id}/publicar/").json()
    assert publicada["status"] == StatusRegra.PUBLICADA and publicada["versao"] == 1
    assert (
        c.post(f"{BASE}simular/", {"pergunta": "pedir diária de viagem"}, format="json").json()["decisao"]
        == "responder"
    )

    # editar volta para rascunho; publicar de novo cria a versão 2
    c.patch(f"{BASE}{regra_id}/", {"resposta": "Prazo de cinco dias úteis."}, format="json")
    assert Regra.objects.get(pk=regra_id).status == StatusRegra.RASCUNHO
    c.post(f"{BASE}{regra_id}/publicar/")
    assert [v["versao"] for v in c.get(f"{BASE}{regra_id}/versoes/").json()] == [2, 1]

    assert c.delete(f"{BASE}{regra_id}/").status_code == 204
    assert Regra.objects.get(pk=regra_id).status == StatusRegra.ARQUIVADA
    acoes = set(EventoAuditoria.objects.filter(tipo="ADMIN_REGRA").values_list("detalhes__acao", flat=True))
    assert {"criar", "publicar", "alterar", "arquivar"} <= acoes


def test_validacoes_e_permissao(cliente, gestor, usuarios):
    c = cliente(gestor)
    assert _nova(c, frases_exemplo=["  "]).status_code == 400
    assert _nova(c, codigo="DI-002", padroes_regex=["(abc"]).status_code == 400
    assert _nova(c, codigo="DI-003", padroes_regex=["a" * 301]).status_code == 400
    assert _nova(c, codigo="DI-004", etapas=[{"descricao": "sem título"}]).status_code == 400
    assert cliente(usuarios["gp"]).get(BASE).status_code == 403
    _nova(c)
    assert len(c.get(f"{BASE}?q=diár").json()["results"]) == 1
