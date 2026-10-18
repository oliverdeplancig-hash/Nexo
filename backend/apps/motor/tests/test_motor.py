import pytest

from apps.acesso.models import Classificacao
from apps.motor.models import FonteRegra, Regra, StatusRegra
from apps.motor.motor import avaliar, renderizar

pytestmark = pytest.mark.django_db


def _regra(codigo, exemplos, **extra):
    return Regra.objects.create(
        codigo=codigo,
        titulo=codigo,
        frases_exemplo=exemplos,
        resposta=f"Resposta {codigo}",
        status=StatusRegra.PUBLICADA,
        **extra,
    )


def test_responde_regra_que_casa(usuarios):
    _regra("MD-001", ["Como solicito férias?"], palavras_chave=["férias"])
    r = avaliar("Como faço para solicitar minhas férias?", usuarios["gp"])
    assert r.decisao == "responder" and r.regra.codigo == "MD-001"
    assert r.rastro["candidatos"][0]["codigo"] == "MD-001"


def test_resultado_e_identico_em_execucoes_repetidas(usuarios):
    _regra("MD-001", ["Como solicito férias?"])
    _regra("MD-002", ["Como solicito licença?"])
    primeiro = avaliar("solicitar férias e licença", usuarios["gp"])
    for _ in range(20):
        r = avaliar("solicitar férias e licença", usuarios["gp"])
        assert (r.decisao, r.rastro) == (primeiro.decisao, primeiro.rastro)


def test_abaixo_do_limiar_nao_aplica(usuarios):
    _regra("MD-001", ["Como solicito férias?"])
    assert avaliar("horário do restaurante", usuarios["gp"]).decisao == "nao_aplicavel"


def test_termos_obrigatorios_e_excludentes(usuarios):
    _regra("MD-001", ["prazo do processo"], termos_obrigatorios=["processo"], termos_excludentes=["licitação"])
    assert avaliar("qual o prazo do processo?", usuarios["gp"]).decisao == "responder"
    assert avaliar("qual o prazo do processo de licitação?", usuarios["gp"]).decisao == "nao_aplicavel"
    assert avaliar("qual o prazo?", usuarios["gp"]).decisao == "nao_aplicavel"


def test_regex_tem_prioridade(usuarios):
    _regra("MD-009", ["algo totalmente diferente"], padroes_regex=[r"\bcontracheque\b"])
    r = avaliar("Onde vejo meu contracheque?", usuarios["gp"])
    assert r.decisao == "responder" and r.pontuacao == 1.0


def test_empate_pede_desambiguacao(usuarios):
    _regra("MD-001", ["como solicitar declaração funcional"])
    _regra("MD-002", ["como solicitar declaração funcional"])
    r = avaliar("como solicitar declaração funcional", usuarios["gp"])
    assert r.decisao == "desambiguar"
    assert [c.regra.codigo for c in r.alternativas] == ["MD-001", "MD-002"]


def test_prioridade_desempata(usuarios):
    _regra("MD-001", ["como solicitar declaração funcional"])
    _regra("MD-002", ["como solicitar declaração funcional"], prioridade=5)
    r = avaliar("como solicitar declaração funcional", usuarios["gp"])
    assert r.decisao == "responder" and r.regra.codigo == "MD-002"


def test_rascunho_e_regras_de_outro_publico_sao_ignorados(usuarios, setores):
    Regra.objects.create(codigo="MD-R", titulo="r", frases_exemplo=["solicitar férias"], resposta="x")
    regra = _regra("MD-T", ["solicitar férias"])
    regra.setores_alvo.set([setores["TI"]])
    assert avaliar("solicitar férias", usuarios["gp"]).decisao == "nao_aplicavel"
    assert avaliar("solicitar férias", usuarios["ti"]).decisao == "responder"


def test_fonte_restrita_vira_apenas_encaminhamento(usuarios, setores, criar_documento):
    doc = criar_documento("Norma TI", "A senha deve ter 12 caracteres.", setor="TI", classificacao=Classificacao.SETOR)
    regra = _regra("MD-003", ["esqueci minha senha"], setor_responsavel=setores["TI"])
    FonteRegra.objects.create(regra=regra, documento=doc, trecho_citado="A senha deve ter 12 caracteres.")

    para_ti = renderizar(regra, usuarios["ti"])
    assert para_ti["modo"] == "completo" and len(para_ti["fontes"]) == 1

    para_gp = renderizar(regra, usuarios["gp"])
    assert para_gp["modo"] == "somente_roteamento"
    assert para_gp["fontes"] == []
    assert "Resposta MD-003" not in para_gp["conteudo"]
    assert para_gp["setor"]["canal_contato"] is None  # contato visível só ao próprio setor
