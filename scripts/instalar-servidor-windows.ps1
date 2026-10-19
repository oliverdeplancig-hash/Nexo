# Instala o Nexo como servidor de rede num computador Windows da instituicao (ADR-019).
# Rode como Administrador: scripts\instalar-servidor-windows.cmd
# Pode ser repetido: atualiza dependencias, telas e banco, sem apagar dados.
# Modo de teste (scripts\instalar-servidor-windows.cmd teste): portas 8443/8080, sem inicio automatico, sem
# mexer na energia do computador, com documentos de demonstracao. Para ensaiar a rede antes da instituicao.
param([switch]$Teste)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$envArq = Join-Path $backend ".env"
$log = Join-Path $PSScriptRoot "instalar-servidor.log"
$env:PYTHONUTF8 = "1"
Start-Transcript -Path $log -Append | Out-Null
$transcrevendo = $true

function Gravar-Env($chave, $valor) {
    $linhas = @()
    if (Test-Path $envArq) { $linhas = @(Get-Content $envArq -Encoding UTF8 | Where-Object { $_ -notmatch "^\s*$chave\s*=" }) }
    $linhas += "$chave=$valor"
    [System.IO.File]::WriteAllLines($envArq, [string[]]$linhas)
}
function Tem-Env($chave) { (Test-Path $envArq) -and (Select-String -Path $envArq -Pattern "^\s*$chave\s*=." -Quiet) }
function Rodar($descricao, [scriptblock]$bloco) {
    & $bloco
    if ($LASTEXITCODE -ne 0) { throw "Falha: $descricao" }
}

