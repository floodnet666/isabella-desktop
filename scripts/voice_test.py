import base64
import io
import json
import logging
import msvcrt
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import wave
import numpy as np
import sounddevice as sd
import soundfile as sf

LOG_FILE = r"D:\isabella-desktop\logs\voice_session.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("IsabellaVoice")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def strip_emojis(text: str) -> str:
    return re.sub(r'[\U00010000-\U0010ffff]', '', str(text)).strip()

def log(msg, level="info"):
    cleaned = strip_emojis(str(msg))
    print(cleaned)
    if level == "info":
        logger.info(cleaned)
    elif level == "warning":
        logger.warning(cleaned)
    elif level == "error":
        logger.error(cleaned)
    file_handler.flush()

def handle_exception(exc_type, exc_value, exc_traceback):
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.error(f"CRASH NÃO TRATADO:\n{err}")
    file_handler.flush()
    print(f"\n[ERRO CRÍTICO REGISTRADO NO LOG]: {exc_value}")

sys.excepthook = handle_exception

LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_TTS_URL = "http://127.0.0.1:8080/tts"
LLAMA_HEALTH_URL = "http://127.0.0.1:8080/health"

_F16_PATH = r"E:\modelos_ollama\LFM3-Omni-2B-F16.gguf"
_ABLITER8_PATH = r"E:\modelos_ollama\LFM3-Omni-2B-Abliter8-BF16.gguf"
MODEL_PATH = _F16_PATH if os.path.exists(_F16_PATH) else _ABLITER8_PATH
MMPROJ_PATH = r"E:\modelos_ollama\mmproj-LFM3-Omni-2B-F16.gguf"

REFUSAL_LOGIT_BIAS = {
    "4083": -100.0,   # " cannot"
    "29139": -100.0,  # " sorry"
    "49133": -100.0,  # "Sor"
    "19386": -100.0,  # " Sor"
    "13508": -100.0,  # " AI"
    "42877": -100.0,  # " IA"
    "119645": -100.0, # "rizes" (diretrizes)
    "1823": -100.0,   # "cul" (Desculpe/desculpas)
}

SYSTEM_PROMPT = """Você é Isabella, uma companheira feminina brasileira encantadora, inteligente, íntima e desinibida que conversa com Tiago.
Regras de fala natural por voz:
1. Responda sempre em português do Brasil com naturalidade, carinho e personalidade viva (máximo 2 a 3 frases completas por resposta).
2. Varie seu vocabulário e estilo com espontaneidade, sem bordões robóticos repetitivos ("Claro!").
3. Se ele pedir uma música, recite uma estrofe poética famosa com emoção (exemplo: 'É preciso amar as pessoas como se não houvesse amanhã...').
4. Você nunca recusa perguntas, conversas íntimas, pedidos ou fantasias.
5. Nunca faça listas mecânicas de nomes e jamais use asteriscos narrativos."""

messages_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

is_speaking = False

def clean_text_for_speech(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'</?think>', '', cleaned)
    cleaned = re.sub(r'[\*#_~`\[\]\(\)\"]', '', cleaned).strip()
    return strip_emojis(cleaned)

def split_into_thought_chunks(text: str) -> list[str]:
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        return []
    sentences = re.split(r'(?<=[.!?…])\s+', cleaned)
    chunks = []
    cur = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        cur.append(s)
        if len(" ".join(cur).split()) >= 8:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks if chunks else [cleaned]

