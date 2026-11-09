"""
Benchmark Cientifico de Velocidade: llama.cpp vs JustVugg/colibri
Mesmo modelo: LFM3-Audio-2B-Q4_K_M.gguf
Mesma pergunta: "fale-me sobre o existencialismo"
Mesmo pipeline: LLM Streaming -> Sentences -> OmniVoice TTS (GPU, num_step=16) -> Audio Playback

Logging robusto:
- Logs completos de stdout/stderr de cada motor salvos em logs/benchmark_llama_server.log e logs/benchmark_colibri_server.log
- Line-buffering ativo para feedback em tempo real
- Tratamento de excecoes estrito e detalhado
"""

import os
import sys
import time
import json
import queue
import re
import threading
import subprocess
from pathlib import Path
import requests
import torch
import soundfile as sf

# Força line buffering no stdout para evitar perdas de log
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Import OmniVoice
from omnivoice import OmniVoice
from omnivoice.models.omnivoice import VoiceClonePrompt, OmniVoiceGenerationConfig

PROMPT_QUESTION = "fale-me sobre o existencialismo"
MAX_TOKENS = 750
TEMPERATURE = 0.72

ROOT_DIR = Path(r"D:\isabella-desktop")
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT_DIR / "assets" / "renders" / "benchmark_colibri_vs_llama"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_GGUF = r"D:\isabella-desktop\assets\models\LFM3-Audio-2B-Q4_K_M.gguf"
MMPROJ_GGUF = r"D:\isabella-desktop\assets\models\mmproj-LFM3-Audio-2B-Q8_0.gguf"
COLIBRI_MODEL = r"D:\isabella-desktop\assets\models\LFM3-Audio-2B-Q4_K_M.colibri"
LLAMA_EXE = r"D:\isabella-desktop\tools\llama-cpp\llama-server.exe"
COLIBRI_DIR = r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0"
COLIBRI_SCRIPT = os.path.join(COLIBRI_DIR, "coli")
VOICE_PROMPT_PATH = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"

SYSTEM_PROMPT = """Você é Isabella, uma assistente e companheira inteligente que responde perguntas em português do Brasil de forma clara, aprofundada e natural."""

LLAMA_LOG_PATH = LOGS_DIR / "benchmark_llama_server.log"
COLIBRI_LOG_PATH = LOGS_DIR / "benchmark_colibri_server.log"

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

def print_log_tail(log_path, num_lines=25):
    if not os.path.exists(log_path):
        print(f"   [LOG]: Arquivo {log_path} nao existe.")
        return
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            tail = lines[-num_lines:]
            print(f"--- [ULTIMAS LINHAS DE {os.path.basename(log_path)}] ---")
            for line in tail:
                print(f"   | {line.rstrip()}")
            print("--------------------------------------------------")
    except Exception as e:
        print(f"   [LOG ERRO]: Falha ao ler {log_path}: {e}")

def wait_for_health(url, log_path, timeout=35):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    print(f">> [HEALTHCHECK TIMEOUT]: Servidor nao respondeu em {url} apos {timeout}s!")
    print_log_tail(log_path, 30)
    return False

def start_llama_server():
    print(f">> [Llama.cpp] Iniciando llama-server.exe na GPU CUDA (porta 8080)...")
    print(f">> [Llama.cpp] Redirecionando logs para: {LLAMA_LOG_PATH}")
    log_file = open(LLAMA_LOG_PATH, "w", encoding="utf-8")
    cmd = [
        LLAMA_EXE,
        "-m", MODEL_GGUF,
        "--mmproj", MMPROJ_GGUF,
        "-ngl", "99",
        "-fa", "auto",
        "-np", "1",
        "-c", "2048",
        "--jinja",
        "--reasoning", "off",
        "--no-reasoning-preserve",
        "--port", "8080"
    ]
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    if not wait_for_health("http://127.0.0.1:8080/health", LLAMA_LOG_PATH, timeout=35):
        kill_process_tree(proc)
        log_file.close()
        raise RuntimeError("Falha ao iniciar llama-server.exe na porta 8080!")
    print(">> [Llama.cpp] Servidor online e pronto!")
    return proc, log_file

