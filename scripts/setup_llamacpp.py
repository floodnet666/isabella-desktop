import os
import sys
import zipfile
import urllib.request
from pathlib import Path

TARGET_DIR = Path(r"D:\isabella-desktop\tools\llama-cpp")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

TAG = "b12102"
FILES = [
    "llama-b12102-bin-win-cuda-12.4-x64.zip",
    "cudart-llama-bin-win-cuda-12.4-x64.zip"
]

def download_and_extract(filename):
    url = f"https://github.com/ggml-org/llama.cpp/releases/download/{TAG}/{filename}"
    zip_path = TARGET_DIR / filename
    
    if not zip_path.exists() or zip_path.stat().st_size < 1024 * 1024:
        print(f"Baixando {filename} de {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out:
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 1024 * 4) # 4MB chunks
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(f"\r  {filename}: {downloaded/(1024**2):.1f}/{total/(1024**2):.1f} MB ({downloaded*100/total:.1f}%)", end="", flush=True)
        print(f"\nDownload de {filename} concluído!")
    else:
        print(f"Arquivo {filename} já existe ({zip_path.stat().st_size/(1024**2):.1f} MB).")
        
    print(f"Extraindo {filename} para {TARGET_DIR}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(TARGET_DIR)
    print(f"Extração de {filename} concluída!")

for f in FILES:
    download_and_extract(f)

print("\nVerificando executáveis extraídos:")
for exe in TARGET_DIR.glob("*.exe"):
    print(f"  - {exe.name}")
