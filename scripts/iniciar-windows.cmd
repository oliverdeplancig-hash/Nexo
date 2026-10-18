@echo off
rem Inicia o Nexo no Windows (duplo clique). Registro em scripts\iniciar.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar-windows.ps1"
