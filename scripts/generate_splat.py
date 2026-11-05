import os
import shutil
from gradio_client import Client, handle_file

INPUT_IMAGE = r"D:\isabella-desktop\assets\references\isabella_portrait.png"
OUTPUT_DIR = r"D:\isabella-desktop\assets\models"
OUTPUT_PLY = os.path.join(OUTPUT_DIR, "isabella_portrait.ply")

print(f"[1/3] Conectando ao pipeline speridlabs/idol...")
client = Client("speridlabs/idol")

print(f"[2/3] Enviando {INPUT_IMAGE} para inferencia 3DGS (262,144 gaussianas)...")
result = client.predict(
    image=handle_file(INPUT_IMAGE),
    mode="Real photo",
    steps=50,
    cfg_scale=3.0,
    rescale_t=3.0,
    seed=42,
    randomize=False,
    gaussians="262,144",
    api_name="/run"
)

ply_path = result[0]
print(f"[3/3] Arquivo .ply gerado em cache: {ply_path}")
shutil.copy(ply_path, OUTPUT_PLY)
size_mb = os.path.getsize(OUTPUT_PLY) / (1024 * 1024)
print(f"Sucesso! Salvo em: {OUTPUT_PLY} ({size_mb:.2f} MB)")
