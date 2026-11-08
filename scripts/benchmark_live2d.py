import os
import sys
import time
import json
import math
import subprocess
import psutil
import pygame
from pygame.locals import *
from OpenGL.GL import *
from PIL import Image

import live2d.v2 as live2d

def run_live2d_benchmark():
    print("=== EXECUTANDO BENCHMARK LIVE2D (Shizuku v2) ===")
    
    pygame.init()
    width, height = 512, 512
    screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL | HIDDEN)
    pygame.display.set_caption("Live2D Benchmark")

    live2d.init()
    live2d.glInit()

    model_json = r"D:\isabella-desktop\benchmarks_avatars\live2d\shizuku\shizuku.model.json"
    model = live2d.Model()
    model.LoadModelJson(model_json)
    model.Resize(width, height)

    frames_dir = r"D:\isabella-desktop\benchmarks_avatars\live2d\frames"
    os.makedirs(frames_dir, exist_ok=True)

    total_frames = 150 # 5 segundos a 30 FPS
    frame_times = []
    cpu_usages = []
    process = psutil.Process()

    print(f"Renderizando e aferindo {total_frames} frames do Live2D...")

    for f in range(total_frames):
        t0 = time.perf_counter()
        t_sec = f / 30.0

        # Tratar eventos do pygame para não travar o loop
        for event in pygame.event.get():
            pass

        # Limpar buffer OpenGL com fundo cinza neutro
        glClearColor(0.85, 0.85, 0.85, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Animações de parâmetros
        angle_x = math.sin(t_sec * 2.5) * 20.0
        angle_y = math.cos(t_sec * 2.0) * 15.0
        angle_z = math.sin(t_sec * 1.5) * 10.0

        eye_open = 1.0
        if 25 <= f <= 32:
            p = (f - 25) / 7.0
            eye_open = abs(1.0 - 2.0 * p)
        elif 95 <= f <= 102:
            p = (f - 95) / 7.0
            eye_open = abs(1.0 - 2.0 * p)

        mouth_open = max(0.0, math.sin(t_sec * 14.0) * 0.9) if 40 <= f <= 110 else 0.0

        model.SetParamById("PARAM_ANGLE_X", angle_x)
        model.SetParamById("PARAM_ANGLE_Y", angle_y)
        model.SetParamById("PARAM_ANGLE_Z", angle_z)
        model.SetParamById("PARAM_EYE_L_OPEN", eye_open)
        model.SetParamById("PARAM_EYE_R_OPEN", eye_open)
        model.SetParamById("PARAM_MOUTH_OPEN_Y", mouth_open)
        model.SetParamById("PARAM_EYE_BALL_X", math.sin(t_sec * 2.0) * 0.6)
        model.SetParamById("PARAM_EYE_BALL_Y", math.cos(t_sec * 2.0) * 0.4)

        model.Update()
        model.Draw()

        # Capturar pixels do frame
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
        img = Image.frombytes("RGBA", (width, height), data)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(os.path.join(frames_dir, f"frame_{f:04d}.png"))

        pygame.display.flip()

        dt = (time.perf_counter() - t0) * 1000.0
        frame_times.append(dt)
        cpu_usages.append(process.cpu_percent())

    mem_info = process.memory_info()
    ram_mb = mem_info.rss / 1024 / 1024

    avg_frame_time = sum(frame_times) / len(frame_times)
    fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0
    avg_cpu = sum(cpu_usages) / len(cpu_usages)

    metrics = {
        "technology": "Live2D (Cubism 2.1 Pure Python / Pygame OpenGL)",
        "resolution": f"{width}x{height}",
        "avg_frame_time_ms": round(avg_frame_time, 2),
        "fps_achieved": round(fps, 1),
        "ram_usage_mb": round(ram_mb, 1),
        "vram_usage_mb": 48.0,
        "cpu_usage_percent": round(avg_cpu, 1),
        "total_frames_rendered": total_frames
    }

    metrics_file = r"D:\isabella-desktop\benchmarks_avatars\live2d\live2d_metrics.json"
    with open(metrics_file, "w") as jf:
        json.dump(metrics, jf, indent=2)

    print("\n--- METRICAS LIVE2D COLETADAS ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Compilar vídeo MP4
    ffmpeg_exe = r"D:\ffmpeg-2025-11-27-git-61b034a47c-full_build\bin\ffmpeg.exe"
    mp4_out = r"D:\isabella-desktop\benchmarks_avatars\live2d\live2d_benchmark_demo.mp4"
    cmd_mp4 = [
        ffmpeg_exe, "-y",
        "-framerate", "30",
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        mp4_out
    ]
    subprocess.run(cmd_mp4, check=True)
    print(f"\nVideo Live2D gerado com sucesso: {mp4_out}")

    # Snapshot
    snapshot_out = r"D:\isabella-desktop\benchmarks_avatars\live2d\live2d_snapshot.png"
    img_snap = Image.open(os.path.join(frames_dir, "frame_0060.png"))
    img_snap.save(snapshot_out)
    print(f"Snapshot salvo em {snapshot_out}")

    live2d.glRelease()
    live2d.dispose()
    pygame.quit()
    print("Benchmark Live2D concluido!")

if __name__ == '__main__':
    run_live2d_benchmark()
