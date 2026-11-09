import os
import urllib.request

base_url = "https://raw.githubusercontent.com/Live2D/CubismWebSamples/develop/Samples/Resources/Hiyori/"
target_dir = r"D:\isabella-desktop\benchmarks_avatars\live2d\Hiyori"
os.makedirs(os.path.join(target_dir, "Hiyori.2048"), exist_ok=True)
os.makedirs(os.path.join(target_dir, "motions"), exist_ok=True)

files = [
    "Hiyori.model3.json",
    "Hiyori.moc3",
    "Hiyori.physics3.json",
    "Hiyori.pose3.json",
    "Hiyori.cdi3.json",
    "Hiyori.2048/texture_00.png",
    "motions/Hiyori_m01.motion3.json",
    "motions/Hiyori_m02.motion3.json"
]

print("Baixando modelo Live2D oficial Hiyori...")
for f in files:
    url = base_url + f
    dest = os.path.join(target_dir, f.replace("/", os.sep))
    if not os.path.exists(dest):
        print(f"Baixando: {f}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"OK: {dest} ({os.path.getsize(dest)} bytes)")
        except Exception as e:
            print(f"Erro em {f}: {e}")
    else:
        print(f"Ja existe: {dest}")

print("Download do modelo Live2D concluido!")
