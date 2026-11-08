import numpy as np
from PIL import Image

def decontaminate_white_fringe(im):
    im = im.convert("RGBA")
    arr = np.array(im, dtype=np.float32)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3] / 255.0
    
    # Onde alpha < 1.0 e alpha > 0.05
    mask = (alpha > 0.05) & (alpha < 0.98)
    
    # Descontaminação: remover a componente branca do pixel semi-transparente
    # C_clean = clamp((C - (1 - alpha) * 255) / alpha)
    for c in range(3):
        cleaned = (rgb[:, :, c] - (1.0 - alpha) * 255.0) / np.maximum(alpha, 0.01)
        rgb[:, :, c] = np.where(mask, np.clip(cleaned, 0, 255), rgb[:, :, c])
        
    arr[:, :, :3] = rgb
    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")

raw = Image.open(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\sprites\neutral.png")
clean = decontaminate_white_fringe(raw)
clean.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\test_decontam.png")

# Compor sobre fundo escuro para checar se o halo branco sumiu
bg = Image.new("RGBA", clean.size, (20, 22, 30, 255))
bg.alpha_composite(clean)
bg.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\test_decontam_dark.png")
print("Teste de descontaminacao salvo!")
