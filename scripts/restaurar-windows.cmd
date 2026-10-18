@echo off
rem Restaura uma copia de seguranca do Nexo. Opcional: caminho do arquivo .nexobak
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restaurar-windows.ps1" %*
pause
