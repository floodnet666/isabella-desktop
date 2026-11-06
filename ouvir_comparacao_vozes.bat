@echo off
title Isabella Desktop - Comparacao de Vozes
cd /d "D:\isabella-desktop"
uv run --with soundfile --with sounddevice python "scripts\play_comparison.py"
pause
