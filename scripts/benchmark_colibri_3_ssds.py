"""
Benchmark Comparativo de Desempenho do Colibrì nos 3 SSDs:
- Drive E: (USB-C - WD Black SN770 2TB)
- Drive D: (NVMe Interno M.2 - WD Black SN750 1TB)
- Drive C: (NVMe Interno M.2 - WD PC SN730 1TB)

Avalia:
1. Benchmark de Hardware I/O (Throughput Sequencial Unbuffered e Latência/IOPS Aleatória 64K)
2. Tempo de Carga dos Pesos Residuais do SSD pelo Colibrì
3. Tempo de Geração de Texto (TTFT Prefill, TTFT Verbal, tok/s) na pergunta: "fale-me sobre o existencialismo"
4. Tempo de Geração de Voz (OmniVoice num_step=16 na GPU)
5. Tempo Total E2E
"""

import os
import sys
import time
import json
import queue
import re
import random
import threading
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
import requests
import torch
import soundfile as sf

# Força line-buffering no stdout
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from omnivoice import OmniVoice
from omnivoice.models.omnivoice import VoiceClonePrompt, OmniVoiceGenerationConfig

PROMPT_QUESTION = "fale-me sobre o existencialismo"
MAX_TOKENS = 750
TEMPERATURE = 0.72

ROOT_DIR = Path(r"D:\isabella-desktop")
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT_DIR / "assets" / "renders" / "benchmark_3_ssds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DRIVES_CONFIG = [
    {
        "id": "Drive_E_USBC",
        "name": "Drive E: (USB-C - WD Black SN770 2TB)",
        "bus": "USB 3.2 (Type-C Enclosure)",
        "model_path": r"E:\modelos_ollama\LFM3-Audio-2B-Q4_K_M.colibri",
        "gguf_path": r"E:\modelos_ollama\LFM3-Audio-2B-Q4_K_M.gguf"
    },
    {
        "id": "Drive_D_NVMe",
        "name": "Drive D: (NVMe M.2 - WD Black SN750 1TB)",
        "bus": "PCIe Gen3 x4 (M.2 Interno)",
        "model_path": r"D:\isabella-desktop\assets\models\LFM3-Audio-2B-Q4_K_M.colibri",
        "gguf_path": r"D:\isabella-desktop\assets\models\LFM3-Audio-2B-Q4_K_M.gguf"
    },
    {
        "id": "Drive_C_NVMe",
        "name": "Drive C: (NVMe M.2 - WD PC SN730 1TB)",
        "bus": "PCIe Gen3 x4 (M.2 Interno)",
        "model_path": r"C:\colibri-models\LFM3-Audio-2B-Q4_K_M.colibri",
        "gguf_path": r"C:\colibri-models\LFM3-Audio-2B-Q4_K_M.gguf"
    }
]

COLIBRI_DIR = r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0"
COLIBRI_SCRIPT = os.path.join(COLIBRI_DIR, "coli")
VOICE_PROMPT_PATH = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"
SYSTEM_PROMPT = """Você é Isabella, uma assistente e companheira inteligente que responde perguntas em português do Brasil de forma clara, aprofundada e natural."""

# Windows Unbuffered I/O Constants
kernel32 = ctypes.windll.kernel32
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_FLAG_NO_BUFFERING = 0x20000000

