import os
import shutil
import time
from gradio_client import Client, handle_file

INPUT_IMAGE = r"D:\isabella-desktop\assets\references\isabella_reference_bar_4x.png"
OUTPUT_DIR = r"D:\isabella-desktop\assets\models"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PLY = os.path.join(OUTPUT_DIR, "isabella_hd_4x_1m.ply")

print("=======================================================")
print("  RECONSTRUCAO 3DGS COM IMAGEM 4X (1,048,576 SPLATS)    ")
print("=======================================================")
print(f"[1/3] Conectando ao cluster speridlabs/idol...")
t0 = time.time()
client = Client("speridlabs/idol")
print(f"      Conectado em {(time.time() - t0):.1f}s")

print(f"[2/3] Enviando imagem 4X para reconstrucao...")
print(f"      Parametros: 1,048,576 gaussianas | Steps=85 | CFG=3.5 | Mode=Real photo")
t_infer = time.time()
result = client.predict(
    image=handle_file(INPUT_IMAGE),
    mode="Real photo",
    steps=85,
    cfg_scale=3.5,
    rescale_t=3.0,
    seed=42,
    randomize=False,
    gaussians="1,048,576",
    api_name="/run"
)

ply_path = result[0]
print(f"      Inferencia concluida em {(time.time() - t_infer):.1f}s!")
print(f"[3/3] Copiando resultado para {OUTPUT_PLY}...")
shutil.copy(ply_path, OUTPUT_PLY)
size_mb = os.path.getsize(OUTPUT_PLY) / (1024 * 1024)
print(f"SUCESSO! Modelo salvo: {OUTPUT_PLY} ({size_mb:.2f} MB)")
