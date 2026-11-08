import bpy
import math
from mathutils import Vector

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

scene = bpy.context.scene
mesh_obj = bpy.data.objects.get('Mesh_0')
arm_obj = bpy.data.objects.get('Armature_WarriorGirl')

# Limpar modificadores duplicados de armature se houver
arm_mods = [m for m in mesh_obj.modifiers if m.type == 'ARMATURE']
if len(arm_mods) > 1:
    for m in arm_mods[1:]:
        mesh_obj.modifiers.remove(m)
arm_mods[0].object = arm_obj

# Testar pose do osso Head
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
head_bone = arm_obj.pose.bones.get('Head')
if head_bone:
    head_bone.rotation_mode = 'XYZ'
    # Inclinar para a esquerda e para baixo (ex: tristeza)
    head_bone.rotation_euler = (math.radians(10), math.radians(15), math.radians(-10))
    print(f"Osso Head rotacionado com sucesso: {head_bone.rotation_euler}")
else:
    print("ERRO: Osso Head nao encontrado!")

bpy.ops.object.mode_set(mode='OBJECT')

# Câmera e luz
cam = bpy.data.objects.get('Camera')
cam.location = (-0.005, -0.75, 0.72)
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.lens = 85
scene.camera = cam

out_path = r'D:\isabella-desktop\assets\renders\warrior_girl\test_head_rotation.png'
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f"Render salvo em {out_path}")