try {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw "Abra o instalador como Administrador (botao direito > Executar como administrador)." }

    Write-Host "[1/8] Ambiente Python..."
    if (-not (Test-Path $py)) {
        & py -3.12 -m venv (Join-Path $backend ".venv")
        if ($LASTEXITCODE -ne 0) { & python -m venv (Join-Path $backend ".venv") }
        if (-not (Test-Path $py)) { throw "Instale o Python 3.12 (python.org) e rode de novo." }
    }
    Rodar "dependencias Python" { & $py -m pip install --disable-pip-version-check -q -r (Join-Path $backend "requirements-local.txt") }

    Write-Host "[2/8] Telas (frontend)..."
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        Write-Host "      Instalando Node.js LTS..."
        & winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements --silent
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Instale o Node.js LTS (nodejs.org) e rode de novo." }
    }
    Push-Location $frontend
    try {
        Rodar "instalar dependencias do frontend" { & npm.cmd ci --no-audit --no-fund }
        Rodar "gerar as telas" { & npm.cmd run build }
    } finally { Pop-Location }

    Write-Host "[3/8] Configuracao de producao (backend\.env)..."
    $maquina = $env:COMPUTERNAME.ToLower()
    $fqdn = ([System.Net.Dns]::GetHostEntry("localhost").HostName).ToLower()
    $ips = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch "^(127\.|169\.254\.)" } | ForEach-Object { $_.IPAddress })
    Write-Host "      Este computador: $maquina  IPs: $($ips -join ', ')"
    $extra = Read-Host "      Nome DNS definido pela TI para o Nexo (ex.: nexo.unidade.local; Enter se nao houver)"
    $nomes = @($maquina, $fqdn, "localhost") + @($ips) + @($(if ($extra) { $extra.Trim().ToLower() }))
    $nomes = @($nomes | Where-Object { $_ } | Select-Object -Unique)
    if ($Teste) {
        if (-not (Tem-Env "NEXO_PORTA_HTTPS")) { Gravar-Env "NEXO_PORTA_HTTPS" "8443" }
        if (-not (Tem-Env "NEXO_PORTA_HTTP")) { Gravar-Env "NEXO_PORTA_HTTP" "8080" }
    }
    $portaHttps = if (Tem-Env "NEXO_PORTA_HTTPS") { ((Select-String -Path $envArq -Pattern "^\s*NEXO_PORTA_HTTPS\s*=(.*)").Matches[0].Groups[1].Value.Trim()) } else { "443" }
    $sufixo = if ($portaHttps -eq "443") { "" } else { ":$portaHttps" }

    if (-not (Tem-Env "NEXO_SECRET_KEY") -or (Select-String -Path $envArq -Pattern "^\s*NEXO_DEBUG\s*=\s*true" -Quiet)) {
        $bytes = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        Gravar-Env "NEXO_SECRET_KEY" ([Convert]::ToBase64String($bytes) -replace '[+/=]', 'x')
    }
    Gravar-Env "NEXO_DEBUG" "false"
    Gravar-Env "NEXO_ALLOWED_HOSTS" ($nomes -join ",")
    Gravar-Env "NEXO_CSRF_TRUSTED_ORIGINS" (($nomes | ForEach-Object { "https://$_$sufixo" }) -join ",")
    Gravar-Env "NEXO_COOKIE_SEGURO" "true"
    Gravar-Env "NEXO_SERVIR_FRONTEND" "true"
    Gravar-Env "NEXO_REDIRECIONAR_HTTPS" "true"
    Gravar-Env "NEXO_PROCESSAR_IMEDIATAMENTE" "false"
    $principal = if ($extra) { $extra.Trim().ToLower() } else { $maquina }
    if (-not (Tem-Env "NEXO_URL_PUBLICA")) { Gravar-Env "NEXO_URL_PUBLICA" "https://$principal$sufixo" }
    if (-not (Tem-Env "NEXO_IA_PROVEDOR")) { Gravar-Env "NEXO_IA_PROVEDOR" "ollama" }
    if ($Teste -and -not (Get-Command ollama -ErrorAction SilentlyContinue) -and
        -not (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"))) {
        # Sem IA local o teste de rede segue com respostas por regra e por trechos (provedor de teste).
        Gravar-Env "NEXO_IA_PROVEDOR" "falso"
        Write-Host "      Ollama nao encontrado: o teste usa respostas por regra e por trechos, sem IA." -ForegroundColor Yellow
    }
    # Capacidade (ADR-020): conexoes do banco compartilhadas e fila da IA. Ajuste em docs\architecture\capacidade.md.
    if (-not (Tem-Env "NEXO_DB_POOL_MAXIMO")) { Gravar-Env "NEXO_DB_POOL_MAXIMO" "40" }
    if (-not (Tem-Env "NEXO_IA_CONCORRENCIA")) { Gravar-Env "NEXO_IA_CONCORRENCIA" "2" }

    Write-Host "[4/8] Banco de dados..."
    $banco = Start-Process -FilePath $py -ArgumentList "banco_local.py", "iniciar" -WorkingDirectory $backend -WindowStyle Hidden -PassThru
    $banco.WaitForExit()
    if ($banco.ExitCode -ne 0) { throw "Falha ao iniciar o PostgreSQL local (veja backend\.pgdata\log)." }
    Push-Location $backend
    try {
        Rodar "migracoes" { & $py manage.py migrate --noinput }
        Rodar "arquivos estaticos" { & $py manage.py collectstatic --noinput -v 0 }
        Rodar "dados iniciais" { & $py manage.py inicializar_nexo }
        if ($Teste) {
            # Documentos ficticios para ter o que perguntar; as contas .demo sao desativadas logo abaixo.
            Rodar "documentos de demonstracao" { & $py manage.py carregar_demo --forcar }
        }
        Rodar "verificacao de producao" { & $py manage.py preparar_producao }

        Write-Host "[5/8] Certificado HTTPS..."
        $argsCert = @("manage.py", "gerar_certificado")
        if ($extra) { $argsCert += @("--nome", $extra.Trim().ToLower()) }
        Rodar "certificado" { & $py @argsCert }
    } finally { Pop-Location }

    Write-Host "[6/8] Firewall e energia..."
    $portaHttp = if (Tem-Env "NEXO_PORTA_HTTP") { ((Select-String -Path $envArq -Pattern "^\s*NEXO_PORTA_HTTP\s*=(.*)").Matches[0].Groups[1].Value.Trim()) } else { "80" }
    $regra = if ($Teste) { "Nexo teste (HTTPS e HTTP)" } else { "Nexo (HTTPS e HTTP)" }
    Get-NetFirewallRule -DisplayName $regra -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $regra -Direction Inbound -Protocol TCP `
        -LocalPort @($portaHttps, $portaHttp) -Action Allow -Profile Domain, Private | Out-Null
    $perfis = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -eq "Public" })
    if ($perfis) {
        Write-Host "      ATENCAO: a rede '$($perfis[0].Name)' esta como Publica; outros aparelhos nao vao alcancar o Nexo." -ForegroundColor Yellow
        Write-Host "      Em Configuracoes > Rede, marque-a como Privada (so em rede confiavel)." -ForegroundColor Yellow
    }
    if (-not $Teste) {
        # Servidor nao pode dormir: os usuarios perderiam o acesso.
        & powercfg /change standby-timeout-ac 0
        & powercfg /change hibernate-timeout-ac 0
    }

    if ($Teste) {
        Write-Host "[7/8] Modo de teste: sem inicio automatico. Abrindo o servidor numa janela propria..."
        Get-Process daphne -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$(Join-Path $PSScriptRoot 'servidor-windows.ps1')`""
    } else {
        Write-Host "[7/8] Inicio automatico com o Windows..."
        Write-Host "      As tarefas rodam com a sua conta, mesmo sem ninguem conectado. Informe a sua senha do Windows."
        $cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Senha do Windows para as tarefas do Nexo"
        $senhaTexto = $cred.GetNetworkCredential().Password
        $acao = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $PSScriptRoot 'servidor-windows.ps1')`""
        $opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
        Register-ScheduledTask -TaskName "Nexo - servidor" -Action $acao -Trigger (New-ScheduledTaskTrigger -AtStartup) `
            -Settings $opcoes -User $cred.UserName -Password $senhaTexto -RunLevel Highest `
            -Description "Servidor de rede do Nexo (scripts\servidor-windows.ps1)" -Force | Out-Null
        $tarefaCopia = Get-ScheduledTask -TaskName "Nexo - copia de seguranca" -ErrorAction SilentlyContinue
        if ($tarefaCopia) {
            Set-ScheduledTask -TaskName "Nexo - copia de seguranca" -User $cred.UserName -Password $senhaTexto | Out-Null
        } else {
            Write-Host "      Agende a copia de seguranca diaria: scripts\agendar-copia-windows.cmd" -ForegroundColor Yellow
        }
        $senhaTexto = $null
        Get-Process daphne -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-ScheduledTask -TaskName "Nexo - servidor"
    }

    # A senha temporaria do administrador nao pode ficar gravada no registro da instalacao.
    Stop-Transcript | Out-Null
    $transcrevendo = $false
    Write-Host "[8/8] Administrador..."
    Push-Location $backend
    try {
        $existe = & $py manage.py shell -c "from apps.contas.models import Usuario; print(Usuario.objects.filter(is_active=True, perfis__codigo='administrador').exclude(username__endswith='.demo').exists())"
        if ($existe -notmatch "True") {
            $usuario = Read-Host "      Usuario do primeiro administrador (ex.: nome.sobrenome)"
            $nome = Read-Host "      Nome completo"
            $email = Read-Host "      E-mail institucional (Enter se nao houver)"
            Rodar "criar administrador" { & $py manage.py criar_administrador --usuario $usuario --nome $nome --email $email }
        } else {
            Write-Host "      Ja existe administrador."
        }
    } finally { Pop-Location }

    $endereco = "https://$principal$sufixo"
    Write-Host ""
    Write-Host "Nexo instalado como servidor de rede." -ForegroundColor Green
    Write-Host "Endereco para os usuarios: $endereco"
    if ($ips) { Write-Host "Tambem por IP: $(($ips | ForEach-Object { "https://$_$sufixo" }) -join '  ')" }
    Write-Host ""
    Write-Host "Certificado: backend\.certificados\nexo.cer. Peca a TI para distribui-lo aos computadores da rede"
    Write-Host "(politica de grupo, 'Autoridades de Certificacao Raiz Confiaveis'); sem isso o navegador mostra um aviso."
    Write-Host "Ou substitua nexo.key e nexo.crt pelo certificado emitido pela TI e reinicie a tarefa 'Nexo - servidor'."
    Write-Host "Registro do servidor: scripts\servidor.log. Para parar: scripts\parar-servidor-windows.cmd"
    if ($Teste) {
        Write-Host ""
        Write-Host "MODO DE TESTE. Para desfazer: scripts\desinstalar-servidor-windows.cmd" -ForegroundColor Yellow
        Write-Host "Outro aparelho na mesma rede (celular no Wi-Fi, outro PC ou o Windows Sandbox) deve abrir o endereco acima."
    }
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
} finally {
    if ($transcrevendo) { Stop-Transcript | Out-Null }
}