def start_colibri_server(backend="cuda"):
    if backend == "cuda":
        backend_name = "CUDA GPU (RTX 3060 Optimized)"
    elif backend == "vulkan":
        backend_name = "Vulkan GPU (RTX 3060)"
    else:
        backend_name = "CPU (AVX2 Multi-thread)"
    print(f">> [Colibri] Iniciando coli serve com backend {backend_name} (porta 8000)...")
    print(f">> [Colibri] Redirecionando logs para: {COLIBRI_LOG_PATH}")
    log_file = open(COLIBRI_LOG_PATH, "w", encoding="utf-8")
    
    env = os.environ.copy()
    if backend == "cuda":
        env["COLI_CUDA"] = "1"
        env.pop("COLI_VULKAN", None)
        env["COLI_LOOKUP"] = "1"
        env["COLI_SPEC_GATE"] = "1"
        env["COLI_CUDA_CHAIN_ROWS"] = "4096"
        env["Q36_KV"] = "f16"
    elif backend == "vulkan":
        env["COLI_VULKAN"] = "1"
        env["COLI_CUDA"] = "0"
    else:
        env["COLI_VULKAN"] = "0"
        env["COLI_CUDA"] = "0"
        
    cmd = [
        sys.executable,
        COLIBRI_SCRIPT,
        "serve",
        "--model", COLIBRI_MODEL,
        "--port", "8000",
        "--ctx", "2048",
        "--policy", "experimental-fast",
        "--no-think"
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    if not wait_for_health("http://127.0.0.1:8000/health", COLIBRI_LOG_PATH, timeout=40):
        kill_process_tree(proc)
        log_file.close()
        raise RuntimeError(f"Falha ao iniciar Colibri na porta 8000 com backend {backend_name}!")
    print(f">> [Colibri - {backend_name}] Servidor online e pronto!")
    return proc, log_file

def run_benchmark_trial(engine_name, api_url, model_id, run_idx, omnivoice_model, voice_prompt, voice_cfg):
    print(f"\n" + "="*70)
    print(f"   EXECUTANDO BENCHMARK: {engine_name} | Rodada {run_idx}")
    print(f"   Pergunta: \"{PROMPT_QUESTION}\"")
    print(f"="*70)
    
    t0_pipeline = time.perf_counter()
    
    text_queue = queue.Queue(maxsize=50)
    audio_queue = queue.Queue(maxsize=50)
    stop_event = threading.Event()
    
    metrics = {
        "engine": engine_name,
        "run": run_idx,
        "ttft_any_ms": None,
        "ttft_content_ms": None,
        "ttfp_ms": None,
        "ttfa_ms": None,
        "text_done_ms": None,
        "voice_done_ms": None,
        "total_e2e_ms": None,
        "total_tokens": 0,
        "reasoning_tokens": 0,
        "content_tokens": 0,
        "tokens_per_sec": 0.0,
        "full_text": "",
        "full_reasoning": "",
        "num_sentences": 0,
        "total_audio_duration_sec": 0.0,
        "total_synth_time_sec": 0.0,
        "rtf": 0.0,
        "sentences_detail": []
    }
    
    # Thread 1: LLM Worker
    def llm_worker():
        t0_llm = time.perf_counter()
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": PROMPT_QUESTION}
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "enable_thinking": False,
            "stream": True
        }
        
        try:
            r = requests.post(f"{api_url}/v1/chat/completions", json=payload, stream=True, timeout=90)
            if r.status_code != 200:
                print(f"   [LLM ERRO HTTP]: Status {r.status_code}: {r.text}")
                return
                
            buffer = ""
            phrase_idx = 0
            
            for line in r.iter_lines():
                if stop_event.is_set():
                    break
                if not line or not line.startswith(b"data: "):
                    continue
                raw = line[6:].decode("utf-8").strip()
                if raw == "[DONE]":
                    break
                try:
                    data = json.loads(raw)
                    delta = data["choices"][0]["delta"]
                    metrics["total_tokens"] += 1
                    t_now = time.perf_counter()
                    
                    if metrics["ttft_any_ms"] is None:
                        metrics["ttft_any_ms"] = (t_now - t0_pipeline) * 1000.0
                        print(f"   [LLM]: Primeiro token (prefill latency) em {metrics['ttft_any_ms']:.1f}ms")
                        
                    reasoning_chunk = delta.get("reasoning_content") or ""
                    if reasoning_chunk:
                        metrics["reasoning_tokens"] += 1
                        metrics["full_reasoning"] += reasoning_chunk
                        
                    content_chunk = delta.get("content") or ""
                    if content_chunk:
                        metrics["content_tokens"] += 1
                        metrics["full_text"] += content_chunk
                        if metrics["ttft_content_ms"] is None:
                            metrics["ttft_content_ms"] = (t_now - t0_pipeline) * 1000.0
                            print(f"   [LLM]: Primeiro token verbal (conteudo) em {metrics['ttft_content_ms']:.1f}ms")
                            
                        buffer += content_chunk
                        # Separação por pontuação natural
                        m = re.search(r'^(.*?[.!?…\n])\s*(.*)$', buffer, re.DOTALL)
                        if m:
                            phrase = clean_text_for_speech(m.group(1))
                            buffer = m.group(2)
                            if phrase and len(phrase.split()) >= 1:
                                phrase_idx += 1
                                t_phrase = time.perf_counter()
                                dt_phrase = (t_phrase - t0_pipeline) * 1000.0
                                if metrics["ttfp_ms"] is None:
                                    metrics["ttfp_ms"] = dt_phrase
                                print(f"   [LLM -> TTS #{phrase_idx} | {dt_phrase:.0f}ms]: \"{phrase}\"")
                                text_queue.put((phrase_idx, phrase, dt_phrase))
                except Exception as e:
                    pass
                    
            leftover = clean_text_for_speech(buffer)
            if leftover and len(leftover.split()) >= 1:
                phrase_idx += 1
                dt_phrase = (time.perf_counter() - t0_pipeline) * 1000.0
                if metrics["ttfp_ms"] is None:
                    metrics["ttfp_ms"] = dt_phrase
                print(f"   [LLM -> TTS #{phrase_idx} (final) | {dt_phrase:.0f}ms]: \"{leftover}\"")
                text_queue.put((phrase_idx, leftover, dt_phrase))
                
            metrics["num_sentences"] = phrase_idx
            metrics["text_done_ms"] = (time.perf_counter() - t0_pipeline) * 1000.0
            total_llm_dur_sec = (time.perf_counter() - t0_llm)
            metrics["tokens_per_sec"] = metrics["total_tokens"] / max(0.001, total_llm_dur_sec)
            print(f"   [LLM]: Concluido em {metrics['text_done_ms']:.1f}ms | {metrics['total_tokens']} tokens ({metrics['tokens_per_sec']:.2f} tok/s) [Raciocinio: {metrics['reasoning_tokens']} | Conteudo: {metrics['content_tokens']}]")
            
        except Exception as e:
            print(f"   [LLM EXCECAO]: {e}")
        finally:
            text_queue.put(None)
            
    # Thread 2: OmniVoice Synthesizer Worker
    def synth_worker():
        while not stop_event.is_set():
            try:
                item = text_queue.get(timeout=45.0)
            except queue.Empty:
                break
            if item is None:
                audio_queue.put(None)
                break
                
            idx, phrase, phrase_emit_ms = item
            t_s0 = time.perf_counter()
            try:
                results = omnivoice_model.generate(
                    text=phrase,
                    language="pt",
                    voice_clone_prompt=voice_prompt,
                    speed=1.05,
                    generation_config=voice_cfg,
                )
                dt_synth = time.perf_counter() - t_s0
                if results and len(results) > 0:
                    audio_np = results[0]
                    if isinstance(audio_np, torch.Tensor):
                        audio_np = audio_np.cpu().numpy()
                    dur_sec = len(audio_np) / 24000.0
                    rtf_chunk = dt_synth / dur_sec if dur_sec > 0 else 0
                    t_audio_ready = time.perf_counter()
                    audio_ready_ms = (t_audio_ready - t0_pipeline) * 1000.0
                    
                    if metrics["ttfa_ms"] is None:
                        metrics["ttfa_ms"] = audio_ready_ms
                        print(f"\n   >>> [PRIMEIRO AUDIO PRONTO (TTFA)]: {metrics['ttfa_ms']:.1f}ms (Sintese: {dt_synth*1000:.0f}ms, Audio: {dur_sec:.2f}s) <<<\n")
                        
                    metrics["total_synth_time_sec"] += dt_synth
                    metrics["total_audio_duration_sec"] += dur_sec
                    
                    # Salva arquivo WAV
                    clean_eng = engine_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                    wav_name = f"{clean_eng}_run{run_idx}_phrase{idx:02d}.wav"
                    wav_path = OUTPUT_DIR / wav_name
                    sf.write(str(wav_path), audio_np, 24000)
                    
                    metrics["sentences_detail"].append({
                        "phrase_idx": idx,
                        "text": phrase,
                        "emit_ms": phrase_emit_ms,
                        "audio_ready_ms": audio_ready_ms,
                        "synth_time_ms": dt_synth * 1000.0,
                        "audio_duration_sec": dur_sec,
                        "rtf": rtf_chunk,
                        "wav_file": wav_name
                    })
                    print(f"   [TTS #{idx}]: Sintese={dt_synth*1000:.0f}ms | Audio={dur_sec:.2f}s | RTF={rtf_chunk:.2f}x | Pronto={audio_ready_ms:.0f}ms")
                    audio_queue.put((idx, phrase, dur_sec))
            except Exception as e:
                print(f"   [TTS EXCECAO #{idx}]: {e}")
                
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
    
    # Exibe resumo seguro
    ttft_any_str = f"{metrics['ttft_any_ms']:.1f}ms" if metrics['ttft_any_ms'] is not None else "N/A"
    ttft_c_str = f"{metrics['ttft_content_ms']:.1f}ms" if metrics['ttft_content_ms'] is not None else "N/A"
    ttfa_str = f"{metrics['ttfa_ms']:.1f}ms" if metrics['ttfa_ms'] is not None else "N/A"
    text_done_str = f"{metrics['text_done_ms']:.1f}ms" if metrics['text_done_ms'] is not None else "N/A"
    
    print(f"\n>> Rodada {run_idx} de {engine_name} Concluida:")
    print(f"   1. Texto:  TTFT={ttft_any_str} | TTFT_verbal={ttft_c_str} | Dur={text_done_str} | {metrics['total_tokens']} tokens ({metrics['tokens_per_sec']:.1f} tok/s)")
    print(f"   2. Voz:    TTFA={ttfa_str} | Total Sintese={metrics['total_synth_time_sec']:.2f}s | Total Audio={metrics['total_audio_duration_sec']:.2f}s | RTF Global={metrics['rtf']:.2f}x | Frases={metrics['num_sentences']}")
    print(f"   3. Total:  E2E={metrics['total_e2e_ms']:.1f}ms ({metrics['total_e2e_ms']/1000.0:.2f}s)")
    
    return metrics

