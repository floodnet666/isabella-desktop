# Recursos de Síntese Vocal (TTS)

Este diretório contém os modelos neurais de Text-to-Speech e pacotes de vozes para síntese local.

## Motores Suportados

### 1. Liquid AI In-Memory TTS (`/tts`)
- Utilizado por padrão pelo pipeline multimodal de baixa latência em conjunto com `llama-server.exe`.
- Opera diretamente na GPU sem necessidade de arquivos ONNX externos adicionais.

### 2. Kokoro TTS (ONNX)
- **Modelo**: `assets/voices/kokoro/kokoro-v1.0.onnx` (~325 MB)
- **Vozes**: `assets/voices/kokoro/voices-v1.0.bin` (~28 MB, inclui voz brasileira `pf_dora`)
- **Como baixar**:
  ```powershell
  uv run python scripts/download_model.py
  ```
  Ou diretamente do repositório Hugging Face: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M).
