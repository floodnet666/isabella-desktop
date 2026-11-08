import os
import urllib.request
import json

base_url = "https://raw.githubusercontent.com/guansss/pixi-live2d-display/master/test/assets/shizuku/"
target_dir = r"D:\isabella-desktop\benchmarks_avatars\live2d\shizuku"
os.makedirs(target_dir, exist_ok=True)

model_json_path = os.path.join(target_dir, "shizuku.model.json")
urllib.request.urlretrieve(base_url + "shizuku.model.json", model_json_path)
print("shizuku.model.json baixado!")

with open(model_json_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Baixar o .moc
moc_file = cfg.get("model")
if moc_file:
    urllib.request.urlretrieve(base_url + moc_file, os.path.join(target_dir, moc_file))
    print(f"{moc_file} baixado!")

# Baixar texturas
for tex in cfg.get("textures", []):
    tex_dest = os.path.join(target_dir, tex.replace("/", os.sep))
    os.makedirs(os.path.dirname(tex_dest), exist_ok=True)
    urllib.request.urlretrieve(base_url + tex, tex_dest)
    print(f"Textura {tex} baixada ({os.path.getsize(tex_dest)} bytes)!")

# Baixar physics se houver
if "physics" in cfg:
    phys = cfg["physics"]
    urllib.request.urlretrieve(base_url + phys, os.path.join(target_dir, phys))
    print(f"Physics {phys} baixado!")

# Baixar pose se houver
if "pose" in cfg:
    pose = cfg["pose"]
    urllib.request.urlretrieve(base_url + pose, os.path.join(target_dir, pose))
    print(f"Pose {pose} baixado!")

print("Modelo Live2D Shizuku baixado 100% com sucesso!")
