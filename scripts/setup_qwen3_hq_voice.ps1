$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Pack = Join-Path $env:LOCALAPPDATA "AGCN Live Voice\voice_hq"
$Bin = Join-Path $Pack "bin"
$Models = Join-Path $Pack "models"
$Vendor = Join-Path $Root ".voice-build\qwentts.cpp"

New-Item -ItemType Directory -Force -Path $Bin | Out-Null
New-Item -ItemType Directory -Force -Path $Models | Out-Null

Write-Host "[1/4] Baixando pesos Qwen3-TTS 1.7B Q8..."
$Talker = Join-Path $Models "qwen-talker-1.7b-customvoice-Q8_0.gguf"
$Codec = Join-Path $Models "qwen-tokenizer-12hz-Q8_0.gguf"

if (!(Test-Path $Talker)) {
  curl.exe -L --fail --retry 3 "https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF/resolve/main/qwen-talker-1.7b-customvoice-Q8_0.gguf?download=true" -o $Talker
}
if (!(Test-Path $Codec)) {
  curl.exe -L --fail --retry 3 "https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF/resolve/main/qwen-tokenizer-12hz-Q8_0.gguf?download=true" -o $Codec
}

Write-Host "[2/4] Preparando qwentts.cpp..."
if (!(Test-Path $Vendor)) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Vendor) | Out-Null
  git clone --recursive --depth 1 https://github.com/ServeurpersoCom/qwentts.cpp.git $Vendor
}

Write-Host "[3/4] Compilando motor local CPU universal..."
$Build = Join-Path $Vendor "build"
cmake -S $Vendor -B $Build -A x64
cmake --build $Build --config Release -j $env:NUMBER_OF_PROCESSORS

$Release = Join-Path $Build "Release"
Copy-Item (Join-Path $Release "tts-server.exe") $Bin -Force
Get-ChildItem $Release -Filter "*.dll" | Copy-Item -Destination $Bin -Force

Write-Host "[4/4] Verificando arquivos..."
if (!(Test-Path (Join-Path $Bin "tts-server.exe"))) { throw "tts-server.exe ausente" }
if (!(Test-Path $Talker)) { throw "talker GGUF ausente" }
if (!(Test-Path $Codec)) { throw "codec GGUF ausente" }

Write-Host ""
Write-Host "Voice Pack HQ instalado em:"
Write-Host $Pack
Write-Host "Perfis: Vivian (feminina) / Ryan (masculina)"
