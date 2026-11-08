import bpy
import math
import os
import subprocess

def animate_and_render():
    blend_path = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    mesh_obj = bpy.data.objects.get('Mesh_0')
    arm_obj = bpy.data.objects.get('Armature_WarriorGirl')
    cam = bpy.data.objects.get('Camera')

    # Configuração de câmera e resolução
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'

    cam.location = (-0.005, -0.78, 0.72)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.lens = 85

    # 300 frames a 30 FPS = 10 segundos
    scene.frame_start = 1
    scene.frame_end = 300
    scene.render.fps = 30

    head_pbone = arm_obj.pose.bones.get('Head')
    neck_pbone = arm_obj.pose.bones.get('Neck')
    chest_pbone = arm_obj.pose.bones.get('Chest')

    # Limpar animações anteriores
    if arm_obj.animation_data:
        arm_obj.animation_data_clear()
    if mesh_obj.data.shape_keys and mesh_obj.data.shape_keys.animation_data:
        mesh_obj.data.shape_keys.animation_data_clear()

    sks = mesh_obj.data.shape_keys.key_blocks

    base_roll = 14.0
    base_pitch = -4.0

    def set_head_pose(pitch, roll, yaw, frame):
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        if head_pbone:
            head_pbone.rotation_mode = 'XYZ'
            head_pbone.rotation_euler = (
                math.radians(pitch + base_pitch),
                math.radians(roll + base_roll),
                math.radians(yaw)
            )
            head_pbone.keyframe_insert(data_path="rotation_euler", frame=frame)
        bpy.ops.object.mode_set(mode='OBJECT')

    def set_sk(name, val, frame):
        sk = sks.get(name)
        if sk:
            sk.value = val
            sk.keyframe_insert(data_path="value", frame=frame)

    # Keyframing das 5 fases da animação de 10s:
    # 0s - 1.5s: Neutro / Respiração Idle
    # 1.5s - 3.5s: Sorriso Maroto (#17)
    # 3.5s - 5.5s: Fala Articulada / Questionadora (#11)
    # 5.5s - 7.5s: Surpresa / Espanto (#06)
    # 7.5s - 9.0s: Sorriso Simpático Gentil (#18)
    # 9.0s - 10.0s: Retorno Neutro

    # Loop de Respiração nos ossos Chest e Neck
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for f in range(1, 301, 15):
        t = f / 30.0
        # Respiração sutil a 0.25 Hz
        breath = math.sin(t * 2.0 * math.pi * 0.25) * 0.012
        if chest_pbone:
            chest_pbone.rotation_mode = 'XYZ'
            chest_pbone.rotation_euler = (breath * 0.5, 0, 0)
            chest_pbone.keyframe_insert(data_path="rotation_euler", frame=f)
    bpy.ops.object.mode_set(mode='OBJECT')

    # FASE 1: Neutro (F1 - F40)
    set_head_pose(0, 0, 0, 1)
    for sk_name in ["AU12_Smile", "AU26_JawOpen", "AU1_2_BrowSurprise", "AU4_BrowFrown", "AU15_MouthFrown", "Smirk_Left", "Eyes_Squint", "Eyes_Wide"]:
        set_sk(sk_name, 0.0, 1)

    # Piscada sutil no frame 25
    set_sk("Eyes_Squint", 0.0, 20)
    set_sk("Eyes_Squint", 0.8, 25)
    set_sk("Eyes_Squint", 0.0, 30)

    # FASE 2: Transição para Sorriso Maroto #17 (F45 - F105)
    set_head_pose(2, 4, 3, 75)
    set_sk("AU12_Smile", 0.95, 75)
    set_sk("Smirk_Left", 0.40, 75)
    set_sk("AU1_2_BrowSurprise", 0.25, 75)
    set_sk("AU20_LipStretch", 0.35, 75)

    # Sustentação e relaxamento
    set_head_pose(2, 4, 3, 95)
    set_sk("AU12_Smile", 0.95, 95)
    set_sk("AU12_Smile", 0.10, 110)
    set_sk("Smirk_Left", 0.0, 110)
    set_sk("AU20_LipStretch", 0.0, 110)

    # FASE 3: Fala Articulada e Cabeça Questionadora #11 (F110 - F170)
    set_head_pose(2, 10, -4, 135)
    set_sk("AU1_2_BrowSurprise", 0.60, 135)
    # Movimentos de fala (fonemas / visemas)
    speech_frames = [
        (115, 0.4, 0.1),
        (122, 0.1, 0.3),
        (130, 0.8, 0.2), # Abertura ampla 'Ah'
        (138, 0.2, 0.5), # 'Ee' / Sorriso
        (145, 0.6, 0.1), # 'Oh'
        (155, 0.3, 0.2),
        (165, 0.0, 0.0)
    ]
    for sf, jaw, sm in speech_frames:
        set_sk("AU26_JawOpen", jaw, sf)
        set_sk("AU12_Smile", sm, sf)

    # FASE 4: Surpresa / Espanto #06 (F175 - F225)
    set_head_pose(-5, 0, 0, 195)
    set_sk("AU1_2_BrowSurprise", 1.0, 195)
    set_sk("Eyes_Wide", 0.95, 195)
    set_sk("AU26_JawOpen", 0.65, 195)

    # Sustenta espanto e relaxa
    set_head_pose(-5, 0, 0, 210)
    set_sk("AU1_2_BrowSurprise", 1.0, 210)
    set_sk("AU1_2_BrowSurprise", 0.0, 230)
    set_sk("Eyes_Wide", 0.0, 230)
    set_sk("AU26_JawOpen", 0.0, 230)

    # FASE 5: Sorriso Simpático Gentil #18 (F235 - F280)
    set_head_pose(0, 0, 0, 255)
    set_sk("AU12_Smile", 0.85, 255)
    set_sk("Eyes_Squint", 0.25, 255) # Olhos sorridentes

    # Retorno elegante ao Neutro (F280 - F300)
    set_head_pose(0, 0, 0, 300)
    set_sk("AU12_Smile", 0.0, 300)
    set_sk("Eyes_Squint", 0.0, 300)

    # Salvar blend animado
    blend_anim = r'D:\isabella-desktop\assets\models\warrior_girl_v3_animated.blend'
    bpy.ops.wm.save_as_mainfile(filepath=blend_anim)
    print(f"Cena animada salva em {blend_anim}")

    # Renderizar sequência de frames
    frames_dir = r'D:\isabella-desktop\assets\renders\warrior_girl\anim_frames'
    os.makedirs(frames_dir, exist_ok=True)
    scene.render.filepath = os.path.join(frames_dir, "frame_")
    
    print("Iniciando renderizacao dos 300 frames (10s a 30 FPS)...")
    bpy.ops.render.render(animation=True)
    print("Renderizacao de frames concluida!")

    # Compilar MP4 e GIF com FFmpeg
    ffmpeg_exe = r'D:\ffmpeg-2025-11-27-git-61b034a47c-full_build\bin\ffmpeg.exe'
    mp4_out = r'D:\isabella-desktop\assets\renders\warrior_girl\warrior_girl_10s_facs_presentation.mp4'
    gif_out = r'D:\isabella-desktop\assets\renders\warrior_girl\warrior_girl_10s_facs_preview.gif'

    # MP4 H.264
    cmd_mp4 = [
        ffmpeg_exe, '-y',
        '-framerate', '30',
        '-i', os.path.join(frames_dir, 'frame_%04d.png'),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '18',
        mp4_out
    ]
    subprocess.run(cmd_mp4, check=True)
    print(f"MP4 gerado com sucesso: {mp4_out}")

    # GIF otimizado
    cmd_gif = [
        ffmpeg_exe, '-y',
        '-i', mp4_out,
        '-vf', 'fps=15,scale=384:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
        gif_out
    ]
    subprocess.run(cmd_gif, check=True)
    print(f"GIF gerado com sucesso: {gif_out}")

if __name__ == '__main__':
    animate_and_render()