def measure_disk_io(file_path):
    # 1. Sequential Read (Unbuffered, 1MB blocks)
    handle = kernel32.CreateFileW(file_path, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING, None)
    if handle == -1:
        return {"seq_mb_s": 0, "iops_64k": 0, "lat_64k_us": 0}
        
    block_size = 1024 * 1024
    buf = ctypes.create_string_buffer(block_size)
    bytes_read = wintypes.DWORD(0)
    total_bytes = 0
    
    t0 = time.perf_counter()
    while True:
        res = kernel32.ReadFile(handle, buf, block_size, ctypes.byref(bytes_read), None)
        if not res or bytes_read.value == 0:
            break
        total_bytes += bytes_read.value
    dt_seq = time.perf_counter() - t0
    kernel32.CloseHandle(handle)
    
    mb = total_bytes / (1024 * 1024)
    seq_speed = mb / dt_seq if dt_seq > 0 else 0
    
    # 2. Random Read (64KB blocks, 500 reads)
    handle2 = kernel32.CreateFileW(file_path, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING, None)
    chunk_size = 64 * 1024
    file_size = kernel32.GetFileSize(handle2, None)
    max_offset = (file_size - chunk_size) // 4096 * 4096
    num_reads = 500
    offsets = [random.randint(0, max_offset // 4096) * 4096 for _ in range(num_reads)]
    
    buf64 = ctypes.create_string_buffer(chunk_size)
    t0_rnd = time.perf_counter()
    for off in offsets:
        kernel32.SetFilePointer(handle2, off, None, 0)
        kernel32.ReadFile(handle2, buf64, chunk_size, ctypes.byref(bytes_read), None)
    dt_rnd = time.perf_counter() - t0_rnd
    kernel32.CloseHandle(handle2)
    
    iops = num_reads / dt_rnd if dt_rnd > 0 else 0
    lat_us = (dt_rnd / num_reads) * 1e6 if num_reads > 0 else 0
    rnd_mb_s = (num_reads * chunk_size) / (1024 * 1024) / dt_rnd if dt_rnd > 0 else 0
    
    return {
        "file_size_mb": mb,
        "seq_mb_s": seq_speed,
        "seq_time_s": dt_seq,
        "iops_64k": iops,
        "rnd_mb_s": rnd_mb_s,
        "lat_64k_us": lat_us
    }

def clean_text_for_speech(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'</?think>', '', cleaned)
    cleaned = re.sub(r'[\*#_~`\[\]\(\)\"]', '', cleaned).strip()
    return re.sub(r'[\U00010000-\U0010ffff]', '', cleaned).strip()

def kill_process_tree(proc):
    if proc is None:
        return
    try:
        pid = proc.pid
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def wait_for_health(url, timeout=35):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def parse_load_time_from_log(log_path):
    load_time = None
    if not os.path.exists(log_path):
        return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r'resident weights loaded in ([\d\.]+)s', line)
                if m:
                    load_time = float(m.group(1))
    except Exception:
        pass
    return load_time

def start_colibri_for_drive(drive_cfg, log_path):
    print(f">> [Colibri] Iniciando a partir de: {drive_cfg['name']}...")
    log_file = open(log_path, "w", encoding="utf-8")
    env = os.environ.copy()
    env["COLI_VULKAN"] = "1"
    
    cmd = [
        sys.executable,
        COLIBRI_SCRIPT,
        "serve",
        "--model", drive_cfg["model_path"],
        "--port", "8000",
        "--no-think"
    ]
    t0_start = time.perf_counter()
    proc = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    if not wait_for_health("http://127.0.0.1:8000/health", timeout=40):
        kill_process_tree(proc)
        log_file.close()
        raise RuntimeError(f"Falha ao iniciar Colibri para {drive_cfg['id']}!")
    dt_server_ready = (time.perf_counter() - t0_start)
    log_file.flush()
    load_time_engine = parse_load_time_from_log(log_path)
    print(f">> [Colibri] Pronto em {dt_server_ready:.2f}s (Carga de pesos do SSD: {load_time_engine}s)!")
    return proc, log_file, dt_server_ready, load_time_engine

def run_trial(drive_cfg, run_idx, omnivoice_model, voice_prompt, voice_cfg):
    print(f"\n--- Teste de Inferência: {drive_cfg['name']} | Rodada {run_idx} ---")
    t0_pipeline = time.perf_counter()
    
    text_queue = queue.Queue(maxsize=50)
    audio_queue = queue.Queue(maxsize=50)
    stop_event = threading.Event()
    
    metrics = {
        "drive_id": drive_cfg["id"],
        "drive_name": drive_cfg["name"],
        "run": run_idx,
        "ttft_any_ms": None,
        "ttft_content_ms": None,
        "ttfa_ms": None,
        "text_done_ms": None,
        "voice_done_ms": None,
        "total_e2e_ms": None,
        "total_tokens": 0,
        "tokens_per_sec": 0.0,
        "num_sentences": 0,
        "total_audio_duration_sec": 0.0,
        "total_synth_time_sec": 0.0,
        "rtf": 0.0
    }
    
    def llm_worker():
        t0_llm = time.perf_counter()
        payload = {
            "model": "lfm3-vl-2b-colibri",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": PROMPT_QUESTION}
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "stream": True
        }
        try:
            r = requests.post("http://127.0.0.1:8000/v1/chat/completions", json=payload, stream=True, timeout=90)
            buffer = ""
            p_idx = 0
            for line in r.iter_lines():
                if stop_event.is_set(): break
                if not line or not line.startswith(b"data: "): continue
                raw = line[6:].decode("utf-8").strip()
                if raw == "[DONE]": break
                try:
                    data = json.loads(raw)
                    delta = data["choices"][0]["delta"]
                    metrics["total_tokens"] += 1
                    t_now = time.perf_counter()
                    
                    if metrics["ttft_any_ms"] is None:
                        metrics["ttft_any_ms"] = (t_now - t0_pipeline) * 1000.0
                        print(f"   [LLM]: TTFT inicial em {metrics['ttft_any_ms']:.1f}ms")
                        
                    content_chunk = delta.get("content") or ""
                    if content_chunk:
                        if metrics["ttft_content_ms"] is None:
                            metrics["ttft_content_ms"] = (t_now - t0_pipeline) * 1000.0
                            print(f"   [LLM]: Primeiro token verbal em {metrics['ttft_content_ms']:.1f}ms")
                        buffer += content_chunk
                        m = re.search(r'^(.*?[.!?…\n])\s*(.*)$', buffer, re.DOTALL)
                        if m:
                            phrase = clean_text_for_speech(m.group(1))
                            buffer = m.group(2)
                            if phrase and len(phrase.split()) >= 1:
                                p_idx += 1
                                dt_phrase = (time.perf_counter() - t0_pipeline) * 1000.0
                                print(f"   [LLM -> TTS #{p_idx} | {dt_phrase:.0f}ms]: \"{phrase[:50]}...\"")
                                text_queue.put((p_idx, phrase))
                except Exception:
                    pass
            leftover = clean_text_for_speech(buffer)
            if leftover and len(leftover.split()) >= 1:
                p_idx += 1
                text_queue.put((p_idx, leftover))
            metrics["num_sentences"] = p_idx
            metrics["text_done_ms"] = (time.perf_counter() - t0_pipeline) * 1000.0
            metrics["tokens_per_sec"] = metrics["total_tokens"] / max(0.001, time.perf_counter() - t0_llm)
            print(f"   [LLM]: Concluido em {metrics['text_done_ms']:.1f}ms | {metrics['total_tokens']} tokens ({metrics['tokens_per_sec']:.1f} tok/s)")
        except Exception as e:
            print(f"   [LLM ERRO]: {e}")
        finally:
            text_queue.put(None)
            
    def synth_worker():
        while not stop_event.is_set():
            try:
                item = text_queue.get(timeout=45.0)
            except queue.Empty:
                break
            if item is None:
                audio_queue.put(None)
                break
            p_idx, phrase = item
            t_s0 = time.perf_counter()
            try:
                results = omnivoice_model.generate(
                    text=phrase,
                    language="pt",
                    voice_clone_prompt=voice_prompt,
                    speed=1.05,
                    generation_config=voice_cfg
                )
                dt_synth = time.perf_counter() - t_s0
                if results and len(results) > 0:
                    audio_np = results[0]
                    if isinstance(audio_np, torch.Tensor):
                        audio_np = audio_np.cpu().numpy()
                    dur_sec = len(audio_np) / 24000.0
                    audio_ready_ms = (time.perf_counter() - t0_pipeline) * 1000.0
                    if metrics["ttfa_ms"] is None:
                        metrics["ttfa_ms"] = audio_ready_ms
                        print(f"   >>> [1o AUDIO PRONTO (TTFA)]: {metrics['ttfa_ms']:.1f}ms (Sintese: {dt_synth*1000:.0f}ms) <<<")
                    metrics["total_synth_time_sec"] += dt_synth
                    metrics["total_audio_duration_sec"] += dur_sec
                    
                    wav_name = f"{drive_cfg['id']}_run{run_idx}_phrase{p_idx:02d}.wav"
                    sf.write(str(OUTPUT_DIR / wav_name), audio_np, 24000)
            except Exception as e:
                print(f"   [TTS ERRO #{p_idx}]: {e}")
        metrics["voice_done_ms"] = (time.perf_counter() - t0_pipeline) * 1000.0
        if metrics["total_audio_duration_sec"] > 0:
            metrics["rtf"] = metrics["total_synth_time_sec"] / metrics["total_audio_duration_sec"]

    t_llm = threading.Thread(target=llm_worker, daemon=True)
    t_synth = threading.Thread(target=synth_worker, daemon=True)
    t_llm.start()
    t_synth.start()
    t_llm.join()
    t_synth.join()
    
    metrics["total_e2e_ms"] = (time.perf_counter() - t0_pipeline) * 1000.0
    return metrics

def main():
    print("="*85)
    print("   BENCHMARK MULTI-SSD: IMPACTO DA VELOCIDADE DO DISCO NO COLIBRI")
    print("   Comparando Drive E (USB-C) vs Drive D (NVMe M.2) vs Drive C (NVMe M.2)")
    print("="*85)
    
    # 1. Medir Hardware I/O Puro dos 3 SSDs
    print("\n>> [1/3] Medindo desempenho de hardware puro (I/O Unbuffered Direct) nos 3 SSDs...")
    io_results = {}
    for cfg in DRIVES_CONFIG:
        print(f"   Testando {cfg['name']}...")
        res = measure_disk_io(cfg["gguf_path"])
        io_results[cfg["id"]] = res
        print(f"      - Leitura Sequencial: {res['seq_mb_s']:.1f} MB/s ({res['seq_time_s']:.3f}s)")
        print(f"      - Leitura Aleatória 64K: {res['iops_64k']:.0f} IOPS | {res['rnd_mb_s']:.1f} MB/s | Latência: {res['lat_64k_us']:.1f} µs")
        
    # 2. Carregar OmniVoice na GPU
    print("\n>> [2/3] Inicializando OmniVoice na VRAM (num_step=16)...")
    omnivoice_model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16,
    )
    voice_prompt = VoiceClonePrompt.load(VOICE_PROMPT_PATH, map_location="cuda:0")
    voice_cfg = OmniVoiceGenerationConfig(num_step=16)
    print(">> [2/3] OmniVoice pronto!")
    
    # 3. Executar Testes com Colibrì em Cada SSD
    print("\n>> [3/3] Executando Colibrì nos 3 SSDs (Pergunta: 'fale-me sobre o existencialismo')...")
    benchmark_data = []
    
    for cfg in DRIVES_CONFIG:
        print(f"\n{'#'*85}")
        print(f"   TESTANDO COLIBRI NO: {cfg['name']}")
        print(f"{'#'*85}")
        
        log_file_path = LOGS_DIR / f"colibri_{cfg['id']}.log"
        proc, log_f, dt_ready, load_time_engine = start_colibri_for_drive(cfg, log_file_path)
        try:
            # Rodada 1 (Cold / Initial)
            r1 = run_trial(cfg, 1, omnivoice_model, voice_prompt, voice_cfg)
            r1["ssd_load_time_s"] = load_time_engine
            r1["server_ready_time_s"] = dt_ready
            r1["io_metrics"] = io_results[cfg["id"]]
            benchmark_data.append(r1)
            time.sleep(2)
            
            # Rodada 2 (Warm)
            r2 = run_trial(cfg, 2, omnivoice_model, voice_prompt, voice_cfg)
            r2["ssd_load_time_s"] = load_time_engine
            r2["server_ready_time_s"] = dt_ready
            r2["io_metrics"] = io_results[cfg["id"]]
            benchmark_data.append(r2)
        finally:
            print(f">> Encerrando Colibri para {cfg['id']}...")
            kill_process_tree(proc)
            log_f.close()
            time.sleep(2)
            torch.cuda.empty_cache()
            
    # Salvar Resultados
    json_path = OUTPUT_DIR / "ssd_comparison_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2, ensure_ascii=False)
        
    # Exibir Tabela Resumo
    print("\n" + "="*110)
    print("                               TABELA COMPARATIVA DOS 3 SSDS NO COLIBRI")
    print("="*110)
    print(f"{'SSD / Conexão':<28} | {'Seq MB/s':<10} | {'IOPS 64K':<9} | {'Carga SSD':<10} | {'TTFT Prefill':<13} | {'Velocidade':<12} | {'1o Audio':<10}")
    print("-" * 110)
    for r in benchmark_data:
        if r["run"] == 1:
            name = r["drive_name"][:28]
            io = r["io_metrics"]
            seq = f"{io['seq_mb_s']:.1f}"
            iops = f"{io['iops_64k']:.0f}"
            load = f"{r['ssd_load_time_s']:.2f} s" if r['ssd_load_time_s'] else "N/A"
            ttft = f"{r['ttft_any_ms']:.1f} ms"
            tok_s = f"{r['tokens_per_sec']:.1f} tok/s"
            ttfa = f"{r['ttfa_ms']/1000.0:.2f} s"
            print(f"{name:<28} | {seq:<10} | {iops:<9} | {load:<10} | {ttft:<13} | {tok_s:<12} | {ttfa:<10}")
    print("="*110)

if __name__ == "__main__":
    main()
