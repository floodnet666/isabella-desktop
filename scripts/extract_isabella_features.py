import os
from PIL import Image

user_img_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793964800834_9d0e32a3.png"
im = Image.open(user_img_path)

# Dimensões da imagem original: 576 x 1024
# Vamos extrair o busto (de Y=15 até Y=550) com fundo transparente
bust = im.crop((80, 15, 496, 550))
out_dir = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber"
os.makedirs(out_dir, exist_ok=True)
bust.save(os.path.join(out_dir, "isabella_bust_orig.png"))

# Coordenadas da face na imagem original:
# A cabeça fica aproximadamente entre X=200..370, Y=25..220
# Olhos: Y ~ 90..120
# Nariz: Y ~ 115..135
# Boca: Y ~ 135..165
# Queixo: Y ~ 165..195

face = im.crop((210, 30, 365, 210))
face.save(os.path.join(out_dir, "isabella_face_orig.png"))

eyes = im.crop((230, 85, 345, 125))
eyes.save(os.path.join(out_dir, "isabella_eyes_orig.png"))

mouth = im.crop((250, 135, 325, 175))
mouth.save(os.path.join(out_dir, "isabella_mouth_orig.png"))

print("Recortes salvos com sucesso!")
