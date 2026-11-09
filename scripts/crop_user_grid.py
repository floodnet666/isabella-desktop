import os
from PIL import Image

grid_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793965707510_e9083491.jpg"
im = Image.open(grid_path)
W, H = im.size

out_dir = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\raw_crops"
os.makedirs(out_dir, exist_ok=True)

# 3 colunas e 3 linhas
col_w = W / 3.0 # 255.0
row_h = H / 3.0 # 341.33

cell_names = [
    # Linha 0
    "01_neutral",
    "02_speaking_soft",
    "03_smile_soft",
    # Linha 1
    "04_joy_radiant",
    "05_anger_frown",
    "06_surprise_shock",
    # Linha 2
    "07_sad_dengo",
    "08_wink_flirt",
    "09_joy_eyes_closed"
]

idx = 0
for r in range(3):
    y0 = int(r * row_h)
    y1 = int((r + 1) * row_h) if r < 2 else H
    for c in range(3):
        x0 = int(c * col_w)
        x1 = int((c + 1) * col_w) if c < 2 else W
        
        crop = im.crop((x0, y0, x1, y1))
        name = cell_names[idx]
        out_file = os.path.join(out_dir, f"{name}.png")
        crop.save(out_file)
        print(f"Célula {idx+1} ({name}) salva: box=({x0}, {y0}, {x1}, {y1}), size={crop.size}")
        idx += 1
