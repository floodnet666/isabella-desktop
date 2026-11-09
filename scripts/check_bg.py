import numpy as np
from PIL import Image

grid_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793965707510_e9083491.jpg"
im = Image.open(grid_path)
arr = np.array(im)

# Verificar cantos de cada célula
# Na célula 1: topo esquerdo (0,0), topo direito (250, 0)
print("RGB (5, 5):", arr[5, 5])
print("RGB (240, 5):", arr[5, 240])
print("RGB (50, 5):", arr[5, 50])
print("Min/Max RGB em Y=0..20, X=0..30:")
sub = arr[0:20, 0:30]
print("Min:", sub.min(axis=(0,1)), "Max:", sub.max(axis=(0,1)))
