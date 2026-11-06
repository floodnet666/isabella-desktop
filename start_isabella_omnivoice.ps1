# Launcher para Isabella Desktop Companion com Clonagem de Voz OmniVoice
$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       INICIANDO ISABELLA DESKTOP - OMNIVOICE          " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Localizar binário do Renderizador 3DGS (Rust)
$CoreExe = "D:\isabella-desktop\isabella-core\target\release\isabella-core.exe"
if (-not (Test-Path $CoreExe)) {
    $CoreExe = "D:\isabella-desktop\isabella-core\target\debug\isabella-core.exe"
}

# 2. Verificar se o servidor multimodal LFM3-Omni-2B esta ativo na porta 8080
$HealthCheck = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($res.status -eq "ok") {
        $HealthCheck = $true
    }
} catch {
    $HealthCheck = $false
}

$ServerProcess = $null
if (-not $HealthCheck) {
    Write-Host "[1/3] Iniciando llama-server com LFM3-Omni-2B na GPU..." -ForegroundColor Yellow
    
    $ModelPath = "E:\modelos_ollama\LFM3-Omni-2B-F16.gguf"
    if (-not (Test-Path $ModelPath)) {
        $ModelPath = "E:\modelos_ollama\LFM3-Omni-2B-Abliter8-BF16.gguf"
    }
    $MmprojPath = "E:\modelos_ollama\mmproj-LFM3-Omni-2B-F16.gguf"
    
    Write-Host "      Modelo: $ModelPath" -ForegroundColor DarkCyan
    $ServerExe = "D:\isabella-desktop\tools\llama-cpp\llama-server.exe"
    $ServerArgs = @(
        "-m", $ModelPath,
        "--mmproj", $MmprojPath,
        "-ngl", "99",
        "-fa", "auto",
        "-np", "2",
        "-c", "4096",
        "--jinja",
        "--reasoning", "off",
        "--no-reasoning-preserve",
        "--port", "8080"
    )
    $ServerProcess = Start-Process -FilePath $ServerExe -ArgumentList $ServerArgs -PassThru -WindowStyle Minimized
    
    Write-Host "      Aguardando carregamento dos pesos na VRAM..." -ForegroundColor Yellow
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $check = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($check.status -eq "ok") {
                Write-Host "      Servidor neural pronto!" -ForegroundColor Green
                break
            }
        } catch {}
    }
} else {
    Write-Host "[1/3] Servidor neural LFM3-Omni-2B ja ativo na porta 8080." -ForegroundColor Green
}

# 3. Iniciar Overlay Transparente 3DGS (Rust)
Write-Host "[2/3] Iniciando Janela 3DGS transparente (Rust)..." -ForegroundColor Green
$OverlayProcess = Start-Process -FilePath $CoreExe -PassThru

Start-Sleep -Seconds 2

# 4. Iniciar Voice Bridge com OmniVoice na VRAM
Write-Host "[3/3] Iniciando Voice Bridge (OmniVoice Cloned Voice + Visemas 3D)..." -ForegroundColor Green
Set-Location "D:\isabella-desktop"
& "D:\isabella-desktop\.venv\Scripts\python.exe" "D:\isabella-desktop\scripts\voice_bridge_omnivoice.py"

# Encerrar overlay ao fechar o console
if ($OverlayProcess -and -not $OverlayProcess.HasExited) {
    Stop-Process -Id $OverlayProcess.Id -Force -ErrorAction SilentlyContinue
}