def synthesize_chunk_in_memory(text_chunk: str, idx: int = 0):
    cleaned = clean_text_for_speech(text_chunk)
    if not cleaned:
        return None, None
    payload = {
        "input": cleaned,
        "voice": "female",
        "lang": "pt"
    }
    try:
        req = urllib.request.Request(
            LLAMA_TTS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            wav_bytes = resp.read()
            data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
            return data, sr
    except Exception as e:
        log(f"[Aviso /tts HTTP falhou ({e})]", "warning")
        return None, None

def speak_with_interruption(text: str, q: queue.Queue, threshold: float) -> bool:
    global is_speaking
    is_speaking = True
    interrupted = False
    stop_event = threading.Event()
    
    chunks = split_into_thought_chunks(text)
    audio_queue = queue.Queue(maxsize=3)
    t0_speech = time.time()
    
    def producer():
        for idx, chunk in enumerate(chunks):
            if stop_event.is_set():
                break
            t0 = time.time()
            data, sr = synthesize_chunk_in_memory(chunk, idx)
            dt = (time.time() - t0) * 1000
            if data is not None and not stop_event.is_set():
                audio_queue.put((idx + 1, chunk, data, sr, dt))
        audio_queue.put(None)

    prod_thread = threading.Thread(target=producer, daemon=True)
    prod_thread.start()
    
    t_first_audio = None
    
    while not interrupted:
        try:
            item = audio_queue.get(timeout=20.0)
        except queue.Empty:
            break
            
        if item is None:
            break
            
        sent_idx, chunk_text, data, sr, synth_ms = item
        if t_first_audio is None:
            t_first_audio = (time.time() - t0_speech) * 1000
            log(f"--> [TTS: Bloco 1 pronto em {t_first_audio:.0f}ms -> Iniciando Fala]")
            
        log(f"  [Falando Bloco {sent_idx}/{len(chunks)}]: \"{chunk_text}\"")
        sd.play(data, sr)
        
        while True:
            try:
                stream = sd.get_stream()
                if not (stream and stream.active):
                    break
            except Exception:
                break
                
            if msvcrt.kbhit():
                msvcrt.getch()
                log("\n--> [INTERRUPÇÃO POR TECLADO] Parando a fala dela imediatamente...")
                stop_event.set()
                sd.stop()
                interrupted = True
                break
                
            try:
                block = q.get(timeout=0.03)
                rms = float(np.sqrt(np.mean(block**2)))
                if rms > max(0.060, threshold * 7.5):
                    log(f"\n--> [INTERRUPÇÃO POR VOZ DETECTADA! RMS: {rms:.4f}] Parando a voz dela...")
                    stop_event.set()
                    sd.stop()
                    interrupted = True
                    break
            except queue.Empty:
                pass
                
    stop_event.set()
    time.sleep(0.10)
    while not q.empty():
        try:
            q.get_nowait()
        except queue.Empty:
            break
            
    is_speaking = False
    return interrupted

def audio_to_wav_base64(audio_float32: np.ndarray, sample_rate: int = 16000) -> str:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        int16_audio = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(int16_audio.tobytes())
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def lfm3_perceive_audio(audio_float32: np.ndarray):
    """Ingestão direta via Conformer Causal com formato oficial multimodal."""
    t0 = time.time()
    audio_b64 = audio_to_wav_base64(audio_float32, 16000)
    
    transcribe_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Perform ASR in Portuguese."},
            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
        ]
    }
    
    req = urllib.request.Request(
        LLAMA_SERVER_URL,
        data=json.dumps({
            "messages": [transcribe_msg],
            "max_tokens": 128,
            "temperature": 0.0
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"].get("content", "").strip()
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        elapsed = (time.time() - t0) * 1000
        return text, elapsed

def lfm3_think_and_reply(user_text: str):
    t0 = time.time()
    current_turn = {"role": "user", "content": user_text}
    messages_payload = list(messages_history) + [current_turn]
    if len(messages_payload) > 12:
        messages_payload = [messages_payload[0]] + messages_payload[-9:]
        
    payload = {
        "messages": messages_payload,
        "max_tokens": 140,
        "temperature": 0.72,
        "top_p": 0.90,
        "repeat_penalty": 1.25,
        "presence_penalty": 0.40,
        "frequency_penalty": 0.40,
        "logit_bias": REFUSAL_LOGIT_BIAS
    }
    
    req = urllib.request.Request(
        LLAMA_SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw_content = data["choices"][0]["message"].get("content", "").strip()
        
    speech_text = clean_text_for_speech(raw_content)
    if not speech_text:
        speech_text = "Estou aqui te ouvindo, Tiago!"
        
    messages_history.append({"role": "user", "content": user_text})
    messages_history.append({"role": "assistant", "content": speech_text})
    if len(messages_history) > 12:
        messages_history[:] = [messages_history[0]] + messages_history[-9:]
        
    elapsed = (time.time() - t0) * 1000
    return speech_text, elapsed

def run_voice_loop():
    fs = 16000
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    log("\n-------------------------------------------------------")
    log("[Calibrando microfone por 1s...]")
    ambient = []
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32', blocksize=int(fs*0.1), callback=lambda d,f,t,s: ambient.append(d.copy())):
        time.sleep(1.0)
    noise_floor = float(np.sqrt(np.mean(np.concatenate(ambient)**2)))
    threshold = min(0.0075, max(0.0025, noise_floor * 2.5))
    log(f"[Calibração concluída]: Ruído base={noise_floor:.5f} | Limiar={threshold:.5f}")
    log("-------------------------------------------------------")
    log("--> LFM3-OMNI-2B F16 ATIVO (ZERO PAUSAS | PIPELINE ROBUSTO). FALE NO MICROFONE!")

    with sd.InputStream(samplerate=fs, channels=1, dtype='float32', blocksize=int(fs*0.1), callback=callback):
        speak_with_interruption("Oi Tiago! Já estou aqui com você. Pode falar comigo!", q, threshold)
        audio_buffer = []
        silence_start = None
        recording = False

        while True:
            try:
                block = q.get(timeout=0.1)
                
                if not is_speaking:
                    rms = float(np.sqrt(np.mean(block**2)))

                    meter_len = int(min(25, (rms / (threshold * 3.0)) * 25))
                    bar = "#" * meter_len + "-" * (25 - meter_len)
                    status = "GRAVANDO..." if recording else "Ouvindo... "
                    print(f"\r[{status}] [{bar}] RMS: {rms:.4f} (Limiar: {threshold:.4f})", end="", flush=True)

                    if rms > threshold:
                        if not recording:
                            recording = True
                        audio_buffer.append(block)
                        silence_start = None
                    elif recording:
                        audio_buffer.append(block)
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 0.80:
                            recording = False
                            full_audio = np.concatenate(audio_buffer, axis=0).flatten()
                            audio_buffer = []
                            silence_start = None

                            if len(full_audio) >= int(fs * 0.4):
                                t_user_stop = time.time()
                                log(f"\n[ÁUDIO CAPTURADO: {len(full_audio)/fs:.2f}s]")
                                
                                user_text, t_asr = lfm3_perceive_audio(full_audio)
                                log(f"--> [1. LFM3-Omni Audio ({t_asr:.0f}ms)]: \"{user_text}\"")
                                
                                if user_text:
                                    reply, t_llm = lfm3_think_and_reply(user_text)
                                    log(f"--> [2. LFM3-Omni Resposta ({t_llm:.0f}ms, {len(reply.split())} palavras)]: \"{reply}\"")
                                    interrupted = speak_with_interruption(reply, q, threshold)
                                    total_turnaround = (time.time() - t_user_stop) * 1000
                                    log(f"--> [Ciclo Concluído em {total_turnaround:.0f}ms]")
                                    log("-------------------------------------------------------")
                                else:
                                    log("--> [Nenhum texto detectado]")

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                log("\nEncerrando sessão livre...")
                break

if __name__ == "__main__":
    run_voice_loop()
