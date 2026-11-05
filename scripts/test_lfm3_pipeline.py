import base64
import io
import json
import logging
import os
import subprocess
import time
import urllib.request
import wave
import numpy as np
import sounddevice as sd
import soundfile as sf

LOG_FILE = r"D:\isabella-desktop\logs\lfm3_test.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL_PATH = r"E:\modelos_ollama\LFM3-Audio-2B-Q4_K_M.gguf"
MMPROJ_PATH = r"E:\modelos_ollama\mmproj-LFM3-Audio-2B-Q8_0.gguf"
LLAMA_TTS_BIN = r"D:\isabella-desktop\tools\llama-cpp\llama-tts.exe"

print("=======================================================")
print("      LIQUID AI - LFM3-AUDIO-2B PIPELINE COMPLETO      ")
print("=======================================================")

def audio_to_wav_base64(audio_float32: np.ndarray, sample_rate: int = 16000) -> str:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        int16_audio = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(int16_audio.tobytes())
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def lfm3_transcribe_audio(audio_float32: np.ndarray) -> str:
    t0 = time.time()
    audio_b64 = audio_to_wav_base64(audio_float32, 16000)
    payload = {
        "messages": [
            {"role": "system", "content": "Perform ASR in Portuguese."},
            {"role": "user", "content": [
                {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
            ]}
        ],
        "max_tokens": 128,
        "temperature": 0.0
    }
    req = urllib.request.Request(
        LLAMA_SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"].get("content", "").strip()
        elapsed = (time.time() - t0) * 1000
        return text, elapsed

def lfm3_synthesize_speech(text: str, output_wav: str = r"D:\isabella-desktop\assets\audio\lfm3_out.wav", voice="female", lang="pt") -> str:
    t0 = time.time()
    cmd = [
        LLAMA_TTS_BIN,
        "-m", MODEL_PATH,
        "-mm", MMPROJ_PATH,
        "-p", text,
        "--tts-voice", voice,
        "--tts-lang", lang,
        "-o", output_wav
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = (time.time() - t0) * 1000
    if res.returncode == 0 and os.path.exists(output_wav):
        return output_wav, elapsed
    else:
        print("[ERRO TTS]:", res.stderr)
        return None, elapsed

if __name__ == "__main__":
    test_audio_path = r"D:\isabella-desktop\assets\audio\test_user_voice.wav"
    print(f"\n[1/3] Testando Ingestão de Áudio com {test_audio_path}...")
    audio_data, sr = sf.read(test_audio_path)
    if sr != 16000:
        import scipy.signal
        num_samples = int(len(audio_data) * 16000 / sr)
        audio_data = scipy.signal.resample(audio_data, num_samples)
        
    text, t_asr = lfm3_transcribe_audio(audio_data)
    print(f"--> Transcrição LFM3 ({t_asr:.1f}ms): \"{text}\"")
    
    print("\n[2/3] Testando Síntese Neural Direta de Fala (LiquidCodec 24kHz)...")
    phrase = "Oi amor, essa é a minha voz sintetizada pelo modelo LFM3."
    out_file, t_tts = lfm3_synthesize_speech(phrase)
    print(f"--> Síntese LFM3 ({t_tts:.1f}ms): Gerado em {out_file}")
    
    if out_file and os.path.exists(out_file):
        print("\n[3/3] Reproduzindo áudio gerado nos alto-falantes...")
        d, r = sf.read(out_file)
        sd.play(d, r)
        sd.wait()
        print("--> Reprodução finalizada com sucesso!")
