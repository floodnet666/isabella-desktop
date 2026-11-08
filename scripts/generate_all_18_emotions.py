import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler

def setup_scene():
    blend_path = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # Render settings
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'

    # Background idêntico à referência (cinza claro suave de estúdio)
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    nodes.clear()
    node_out = nodes.new('ShaderNodeOutputWorld')
    node_bg = nodes.new('ShaderNodeBackground')
    node_bg.inputs['Color'].default_value = (0.83, 0.84, 0.83, 1.0)
    node_bg.inputs['Strength'].default_value = 0.95
    scene.world.node_tree.links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

    # Luzes de estúdio profissionais (Key, Fill, Rim)
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

    # Key light frontal superior direita
    key_data = bpy.data.lights.new('KeyArea', type='AREA')
    key_data.energy = 7.5
    key_data.size = 0.6
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new('KeyArea', key_data)
    scene.collection.objects.link(key_obj)
    key_obj.location = (0.22, -0.70, 1.10)
    key_obj.rotation_euler = (math.radians(55), math.radians(12), math.radians(15))

    # Fill light frontal esquerda
    fill_data = bpy.data.lights.new('FillArea', type='AREA')
    fill_data.energy = 4.2
    fill_data.size = 0.8
    fill_data.color = (0.95, 0.98, 1.0)
    fill_obj = bpy.data.objects.new('FillArea', fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = (-0.30, -0.65, 0.90)
    fill_obj.rotation_euler = (math.radians(50), math.radians(-15), math.radians(-20))

    # Câmera retrato 85mm
    cam = bpy.data.objects.get('Camera')
    if not cam:
        cam_data = bpy.data.cameras.new('Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 85
    cam.location = (-0.005, -0.78, 0.72)
    cam.rotation_euler = (math.radians(90), 0, 0)

    # Garantir que Mesh_0 tem modificador Armature único
    mesh_obj = bpy.data.objects.get('Mesh_0')
    arm_obj = bpy.data.objects.get('Armature_WarriorGirl')
    for m in list(mesh_obj.modifiers):
        if m.type == 'ARMATURE':
            mesh_obj.modifiers.remove(m)
    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = arm_obj

    return scene, mesh_obj, arm_obj

def build_shapekeys(mesh_obj):
    # Garantir Basis
    if not mesh_obj.data.shape_keys:
        mesh_obj.shape_key_add(name="Basis")
    basis = mesh_obj.data.shape_keys.key_blocks["Basis"]

    def add_sk(name, fn):
        sk = mesh_obj.data.shape_keys.key_blocks.get(name)
        if not sk:
            sk = mesh_obj.shape_key_add(name=name)
        for idx, v in enumerate(mesh_obj.data.vertices):
            orig = basis.data[idx].co
            disp = fn(orig)
            sk.data[idx].co = orig + disp
        return sk

    # 1. AU12: Sorriso Aberto / Harmônico
    def sk_smile(p):
        d = Vector((0.0, 0.0, 0.0))
        # Cantos labiais
        dl = ((p.x - 0.038)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        dr = ((p.x - (-0.038))**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        if dl < 0.045:
            w = (1.0 - dl / 0.045)**2
            d += Vector((0.012 * w, 0.008 * w, 0.024 * w))
        if dr < 0.045:
            w = (1.0 - dr / 0.045)**2
            d += Vector((-0.012 * w, 0.008 * w, 0.024 * w))
        # Bochechas elevadas
        for cx in [0.045, -0.045]:
            dc = ((p.x - cx)**2 + (p.y - (-0.11))**2 + (p.z - 0.70)**2)**0.5
            if dc < 0.05:
                w = (1.0 - dc / 0.05)**2
                d += Vector((0.0, -0.004 * w, 0.015 * w))
        return d
    add_sk("AU12_Smile", sk_smile)

    # 2. AU15: Tristeza / Cantos da Boca Baixos (Depressor)
    def sk_frown_mouth(p):
        d = Vector((0.0, 0.0, 0.0))
        dl = ((p.x - 0.038)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        dr = ((p.x - (-0.038))**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        if dl < 0.042:
            w = (1.0 - dl / 0.042)**2
            d += Vector((-0.005 * w, -0.003 * w, -0.026 * w))
        if dr < 0.042:
            w = (1.0 - dr / 0.042)**2
            d += Vector((0.005 * w, -0.003 * w, -0.026 * w))
        # Centro do lábio inferior puxado
        dm = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.638)**2)**0.5
        if dm < 0.035:
            w = (1.0 - dm / 0.035)**2
            d += Vector((0.0, -0.002 * w, -0.015 * w))
        return d
    add_sk("AU15_MouthFrown", sk_frown_mouth)

    # 3. AU26: Abertura da Boca / Mandíbula (Jaw Drop)
    def sk_jaw_drop(p):
        d = Vector((0.0, 0.0, 0.0))
        # Vértices do lábio inferior e queixo (z < 0.655, y < -0.06, |x| < 0.05)
        if p.z < 0.655 and p.y < -0.06 and abs(p.x) < 0.055:
            dist = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.64)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.08)
            # Mandíbula desce e recua ligeiramente para abrir a boca
            d += Vector((0.0, 0.015 * w, -0.045 * w))
        # Lábio superior sobe suavemente para expor dentes superiores
        if 0.655 <= p.z <= 0.68 and p.y < -0.07 and abs(p.x) < 0.04:
            dist = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.665)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.04)
            d += Vector((0.0, -0.005 * w, 0.018 * w))
        return d
    add_sk("AU26_JawOpen", sk_jaw_drop)

    # 4. AU20: Lábios Esticados Horizontais (Raiva / Dentes Cerrados)
    def sk_lip_stretch(p):
        d = Vector((0.0, 0.0, 0.0))
        # Lábios abrem horizontalmente expondo dentes
        if 0.63 <= p.z <= 0.68 and p.y < -0.07 and abs(p.x) < 0.05:
            dist = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.652)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.06)
            sign_x = 1.0 if p.x > 0 else -1.0
            d += Vector((sign_x * 0.016 * w, 0.008 * w, (0.012 if p.z > 0.652 else -0.015) * w))
        return d
    add_sk("AU20_LipStretch", sk_lip_stretch)

    # 5. AU4: Sobrancelhas Baixas / Franzidas (Raiva / Foco)
    def sk_brow_frown(p):
        d = Vector((0.0, 0.0, 0.0))
        # Sobrancelhas (z entre 0.79 e 0.86, y < -0.11, |x| < 0.07)
        if 0.79 <= p.z <= 0.86 and p.y < -0.11 and abs(p.x) < 0.07:
            # Puxa para baixo e converge para o centro X=0
            dist = (p.x**2 + (p.y - (-0.14))**2 + (p.z - 0.825)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.07)
            sign_x = -1.0 if p.x > 0 else 1.0
            d += Vector((sign_x * 0.012 * w, -0.006 * w, -0.028 * w))
        return d
    add_sk("AU4_BrowFrown", sk_brow_frown)

    # 6. AU1+AU2: Sobrancelhas Altas (Surpresa / Choque)
    def sk_brow_surprise(p):
        d = Vector((0.0, 0.0, 0.0))
        if 0.79 <= p.z <= 0.86 and p.y < -0.11 and abs(p.x) < 0.075:
            dist = (p.x**2 + (p.y - (-0.14))**2 + (p.z - 0.825)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.08)
            d += Vector((0.0, -0.004 * w, 0.034 * w))
        return d
    add_sk("AU1_2_BrowSurprise", sk_brow_surprise)

    # 7. AU1: Sobrancelhas Tristes (Centro erguido em arco melancólico)
    def sk_brow_sad(p):
        d = Vector((0.0, 0.0, 0.0))
        if 0.79 <= p.z <= 0.86 and p.y < -0.11 and abs(p.x) < 0.07:
            dist_mid = (p.x**2 + (p.y - (-0.145))**2 + (p.z - 0.82)**2)**0.5
            if dist_mid < 0.035:
                w = (1.0 - dist_mid / 0.035)**2
                d += Vector((0.0, -0.005 * w, 0.030 * w)) # Centro sobe
            dist_outer = (abs(p.x) - 0.045)
            if dist_outer > 0:
                d += Vector((0.0, 0.0, -0.018 * min(1.0, dist_outer / 0.02))) # Laterais descem
        return d
    add_sk("AU1_BrowSadness", sk_brow_sad)

    # 8. Smirk Esquerdo (Desdém unilateral)
    def sk_smirk_l(p):
        d = Vector((0.0, 0.0, 0.0))
        dl = ((p.x - 0.038)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        if dl < 0.045:
            w = (1.0 - dl / 0.045)**2
            d += Vector((0.015 * w, 0.010 * w, 0.032 * w))
        # Bochecha esquerda sobe
        dc = ((p.x - 0.045)**2 + (p.y - (-0.11))**2 + (p.z - 0.70)**2)**0.5
        if dc < 0.05:
            w = (1.0 - dc / 0.05)**2
            d += Vector((0.0, -0.005 * w, 0.018 * w))
        return d
    add_sk("Smirk_Left", sk_smirk_l)

    # 9. AU9: Nariz Franzido / Nojo (Sneer)
    def sk_sneer(p):
        d = Vector((0.0, 0.0, 0.0))
        # Nariz e lábio superior sobem
        if 0.65 <= p.z <= 0.77 and p.y < -0.10 and abs(p.x) < 0.035:
            dist = (p.x**2 + (p.y - (-0.16))**2 + (p.z - 0.74)**2)**0.5
            w = max(0.0, 1.0 - dist / 0.06)
            d += Vector((0.0, -0.008 * w, 0.026 * w))
        return d
    add_sk("AU9_Sneer", sk_sneer)

    # 10. Eyes Wide (Olhos arregalados)
    def sk_eyes_wide(p):
        d = Vector((0.0, 0.0, 0.0))
        if 0.75 <= p.z <= 0.81 and p.y < -0.12 and abs(p.x) > 0.015 and abs(p.x) < 0.065:
            w = 1.0 if p.z > 0.78 else -0.6
            d += Vector((0.0, -0.003, 0.012 * w))
        return d
    add_sk("Eyes_Wide", sk_eyes_wide)

    # 11. Eyes Squint (Olhos apertados / Foco)
    def sk_eyes_squint(p):
        d = Vector((0.0, 0.0, 0.0))
        if 0.75 <= p.z <= 0.81 and p.y < -0.12 and abs(p.x) > 0.015 and abs(p.x) < 0.065:
            w = -1.0 if p.z > 0.78 else 0.8
            d += Vector((0.0, 0.002, 0.014 * w))
        return d
    add_sk("Eyes_Squint", sk_eyes_squint)

    print("Todas as 11 Shape Keys fundamentais criadas com sucesso!")

# Dicionário das 18 Emoções com Parâmetros Completos
EMOTIONS_CONFIG = [
    {
        "id": 1,
        "ref": "Screenshot 2024-11-26 104001.png",
        "name": "Perfil_Rosnado_Furioso",
        "pose": {"yaw": 82, "pitch": 6, "roll": 2, "neck_pitch": 4},
        "shapekeys": {"AU4_BrowFrown": 1.0, "AU20_LipStretch": 1.0, "AU9_Sneer": 0.8, "Eyes_Squint": 0.7},
        "cam": {"x": 0.0, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 2,
        "ref": "Screenshot 2024-11-26 104108.png",
        "name": "34_Grito_de_Guerra",
        "pose": {"yaw": 52, "pitch": -12, "roll": 5, "neck_pitch": -6},
        "shapekeys": {"AU26_JawOpen": 1.0, "AU4_BrowFrown": 0.8, "AU1_2_BrowSurprise": 0.4, "Eyes_Wide": 0.6},
        "cam": {"x": -0.02, "y": -0.80, "z": 0.73, "lens": 85}
    },
    {
        "id": 3,
        "ref": "Screenshot 2024-11-26 104205.png",
        "name": "Frontal_Grito_Furioso",
        "pose": {"yaw": 0, "pitch": 6, "roll": 0, "neck_pitch": 4},
        "shapekeys": {"AU26_JawOpen": 1.0, "AU4_BrowFrown": 1.0, "AU9_Sneer": 0.5, "Eyes_Wide": 0.8},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 4,
        "ref": "Screenshot 2024-11-26 104213.png",
        "name": "Frontal_Raiva_Dentes_Cerrados",
        "pose": {"yaw": 0, "pitch": 5, "roll": 0, "neck_pitch": 3},
        "shapekeys": {"AU20_LipStretch": 1.0, "AU4_BrowFrown": 1.0, "AU9_Sneer": 0.7, "Eyes_Squint": 0.8},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 5,
        "ref": "Screenshot 2024-11-26 104224.png",
        "name": "Frontal_Desgosto_Magoada",
        "pose": {"yaw": 2, "pitch": -2, "roll": 4, "neck_pitch": 0},
        "shapekeys": {"AU1_BrowSadness": 1.0, "AU15_MouthFrown": 1.0, "Eyes_Wide": 0.4},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 6,
        "ref": "Screenshot 2024-11-26 104233.png",
        "name": "Frontal_Espanto_Choque",
        "pose": {"yaw": 0, "pitch": -4, "roll": 0, "neck_pitch": -2},
        "shapekeys": {"AU1_2_BrowSurprise": 1.0, "AU26_JawOpen": 0.55, "Eyes_Wide": 1.0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 7,
        "ref": "Screenshot 2024-11-26 104242.png",
        "name": "Frontal_Desprezo_Desdem",
        "pose": {"yaw": -5, "pitch": 4, "roll": -6, "neck_pitch": 0},
        "shapekeys": {"Smirk_Left": 0.8, "AU4_BrowFrown": 0.7, "AU9_Sneer": 0.6, "Eyes_Squint": 0.6},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 8,
        "ref": "Screenshot 2024-11-26 104249.png",
        "name": "34_Nojo_Intenso",
        "pose": {"yaw": 38, "pitch": 6, "roll": 4, "neck_pitch": 2},
        "shapekeys": {"AU9_Sneer": 1.0, "AU20_LipStretch": 0.7, "AU4_BrowFrown": 0.8, "Eyes_Squint": 0.7},
        "cam": {"x": -0.015, "y": -0.80, "z": 0.72, "lens": 85}
    },
    {
        "id": 9,
        "ref": "Screenshot 2024-11-26 104255.png",
        "name": "Frontal_Irritacao_Ameaca",
        "pose": {"yaw": 0, "pitch": 10, "roll": 0, "neck_pitch": 4},
        "shapekeys": {"AU4_BrowFrown": 1.0, "AU15_MouthFrown": 0.6, "Eyes_Squint": 0.9},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 10,
        "ref": "Screenshot 2024-11-26 104302.png",
        "name": "Frontal_Desconfiada_Olhar_Lateral",
        "pose": {"yaw": 0, "pitch": 0, "roll": 0, "neck_pitch": 0},
        "shapekeys": {"AU4_BrowFrown": 0.4, "AU1_2_BrowSurprise": 0.2, "Eyes_Squint": 0.3},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 11,
        "ref": "Screenshot 2024-11-26 104309.png",
        "name": "Frontal_Cetica_Questionadora",
        "pose": {"yaw": -4, "pitch": 2, "roll": 9, "neck_pitch": 0},
        "shapekeys": {"AU1_2_BrowSurprise": 0.5, "AU4_BrowFrown": 0.3, "AU15_MouthFrown": 0.4},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 12,
        "ref": "Screenshot 2024-11-26 104322.png",
        "name": "Frontal_Emburrada_Furia_Contida",
        "pose": {"yaw": 0, "pitch": 7, "roll": 0, "neck_pitch": 3},
        "shapekeys": {"AU4_BrowFrown": 0.9, "AU15_MouthFrown": 0.8, "Eyes_Squint": 0.5},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 13,
        "ref": "Screenshot 2024-11-26 104334.png",
        "name": "Frontal_Tristeza_Dengo",
        "pose": {"yaw": 2, "pitch": -3, "roll": 11, "neck_pitch": 0},
        "shapekeys": {"AU1_BrowSadness": 1.0, "AU15_MouthFrown": 1.0, "Eyes_Squint": 0.3},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 14,
        "ref": "Screenshot 2024-11-26 104340.png",
        "name": "Perfil_Neutro",
        "pose": {"yaw": 88, "pitch": 0, "roll": 0, "neck_pitch": 0},
        "shapekeys": {},
        "cam": {"x": 0.0, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 15,
        "ref": "Screenshot 2024-11-26 104346.png",
        "name": "Frontal_Sorriso_Contido",
        "pose": {"yaw": 0, "pitch": 0, "roll": 0, "neck_pitch": 0},
        "shapekeys": {"AU12_Smile": 0.45},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 16,
        "ref": "Screenshot 2024-11-26 104352.png",
        "name": "Frontal_Pensativa_Olhar_Superior",
        "pose": {"yaw": 0, "pitch": -16, "roll": 0, "neck_pitch": -8},
        "shapekeys": {"AU1_2_BrowSurprise": 0.4, "Eyes_Wide": 0.5, "AU12_Smile": 0.2},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 17,
        "ref": "Screenshot 2024-11-26 104414.png",
        "name": "Frontal_Sorriso_Maroto_Provocante",
        "pose": {"yaw": 2, "pitch": 2, "roll": 2, "neck_pitch": 0},
        "shapekeys": {"AU12_Smile": 0.95, "AU20_LipStretch": 0.4, "Smirk_Left": 0.4, "AU1_2_BrowSurprise": 0.3},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    },
    {
        "id": 18,
        "ref": "Screenshot 2024-11-26 104423.png",
        "name": "Frontal_Sorriso_Simpatico_Gentil",
        "pose": {"yaw": 0, "pitch": 0, "roll": 0, "neck_pitch": 0},
        "shapekeys": {"AU12_Smile": 0.80},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "lens": 85}
    }
]

def render_all():
    scene, mesh_obj, arm_obj = setup_scene()
    build_shapekeys(mesh_obj)

    out_dir = r"D:\isabella-desktop\assets\renders\warrior_girl\emotions"
    os.makedirs(out_dir, exist_ok=True)

    head_pbone = arm_obj.pose.bones.get('Head')
    neck_pbone = arm_obj.pose.bones.get('Neck')

    cam = bpy.data.objects.get('Camera')

    print(f"\nIniciando renderizacao das {len(EMOTIONS_CONFIG)} emocoes...")

    for cfg in EMOTIONS_CONFIG:
        idx = cfg["id"]
        name = cfg["name"]
        pose = cfg["pose"]
        sk_dict = cfg["shapekeys"]
        cam_cfg = cfg["cam"]

        # 1. Resetar todas as shape keys
        for sk in mesh_obj.data.shape_keys.key_blocks:
            if sk.name != "Basis":
                sk.value = 0.0

        # 2. Aplicar shape keys da emoção
        for sk_name, val in sk_dict.items():
            sk = mesh_obj.data.shape_keys.key_blocks.get(sk_name)
            if sk:
                sk.value = val

        # 3. Aplicar pose óssea cervical
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        
        # O modelo guerreira tem uma inclinação nativa no mesh de ~14° de Roll.
        # Nós compensamos para que yaw=0, pitch=0, roll=0 fique perfeitamente alinhado.
        base_head_roll = 14.0
        base_head_pitch = -4.0
        
        yaw_rad = math.radians(pose.get("yaw", 0))
        pitch_rad = math.radians(pose.get("pitch", 0) + base_head_pitch)
        roll_rad = math.radians(pose.get("roll", 0) + base_head_roll)
        
        if head_pbone:
            head_pbone.rotation_mode = 'XYZ'
            head_pbone.rotation_euler = (pitch_rad, roll_rad, yaw_rad)

        if neck_pbone:
            neck_pitch = math.radians(pose.get("neck_pitch", 0))
            neck_pbone.rotation_mode = 'XYZ'
            neck_pbone.rotation_euler = (neck_pitch, 0, 0)

        bpy.ops.object.mode_set(mode='OBJECT')

        # 4. Configurar câmera
        cam.location = (cam_cfg["x"], cam_cfg["y"], cam_cfg["z"])
        cam.data.lens = cam_cfg["lens"]

        # 5. Renderizar
        render_path = os.path.join(out_dir, f"emotion_{idx:02d}_{name}.png")
        scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)
        print(f"[{idx}/18] Renderizado: {name} -> {render_path}")

    # Salvar blend final
    blend_final = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
    bpy.ops.wm.save_as_mainfile(filepath=blend_final)
    print(f"\nConcluido! Todas as 18 emocoes renderizadas e blend salvo em {blend_final}")

if __name__ == '__main__':
    render_all()
