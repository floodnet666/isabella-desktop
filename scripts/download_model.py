import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

TARGET_DIR = Path(r"D:\isabella-desktop\assets\models\llm_multimodal")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

REPO_ID = "llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF"
FILES = [
    "gemma-4-E4B-it-mmproj-BF16.gguf",
    "gemma-4-E4B-it-ultra-uncensored-heretic-Q4_K_M.gguf"
]

token_path = Path.home() / ".cache" / "huggingface" / "token"
token = None
if token_path.exists():
    token = token_path.read_text().strip()

print(f"Iniciando download de {REPO_ID} para {TARGET_DIR}...")
for filename in FILES:
    dest = TARGET_DIR / filename
    if dest.exists() and dest.stat().st_size > 100 * 1024 * 1024:
        print(f"Arquivo já existe: {filename} ({dest.stat().st_size / (1024**3):.2f} GB). Pulando...")
        continue
    
    print(f"\nBaixando {filename}...")
    hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        local_dir=str(TARGET_DIR),
        token=token
    )
    print(f"Concluído: {filename} ({dest.stat().st_size / (1024**3):.2f} GB)")

print("\nTodos os arquivos foram baixados com sucesso!")
