import os
import sys
import time
import subprocess
import requests

MODEL_DIR = r"C:\colibri-models\LFM3-Audio-2B-Q4_K_M.colibri"
COLIBRI_CMD = r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0\coli.cmd"
PORT = 8000
PROMPT_QUESTION = "fale-me sobre o existencialismo"

def run_test(config_name, env_vars, extra_flags):
    print(f"\n=======================================================")
    print(f"TESTING CONFIG: {config_name}")
    print(f"Env vars: {env_vars}")
    print(f"Flags: {extra_flags}")
    print(f"=======================================================")
    
    env = os.environ.copy()
    env.update(env_vars)
    
    cmd = [
        COLIBRI_CMD, "serve",
        "--model", MODEL_DIR,
        "--port", str(PORT),
        "--ctx", "2048",
    ] + extra_flags
    
    log_path = f"logs/tuning_{config_name}.log"
    log_f = open(log_path, "w", encoding="utf-8")
    
    proc = subprocess.Popen(cmd, env=env, stdout=log_f, stderr=subprocess.STDOUT)
    
    # Wait for health
    t0 = time.time()
    healthy = False
    while time.time() - t0 < 30:
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}/health", timeout=1)
            if r.status_code == 200:
                healthy = True
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    if not healthy:
        print("FAILED TO START SERVER. Log tail:")
        proc.kill()
        log_f.close()
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            print("".join(f.readlines()[-20:]))
        return None
        
    # Get model ID
    try:
        models_resp = requests.get(f"http://127.0.0.1:{PORT}/v1/models").json()
        model_id = models_resp["data"][0]["id"]
    except Exception:
        model_id = "default"
    print(f"Server healthy in {time.time() - t0:.2f}s! Using model: {model_id}. Sending chat completion request...")
    
    # Request
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": PROMPT_QUESTION}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True
    }
    
    req_t0 = time.time()
    resp = requests.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", json=payload, stream=True, timeout=60)
    
    first_token_time = None
    chunks = 0
    full_text = ""
    
    for line in resp.iter_lines():
        if not line:
            continue
        line_str = line.decode('utf-8', errors='replace')
        if not line_str.startswith("data: "):
            continue
        data_str = line_str[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk_data = json.loads(data_str)
            choices = chunk_data.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content") or delta.get("reasoning_content") or ""
            if content:
                if first_token_time is None:
                    first_token_time = time.time()
                chunks += 1
                full_text += content
        except Exception:
            pass
            
    total_time = time.time() - req_t0
    ttft = (first_token_time - req_t0) if first_token_time else 0.0
    decode_time = total_time - ttft
    tok_s = (chunks / decode_time) if decode_time > 0 else 0.0
    
    print(f"Done! Chunks/Tokens: {chunks} | TTFT: {ttft*1000:.1f}ms | Total: {total_time:.2f}s | Decode Speed: {tok_s:.2f} tok/s")
    print(f"Text snippet: {full_text[:120]}...")
    
    # Terminate process tree
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    log_f.close()
    
    # Read server stats from log
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_lines = f.readlines()
        for l in log_lines:
            if "spec gate" in l or "lookup" in l or "chain" in l and "per decode token" in l:
                print("   [ENGINE STAT]: " + l.strip())
                
    time.sleep(2)
    return {
        "config": config_name,
        "tokens": chunks,
        "ttft_ms": ttft * 1000,
        "tok_s": tok_s,
        "total_s": total_time
    }

if __name__ == "__main__":
    import json
    results = []
    
    # Config 1: Baseline CUDA + experimental-fast
    r1 = run_test("CUDA_baseline", {"COLI_CUDA": "1"}, ["--policy", "experimental-fast"])
    if r1: results.append(r1)
    
    # Config 2: CUDA + no-think + experimental-fast
    r2 = run_test("CUDA_no_think", {"COLI_CUDA": "1"}, ["--policy", "experimental-fast", "--no-think"])
    if r2: results.append(r2)
    
    # Config 3: CUDA + speculative lookup aggressive (COLI_SPEC_GATE=0, COLI_LOOKUP=1, COLI_LOOKUP_DRAFTS=5)
    r3 = run_test("CUDA_spec_aggressive", {
        "COLI_CUDA": "1",
        "COLI_LOOKUP": "1",
        "COLI_SPEC_GATE": "0",
        "COLI_LOOKUP_DRAFTS": "5"
    }, ["--policy", "experimental-fast", "--no-think"])
    if r3: results.append(r3)
    
    # Config 4: CUDA + COLI_CUDA_CHAIN_ROWS=8192 + Q36_KV=f16
    r4 = run_test("CUDA_spec_optimized", {
        "COLI_CUDA": "1",
        "COLI_LOOKUP": "1",
        "COLI_SPEC_GATE": "0",
        "COLI_LOOKUP_DRAFTS": "5",
        "COLI_CUDA_CHAIN_ROWS": "4096",
        "Q36_KV": "f16"
    }, ["--policy", "experimental-fast", "--no-think"])
    if r4: results.append(r4)

    print("\n================== SUMMARY ==================")
    for r in results:
        print(f"{r['config']:25} | {r['tok_s']:6.2f} tok/s | TTFT: {r['ttft_ms']:6.1f}ms | Tokens: {r['tokens']}")
