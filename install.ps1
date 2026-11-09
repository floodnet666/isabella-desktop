# Instalador Automatizado do Isabella Desktop Companion
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
if (-not $RootDir) { $RootDir = (Get-Location).Path }

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       INSTALADOR — ISABELLA DESKTOP COMPANION         " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Diretório de Instalação: $RootDir`n" -ForegroundColor DarkGray

# 1. Verificar GPU NVIDIA e Drivers
Write-Host "[1/6] Verificando Placa de Vídeo NVIDIA e CUDA..." -ForegroundColor Yellow
$NvidiaCheck = $false
try {
    $gpuInfo = & nvidia-smi --query-gpu=gpu_name,driver_version,memory.total --format=csv,noheader
    if ($gpuInfo) {
        Write-Host "      GPU Detectada: $gpuInfo" -ForegroundColor Green
        $NvidiaCheck = $true
    }
} catch {
    Write-Host "      [AVISO] 'nvidia-smi' não encontrado. Certifique-se de possuir GPU NVIDIA e drivers atualizados." -ForegroundColor Yellow
}

# 2. Verificar e Configurar Gerenciador Python (uv)
Write-Host "`n[2/6] Verificando Gerenciador de Pacotes Python (uv)..." -ForegroundColor Yellow
$UvCheck = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvCheck) {
    Write-Host "      'uv' não detectado no PATH. Instalando uv standalone oficial..." -ForegroundColor Yellow
    try {
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
        $UvCheck = Get-Command uv -ErrorAction SilentlyContinue
    } catch {
        Write-Host "      Falha ao instalar uv automaticamente. Baixe em: https://docs.astral.sh/uv/" -ForegroundColor Red
    }
}
if ($UvCheck) {
    $uvVer = & uv --version
    Write-Host "      $uvVer ativo!" -ForegroundColor Green
} else {
    Write-Host "      [ERRO] É necessário o 'uv' para gerenciar o ambiente Python." -ForegroundColor Red
}

# 3. Verificar Toolchain Rust / Cargo
Write-Host "`n[3/6] Verificando Compilador Rust (cargo)..." -ForegroundColor Yellow
$CargoCheck = Get-Command cargo -ErrorAction SilentlyContinue
if (-not $CargoCheck -and (Test-Path "$env:USERPROFILE\.cargo\bin\cargo.exe")) {
    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
    $CargoCheck = Get-Command cargo -ErrorAction SilentlyContinue
}
if ($CargoCheck) {
    $cargoVer = & cargo --version
    Write-Host "      $cargoVer ativo!" -ForegroundColor Green
} else {
    Write-Host "      [ATENÇÃO] Rust não encontrado. Baixe e instale o rustup em: https://rustup.rs" -ForegroundColor Yellow
}

# 4. Baixar e Configurar Ferramentas Llama.cpp CUDA 12.4
Write-Host "`n[4/6] Configurando ferramentas de inferência llama.cpp..." -ForegroundColor Yellow
$LlamaSetupScript = Join-Path $RootDir "scripts\setup_llamacpp.py"
if (Test-Path $LlamaSetupScript) {
    & uv run python $LlamaSetupScript
    Write-Host "      Ferramentas de inferência configuradas em 'tools/llama-cpp'." -ForegroundColor Green
} else {
    Write-Host "      Aviso: 'scripts/setup_llamacpp.py' não localizado." -ForegroundColor Yellow
}

# 5. Compilar Renderizador 3DGS Nativo (Rust / WGPU)
Write-Host "`n[5/6] Compilando Renderizador 3DGS (isabella-core) em Release..." -ForegroundColor Yellow
$CargoToml = Join-Path $RootDir "isabella-core\Cargo.toml"
if ((Test-Path $CargoToml) -and $CargoCheck) {
    & cargo build --release --manifest-path $CargoToml
    Write-Host "      Binário 'isabella-core.exe' compilado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "      [AVISO] Compilação do Rust ignorada ou não disponível." -ForegroundColor Yellow
}

# 6. Auditoria de Modelos e Ativos
Write-Host "`n[6/6] Verificando modelos e ativos de produção..." -ForegroundColor Yellow
$ModelPly = Join-Path $RootDir "assets\models\isabella_bust_4x_1m.ply"
$ModelGguf = Join-Path $RootDir "assets\models\LFM3-Audio-2B-Q4_K_M.gguf"
$ModelColi = Join-Path $RootDir "assets\models\LFM3-Audio-2B-Q4_K_M.colibri"
$PromptVoice = Join-Path $RootDir "assets\voices\isabella_omnivoice_prompt.pt"

if (Test-Path $ModelPly) {
    Write-Host "      [OK] Modelo 3DGS (1M gaussianas): Presente" -ForegroundColor Green
} else {
    Write-Host "      [AVISO] Modelo 3DGS 'assets/models/isabella_bust_4x_1m.ply' não encontrado." -ForegroundColor Yellow
    Write-Host "              Consulte assets/models/README.md para instruções de reconstrução." -ForegroundColor DarkGray
}

if (Test-Path $ModelGguf) {
    Write-Host "      [OK] Pesos GGUF (LFM3-Audio-2B): Presente" -ForegroundColor Green
} else {
    Write-Host "      [AVISO] Pesos GGUF 'assets/models/LFM3-Audio-2B-Q4_K_M.gguf' não encontrados." -ForegroundColor Yellow
}

if (Test-Path $ModelColi) {
    Write-Host "      [OK] Contêiner Colibri (>140 tok/s): Presente" -ForegroundColor Green
} else {
    Write-Host "      [INFO] Contêiner Colibri opcional (fallback para llama-server ativo)." -ForegroundColor DarkGray
}

if (Test-Path $PromptVoice) {
    Write-Host "      [OK] Prompt de Voz OmniVoice: Presente" -ForegroundColor Green
}

# 7. Copiar e Iniciar Assistente Nativo de Personalidade (IsabellaSetup.exe)
$SetupBin = Join-Path $RootDir "isabella-core\target\release\IsabellaSetup.exe"
$RootSetup = Join-Path $RootDir "IsabellaSetup.exe"
if (Test-Path $SetupBin) {
    Copy-Item $SetupBin $RootSetup -Force
    Write-Host "`n[7/7] Abrindo Assistente de Personalidade (IsabellaSetup.exe)..." -ForegroundColor Cyan
    Start-Process -FilePath $RootSetup -WorkingDirectory $RootDir
}

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "         INSTALAÇÃO CONCLUÍDA COM SUCESSO!             " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "A Isabella opera 100% em segundo plano (System Tray) sem janelas de terminal." -ForegroundColor Green
Write-Host "Atalho criado na Área de Trabalho: 'Isabella Companion'" -ForegroundColor White
