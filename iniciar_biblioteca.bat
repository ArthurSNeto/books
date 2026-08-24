@echo off
title Biblioteca Digital & Leitor Web
color 0B
chcp 65001 >nul

cd /d "%~dp0"

echo =======================================================
echo         BIBLIOTECA DIGITAL PRO - LEITOR WEB
echo =======================================================
echo.
echo  Iniciando servidor local na porta 8000...
echo.

:: Abrir navegador automaticamente apos 2 segundos em segundo plano
start "" powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"

:: Iniciar servidor FastAPI com Uvicorn
python run_server.py

pause
