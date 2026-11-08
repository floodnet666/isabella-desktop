import os
from PIL import Image

ref_grid = r"C:\Users\thiag\Pictures\REf emoçoes\emtions grid.jpg"
im = Image.open(ref_grid)
print("emtions grid size:", im.size)

ref_faces = r"C:\Users\thiag\Pictures\REf emoçoes\ref faces.jpg"
im2 = Image.open(ref_faces)
print("ref faces size:", im2.size)

# Também os screenshots
ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"
for f in os.listdir(ref_dir):
    if f.startswith("Screenshot"):
        print("Screenshot file:", f)
