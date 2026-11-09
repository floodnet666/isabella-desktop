import os
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

def create_photorealistic_isabella_sprites():
    out_dir = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\sprites"
    os.makedirs(out_dir, exist_ok=True)

    user_img_path = r"C:\Users\thiag\.gemini\antigravity\brain\717d88c3-f239-4f17-a66d-8c616231e548\.user_uploaded\media_1793964800834_9d0e32a3.png"
    im_full = Image.open(user_img_path).convert("RGBA")

    # Busto / Companion
    crop_box = (80, 15, 496, 580)
    bust = im_full.crop(crop_box)
    W, H = bust.size

    arr_base = np.array(bust, dtype=np.float32)
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)

    def warp_image(flow_y, flow_x):
        coords_y = Y + flow_y
        coords_x = X + flow_x
        warped = np.zeros_like(arr_base)
        for c in range(4):
            warped[:, :, c] = map_coordinates(arr_base[:, :, c], [coords_y, coords_x], order=3, mode='nearest')
        warped = np.clip(warped, 0, 255).astype(np.uint8)
        return Image.fromarray(warped, mode="RGBA")

    def gaussian_blob(cx, cy, radius_x, radius_y):
        dist = ((X - cx) / radius_x)**2 + ((Y - cy) / radius_y)**2
        return np.exp(-0.5 * dist)

    # 1. NEUTRAL
    sprite_neutral = bust.copy()
    sprite_neutral.save(os.path.join(out_dir, "isabella_neutral.png"))

    # 2. JOY / SMILE (Sorriso aberto natural com maçãs do rosto elevadas)
    flow_y_joy = np.zeros((H, W), dtype=np.float32)
    flow_x_joy = np.zeros((H, W), dtype=np.float32)

    # Cantos da boca sobem e expandem
    k_corner_l = gaussian_blob(185, 125, 14, 11)
    k_corner_r = gaussian_blob(223, 123, 14, 11)
    flow_y_joy -= k_corner_l * 7.5
    flow_x_joy -= k_corner_l * 4.0
    flow_y_joy -= k_corner_r * 7.5
    flow_x_joy += k_corner_r * 4.0

    # Lábio superior sobe suavemente
    k_lip_up = gaussian_blob(204, 120, 16, 8)
    flow_y_joy -= k_lip_up * 3.5

    # Bochechas sobem (Duchenne)
    k_cheek = gaussian_blob(160, 105, 20, 16) + gaussian_blob(245, 102, 20, 16)
    flow_y_joy -= k_cheek * 4.5

    # Estreitamento inferior dos olhos
    k_eyes_dn = gaussian_blob(178, 88, 16, 9) + gaussian_blob(228, 86, 16, 9)
    flow_y_joy -= k_eyes_dn * 3.0

    sprite_joy = warp_image(flow_y_joy, flow_x_joy)
    sprite_joy.save(os.path.join(out_dir, "isabella_joy.png"))

    # 3. SMIRK / PROVOCANTE (Assimetria maliciosa)
    flow_y_smirk = np.zeros((H, W), dtype=np.float32)
    flow_x_smirk = np.zeros((H, W), dtype=np.float32)

    # Canto direito sobe intensamente
    k_smirk_r = gaussian_blob(223, 123, 15, 13)
    flow_y_smirk -= k_smirk_r * 9.0
    flow_x_smirk += k_smirk_r * 4.5

    # Canto esquerdo levemente para baixo
    k_smirk_l = gaussian_blob(185, 125, 12, 10)
    flow_y_smirk += k_smirk_l * 1.5

    # Sobrancelha direita arqueada
    k_brow_r = gaussian_blob(228, 55, 18, 12)
    flow_y_smirk -= k_brow_r * 4.5

    # Bochecha direita sobe
    k_cheek_r = gaussian_blob(245, 102, 18, 14)
    flow_y_smirk -= k_cheek_r * 3.5

    sprite_smirk = warp_image(flow_y_smirk, flow_x_smirk)
    sprite_smirk.save(os.path.join(out_dir, "isabella_smirk.png"))

    # 4. SURPRISE / CURIOSA (Sobrancelhas e olhos erguidos, mandíbula relaxada)
    flow_y_surp = np.zeros((H, W), dtype=np.float32)
    flow_x_surp = np.zeros((H, W), dtype=np.float32)

    # Sobrancelhas erguidas
    k_brows = gaussian_blob(178, 58, 22, 14) + gaussian_blob(228, 55, 22, 14)
    flow_y_surp -= k_brows * 7.5

    # Olhos abertos
    k_eyes_up = gaussian_blob(178, 80, 16, 10) + gaussian_blob(228, 78, 16, 10)
    flow_y_surp -= k_eyes_up * 3.5

    # Queixo e lábio inferior descem
    k_jaw_down = gaussian_blob(204, 132, 18, 14)
    flow_y_surp += k_jaw_down * 7.0

    sprite_surprise = warp_image(flow_y_surp, flow_x_surp)
    sprite_surprise.save(os.path.join(out_dir, "isabella_surprise.png"))

    # 5. SAD / DENGO (Sobrancelhas em arco interno, cantos caídos)
    flow_y_sad = np.zeros((H, W), dtype=np.float32)
    flow_x_sad = np.zeros((H, W), dtype=np.float32)

    # Centro das sobrancelhas sobe
    k_brow_mid = gaussian_blob(203, 58, 18, 12)
    flow_y_sad -= k_brow_mid * 6.5

    # Extremidades descem
    k_brow_out = gaussian_blob(162, 60, 14, 10) + gaussian_blob(244, 57, 14, 10)
    flow_y_sad += k_brow_out * 3.0

    # Cantos da boca descem
    k_corners = gaussian_blob(185, 125, 12, 10) + gaussian_blob(223, 123, 12, 10)
    flow_y_sad += k_corners * 5.5

    sprite_sad = warp_image(flow_y_sad, flow_x_sad)
    sprite_sad.save(os.path.join(out_dir, "isabella_sad.png"))

    # 6. BLINK (Pálpebra fechada via deformação dérmica pura, sem pintura fake)
    # A pálpebra superior e cílios descem em direção à linha palpebral inferior
    flow_y_blink = np.zeros((H, W), dtype=np.float32)
    flow_x_blink = np.zeros((H, W), dtype=np.float32)

    # Puxar pálpebra superior (Y=78..82) para baixo em Y=86
    k_lid_l = gaussian_blob(178, 79, 15, 8)
    k_lid_r = gaussian_blob(228, 77, 15, 8)
    flow_y_blink += (k_lid_l + k_lid_r) * 8.5

    # Pálpebra inferior sobe levemente para encontrar
    k_lid_inf_l = gaussian_blob(178, 88, 15, 6)
    k_lid_inf_r = gaussian_blob(228, 86, 15, 6)
    flow_y_blink -= (k_lid_inf_l + k_lid_inf_r) * 2.5

    sprite_blink = warp_image(flow_y_blink, flow_x_blink)
    sprite_blink.save(os.path.join(out_dir, "isabella_blink.png"))

    # 7. SPEAKING (Abertura labial e articulação de fala pura)
    flow_y_spk = np.zeros((H, W), dtype=np.float32)
    flow_x_spk = np.zeros((H, W), dtype=np.float32)

    # Lábio inferior desce
    k_spk_dn = gaussian_blob(204, 128, 16, 10)
    flow_y_spk += k_spk_dn * 6.5

    # Lábio superior sobe
    k_spk_up = gaussian_blob(204, 120, 15, 8)
    flow_y_spk -= k_spk_up * 2.5

    # Cantos da boca aproximam-se levemente (fala visema 'O/U')
    k_corner_spk_l = gaussian_blob(185, 125, 12, 10)
    k_corner_spk_r = gaussian_blob(223, 123, 12, 10)
    flow_x_spk += k_corner_spk_l * 2.0
    flow_x_spk -= k_corner_spk_r * 2.0

    sprite_speaking = warp_image(flow_y_spk, flow_x_spk)
    sprite_speaking.save(os.path.join(out_dir, "isabella_speaking.png"))

    print(f"Todas as 7 expressões 100% fotorealistas da Isabella salvas em {out_dir}!")

    # Montar painel comparativo 4x2
    from PIL import ImageDraw
    grid_img = Image.new("RGBA", (W * 4, H * 2), (20, 22, 28, 255))
    sprites = [
        ("1. Neutra (Repouso)", sprite_neutral),
        ("2. Piscando (Blink)", sprite_blink),
        ("3. Alegria (Joy Smile)", sprite_joy),
        ("4. Smirk (Provocante)", sprite_smirk),
        ("5. Surpresa (Curiosa)", sprite_surprise),
        ("6. Tristeza (Dengo)", sprite_sad),
        ("7. Fala (Sincronia Labial)", sprite_speaking),
        ("8. Isabella Original (Ref)", bust)
    ]

    for idx, (label, s_img) in enumerate(sprites):
        row = idx // 4
        col = idx % 4
        px = col * W
        py = row * H
        grid_img.alpha_composite(s_img, (px, py))
        dl = ImageDraw.Draw(grid_img)
        dl.rectangle([(px + 10, py + 10), (px + 230, py + 38)], fill=(10, 10, 15, 220))
        dl.text((px + 16, py + 16), label, fill=(255, 255, 255, 255))

    grid_path = r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber\isabella_emotions_grid.png"
    grid_img.save(grid_path)
    print(f"Novo painel comparativo 100% fotorealista salvo em {grid_path}")

if __name__ == "__main__":
    create_photorealistic_isabella_sprites()
