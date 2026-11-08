import os
import numpy as np
from PIL import Image

grid_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793965707510_e9083491.jpg"
im = Image.open(grid_path)
W, H = im.size
arr = np.array(im)

# Vamos encontrar os pontos médios dos separadores:
# Colunas:
# Col 0: de 0 a ~255
# Col 1: de ~255 a ~510
# Col 2: de ~510 a 765
# Linhas:
# Row 0: 0 a ~341
# Row 1: ~341 a ~682
# Row 2: ~682 a 1024

# Vamos verificar a linha horizontal exata de corte entre Row 0 e Row 1:
# Inspecionar arr[335:348, :, :]
diffs_row1 = np.diff(arr[330:350, :, :].astype(float), axis=0)
print("Row separator 1 inspection:")

# Fazer o recorte com margem interna de segurança (trim de 3px para evitar vazamento das células vizinhas)
def get_clean_box(col, row):
    x0 = int(col * (W / 3.0))
    x1 = int((col + 1) * (W / 3.0))
    y0 = int(row * (H / 3.0))
    y1 = int((row + 1) * (H / 3.0))
    
    # Se não for a primeira linha, avançar 4px para baixo (para tirar pedaço da cabeça anterior)
    if row > 0:
        y0 += 4
    # Se não for a última linha, recuar 4px
    if row < 2:
        y1 -= 4
        
    if col > 0:
        x0 += 2
    if col < 2:
        x1 -= 2
        
    return (x0, y0, x1, y1)

out_clean = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\clean_sprites"
os.makedirs(out_clean, exist_ok=True)

names = [
    ["neutral", "speaking_soft", "smile_soft"],
    ["joy_radiant", "anger_frown", "surprise_shock"],
    ["sad_dengo", "wink_flirt", "joy_eyes_closed"]
]

for r in range(3):
    for c in range(3):
        box = get_clean_box(c, r)
        crop = im.crop(box)
        name = names[r][c]
        crop.save(os.path.join(out_clean, f"{name}_raw.png"))
        print(f"Salvo {name}: box={box}, size={crop.size}")
