@echo off
rem Instala o OCR (Tesseract + portugues) para documentos digitalizados. Registro em scripts\instalar-ocr.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-ocr.ps1"
