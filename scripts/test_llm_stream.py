import time
import requests
import json
import re

LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"

def main():
    print(">> Testando streaming de tokens do LLM...")
    payload = {
        "messages": [
            {"role": "system", "content": "Você é Isabella, responda em português com carinho."},
            {"role": "user", "content": "Tudo bem com você?"}
        ],
        "temperature": 0.7,
        "max_tokens": 80,
        "stream": True
    }
    
    t0 = time.time()
    try:
        r = requests.post(LLAMA_SERVER_URL, json=payload, stream=True, timeout=10)
    except Exception as e:
        print("[ERRO]: llama-server offline na porta 8080:", e)
        return
        
    first_token_t = None
    first_sentence_t = None
    buffer = ""
    first_sentence = None
    
    for line in r.iter_lines():
        if not line or not line.startswith(b"data: "):
            continue
        raw_data = line[6:].decode("utf-8").strip()
        if raw_data == "[DONE]":
            break
        try:
            chunk = json.loads(raw_data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                if first_token_t is None:
                    first_token_t = time.time() - t0
                buffer += delta
                if first_sentence is None and re.search(r'[.!?…]\s*$', buffer):
                    first_sentence = buffer.strip()
                    first_sentence_t = time.time() - t0
        except Exception:
            pass
            
    total_t = time.time() - t0
    print(f">> Primeiro token em: {first_token_t*1000:.0f}ms")
    print(f">> Primeira frase ('{first_sentence}') em: {first_sentence_t*1000 if first_sentence_t else 0:.0f}ms")
    print(f">> Resposta completa ('{buffer.strip()}') em: {total_t*1000:.0f}ms")

if __name__ == "__main__":
    main()
