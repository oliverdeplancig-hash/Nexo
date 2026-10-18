"""Painel do acervo e aviso de fonte revogada (ADR-016)."""

from datetime import timedelta

from django.utils import timezone

from apps.acesso.models import Classificacao
from apps.documentos.models import Documento
from apps.motor.models import FonteRegra, Regra, StatusRegra
from apps.notificacoes.models import Notificacao

hoje = timezone.localdate


def test_painel_conta_so_o_que_a_pessoa_ve(cliente, usuarios, criar_documento):
    geral = criar_documento("Manual geral", "texto geral sobre férias")
    criar_documento("Plano restrito TI", "texto sigiloso", setor="TI", classificacao=Classificacao.RESTRITO)
    revogado = criar_documento("Norma antiga", "texto antigo")
    Documento.objects.filter(pk=revogado.pk).update(vigencia="revogado")
    Documento.objects.filter(pk=geral.pk).update(revisar_em=hoje() - timedelta(days=4))

    c = cliente(usuarios["gestor"])  # TI, importar_documentos; o restrito não tem autorização para ele
    c.get(f"/api/v1/documentos/{geral.id}/")
    c.get(f"/api/v1/documentos/{geral.id}/")
    dados = c.get("/api/v1/painel/acervo/").json()
    assert dados["resumo"]["total"] == 2
    assert dados["resumo"]["revogados"] == 1 and dados["resumo"]["revisao_atrasada"] == 1
    assert [d["titulo"] for d in dados["revisoes_atrasadas"]] == ["Manual geral"]
    assert dados["revisoes_atrasadas"][0]["dias_atraso"] == 4
    assert dados["mais_consultados"][0] == {
        "id": geral.id,
        "titulo": "Manual geral",
        "setor": "GP",
        "vigencia": "vigente",
        "aberturas": 2,
    }
    assert "Plano restrito TI" not in str(dados)
    assert "gestor" not in str(dados["mais_consultados"])  # sem quem abriu


def test_painel_exige_funcao_de_gestao(cliente, usuarios):
    assert cliente(usuarios["gp"]).get("/api/v1/painel/acervo/").status_code == 403
    assert cliente(usuarios["auditor"]).get("/api/v1/painel/acervo/").status_code == 200


def test_revogar_avisa_quem_mantem_a_regra(cliente, usuarios, criar_documento):
    doc = criar_documento("Norma de férias", "texto", responsavel=usuarios["gp"])
    regra = Regra.objects.create(
        codigo="MD-077", titulo="Prazo", resposta="...", status=StatusRegra.PUBLICADA, criada_por=usuarios["gestor"]
    )
    FonteRegra.objects.create(regra=regra, documento=doc, trecho_citado="x")
    rascunho = Regra.objects.create(codigo="MD-078", titulo="Rascunho", resposta="...", criada_por=usuarios["gestor"])
    FonteRegra.objects.create(regra=rascunho, documento=doc, trecho_citado="x")

    cliente(usuarios["gp"]).post(f"/api/v1/documentos/{doc.id}/revogar/", {"motivo": "nova norma"}, format="json")
    avisos = Notificacao.objects.filter(tipo="regra_fonte_revogada")
    assert [(a.usuario_id, a.dados["regra"]) for a in avisos] == [(usuarios["gestor"].id, "MD-077")]
