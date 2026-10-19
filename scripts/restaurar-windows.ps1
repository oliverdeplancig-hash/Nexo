# Restaura uma copia de seguranca do Nexo no Windows.
# SUBSTITUI todo o banco e os arquivos. Antes, o estado atual e copiado automaticamente.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$log = Join-Path $PSScriptRoot "restaurar.log"
$env:PYTHONUTF8 = "1"
Start-Transcript -Path $log -Append | Out-Null
try {
    if (-not (Test-Path $py)) { throw "Ambiente Python nao encontrado. Rode scripts\iniciar-windows.cmd uma vez." }

    Write-Host "Parando o Nexo (o banco continua ligado para a restauracao)..."
    $servidor = Get-ScheduledTask -TaskName "Nexo - servidor" -ErrorAction SilentlyContinue
    if ($servidor -and $servidor.State -eq "Running") {
        # Servidor de rede (ADR-019): pede a parada ao supervisor e espera.
        Set-Content -Path (Join-Path $PSScriptRoot "servidor.parar") -Value "parar"
        for ($i = 0; $i -lt 30 -and (Test-Path (Join-Path $PSScriptRoot "servidor.parar")); $i++) { Start-Sleep 1 }
        Stop-ScheduledTask -TaskName "Nexo - servidor" -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $PSScriptRoot "servidor.parar") -ErrorAction SilentlyContinue
    }
    Get-Process daphne -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    $banco = Start-Process -FilePath $py -ArgumentList "banco_local.py", "iniciar" -WorkingDirectory $backend `
        -WindowStyle Hidden -PassThru
    $banco.WaitForExit()
    if ($banco.ExitCode -ne 0) { throw "Falha ao iniciar o PostgreSQL local." }

    Push-Location $backend
    try {
        $arquivo = $args[0]
        if (-not $arquivo) {
            $lista = & $py manage.py shell -c "from apps.manutencao import copia; [print(c['caminho']) for c in copia.listar()]"
            $copias = @($lista | Where-Object { $_ -match '\.nexobak$' })
            if ($copias.Count -eq 0) { throw "Nenhuma copia encontrada na pasta de copias. Informe o arquivo: restaurar-windows.cmd C:\caminho\arquivo.nexobak" }
            Write-Host ""
            Write-Host "Copias disponiveis (mais recente primeiro):"
            for ($i = 0; $i -lt $copias.Count; $i++) { Write-Host ("  [{0}] {1}" -f ($i + 1), (Split-Path -Leaf $copias[$i])) }
            $n = Read-Host "Numero da copia a restaurar (Enter cancela)"
            if (-not $n) { Write-Host "Cancelado."; return }
            $arquivo = $copias[[int]$n - 1]
        }
        Write-Host ""
        Write-Host "Conferindo a copia $arquivo ..."
        & $py manage.py copia_seguranca verificar $arquivo
        if ($LASTEXITCODE -ne 0) { throw "A copia nao passou na verificacao. Nada foi alterado." }

        Write-Host ""
        Write-Host "ATENCAO: o banco e os arquivos atuais do Nexo serao SUBSTITUIDOS por esta copia." -ForegroundColor Yellow
        Write-Host "O estado atual sera guardado antes, numa copia 'nexo-antes-restauracao'." -ForegroundColor Yellow
        $ok = Read-Host "Digite RESTAURAR para continuar"
        if ($ok -cne "RESTAURAR") { Write-Host "Cancelado. Nada foi alterado."; return }

        & $py manage.py copia_seguranca restaurar $arquivo --confirmar
        if ($LASTEXITCODE -ne 0) { throw "A restauracao falhou (detalhes acima). O banco foi mantido como estava." }
    } finally { Pop-Location }
    Write-Host ""
    if ($servidor) {
        Write-Host "Restauracao concluida. O servidor de rede do Nexo sera religado." -ForegroundColor Green
    } else {
        Write-Host "Restauracao concluida. Abra o Nexo com scripts\iniciar-windows.cmd" -ForegroundColor Green
    }
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
} finally {
    # Com ou sem restauracao (cancelada, falhou), o servidor de rede volta a funcionar.
    if ($servidor) { Start-ScheduledTask -TaskName "Nexo - servidor" -ErrorAction SilentlyContinue }
    Stop-Transcript | Out-Null
}
