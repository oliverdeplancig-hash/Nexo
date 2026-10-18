# Inicia o Nexo localmente no Windows (backend + frontend em janelas separadas).
# Pré-requisitos: PostgreSQL com pgvector, Ollama, Python 3.11+, Node 20+.
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"

if (-not (Test-Path (Join-Path $backend ".venv"))) {
    Write-Host "Criando ambiente virtual e instalando dependências..."
    python -m venv (Join-Path $backend ".venv")
    & (Join-Path $backend ".venv\Scripts\pip.exe") install -r (Join-Path $backend "requirements-dev.txt")
}
if (-not (Test-Path (Join-Path $backend ".env"))) {
    Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env")
    Write-Host "Arquivo backend\.env criado. Revise as configurações." -ForegroundColor Yellow
}
$py = Join-Path $backend ".venv\Scripts\python.exe"
Push-Location $backend
& $py manage.py migrate
& $py manage.py inicializar_nexo
Pop-Location

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; .\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 nexo.asgi:application"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Push-Location $frontend; npm install; Pop-Location }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev"
Write-Host "Nexo em http://localhost:5173" -ForegroundColor Green
