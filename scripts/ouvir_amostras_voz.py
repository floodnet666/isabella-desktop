import os
import time
import sounddevice as sd
import soundfile as sf

SAMPLES_DIR = r"D:\isabella-desktop\assets\audio\voice_samples"

samples = [
    ("Blend 1 - Aveludada & Intima (pf_dora 60% + af_heart 40%)", os.path.join(SAMPLES_DIR, "blend1_intima.wav")),
    ("Blend 2 - Jovem & Provocante (pf_dora 55% + af_heart 25% + af_bella 20%)", os.path.join(SAMPLES_DIR, "blend2_provocante.wav")),
    ("Blend 3 - Sussurrada & Sedutora (pf_dora 50% + af_heart 25% + af_nicole 25%)", os.path.join(SAMPLES_DIR, "blend3_sedutora.wav")),
]

print("=======================================================")
print("     COMPARACAO AUDITIVA DOS BLENDS DE VOZ DA ISABELA   ")
print("=======================================================\n")

for label, file_path in samples:
    if os.path.exists(file_path):
        print(f"--> Tocando: {label}...")
        data, sr = sf.read(file_path)
        sd.play(data, sr)
        sd.wait()
        time.sleep(0.5)
    else:
        print(f"[Arquivo nao encontrado]: {file_path}")

print("\nReproducao concluida!")
