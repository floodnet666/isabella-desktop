# Isabella Desktop — Manual Técnico e Governança do Projeto (GEMINI.md)

Este documento é a fonte de verdade absoluta para o projeto **Isabella Desktop**. Qualquer agente, desenvolvedor ou nova sessão que assuma o projeto deve ler e seguir este manual para manter a consistência arquitetural, a qualidade visual e a integridade de engenharia.

---

## 1. Visão Geral e Arquitetura do Sistema

O **Isabella Desktop** é um companion interativo de área de trabalho para Windows 11, executado **100% localmente**, baseado em **3D Gaussian Splatting (3DGS)** fotorealista com deformação em GPU (WGPU/WGSL), transparência Win32 sem bordas, rastreamento global do cursor do mouse, escuta contínua de voz (Whisper STT), síntese de fala com voz feminina ultranatural (Kokoro TTS), inteligência conversacional sem censura (Ollama Gemma 4 Uncensored) e expressões emocionais sincronizadas (FACS + Cinemática Cervical 3D).

```
                      +------------------------------------------+
                      |       Microfone do Usuário (VAD)        |
                      +--------------------+---------------------+
                                           |
                                           v
                      +------------------------------------------+
                      |     Faster-Whisper (STT CPU int8)        |
                      +--------------------+---------------------+
                                           |
                                           v
                      +------------------------------------------+
                      | Ollama LLM (Gemma-4-E2B Uncensored Q8_0) |
                      +--------------------+---------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v (Texto)                                     v (Classificação)
       +-------------------------+                   +-------------------------+
       |   Kokoro TTS (ONNX)     |                   | Emotion Detector (FACS) |
       |  Voz: pf_dora (PT-BR)   |                   | Joy, Anger, Smirk, etc. |
       +------------+------------+                   +------------+------------+
                    |                                             |
                    v (Áudio PCM 24kHz)                           |
       +-------------------------+                                |
       | FFT Viseme Extraction   |                                |
       |  (jaw, round, spread)   |                                |
       +------------+------------+                                |
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
   |   - C1 FACS Deformers   |                           |  - Docking Taskbar      |
   |   - Cervical Kinematics |                           |  - Drag-and-Drop & Zoom |
   +-------------------------+                           +-------------------------+
```

---

## 2. Fase Atual do Projeto

**Status Atual**: **Fase 2 Concluída com Sucesso / Fase 3 Pronta para Início**.

### O Que Já Está Implementado e Validado:
1. **Modelo 3DGS HD de 1.048.576 Gaussianas** (`isabella_bust_4x_1m.ply`):
   - Reconstrução 3D de 360° via `idol-sdk` (DINOv3 ViT-H/16+ e FLUX.2 VAE).
   - Micro-densificação em espaço UV (arXiv:2601.12770) com calibração por Powell em 9 parâmetros, garantindo fidelidade sub-milimétrica nos olhos, sobrancelhas e colar de ouro.
2. **Motor de Renderização em Rust (WGPU)**:
   - Projeção elíptica EWA completa (Zwicker / Kerbl et al.) com decomposição espectral 2x2 analítica.
   - Blendagem `PREMULTIPLIED_ALPHA_BLENDING` para eliminação de pontilhismo.
   - Ordenação em GPU/CPU determinística e estável.
   - Color grading fílmico com espaço perceptual sRGB.
3. **Janela e Overlay Win32**:
   - Transparência nativa DWM per-pixel (`with_transparent(true)` + `CompositeAlphaMode::PreMultiplied`), tornando o fundo 100% transparente com fusão sub-pixel sobre o desktop do Windows sem artefatos ou caixas pretas.
   - Posicionamento dinâmico ancorado na barra de tarefas do Windows via `GetMonitorInfoW` (`rcWork`).
   - Rastreamento global do cursor com `GetCursorPos` Win32 mapeado para rotação cervical natural.
   - Suporte completo a arrasto (drag-and-drop a 60 FPS) e redimensionamento dinâmico (roda do mouse e atalhos de teclado).
4. **Ciclos Orgânicos Idle e Fala**:
   - Respiração torácica assimétrica em 0.23 Hz com elevação de clavícula.
   - Piscadas de olhos naturais periódicas com variação estocástica e piscadas duplas.
   - Sincronia labial (visemas) acionada por análise espectral FFT em 3 bandas formantes vocais a 30 Hz via UDP.
