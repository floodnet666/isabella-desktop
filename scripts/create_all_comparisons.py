import os
from PIL import Image, ImageDraw, ImageFont

ref_dir = r"C:\Users\thiag\Pictures\REf emoçoes"
render_dir = r"D:\isabella-desktop\assets\renders\warrior_girl\emotions"
out_dir = r"D:\isabella-desktop\assets\renders\warrior_girl\comparisons"
os.makedirs(out_dir, exist_ok=True)

emotions = [
    (1, "Screenshot 2024-11-26 104001.png", "Perfil_Rosnado_Furioso", "AU4 (Brows Down) + AU20 (Lip Stretch) + AU9 (Sneer)", "Yaw 82°, Neck Stretch"),
    (2, "Screenshot 2024-11-26 104108.png", "34_Grito_de_Guerra", "AU26 (Jaw Open) + AU4 (Frown) + AU1+2 (Surprise)", "Yaw 52°, Pitch -12°"),
    (3, "Screenshot 2024-11-26 104205.png", "Frontal_Grito_Furioso", "AU26 (Jaw Open Wide) + AU4 (Brow Frown) + Eyes Wide", "Pitch 6° (Projetada)"),
    (4, "Screenshot 2024-11-26 104213.png", "Frontal_Raiva_Dentes_Cerrados", "AU20 (Lip Stretch) + AU4 (Brow Frown) + Eyes Squint", "Pitch 5°"),
    (5, "Screenshot 2024-11-26 104224.png", "Frontal_Desgosto_Magoada", "AU1 (Inner Brow Up) + AU15 (Lip Depressor)", "Roll 4°"),
    (6, "Screenshot 2024-11-26 104233.png", "Frontal_Espanto_Choque", "AU1+2 (Brows Surprise) + AU26 (Jaw Drop O) + Eyes Wide", "Pitch -4° (Recuo)"),
    (7, "Screenshot 2024-11-26 104242.png", "Frontal_Desprezo_Desdem", "Smirk Left + AU4 (Frown) + AU9 (Sneer) + Eyes Squint", "Roll -6°, Yaw -5°"),
    (8, "Screenshot 2024-11-26 104249.png", "34_Nojo_Intenso", "AU9 (Sneer) + AU20 (Lip Stretch) + AU4 (Brow Frown)", "Yaw 38°, Pitch 6°"),
    (9, "Screenshot 2024-11-26 104255.png", "Frontal_Irritacao_Ameaca", "AU4 (Brow Frown Max) + AU15 (Frown) + Eyes Squint", "Pitch 10°"),
    (10, "Screenshot 2024-11-26 104302.png", "Frontal_Desconfiada_Olhar_Lateral", "AU4 (Brow Frown) + AU1+2 (Slight) + Eyes Squint", "Pose Neutra / Olhar"),
    (11, "Screenshot 2024-11-26 104309.png", "Frontal_Cetica_Questionadora", "AU1+2 (One Brow Up) + AU15 (Lip Depressor)", "Roll 9° (Inclinada)"),
    (12, "Screenshot 2024-11-26 104322.png", "Frontal_Emburrada_Furia_Contida", "AU4 (Brow Frown) + AU15 (Lip Depressor) + Squint", "Pitch 7°"),
    (13, "Screenshot 2024-11-26 104334.png", "Frontal_Tristeza_Dengo", "AU1 (Inner Brow Up Max) + AU15 (Lip Depressor)", "Roll 11° (Melancolia)"),
    (14, "Screenshot 2024-11-26 104340.png", "Perfil_Neutro", "Anatomia Neutra de Perfil", "Yaw 88°"),
    (15, "Screenshot 2024-11-26 104346.png", "Frontal_Sorriso_Contido", "AU12 (Smile Closed / Subtle)", "Pose Neutra"),
    (16, "Screenshot 2024-11-26 104352.png", "Frontal_Pensativa_Olhar_Superior", "AU1+2 (Brows Raised) + AU12 (Slight) + Eyes Wide", "Pitch -16° (Olhar Teto)"),
    (17, "Screenshot 2024-11-26 104414.png", "Frontal_Sorriso_Maroto_Provocante", "AU12 (Smile Open) + Smirk Left + AU20 (Stretch)", "Roll 2°, Yaw 2°"),
    (18, "Screenshot 2024-11-26 104423.png", "Frontal_Sorriso_Simpatico_Gentil", "AU12 (Smile Cheek Raiser Harmony)", "Pose Neutra")
]

