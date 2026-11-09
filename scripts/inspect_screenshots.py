import os
from PIL import Image

ref_inspect_dir = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\ref_inspect"

# Vamos ver o primeiro screenshot
fnames = sorted([f for f in os.listdir(ref_inspect_dir) if f.startswith("Screenshot")])
print("Primeiros screenshots:", fnames[:5])

# Inspecionar emtions grid.jpg
im_grid = Image.open(os.path.join(ref_inspect_dir, "emtions grid.jpg"))
print("Grid format:", im_grid.format, im_grid.size)

# Inspecionar ref faces.jpg
im_faces = Image.open(os.path.join(ref_inspect_dir, "ref faces.jpg"))
print("Faces format:", im_faces.format, im_faces.size)
