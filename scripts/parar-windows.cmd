@echo off
rem Encerra o Nexo local (backend, frontend e PostgreSQL embutido)
taskkill /f /im daphne.exe >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr LISTENING') do taskkill /f /pid %%p >nul 2>&1
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\backend\banco_local.py" parar
echo Nexo encerrado.
timeout /t 3 >nul
