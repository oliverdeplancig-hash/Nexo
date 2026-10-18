"""Vigência e revisão de documentos (ADR-015)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.acesso.models import Classificacao
from apps.auditoria.models import EventoAuditoria
from apps.documentos.models import Documento
from apps.documentos.vigencia import avisar_revisoes
from apps.notificacoes.models import Notificacao

hoje = timezone.localdate


@pytest.fixture
def normas(criar_documento, usuarios):
    antiga = criar_documento(
        "Norma de plantão 2024", "O plantão de fim de semana começa às 07h de sábado.", responsavel=usuarios["gp"]
    )
    nova = criar_documento("Norma de plantão 2026", "O plantão de fim de semana começa às 08h de sábado.")
    return antiga, nova


def test_revogar_tira_da_busca_e_do_assistente_mas_mantem_consulta(cliente, usuarios, normas):
    antiga, nova = normas
    c = cliente(usuarios["gp"])  # responsável pela norma antiga: pode editar
    r = c.post(
        f"/api/v1/documentos/{antiga.id}/revogar/",
        {"motivo": "Revogada pela norma 2026", "substituido_por": nova.id},
        format="json",
    )
    assert r.status_code == 200, r.content
    dados = r.json()
    assert dados["vigencia"] == "revogado" and dados["substituido_por"] == {"id": nova.id, "titulo": nova.titulo}
    assert dados["revogado_em"] == hoje().isoformat()

    titulos = [x["documento"]["titulo"] for x in c.get("/api/v1/busca/?q=plantao%20sabado").json()["resultados"]]
    assert "Norma de plantão 2024" not in titulos and "Norma de plantão 2026" in titulos
    com_revogados = c.get("/api/v1/busca/?q=plantao%20sabado&revogados=1").json()["resultados"]
    assert "Norma de plantão 2024" in [x["documento"]["titulo"] for x in com_revogados]

    resposta = c.post(
        "/api/v1/conversas/perguntar/", {"texto": "Que horas começa o plantão de sábado?"}, format="json"
    ).json()
    assert all(f["documento_id"] != antiga.id for f in resposta["mensagem"]["fontes"])

    # continua consultável, com a revogação visível; o substituto mostra quem ele substitui
    assert c.get(f"/api/v1/documentos/{antiga.id}/").status_code == 200
    assert c.get(f"/api/v1/documentos/{nova.id}/").json()["substitui"] == [{"id": antiga.id, "titulo": antiga.titulo}]
    assert EventoAuditoria.objects.filter(tipo="DOCUMENTO_ALTERADO", detalhes__acao="revogar").exists()

    assert c.post(f"/api/v1/documentos/{antiga.id}/restabelecer/").json()["vigencia"] == "vigente"
    assert Documento.objects.get(pk=antiga.pk).substituido_por is None


def test_revogar_exige_motivo_e_permissao_de_edicao(cliente, usuarios, normas):
    antiga, _ = normas
    assert (
        cliente(usuarios["gp"]).post(f"/api/v1/documentos/{antiga.id}/revogar/", {}, format="json").status_code == 400
    )
    r = cliente(usuarios["ti"]).post(f"/api/v1/documentos/{antiga.id}/revogar/", {"motivo": "x"}, format="json")
    assert r.status_code == 403
    assert Documento.objects.get(pk=antiga.pk).vigencia == "vigente"


def test_substituto_restrito_nao_e_revelado(cliente, usuarios, criar_documento, normas):
    antiga, _ = normas
    sigiloso = criar_documento("Sigiloso TI", "conteúdo", setor="TI", classificacao=Classificacao.RESTRITO)
    Documento.objects.filter(pk=antiga.pk).update(vigencia="revogado", substituido_por=sigiloso)
    detalhe = cliente(usuarios["gp"]).get(f"/api/v1/documentos/{antiga.id}/").json()
    assert detalhe["substituido_por"] is None
    # e não dá para apontar como substituto um documento que a pessoa não vê
    r = cliente(usuarios["gp"]).post(
        f"/api/v1/documentos/{antiga.id}/revogar/", {"motivo": "x", "substituido_por": sigiloso.id}, format="json"
    )
    assert r.status_code == 400


def test_revisao_avisa_responsavel_uma_vez_e_repete_quando_atrasada(usuarios, normas, settings):
    antiga, nova = normas
    Documento.objects.filter(pk=antiga.pk).update(revisar_em=hoje() + timedelta(days=10))
    Documento.objects.filter(pk=nova.pk).update(revisar_em=hoje() + timedelta(days=200))
    assert avisar_revisoes() == 1
    aviso = Notificacao.objects.get(usuario=usuarios["gp"], tipo="revisao_documento")
    assert aviso.tipo == "revisao_documento" and "próxima" in aviso.titulo and aviso.link == f"/documentos/{antiga.id}"
    assert avisar_revisoes() == 0  # idempotente

    # atrasada: repete depois de REPETIR_DIAS
    Documento.objects.filter(pk=antiga.pk).update(
        revisar_em=hoje() - timedelta(days=1),
        revisao_avisada_em=hoje() - timedelta(days=settings.NEXO_REVISAO["REPETIR_DIAS"]),
    )
    assert avisar_revisoes() == 1
    assert "atrasada" in Notificacao.objects.filter(usuario=usuarios["gp"], tipo="revisao_documento").first().titulo


def test_sem_responsavel_avisa_quem_importa_no_setor(usuarios, criar_documento):
    doc = criar_documento("Sem dono", "texto qualquer", setor="TI")
    Documento.objects.filter(pk=doc.pk).update(responsavel=None, criado_por=None, revisar_em=hoje())
    avisar_revisoes()
    # gestor (TI, importar_documentos) recebe; ti (TI, só servidor) não
    assert Notificacao.objects.filter(usuario=usuarios["gestor"], tipo="revisao_documento").count() == 1
    assert not Notificacao.objects.filter(usuario=usuarios["ti"], tipo="revisao_documento").exists()


def test_registrar_revisao_e_aba_de_revisao(cliente, usuarios, normas):
    antiga, nova = normas
    Documento.objects.filter(pk__in=[antiga.pk, nova.pk]).update(revisar_em=hoje() + timedelta(days=5))
    c = cliente(usuarios["gp"])
    aba = [d["id"] for d in c.get("/api/v1/documentos/?aba=revisao").json()["results"]]
    assert aba == [antiga.id]  # só o que a pessoa pode editar
    assert c.get(f"/api/v1/documentos/{antiga.id}/").json()["situacao_revisao"] == "proxima"

    assert (
        c.post(f"/api/v1/documentos/{antiga.id}/revisao/", {"proxima": hoje().isoformat()}, format="json").status_code
        == 400
    )
    r = c.post(
        f"/api/v1/documentos/{antiga.id}/revisao/",
        {"proxima": (hoje() + timedelta(days=365)).isoformat()},
        format="json",
    )
    assert r.status_code == 200 and r.json()["revisado_em"] == hoje().isoformat()
    assert r.json()["situacao_revisao"] is None
    assert c.get("/api/v1/documentos/?aba=revisao").json()["results"] == []


def test_regra_com_fonte_revogada_avisa_e_baixa_a_confianca(cliente, usuarios, criar_documento):
    from apps.motor.models import FonteRegra, Regra, StatusRegra

    doc = criar_documento("Norma de férias antiga", "Férias com 30 dias de antecedência.")
    regra = Regra.objects.create(
        codigo="MD-090",
        titulo="Prazo de férias",
        frases_exemplo=["qual o prazo para pedir férias"],
        palavras_chave=["prazo", "férias"],
        termos_obrigatorios=["férias"],
        resposta="Peça com 30 dias de antecedência.",
        status=StatusRegra.PUBLICADA,
        publicada_em=timezone.now(),
        versao=1,
    )
    FonteRegra.objects.create(regra=regra, documento=doc, trecho_citado="30 dias")
    c = cliente(usuarios["gp"])
    pergunta = {"texto": "qual o prazo para pedir férias"}
    assert (
        c.post("/api/v1/conversas/perguntar/", pergunta, format="json").json()["mensagem"]["confianca"] == "verificada"
    )

    Documento.objects.filter(pk=doc.pk).update(vigencia="revogado", revogado_em=hoje())
    m = c.post("/api/v1/conversas/perguntar/", pergunta, format="json").json()["mensagem"]
    assert m["origem"] == "deterministico" and m["confianca"] == "cautela"
    assert "foi revogado" in m["conteudo"] and m["fontes"][0]["vigencia"] == "revogado"
