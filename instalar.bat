@echo off
title Instalador - Isabella Desktop Companion
cd /d "%~dp0"
echo =======================================================
echo       INICIANDO INSTALADOR ISABELLA DESKTOP
echo =======================================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Ocorreu uma falha durante a instalacao.
) else (
    echo.
    echo [SUCESSO] Instalacao finalizada!
)
pause
