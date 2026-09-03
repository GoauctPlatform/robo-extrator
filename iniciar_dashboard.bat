@echo off
title Parcel Auction Pipeline - Dashboard
cd /d "%~dp0"

echo ======================================================
echo    Parcel Auction Pipeline - Dashboard
echo ======================================================
echo.

:: 1. Verifica se o dashboard ja esta rodando na porta 5050
netstat -ano | findstr ":5050" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [INFO] O Dashboard ja esta ativo na porta 5050.
    echo [INFO] Abrindo navegador em http://localhost:5050...
    start "" "http://localhost:5050"
    exit /b 0
)

echo [INFO] Iniciando o servidor do Dashboard...
echo [INFO] O navegador abrirá automaticamente em http://localhost:5050
echo [INFO] Pressione CTRL+C para encerrar o servidor.
echo.

python dashboard_server.py
if errorlevel 1 (
    echo.
    echo [AVISO] O servidor foi finalizado com erro.
    pause
)
