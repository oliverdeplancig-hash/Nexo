# Faz uma copia de seguranca do Nexo (banco + arquivos dos documentos).
# Usado pela tarefa agendada (agendar-copia-windows.cmd) e por duplo clique em copia-seguranca.cmd.
# Registro em scripts\copia-seguranca.log
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$log = Join-Path $PSScriptRoot "copia-seguranca.log"
$env:PYTHONUTF8 = "1"
Start-Transcript -Path $log -Append | Out-Null
$codigo = 0
$bancoJaAtivo = Test-Path (Join-Path $backend ".pgdata\postmaster.pid")
try {
    Write-Host ("=== " + (Get-Date -Format "dd/MM/yyyy HH:mm") + " - copia de seguranca do Nexo ===")
    if (-not (Test-Path $py)) { throw "Ambiente Python nao encontrado. Rode scripts\iniciar-windows.cmd uma vez." }
    $banco = Start-Process -FilePath $py -ArgumentList "banco_local.py", "iniciar" -WorkingDirectory $backend `
        -WindowStyle Hidden -PassThru
    $banco.WaitForExit()
    if ($banco.ExitCode -ne 0) { throw "Falha ao iniciar o PostgreSQL local." }
    Push-Location $backend
    try {
        & $py manage.py copia_seguranca criar
        if ($LASTEXITCODE -ne 0) { throw "A copia de seguranca falhou (detalhes acima)." }
    } finally { Pop-Location }
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
    $codigo = 1
} finally {
    # Se o PostgreSQL so foi ligado para a copia, desliga de novo.
    if (-not $bancoJaAtivo) { & $py (Join-Path $backend "banco_local.py") parar | Out-Null }
    Stop-Transcript | Out-Null
}
exit $codigo
