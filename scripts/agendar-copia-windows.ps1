# Agenda a copia de seguranca diaria do Nexo no Agendador de Tarefas do Windows (usuario atual).
# Se o computador estiver desligado no horario, a copia roda assim que ele for ligado.
param([string]$Horario = "12:30")
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$envArq = Join-Path $backend ".env"
$script = Join-Path $PSScriptRoot "copia-seguranca.ps1"

function Gravar-Env($chave, $valor) {
    $linhas = @()
    if (Test-Path $envArq) { $linhas = @(Get-Content $envArq -Encoding UTF8 | Where-Object { $_ -notmatch "^\s*$chave\s*=" }) }
    $linhas += "$chave=$valor"
    [System.IO.File]::WriteAllLines($envArq, [string[]]$linhas)
}

try {
    if (-not (Test-Path $envArq)) { throw "Rode scripts\iniciar-windows.cmd uma vez antes de agendar." }

    if (-not (Select-String -Path $envArq -Pattern "^NEXO_BACKUP_SENHA=." -Quiet)) {
        Write-Host "As copias contem os documentos da instituicao e devem ser cifradas."
        Write-Host "Escolha uma senha para as copias. ANOTE-A EM LOCAL SEGURO, FORA DESTE COMPUTADOR:"
        Write-Host "sem ela nenhuma copia pode ser restaurada."
        $s1 = Read-Host "Senha das copias (minimo 12 caracteres)" -AsSecureString
        $s2 = Read-Host "Repita a senha" -AsSecureString
        $p1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1))
        $p2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2))
        if ($p1 -ne $p2) { throw "As senhas nao conferem." }
        if ($p1.Length -lt 12) { throw "Use pelo menos 12 caracteres." }
        if ($p1 -match '[#"]' -or $p1 -match '^\s|\s$') { throw "Evite os caracteres # e aspas e espacos nas pontas." }
        Gravar-Env "NEXO_BACKUP_SENHA" $p1
        Write-Host "Senha gravada em backend\.env."
    }

    $acao = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
    $opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName "Nexo - copia de seguranca" -Action $acao -Trigger $gatilho -Settings $opcoes `
        -Description "Copia diaria do banco e dos arquivos do Nexo (scripts\copia-seguranca.ps1)" -Force | Out-Null
    Write-Host ""
    Write-Host "Copia diaria agendada para as $Horario." -ForegroundColor Green
    Write-Host "Fazendo a primeira copia agora para testar..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $script
    if ($LASTEXITCODE -ne 0) { throw "A primeira copia falhou. Veja scripts\copia-seguranca.log" }
    Write-Host "Tudo certo. As copias ficam em backend\copias (ou em NEXO_BACKUP_DIR, se definido no .env)."
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
}
