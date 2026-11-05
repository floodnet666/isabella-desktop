@echo off
title ISABELLA - TESTE LIQUID AI LFM3-AUDIO-2B
cd /d "D:\isabella-desktop"
echo =======================================================
echo     TESTE LIQUID AI LFM3-AUDIO-2B (ZERO WHISPER)
echo =======================================================

:: 1. Verificar se llama-server esta rodando com LFM3 na porta 8080
curl.exe -s http://127.0.0.1:8080/health | findstr /i "ok" >nul
if errorlevel 1 (
    echo [1/2] Iniciando llama-server com LFM3-Audio-2B na GPU...
    start "" /b "D:\isabella-desktop\tools\llama-cpp\llama-server.exe" -m "E:\modelos_ollama\LFM3-Audio-2B-Q4_K_M.gguf" --mmproj "E:\modelos_ollama\mmproj-LFM3-Audio-2B-Q8_0.gguf" -ngl 99 -c 4096 --port 8080
    timeout /t 6 /nobreak >nul
) else (
    echo [1/2] Servidor LFM3-Audio-2B ja esta ativo na porta 8080.
)

echo [2/2] Executando pipeline completo (Ingestao de Audio 16kHz + Sintese LiquidCodec 24kHz)...
uv run --with sounddevice --with soundfile --with scipy python scripts/test_lfm3_pipeline.py
pause
