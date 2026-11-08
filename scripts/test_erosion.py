import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import binary_erosion

def clean_alpha_edge(im):
    im = im.convert("RGBA")
    arr = np.array(im)
    alpha = arr[:, :, 3]
    
    # Criar máscara binária sólida
    solid_mask = alpha > 128
    
    # Erodir 2 pixels para eliminar o halo branco da borda
    eroded = binary_erosion(solid_mask, iterations=2)
    
    # Suavizar as bordas da nova máscara
    eroded_img = Image.fromarray((eroded * 255).astype(np.uint8), mode="L")
    smooth_alpha = eroded_img.filter(ImageFilter.GaussianBlur(1.0))
    
    arr[:, :, 3] = np.array(smooth_alpha)
    return Image.fromarray(arr, mode="RGBA")

raw = Image.open(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\test_decontam.png")
clean = clean_alpha_edge(raw)
clean.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\test_eroded.png")

bg = Image.new("RGBA", clean.size, (20, 22, 30, 255))
bg.alpha_composite(clean)
bg.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_master\test_eroded_dark.png")
print("Teste de erosao de borda salvo!")
