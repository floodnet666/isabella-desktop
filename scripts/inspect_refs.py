import os
from PIL import Image

user_img_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793964800834_9d0e32a3.png"
ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"

img = Image.open(user_img_path)
print(f"User image: {img.size}, mode={img.mode}")

for fname in os.listdir(ref_dir):
    fpath = os.path.join(ref_dir, fname)
    if os.path.isfile(fpath) and fname.lower().endswith(('.png', '.jpg', '.webp')):
        im = Image.open(fpath)
        print(f"Ref: {fname} -> {im.size}, mode={im.mode}")