5. **Sistema Completo de Expressões Emocionais (FACS)**:
   - 8 estados emocionais integrados: **Neutro**, **Alegria (Joy)**, **Smirk / Provocante**, **Surpresa / Curiosa**, **Tristeza / Dengo**, **Medo / Chocada**, **Raiva / Tensa**, **Nojo / Desdém**.
   - Deformadores em envelope contínuo $C^1$ (sem quebra de malha) aliados à cinemática cervical 3D (Roll, Pitch, Yaw).
   - Teclas de atalho `F1`–`F8` e injeção automática pelo Voice Bridge via análise léxica das respostas do LLM.

---

## 3. Lições Aprendidas e Erros Críticos (Post-Mortem)

Qualquer alteração futura no código deve respeitar rigorosamente os seguintes aprendizados empíricos:

### ⚠️ Erro Crítico 1: Cortes Rígidos no Shader (`if y > threshold`)
- **Falha**: Uma tentativa de mover as sobrancelhas com `if (pos.y > 0.305)` cortou as 9.574 gaussianas da sobrancelha: 3.116 estavam abaixo de 0.305 e ficaram imóveis, enquanto 6.458 subiram. Isso **rasgou as sobrancelhas no meio**, gerando uma barra preta horizontal grotesca sobre os olhos em medo e surpresa.
- **Regra Absoluta**: Em 3D Gaussian Splatting, **NUNCA use cortes booleanos rígidos em coordenadas espaciais**. Todo deformador dérmico deve usar envelopes contínuos de classe $C^1$ (`smoothstep` ou gaussianas) que avaliem para **exatamente 0.0 nas fronteiras**, garantindo que as partículas se movam em conjunto como uma malha biológica unificada.

### ⚠️ Erro Crítico 2: Macrodeformações Excessivas (Uncanny Valley)
- **Falha**: Deslocamentos de 15mm a 26mm em sobrancelhas e queixo puxaram a nuvem 3DGS além do seu limite plástico de captura única, gerando deformações de desenho animado bizarras e deformadas.
- **Regra Absoluta**: Modelos 3DGS fotogramétricos capturados de pose única toleram **microexpressões de 1.5mm a 3.5mm**. A expressividade dramática real em humanos decorre primariamente da **postura cervical da cabeça (Roll, Pitch, Yaw)**. Como a rotação rígida não deforma a geometria interna, ela possui **zero artefatos e preserva 100% do fotorealismo**.

### ⚠️ Erro Crítico 3: Alpha Squaring e Pontilhismo de "Pimenta"
- **Falha**: O uso de `ALPHA_BLENDING` convencional em partículas gaussianas com cor multiplicada por alfa resultava em atenuação quadrática `color * alpha^2`, criando manchas escuras na pele.
- **Regra Absoluta**: Utilizar SEMPRE `PREMULTIPLIED_ALPHA_BLENDING` em shaders de Gaussian Splatting com WGPU.

### ⚠️ Erro Crítico 4: Matriz de Carga com Espelhamento (Det = -1)
- **Falha**: Trocas incorretas de eixos como `x = -raw_z` invertiam a quiralidade da modelo (determinante negativo), fazendo a modelo parecer espelhada e sumir na visão de perfil lateral.
- **Regra Absoluta**: A matriz de conversão própria ($\det = +1$) é:
  $$x = raw\_z, \quad y = -raw\_y, \quad z = raw\_x$$
  com quatérnion de rotação $q = [0.0, \frac{\sqrt{2}}{2}, 0.0, \frac{\sqrt{2}}{2}]$.

### ⚠️ Erro Crítico 5: Gerenciador de Pacotes Python
- **Regra Absoluta**: Utilizar estritamente o `uv` (`uv run`, `uv add`) como executável standalone externo, nunca instalando pacotes de forma ad-hoc ou dependendo de ambientes corrompidos.

---

## 4. Workflows Generalizados Passo a Passo

### Workflow A: Processar uma Nova Imagem de Referência para Criar um Novo Avatar 3DGS
Caso deseje criar um novo avatar a partir de outra fotografia ou personagem:

1. **Preparação da Imagem**:
   - Salve a imagem frontal quadrada de alta resolução em `assets/references/novo_avatar_1024.png`.
   - Remova o fundo para preto puro ou transparente se necessário, focando no busto, pescoço e cabeça.
