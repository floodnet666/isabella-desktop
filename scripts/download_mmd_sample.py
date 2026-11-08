import os
import urllib.request

base_url = "https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/models/mmd/miku/"
target_dir = r"D:\isabella-desktop\benchmarks_avatars\mmd"
os.makedirs(target_dir, exist_ok=True)

files = [
    "miku_v2.pmd",
    "body.png",
    "hair.png",
    "eye.png",
    "cloth.png",
    "face.png"
]

print("Baixando modelo oficial MMD Miku v2...")
for f in files:
    url = base_url + f
    dest = os.path.join(target_dir, f)
    try:
        print(f"Baixando {f}...")
        urllib.request.urlretrieve(url, dest)
        print(f"OK: {dest} ({os.path.getsize(dest)} bytes)")
    except Exception as e:
        print(f"Erro em {f}: {e}")

print("Download MMD concluido!")
