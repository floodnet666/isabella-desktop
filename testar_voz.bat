@echo off
chcp 65001 >nul
title ISABELLA - LFM3-OMNI-2B (SEM QUANTIZACAO + IN-MEMORY TTS + UNCENSORED)
cd /d "D:\isabella-desktop"
echo =======================================================
echo   ISABELLA - LFM3-OMNI-2B (SEM QUANTIZACAO)
echo   PIPELINE IN-MEMORY /tts + STREAMING + UNCENSORED
echo =======================================================

:: 1. Definir modelo (Prioridade: F16 -> Abliter8 BF16)
set "MODEL_FILE=E:\modelos_ollama\LFM3-Omni-2B-F16.gguf"
if not exist "%MODEL_FILE%" (
    set "MODEL_FILE=E:\modelos_ollama\LFM3-Omni-2B-Abliter8-BF16.gguf"
)

:: 2. Verificar se o servidor multimodal llama-server esta ativo na porta 8080
curl.exe -s http://127.0.0.1:8080/health | findstr /i "ok" >nul
if errorlevel 1 (
    echo [1/2] Iniciando llama-server com %MODEL_FILE% na GPU...
    start "" /b "D:\isabella-desktop\tools\llama-cpp\llama-server.exe" -m "%MODEL_FILE%" --mmproj "E:\modelos_ollama\mmproj-LFM3-Omni-2B-F16.gguf" -ngl 99 -fa auto -np 2 -c 4096 --jinja --reasoning off --no-reasoning-preserve --port 8080
    echo Aguardando carregamento dos pesos na VRAM...
    timeout /t 8 /nobreak >nul
) else (
    echo [1/2] Servidor LFM3-Omni-2B ativo na porta 8080.
)

echo [2/2] Iniciando loop de conversacao com sintese In-Memory /tts e streaming...
uv run --with sounddevice --with soundfile --with requests python scripts/voice_test.py
if errorlevel 1 (
    echo.
    echo [ERRO] O script de voz encerrou com erro.
)
pause
