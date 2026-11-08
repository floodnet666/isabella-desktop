import bpy
import os
import subprocess

blend_anim = r'D:\isabella-desktop\assets\models\warrior_girl_v3_animated.blend'
bpy.ops.wm.open_mainfile(filepath=blend_anim)
scene = bpy.context.scene

scene.frame_start = 248
scene.frame_end = 300

frames_dir = r'D:\isabella-desktop\assets\renders\warrior_girl\anim_frames'
scene.render.filepath = os.path.join(frames_dir, "frame_")

print("Renderizando frames restantes 248 a 300...")
bpy.ops.render.render(animation=True)
print("Frames 248 a 300 concluidos!")

# Compilar MP4 e GIF com FFmpeg
ffmpeg_exe = r'D:\ffmpeg-2025-11-27-git-61b034a47c-full_build\bin\ffmpeg.exe'
mp4_out = r'D:\isabella-desktop\assets\renders\warrior_girl\warrior_girl_10s_facs_presentation.mp4'
gif_out = r'D:\isabella-desktop\assets\renders\warrior_girl\warrior_girl_10s_facs_preview.gif'

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

cmd_gif = [
    ffmpeg_exe, '-y',
    '-i', mp4_out,
    '-vf', 'fps=15,scale=384:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
    gif_out
]
subprocess.run(cmd_gif, check=True)
print(f"GIF gerado com sucesso: {gif_out}")
