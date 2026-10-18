@echo off
rem Faz uma copia de seguranca do Nexo agora (banco + arquivos). Registro em scripts\copia-seguranca.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0copia-seguranca.ps1"
if errorlevel 1 (echo. & echo A copia FALHOU. Veja scripts\copia-seguranca.log) else (echo. & echo Copia concluida.)
pause
