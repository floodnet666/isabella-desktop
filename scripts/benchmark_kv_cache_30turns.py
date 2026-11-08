"""
Benchmark de KV cache em conversa de 30 turnos - JustVugg/Colibri (motor qwen36, LFM3-Audio-2B).

Mede por turno: TTFT, tok/s de decodificacao, tokens de prompt/completion, reuso de prefixo
(COLI_PREFIX_LOG), custo T(1) do gate especulativo, aceitacao do lookup, espera de GPU por token,
VRAM (nvidia-smi), RSS do motor (psutil) e tamanho do KV cache (ocupado e capacidade alocada).

Tamanho do KV cache: o motor so imprime o tamanho na primeira alocacao (qwen36.c, ensure_kv).
Por isso ele e calculado com a geometria do config.json e com a regra de crescimento do motor:
  - por camada de atencao e por posicao: 2 (K+V) * kv_heads * head_dim * bytes_por_elemento
  - camadas full_attention crescem com o contexto; sliding_attention ficam num anel de
    window + 256 posicoes (Q36_KV_RING, padrao ligado)
  - capacidade: cresce 1,5x a partir de 1024, em passos de 256, ate --ctx (qwen36.c ~L7441)

Uso:
  uv run python scripts/benchmark_kv_cache_30turns.py --label baseline_f16
  uv run python scripts/benchmark_kv_cache_30turns.py --label kv_f32 --env Q36_KV=f32
"""

import argparse
import json
import logging
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import psutil
import requests

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
except Exception:
    pass

