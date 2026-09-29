@echo off
setlocal
cd /d %~dp0\..

echo [1/4] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
python -m pip install pyinstaller
if errorlevel 1 goto :fail

echo [2/4] Testando imports...
set PYTHONPATH=.
python -c "import core.runtime, core.presenter_v3, core.tts_providers, core.audio_output, desktop.main_window; print('imports ok')"
if errorlevel 1 goto :fail

echo [3/4] Compilando...
pyinstaller --noconfirm --clean --windowed --name "AGCN Live Voice" --paths . --collect-all TikTokLive --collect-all keyring desktop\main.py
if errorlevel 1 goto :fail

echo [4/4] Validando arquivo...
if not exist "dist\AGCN Live Voice\AGCN Live Voice.exe" (
  echo Executavel nao encontrado.
  goto :fail
)

echo.
echo Build concluido:
echo dist\AGCN Live Voice\AGCN Live Voice.exe
exit /b 0

:fail
echo.
echo BUILD FALHOU.
exit /b 1
