import os
from PIL import Image

ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"

# Vamos copiar os primeiros screenshots para podermos inspecionar
import shutil
out_dir = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\ref_inspect"
os.makedirs(out_dir, exist_ok=True)

for f in sorted(os.listdir(ref_dir)):
    src = os.path.join(ref_dir, f)
    dst = os.path.join(out_dir, f)
    if os.path.isfile(src):
        shutil.copy(src, dst)

print(f"Copiados todos os {len(os.listdir(ref_dir))} arquivos de referencia para {out_dir}")
