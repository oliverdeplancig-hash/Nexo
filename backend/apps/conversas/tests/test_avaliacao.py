"""Avaliação da qualidade das respostas e melhorias que ela orientou (ADR-025)."""

import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.conversas import avaliacao
from apps.conversas.models import Conversa

pytestmark = pytest.mark.django_db


@pytest.fixture
def acervo(criar_documento):
    criar_documento(
        "Manual de diárias",
        "As diárias devem ser solicitadas com cinco dias de antecedência pelo sistema de viagens.",
    )
    criar_documento("Guia de férias", "A solicitação de férias deve ser feita com trinta dias de antecedência.")


def _conjunto(tmp_path, casos, usuario="gp"):
    arquivo = tmp_path / "conjunto.json"
    arquivo.write_text(json.dumps({"nome": "Teste", "usuario": usuario, "casos": casos}), encoding="utf-8")
    return arquivo


def test_mede_fonte_conteudo_e_recusa(acervo, usuarios):
    certo = avaliacao.avaliar_caso(
        usuarios["gp"],
        avaliacao.Caso(id="d", pergunta="antecedência das diárias", fontes=["diárias"], contem=["cinco dias"]),
    )
    assert certo.fonte_ok and certo.posicao_fonte == 1 and certo.evidencia_ok and certo.aprovado
    errado = avaliacao.avaliar_caso(
        usuarios["gp"], avaliacao.Caso(id="e", pergunta="antecedência das diárias", fontes=["inexistente"])
    )
    assert errado.fonte_ok is False and not errado.aprovado
    fora = avaliacao.avaliar_caso(
        usuarios["gp"], avaliacao.Caso(id="f", pergunta="cardápio do refeitório", sem_resposta=True)
    )
    assert fora.recusa_ok and fora.origem == "sem_fontes"
    assert not Conversa.objects.filter(usuario=usuarios["gp"]).exists()  # não deixa conversas no histórico


def test_palavra_generica_nao_basta_como_evidencia(acervo, usuarios):
    """Antes da ADR-025, "deve" em comum bastava para responder com trechos sem relação."""
    r = avaliacao.avaliar_caso(
        usuarios["gp"],
        avaliacao.Caso(id="g", pergunta="Quantos caracteres deve ter a senha de rede?", sem_resposta=True),
    )
    assert r.recusa_ok, r.resposta


def test_comando_gera_relatorio_e_respeita_minimo(acervo, usuarios, tmp_path, capsys):
    arquivo = _conjunto(
        tmp_path,
        [
            {"id": "ok", "pergunta": "antecedência das diárias", "fontes": ["diárias"], "contem": ["cinco dias"]},
            {"id": "ruim", "pergunta": "antecedência das diárias", "contem": ["dez dias"]},
        ],
    )
    call_command("avaliar_respostas", str(arquivo), saida=str(tmp_path / "saida"))
    relatorio = next((tmp_path / "saida").glob("*.md")).read_text(encoding="utf-8")
    assert "Casos aprovados | 50% (1/2)" in relatorio and "faltou: dez dias" in relatorio
    dados = json.loads(next((tmp_path / "saida").glob("*.json")).read_text(encoding="utf-8"))
    assert dados["resumo"]["aprovados"]["acertos"] == 1
    with pytest.raises(CommandError, match="abaixo do mínimo"):
        call_command("avaliar_respostas", str(arquivo), minimo=0.9)


def test_conjunto_invalido(tmp_path, usuarios):
    with pytest.raises(CommandError, match="usuário ativo"):
        call_command("avaliar_respostas", str(_conjunto(tmp_path, [], usuario="ninguem")))
    repetido = _conjunto(tmp_path, [{"id": "a", "pergunta": "x"}, {"id": "a", "pergunta": "y"}])
    with pytest.raises(CommandError, match="mesmo id"):
        call_command("avaliar_respostas", str(repetido))


def test_conjunto_de_exemplo_e_valido():
    from django.conf import settings

    dados, casos = avaliacao.carregar(settings.BASE_DIR / "avaliacao" / "exemplo-demonstracao.json")
    assert dados["usuario"] == "servidor.demo" and len(casos) >= 5