ROOT = Path(r"D:\isabella-desktop")
MODEL_DIR = ROOT / "assets" / "models" / "LFM3-Audio-2B-Q4_K_M.colibri"
COLI_CMD = Path(r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0\coli.cmd")
OUT_DIR = ROOT / "assets" / "renders" / "benchmark_kv_cache"
LOG_DIR = ROOT / "logs"
PORT = 8000

SYSTEM_PROMPT = ("Você é Isabella, uma assistente e companheira inteligente que responde perguntas "
                 "em português do Brasil de forma clara, aprofundada e natural.")

QUESTIONS = [
    "O existencialismo é um humanismo?",
    "O que Sartre quer dizer com \"a existência precede a essência\"?",
    "Como Sartre responde à acusação de que o existencialismo é uma filosofia do desespero e do quietismo?",
    "Qual a diferença entre o existencialismo cristão e o ateu na conferência de 1945?",
    "O que significa dizer que o homem está \"condenado a ser livre\"?",
    "Como se relacionam angústia, desamparo e desespero no texto de Sartre?",
    "O que o exemplo do aluno dividido entre cuidar da mãe e entrar na Resistência mostra sobre a moral?",
    "Por que, ao escolher para si, o homem escolhe para toda a humanidade?",
    "O que é a má-fé e como ela aparece no exemplo do garçom?",
    "Como Simone de Beauvoir desenvolve essa ética em \"Por uma moral da ambiguidade\"?",
    "Quais as principais críticas de Heidegger a Sartre na \"Carta sobre o humanismo\"?",
    "Em que o absurdo de Camus se distingue do existencialismo sartriano?",
    "Como Kierkegaard antecipa a angústia e a escolha?",
    "É possível conciliar existencialismo e marxismo, como Sartre tentou na \"Crítica da razão dialética\"?",
    "Que humanismo Sartre rejeita no final da conferência, e qual ele propõe no lugar?",
    "O existencialismo ainda serve para pensar liberdade e responsabilidade hoje?",
    "Qual o papel do olhar do outro em \"O ser e o nada\" e como isso aparece em \"Entre quatro paredes\"?",
    "O que Sartre entende por projeto fundamental?",
    "Como Merleau-Ponty critica a noção sartriana de liberdade absoluta?",
    "De que modo Dostoiévski, com a frase \"se Deus não existe, tudo é permitido\", é usado por Sartre?",
    "Qual a relação entre a fenomenologia de Husserl e o existencialismo francês?",
    "Como Sartre trata a emoção no \"Esboço para uma teoria das emoções\"?",
    "O que é a náusea no romance de Sartre e o que ela revela sobre a contingência?",
    "Como o existencialismo influenciou a psicoterapia, por exemplo em Viktor Frankl e na análise existencial?",
    "Que lugar a morte ocupa no pensamento de Heidegger em comparação com o de Sartre?",
    "Como Beauvoir aplica o existencialismo à condição feminina em \"O segundo sexo\"?",
    "Por que Sartre recusou o Prêmio Nobel de Literatura em 1964, e como isso se liga à sua filosofia?",
    "O engajamento político de Sartre é coerente com sua ética da liberdade?",
    "Quais objeções analíticas, como as de Ayer, foram feitas ao existencialismo?",
    "Depois de tudo o que discutimos, como você responderia hoje à pergunta inicial: o existencialismo é um humanismo?",
]
assert len(QUESTIONS) == 30, "o protocolo fixa 30 turnos"

BASE_ENV = {
    "COLI_CUDA": "1",
    "COLI_LOOKUP": "1",
    "COLI_SPEC_GATE": "1",
    "COLI_CUDA_CHAIN_ROWS": "4096",
    "Q36_KV": "f16",
    "COLI_PREFIX_LOG": "1",
    # KVSAVE=1 restauraria a conversa da execucao anterior a partir de <model>/.coli_kv,
    # tornando o turno 1 "quente" e invalidando a comparacao entre configuracoes.
    "KVSAVE": "0",
}

RE_PREFIX_REUSE = re.compile(r"\[PREFIX\] reusing (\d+) of (\d+) prompt tokens")
RE_PREFIX_MISS = re.compile(r"\[PREFIX\] no reuse: held=(\d+) cap=(\d+) prompt=(\d+)")
RE_GATE = re.compile(r"\[qwen36 spec gate\] turn (\d+): T\(1\) ([\d.]+) ms")
RE_LOOKUP = re.compile(r"\[qwen36 lookup\] turn (\d+): ([\d.]+) tokens/forward .*?acceptance ([\d.]+)%")
RE_CHAIN = re.compile(r"\[chain\] qwen36: (\d+) forwards.*?([\d.]+) ms waiting for the device.*?"
                      r"([\d.]+) MiB on the device(?:; per decode token ([\d.]+) ms waiting.*?\((\d+) tokens\))?")
RE_KV_FIRST = re.compile(r"\[qwen36\] KV cache: (float16|float32), ([\d.]+) GiB at (\d+) positions")

log = logging.getLogger("kv30")


def setup_logging(label: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"kv30_{label}_client.log"
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(path, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.setLevel(logging.INFO)
    log.handlers = [fh, sh]
    return path


def kv_geometry(model_dir: Path, kv_dtype: str) -> dict:
    cfg = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    types = cfg["layer_types"]
    es = 2 if kv_dtype == "f16" else 4
    row = 2 * cfg["num_key_value_heads"] * cfg["head_dim"] * es
    return {
        "full_layers": types.count("full_attention"),
        "sliding_layers": types.count("sliding_attention"),
        "window": cfg["sliding_window"],
        "ring_rows": cfg["sliding_window"] + 256,
        "bytes_per_layer_row": row,
        "kv_heads": cfg["num_key_value_heads"],
        "head_dim": cfg["head_dim"],
        "bytes_per_element": es,
    }


def kv_bytes(geo: dict, positions: int, ring_on: bool) -> int:
    sliding_rows = min(positions, geo["ring_rows"]) if ring_on else positions
    return geo["bytes_per_layer_row"] * (geo["full_layers"] * positions + geo["sliding_layers"] * sliding_rows)


def next_capacity(cap: int, requested: int, top: int) -> int:
    """Regra de crescimento de ensure_kv() em qwen36.c."""
    if cap >= requested and cap > 0:
        return cap
    want = requested
    if cap and cap + cap // 2 > want:
        want = cap + cap // 2
    want = max(want, 1024)
    want = (want + 255) // 256 * 256
    return min(want, top)


def gpu_mem_used_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5, check=True).stdout
        return int(out.strip().splitlines()[0])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError) as e:
        log.warning("nvidia-smi falhou: %s", e)
        return None


def engine_rss_mib() -> float | None:
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            if (p.info["name"] or "").lower() == "qwen36.exe":
                return p.info["memory_info"].rss / 2**20
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def wait_health(proc: subprocess.Popen, timeout: float = 60.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            if requests.get(f"http://127.0.0.1:{PORT}/health", timeout=1).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def kill_tree(proc: subprocess.Popen) -> None:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_new(path: Path, offset: int) -> tuple[str, int]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        text = f.read()
        return text, f.tell()


def stream_turn(model_id: str, messages: list, max_tokens: int, temperature: float) -> dict:
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "enable_thinking": False,
        "preserve_thinking": True,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    t0 = time.perf_counter()
    t_first = None
    chunks = 0
    text = []
    usage = None
    finish = None
    with requests.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", json=payload,
                       stream=True, timeout=(10, 300)) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        for raw in r.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                ev = json.loads(data)
            except json.JSONDecodeError:
                log.warning("evento SSE invalido: %s", data[:200])
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content") or ""
                if piece:
                    if t_first is None:
                        t_first = time.perf_counter()
                    chunks += 1
                    text.append(piece)
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    t_end = time.perf_counter()
    completion = (usage or {}).get("completion_tokens") or chunks
    decode_s = (t_end - t_first) if t_first else 0.0
    return {
        "ttft_ms": (t_first - t0) * 1000 if t_first else None,
        "turn_s": t_end - t0,
        "decode_s": decode_s,
        "completion_tokens": completion,
        "content_chunks": chunks,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "usage_reported": usage is not None,
        "tok_s": completion / decode_s if decode_s > 0 else 0.0,
        "finish_reason": finish,
        "text": "".join(text),
    }


def parse_engine(text: str) -> dict:
    out = {}
    m = RE_PREFIX_REUSE.search(text)
    if m:
        out["prefix_reused"], out["prefix_prompt"] = int(m.group(1)), int(m.group(2))
    else:
        m = RE_PREFIX_MISS.search(text)
        if m:
            out["prefix_reused"], out["prefix_prompt"] = 0, int(m.group(3))
    m = RE_GATE.search(text)
    if m:
        out["gate_t1_ms"] = float(m.group(2))
    m = RE_LOOKUP.search(text)
    if m:
        out["lookup_tok_per_fwd"], out["lookup_accept_pct"] = float(m.group(2)), float(m.group(3))
    chains = list(RE_CHAIN.finditer(text))
    if chains:
        c = chains[-1]
        out["chain_forwards_cum"] = int(c.group(1))
        out["chain_wait_ms_cum"] = float(c.group(2))
        out["device_mib"] = float(c.group(3))
        if c.group(5):
            out["chain_decode_tokens_cum"] = int(c.group(5))
    m = RE_KV_FIRST.search(text)
    if m:
        out["kv_first_alloc"] = {"dtype": m.group(1), "gib": float(m.group(2)), "positions": int(m.group(3))}
    return out


def pct(values: list, q: float) -> float:
    return float(np.percentile(values, q)) if values else float("nan")


def summarize(turns: list, geo: dict, ctx: int, ring_on: bool, wall_s: float) -> dict:
    tps = [t["tok_s"] for t in turns if t["tok_s"] > 0]
    tokens = sum(t["completion_tokens"] for t in turns)
    decode = sum(t["decode_s"] for t in turns)
    ctx_pos = [t["context_positions"] for t in turns]
    slope = float(np.polyfit(ctx_pos, [t["tok_s"] for t in turns], 1)[0] * 1000) if len(turns) > 2 else None
    reuse = [t["prefix_reused"] / t["prefix_prompt"] for t in turns
             if t.get("prefix_prompt") and t.get("turn", 1) > 1]
    vram = [t["vram_mib"] for t in turns if t.get("vram_mib") is not None]
    last = turns[-1]
    return {
        "turns": len(turns),
        "total_wall_s": wall_s,
        "total_turn_s": sum(t["turn_s"] for t in turns),
        "total_decode_s": decode,
        "total_completion_tokens": tokens,
        "tok_s_weighted": tokens / decode if decode else 0.0,
        "tok_s_mean": statistics.fmean(tps) if tps else 0.0,
        "tok_s_peak": max(tps) if tps else 0.0,
        "tok_s_min": min(tps) if tps else 0.0,
        "tok_s_median": statistics.median(tps) if tps else 0.0,
        "tok_s_p05": pct(tps, 5),
        "tok_s_slope_per_1k_ctx": slope,
        "ttft_ms_first": turns[0]["ttft_ms"],
        "ttft_ms_last": last["ttft_ms"],
        "ttft_ms_mean": statistics.fmean([t["ttft_ms"] for t in turns if t["ttft_ms"] is not None]),
        "prefix_reuse_mean_pct": 100 * statistics.fmean(reuse) if reuse else None,
        "final_context_positions": last["context_positions"],
        "context_occupancy_pct": 100 * last["context_positions"] / ctx,
        "kv_occupied_mib_final": last["kv_occupied_mib"],
        "kv_capacity_mib_final": last["kv_capacity_mib"],
        "kv_capacity_positions_final": last["kv_capacity_positions"],
        "kv_bytes_per_token_growing": geo["bytes_per_layer_row"] * geo["full_layers"],
        "kv_fixed_ring_mib": geo["bytes_per_layer_row"] * geo["sliding_layers"] * geo["ring_rows"] / 2**20 if ring_on else None,
        "vram_mib_first": vram[0] if vram else None,
        "vram_mib_last": vram[-1] if vram else None,
        "vram_mib_peak": max(vram) if vram else None,
        "rss_mib_last": last.get("rss_mib"),
        "truncated_turns": sum(1 for t in turns if t["finish_reason"] == "length"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--env", action="append", default=[], help="KEY=VAL extra para o motor (repetivel)")
    ap.add_argument("--ctx", type=int, default=32768)
    ap.add_argument("--max-tokens", type=int, default=750)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--turns", type=int, default=30)
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.label):
        print("label invalido: use apenas [A-Za-z0-9_.-]", file=sys.stderr)
        return 2
    client_log = setup_logging(args.label)

    env = os.environ.copy()
    env.pop("COLI_VULKAN", None)
    env.update(BASE_ENV)
    for kv in args.env:
        if "=" not in kv:
            log.error("--env sem '=': %s", kv)
            return 2
        k, v = kv.split("=", 1)
        env[k.strip()] = v.strip()
    kv_dtype = env.get("Q36_KV", "f16")
    ring_on = env.get("Q36_KV_RING", "1") != "0"
    geo = kv_geometry(MODEL_DIR, kv_dtype)
    engine_env = {k: env[k] for k in sorted(set(BASE_ENV) | {kv.split("=", 1)[0].strip() for kv in args.env})}
    log.info("config=%s ctx=%d max_tokens=%d temp=%.2f env=%s", args.label, args.ctx, args.max_tokens,
             args.temperature, engine_env)
    log.info("geometria KV: %s", geo)

    for _ in range(15):
        busy = False
        for p in psutil.net_connections(kind="tcp"):
            if p.laddr and p.laddr.port == PORT and p.status == psutil.CONN_LISTEN and p.pid:
                busy = True
                break
        if not busy:
            break
        time.sleep(1)
    else:
        log.error("porta %d ocupada (pid %s)", PORT, p.pid)
        return 3

    server_log = LOG_DIR / f"kv30_{args.label}_server.log"
    vram_idle = gpu_mem_used_mib()
    cmd = [str(COLI_CMD), "serve", "--model", str(MODEL_DIR), "--port", str(PORT), "--ctx", str(args.ctx),
           "--policy", "experimental-fast", "--no-think"]
    log_f = open(server_log, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, env=env, stdout=log_f, stderr=subprocess.STDOUT)
    turns = []
    t_wall0 = time.perf_counter()
    try:
        if not wait_health(proc):
            log.error("servidor nao ficou saudavel; ver %s", server_log)
            return 4
        model_id = requests.get(f"http://127.0.0.1:{PORT}/v1/models", timeout=5).json()["data"][0]["id"]
        vram_loaded = gpu_mem_used_mib()
        offset = server_log.stat().st_size
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        kv_cap = 0
        chain_prev = {"wait": 0.0, "tok": 0}
        kv_first = None
        t_wall0 = time.perf_counter()

        for i, q in enumerate(QUESTIONS[:args.turns], start=1):
            messages.append({"role": "user", "content": q})
            res = stream_turn(model_id, messages, args.max_tokens, args.temperature)
            messages.append({"role": "assistant", "content": res["text"]})
            time.sleep(0.6)  # o motor imprime as linhas de estatistica apos fechar o stream
            new, offset = read_new(server_log, offset)
            eng = parse_engine(new)
            kv_first = kv_first or eng.pop("kv_first_alloc", None)
            eng.pop("kv_first_alloc", None)

            prompt_tok = res["prompt_tokens"] if res["prompt_tokens"] is not None else eng.get("prefix_prompt")
            if prompt_tok is None:
                raise RuntimeError(f"turno {i}: tamanho do prompt indisponivel (usage e [PREFIX] ausentes)")
            ctx_pos = prompt_tok + res["completion_tokens"]
            if ctx_pos >= args.ctx:
                log.warning("turno %d: contexto %d atingiu --ctx %d", i, ctx_pos, args.ctx)
            kv_cap = next_capacity(kv_cap, min(prompt_tok + args.max_tokens, args.ctx), args.ctx)

            wait_turn = tok_turn = None
            if "chain_wait_ms_cum" in eng and "chain_decode_tokens_cum" in eng:
                wait_turn = eng["chain_wait_ms_cum"] - chain_prev["wait"]
                tok_turn = eng["chain_decode_tokens_cum"] - chain_prev["tok"]
                chain_prev = {"wait": eng["chain_wait_ms_cum"], "tok": eng["chain_decode_tokens_cum"]}

            row = {
                "turn": i,
                "question": q,
                **{k: v for k, v in res.items() if k != "text"},
                "answer_chars": len(res["text"]),
                "prompt_tokens_used": prompt_tok,
                "context_positions": ctx_pos,
                "kv_occupied_mib": kv_bytes(geo, ctx_pos, ring_on) / 2**20,
                "kv_capacity_positions": kv_cap,
                "kv_capacity_mib": kv_bytes(geo, kv_cap, ring_on) / 2**20,
                "device_wait_ms_per_token": (wait_turn / tok_turn) if wait_turn is not None and tok_turn else None,
                "vram_mib": gpu_mem_used_mib(),
                "rss_mib": engine_rss_mib(),
                **eng,
            }
            turns.append(row)
            log.info("T%02d | ctx %5d | prompt %5d (reuso %s) | gen %4d | TTFT %6.1f ms | %6.1f tok/s | "
                     "KV %.1f/%.1f MiB | VRAM %s MiB | T(1) %s ms | lookup %s%%",
                     i, ctx_pos, prompt_tok, eng.get("prefix_reused", "?"), res["completion_tokens"],
                     res["ttft_ms"] or -1, res["tok_s"], row["kv_occupied_mib"], row["kv_capacity_mib"],
                     row["vram_mib"], eng.get("gate_t1_ms", "?"), eng.get("lookup_accept_pct", "?"))
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as e:
        log.exception("execucao interrompida no turno %d: %s", len(turns) + 1, e)
    finally:
        wall = time.perf_counter() - t_wall0
        kill_tree(proc)
        log_f.close()

    if not turns:
        log.error("nenhum turno concluido")
        return 5

    summary = summarize(turns, geo, args.ctx, ring_on, wall)
    summary.update({"vram_mib_idle": vram_idle, "vram_mib_after_load": locals().get("vram_loaded"),
                    "kv_first_alloc_engine": kv_first})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"kv30_{args.label}_{stamp}.json"
    out.write_text(json.dumps({
        "label": args.label, "timestamp": stamp, "ctx": args.ctx, "max_tokens": args.max_tokens,
        "temperature": args.temperature, "engine_env": engine_env, "kv_geometry": geo,
        "summary": summary, "turns": turns, "server_log": str(server_log), "client_log": str(client_log),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("=" * 78)
    for k, v in summary.items():
        log.info("%-32s %s", k, f"{v:.2f}" if isinstance(v, float) else v)
    log.info("resultado salvo em %s", out)
    return 0 if len(turns) == args.turns else 6


if __name__ == "__main__":
    sys.exit(main())