2. **Reconstrução 3D com `idol-sdk`**:
   - Execute o pipeline de reconstrução neural local (GPU RTX):
     ```powershell
     uv run --directory idol-sdk python ../scripts/run_local_idol.py --image assets/references/novo_avatar_1024.png --output assets/models/novo_avatar_raw.ply
     ```
   - Isso utiliza o modelo DINOv3 ViT-H/16+ local (`assets/models/dinov3_vith16plus_hf`) e o VAE do FLUX.2 para gerar 1.048.576 gaussianas 3D.
3. **Projeção de Textura UV e Micro-Densificação**:
   - Execute o algoritmo de projeção sub-pixel com calibração de Powell:
     ```powershell
     uv run python scripts/apply_uv_texture_3dgs.py --input-ply assets/models/novo_avatar_raw.ply --texture assets/references/novo_avatar_1024.png --output-ply assets/models/novo_avatar_clean.ply
     ```
4. **Verificação de Qualidade Multiview**:
   - Renderize as 4 perspectivas (frontal, perfil 90°, costas 180° e close-up de face):
     ```powershell
     Set-Location "isabella-core"
     & "$env:USERPROFILE\.cargo\bin\cargo.exe" run --release -- --multiview assets/renders/multiview_novo
     ```

---

### Workflow B: Trocar ou Ajustar a Voz e Modelo de TTS
O sistema de síntese de fala opera via ONNX de alta performance (`kokoro-onnx`).

1. **Trocar a Voz Feminina do Kokoro**:
   - No arquivo `scripts/voice_bridge.py`, localize a chamada de criação de fala:
     ```python
     samples, sr = kokoro.create(text, voice="pf_dora", speed=1.05, lang="pt-br")
     ```
   - O arquivo de vozes `assets/voices/kokoro/voices-v1.0.bin` inclui vozes treinadas como:
     - `pf_dora`: Português do Brasil, tom feminino doce, quente e aveludado (padrão atual).
     - `af_bella`, `af_sarah`, `af_nicole`, `af_sky`: Vozes em inglês de alta fidelidade.
   - Basta alterar o parâmetro `voice="nome_da_voz"` e `lang="pt-br"` (ou `lang="en-us"`).
2. **Substituir o Motor de TTS (ex: Piper ONNX ou Edge-TTS)**:
   - Se optar por outro motor, garanta apenas que o pipeline retorne um array de áudio linear PCM float32 (`samples`) e sua taxa de amostragem (`sr`).
   - Mantenha o loop de fatiamento de 33ms chamando `extract_visemes(chunk, sr)` e `send_state("speaking", jaw_open, lip_round, lip_spread, ...)` para manter a sincronia labial do modelo 3D.

---

### Workflow C: Trocar o Modelo de Linguagem (LLM) ou STT (Whisper)

1. **Alterar o Modelo no Ollama**:
   - No arquivo `scripts/voice_bridge.py`:
     ```python
     OLLAMA_URL = "http://localhost:11434/api/generate"
     MODEL_NAME = "hf.co/mradermacher/gemma-4-E2B-it-uncensored-GGUF:Q8_0"
     ```
   - Altere `MODEL_NAME` para qualquer modelo instalado no Ollama (ex: `dolphin-mistral`, `llama3.3:8b`, etc.).
   - O `SYSTEM_PROMPT` no topo de `voice_bridge.py` dita a personalidade, limites e tom de relacionamento da Isabella.
2. **Ajustar o Reconhecimento de Voz (Whisper)**:
   - Atualmente configurado para CPU com quantização INT8 ultrarrápida:
     ```python
     whisper = WhisperModel("base", device="cpu", compute_type="int8")
     ```
   - Para maior precisão em ambientes ruidosos ou com GPU dedicada:
     ```python
     whisper = WhisperModel("small", device="cuda", compute_type="float16")
     ```

---

### Workflow D: Compilação, Execução e Testes do Renderizador Rust

1. **Compilar a Versão Otimizada**:
   ```powershell
   Set-Location "D:\isabella-desktop\isabella-core"
   & "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release
   ```
2. **Baterias de Validação Automatizada (CLI Flags)**:
   - Snapshot único offscreen:
     ```powershell
     target\release\isabella-core.exe --snapshot assets/renders/snapshot.png
     ```
   - Renderização das 4 vistas 360°:
     ```powershell
     target\release\isabella-core.exe --multiview assets/renders/multiview
     ```
   - Teste de expressões labiais e piscar:
     ```powershell
     target\release\isabella-core.exe --test-expressions assets/renders/test_expressions
     ```
   - Bateria completa das 8 expressões emocionais FACS:
     ```powershell
     target\release\isabella-core.exe --test-emotions assets/renders/test_emotions
     ```
