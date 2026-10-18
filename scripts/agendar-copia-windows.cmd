@echo off
rem Agenda a copia de seguranca diaria do Nexo (padrao 12:30). Outro horario: agendar-copia-windows.cmd 18:00
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0agendar-copia-windows.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0agendar-copia-windows.ps1" -Horario %1
)
pause
