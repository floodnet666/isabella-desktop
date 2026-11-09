import json
import struct

vrm_path = r"D:\isabella-desktop\benchmarks_avatars\vrm\AliciaSolid.vrm"
with open(vrm_path, "rb") as f:
    magic, version, length = struct.unpack("<4sII", f.read(12))
    chunk_len, chunk_type = struct.unpack("<II", f.read(8))
    json_data = f.read(chunk_len).decode("utf-8")
    gltf = json.loads(json_data)

vrm_ext = gltf.get("extensions", {}).get("VRM", {})
groups = vrm_ext.get("blendShapeMaster", {}).get("blendShapeGroups", [])

print("=== MAPA DE BLENDSHAPES VRM FACS ===")
for g in groups:
    name = g.get("name")
    preset = g.get("presetName")
    binds = g.get("binds", [])
    print(f"Blendshape: '{name}' (Preset: {preset}), Binds: {binds}")
