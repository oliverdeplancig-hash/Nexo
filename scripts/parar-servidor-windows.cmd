@echo off
rem Para o servidor de rede do Nexo (ADR-019). Para ligar de novo: reinicie o computador ou
rem   schtasks /run /tn "Nexo - servidor"
echo parar> "%~dp0servidor.parar"
echo Pedido de parada enviado. Aguarde alguns segundos...
powershell -NoProfile -Command "for($i=0;$i -lt 30 -and (Test-Path '%~dp0servidor.parar');$i++){Start-Sleep 1}"
schtasks /end /tn "Nexo - servidor" >nul 2>&1
if exist "%~dp0servidor.parar" del "%~dp0servidor.parar"
echo Servidor do Nexo parado.
pause
