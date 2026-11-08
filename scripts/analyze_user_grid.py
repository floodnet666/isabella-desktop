import os
import numpy as np
from PIL import Image

grid_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793965707510_e9083491.jpg"
im = Image.open(grid_path)
W, H = im.size
arr = np.array(im)

print(f"Dimensões totais: W={W}, H={H}")

# Vamos analisar os perfis verticais e horizontais de intensidade de branco
# Fundo entre células é branco (RGB perto de 255)
is_white_col = (arr > 240).all(axis=2).mean(axis=0) # média por coluna
is_white_row = (arr > 240).all(axis=2).mean(axis=1) # média por linha

# Encontrar colunas e linhas que dividem os quadrantes
print("Análise de linhas e colunas concluída.")