3. **Iniciar o Companion em Produção**:
   - Execute o script PowerShell mestre:
     ```powershell
     .\start_isabella.ps1
     ```
   - Ou utilize o atalho de duplo clique `iniciar_isabella.bat`.

---

## 5. Mapeamento da Estrutura de Diretórios

```
D:\isabella-desktop\
│
├── README.md                    # Manual de introdução, onboarding e arquitetura para devs
├── GEMINI.md                    # Manual de governança técnica e lições aprendidas
├── CHANGELOG.md                 # Histórico cirúrgico de todas as alterações
├── start_isabella.ps1           # Script mestre de inicialização paralela
├── iniciar_isabella.bat         # Launcher rápido para o usuário
│
├── isabella-core\               # Aplicação Desktop Rust / WGPU (3DGS Renderer)
│   ├── Cargo.toml               # Dependências (wgpu, winit, glam, tokio, image, windows)
│   └── src\
│       ├── main.rs              # Loop principal, janela Win32 ColorKey, UDP listener, hotkeys
│       ├── renderer.rs          # Pipeline WGPU, uniform buffers, camera, depth sorting
│       ├── ply_loader.rs        # Parser PLY 3DGS, conversão de quatérnios e rotação própria
│       └── shader.wgsl          # Vertex shader EWA 3DGS, deformadores FACS e cinemática
│
├── scripts\                     # Pipelines Python de suporte e IA
│   ├── voice_bridge.py          # Listener contínuo: VAD + ASR + TTS + UDP
│   ├── voice_test.py            # Testador interativo de streaming e visemas
│   ├── setup_llamacpp.py        # Instalador automatizado do backend llama.cpp CUDA
│   ├── run_local_idol.py        # Pipeline de reconstrução 3D neural (DINOv3 + FLUX.2 VAE)
│   └── apply_uv_texture_3dgs.py # Otimização Powell de projeção UV e micro-densificação
│
├── assets\                      # Recursos binários e modelos
│   ├── models\                  # Nuvens de gaussianas (.ply) e pesos neurais DINOv3
│   │   ├── isabella_bust_4x_1m.ply # Modelo HD de produção (1.048.576 splats)
│   │   └── dinov3_vith16plus_hf/   # Pesos locais DINOv3 ViT-H/16+
│   ├── references\              # Fotografias de referência 4X de entrada
│   ├── renders\                 # Snapshots de auditoria, multiview e testes FACS
│   └── voices\                  # Modelos Kokoro ONNX e vozes binárias
│       └── kokoro\
│           ├── kokoro-v1.0.onnx # Modelo ONNX de síntese neural
│           └── voices-v1.0.bin  # Conjunto de vozes (pf_dora, etc.)
│
├── tools\                       # Binários de suporte e infraestrutura local
│   └── llama-cpp\               # Binários CUDA e DLLs do llama-server (gerado via setup)
│
├── backups\                     # Arquivo histórico de backups (ignorado no Git)
│   ├── changelogs\              # Histórico de CHANGELOG.md.bak_*
│   ├── root\                    # Backups de scripts da raiz
│   ├── isabella-core\           # Backups de fontes Rust
│   └── scripts\                 # Backups de scripts Python
│
└── logs\                        # Registros de depuração em runtime
    └── voice_bridge.log         # Log de conversas e estados da IA
```

---

## 6. Governança e Regras Invioláveis de Desenvolvimento

1. **Protocolo Anti-Alucinação**:
   - Nunca declare uma ação como concluída sem antes inspecionar o output real dos comandos ou ler os arquivos/imagens gerados.
   - Sempre audite visualmente os renders gerados antes de apresentá-los.
2. **Backups e Changelog Cirúrgico**:
   - Antes de modificar qualquer arquivo existente: criar backup com sufixo `.bak_YYYYMMDD_HHMMSS`.
   - Após a alteração: registrar detalhadamente no `CHANGELOG.md` o que foi removido, o que foi adicionado e a justificativa técnica.
3. **Padrão de Qualidade Visual 3DGS**:
   - Zero estrias escuras nos olhos, zero cortes em degrau na geometria, zero transições abruptas.
   - Todas as deformações do vertex shader devem manter a suavidade de curvatura da superfície dérmica.