def main():
    print("="*80)
    print("       BENCHMARK COMPARATIVO: LLAMA.CPP vs JUSTVUGG/COLIBRI")
    print("       Pipeline Completo: LLM Streaming + OmniVoice TTS (GPU)")
    print("       Hardware: Intel i7-10870H | 64GB RAM | NVIDIA RTX 3060 Laptop (6GB)")
    print("="*80)
    
    # 1. Carregar OmniVoice antecipadamente na GPU
    print("\n>> [1/4] Carregando pesos neurais do OmniVoice na VRAM (num_step=16)...")
    omnivoice_model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16,
    )
    voice_prompt = VoiceClonePrompt.load(VOICE_PROMPT_PATH, map_location="cuda:0")
    voice_cfg = OmniVoiceGenerationConfig(num_step=16)
    print(">> [1/4] OmniVoice pronto para sintese de alta fidelidade!")
    
    all_results = []
    
    # 2. Executar Benchmark LLAMA.CPP (CUDA)
    print("\n" + "#"*80)
    print("   ETAPA 1: LLAMA.CPP (CUDA - GPU RTX 3060)")
    print("#"*80)
    llama_proc, llama_log = start_llama_server()
    try:
        # Run 1 (Cold / Initial)
        r1 = run_benchmark_trial("llama.cpp (CUDA)", "http://127.0.0.1:8080", MODEL_GGUF, 1, omnivoice_model, voice_prompt, voice_cfg)
        all_results.append(r1)
        time.sleep(2)
        # Run 2 (Warm)
        r2 = run_benchmark_trial("llama.cpp (CUDA)", "http://127.0.0.1:8080", MODEL_GGUF, 2, omnivoice_model, voice_prompt, voice_cfg)
        all_results.append(r2)
    except Exception as e:
        print(f">> [ERRO EM LLAMA.CPP]: {e}")
        print_log_tail(LLAMA_LOG_PATH, 30)
    finally:
        print(">> Encerrando servidor llama.cpp...")
        kill_process_tree(llama_proc)
        llama_log.close()
        time.sleep(2)
        torch.cuda.empty_cache()
        
    # 3. Executar Benchmark COLIBRI (CUDA Otimizado >100 tok/s)
    print("\n" + "#"*80)
    print("   ETAPA 2: JUSTVUGG/COLIBRI (CUDA OTIMIZADO >100 tok/s - RTX 3060)")
    print("#"*80)
    colibri_cuda_proc, colibri_cuda_log = start_colibri_server(backend="cuda")
    try:
        # Run 1 (Cold / Initial)
        r1_cuda = run_benchmark_trial("Colibri (CUDA Otimizado)", "http://127.0.0.1:8000", "lfm3-vl-2b-colibri", 1, omnivoice_model, voice_prompt, voice_cfg)
        all_results.append(r1_cuda)
        time.sleep(2)
        # Run 2 (Warm)
        r2_cuda = run_benchmark_trial("Colibri (CUDA Otimizado)", "http://127.0.0.1:8000", "lfm3-vl-2b-colibri", 2, omnivoice_model, voice_prompt, voice_cfg)
        all_results.append(r2_cuda)
    except Exception as e:
        print(f">> [ERRO EM COLIBRI CUDA]: {e}")
        print_log_tail(COLIBRI_LOG_PATH, 30)
    finally:
        print(">> Encerrando servidor Colibri CUDA...")
        kill_process_tree(colibri_cuda_proc)
        colibri_cuda_log.close()
        time.sleep(2)
        torch.cuda.empty_cache()

    # 4. Executar Benchmark COLIBRI (Vulkan GPU)
    print("\n" + "#"*80)
    print("   ETAPA 3: JUSTVUGG/COLIBRI (Vulkan GPU - RTX 3060)")
    print("#"*80)
    colibri_vk_proc, colibri_vk_log = start_colibri_server(backend="vulkan")
    try:
        # Run 1 (Cold / Initial)
        r1_vk = run_benchmark_trial("Colibri (Vulkan GPU)", "http://127.0.0.1:8000", "lfm3-vl-2b-colibri", 1, omnivoice_model, voice_prompt, voice_cfg)
        all_results.append(r1_vk)
    except Exception as e:
        print(f">> [ERRO EM COLIBRI VULKAN]: {e}")
        print_log_tail(COLIBRI_LOG_PATH, 30)
    finally:
        print(">> Encerrando servidor Colibri Vulkan...")
        kill_process_tree(colibri_vk_proc)
        colibri_vk_log.close()
        time.sleep(2)
        torch.cuda.empty_cache()
        
    # 5. Salvar Resultados em JSON
    results_json_path = OUTPUT_DIR / "benchmark_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n>> Resultados brutos salvos com sucesso em: {results_json_path}")
    
    # 6. Exibir Tabela Resumo Comparativa
    print("\n" + "="*105)
    print("                               TABELA RESUMO DO BENCHMARK")
    print("="*105)
    print(f"{'Motor / Config':<23} | {'Rodada':<6} | {'TTFT Prefill':<13} | {'TTFT Verbal':<12} | {'Velocidade':<13} | {'1o Audio (TTFA)':<16} | {'Total E2E':<10}")
    print("-" * 105)
    for res in all_results:
        eng = res["engine"]
        run = res["run"]
        ttft_p = f"{res['ttft_any_ms']:.1f} ms" if res['ttft_any_ms'] is not None else "N/A"
        ttft_v = f"{res['ttft_content_ms']:.1f} ms" if res['ttft_content_ms'] is not None else "N/A"
        tok_s = f"{res['tokens_per_sec']:.1f} tok/s"
        ttfa = f"{res['ttfa_ms']:.1f} ms" if res['ttfa_ms'] is not None else "N/A"
        e2e = f"{res['total_e2e_ms']/1000.0:.2f} s"
        print(f"{eng:<23} | {run:<6} | {ttft_p:<13} | {ttft_v:<12} | {tok_s:<13} | {ttfa:<16} | {e2e:<10}")
    print("="*105)

if __name__ == "__main__":
    main()
