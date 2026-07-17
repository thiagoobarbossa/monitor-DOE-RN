@echo off
cd /d "%~dp0"
echo Instalando dependencias do Monitor DOE/RN...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pause
