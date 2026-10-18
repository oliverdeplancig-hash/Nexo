"""Avaliação das respostas pelo autor e lacunas para a gestão do motor."""

import pytest

from apps.acesso.models import Classificacao
from apps.auditoria.models import EventoAuditoria
from apps.conversas.models import Conversa, Mensagem, Origem
from apps.motor.models import Regra


def _troca(usuario, pergunta, origem, **resposta):
    conversa = Conversa.objects.create(usuario=usuario, titulo=pergunta[:40])
    Mensagem.objects.create(conversa=conversa, papel=Mensagem.Papel.USUARIO, conteudo=pergunta)
    return Mensagem.objects.create(
        conversa=conversa,
        papel=Mensagem.Papel.ASSISTENTE,
        conteudo=resposta.pop("conteudo", "Resposta do assistente com trecho confidencial."),
        origem=origem,
        **resposta,
    )


@pytest.fixture
def respostas(usuarios):
    gp = usuarios["gp"]
    return {
        "boa": _troca(gp, "Como solicito férias?", Origem.DETERMINISTICO, rastro={"regra": {"codigo": "MD-001"}}),
        "sem_fontes": _troca(
            gp,
            "Qual o prazo do auxílio-creche?",
            Origem.SEM_FONTES,
            rastro={"motor": {"candidatos": [{"codigo": "MD-009", "titulo": "Benefícios", "pontuacao": 0.48}]}},
        ),
        "rag": _troca(gp, "Quem assina o termo de posse?", Origem.RAG),
    }


