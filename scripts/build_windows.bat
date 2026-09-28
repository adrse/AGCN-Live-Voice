@echo off
setlocal
cd /d %~dp0\..
python -m pip install -r requirements-desktop.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "AGCN Live Voice" --paths . desktop\main.py

echo.
echo Build concluido em dist\AGCN Live Voice\
pause
