# Inicia o Nexo localmente no Windows, sem precisar de PostgreSQL instalado.
# 1) ambiente Python + dependencias  2) PostgreSQL embutido (pgserver)
# 3) migracoes e dados de demonstracao  4) backend e frontend  5) abre o navegador
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$log = Join-Path $PSScriptRoot "iniciar.log"
Start-Transcript -Path $log -Force | Out-Null
$env:PYTHONUTF8 = "1"

try {
    $py = Join-Path $backend ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Write-Host "[1/5] Criando ambiente Python..."
        & py -3.12 -m venv (Join-Path $backend ".venv")
        if ($LASTEXITCODE -ne 0) { & python -m venv (Join-Path $backend ".venv") }
    }
    Write-Host "[1/5] Instalando dependencias Python..."
    & $py -m pip install --disable-pip-version-check -q -r (Join-Path $backend "requirements-local.txt")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias Python." }

    $envArq = Join-Path $backend ".env"
    if (-not (Test-Path $envArq)) {
        $chave = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 50 | ForEach-Object { [char]$_ })
        [System.IO.File]::WriteAllLines($envArq, [string[]]@(
            "NEXO_SECRET_KEY=$chave",
            "NEXO_DEBUG=true",
            "NEXO_COOKIE_SEGURO=false",
            "NEXO_ALLOWED_HOSTS=localhost,127.0.0.1",
            "NEXO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173",
            "NEXO_PROCESSAR_IMEDIATAMENTE=true",
            "NEXO_IA_PROVEDOR=falso"
        ))
    }

    Write-Host "[2/5] Iniciando PostgreSQL local..."
    Push-Location $backend
    & $py banco_local.py iniciar
    if ($LASTEXITCODE -ne 0) { throw "Falha ao iniciar o PostgreSQL local." }

    Write-Host "[3/5] Preparando o banco..."
    & $py manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "Falha nas migracoes." }
    & $py manage.py carregar_demo
    Pop-Location

    Write-Host "[4/5] Iniciando backend e frontend..."
    $daphne = Join-Path $backend ".venv\Scripts\daphne.exe"
    Start-Process -FilePath $daphne -ArgumentList "-b", "127.0.0.1", "-p", "8000", "nexo.asgi:application" `
        -WorkingDirectory $backend -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $PSScriptRoot "backend.log") -RedirectStandardError (Join-Path $PSScriptRoot "backend-erros.log")

    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
        Write-Host "      Instalando dependencias do frontend (primeira vez)..."
        Push-Location $frontend
        & npm.cmd install --no-audit --no-fund
        Pop-Location
    }
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm.cmd run dev -- --host 127.0.0.1 > ..\scripts\frontend.log 2>&1" `
        -WorkingDirectory $frontend -WindowStyle Minimized

    Write-Host "[5/5] Aguardando os servicos..."
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5173/api/v1/saude/" -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep 2 }
    }
    Start-Process "http://localhost:5173"
    Write-Host ""
    Write-Host "Nexo em execucao: http://localhost:5173"
    Write-Host "Usuarios: admin.demo / servidor.demo / ti.demo  -  senha: Nexo@demo2026"
    Write-Host "Para encerrar: scripts\parar-windows.cmd"
    Write-Host "PRONTO"
}
catch {
    Write-Host "ERRO: $($_.Exception.Message)"
}
finally {
    Stop-Transcript | Out-Null
}
Start-Sleep 8
