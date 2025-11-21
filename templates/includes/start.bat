@echo off
REM === Start RocrailVolt ===
cd /d "C:\Users\andre\OneDrive\Documents\RocrailVolt"

REM Ativar o venv
call .venv\Scripts\activate.bat

REM Iniciar o servidor Flask
python run.py

REM Manter a janela aberta se o programa terminar
pause
