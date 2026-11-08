import time
import requests
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
    print(">> Lendo trecho de áudio...")
    audio, sr = sf.read(r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref_12s.wav", dtype="float32")
    # Pega 3.6s
    chunk = audio[:int(sr * 3.6)]
    # Resample para 16kHz se for 24kHz
    if sr != 16000:
        import torchaudio
        import torch
        chunk_t = torchaudio.functional.resample(torch.from_numpy(chunk), sr, 16000).numpy()
    else:
        chunk_t = chunk
        
    b64 = audio_to_wav_base64(chunk_t, 16000)
    
    transcribe_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Perform ASR in Portuguese."},
            {"type": "input_audio", "input_audio": {"data": b64, "format": "wav"}}
        ]
    }
    
    print(">> Enviando para llama-server (127.0.0.1:8080)...")
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
        dt = time.time() - t0
        print(f">> Status: {r.status_code} em {dt:.2f}s")
        if r.status_code == 200:
            print(">> Resposta:", r.json()["choices"][0]["message"]["content"])
        else:
            print(">> Erro:", r.text)
    except Exception as e:
        print(f">> Exceção após {time.time() - t0:.2f}s:", e)

if __name__ == "__main__":
    main()
