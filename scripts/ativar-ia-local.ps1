# Ativa a IA local (Ollama) no Nexo: liga o Ollama, baixa os modelos,
# troca o provedor no .env, refaz os embeddings e reinicia o backend.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
Start-Transcript -Path (Join-Path $PSScriptRoot "ativar-ia.log") -Force | Out-Null
$env:PYTHONUTF8 = "1"
try {
    $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $ollama) { $ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
    if (-not (Test-Path $ollama)) { throw "Ollama nao encontrado. Instale em https://ollama.com/download" }

    Write-Host "[1/5] Ligando o Ollama..."
    $ativo = $false
    try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null; $ativo = $true } catch {}
    if (-not $ativo) {
        Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 30; $i++) {
            try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null; $ativo = $true; break } catch { Start-Sleep 2 }
        }
    }
    if (-not $ativo) { throw "O Ollama nao respondeu em http://127.0.0.1:11434" }

    Write-Host "[2/5] Baixando modelos (pode levar varios minutos na primeira vez)..."
    & $ollama pull bge-m3
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar bge-m3." }
    & $ollama pull qwen2.5:7b-instruct
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar qwen2.5:7b-instruct." }

    Write-Host "[3/5] Ativando o provedor Ollama no .env..."
    Push-Location $backend
    # Janela oculta e propria: fechar este terminal nao derruba o PostgreSQL.
    $banco = Start-Process -FilePath $py -ArgumentList "banco_local.py", "iniciar" -WorkingDirectory $backend `
        -WindowStyle Hidden -PassThru
    $banco.WaitForExit()
    if ($banco.ExitCode -ne 0) { throw "Falha ao iniciar o PostgreSQL local (veja backend\.pgdata\log)." }
    Write-Host "      PostgreSQL local em execucao."
    & $py -c "import banco_local as b; b.gravar_env('NEXO_IA_PROVEDOR','ollama'); b.gravar_env('NEXO_OLLAMA_URL','http://127.0.0.1:11434')"

    Write-Host "[4/5] Refazendo a indexacao semantica com bge-m3..."
    & $py manage.py reindexar_semantica --todos
    if ($LASTEXITCODE -ne 0) { throw "Falha ao refazer a indexacao semantica." }
    Pop-Location

    Write-Host "[5/5] Reiniciando o backend..."
    Get-Process daphne -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Process -FilePath (Join-Path $backend ".venv\Scripts\daphne.exe") -ArgumentList "-b", "127.0.0.1", "-p", "8000", "nexo.asgi:application" `
        -WorkingDirectory $backend -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $PSScriptRoot "backend.log") -RedirectStandardError (Join-Path $PSScriptRoot "backend-erros.log")
    Write-Host "IA local ativa. Recarregue http://localhost:5173"
    Write-Host "PRONTO"
}
catch { Write-Host "ERRO: $($_.Exception.Message)" }
finally { Stop-Transcript | Out-Null }
Start-Sleep 8
