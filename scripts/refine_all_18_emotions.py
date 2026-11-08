import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler

def setup_scene():
    blend_path = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'

    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    nodes.clear()
    node_out = nodes.new('ShaderNodeOutputWorld')
    node_bg = nodes.new('ShaderNodeBackground')
    node_bg.inputs['Color'].default_value = (0.83, 0.84, 0.83, 1.0)
    node_bg.inputs['Strength'].default_value = 0.95
    scene.world.node_tree.links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

    # Key light estúdio
    key_data = bpy.data.lights.new('KeyArea', type='AREA')
    key_data.energy = 7.5
    key_data.size = 0.6
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new('KeyArea', key_data)
    scene.collection.objects.link(key_obj)
    key_obj.location = (0.22, -0.70, 1.10)
    key_obj.rotation_euler = (math.radians(55), math.radians(12), math.radians(15))

    # Fill light estúdio
    fill_data = bpy.data.lights.new('FillArea', type='AREA')
    fill_data.energy = 4.2
    fill_data.size = 0.8
    fill_data.color = (0.95, 0.98, 1.0)
    fill_obj = bpy.data.objects.new('FillArea', fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = (-0.30, -0.65, 0.90)
    fill_obj.rotation_euler = (math.radians(50), math.radians(-15), math.radians(-20))

    cam = bpy.data.objects.get('Camera')
    if not cam:
        cam_data = bpy.data.cameras.new('Camera')
        cam = bpy.data.objects.new('Camera', cam_data)
        scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 85

    mesh_obj = bpy.data.objects.get('Mesh_0')
    arm_obj = bpy.data.objects.get('Armature_WarriorGirl')
    
    # Posicionar os dentes exatamente na linha frontal da boca aberta
    teeth_up = bpy.data.objects.get('Teeth_Upper')
    teeth_low = bpy.data.objects.get('Teeth_Lower')
    mouth_cav = bpy.data.objects.get('Mouth_Interior')
    
    if teeth_up:
        teeth_up.location = Vector((-0.005, -0.016, 0.002))
    if teeth_low:
        teeth_low.location = Vector((-0.005, -0.014, -0.010))
    if mouth_cav:
        mouth_cav.location = Vector((-0.005, -0.005, -0.005))

    return scene, mesh_obj, arm_obj

def build_smooth_shapekeys(mesh_obj):
    if mesh_obj.data.shape_keys:
        for kb in list(mesh_obj.data.shape_keys.key_blocks):
            if kb.name != "Basis":
                mesh_obj.shape_key_remove(kb)
    else:
        mesh_obj.shape_key_add(name="Basis")

    basis = mesh_obj.data.shape_keys.key_blocks["Basis"]

    def add_sk(name, fn):
        sk = mesh_obj.shape_key_add(name=name)
        for idx, v in enumerate(mesh_obj.data.vertices):
            orig = basis.data[idx].co
            disp = fn(orig)
            sk.data[idx].co = orig + disp
        return sk

    # 1. AU12: Sorriso Harmônico
    def sk_smile(p):
        d = Vector((0.0, 0.0, 0.0))
        for side, cx in [("L", 0.038), ("R", -0.038)]:
            dist = ((p.x - cx)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
            if dist < 0.045:
                w = (1.0 - dist / 0.045)**2
                sign_x = 1.0 if side == "L" else -1.0
                d += Vector((sign_x * 0.014 * w, 0.007 * w, 0.026 * w))
        for cx in [0.045, -0.045]:
            dc = ((p.x - cx)**2 + (p.y - (-0.11))**2 + (p.z - 0.70)**2)**0.5
            if dc < 0.05:
                w = (1.0 - dc / 0.05)**2
                d += Vector((0.0, -0.004 * w, 0.015 * w))
        return d
    add_sk("AU12_Smile", sk_smile)

    # 2. AU15: Tristeza / Cantos da Boca Baixos
    def sk_frown_mouth(p):
        d = Vector((0.0, 0.0, 0.0))
        for side, cx in [("L", 0.038), ("R", -0.038)]:
            dist = ((p.x - cx)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
            if dist < 0.045:
                w = (1.0 - dist / 0.045)**2
                sign_x = -1.0 if side == "L" else 1.0
                d += Vector((sign_x * 0.005 * w, -0.003 * w, -0.028 * w))
        dm = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.638)**2)**0.5
        if dm < 0.038:
            w = (1.0 - dm / 0.038)**2
            d += Vector((0.0, -0.003 * w, -0.018 * w))
        return d
    add_sk("AU15_MouthFrown", sk_frown_mouth)

    # 3. AU26: Abertura Dramática de Boca / Mandíbula (Grito / Choque)
    def sk_jaw_drop(p):
        d = Vector((0.0, 0.0, 0.0))
        # Mandíbula / lábio inferior desce profundamente
        dist_low = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.640)**2)**0.5
        if dist_low < 0.085 and p.z <= 0.655:
            w = (1.0 - dist_low / 0.085)**2
            d += Vector((0.0, 0.022 * w, -0.065 * w))
        # Lábio superior sobe para revelar arcada
        dist_up = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.665)**2)**0.5
        if dist_up < 0.050 and p.z > 0.655:
            w = (1.0 - dist_up / 0.050)**2
            d += Vector((0.0, -0.006 * w, 0.026 * w))
        return d
    add_sk("AU26_JawOpen", sk_jaw_drop)

    # 4. AU20: Lábios Esticados Horizontais (Raiva Dentes Cerrados)
    def sk_lip_stretch(p):
        d = Vector((0.0, 0.0, 0.0))
        dist = (p.x**2 + (p.y - (-0.09))**2 + (p.z - 0.652)**2)**0.5
        if dist < 0.065:
            w = (1.0 - dist / 0.065)**2
            sign_x = 1.0 if p.x > 0 else -1.0
            z_dir = 0.016 if p.z > 0.652 else -0.018
            d += Vector((sign_x * 0.018 * w, 0.008 * w, z_dir * w))
        return d
    add_sk("AU20_LipStretch", sk_lip_stretch)

    # 5. AU4: Sobrancelhas Franzidas (Raiva / Foco)
    def sk_brow_frown(p):
        d = Vector((0.0, 0.0, 0.0))
        for side, bx in [("L", 0.035), ("R", -0.035)]:
            dist = ((p.x - bx)**2 + (p.y - (-0.14))**2 + (p.z - 0.825)**2)**0.5
            if dist < 0.055:
                w = (1.0 - dist / 0.055)**2
                sign_x = -1.0 if side == "L" else 1.0
                d += Vector((sign_x * 0.010 * w, -0.004 * w, -0.025 * w))
        dm = (p.x**2 + (p.y - (-0.145))**2 + (p.z - 0.820)**2)**0.5
        if dm < 0.038:
            w = (1.0 - dm / 0.038)**2
            d += Vector((0.0, -0.005 * w, -0.022 * w))
        return d
    add_sk("AU4_BrowFrown", sk_brow_frown)

    # 6. AU1+AU2: Sobrancelhas Altas (Surpresa / Choque)
    def sk_brow_surprise(p):
        d = Vector((0.0, 0.0, 0.0))
        for bx in [0.040, -0.040, 0.0]:
            dist = ((p.x - bx)**2 + (p.y - (-0.14))**2 + (p.z - 0.825)**2)**0.5
            if dist < 0.065:
                w = (1.0 - dist / 0.065)**2
                d += Vector((0.0, -0.004 * w, 0.034 * w))
        return d
    add_sk("AU1_2_BrowSurprise", sk_brow_surprise)

    # 7. AU1: Sobrancelhas Tristes (Melancolia)
    def sk_brow_sad(p):
        d = Vector((0.0, 0.0, 0.0))
        dm = (p.x**2 + (p.y - (-0.145))**2 + (p.z - 0.820)**2)**0.5
        if dm < 0.042:
            w = (1.0 - dm / 0.042)**2
            d += Vector((0.0, -0.005 * w, 0.032 * w))
        for bx in [0.055, -0.055]:
            dist = ((p.x - bx)**2 + (p.y - (-0.135))**2 + (p.z - 0.825)**2)**0.5
            if dist < 0.038:
                w = (1.0 - dist / 0.038)**2
                d += Vector((0.0, 0.0, -0.016 * w))
        return d
    add_sk("AU1_BrowSadness", sk_brow_sad)

    # 8. Smirk Esquerdo
    def sk_smirk_l(p):
        d = Vector((0.0, 0.0, 0.0))
        dist = ((p.x - 0.038)**2 + (p.y - (-0.08))**2 + (p.z - 0.653)**2)**0.5
        if dist < 0.045:
            w = (1.0 - dist / 0.045)**2
            d += Vector((0.015 * w, 0.008 * w, 0.032 * w))
        dc = ((p.x - 0.045)**2 + (p.y - (-0.11))**2 + (p.z - 0.70)**2)**0.5
        if dc < 0.05:
            w = (1.0 - dc / 0.05)**2
            d += Vector((0.0, -0.004 * w, 0.018 * w))
        return d
    add_sk("Smirk_Left", sk_smirk_l)

    # 9. AU9: Nariz Franzido / Nojo (Sneer)
    def sk_sneer(p):
        d = Vector((0.0, 0.0, 0.0))
        dist = (p.x**2 + (p.y - (-0.16))**2 + (p.z - 0.740)**2)**0.5
        if dist < 0.058:
            w = (1.0 - dist / 0.058)**2
            d += Vector((0.0, -0.006 * w, 0.026 * w))
        return d
    add_sk("AU9_Sneer", sk_sneer)

    # 10. Eyes Wide
    def sk_eyes_wide(p):
        d = Vector((0.0, 0.0, 0.0))
        for ex in [0.038, -0.038]:
            dist = ((p.x - ex)**2 + (p.y - (-0.135))**2 + (p.z - 0.780)**2)**0.5
            if dist < 0.042:
                w = (1.0 - dist / 0.042)**2
                z_dir = 0.012 if p.z > 0.780 else -0.008
                d += Vector((0.0, -0.002 * w, z_dir * w))
        return d
    add_sk("Eyes_Wide", sk_eyes_wide)

    # 11. Eyes Squint
    def sk_eyes_squint(p):
        d = Vector((0.0, 0.0, 0.0))
        for ex in [0.038, -0.038]:
            dist = ((p.x - ex)**2 + (p.y - (-0.135))**2 + (p.z - 0.780)**2)**0.5
            if dist < 0.040:
                w = (1.0 - dist / 0.040)**2
                z_dir = -0.010 if p.z > 0.780 else 0.006
                d += Vector((0.0, 0.002 * w, z_dir * w))
        return d
    add_sk("Eyes_Squint", sk_eyes_squint)

    print("Shape Keys C1 refinadas com sucesso!")