# ---------------------------------------------------------------- avaliação
def test_autor_avalia_resposta_e_ve_no_historico(cliente, usuarios, respostas):
    c = cliente(usuarios["gp"])
    r = c.put(
        f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/",
        {"util": False, "motivo": "incompleta", "comentario": "Faltou o prazo."},
        format="json",
    )
    assert r.status_code == 200, r.content
    historico = c.get(f"/api/v1/conversas/{respostas['rag'].conversa_id}/mensagens/").json()
    assert historico[0]["avaliacao"] is None  # pergunta do usuário não tem avaliação
    assert historico[1]["avaliacao"]["motivo"] == "incompleta"

    # muda de ideia: útil apaga o motivo
    r = c.put(
        f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/", {"util": True, "motivo": "incompleta"}, format="json"
    )
    assert r.json()["util"] is True and r.json()["motivo"] == ""
    assert c.delete(f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/").status_code == 204


def test_ninguem_avalia_resposta_de_outra_pessoa(cliente, usuarios, respostas):
    r = cliente(usuarios["ti"]).put(
        f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/", {"util": False}, format="json"
    )
    assert r.status_code == 404


def test_pergunta_do_usuario_nao_pode_ser_avaliada(cliente, usuarios, respostas):
    pergunta = Mensagem.objects.get(conversa=respostas["rag"].conversa, papel=Mensagem.Papel.USUARIO)
    r = cliente(usuarios["gp"]).put(f"/api/v1/mensagens/{pergunta.id}/avaliacao/", {"util": True}, format="json")
    assert r.status_code == 404


def test_motivo_invalido_e_recusado(cliente, usuarios, respostas):
    r = cliente(usuarios["gp"]).put(
        f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/", {"util": False, "motivo": "xyz"}, format="json"
    )
    assert r.status_code == 400


# ---------------------------------------------------------------- lacunas
def test_lacunas_exigem_gestao_de_regras(cliente, usuarios, respostas):
    assert cliente(usuarios["gp"]).get("/api/v1/lacunas/").status_code == 403
    assert cliente(usuarios["super"]).get("/api/v1/lacunas/").status_code == 403


def test_lacunas_listam_sem_fontes_e_negativas_sem_identificar_autor_nem_resposta(cliente, usuarios, respostas):
    cliente(usuarios["gp"]).put(
        f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/", {"util": False, "motivo": "incorreta"}, format="json"
    )
    r = cliente(usuarios["gestor"]).get("/api/v1/lacunas/")
    assert r.status_code == 200
    itens = {i["pergunta"]: i for i in r.json()["results"]}
    assert set(itens) == {"Qual o prazo do auxílio-creche?", "Quem assina o termo de posse?"}
    sem_fontes = itens["Qual o prazo do auxílio-creche?"]
    assert sem_fontes["regra_proxima"] == {"codigo": "MD-009", "titulo": "Benefícios", "pontuacao": 0.48}
    assert itens["Quem assina o termo de posse?"]["avaliacao"]["motivo"] == "incorreta"
    bruto = r.content.decode()
    assert "confidencial" not in bruto  # conteúdo da resposta não sai
    assert "gp" not in {k for i in r.json()["results"] for k in i}  # nada de autor
    assert usuarios["gp"].username not in bruto and "Gestão de Pessoas" not in bruto

    so_negativas = cliente(usuarios["gestor"]).get("/api/v1/lacunas/?tipo=negativas").json()["results"]
    assert [i["pergunta"] for i in so_negativas] == ["Quem assina o termo de posse?"]


def test_fonte_restrita_nao_aparece_para_o_gestor(cliente, usuarios, criar_documento):
    restrito = criar_documento(
        "Sindicância interna", "Conteúdo sigiloso da sindicância.", setor="GP", classificacao=Classificacao.RESTRITO
    )
    geral = criar_documento("Manual de posse", "A posse é assinada pela autoridade competente.", setor="GP")
    m = _troca(
        usuarios["gp"],
        "Quem assina?",
        Origem.EXTRATIVO,
        fontes=[{"documento_id": restrito.id, "citada": True}, {"documento_id": geral.id, "citada": True}],
    )
    item = cliente(usuarios["gestor"]).get("/api/v1/lacunas/").json()["results"][0]
    assert item["id"] == m.id
    assert item["fontes"] == [{"documento_id": geral.id, "titulo": "Manual de posse"}]


def test_tratar_lacuna_vincula_regra_audita_e_sai_das_pendentes(cliente, usuarios, respostas):
    regra = Regra.objects.create(
        codigo="MD-010", titulo="Auxílio-creche", resposta="...", criada_por=usuarios["gestor"]
    )
    c = cliente(usuarios["gestor"])
    lacuna = respostas["sem_fontes"]
    r = c.post(
        f"/api/v1/lacunas/{lacuna.id}/tratar/", {"regra": regra.id, "observacao": "Regra criada."}, format="json"
    )
    assert r.status_code == 200, r.content
    assert r.json()["tratamento"]["regra"] == "MD-010"
    assert lacuna.id not in [i["id"] for i in c.get("/api/v1/lacunas/").json()["results"]]
    assert lacuna.id in [i["id"] for i in c.get("/api/v1/lacunas/?situacao=tratadas").json()["results"]]
    assert EventoAuditoria.objects.filter(tipo="LACUNA_TRATADA", usuario=usuarios["gestor"]).exists()

    assert c.delete(f"/api/v1/lacunas/{lacuna.id}/tratar/").status_code == 204
    assert lacuna.id in [i["id"] for i in c.get("/api/v1/lacunas/").json()["results"]]


def test_resposta_boa_nao_e_lacuna(cliente, usuarios, respostas):
    r = cliente(usuarios["gestor"]).post(f"/api/v1/lacunas/{respostas['boa'].id}/tratar/", {}, format="json")
    assert r.status_code == 404


def test_resumo_conta_respostas_e_avaliacoes(cliente, usuarios, respostas):
    c = cliente(usuarios["gp"])
    c.put(f"/api/v1/mensagens/{respostas['boa'].id}/avaliacao/", {"util": True}, format="json")
    c.put(f"/api/v1/mensagens/{respostas['rag'].id}/avaliacao/", {"util": False}, format="json")
    dados = cliente(usuarios["gestor"]).get("/api/v1/lacunas/resumo/").json()
    assert dados["respostas"] == 3
    assert dados["por_origem"] == {"deterministico": 1, "sem_fontes": 1, "rag": 1}
    assert (dados["avaliadas"], dados["uteis"], dados["nao_uteis"]) == (2, 1, 1)
    assert dados["lacunas_pendentes"] == 2


def test_apagar_conversa_apaga_a_lacuna(cliente, usuarios, respostas):
    respostas["sem_fontes"].conversa.delete()
    itens = cliente(usuarios["gestor"]).get("/api/v1/lacunas/").json()["results"]
    assert itens == []
