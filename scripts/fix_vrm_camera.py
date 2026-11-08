import bpy
import math

blend_path = r"D:\isabella-desktop\benchmarks_avatars\vrm\AliciaSolid_bench.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene
cam = bpy.data.objects.get('Camera')
# Frente da modelo: Y positivo
cam.location = (0.0, 1.10, 1.28)
cam.rotation_euler = (math.radians(90), 0, math.radians(180))

# Testar shape key de sorriso e olhos abertos
face_obj = bpy.data.objects.get('face')
if face_obj and face_obj.data.shape_keys:
    sks = face_obj.data.shape_keys.key_blocks
    # Joy
    if sks.get('target_25'):
        sks['target_25'].value = 0.8 # Olhos sorridentes
    if sks.get('target_38'):
        sks['target_38'].value = 0.9 # Boca sorridente

out_snap = r"D:\isabella-desktop\benchmarks_avatars\vrm\vrm_snapshot.png"
scene.render.filepath = out_snap
bpy.ops.render.render(write_still=True)
print(f"Novo snapshot frontal salvo em {out_snap}")
