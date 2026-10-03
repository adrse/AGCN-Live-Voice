$ErrorActionPreference = "Stop"

param(
    [string]$AdapterPath = ""
)

$expected = "19298caf2b03b90fbbc215786df16e5ea83fa005dc9a595125cac20376585ee5"
$fileName = "AGCN-Presenter-v0.1-F16.gguf"

if ([string]::IsNullOrWhiteSpace($AdapterPath)) {
    $AdapterPath = Join-Path $PSScriptRoot $fileName
}

$source = [System.IO.Path]::GetFullPath($AdapterPath)
$destDir = Join-Path $env:LOCALAPPDATA "AGCN Live Voice\models"
$dest = Join-Path $destDir $fileName

if (-not (Test-Path $source)) {
    throw "Arquivo do AGCN Presenter nao encontrado: $source"
}

$hash = (Get-FileHash -Algorithm SHA256 $source).Hash.ToLower()
if ($hash -ne $expected) {
    throw "SHA256 invalido. Esperado: $expected | Encontrado: $hash"
}

$stream = [System.IO.File]::OpenRead($source)
try {
    $bytes = New-Object byte[] 4
    [void]$stream.Read($bytes, 0, 4)
} finally {
    $stream.Dispose()
}
$magic = [System.Text.Encoding]::ASCII.GetString($bytes)
if ($magic -ne "GGUF") {
    throw "O arquivo nao possui cabecalho GGUF valido."
}

New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Copy-Item -Path $source -Destination $dest -Force

$destHash = (Get-FileHash -Algorithm SHA256 $dest).Hash.ToLower()
if ($destHash -ne $expected) {
    throw "Falha na verificacao depois da copia."
}

Write-Host ""
Write-Host "AGCN Presenter v0.1 instalado com sucesso." -ForegroundColor Green
Write-Host "Destino: $dest"
Write-Host "SHA256: $destHash"
Write-Host ""
Write-Host "Feche e abra o AGCN Live Voice para carregar o Presenter treinado."
