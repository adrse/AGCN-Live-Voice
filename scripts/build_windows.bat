@echo off
setlocal
cd /d %~dp0\..

echo [1/6] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
python -m pip install pyinstaller
if errorlevel 1 goto :fail

echo [2/6] Preparando vozes neurais locais...
if not exist "models\kokoro" mkdir "models\kokoro"
if not exist "models\kokoro\kokoro-v1.0.onnx" (
  curl.exe -L --fail --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx" -o "models\kokoro\kokoro-v1.0.onnx"
  if errorlevel 1 goto :fail
)
if not exist "models\kokoro\voices-v1.0.bin" (
  curl.exe -L --fail --retry 3 "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin" -o "models\kokoro\voices-v1.0.bin"
  if errorlevel 1 goto :fail
)

echo [3/6] Testando imports...
set PYTHONPATH=.
python -c "import core.runtime, core.presenter_v3, core.tts_providers, core.local_kokoro_tts, core.audio_output, desktop.main_window; print('imports ok')"
if errorlevel 1 goto :fail

echo [4/6] Testando Dora e Alex offline...
python scripts\smoke_kokoro.py
if errorlevel 1 goto :fail

echo [5/6] Compilando...
pyinstaller --noconfirm --clean --windowed --name "AGCN Live Voice" --paths . --add-data "models\kokoro;models\kokoro" --collect-all TikTokLive --collect-all keyring --collect-all kokoro_onnx --collect-all espeakng_loader --collect-all phonemizer --collect-all onnxruntime desktop\main.py
if errorlevel 1 goto :fail

echo [6/6] Validando arquivos...
if not exist "dist\AGCN Live Voice\AGCN Live Voice.exe" goto :fail
if not exist "dist\AGCN Live Voice\_internal\models\kokoro\kokoro-v1.0.onnx" goto :fail
if not exist "dist\AGCN Live Voice\_internal\models\kokoro\voices-v1.0.bin" goto :fail

echo.
echo Build concluido:
echo dist\AGCN Live Voice\AGCN Live Voice.exe
echo Vozes locais: Dora (feminina) + Alex (masculina)
exit /b 0

:fail
echo.
echo BUILD FALHOU.
exit /b 1
