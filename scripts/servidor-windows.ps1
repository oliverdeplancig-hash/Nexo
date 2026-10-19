# Servidor de rede do Nexo no Windows (ADR-019). Iniciado pela tarefa agendada "Nexo - servidor" na
# inicializacao do computador. Liga o PostgreSQL local, o Ollama (se configurado), o processador da fila e o
# servidor web (HTTPS na porta 443 e HTTP na 80, que so redireciona). Se algum processo cair, ele e religado.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$envArq = Join-Path $backend ".env"
$log = Join-Path $PSScriptRoot "servidor.log"
$env:PYTHONUTF8 = "1"

function Escrever($texto) {
    $linha = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $texto
    Add-Content -Path $log -Value $linha -Encoding UTF8
    Write-Host $linha  # visivel quando aberto numa janela (modo de teste)
}

function Valor-Env($chave, $padrao) {
    $linha = Get-Content $envArq -Encoding UTF8 | Where-Object { $_ -match "^\s*$chave\s*=" } | Select-Object -Last 1
    if ($linha) { return ($linha -split "=", 2)[1].Trim() }
    return $padrao
}

function Iniciar-Banco {
    $banco = Start-Process -FilePath $py -ArgumentList "banco_local.py", "iniciar" -WorkingDirectory $backend `
        -WindowStyle Hidden -PassThru
    $banco.WaitForExit()
    if ($banco.ExitCode -ne 0) { throw "Falha ao iniciar o PostgreSQL local (veja backend\.pgdata\log)." }
}

function Iniciar-Ollama {
    if ((Valor-Env "NEXO_IA_PROVEDOR" "ollama") -ne "ollama") { return }
    try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null; return } catch {}
    $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $ollama) { $ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
    if (-not (Test-Path $ollama)) { Escrever "Ollama nao encontrado: o assistente respondera so com regras e trechos."; return }
    # Atende varias perguntas ao mesmo tempo (ADR-020). Ajuste conforme a memoria do computador.
    $env:OLLAMA_NUM_PARALLEL = Valor-Env "NEXO_IA_CONCORRENCIA" "2"
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    Escrever "Ollama iniciado."
}

if (-not (Test-Path $py)) { Escrever "Ambiente Python nao encontrado. Rode scripts\instalar-servidor-windows.cmd."; exit 1 }
$portaHttps = Valor-Env "NEXO_PORTA_HTTPS" "443"
$portaHttp = Valor-Env "NEXO_PORTA_HTTP" "80"

# Caminhos relativos a pasta backend: o "C:" de um caminho absoluto confundiria a sintaxe do endereco do daphne.
$web = @("-m", "daphne",
    "-e", "ssl:${portaHttps}:privateKey=.certificados/nexo.key:certKey=.certificados/nexo.crt",
    "-e", "tcp:${portaHttp}",
    "nexo.asgi:application")
$fila = @("manage.py", "processar_fila", "--continuo")

Escrever "Iniciando o servidor do Nexo (HTTPS $portaHttps, HTTP $portaHttp)."
try { Iniciar-Banco } catch { Escrever "ERRO: $_"; exit 1 }
Iniciar-Ollama

$processos = @{}
$quedas = @{ web = 0; fila = 0 }
while ($true) {
    foreach ($nome in @("web", "fila")) {
        $p = $processos[$nome]
        if ($p -and -not $p.HasExited) { continue }
        if ($p) {
            $quedas[$nome]++
            Escrever "Processo '$nome' encerrou (codigo $($p.ExitCode)). Religando."
            # Recomeco em sequencia rapida costuma ser o banco desligado: liga de novo antes.
            try { Iniciar-Banco } catch { Escrever "ERRO: $_" }
            Start-Sleep -Seconds ([Math]::Min(60, 5 * $quedas[$nome]))
        }
        $argumentos = if ($nome -eq "web") { $web } else { $fila }
        $processos[$nome] = Start-Process -FilePath $py -ArgumentList $argumentos -WorkingDirectory $backend `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $PSScriptRoot "servidor-$nome.log") `
            -RedirectStandardError (Join-Path $PSScriptRoot "servidor-$nome-erros.log")
        Escrever "Processo '$nome' iniciado (PID $($processos[$nome].Id))."
    }
    if (Test-Path (Join-Path $PSScriptRoot "servidor.parar")) {
        Escrever "Pedido de parada recebido."
        foreach ($p in $processos.Values) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
        Remove-Item (Join-Path $PSScriptRoot "servidor.parar") -Force
        & $py (Join-Path $backend "banco_local.py") parar | Out-Null
        Escrever "Servidor parado."
        exit 0
    }
    Start-Sleep -Seconds 5
}
