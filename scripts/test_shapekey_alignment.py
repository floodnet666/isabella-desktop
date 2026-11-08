import bpy
import bmesh
import math
from mathutils import Vector

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

scene = bpy.context.scene
mesh_obj = bpy.data.objects.get('Mesh_0')
arm_obj = bpy.data.objects.get('Armature_WarriorGirl')

# 1. Alinhar a pose da cabeça na Armature (corrigir o roll original de ~15° para ficar reta)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
head_pbone = arm_obj.pose.bones.get('head')
neck_pbone = arm_obj.pose.bones.get('neck')

# Limpar rotações anteriores
if head_pbone:
    head_pbone.rotation_mode = 'XYZ'
    # Compensar a inclinação da cabeça nativa para alinhamento frontal
    head_pbone.rotation_euler = (math.radians(-4), math.radians(14), math.radians(-3))

if neck_pbone:
    neck_pbone.rotation_mode = 'XYZ'
    neck_pbone.rotation_euler = (0, 0, 0)

bpy.ops.object.mode_set(mode='OBJECT')

# 2. Configurar Shape Keys na malha Mesh_0
if not mesh_obj.data.shape_keys:
    mesh_obj.shape_key_add(name="Basis")

basis = mesh_obj.data.shape_keys.key_blocks["Basis"]

# Função auxiliar para criar shape key com deslocamento ponderado por distância e gaussiana
def create_smooth_shapekey(name, deform_func):
    sk = mesh_obj.data.shape_keys.key_blocks.get(name)
    if not sk:
        sk = mesh_obj.shape_key_add(name=name)
    
    for idx, v in enumerate(mesh_obj.data.vertices):
        # Posição base
        orig_co = basis.data[idx].co
        # Aplica a função de deformação
        offset = deform_func(orig_co)
        sk.data[idx].co = orig_co + offset
    return sk

# Centros anatômicos identificados:
# Boca: x=0.0, y=-0.09, z=0.652
# Canto L: x=0.038, y=-0.075, z=0.653
# Canto R: x=-0.038, y=-0.075, z=0.653
# Sobrancelha L centro: x=0.040, y=-0.140, z=0.825
# Sobrancelha R centro: x=-0.040, y=-0.140, z=0.825
# Sobrancelhas meio: x=0.000, y=-0.145, z=0.820
# Nariz ponta: x=-0.014, y=-0.178, z=0.740
# Olho L: x=0.038, y=-0.135, z=0.780
# Olho R: x=-0.038, y=-0.135, z=0.780

# Função Sorriso (Joy / Smile)
def calc_smile(p):
    offset = Vector((0.0, 0.0, 0.0))
    # Cantos da boca sobem e alargam
    dist_l = ((p.x - 0.035)**2 + (p.y - (-0.08))**2 + (p.z - 0.65)**2)**0.5
    dist_r = ((p.x - (-0.035))**2 + (p.y - (-0.08))**2 + (p.z - 0.65)**2)**0.5
    
    r_mouth = 0.045
    if dist_l < r_mouth:
        w = (1.0 - dist_l / r_mouth)**2
        offset += Vector((0.010 * w, 0.006 * w, 0.022 * w))
    if dist_r < r_mouth:
        w = (1.0 - dist_r / r_mouth)**2
        offset += Vector((-0.010 * w, 0.006 * w, 0.022 * w))
    
    # Centro do lábio superior sobe suavemente
    dist_mid = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.655)**2)**0.5
    if dist_mid < 0.035 and p.z >= 0.65:
        w = (1.0 - dist_mid / 0.035)**2
        offset += Vector((0.0, 0.003 * w, 0.008 * w))
        
    # Bochechas sobem
    for cheek_x in [0.05, -0.05]:
        d_cheek = ((p.x - cheek_x)**2 + (p.y - (-0.10))**2 + (p.z - 0.70)**2)**0.5
        if d_cheek < 0.05:
            w = (1.0 - d_cheek / 0.05)**2
            offset += Vector((0.0, -0.003 * w, 0.012 * w))
            
    return offset

create_smooth_shapekey("Joy_Smile", calc_smile)

# Testar render da cabeça alinhada com e sem sorriso
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.display_settings.display_device = 'sRGB'
scene.view_settings.view_transform = 'Standard'

# Setup da câmera e iluminação
cam = bpy.data.objects.get('Camera')
cam.location = (-0.005, -0.75, 0.72)
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.lens = 85
scene.camera = cam

# Render 1: Neutro (todos shape keys 0)
for sk in mesh_obj.data.shape_keys.key_blocks:
    if sk.name != "Basis":
        sk.value = 0.0

out_neutral = r'D:\isabella-desktop\assets\renders\warrior_girl\test_aligned_neutral.png'
scene.render.filepath = out_neutral
bpy.ops.render.render(write_still=True)

# Render 2: Sorriso ativo
sk_smile = mesh_obj.data.shape_keys.key_blocks.get("Joy_Smile")
if sk_smile:
    sk_smile.value = 1.0

out_smile = r'D:\isabella-desktop\assets\renders\warrior_girl\test_aligned_smile.png'
scene.render.filepath = out_smile
bpy.ops.render.render(write_still=True)
print("Renders gerados com sucesso!")
