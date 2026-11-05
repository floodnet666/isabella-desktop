import urllib.request
import json
import time
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

t0 = time.time()
req = urllib.request.Request(
    'http://localhost:11434/api/generate',
    data=json.dumps({'model': 'isabela-heretic', 'prompt': 'Oi Isabela! Como você está hoje?', 'stream': False}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    elapsed = (time.time() - t0) * 1000
    print(f"Tempo de Resposta (em VRAM): {elapsed:.1f}ms")
    print(f"Resposta:\n{res.get('response')}")
