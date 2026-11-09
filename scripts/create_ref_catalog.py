import os
from PIL import Image, ImageDraw, ImageFont

ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"
files = sorted([f for f in os.listdir(ref_dir) if f.startswith("Screenshot") and f.endswith(".png")])

# Criar um grid 3x6 rotulado
w, h = 300, 320
grid_img = Image.new("RGB", (w * 6, h * 3), (240, 240, 240))
draw = ImageDraw.Draw(grid_img)

for idx, f in enumerate(files):
    row = idx // 6
    col = idx % 6
    path = os.path.join(ref_dir, f)
    with Image.open(path) as img:
        img_rgb = img.convert("RGB").resize((w, 290))
        grid_img.paste(img_rgb, (col * w, row * h))
        time_part = f.replace("Screenshot 2024-11-26 ", "").replace(".png", "")
        draw.text((col * w + 10, row * h + 295), f"#{idx+1}: {time_part}", fill=(0, 0, 0))

out_path = r"D:\isabella-desktop\assets\renders\warrior_girl\ref_catalog_grid.jpg"
grid_img.save(out_path, quality=90)
print(f"Salvo catalogo em {out_path}")
