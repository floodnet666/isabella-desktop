import os
from PIL import Image

ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"

# Vamos listar todos os arquivos com data e tamanho
files = sorted(os.listdir(ref_dir))
for f in files:
    fp = os.path.join(ref_dir, f)
    if os.path.isfile(fp):
        im = Image.open(fp)
        print(f"{f}: size={im.size}, mode={im.mode}")
