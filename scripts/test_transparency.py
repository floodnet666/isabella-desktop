import os
import numpy as np
from PIL import Image, ImageFilter

def make_transparent(im, bg_thresh=245):
    """Converte fundo branco em transparência suave com anti-aliasing."""
    im = im.convert("RGBA")
    arr = np.array(im, dtype=np.float32)
    rgb = arr[:, :, :3]
    
    # Distância para branco (255, 255, 255)
    dist_to_white = np.sqrt(np.sum((255.0 - rgb)**2, axis=2))
    
    # Criar alfa suave
    # dist = 0 -> alpha = 0 (transparente)
    # dist > 35 -> alpha = 255 (opaco)
    alpha = np.clip((dist_to_white - 8.0) / 25.0, 0.0, 1.0) * 255.0
    
    # Aplicar limpeza nos pixels totalmente brancos
    arr[:, :, 3] = alpha
    result = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
    return result

test_img = Image.open(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\raw_crops\01_neutral.png")
transp = make_transparent(test_img)
out_test = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\test_transp.png"
transp.save(out_test)
print(f"Teste de transparencia salvo em {out_test}")
