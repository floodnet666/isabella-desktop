import subprocess
import time
import requests
import sounddevice as sd
import numpy as np
import io
import soundfile as sf
import base64

def audio_to_wav_base64(audio_float32: np.ndarray, sr: int = 16000) -> str:
    audio_int16 = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    sf.write(buf, audio_int16, sr, format='WAV', subtype='PCM_16')
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def main():
    print(">> Gravando 3 segundos do microfone real para teste...")
    fs = 16000
    rec = sd.rec(int(fs * 3.0), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    rec = rec.flatten()
    print(f">> Gravado! RMS: {np.sqrt(np.mean(rec**2)):.5f}, shape: {rec.shape}")
    
    b64 = audio_to_wav_base64(rec, fs)
    print(f">> Base64 gerado: {len(b64)} chars")
    
    transcribe_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Perform ASR in Portuguese."},
            {"type": "input_audio", "input_audio": {"data": b64, "format": "wav"}}
        ]
    }
    
    print(">> Enviando para llama-server...")
    t0 = time.time()
    try:
        r = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={
                "messages": [transcribe_msg],
                "temperature": 0.0,
                "max_tokens": 128
            },
            timeout=30
        )
        print(f">> Resposta em {time.time()-t0:.2f}s (Status: {r.status_code}):", r.text)
    except Exception as e:
        print(f">> Falha após {time.time()-t0:.2f}s:", e)

if __name__ == "__main__":
    main()
