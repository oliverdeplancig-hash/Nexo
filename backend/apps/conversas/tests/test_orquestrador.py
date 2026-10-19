import pytest
from asgiref.sync import async_to_sync

from apps.acesso.models import Acao, AutorizacaoDocumento, Classificacao
from apps.conversas.models import Conversa, Origem
from apps.conversas.orquestrador import ErroConversa, executar
from apps.motor.models import Regra, StatusRegra

pytestmark = pytest.mark.django_db


def _perguntar(usuario, texto, **kw):
    eventos = []

    async def emitir(e):
        eventos.append(e)

    async_to_sync(executar)(usuario, kw.pop("conversa_id", None), texto, emitir, **kw)
    return eventos, next(e for e in eventos if e["tipo"] == "resposta")["mensagem"]


def test_motor_responde_sem_llm(usuarios):
    Regra.objects.create(
        codigo="MD-001",
        titulo="Férias",
        frases_exemplo=["como solicitar férias"],
        resposta="Solicite com 30 dias.",
        status=StatusRegra.PUBLICADA,
    )
    eventos, msg = _perguntar(usuarios["gp"], "Como solicitar férias?")
    assert msg["origem"] == Origem.DETERMINISTICO
    assert msg["conteudo"] == "Solicite com 30 dias."
    assert not [e for e in eventos if e["tipo"] == "token"]


def test_rag_cita_somente_documentos_autorizados(usuarios, criar_documento):
    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com cinco dias de antecedência.")
    criar_documento(
        "Diárias sigilosas",
        "Diárias da missão especial são pagas em dobro.",
        setor="TI",
        classificacao=Classificacao.RESTRITO,
    )
    eventos, msg = _perguntar(usuarios["gp"], "Qual a antecedência para solicitar diárias?")
    assert msg["origem"] == Origem.RAG
    assert msg["confianca"] == "fundamentada"
    titulos = {f["titulo"] for f in msg["fontes"]}
    assert titulos == {"Manual de diárias"}
    assert "dobro" not in msg["conteudo"]
    assert [e["etapa"] for e in eventos if e["tipo"] == "status"] == ["analisando", "consultando_fontes", "gerando"]
    assert any(e["tipo"] == "token" for e in eventos)


def test_sem_evidencia_sugere_setor(usuarios, criar_documento):
    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com antecedência.")
    _, msg = _perguntar(usuarios["gp"], "Como funciona a licença de férias?")
    assert msg["origem"] == Origem.SEM_FONTES
    assert [s["sigla"] for s in msg["setores_sugeridos"]] == ["GP"]


def test_conversa_de_outro_usuario_e_inexistente(usuarios):
    conversa = Conversa.objects.create(usuario=usuarios["ti"], titulo="minha")
    with pytest.raises(ErroConversa) as erro:
        _perguntar(usuarios["gp"], "oi", conversa_id=conversa.id)
    assert erro.value.codigo == "conversa_inexistente"


def test_contexto_de_documento_restrito_e_negado(usuarios, criar_documento):
    doc = criar_documento("Sigiloso", "conteúdo reservado", setor="TI", classificacao=Classificacao.RESTRITO)
    with pytest.raises(ErroConversa):
        _perguntar(usuarios["gp"], "resuma", documento_id=doc.id)


def test_historico_oculta_fonte_apos_revogacao(usuarios, criar_documento, cliente):
    doc = criar_documento(
        "Plano",
        "O plano é acionado após quatro horas de indisponibilidade.",
        setor="TI",
        classificacao=Classificacao.RESTRITO,
    )
    aut = AutorizacaoDocumento.objects.create(documento=doc, usuario=usuarios["gp"], acoes=[Acao.VISUALIZAR])
    _, msg = _perguntar(usuarios["gp"], "Quando o plano é acionado?")
    assert msg["fontes"]
    conversa = Conversa.objects.get(usuario=usuarios["gp"])
    aut.delete()
    historico = cliente(usuarios["gp"]).get(f"/api/v1/conversas/{conversa.id}/mensagens/").json()
    assert historico[-1]["fontes"] == []


def test_ia_indisponivel_degrada_para_extrativo(usuarios, criar_documento, monkeypatch):
    from apps.ia import provedores

    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com cinco dias de antecedência.")

    async def falha(self, mensagens):
        raise provedores.ProvedorIndisponivel("fora do ar")
        yield  # pragma: no cover

    monkeypatch.setattr(provedores.ProvedorFalso, "gerar_stream", falha)
    eventos, msg = _perguntar(usuarios["gp"], "antecedência das diárias")
    assert msg["origem"] == Origem.EXTRATIVO
    assert any(e["tipo"] == "aviso" and e["codigo"] == "ia_indisponivel" for e in eventos)
    assert msg["fontes"] and msg["fontes"][0]["citada"]


def test_fila_da_ia_cheia_responde_com_trechos_sem_virar_lacuna(usuarios, criar_documento, monkeypatch):
    """ADR-020: com a fila cheia a pessoa recebe os trechos na hora; isso não é falta de conhecimento."""
    from contextlib import asynccontextmanager

    from apps.conversas import lacunas, orquestrador
    from apps.ia.fila import IAOcupada

    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com cinco dias de antecedência.")

    @asynccontextmanager
    async def cheia(avisar=None):
        raise IAOcupada()
        yield  # pragma: no cover

    monkeypatch.setattr(orquestrador, "vaga", cheia)
    eventos, msg = _perguntar(usuarios["gp"], "antecedência das diárias")
    assert msg["origem"] == Origem.EXTRATIVO and msg["fontes"]
    assert any(e["tipo"] == "aviso" and e["codigo"] == "ia_ocupada" for e in eventos)
    assert "muitas perguntas" in msg["conteudo"].lower()
    assert not lacunas._lacunas_base().filter(pk=msg["id"]).exists()
