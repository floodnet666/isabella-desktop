# Isabella Desktop Companion

[![Rust 2021](https://img.shields.io/badge/Rust-2021%20Edition-orange.svg)](https://www.rust-lang.org/)
[![WGPU](https://img.shields.io/badge/Render-WGPU%20%2F%20WGSL-blue.svg)](https://wgpu.rs/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B%20%28uv%29-yellow.svg)](https://docs.astral.sh/uv/)
[![CUDA 12.4](https://img.shields.io/badge/CUDA-12.4-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011%20Win32-lightgrey.svg)]()
[![CI Pipeline](https://github.com/floodnet666/isabella-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/floodnet666/isabella-desktop/actions/workflows/ci.yml)

> **Companion interativo de desktop para Windows 11 com inteligência multimodal 100% local, renderização fotorealista via 3D Gaussian Splatting (3DGS) em GPU, janela transparente per-pixel DWM, rastreamento dinâmico de cursor, síntese de voz neural clonada em tempo real e memória persistente multi-sessão (HippoRAG 2 + FTS5).**

---

## 📸 Visão Geral

O **Isabella Desktop** é uma assistente interativa executada inteiramente no hardware local do usuário (sem APIs pagas ou telemetria em nuvem). O sistema combina:

1. **Renderização 3DGS de Alta Fidelidade (Rust / WGPU)**: Nuvem de mais de 1 milhão de elipsóides gaussianos deformados em GPU com projeção EWA e decomposição espectral 2x2 analítica.
2. **Overlay Transparente Win32 Nativo**: Janela sem bordas integrada ao Desktop Window Manager (DWM) com transparência pré-multiplicada por pixel (`PreMultiplied`), ancoragem dinâmica na barra de tarefas e suporte a arrasto (*drag-and-drop*) a 60 FPS.
3. **Cinemática Cervical 3D e Rastreamento de Olhos**: Mapeamento contínuo da posição global do cursor do mouse para rotação tridimensional suave da cabeça (Pitch, Yaw, Roll).
4. **Ciclos Biológicos Autônomos**: Respiração torácica assimétrica em 0.23 Hz com elevação de clavícula e piscadas naturais periódicas com variação estocástica.
5. **Expressões Emocionais FACS**: 8 estados emocionais integrados (*Neutro, Alegria, Raiva, Desdém, Medo, Tristeza, Surpresa e Provocante*) com deformadores dérmicos de curvatura contínua $C^1$.
6. **Motor Neural Streaming Ultrarrápido (>140 tok/s)**: Inferência conversacional via **Colibri v2.1.0 (CUDA nativo)** com decodificação especulativa por n-gramas e TTFT $<100\text{ ms}$ no modelo `LFM3-Audio-2B` em NVMe local.
7. **Clonagem de Voz Acústica em GPU (OmniVoice Diffusion)**: Síntese de fala a 24 kHz com extração espectral FFT em 3 bandas formantes vocais a 30 Hz enviadas via UDP para o avatar 3D.
8. **Memória Persistente Multi-Hop (HippoRAG 2 + Contextual FTS5)**: Grafo hipocampal associativo em SQLite com algoritmo *Personalized PageRank* (PPR em $<15\text{ ms}$) e orquestração de contexto elástica (2k-8k tokens) garantindo 100% de retenção de preferências e coerência factual entre sessões.

---

## 🏛️ Arquitetura do Sistema

```
                      +------------------------------------------+
                      |       Microfone do Usuário (VAD)        |
                      +--------------------+---------------------+
                                           |
                                           v (Áudio PCM 16kHz)
                      +------------------------------------------+
                      |      ASR / Ingestão Fonética Rápida      |
                      |   (Conformer Causal / Faster-Whisper)    |
                      +--------------------+---------------------+
                                           |
                                           v (Texto do Usuário)
       +-----------------------------------+-----------------------------------+
       |                                                                       |
       v                                                                       v
+-------------------------------+                               +-------------------------------+
|  HippoRAG 2 (Grafo Associativo)|                               |   Contextual FTS5 BM25        |
|  - Personalized PageRank <15ms|                               |   - Citações Literais Exatas  |
|  - Conexão Fatos Multi-Hop    |                               |   - Custo Zero de VRAM        |
+---------------+---------------+                               +---------------+---------------+
                |                                                               |
                +------------------------------+--------------------------------+
                                               |
                                               v (Memórias Relevantes Injetadas)
                               +-------------------------------+
                               |  Orquestrador de Janela       |
                               |  Elástica (2k a 8k Tokens)    |
                               |  - Gating de Fronteira        |
                               +---------------+---------------+
                                               |
                                               v (Prompt Otimizado)
                               +-------------------------------+
                               | Motor Neural Colibri v2.1.0   |
                               | - CUDA Nativo (>140 tok/s)    |
                               | - NVMe Interno Local D:       |
                               +---------------+---------------+
                                               |
                    +--------------------------+--------------------------+
                    | (SSE Token Stream)                                  | (Classificação Léxica)
                    v                                                     v
       +-------------------------+                           +-------------------------+
       | OmniVoice TTS (GPU 24k) |                           | Emotion Detector (FACS) |
       | - Prompt Acústico VRAM  |                           | 8 Estados Emocionais    |
       | - Pipelining 3 Estágios |                           | Joy, Smirk, Anger, etc. |
       | (Alt: Kokoro ONNX CPU)  |                           |                         |
       +------------+------------+                           +------------+------------+
                    |                                                     |
                    v (Áudio PCM 24kHz)                                   |
       +-------------------------+                                        |
       | FFT Viseme Extraction   |                                        |
       |  (jaw, round, spread)   |                                        |
       +------------+------------+                                        |
                    |                                                     |
                    +--------------------------+--------------------------+
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
- **Placa de Vídeo**: GPU NVIDIA com suporte a CUDA 12.4 e 6 GB+ VRAM (ex: RTX 3060, 4060, 4070 ou superior).
- **Compilador Rust**: [Rust 1.80+](https://rustup.rs/) com toolchain `stable-x86_64-pc-windows-msvc`.
- **Gerenciador Python**: [uv](https://docs.astral.sh/uv/) (executável standalone).
- **Git**: Com suporte a submódulos (`git clone --recurse-submodules`).

---

## 🚀 Instalação Rápida (1 Clique)

### 1. Clonar o Repositório
```powershell
git clone --recurse-submodules https://github.com/floodnet666/isabella-desktop.git
cd isabella-desktop
```

### 2. Executar o Instalador Automático
Dê duplo clique em **`instalar.bat`** (ou execute no PowerShell):
```powershell
.\install.ps1
```
O instalador automaticamente:
1. Valida a GPU NVIDIA e o suporte a CUDA;
2. Configura o gerenciador Python `uv`;
3. Baixa os binários oficiais de inferência CUDA do `llama.cpp`;
4. Compila o núcleo Rust `isabella-core` em modo release otimizado;
5. Audita a pasta `assets/models/` para verificação de ativos.

### 3. Iniciar o Companion
- **Modo OmniVoice (Clonagem de Voz na VRAM)**:
  Dê duplo clique em **`iniciar_conversa_omnivoice.bat`** (ou `.\start_isabella_omnivoice.ps1`).
- **Modo Rápido / CPU (Kokoro ONNX)**:
  Dê duplo clique em **`iniciar_isabella.bat`** (ou `.\start_isabella.ps1`).

---

## 🧠 Ativos e Modelos Neurais

Devido ao grande volume de dados (arquivos de dezenas de megabytes a gigabytes), os pesos pesados são mantidos localmente na pasta `assets/models/`:

| Arquivo | Descrição | Localização |
| :--- | :--- | :--- |
| **`isabella_bust_4x_1m.ply`** | Nuvem 3DGS HD de 1.048.576 gaussianas com projeção UV sub-milimétrica | `assets/models/` |
| **`LFM3-Audio-2B-Q4_K_M.gguf`** | Pesos quantizados em Q4_K_M para ASR e LLM multimodal | `assets/models/` |
| **`mmproj-LFM3-Audio-2B-Q8_0.gguf`** | Projetor multimodal de áudio e visão | `assets/models/` |
| **`LFM3-Audio-2B-Q4_K_M.colibri`** | Contêiner nativo Colibri v2.1.0 para inferência >140 tok/s | `assets/models/` |
| **`isabella_omnivoice_prompt.pt`** | Prompt acústico latente para síntese de voz OmniVoice | `assets/voices/` |

> *Para instruções sobre como gerar um novo avatar a partir de fotografias via DINOv3 e FLUX.2 VAE, consulte [GEMINI.md](GEMINI.md).*

---

## ⚡ Benchmarks de Performance e Memória

Testes empíricos realizados em hardware de consumo (NVIDIA GeForce RTX 3060 Laptop 6GB, SSD NVMe interno WD_BLACK SN750):

| Métrica | Meta do Projeto | Resultado Obtido | Status |
| :--- | :--- | :--- | :--- |
| **Velocidade Média de Geração** | $\ge 120\text{ tok/s}$ | **146,53 tok/s** | ✅ **Superada (+22%)** |
| **Pico de Velocidade** | $\sim 200\text{ tok/s}$ | **193,04 tok/s** | ✅ **Alcançado** |
| **Velocidade Mínima Sustentada** | $\ge 100\text{ tok/s}$ | **127,12 tok/s** | ✅ **Superada (+27%)** |
| **Time to First Token (TTFT)** | $< 250\text{ ms}$ | **157,54 ms** | ✅ **Excelente** |
| **Preference Recall Accuracy (PRA)** | $100\%$ | **100% (1,00)** | ✅ **Retenção Perfeita** |
| **Self-Answer Consistency (SAC)** | $\ge 90\%$ | **100% (1,00)** | ✅ **Alinhamento Total** |
| **Consumo de VRAM de Pico** | $< 4.000\text{ MiB}$ | **1.792 MiB** | ✅ **29,2% da VRAM** |

---

## 🎮 Controles e Interações em Tempo Real

| Ação | Atalho / Gesto | Descrição |
| :--- | :--- | :--- |
| **Mover Personagem** | Botão Esquerdo do Mouse + Arrastar | Move Isabella livremente pela tela do Windows a 60 FPS |
| **Ajustar Escala (Zoom)** | Roda do Mouse (ou `PgUp` / `PgDn`) | Redimensiona o busto de 0.5x a 2.5x em tempo real |
| **Fechar Aplicação** | `Esc` | Encerra a janela e finaliza todos os processos em background |
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
├── .github/                  # Workflows de CI/CD (GitHub Actions)
│   └── workflows/ci.yml      # Pipeline automatizado (Rust, Python, Docs)
├── README.md                 # Guia de inicialização rápida e arquitetura
├── GEMINI.md                 # Manual de governança técnica e lições aprendidas
├── CHANGELOG.md              # Registro cirúrgico de todas as alterações
├── install.ps1               # Instalador automatizado PowerShell
├── instalar.bat              # Launcher do instalador em lote (1 clique)
├── start_isabella.ps1        # Script PowerShell mestre de inicialização paralela
├── start_isabella_omnivoice.ps1 # Launcher com OmniVoice clonado em VRAM
├── iniciar_isabella.bat      # Launcher rápido padrão
├── iniciar_conversa_omnivoice.bat # Launcher rápido com OmniVoice
│
├── isabella-core/            # Renderizador 3DGS nativo (Rust / WGPU)
│   ├── Cargo.toml            # Dependências (wgpu, winit, glam, tokio, windows)
│   └── src/
│       ├── main.rs           # Janela Win32 transparente, loop de eventos e hotkeys
│       ├── renderer.rs       # Pipeline WGPU, uniform buffers, camera e ordenação
│       ├── ply_loader.rs     # Parser PLY 3DGS, quatérnios e matriz de eixos própria
│       └── shader.wgsl       # Shader EWA 3DGS, deformadores dérmicos C1 e cinemática
│
├── scripts/                  # Pipelines Python e subsistemas de IA
│   ├── memory/               # Subsistema de memória persistente e multi-hop (2026)
│   │   ├── hipporag_engine.py   # Grafo hipocampal e Personalized PageRank (PPR)
│   │   ├── contextual_fts5.py   # Busca léxica contextualizada BM25 via SQLite FTS5
│   │   ├── elastic_window.py    # Orquestrador de contexto elástico (2k-8k tok)
│   │   ├── sleep_dreamer.py     # Consolidação desacoplada em tempo de ociosidade
│   │   └── memory_observer.py   # Logger de proveniência (Path Trace) e métricas
│   ├── benchmark_multisession_memory.py # Benchmark científico de memória multi-sessão
│   ├── voice_bridge.py       # Loop de voz contínuo (VAD + ASR + TTS Kokoro + UDP)
│   ├── voice_bridge_omnivoice.py # Loop com OmniVoice Diffusion e watchdog neural
│   └── setup_llamacpp.py     # Baixa e configura os binários CUDA do llama.cpp
│
├── tests/                    # Suíte de testes automatizados (TDD / XP)
│   └── test_memory_system.py # Testes de regressão do subsistema de memória
│
├── assets/                   # Recursos binários e modelos locais
│   ├── models/               # Nuvem de pontos 3D (.ply) e modelos neurais
│   ├── voices/               # Modelos de voz Kokoro ONNX e prompts OmniVoice
│   ├── references/           # Imagens de referência de alta resolução
│   └── renders/              # Snapshots de auditoria visual e benchmarks
│
└── tools/                    # Ferramentas locais e executáveis auxiliares
    └── llama-cpp/            # Binários CUDA e DLLs do llama-server
```

---

## 🛡️ Governança e Regras de Engenharia

O projeto segue padrões estritos de qualidade documentados detalhadamente em [GEMINI.md](GEMINI.md):
- **Deformações $C^1$ Contínuas**: Nunca utilizar cortes rígidos booleanos no shader que possam rasgar a nuvem de gaussianas.
- **Transparência Pré-multiplicada**: Renderização estritamente em `PREMULTIPLIED_ALPHA_BLENDING` para erradicar o pontilhismo escuro ("pimenta").
- **Matriz de Carga Própria**: Preservação de quiralidade ($\det = +1$) na conversão de eixos de coordenadas ($x = raw\_z, y = -raw\_y, z = raw\_x$).
- **Gestão de Dependências Python**: Uso exclusivo do executável standalone `uv`.

---

## 📄 Licença

Distribuído sob licença de código aberto MIT. Consulte `LICENSE` para maiores detalhes.
