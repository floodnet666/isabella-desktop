import os
from PIL import Image, ImageDraw

bust_path = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\sprites\isabella_neutral.png"
bust = Image.open(bust_path)

# Recortar a face com margem
# A face está aproximadamente em X=100..300, Y=0..200
face_zone = bust.crop((120, 10, 290, 180)) # W=170, H=170
W, H = face_zone.size

# Criar imagem com grid de medição a cada 10px
grid_face = face_zone.copy()
d = ImageDraw.Draw(grid_face)

for x in range(0, W, 10):
    color = (255, 0, 0, 120) if x % 50 == 0 else (255, 255, 255, 60)
    d.line([(x, 0), (x, H)], fill=color, width=1)
    if x % 20 == 0:
        d.text((x + 1, 2), str(x), fill=(255, 255, 0, 255))

for y in range(0, H, 10):
    color = (255, 0, 0, 120) if y % 50 == 0 else (255, 255, 255, 60)
    d.line([(0, y), (W, y)], fill=color, width=1)
    if y % 20 == 0:
        d.text((2, y + 1), str(y), fill=(255, 255, 0, 255))

out_path = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\face_grid_measure.png"
grid_face.save(out_path)
print(f"Face grid salva em {out_path} (origem X=120, Y=10)")
