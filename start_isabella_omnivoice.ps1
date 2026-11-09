# Launcher para Isabella Desktop Companion com Clonagem de Voz OmniVoice
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
if (-not $RootDir) { $RootDir = (Get-Location).Path }

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       INICIANDO ISABELLA DESKTOP - OMNIVOICE          " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Raiz do projeto: $RootDir" -ForegroundColor DarkGray

# 1. Localizar binário do Renderizador 3DGS (Rust)
$CoreExe = Join-Path $RootDir "isabella-core\target\release\isabella-core.exe"
if (-not (Test-Path $CoreExe)) {
    $CoreExe = Join-Path $RootDir "isabella-core\target\debug\isabella-core.exe"
}
if (-not (Test-Path $CoreExe)) {
    Write-Host "[Compilando núcleo Rust em modo release...]" -ForegroundColor Yellow
    Set-Location (Join-Path $RootDir "isabella-core")
    & "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release
    $CoreExe = Join-Path $RootDir "isabella-core\target\release\isabella-core.exe"
}

# 2. Configurar e Iniciar Motor Neural Colibri de Alta Performance (CUDA >140 tok/s)
$ColiPort = 8000
$ColiHealth = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:$ColiPort/v1/models" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($res.data) { $ColiHealth = $true }
} catch { $ColiHealth = $false }

$ColiProcess = $null
$ColiModel = Join-Path $RootDir "assets\models\LFM3-Audio-2B-Q4_K_M.colibri"
$ColiCmd = if (Test-Path "$env:LOCALAPPDATA\colibri\runtime\colibri-v2.1.0\coli.cmd") {
    "$env:LOCALAPPDATA\colibri\runtime\colibri-v2.1.0\coli.cmd"
} else {
    (Get-Command coli.cmd -ErrorAction SilentlyContinue)?.Source
}

if (-not $ColiHealth -and $ColiCmd -and (Test-Path $ColiCmd) -and (Test-Path $ColiModel)) {
    Write-Host "[1/4] Iniciando Colibri CUDA v2.1.0 na porta $ColiPort (Metodologia Ótima)..." -ForegroundColor Yellow
    $env:COLI_CUDA = "1"
    $env:COLI_LOOKUP = "1"
    $env:COLI_SPEC_GATE = "1"
    $env:COLI_CUDA_CHAIN_ROWS = "4096"
    $env:Q36_KV = "f16"
    $env:Q36_KV_RING = "1"
    $env:KVSAVE = "0"
    
    $ColiArgs = @("serve", "--model", $ColiModel, "--port", "$ColiPort", "--ctx", "8192", "--policy", "experimental-fast", "--no-think")
    $ColiProcess = Start-Process -FilePath $ColiCmd -ArgumentList $ColiArgs -PassThru -WindowStyle Minimized
    
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $check = Invoke-RestMethod -Uri "http://127.0.0.1:$ColiPort/v1/models" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($check.data) {
                Write-Host "      Colibri neural pronto na porta $ColiPort (>140 tok/s)!" -ForegroundColor Green
                break
            }
        } catch {}
    }
} elseif ($ColiHealth) {
    Write-Host "[1/4] Motor Colibri já ativo na porta $ColiPort." -ForegroundColor Green
} else {
    Write-Host "[1/4] Colibri não configurado; operando em modo fallback nativo." -ForegroundColor DarkGray
}

# 3. Verificar se o servidor multimodal LFM3-Omni-2B (ASR) está ativo na porta 8080
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
    Write-Host "[2/4] Iniciando llama-server para ASR Multimodal..." -ForegroundColor Yellow
    
    $ModelPath = Join-Path $RootDir "assets\models\LFM3-Audio-2B-Q4_K_M.gguf"
    $MmprojPath = Join-Path $RootDir "assets\models\mmproj-LFM3-Audio-2B-Q8_0.gguf"
    $ServerExe = Join-Path $RootDir "tools\llama-cpp\llama-server.exe"
    
    if ((Test-Path $ServerExe) -and (Test-Path $ModelPath) -and (Test-Path $MmprojPath)) {
        Write-Host "      Modelo: $ModelPath" -ForegroundColor DarkCyan
        $ServerArgs = @(
            "-m", $ModelPath,
            "--mmproj", $MmprojPath,
            "-ngl", "99",
            "-fa", "auto",
            "-np", "1",
            "-c", "2048",
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
                    Write-Host "      Servidor ASR pronto!" -ForegroundColor Green
                    break
                }
            } catch {}
        }
    } else {
        Write-Host "      Aviso: llama-server ou modelos não encontrados. Execute 'instalar.bat'." -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/4] Servidor multimodal ASR já ativo na porta 8080." -ForegroundColor Green
}

# 4. Iniciar Overlay Transparente 3DGS (Rust)
Write-Host "[3/4] Iniciando Janela 3DGS transparente (Rust)..." -ForegroundColor Green
$OverlayProcess = Start-Process -FilePath $CoreExe -PassThru

Start-Sleep -Seconds 2

# 5. Iniciar Voice Bridge com OmniVoice na VRAM
Write-Host "[4/4] Iniciando Voice Bridge (OmniVoice Cloned Voice + Visemas 3D)..." -ForegroundColor Green
Set-Location $RootDir
$VoiceScript = Join-Path $RootDir "scripts\voice_bridge_omnivoice.py"
& uv run python $VoiceScript

# Encerrar processos ao fechar o console
if ($OverlayProcess -and -not $OverlayProcess.HasExited) {
    Stop-Process -Id $OverlayProcess.Id -Force -ErrorAction SilentlyContinue
}
if ($ColiProcess -and -not $ColiProcess.HasExited) {
    Stop-Process -Id $ColiProcess.Id -Force -ErrorAction SilentlyContinue
}
if ($ServerProcess -and -not $ServerProcess.HasExited) {
    Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
}
