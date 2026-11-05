@echo off
chcp 65001 >nul
title Isabella Desktop Companion
cd /d "D:\isabella-desktop"
echo =======================================================
echo          ISABELLA DESKTOP COMPANION
echo =======================================================
echo Iniciando overlay 3DGS e escuta de voz multimodal...
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\isabella-desktop\start_isabella.ps1"
if errorlevel 1 (
    echo.
    echo [ERRO] A sessao encerrou com erro.
)
pause
