import io
import shutil

import pytest
from django.test import override_settings
from PIL import Image, ImageDraw, ImageFont

from apps.ingestao import ocr as modulo_ocr
from apps.ingestao.extratores import FalhaExtracao, extrair

TEM_TESSERACT = shutil.which("tesseract") is not None
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _imagem_com_texto(linhas: list[str]) -> Image.Image:
    imagem = Image.new("L", (1700, 600), 255)
    desenho = ImageDraw.Draw(imagem)
    try:
        fonte = ImageFont.truetype(FONTE, 48)
    except OSError:
        fonte = ImageFont.load_default()
    for i, linha in enumerate(linhas):
        desenho.text((80, 80 + i * 90), linha, fill=0, font=fonte)
    return imagem


def _pdf_digitalizado(linhas: list[str]) -> bytes:
    """PDF sem camada de texto: só a imagem da página, como um escaneamento."""
    buffer = io.BytesIO()
    _imagem_com_texto(linhas).convert("RGB").save(buffer, format="PDF", resolution=150)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _limpar_cache_ocr():
    modulo_ocr.obter_ocr.cache_clear()
    yield
    modulo_ocr.obter_ocr.cache_clear()


@pytest.mark.skipif(not TEM_TESSERACT, reason="Tesseract não instalado")
def test_pdf_digitalizado_e_lido_por_ocr():
    blocos = extrair(_pdf_digitalizado(["Portaria de férias", "Prazo de trinta dias"]), ".pdf")
    assert blocos[0].ocr is True and blocos[0].pagina == 1
    texto = blocos[0].texto.lower()
    assert "portaria" in texto and "prazo" in texto


@pytest.mark.skipif(not TEM_TESSERACT, reason="Tesseract não instalado")
def test_imagem_png_e_lida_por_ocr():
    buffer = io.BytesIO()
    _imagem_com_texto(["Protocolo geral"]).save(buffer, format="PNG")
    blocos = extrair(buffer.getvalue(), ".png")
    assert "protocolo" in blocos[0].texto.lower()


@override_settings(
    NEXO_OCR={"MOTOR": "desligado", "TESSERACT_CMD": "", "TESSDATA_DIR": "", "IDIOMA": "por", "DPI": 300}
)
def test_sem_ocr_mensagem_orienta_instalacao():
    with pytest.raises(FalhaExtracao, match="Tesseract"):
        extrair(_pdf_digitalizado(["Texto qualquer"]), ".pdf")


def test_imagem_com_assinatura_errada_e_recusada():
    with pytest.raises(FalhaExtracao, match="imagem válida"):
        extrair(b"nao sou png", ".png")
