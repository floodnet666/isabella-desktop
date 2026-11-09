import bpy
import math
import bmesh
from mathutils import Vector

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

scene = bpy.context.scene
mesh_obj = bpy.data.objects.get('Mesh_0')
arm_obj = bpy.data.objects.get('Armature_WarriorGirl')

# Remover objetos velhos de dentes se existirem
for name in ['Teeth_Upper', 'Teeth_Lower', 'Mouth_Interior']:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

# 1. Criar Arcada Superior (Teeth_Upper)
# Um arco curvo de dentes limpos
bm = bmesh.new()
# Criar 8 dentes superiores em arco
radius_x = 0.024
radius_y = 0.015
center_z = 0.660
center_y = -0.088

# Criar geometria dos dentes superiores
for i in range(8):
    angle = math.pi * (0.15 + 0.70 * (i / 7.0)) # arco frontal
    x = radius_x * math.cos(angle)
    y = center_y + radius_y * (math.sin(angle) - 1.0) * 0.5
    z = center_z
    
    # Criar um dente estilizado (prisma)
    bmesh.ops.create_cube(bm, size=0.005)
    # Escalar para parecer incisivo/canino
    for v in bm.verts[-8:]:
        v.co.x = v.co.x * 0.7 + x
        v.co.y = v.co.y * 0.6 + y
        v.co.z = v.co.z * 1.2 + z

mesh_teeth_up = bpy.data.meshes.new("Teeth_Upper_Mesh")
bm.to_mesh(mesh_teeth_up)
bm.free()

teeth_up_obj = bpy.data.objects.new("Teeth_Upper", mesh_teeth_up)
scene.collection.objects.link(teeth_up_obj)

# Material dentes brancos com esmalte sutil
mat_teeth = bpy.data.materials.new(name="Teeth_Material")
mat_teeth.use_nodes = True
bsdf = mat_teeth.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.95, 0.94, 0.92, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.15
teeth_up_obj.data.materials.append(mat_teeth)

# Parentar com a cabeça
teeth_up_obj.parent = arm_obj
teeth_up_obj.parent_type = 'BONE'
teeth_up_obj.parent_bone = 'Head'

# 2. Criar Arcada Inferior (Teeth_Lower)
bm_low = bmesh.new()
center_z_low = 0.642
for i in range(8):
    angle = math.pi * (0.15 + 0.70 * (i / 7.0))
    x = radius_x * 0.95 * math.cos(angle)
    y = (center_y + 0.002) + radius_y * (math.sin(angle) - 1.0) * 0.5
    z = center_z_low
    bmesh.ops.create_cube(bm_low, size=0.0045)
    for v in bm_low.verts[-8:]:
        v.co.x = v.co.x * 0.7 + x
        v.co.y = v.co.y * 0.6 + y
        v.co.z = v.co.z * 1.1 + z

mesh_teeth_low = bpy.data.meshes.new("Teeth_Lower_Mesh")
bm_low.to_mesh(mesh_teeth_low)
bm_low.free()

teeth_low_obj = bpy.data.objects.new("Teeth_Lower", mesh_teeth_low)
scene.collection.objects.link(teeth_low_obj)
teeth_low_obj.data.materials.append(mat_teeth)

teeth_low_obj.parent = arm_obj
teeth_low_obj.parent_type = 'BONE'
teeth_low_obj.parent_bone = 'Head'

# 3. Criar Fundo Escuro da Boca (Mouth_Interior)
bm_cav = bmesh.new()
bmesh.ops.create_uvsphere(bm_cav, u_segments=12, v_segments=8, radius=0.025)
for v in bm_cav.verts:
    v.co.x = v.co.x * 0.9
    v.co.y = v.co.y * 0.6 + (center_y + 0.02)
    v.co.z = v.co.z * 0.7 + center_z - 0.005
mesh_cav = bpy.data.meshes.new("Mouth_Interior_Mesh")
bm_cav.to_mesh(mesh_cav)
bm_cav.free()

cav_obj = bpy.data.objects.new("Mouth_Interior", mesh_cav)
scene.collection.objects.link(cav_obj)

mat_cav = bpy.data.materials.new(name="Mouth_Interior_Mat")
mat_cav.use_nodes = True
bsdf_cav = mat_cav.node_tree.nodes.get('Principled BSDF')
if bsdf_cav:
    bsdf_cav.inputs['Base Color'].default_value = (0.12, 0.02, 0.03, 1.0) # Vermelho escuro / sombra
    bsdf_cav.inputs['Roughness'].default_value = 0.7
cav_obj.data.materials.append(mat_cav)

cav_obj.parent = arm_obj
cav_obj.parent_type = 'BONE'
cav_obj.parent_bone = 'Head'

# Salvar o blend atualizado
blend_out = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print(f"Salvo modelo com dentes e cavidade em {blend_out}")
