param(
    [string]$Name = "SimpleLocalRag-v0.1.3"
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    throw "Manca l'ambiente virtuale .venv. Crealo e installa le dipendenze prima di compilare."
}

$distPath = Join-Path $PSScriptRoot "dist"
$workPath = Join-Path $PSScriptRoot "build\pyinstaller"
$specPath = Join-Path $PSScriptRoot "build\pyinstaller-spec"
$portableZip = Join-Path $PSScriptRoot "$Name-portable.zip"
$srcPath = Join-Path $PSScriptRoot "src"
$pdfDocsPath = Join-Path $srcPath "pdf_docs"

if (Test-Path $distPath) {
    Remove-Item $distPath -Recurse -Force
}

if (Test-Path $workPath) {
    Remove-Item $workPath -Recurse -Force
}

if (Test-Path $specPath) {
    Remove-Item $specPath -Recurse -Force
}

if (Test-Path $portableZip) {
    Remove-Item $portableZip -Force
}

& .\.venv\Scripts\python.exe -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name $Name `
    --distpath $distPath `
    --workpath $workPath `
    --specpath $specPath `
    --paths $srcPath `
    --add-data "$pdfDocsPath;pdf_docs" `
    --exclude-module torch `
    --exclude-module torchvision `
    --exclude-module torchaudio `
    --exclude-module tensorflow `
    --exclude-module matplotlib `
    --exclude-module pandas `
    --exclude-module scipy `
    src\main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller è fallito con codice $LASTEXITCODE"
}

try {
    Compress-Archive -Path (Join-Path $distPath $Name) -DestinationPath $portableZip -Force -ErrorAction Stop
    Write-Host "Pacchetto zip creato: $portableZip"
} catch {
    Write-Warning "Zip non creato automaticamente: $($_.Exception.Message)"
    Write-Warning "La cartella portable resta disponibile in $(Join-Path $distPath $Name)"
}

Write-Host "Build completata."
Write-Host "Cartella pronta: $(Join-Path $distPath $Name)"
if (Test-Path $portableZip) {
    Write-Host "Pacchetto condivisibile: $portableZip"
}