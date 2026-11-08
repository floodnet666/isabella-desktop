import os
from PIL import Image

img_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793964800834_9d0e32a3.png"
im = Image.open(img_path)

# Encontrar bounding box do canal alfa não-transparente
alpha = im.split()[-1]
bbox = alpha.getbbox()
print("Full body bbox:", bbox)

# A cabeça está no topo. Vamos recortar a área do busto/rosto
# (x0, y0, x1, y1)
# Busto: do topo até a cintura ou ombros
# Vamos inspecionar os primeiros 450 pixels verticais
crop_bust = im.crop((120, 20, 456, 450))
os.makedirs(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber", exist_ok=True)
crop_bust.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\isabella_bust_raw.png")

# Face close-up
crop_face = im.crop((200, 25, 370, 220))
crop_face.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\isabella_face_raw.png")

print(f"Bust salvo: {crop_bust.size}")
print(f"Face salva: {crop_face.size}")
