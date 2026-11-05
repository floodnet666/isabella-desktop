# Modelos 3D e Pesos Neurais — Isabella Desktop

Os arquivos deste diretório contêm os modelos 3D Gaussian Splatting (3DGS) e os pesos neurais de inteligência artificial do projeto. Devido ao volume de dados (arquivos de dezenas de megabytes a gigabytes), os pesos binários são ignorados no repositório Git.

## Modelos Utilizados

### 1. Modelo 3D Gaussian Splatting (3DGS)
- **Arquivo principal**: `isabella_bust_4x_1m.ply` (~71 MB, 1.048.576 gaussianas).
- **Descrição**: Busto fotorealista de alta fidelidade com microdensificação UV sub-milimétrica.
- **Como gerar localmente**:
  1. Forneça uma fotografia frontal de referência em `assets/references/isabella_bust_4x_clean.png`.
  2. Execute a reconstrução 3D neural com o SDK DINOv3 + FLUX.2 VAE:
     ```powershell
     uv run --directory idol-sdk python ../scripts/run_local_idol.py --image assets/references/isabella_bust_4x_clean.png --output assets/models/isabella_raw.ply
     ```
  3. Execute a projeção UV com calibração de Powell:
     ```powershell
     uv run python scripts/apply_uv_texture_3dgs.py --input-ply assets/models/isabella_raw.ply --texture assets/references/isabella_bust_4x_clean.png --output-ply assets/models/isabella_bust_4x_1m.ply
     ```

### 2. Modelo Multimodal Conversacional (LLM / ASR / TTS)
- **Modelo Principal**: `LFM3-Omni-2B-F16.gguf` (ou `LFM3-Omni-2B-Abliter8-BF16.gguf`)
- **Projetor Multimodal (ASR / Áudio)**: `mmproj-LFM3-Omni-2B-F16.gguf`
- **Localização Padrão**: Configure o caminho no `start_isabella.ps1` (padrão em disco local `E:\modelos_ollama\` ou `assets/models/llm_multimodal/`).
- **Alternativa Ollama**: Você também pode utilizar o modelo Ollama uncensored configurando `voice_bridge.py` conforme descrito no `GEMINI.md`.