# Tentar carregar fonte padrão ou usar default
font = None
font_title = None

pair_w, pair_h = 512, 512
header_h = 60
footer_h = 50
canvas_w = pair_w * 2 + 30
canvas_h = header_h + pair_h + footer_h

individual_pairs = []

for idx, ref_name, emo_name, facs_desc, pose_desc in emotions:
    ref_path = os.path.join(ref_dir, ref_name)
    render_path = os.path.join(render_dir, f"emotion_{idx:02d}_{emo_name}.png")

    if not os.path.exists(ref_path) or not os.path.exists(render_path):
        print(f"Pular {idx}: arquivos nao encontrados")
        continue

    img_ref = Image.open(ref_path).convert("RGB").resize((pair_w, pair_h), Image.Resampling.LANCZOS)
    img_3d = Image.open(render_path).convert("RGB").resize((pair_w, pair_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (30, 32, 36))
    draw = ImageDraw.Draw(canvas)

    # Header
    title_text = f"EMOCAO #{idx:02d} — {emo_name.replace('_', ' ').upper()}"
    draw.text((20, 15), title_text, fill=(255, 215, 0))
    draw.text((pair_w + 30, 38), "WARRIOR GIRL 3D (BLENDER)", fill=(100, 220, 255))
    draw.text((20, 38), "REFERENCIA HUMANA (FACS)", fill=(180, 255, 180))

    # Paste images
    canvas.paste(img_ref, (10, header_h))
    canvas.paste(img_3d, (pair_w + 20, header_h))

    # Footer
    footer_text = f"FACS: {facs_desc} | Pose Cervical: {pose_desc}"
    draw.text((20, header_h + pair_h + 15), footer_text, fill=(220, 220, 220))

    out_file = os.path.join(out_dir, f"compare_{idx:02d}_{emo_name}.jpg")
    canvas.save(out_file, quality=92)
    print(f"Salvo comparativo: {out_file}")

    # Guardar para a master grid (versão reduzida)
    thumb_w, thumb_h = 240, 240
    t_ref = img_ref.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
    t_3d = img_3d.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
    individual_pairs.append((idx, emo_name, t_ref, t_3d))

# Criar Master Comparison Grid (6 colunas x 3 linhas de pares)
# Cada célula tem Ref + 3D (480x280)
cell_w = 480
cell_h = 290
grid_w = cell_w * 3
grid_h = cell_h * 6 + 70

master_canvas = Image.new("RGB", (grid_w, grid_h), (20, 22, 25))
draw_m = ImageDraw.Draw(master_canvas)

draw_m.text((25, 20), "WARRIOR GIRL 3D vs REFERENCIA FACS — GRADE COMPARATIVA COMPLETA (18 EMOCOES)", fill=(255, 215, 0))

for i, (idx, emo_name, t_ref, t_3d) in enumerate(individual_pairs):
    row = i // 3
    col = i % 3
    x = col * cell_w + 10
    y = row * cell_h + 60

    # Borda da célula
    draw_m.rectangle([x, y, x + cell_w - 20, y + cell_h - 15], outline=(60, 65, 75), width=1)

    # Imagens lado a lado
    master_canvas.paste(t_ref, (x + 5, y + 25))
    master_canvas.paste(t_3d, (x + 240, y + 25))

    # Título da célula
    draw_m.text((x + 8, y + 6), f"#{idx:02d} {emo_name.replace('_', ' ')}", fill=(255, 255, 255))
    draw_m.text((x + 8, y + 268), "Ref", fill=(150, 230, 150))
    draw_m.text((x + 245, y + 268), "Warrior Girl 3D", fill=(120, 210, 255))

master_out = r"D:\isabella-desktop\assets\renders\warrior_girl\master_comparison_grid.jpg"
master_canvas.save(master_out, quality=90)
print(f"\nMaster Grid salva com sucesso em {master_out}!")
