"""Memória da conversa por compactação (ADR-021)."""

import pytest
from django.test import override_settings

from apps.acesso.models import Acao, AutorizacaoDocumento, Classificacao
from apps.conversas import memoria
from apps.conversas.models import Conversa, Mensagem

pytestmark = pytest.mark.django_db


def _troca(conversa, pergunta, resposta, documentos=(), origem="rag"):
    Mensagem.objects.create(conversa=conversa, papel=Mensagem.Papel.USUARIO, conteudo=pergunta)
    Mensagem.objects.create(
        conversa=conversa,
        papel=Mensagem.Papel.ASSISTENTE,
        conteudo=resposta,
        origem=origem,
        fontes=[{"documento_id": d, "citada": True} for d in documentos],
    )


@override_settings(NEXO_MEMORIA={"JANELA_RECENTE": 2, "MAXIMO_ITENS": 3})
def test_compacta_sem_copiar_respostas(usuarios, criar_documento):
    doc = criar_documento("Manual de diárias", "As diárias devem ser pedidas com cinco dias de antecedência.")
    conversa = Conversa.objects.create(usuario=usuarios["gp"])
    _troca(conversa, "Como pedir diárias?", "TEXTO SIGILOSO DA RESPOSTA", [doc.id])
    _troca(conversa, "E o prazo?", "Cinco dias [1]", [doc.id])
    assert memoria.atualizar(conversa)
    conversa.refresh_from_db()
    assert conversa.memoria["compactadas"] == 2  # a primeira troca saiu da janela de 2 mensagens
    assert memoria.atualizar(conversa, manter=0)
    conversa.refresh_from_db()
    assert "SIGILOSO" not in str(conversa.memoria)
    resumo = memoria.texto_para_ia(conversa, usuarios["gp"])
    assert "Como pedir diárias?" in resumo and "Manual de diárias" in resumo


@override_settings(NEXO_MEMORIA={"JANELA_RECENTE": 0, "MAXIMO_ITENS": 2})
def test_limita_itens_e_conta_descartados(usuarios):
    conversa = Conversa.objects.create(usuario=usuarios["gp"])
    for i in range(4):
        _troca(conversa, f"Pergunta {i}", "ok", origem="sem_fontes")
    memoria.atualizar(conversa, manter=0)
    conversa.refresh_from_db()
    assert [i["pergunta"] for i in conversa.memoria["itens"]] == ["Pergunta 2", "Pergunta 3"]
    assert conversa.memoria["descartadas"] == 2
    assert "não havia fontes" in memoria.texto_para_ia(conversa, usuarios["gp"])


def test_documento_que_deixou_de_ser_permitido_some_do_resumo(usuarios, criar_documento):
    doc = criar_documento("Plano reservado", "Conteúdo.")
    doc.classificacao = Classificacao.RESTRITO
    doc.save()
    aut = AutorizacaoDocumento.objects.create(documento=doc, usuario=usuarios["gp"], acoes=[Acao.VISUALIZAR])
    conversa = Conversa.objects.create(usuario=usuarios["gp"])
    _troca(conversa, "O que diz o plano?", "...", [doc.id])
    memoria.atualizar(conversa, manter=0)
    conversa.refresh_from_db()
    assert "Plano reservado" in memoria.texto_para_ia(conversa, usuarios["gp"])
    aut.delete()
    resumo = memoria.texto_para_ia(conversa, usuarios["gp"])
    assert "Plano reservado" not in resumo and "O que diz o plano?" in resumo


@pytest.mark.parametrize(
    "pergunta,continua",
    [
        ("e o prazo?", True),
        ("E para servidor cedido?", True),
        ("Quanto ao valor?", True),
        ("Qual o prazo disso?", True),
        ("Como pedir férias?", False),
        ("Qual o horário do protocolo?", False),
    ],
)
def test_reconhece_pergunta_de_continuacao(usuarios, pergunta, continua):
    conversa = Conversa.objects.create(usuario=usuarios["gp"])
    _troca(conversa, "Como pedir diárias?", "...")
    Mensagem.objects.create(conversa=conversa, papel=Mensagem.Papel.USUARIO, conteudo=pergunta)
    consulta, continuacao = memoria.pergunta_para_busca(conversa, pergunta)
    assert continuacao is continua
    assert ("diárias" in consulta) is continua


def test_continuacao_encontra_o_documento_da_pergunta_anterior(usuarios, criar_documento):
    from asgiref.sync import async_to_sync

    from apps.conversas.orquestrador import executar

    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com cinco dias de antecedência.")

    async def nada(_):
        pass

    primeira = async_to_sync(executar)(usuarios["gp"], None, "antecedência das diárias", nada)
    segunda = async_to_sync(executar)(usuarios["gp"], primeira.conversa_id, "e nesse caso?", nada)
    assert segunda.rastro.get("continuacao") and segunda.fontes
