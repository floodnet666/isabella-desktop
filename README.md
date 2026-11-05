# Isabella Desktop Companion

[![Rust 2021](https://img.shields.io/badge/Rust-2021%20Edition-orange.svg)](https://www.rust-lang.org/)
[![WGPU](https://img.shields.io/badge/Render-WGPU%20%2F%20WGSL-blue.svg)](https://wgpu.rs/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B%20%28uv%29-yellow.svg)](https://docs.astral.sh/uv/)
[![CUDA 12.4](https://img.shields.io/badge/CUDA-12.4-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011%20Win32-lightgrey.svg)]()

> **Companion interativo de desktop para Windows 11 com inteligência multimodal 100% local, renderização fotorealista via 3D Gaussian Splatting (3DGS) em GPU, janela transparente per-pixel DWM, rastreamento dinâmico de cursor e sincronia labial em tempo real.**

---

## 📸 Visão Geral

O **Isabella Desktop** é uma assistente interativa executada inteiramente no hardware local do usuário (sem APIs pagas ou telemetria em nuvem). O sistema combina:

1. **Renderização 3DGS de Alta Fidelidade (Rust / WGPU)**: Nuvem de mais de 1 milhão de elipsóides gaussianos deformados em GPU com projeção EWA e decomposição espectral 2x2 analítica.
2. **Overlay Transparente Win32 Nativo**: Janela sem bordas integrada ao Desktop Window Manager (DWM) com transparência pré-multiplicada por pixel, ancoragem dinâmica na barra de tarefas e suporte a arrasto (*drag-and-drop*) a 60 FPS.
3. **Cinemática Cervical 3D e Rastreamento de Olhos**: Mapeamento contínuo da posição global do cursor do mouse para rotação tridimensional suave da cabeça (Pitch, Yaw, Roll).
4. **Ciclos Biológicos Autônomos**: Respiração torácica assimétrica em 0.23 Hz com elevação de clavícula e piscadas naturais periódicas com variação estocástica.
5. **Expressões Emocionais FACS**: 8 estados emocionais integrados (*Neutro, Alegria, Raiva, Desdém, Medo, Tristeza, Surpresa e Provocante*) com deformadores dérmicos de curvatura contínua $C^1$.
6. **Pipeline de Voz Multimodal de Baixa Latência**: Ingestão de áudio via microfone (VAD calibrado), reconhecimento fonético (ASR), inteligência conversacional sem censura e síntese de voz neural na GPU com sincronia labial precisa via UDP.

---

## 🏛️ Arquitetura do Sistema

```
                      +------------------------------------------+
                      |       Microfone do Usuário (VAD)        |
                      +--------------------+---------------------+
                                           |
                                           v
                      +------------------------------------------+
                      |       llama-server (LFM3-Omni-2B)        |
                      |    - ASR Multimodal Nativo (16 kHz)      |
                      |    - LLM Conversacional Streaming        |
                      |    - In-Memory TTS LiquidCodec (24 kHz)  |
                      +--------------------+---------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v (Áudio PCM 24kHz)                           v (Sentimento / FACS)
       +-------------------------+                   +-------------------------+
       |   FFT Viseme Extraction |                   |  Emotion State (F1-F8)  |
       |  (jaw, round, spread)   |                   | Joy, Anger, Smirk, etc. |
       +------------+------------+                   +------------+------------+
                    |                                             |
                    +----------------------+----------------------+
                                           |
                                           v (UDP JSON 127.0.0.1:9888)
                             +---------------------------+
                             |  isabella-core.exe (Rust) |
                             +-------------+-------------+
                                           |
                +--------------------------+--------------------------+
                |                                                     |
                v                                                     v
   +-------------------------+                           +-------------------------+
   |   WGPU Vertex Shader    |                           |  Win32 Window Overlay   |
   |   - EWA 3DGS Projection |                           |  - DWM PreMult Alpha    |
   |   - C1 FACS Deformers   |                           |  - Taskbar Docking      |
   |   - Cervical Kinematics |                           |  - Drag-and-Drop & Zoom |
   +-------------------------+                           +-------------------------+
```

---

## ⚙️ Pré-requisitos do Sistema

- **Sistema Operacional**: Windows 11 (64-bit).
- **Placa de Vídeo**: GPU NVIDIA com suporte a CUDA 12.4 e 8 GB+ VRAM (ex: RTX 3060, 4060, 4070 ou superior).
- **Compilador Rust**: [Rust 1.80+](https://rustup.rs/) com toolchain `stable-x86_64-pc-windows-msvc`.
- **Gerenciador Python**: [uv](https://docs.astral.sh/uv/) (executável standalone).
- **Git**: Com suporte a submódulos (`git clone --recurse-submodules`).

---

## 🚀 Instalação e Inicialização Rápida

### 1. Clonar o Repositório (com Submódulos)
```powershell
git clone --recurse-submodules https://github.com/usuario/isabella-desktop.git
cd isabella-desktop
```

### 2. Baixar as Ferramentas de Inferência Llama.cpp
O projeto inclui um script automatizado que baixa a compilação oficial de `llama.cpp` otimizada para CUDA 12.4:
```powershell
uv run python scripts/setup_llamacpp.py
```

### 3. Configurar Modelos e Pesos
- **Modelo 3DGS (`.ply`)**: Coloque o arquivo de gaussianas em `assets/models/isabella_bust_4x_1m.ply` (consulte `assets/models/README.md` para instruções de reconstrução via `idol-sdk`).
- **Modelo Multimodal (`.gguf`)**: Certifique-se de que o modelo `LFM3-Omni-2B-F16.gguf` e o projetor `mmproj-LFM3-Omni-2B-F16.gguf` estejam no caminho configurado no script (padrão: `E:\modelos_ollama\` ou `assets/models/llm_multimodal/`).

### 4. Compilar o Renderizador em Rust
```powershell
cd isabella-core
cargo build --release
cd ..
```

### 5. Iniciar o Companion
Execute o script de inicialização mestre no PowerShell:
```powershell
.\start_isabella.ps1
```
Ou dê duplo clique no atalho `iniciar_isabella.bat`.

---

## 🎮 Controles e Interações em Runtime

| Ação | Atalho / Gesto | Descrição |
|---|---|---|
| **Mover Personagem** | Botão Esquerdo do Mouse + Arrastar | Move Isabella livremente pela tela do Windows |
| **Ajustar Escala (Zoom)** | Roda do Mouse (ou `PgUp` / `PgDn`) | Redimensiona o busto em tempo real |
| **Fechar Aplicação** | `Esc` | Encerra a janela de renderização e os serviços de background |
| **Expressão Neutra** | `F1` | Postura serena de repouso |
| **Alegria (Joy)** | `F2` | Sorriso suave, sobrancelhas relaxadas e inclinação empática |
| **Raiva (Anger)** | `F3` | Sobrancelhas franzidas, postura frontal firme |
| **Desdém (Disgust)** | `F4` | Nariz levemente retraído e cabeça desviada em perfil |
| **Medo / Alerta** | `F5` | Olhos arregalados e cabeça retraída |
| **Tristeza / Dengo** | `F6` | Olhar caído e inclinação carinhosa |
| **Surpresa** | `F7` | Boca entreaberta e sobrancelhas elevadas em arco |
| **Smirk / Sedutora** | `F8` | Sorriso assimétrico malicioso e rotação cervical provocante |

---

## 📁 Estrutura do Diretório

```
isabella-desktop/
├── README.md                 # Este guia de inicialização e arquitetura
├── GEMINI.md                 # Manual de governança técnica e lições aprendidas
├── CHANGELOG.md              # Registro cronológico cirúrgico de alterações
├── start_isabella.ps1        # Script PowerShell mestre de inicialização paralela
├── iniciar_isabella.bat      # Launcher rápido em lote (.bat)
│
├── isabella-core/            # Renderizador 3DGS nativo (Rust / WGPU)
│   ├── Cargo.toml            # Dependências (wgpu, winit, glam, tokio, windows)
│   └── src/
│       ├── main.rs           # Janela Win32 transparente, loop de eventos e hotkeys
│       ├── renderer.rs       # Pipeline WGPU, uniform buffers, camera e ordenação
│       ├── ply_loader.rs     # Parser PLY 3DGS, quatérnios e matriz de eixos própria
│       └── shader.wgsl       # Shader EWA 3DGS, deformadores dérmicos C1 e cinemática
│
├── scripts/                  # Pipelines Python auxiliares
│   ├── voice_bridge.py       # Loop de voz multimodal contínuo (VAD + ASR + TTS + UDP)
│   ├── voice_test.py         # Testador interativo de conversação e streaming
│   ├── setup_llamacpp.py     # Baixa e configura os binários CUDA do llama.cpp
│   ├── apply_uv_texture_3dgs.py # Microdensificação e alinhamento de textura UV
│   └── run_local_idol.py     # Reconstrução neural de modelo 3D (DINOv3 + FLUX.2 VAE)
│
├── assets/                   # Recursos binários
│   ├── models/               # Nuvem de pontos 3D (.ply) e modelos neurais
│   ├── voices/               # Modelos e vozes neurais Kokoro ONNX
│   ├── references/           # Imagens de referência de alta resolução
│   ├── renders/              # Snapshots de auditoria visual e testes de expressões
│   └── audio/                # Diretório de buffers temporários e validação sonora
│
├── tools/                    # Ferramentas locais e executáveis auxiliares
│   └── llama-cpp/            # Binários CUDA e DLLs do llama-server
│
└── backups/                  # Arquivo histórico de backups (ignorado pelo Git)
```

---

## 🛡️ Governança e Regras de Engenharia

O projeto segue padrões estritos de qualidade documentados detalhadamente em [GEMINI.md](GEMINI.md):
- **Deformações $C^1$ Contínuas**: Nunca utilizar cortes rígidos booleanos no shader que possam rasgar a nuvem de gaussianas.
- **Transparência Pré-multiplicada**: Renderização estritamente em `PREMULTIPLIED_ALPHA_BLENDING` para erradicar o pontilhismo escuro ("pimenta").
- **Matriz de Carga Própria**: Preservação de quiralidade ($\det = +1$) na conversão de eixos de coordenadas.

---

## 📄 Licença

Distribuído sob licença de código aberto MIT. Consulte `LICENSE` para maiores detalhes.
