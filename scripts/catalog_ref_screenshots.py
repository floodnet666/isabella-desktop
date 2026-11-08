import os
from PIL import Image

ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"
files = [f for f in os.listdir(ref_dir) if f.startswith("Screenshot") and f.endswith(".png")]

print(f"Total screenshots: {len(files)}")
for f in sorted(files):
    path = os.path.join(ref_dir, f)
    with Image.open(path) as img:
        print(f"{f}: size={img.size}, mode={img.mode}")
