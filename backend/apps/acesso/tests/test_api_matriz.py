"""Matriz de permissões por documento pela API (tela 08)."""

import pytest

from apps.acesso.models import Acao, Classificacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def restrito(criar_documento):
    return criar_documento("Plano reservado", "Conteúdo reservado.", setor="TI", classificacao=Classificacao.RESTRITO)


def test_concede_e_revoga_com_auditoria(cliente, usuarios, perfis, restrito):
    usuarios["admin"].perfis.add(perfis["adminperm"])
    admin = cliente(usuarios["admin"])
    leitor = cliente(usuarios["gp"])
    assert leitor.get(f"/api/v1/acesso/documentos/{restrito.id}/minhas/").status_code == 404

    r = admin.post(
        f"/api/v1/acesso/documentos/{restrito.id}/matriz/",
        {"usuario": usuarios["gp"].id, "acoes": [Acao.VISUALIZAR], "motivo": "necessidade de conhecimento"},
        format="json",
    )
    assert r.status_code == 201, r.json()
    minhas = leitor.get(f"/api/v1/acesso/documentos/{restrito.id}/minhas/").json()
    assert Acao.VISUALIZAR in minhas["acoes"] and minhas["motivos"]
    matriz = admin.get(f"/api/v1/acesso/documentos/{restrito.id}/matriz/").json()
    assert len(matriz["autorizacoes"]) == 1

    assert admin.delete(f"/api/v1/acesso/autorizacoes/{r.json()['id']}/").status_code == 204
    assert leitor.get(f"/api/v1/acesso/documentos/{restrito.id}/minhas/").status_code == 404


def test_quem_nao_administra_nao_ve_a_matriz(cliente, usuarios, criar_documento):
    geral = criar_documento("Guia geral", "Conteúdo geral.")
    r = cliente(usuarios["gp"]).get(f"/api/v1/acesso/documentos/{geral.id}/matriz/")
    assert r.status_code == 403  # consulta, mas não administra
    acoes = cliente(usuarios["gp"]).get("/api/v1/acesso/acoes/").json()
    assert {"valor": "consultar", "rotulo": Acao.CONSULTAR.label} in acoes


def test_conceder_administracao_exige_funcao_critica(cliente, usuarios, perfis, restrito):
    from apps.acesso.models import AutorizacaoDocumento

    AutorizacaoDocumento.objects.create(documento=restrito, usuario=usuarios["ti"], acoes=[Acao.ADMINISTRAR])
    r = cliente(usuarios["ti"]).post(
        f"/api/v1/acesso/documentos/{restrito.id}/matriz/",
        {"usuario": usuarios["gp"].id, "acoes": [Acao.ADMINISTRAR]},
        format="json",
    )
    assert r.status_code == 403
