import os
import soundfile as sf
from kokoro_onnx import Kokoro

KOKORO_MODEL = r"D:\isabella-desktop\assets\voices\kokoro\kokoro-v1.0.onnx"
KOKORO_VOICES = r"D:\isabella-desktop\assets\voices\kokoro\voices-v1.0.bin"
OUTPUT_WAV = r"D:\isabella-desktop\assets\audio\test_user_voice.wav"
os.makedirs(os.path.dirname(OUTPUT_WAV), exist_ok=True)

kokoro = Kokoro(KOKORO_MODEL, KOKORO_VOICES)
text = "Oi Isabela, qual é o seu segredo mais safado?"
samples, sr = kokoro.create(text, voice="af_bella", speed=1.0, lang="pt-br")

# Resample para 16kHz mono para compatibilidade ideal com o conformer de áudio
import numpy as np
import scipy.signal

if sr != 16000:
    num_output_samples = int(len(samples) * 16000 / sr)
    samples_16k = scipy.signal.resample(samples, num_output_samples)
else:
    samples_16k = samples

sf.write(OUTPUT_WAV, samples_16k.astype(np.float32), 16000)
print(f"Áudio de teste gerado em {OUTPUT_WAV} (16kHz mono, {len(samples_16k)/16000:.2f}s)")
