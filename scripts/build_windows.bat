@echo off
setlocal
cd /d %~dp0\..

set "HQPACK=%LOCALAPPDATA%\AGCN Live Voice\voice_hq"

echo [1/7] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
python -m pip install -r requirements-voice-hq.txt
python -m pip install pyinstaller
if errorlevel 1 goto :fail

echo [2/7] Preparando fallback neural local...
if not exist "models\kokoro" mkdir "models\kokoro"
if not exist "models\kokoro\kokoro-v1.0.onnx" (
  curl.exe -L --fail --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx" -o "models\kokoro\kokoro-v1.0.onnx"
  if errorlevel 1 goto :fail
)
if not exist "models\kokoro\voices-v1.0.bin" (
  curl.exe -L --fail --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin" -o "models\kokoro\voices-v1.0.bin"
  if errorlevel 1 goto :fail
)

echo [3/7] Verificando Voice Pack HQ...
if exist "%HQPACK%\bin\tts-server.exe" (
  echo Voice Pack HQ encontrado: %HQPACK%
) else (
  echo AVISO: Voice Pack HQ nao encontrado.
  echo O build sera funcional com Kokoro fallback.
  echo Para qualidade maxima execute:
  echo powershell -ExecutionPolicy Bypass -File scripts\setup_qwen3_hq_voice.ps1
)

echo [4/7] Testando imports...
set PYTHONPATH=.
python -c "import core.runtime, core.presenter_v3, core.tts_providers, core.local_qwen3_tts, core.local_kokoro_tts, core.audio_output, desktop.main_window; print('imports ok')"
if errorlevel 1 goto :fail

echo [5/7] Testando fallback Dora/Alex...
python scripts\smoke_kokoro.py
if errorlevel 1 goto :fail

echo [6/7] Compilando...
pyinstaller --noconfirm --clean --windowed --name "AGCN Live Voice" --paths . --add-data "models\kokoro;models\kokoro" --collect-all TikTokLive --collect-all keyring --collect-all kokoro_onnx --collect-all espeakng_loader --collect-all phonemizer --collect-all onnxruntime --collect-all imageio_ffmpeg desktop\main.py
if errorlevel 1 goto :fail

if exist "%HQPACK%\bin\tts-server.exe" (
  echo Copiando Voice Pack HQ para o programa...
  if not exist "dist\AGCN Live Voice\_internal\voice_hq" mkdir "dist\AGCN Live Voice\_internal\voice_hq"
  xcopy "%HQPACK%\*" "dist\AGCN Live Voice\_internal\voice_hq\" /E /I /Y >nul
  if errorlevel 1 goto :fail
)

echo [7/7] Validando arquivos...
if not exist "dist\AGCN Live Voice\AGCN Live Voice.exe" goto :fail
if not exist "dist\AGCN Live Voice\_internal\models\kokoro\kokoro-v1.0.onnx" goto :fail
if not exist "dist\AGCN Live Voice\_internal\models\kokoro\voices-v1.0.bin" goto :fail

echo.
echo Build concluido:
echo dist\AGCN Live Voice\AGCN Live Voice.exe
if exist "dist\AGCN Live Voice\_internal\voice_hq\bin\tts-server.exe" (
  echo Voz principal: Qwen3-TTS 1.7B HQ - Vivian/Ryan
) else (
  echo Voz ativa: Kokoro fallback - Dora/Alex
)
exit /b 0

:fail
echo.
echo BUILD FALHOU.
exit /b 1
