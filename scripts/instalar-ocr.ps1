# Instala o OCR (Tesseract + idioma portugues) para o Nexo no Windows. Ver ADR-009.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
Start-Transcript -Path (Join-Path $PSScriptRoot "instalar-ocr.log") -Force | Out-Null
try {
    $exe = $null
    foreach ($c in @("$env:ProgramFiles\Tesseract-OCR\tesseract.exe", "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe")) {
        if (Test-Path $c) { $exe = $c }
    }
    if (-not $exe) {
        Write-Host "[1/3] Instalando o Tesseract (o Windows pode pedir permissao de administrador)..."
        & winget install --id UB-Mannheim.TesseractOCR -e --silent --accept-package-agreements --accept-source-agreements
        foreach ($c in @("$env:ProgramFiles\Tesseract-OCR\tesseract.exe", "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe")) {
            if (Test-Path $c) { $exe = $c }
        }
        if (-not $exe) { throw "Tesseract nao foi instalado. Instale manualmente: https://github.com/UB-Mannheim/tesseract/wiki" }
    } else {
        Write-Host "[1/3] Tesseract ja instalado: $exe"
    }

    Write-Host "[2/3] Baixando o idioma portugues..."
    $tessdata = Join-Path $backend ".tessdata"
    New-Item -ItemType Directory -Force -Path $tessdata | Out-Null
    foreach ($idioma in @("por", "osd")) {
        $destino = Join-Path $tessdata "$idioma.traineddata"
        if (-not (Test-Path $destino)) {
            Invoke-WebRequest -UseBasicParsing "https://github.com/tesseract-ocr/tessdata/raw/main/$idioma.traineddata" -OutFile $destino
        }
    }

    Write-Host "[3/3] Configurando o Nexo..."
    Push-Location $backend
    & $py -m pip install --disable-pip-version-check -q -r requirements-local.txt
    & $py -c "import banco_local as b; b.gravar_env('NEXO_OCR_MOTOR','tesseract'); b.gravar_env('NEXO_TESSERACT_CMD', r'$exe'); b.gravar_env('NEXO_TESSDATA_DIR', r'$tessdata')"
    & $py -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd=r'$exe'; print('Idiomas:', pytesseract.get_languages(config=r'--tessdata-dir \"$tessdata\"'))"
    Pop-Location
    Write-Host "OCR instalado. Reinicie o Nexo (scripts\iniciar-windows.cmd)."
    Write-Host "PRONTO"
}
catch { Write-Host "ERRO: $($_.Exception.Message)" }
finally { Stop-Transcript | Out-Null }
Start-Sleep 8
