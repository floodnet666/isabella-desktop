# Ferramentas Llama.cpp (Local Inference Backend)

Este diretório contém os binários executáveis e bibliotecas CUDA do `llama.cpp` utilizados pelo backend multimodal do Isabella Desktop.

Por se tratarem de binários pesados (~1.8 GB com dependências CUDA), eles são ignorados pelo Git.

## Como Instalar Automaticamente

Para baixar e extrair automaticamente a versão compatível com aceleração CUDA 12.4, execute a partir da raiz do projeto:

```powershell
uv run python scripts/setup_llamacpp.py
```

O script baixa os pacotes oficiais de release do `ggml-org/llama.cpp` (versão com suporte a áudio multimodal) e extrai os executáveis (`llama-server.exe`, `llama-tts.exe`, DLLs CUDA) diretamente neste diretório.
