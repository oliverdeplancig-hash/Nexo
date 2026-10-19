@echo off
rem Desfaz a instalacao do servidor de rede do Nexo (ADR-019): para o servidor, remove a tarefa de inicio
rem automatico e as regras de firewall. NAO apaga banco, documentos, copias de seguranca nem certificados.
net session >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
  exit /b
)
echo parar> "%~dp0servidor.parar"
powershell -NoProfile -Command "for($i=0;$i -lt 30 -and (Test-Path '%~dp0servidor.parar');$i++){Start-Sleep 1}"
if exist "%~dp0servidor.parar" del "%~dp0servidor.parar"
schtasks /end /tn "Nexo - servidor" >nul 2>&1
schtasks /delete /tn "Nexo - servidor" /f >nul 2>&1
powershell -NoProfile -Command "Get-NetFirewallRule -DisplayName 'Nexo (HTTPS e HTTP)','Nexo teste (HTTPS e HTTP)' -ErrorAction SilentlyContinue | Remove-NetFirewallRule"
echo.
echo Servidor de rede do Nexo removido deste computador. Dados e configuracao foram mantidos
echo (backend\.env, backend\.pgdata, armazenamento e copias). A tarefa de copia de seguranca, se existir,
echo continua agendada: remova-a no Agendador de Tarefas se nao quiser mais.
pause
