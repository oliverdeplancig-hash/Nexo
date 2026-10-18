# ADR-009 — OCR local com Tesseract para documentos digitalizados

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Grande parte do acervo institucional é digitalizada (PDF de imagem, fotos e TIFF de scanner). Sem camada de
texto, esses arquivos falhavam na importação ("nenhum texto pôde ser extraído"). O Nexo roda em computador
local (Windows) e no servidor da instituição (Linux, sem Docker), e não pode enviar documentos para fora da
rede (ADR-004).

## Decisão
- OCR com **Tesseract** (idioma `por`), executado localmente pelo módulo `apps/ingestao/ocr.py`.
- Aplicado **somente** às páginas de PDF com menos de 25 caracteres úteis, e a imagens PNG, JPG e TIFF
  (inclusive TIFF de várias páginas). Páginas renderizadas a 300 dpi com `pypdfium2`, sem Poppler.
- O motor é trocável (`NEXO_OCR_MOTOR`: `tesseract` ou `desligado`). Sem OCR disponível, a importação falha
  com mensagem que orienta a instalação.
- Documentos lidos por OCR guardam `paginas_ocr`; a importação registra aviso e a tela do documento alerta
  que a leitura automática pode conter erros.

### Onde roda
| Ambiente | Instalação |
|---|---|
| Servidor Linux / nuvem (Ubuntu, Debian) | `apt install tesseract-ocr tesseract-ocr-por` |
| Contêiner Docker (opcional) | mesma linha no `Dockerfile` da imagem |
| Windows local | `scripts\instalar-ocr.cmd` (instalador do Tesseract + idioma português em `backend\.tessdata`) |

## Alternativas consideradas
- **Serviços de OCR em nuvem (Google Vision, AWS Textract, Azure Document Intelligence):** melhor precisão
  em manuscritos e tabelas, mas enviam documentos para fora da instituição — conflita com a ADR-004. Podem
  ser acrescentados como outro `MotorOCR` mediante nova ADR e classificação dos documentos.
- **EasyOCR / PaddleOCR:** bons resultados, mas exigem PyTorch/Paddle (gigabytes) e, de preferência, GPU.
- **Modelo de visão no Ollama:** promissor; lento em CPU e menos previsível. Candidato futuro.
- **OCRmyPDF:** excelente para gerar PDF pesquisável, mas depende de Ghostscript e mais binários; o Nexo só
  precisa do texto.

## Consequências
- Documentos digitalizados passam a entrar na busca e no assistente.
- OCR custa CPU (≈1–3 s por página); com o worker `processar_fila` isso não bloqueia o servidor web.
- Qualidade depende da digitalização (recomenda-se 300 dpi). Erros de leitura são sinalizados ao usuário.
- Backlog: pré-processamento (correção de inclinação), OCR de tabelas e avaliação de modelo de visão local.
