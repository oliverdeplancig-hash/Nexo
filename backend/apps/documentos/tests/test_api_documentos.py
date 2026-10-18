import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.acesso.models import Classificacao
from apps.auditoria.models import EventoAuditoria
from apps.documentos.models import Documento, StatusDocumento
from apps.ingestao.pipeline import processar

pytestmark = pytest.mark.django_db


def test_documento_restrito_responde_404_e_nao_aparece_na_lista(usuarios, criar_documento, cliente):
    restrito = criar_documento("Sigiloso", "conteúdo reservado", setor="TI", classificacao=Classificacao.RESTRITO)
    geral = criar_documento("Aberto", "conteúdo aberto")
    c = cliente(usuarios["gp"])
    ids = [d["id"] for d in c.get("/api/v1/documentos/").json()["results"]]
    assert ids == [geral.id]
    assert c.get(f"/api/v1/documentos/{restrito.id}/").status_code == 404
    assert c.get(f"/api/v1/documentos/{restrito.id}/arquivo/").status_code == 404


def test_download_exige_permissao_e_e_auditado(usuarios, criar_documento, cliente):
    doc = criar_documento("Aberto", "conteúdo aberto")
    c = cliente(usuarios["ti"])
    assert c.get(f"/api/v1/documentos/{doc.id}/arquivo/?download=1").status_code == 403
    assert EventoAuditoria.objects.filter(tipo="FALHA_AUTORIZACAO").exists()
    assert c.get(f"/api/v1/documentos/{doc.id}/arquivo/").status_code == 200


def test_classificacao_so_aparece_para_quem_pode(usuarios, criar_documento, cliente):
    doc = criar_documento("Aberto", "conteúdo aberto", setor="GP")
    assert cliente(usuarios["gp"]).get(f"/api/v1/documentos/{doc.id}/").json()["classificacao"] == "geral"
    assert cliente(usuarios["ti"]).get(f"/api/v1/documentos/{doc.id}/").json()["classificacao"] is None


def test_compartilhar_nao_permite_escalar_acoes(usuarios, criar_documento, cliente):
    doc = criar_documento("Aberto", "conteúdo aberto")
    resposta = cliente(usuarios["ti"]).post(
        f"/api/v1/documentos/{doc.id}/compartilhar/",
        {"usuario": usuarios["gp"].id, "acoes": ["visualizar"]},
        format="json",
    )
    assert resposta.status_code == 403  # ti não tem "compartilhar"


def test_importacao_processa_e_disponibiliza(usuarios, setores, cliente):
    arquivo = SimpleUploadedFile(
        "guia.md", "# Guia\n\nO ponto eletrônico fecha no dia 25.".encode(), content_type="text/markdown"
    )
    c = cliente(usuarios["gestor"])
    resposta = c.post(
        "/api/v1/ingestao/importar/",
        {
            "arquivos": [arquivo],
            "setor_responsavel": setores["GP"].id,
            "classificacao": "geral",
            "titulo": "Guia do ponto",
        },
        format="multipart",
    )
    assert resposta.status_code == 201, resposta.content
    doc = Documento.objects.get(pk=resposta.json()["resultados"][0]["id"])
    assert doc.status == StatusDocumento.RECEBIDO
    assert cliente(usuarios["gp"]).get(f"/api/v1/documentos/{doc.id}/").status_code == 404  # ainda não disponível
    processar(doc)
    doc.refresh_from_db()
    assert doc.status == StatusDocumento.DISPONIVEL and doc.trechos.exists() and doc.indexacao_semantica
    busca = cliente(usuarios["gp"]).get("/api/v1/busca/?q=ponto eletrônico").json()
    assert busca["resultados"][0]["documento"]["id"] == doc.id
    assert "\u0002" in busca["resultados"][0]["trechos"][0]["destaque"]


def test_importacao_rejeita_formato_e_assinatura(usuarios, setores, cliente):
    c = cliente(usuarios["gestor"])
    falso_pdf = SimpleUploadedFile("x.pdf", b"nao sou pdf", content_type="application/pdf")
    exe = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
    resposta = c.post(
        "/api/v1/ingestao/importar/",
        {"arquivos": [falso_pdf, exe], "setor_responsavel": setores["GP"].id},
        format="multipart",
    )
    assert resposta.status_code == 400
    erros = [r["erro"] for r in resposta.json()["resultados"]]
    assert "PDF" in erros[0] and "Formato" in erros[1]


def test_importacao_exige_funcao(usuarios, setores, cliente):
    arquivo = SimpleUploadedFile("a.txt", b"texto", content_type="text/plain")
    resposta = cliente(usuarios["gp"]).post("/api/v1/ingestao/importar/", {"arquivos": [arquivo]}, format="multipart")
    assert resposta.status_code == 403


def test_busca_nao_revela_restritos_nem_em_facetas(usuarios, criar_documento, cliente):
    criar_documento("Sigiloso", "orçamento reservado da operação", setor="TI", classificacao=Classificacao.RESTRITO)
    criar_documento("Público", "orçamento anual aprovado")
    dados = cliente(usuarios["gp"]).get("/api/v1/busca/?q=orçamento").json()
    assert dados["total_documentos"] == 1
    assert [f["setor_responsavel__sigla"] for f in dados["facetas"]["setor"]] == ["GP"]


@pytest.mark.skipif(not __import__("shutil").which("tesseract"), reason="Tesseract não instalado")
def test_pdf_digitalizado_entra_na_busca_via_ocr(usuarios, setores, cliente):
    from apps.ingestao.ocr import obter_ocr
    from apps.ingestao.tests.test_ocr import _pdf_digitalizado

    obter_ocr.cache_clear()
    arquivo = SimpleUploadedFile("escaneado.pdf", _pdf_digitalizado(["Regimento interno", "Plantao de domingo"]))
    resposta = cliente(usuarios["gestor"]).post(
        "/api/v1/ingestao/importar/",
        {"arquivos": [arquivo], "setor_responsavel": setores["GP"].id, "classificacao": "geral"},
        format="multipart",
    )
    doc = Documento.objects.get(pk=resposta.json()["resultados"][0]["id"])
    processar(doc)
    doc.refresh_from_db()
    assert doc.status == StatusDocumento.DISPONIVEL and doc.paginas_ocr == 1
    assert doc.etapas.filter(situacao="aviso", mensagem__icontains="OCR").exists()
    busca = cliente(usuarios["gp"]).get("/api/v1/busca/?q=regimento").json()
    assert busca["resultados"][0]["documento"]["id"] == doc.id
