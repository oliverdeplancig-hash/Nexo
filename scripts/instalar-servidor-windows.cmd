@echo off
rem Instala o Nexo como servidor de rede neste computador (ADR-019). Precisa de Administrador.
net session >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0' -ArgumentList '%1'"
  exit /b
)
rem "instalar-servidor-windows.cmd teste" ensaia a rede sem inicio automatico nem mudar a energia do computador.
if /i "%1"=="teste" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-servidor-windows.ps1" -Teste
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-servidor-windows.ps1"
)
pause
