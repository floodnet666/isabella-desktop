import os
import sys
import time
import subprocess
import requests
import json

MODEL_DIR = r"D:\isabella-desktop\assets\models\LFM3-Audio-2B-Q4_K_M.colibri"
COLIBRI_CMD = r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0\coli.cmd"
PORT = 8000
PROMPT_QUESTION = "fale-me sobre o existencialismo"

def main():
    env = os.environ.copy()
    env["COLI_CUDA"] = "1"
    env.pop("COLI_VULKAN", None)
    env["COLI_LOOKUP"] = "1"
    env["COLI_SPEC_GATE"] = "1"
    env["COLI_CUDA_CHAIN_ROWS"] = "4096"
    env["Q36_KV"] = "f16"

    cmd = [
        COLIBRI_CMD, "serve",
        "--model", MODEL_DIR,
        "--port", str(PORT),
        "--ctx", "2048",
        "--policy", "experimental-fast",
        "--no-think"
    ]
    log_f = open("logs/test_direct_speed.log", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, env=env, stdout=log_f, stderr=subprocess.STDOUT)
    
    t0 = time.time()
    while time.time() - t0 < 30:
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    print(f"Server ready in {time.time() - t0:.2f}s!")
    
    # Request with enable_thinking: False
    payload = {
        "model": "lfm3-vl-2b-colibri",
        "messages": [
            {"role": "user", "content": PROMPT_QUESTION}
        ],
        "temperature": 0.72,
        "max_tokens": 300,
        "enable_thinking": False,
        "stream": True
    }
    
    for round_idx in (1, 2):
        print(f"\n--- RUNNING ROUND {round_idx} ---")
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
                delta = chunk_data.get("choices", [])[0].get("delta", {})
                content = delta.get("content") or ""
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
        
        print(f"Round {round_idx}: Tokens: {chunks} | TTFT: {ttft*1000:.1f}ms | Total Time: {total_time:.2f}s | Speed: {tok_s:.2f} tok/s")
        print(f"Text snippet: {full_text[:150]}...")
        time.sleep(1)
        
    # Cleanup
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_f.close()
    
    with open("logs/test_direct_speed.log", "r", encoding="utf-8", errors="replace") as f:
        for l in f.readlines():
            if "spec gate" in l or "lookup" in l or "chain" in l and "per decode token" in l:
                print("   [COLIBRI ENGINE]: " + l.strip())

if __name__ == "__main__":
    main()
