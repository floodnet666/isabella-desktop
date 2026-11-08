import time
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

def main():
    print(">> Carregando Faster-Whisper base (CPU, int8)...")
    t0 = time.time()
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print(f">> Modelo carregado em {time.time() - t0:.2f}s")
    
    audio, sr = sf.read(r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref_12s.wav", dtype="float32")
    chunk_3s = audio[:int(sr * 3.6)]
    
    print(">> Transcrevendo áudio de 3.6s...")
    t1 = time.time()
    segments, info = model.transcribe(chunk_3s, language="pt", beam_size=1)
    text = " ".join([seg.text for seg in segments]).strip()
    dt = time.time() - t1
    print(f">> Transcrição em {dt*1000:.0f}ms: \"{text}\"")

if __name__ == "__main__":
    main()
