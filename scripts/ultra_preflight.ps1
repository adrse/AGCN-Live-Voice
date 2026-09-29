$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "========================================"
Write-Host "AGCN LIVE VOICE - ULTRA PREFLIGHT"
Write-Host "========================================"

Write-Host ""
Write-Host "[1] Git"
git status --short
git branch --show-current
git log -1 --oneline

Write-Host ""
Write-Host "[2] Python"
python --version

Write-Host ""
Write-Host "[3] Dependencias"
python -m pip install -r requirements.txt
python -m pip install -r requirements-desktop.txt
python -m pip install pytest pyinstaller

Write-Host ""
Write-Host "[4] Suite completa"
python -m pytest -q
$tests = $LASTEXITCODE

Write-Host ""
Write-Host "[5] Doctor"
python scripts\doctor.py
$doctor = $LASTEXITCODE

Write-Host ""
Write-Host "[6] Qwen"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    ollama --version
    ollama list
    python scripts\test_brain.py --provider qwen_local --proactive
    python scripts\test_brain.py --provider qwen_local --comment "quanto custa?"
} else {
    Write-Host "PENDENTE: Ollama nao instalado."
}

Write-Host ""
Write-Host "[6.5] Voice Pack HQ"
$hqPack = Join-Path $env:LOCALAPPDATA "AGCN Live Voice\voice_hq"
if (!(Test-Path (Join-Path $hqPack "bin\tts-server.exe"))) {
    Write-Host "PENDENTE: Voice Pack HQ nao instalado."
    Write-Host "Execute: powershell -ExecutionPolicy Bypass -File scripts\setup_qwen3_hq_voice.ps1"
}

Write-Host ""
Write-Host "[7] Voz HQ local e audio"
python scripts\test_voice.py --list-devices
python scripts\test_voice.py --profile female_fast --speed 1.28
python scripts\test_voice.py --profile male_fast --speed 1.28

Write-Host ""
Write-Host "[8] Build"
cmd /c scripts\build_windows.bat
$build = $LASTEXITCODE

Write-Host ""
Write-Host "========================================"
Write-Host "RESUMO"
Write-Host "========================================"
Write-Host "Tests exit:  $tests"
Write-Host "Doctor exit: $doctor"
Write-Host "Build exit:  $build"

if ($tests -eq 0 -and $build -eq 0) {
    Write-Host "CORE/BUILD OK. Voz local, Qwen, audio, VB-CABLE e TikTok devem ser validados no ambiente real."
    exit 0
}

Write-Host "Ha falha objetiva para investigar. Abra somente a camada apontada acima."
exit 1
