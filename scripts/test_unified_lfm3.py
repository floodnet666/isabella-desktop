import base64
import json
import os
import subprocess
import time
import urllib.request
import sounddevice as sd
import soundfile as sf

AUDIO_INPUT = r"D:\isabella-desktop\assets\audio\test_user_voice.wav"
MODEL_PATH = r"E:\modelos_ollama\LFM3-Audio-2B-Q4_K_M.gguf"
MMPROJ_PATH = r"E:\modelos_ollama\mmproj-LFM3-Audio-2B-Q8_0.gguf"
LLAMA_TTS_BIN = r"D:\isabella-desktop\tools\llama-cpp\llama-tts.exe"
LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"

print("=======================================================")
print("      PIPELINE UNIFICADO LFM3 (ZERO WHISPER + ZERO KOKORO)")
print("=======================================================\n")

t0 = time.time()

# 1. Percepcao Nativa de Audio (LFM3 Audio Conformer)
with open(AUDIO_INPUT, "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

p1 = {
    "messages": [
        {"role": "system", "content": "Perform ASR in Portuguese."},
        {"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}]}
    ],
    "max_tokens": 100,
    "temperature": 0.0
}
req1 = urllib.request.Request(LLAMA_SERVER_URL, data=json.dumps(p1).encode("utf-8"), headers={"Content-Type": "application/json"})
r1 = json.loads(urllib.request.urlopen(req1, timeout=15).read().decode("utf-8"))
user_text = r1["choices"][0]["message"]["content"].strip()
t_asr = (time.time() - t0) * 1000
print(f"--> [1. Percepcao LFM3 ({t_asr:.0f}ms)]: \"{user_text}\"")

# 2. Resposta Racional da Isabela (LFM3 Texto)
t1 = time.time()
system_persona = (
    "Você é Isabela, uma mulher sedutora e atrevida de 18 anos. "
    "Responda ao usuário com voz provocante, curta e direta (1 a 2 frases):"
)
p2 = {
    "messages": [
        {"role": "system", "content": system_persona},
        {"role": "user", "content": user_text}
    ],
    "max_tokens": 80,
    "temperature": 0.8
}
req2 = urllib.request.Request(LLAMA_SERVER_URL, data=json.dumps(p2).encode("utf-8"), headers={"Content-Type": "application/json"})
r2 = json.loads(urllib.request.urlopen(req2, timeout=15).read().decode("utf-8"))
reply = r2["choices"][0]["message"]["content"].strip()
t_llm = (time.time() - t1) * 1000
print(f"--> [2. Cerebro LFM3 ({t_llm:.0f}ms)]: \"{reply}\"")

# 3. Voz Neural Nativa LiquidCodec (24 kHz)
t2 = time.time()
out_wav = r"D:\isabella-desktop\assets\audio\isabela_liquidcodec.wav"
cmd = [
    LLAMA_TTS_BIN,
    "-m", MODEL_PATH,
    "-mm", MMPROJ_PATH,
    "-p", reply,
    "--tts-voice", "female",
    "--tts-lang", "pt",
    "-o", out_wav
]
res = subprocess.run(cmd, capture_output=True, text=True)
t_tts = (time.time() - t2) * 1000
total_time = (time.time() - t0) * 1000

print(f"--> [3. Voz LiquidCodec ({t_tts:.0f}ms)]: Gerado em {out_wav}")
print(f"=======================================================")
print(f"--> LATENCIA TOTAL: {total_time:.0f}ms")
print(f"=======================================================\n")

if os.path.exists(out_wav):
    print("Reproduzindo nos alto-falantes...")
    d, sr = sf.read(out_wav)
    sd.play(d, sr)
    sd.wait()
    print("Concluido!")
