@echo off
cd /d "%~dp0"
echo Executando um teste unico do Monitor DOE/RN...
python monitor_doe_rn.py --once
pause
