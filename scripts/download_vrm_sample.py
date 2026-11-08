import os
import urllib.request

url = "https://github.com/vrm-c/UniVRM/raw/master/Tests/Models/Alicia_vrm-0.51/AliciaSolid_vrm-0.51.vrm"
target_dir = r"D:\isabella-desktop\benchmarks_avatars\vrm"
dest = os.path.join(target_dir, "AliciaSolid.vrm")

print("Baixando modelo oficial VRM AliciaSolid...")
urllib.request.urlretrieve(url, dest)
size = os.path.getsize(dest)
print(f"VRM baixado com sucesso! Arquivo: {dest} ({size / 1024 / 1024:.2f} MB)")
