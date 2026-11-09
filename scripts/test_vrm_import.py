import bpy
import os

vrm_path = r"D:\isabella-desktop\benchmarks_avatars\vrm\AliciaSolid.vrm"
# No Blender, o importador gltf aceita .glb e .gltf
glb_temp = r"D:\isabella-desktop\benchmarks_avatars\vrm\AliciaSolid.glb"
if not os.path.exists(glb_temp):
    import shutil
    shutil.copy(vrm_path, glb_temp)

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_temp)

print("=== OBJETOS IMPORTADOS DO VRM ===")
for obj in bpy.data.objects:
    print(f"Obj: {obj.name}, Tipo: {obj.type}")
    if obj.type == 'MESH' and obj.data.shape_keys:
        print(f"  Shape keys em {obj.name}: {[kb.name for kb in obj.data.shape_keys.key_blocks[:10]]}")