EMOTIONS_REFINED = [
    {
        "id": 1,
        "ref": "Screenshot 2024-11-26 104001.png",
        "name": "Perfil_Rosnado_Furioso",
        # Perfil virado para a esquerda (câmera no lado -X)
        "pose": {"pitch": 6, "yaw": 0, "roll": 0, "neck_pitch": 4},
        "cam": {"x": -0.75, "y": -0.10, "z": 0.72, "rot_z": -90, "lens": 85},
        "shapekeys": {"AU4_BrowFrown": 0.8, "AU20_LipStretch": 1.0, "AU9_Sneer": 0.7, "Eyes_Squint": 0.5}
    },
    {
        "id": 2,
        "ref": "Screenshot 2024-11-26 104108.png",
        "name": "34_Grito_de_Guerra",
        # 3/4 virada para a esquerda
        "pose": {"pitch": -10, "yaw": 0, "roll": 4, "neck_pitch": -4},
        "cam": {"x": -0.52, "y": -0.55, "z": 0.73, "rot_z": -45, "lens": 85},
        "shapekeys": {"AU26_JawOpen": 1.0, "AU4_BrowFrown": 0.7, "AU1_2_BrowSurprise": 0.4, "Eyes_Wide": 0.6}
    },
    {
        "id": 3,
        "ref": "Screenshot 2024-11-26 104205.png",
        "name": "Frontal_Grito_Furioso",
        "pose": {"pitch": 6, "yaw": 0, "roll": 0, "neck_pitch": 4},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU26_JawOpen": 1.0, "AU4_BrowFrown": 0.9, "AU9_Sneer": 0.5, "Eyes_Wide": 0.8}
    },
    {
        "id": 4,
        "ref": "Screenshot 2024-11-26 104213.png",
        "name": "Frontal_Raiva_Dentes_Cerrados",
        "pose": {"pitch": 5, "yaw": 0, "roll": 0, "neck_pitch": 3},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU20_LipStretch": 1.0, "AU4_BrowFrown": 0.9, "AU9_Sneer": 0.6, "Eyes_Squint": 0.5}
    },
    {
        "id": 5,
        "ref": "Screenshot 2024-11-26 104224.png",
        "name": "Frontal_Desgosto_Magoada",
        "pose": {"pitch": -2, "yaw": 2, "roll": 5, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU1_BrowSadness": 1.0, "AU15_MouthFrown": 1.0, "Eyes_Wide": 0.3}
    },
    {
        "id": 6,
        "ref": "Screenshot 2024-11-26 104233.png",
        "name": "Frontal_Espanto_Choque",
        "pose": {"pitch": -4, "yaw": 0, "roll": 0, "neck_pitch": -2},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU1_2_BrowSurprise": 1.0, "AU26_JawOpen": 0.60, "Eyes_Wide": 0.9}
    },
    {
        "id": 7,
        "ref": "Screenshot 2024-11-26 104242.png",
        "name": "Frontal_Desprezo_Desdem",
        "pose": {"pitch": 4, "yaw": -4, "roll": -6, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"Smirk_Left": 0.8, "AU4_BrowFrown": 0.6, "AU9_Sneer": 0.5, "Eyes_Squint": 0.4}
    },
    {
        "id": 8,
        "ref": "Screenshot 2024-11-26 104249.png",
        "name": "34_Nojo_Intenso",
        # 3/4 virada para a esquerda
        "pose": {"pitch": 5, "yaw": 0, "roll": 3, "neck_pitch": 2},
        "cam": {"x": -0.45, "y": -0.62, "z": 0.72, "rot_z": -36, "lens": 85},
        "shapekeys": {"AU9_Sneer": 1.0, "AU20_LipStretch": 0.6, "AU4_BrowFrown": 0.7, "Eyes_Squint": 0.4}
    },
    {
        "id": 9,
        "ref": "Screenshot 2024-11-26 104255.png",
        "name": "Frontal_Irritacao_Ameaca",
        "pose": {"pitch": 10, "yaw": 0, "roll": 0, "neck_pitch": 4},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU4_BrowFrown": 0.9, "AU15_MouthFrown": 0.5, "Eyes_Squint": 0.5}
    },
    {
        "id": 10,
        "ref": "Screenshot 2024-11-26 104302.png",
        "name": "Frontal_Desconfiada_Olhar_Lateral",
        "pose": {"pitch": 0, "yaw": 0, "roll": 0, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU4_BrowFrown": 0.4, "AU1_2_BrowSurprise": 0.2, "Eyes_Squint": 0.3}
    },
    {
        "id": 11,
        "ref": "Screenshot 2024-11-26 104309.png",
        "name": "Frontal_Cetica_Questionadora",
        "pose": {"pitch": 2, "yaw": -4, "roll": 10, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU1_2_BrowSurprise": 0.5, "AU4_BrowFrown": 0.3, "AU15_MouthFrown": 0.3}
    },
    {
        "id": 12,
        "ref": "Screenshot 2024-11-26 104322.png",
        "name": "Frontal_Emburrada_Furia_Contida",
        "pose": {"pitch": 7, "yaw": 0, "roll": 0, "neck_pitch": 3},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU4_BrowFrown": 0.8, "AU15_MouthFrown": 0.7, "Eyes_Squint": 0.4}
    },
    {
        "id": 13,
        "ref": "Screenshot 2024-11-26 104334.png",
        "name": "Frontal_Tristeza_Dengo",
        "pose": {"pitch": -3, "yaw": 2, "roll": 12, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU1_BrowSadness": 1.0, "AU15_MouthFrown": 1.0, "Eyes_Squint": 0.2}
    },
    {
        "id": 14,
        "ref": "Screenshot 2024-11-26 104340.png",
        "name": "Perfil_Neutro",
        # Perfil virado para a esquerda
        "pose": {"pitch": 0, "yaw": 0, "roll": 0, "neck_pitch": 0},
        "cam": {"x": -0.75, "y": -0.05, "z": 0.72, "rot_z": -90, "lens": 85},
        "shapekeys": {}
    },
    {
        "id": 15,
        "ref": "Screenshot 2024-11-26 104346.png",
        "name": "Frontal_Sorriso_Contido",
        "pose": {"pitch": 0, "yaw": 0, "roll": 0, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU12_Smile": 0.45}
    },
    {
        "id": 16,
        "ref": "Screenshot 2024-11-26 104352.png",
        "name": "Frontal_Pensativa_Olhar_Superior",
        "pose": {"pitch": -16, "yaw": 0, "roll": 0, "neck_pitch": -8},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU1_2_BrowSurprise": 0.4, "Eyes_Wide": 0.5, "AU12_Smile": 0.2}
    },
    {
        "id": 17,
        "ref": "Screenshot 2024-11-26 104414.png",
        "name": "Frontal_Sorriso_Maroto_Provocante",
        "pose": {"pitch": 2, "yaw": 2, "roll": 2, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU12_Smile": 0.95, "AU20_LipStretch": 0.35, "Smirk_Left": 0.35, "AU1_2_BrowSurprise": 0.2}
    },
    {
        "id": 18,
        "ref": "Screenshot 2024-11-26 104423.png",
        "name": "Frontal_Sorriso_Simpatico_Gentil",
        "pose": {"pitch": 0, "yaw": 0, "roll": 0, "neck_pitch": 0},
        "cam": {"x": -0.005, "y": -0.78, "z": 0.72, "rot_z": 0, "lens": 85},
        "shapekeys": {"AU12_Smile": 0.80}
    }
]

def render_refined():
    scene, mesh_obj, arm_obj = setup_scene()
    build_smooth_shapekeys(mesh_obj)

    out_dir = r"D:\isabella-desktop\assets\renders\warrior_girl\emotions"
    os.makedirs(out_dir, exist_ok=True)

    head_pbone = arm_obj.pose.bones.get('Head')
    neck_pbone = arm_obj.pose.bones.get('Neck')
    cam = bpy.data.objects.get('Camera')

    print(f"\nIniciando renderizacao REFINADA V2 das {len(EMOTIONS_REFINED)} emocoes...")

    for cfg in EMOTIONS_REFINED:
        idx = cfg["id"]
        name = cfg["name"]
        pose = cfg["pose"]
        sk_dict = cfg["shapekeys"]
        cam_cfg = cfg["cam"]

        # Resetar shape keys
        for sk in mesh_obj.data.shape_keys.key_blocks:
            if sk.name != "Basis":
                sk.value = 0.0

        # Aplicar shape keys
        for sk_name, val in sk_dict.items():
            sk = mesh_obj.data.shape_keys.key_blocks.get(sk_name)
            if sk:
                sk.value = val

        # Pose cervical
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        
        base_head_roll = 14.0
        base_head_pitch = -4.0
        
        pitch_rad = math.radians(pose.get("pitch", 0) + base_head_pitch)
        roll_rad = math.radians(pose.get("roll", 0) + base_head_roll)
        yaw_rad = math.radians(pose.get("yaw", 0))
        
        if head_pbone:
            head_pbone.rotation_mode = 'XYZ'
            head_pbone.rotation_euler = (pitch_rad, roll_rad, yaw_rad)

        if neck_pbone:
            neck_pitch = math.radians(pose.get("neck_pitch", 0))
            neck_pbone.rotation_mode = 'XYZ'
            neck_pbone.rotation_euler = (neck_pitch, 0, 0)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Configurar câmera
        cam.location = (cam_cfg["x"], cam_cfg["y"], cam_cfg["z"])
        rot_z = math.radians(cam_cfg.get("rot_z", 0))
        cam.rotation_euler = (math.radians(90), 0, rot_z)
        cam.data.lens = cam_cfg["lens"]

        # Renderizar
        render_path = os.path.join(out_dir, f"emotion_{idx:02d}_{name}.png")
        scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)
        print(f"[{idx}/18] Refinado V2: {name} -> {render_path}")

    blend_final = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
    bpy.ops.wm.save_as_mainfile(filepath=blend_final)
    print(f"\nFinalizado V2! Renders refinados e blend salvo em {blend_final}")

if __name__ == '__main__':
    render_refined()
