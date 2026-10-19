"""OCR de páginas digitalizadas (ver docs/adr/ADR-009).

Motor padrão: Tesseract com o idioma português, executado localmente — nenhuma
imagem sai da máquina. O OCR só é aplicado a páginas sem camada de texto.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger("nexo.ocr")


class OCRIndisponivel(Exception):
    """O motor de OCR não está instalado ou configurado."""


class MotorOCR:
    nome = "base"

    def disponivel(self) -> bool:
        raise NotImplementedError

    def reconhecer(self, imagem) -> str:
        """Recebe uma imagem PIL e devolve o texto reconhecido."""
        raise NotImplementedError


class OCRDesligado(MotorOCR):
    nome = "desligado"

    def disponivel(self) -> bool:
        return False

    def reconhecer(self, imagem) -> str:
        raise OCRIndisponivel("OCR desligado na configuração (NEXO_OCR_MOTOR).")


class OCRTesseract(MotorOCR):
    nome = "tesseract"

    def __init__(self):
        import pytesseract

        self._pytesseract = pytesseract
        cfg = settings.NEXO_OCR
        caminho = cfg["TESSERACT_CMD"] or shutil.which("tesseract") or _caminho_padrao_windows()
        if caminho:
            pytesseract.pytesseract.tesseract_cmd = caminho
        self.idioma = cfg["IDIOMA"]
        # Pasta própria de idiomas (ex.: backend/.tessdata no Windows, sem precisar de administrador).
        # Usa a variável de ambiente padrão do Tesseract: no Windows, aspas em --tessdata-dir
        # chegam literais ao executável.
        if cfg.get("TESSDATA_DIR"):
            os.environ["TESSDATA_PREFIX"] = str(cfg["TESSDATA_DIR"])

    def disponivel(self) -> bool:
        try:
            idiomas = set(self._pytesseract.get_languages(config=""))
        except Exception:  # binário ausente ou inválido
            return False
        return all(i in idiomas for i in self.idioma.split("+"))

    def reconhecer(self, imagem) -> str:
        try:
            # psm 3: segmentação automática de página (documentos administrativos comuns)
            return self._pytesseract.image_to_string(imagem, lang=self.idioma, config="--psm 3")
        except Exception as erro:
            raise OCRIndisponivel(f"Falha no Tesseract: {erro}") from erro


def _caminho_padrao_windows() -> str | None:
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "") + "\\Programs"):
        candidato = os.path.join(base, "Tesseract-OCR", "tesseract.exe")
        if base and os.path.exists(candidato):
            return candidato
    return None


@lru_cache(maxsize=1)
def obter_ocr() -> MotorOCR:
    motor = settings.NEXO_OCR["MOTOR"]
    if motor == "tesseract":
        try:
            ocr = OCRTesseract()
        except ImportError:
            logger.warning("pytesseract não instalado; OCR desligado.")
            return OCRDesligado()
        if not ocr.disponivel():
            logger.warning("Tesseract (idioma %s) não encontrado; OCR desligado.", settings.NEXO_OCR["IDIOMA"])
            return OCRDesligado()
        return ocr
    return OCRDesligado()


def renderizar_pagina_pdf(conteudo: bytes, indice: int):
    """Renderiza uma página do PDF (índice a partir de 0) como imagem PIL."""
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(conteudo)
    pagina = documento[indice]
    try:
        escala = settings.NEXO_OCR["DPI"] / 72
        return pagina.render(scale=escala, grayscale=True).to_pil()
    finally:
        pagina.close()  # fecha a página antes do documento (evita aviso do pdfium ao encerrar)
        documento.close()


def imagens_de_arquivo(conteudo: bytes):
    """Páginas de uma imagem (TIFF pode ter várias)."""
    from PIL import Image, ImageSequence

    with Image.open(io.BytesIO(conteudo)) as imagem:
        for quadro in ImageSequence.Iterator(imagem):
            yield quadro.convert("L")
