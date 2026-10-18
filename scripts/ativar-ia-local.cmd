@echo off
rem Ativa a IA local (Ollama) no Nexo. Registro em scripts\ativar-ia.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ativar-ia-local.ps1"
