"""
Script de teste de estresse de KV Cache no JustVugg/Colibri (LFM3-Audio-2B em NVMe D:)
Avalia os limites da metodologia otima (FP16 + Ring Buffer) ate e alem de 1.0 GiB e 2.0 GiB de KV Cache:
- Metas do usuario: Minimo >= 100 tok/s, Medio >= 120 tok/s, Pico buscando ~200 tok/s.
- Marcos de contexto testados:
  1.  2.000 tokens  (~28 MiB KV)   - Contexto Curto
  2. 10.000 tokens  (~123 MiB KV)  - Contexto Medio
  3. 22.331 tokens  (~267 MiB KV)  - Fim do teste de 30 turnos
  4. 32.768 tokens  (~389 MiB KV)  - Limite da janela 32k
  5. 50.000 tokens  (~614 MiB KV)  - Contexto Ultra-Longo
  6. 86.954 tokens  (~1.024 MiB KV) - EXATAMENTE 1.0 GiB DE KV CACHE
  7. 128.000 tokens (~1.505 MiB KV) - LIMITE max_position_embeddings DO MODELO
  8. 174.335 tokens (~2.048 MiB KV) - EXATAMENTE 2.0 GiB DE KV CACHE
  9. 200.000 tokens (~2.349 MiB KV) - TESTE DE RUPTURA / EXTREMO

Uso:
  uv run python scripts/stress_test_kv_limits.py
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import requests

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
except Exception:
    pass

ROOT = Path(r"D:\isabella-desktop")
MODEL_DIR = ROOT / "assets" / "models" / "LFM3-Audio-2B-Q4_K_M.colibri"
COLI_CMD = Path(r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0\coli.cmd")
OUT_DIR = ROOT / "assets" / "renders" / "benchmark_kv_limits"
LOG_DIR = ROOT / "logs"
PORT = 8000

BASE_ENV = {
    "COLI_CUDA": "1",
    "COLI_LOOKUP": "1",
    "COLI_SPEC_GATE": "1",
    "COLI_CUDA_CHAIN_ROWS": "4096",
    "Q36_KV": "f16",
    "Q36_KV_RING": "1",
    "KVSAVE": "0",
    "COLI_PREFIX_LOG": "1",
}

# Geometria analitica do LFM3-Audio-2B
FULL_LAYERS = 6
SLIDING_LAYERS = 5
KV_HEADS = 4
HEAD_DIM = 128
BYTES_PER_ELEM = 2  # FP16
BYTES_PER_FULL_POS = FULL_LAYERS * 2 * KV_HEADS * HEAD_DIM * BYTES_PER_ELEM  # 12.288 bytes
RING_POS = 512
BYTES_FIXED_RING = SLIDING_LAYERS * 2 * KV_HEADS * HEAD_DIM * BYTES_PER_ELEM * RING_POS  # 5.242.880 bytes = 5.0 MiB

def kv_occupied_bytes(ctx_positions: int) -> int:
    return BYTES_FIXED_RING + (ctx_positions * BYTES_PER_FULL_POS)

# Texto base filosofico de alta densidade em portugues
BASE_TEXT_SEGMENT = (
    "Na conferência de outubro de 1945, Jean-Paul Sartre defende o existencialismo das críticas que lhe eram dirigidas "
    "pelos comunistas, que o acusavam de quietismo burguês e desespero estéril, e pelos cristãos, que viam na recusa de "
    "Deus o abandono de qualquer fundamento moral objetivo. Sartre formula o axioma fundamental: a existência precede a "
    "essência. Para os objetos fabricados, como um corta-papel, a essência — sua ideia, propósito e técnica de fabricação — "
    "precede sua existência concreta. Para o ser humano desprovido de criador, ele primeiro existe no mundo, surge, "
    "encontra a si mesmo e só depois se define por meio de suas ações e escolhas. Disso decorre a tese de que o homem "
    "está condenado a ser livre. Ao escolher para si, ele escolhe inevitavelmente para toda a humanidade, assumindo "
    "uma responsabilidade cósmica que gera a angústia. A má-fé é a tentativa de fugir dessa liberdade, fingindo ser uma coisa "
    "determinada pelo papel social, como o garçom de café que imita minuciosamente seus gestos para se esquivar da contingência. "
    "Simone de Beauvoir, por sua vez, amplia essa ética ao demonstrar que a liberdade individual só se realiza plenamente quando "
    "engajada na libertação da liberdade dos outros. Heidegger, na Carta sobre o Humanismo dirigida a Jean Beaufret, rompe com "
    "a interpretação sartriana, afirmando que inverter a metafísica tradicional ainda permanece prisioneiro da metafísica, "
    "pois o ser humano não é o senhor do ente, mas o pastor do Ser. Camus rejeita o rótulo de existencialista ao estruturar "
    "o absurdo como o confronto irremediável entre o anseio humano de sentido e o silêncio irracional do universo. "
    "Merleau-Ponty reintroduz a corporeidade e a situação encarnada, contestando a liberdade absoluta e transparente de Sartre, "
    "enquanto Dostoiévski ecoa na proposição de que se Deus não existe, o ser humano é desamparado e tudo lhe é permitido. "
)

def build_long_prompt(target_tokens: int) -> str:
    """Gera um prompt com aproximadamente target_tokens de texto estruturado (504 tokens por bloco)."""
    needed_repeats = max(1, int(target_tokens / 504))
    parts = ["Contexto Histórico e Filosófico do Pensamento Existencialista Contemporâneo:"]
    for i in range(1, needed_repeats + 1):
        parts.append(f"\n[Seção de Análise Epistemológica {i:04d}]\n{BASE_TEXT_SEGMENT}")
    parts.append("\nPergunta conclusiva: Diante de toda a fundamentação acima apresentada sobre a liberdade, a responsabilidade e o absurdo, formule uma síntese analítica abrangente sobre o destino da moralidade humana.")
    return "\n".join(parts)

def gpu_mem_used_mib() -> int:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True, timeout=2
        ).strip().splitlines()
        return int(out[0])
    except Exception:
        return 0

def kill_tree(proc: subprocess.Popen):
    try:
        p = psutil.Process(proc.pid)
        for child in p.children(recursive=True):
            child.kill()
        p.kill()
    except Exception:
        pass

def free_port(port: int):
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.pid:
            try:
                p_old = psutil.Process(conn.pid)
                for c_old in p_old.children(recursive=True):
                    c_old.kill()
                p_old.kill()
                time.sleep(1)
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-gen", type=int, default=256, help="Tokens gerados por teste")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    log = logging.getLogger("KV_StressTest")

    # Lista dos 9 marcos de contexto com buffers de margem de seguranca
    CHECKPOINTS = [
        {"name": "2k_baseline",      "target_tokens": 2000,   "expected_kv_mib": kv_occupied_bytes(2000) / 2**20,   "server_ctx": 4096},
        {"name": "10k_medium",       "target_tokens": 10000,  "expected_kv_mib": kv_occupied_bytes(10000) / 2**20,  "server_ctx": 16384},
        {"name": "22k_turn30_point", "target_tokens": 22331,  "expected_kv_mib": kv_occupied_bytes(22331) / 2**20,  "server_ctx": 32768},
        {"name": "32k_boundary",     "target_tokens": 32000,  "expected_kv_mib": kv_occupied_bytes(32000) / 2**20,  "server_ctx": 40960},
        {"name": "50k_deep_context", "target_tokens": 50000,  "expected_kv_mib": kv_occupied_bytes(50000) / 2**20,  "server_ctx": 65536},
        {"name": "87k_1GB_KV",       "target_tokens": 86954,  "expected_kv_mib": 1024.0,                             "server_ctx": 98304},
        {"name": "128k_model_limit", "target_tokens": 128000, "expected_kv_mib": kv_occupied_bytes(128000) / 2**20, "server_ctx": 140000},
        {"name": "174k_2GB_KV",      "target_tokens": 174335, "expected_kv_mib": 2048.0,                             "server_ctx": 185000},
        {"name": "200k_stress_break","target_tokens": 200000, "expected_kv_mib": kv_occupied_bytes(200000) / 2**20, "server_ctx": 215000},
    ]

    results = []

    log.info("==============================================================================")
    log.info("    INICIANDO TESTE DE ESTRESSE AO LIMITE: ESCALONAMENTO DO KV CACHE          ")
    log.info("    Metas do Usuario: Min >= 100 tok/s | Med >= 120 tok/s | Pico buscando ~200")
    log.info("==============================================================================")

    for cp in CHECKPOINTS:
        name = cp["name"]
        target = cp["target_tokens"]
        expected_kv = cp["expected_kv_mib"]
        server_ctx = cp["server_ctx"]

        log.info("\n------------------------------------------------------------------------------")
        log.info("TESTANDO MARCO: %s (Alvo: ~%d tokens | KV esperado: %.1f MiB | Ctx: %d)",
                 name, target, expected_kv, server_ctx)
        log.info("------------------------------------------------------------------------------")

        free_port(PORT)

        env = os.environ.copy()
        env.pop("COLI_VULKAN", None)
        env.update(BASE_ENV)

        server_log_path = LOG_DIR / f"stress_{name}_server.log"
        server_log = open(server_log_path, "w", encoding="utf-8")

        cmd = [
            str(COLI_CMD), "serve",
            "--model", str(MODEL_DIR),
            "--port", str(PORT),
            "--ctx", str(server_ctx),
            "--policy", "experimental-fast",
            "--no-think"
        ]

        proc = subprocess.Popen(cmd, env=env, stdout=server_log, stderr=subprocess.STDOUT)

        # Aguardar servidor
        healthy = False
        for _ in range(30):
            try:
                r = requests.get(f"http://127.0.0.1:{PORT}/v1/models", timeout=1)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            if proc.poll() is not None:
                break
            time.sleep(1)

        if not healthy:
            log.error("[%s] Falha ao iniciar servidor com --ctx %d! Ver log %s", name, server_ctx, server_log_path)
            kill_tree(proc)
            server_log.close()
            results.append({
                "checkpoint": name, "target_tokens": target, "status": "SERVER_STARTUP_FAILED",
                "error": "Server failed to become healthy with ctx", "server_ctx": server_ctx
            })
            continue

        model_id = requests.get(f"http://127.0.0.1:{PORT}/v1/models", timeout=5).json()["data"][0]["id"]
        vram_loaded = gpu_mem_used_mib()
        prompt_text = build_long_prompt(target)

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Você é Isabella, uma inteligência filosófica e lúcida."},
                {"role": "user", "content": prompt_text}
            ],
            "max_tokens": args.max_gen,
            "temperature": 0.0,
            "enable_thinking": False,
            "preserve_thinking": True,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        row = {
            "checkpoint": name,
            "target_tokens": target,
            "expected_kv_mib": expected_kv,
            "server_ctx": server_ctx,
            "vram_loaded_mib": vram_loaded,
        }

        try:
            log.info("[%s] Enviando requisicao de inferencia (Prefill do contexto)...", name)
            t_req0 = time.perf_counter()
            t_first_tok = None
            chunks_count = 0
            completion_text = []
            usage_info = None

            with requests.post(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                               json=payload, stream=True, timeout=(15, 600)) as resp:
                if resp.status_code != 200:
                    err_text = resp.text[:500]
                    log.error("[%s] Erro HTTP %d: %s", name, resp.status_code, err_text)
                    row.update({"status": f"HTTP_{resp.status_code}", "error": err_text})
                else:
                    for chunk_line in resp.iter_lines():
                        if not chunk_line:
                            continue
                        line_str = chunk_line.decode("utf-8", errors="replace").strip()
                        if not line_str.startswith("data: "):
                            continue
                        payload_str = line_str[6:].strip()
                        if payload_str == "[DONE]":
                            break

                        try:
                            d = json.loads(payload_str)
                        except Exception:
                            continue

                        if d.get("usage"):
                            usage_info = d["usage"]

                        for ch in d.get("choices") or []:
                            piece = (ch.get("delta") or {}).get("content") or ""
                            if piece:
                                if t_first_tok is None:
                                    t_first_tok = time.perf_counter()
                                chunks_count += 1
                                completion_text.append(piece)

                    t_end = time.perf_counter()
                    prompt_tok = (usage_info or {}).get("prompt_tokens")
                    comp_tok = (usage_info or {}).get("completion_tokens") or chunks_count
                    ttft_ms = ((t_first_tok - t_req0) * 1000.0) if t_first_tok else None
                    decode_s = (t_end - t_first_tok) if t_first_tok else 0.0
                    tok_s = (comp_tok / decode_s) if decode_s > 0 else 0.0
                    vram_peak = gpu_mem_used_mib()

                    # Ler estatisticas do servidor Colibri
                    time.sleep(0.5)
                    server_log.flush()
                    log_content = server_log_path.read_text(encoding="utf-8", errors="replace")

                    prefix_prompt = None
                    m_pref = re.search(r"\[PREFIX\] (?:reusing (\d+) of (\d+) prompt tokens|no reuse: .*? prompt=(\d+))", log_content)
                    if m_pref:
                        prefix_prompt = int(m_pref.group(2) or m_pref.group(3) or target)

                    prompt_final = prompt_tok or prefix_prompt or target
                    actual_ctx = prompt_final + comp_tok
                    actual_kv_mib = kv_occupied_bytes(actual_ctx) / 2**20

                    m_lookup = re.search(r"\[qwen36 lookup\] turn \d+: ([\d.]+) tokens/forward .*?acceptance ([\d.]+)%", log_content)
                    lookup_accept = None
                    if m_lookup:
                        try:
                            lookup_accept = float(m_lookup.group(2))
                        except (IndexError, ValueError):
                            pass

                    m_gate = re.search(r"\[qwen36 spec gate\] turn \d+: T\(1\) ([\d.]+) ms", log_content)
                    gate_t1 = None
                    if m_gate:
                        try:
                            gate_t1 = float(m_gate.group(1))
                        except (IndexError, ValueError):
                            pass

                    # Metas do usuario
                    meets_min_100 = tok_s >= 100.0
                    meets_mean_120 = tok_s >= 120.0
                    reached_200 = tok_s >= 200.0

                    row.update({
                        "status": "SUCCESS",
                        "prompt_tokens_actual": prompt_final,
                        "completion_tokens": comp_tok,
                        "context_positions": actual_ctx,
                        "actual_kv_mib": actual_kv_mib,
                        "actual_kv_gib": actual_kv_mib / 1024.0,
                        "ttft_ms": ttft_ms,
                        "decode_s": decode_s,
                        "tok_s": tok_s,
                        "vram_peak_mib": vram_peak,
                        "vram_pct_of_6gb": round((vram_peak / 6144.0) * 100.0, 1),
                        "lookup_acceptance_pct": lookup_accept,
                        "gate_t1_ms": gate_t1,
                        "meets_min_100_toks": meets_min_100,
                        "meets_mean_120_toks": meets_mean_120,
                        "reached_200_toks": reached_200,
                        "sample_output": ("".join(completion_text[:20]) + "...") if completion_text else "",
                    })

                    log.info("[%s] SUCESSO: Contexto=%d | KV Cache=%.1f MiB (%.2f GiB) | TTFT=%.1f ms | "
                             "Velocidade=%.1f tok/s | VRAM=%d MiB (%.1f%%) | Lookup=%s%% | Gate T(1)=%s ms",
                             name, actual_ctx, actual_kv_mib, actual_kv_mib / 1024.0, ttft_ms or -1,
                             tok_s, vram_peak, row["vram_pct_of_6gb"], str(lookup_accept), str(gate_t1))

                    if not meets_min_100:
                        log.warning("[%s] ATENCAO: Velocidade de %.1f tok/s caiu abaixo da meta minima de 100 tok/s!", name, tok_s)

        except Exception as e:
            log.exception("[%s] Excecao durante execucao: %s", name, e)
            row.update({"status": "EXCEPTION", "error": str(e)})
        finally:
            kill_tree(proc)
            server_log.close()

        results.append(row)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = OUT_DIR / f"kv_stress_results_{stamp}.json"
        out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        if row.get("status") not in ("SUCCESS",):
            log.warning("[%s] Rompimento detectado no marco %s: %s", name, name, row.get("error"))

    log.info("\n==============================================================================")
    log.info("    TABELA CONSOLIDADA DO TESTE DE ESTRESSE DE KV CACHE                       ")
    log.info("==============================================================================")
    log.info("%-18s | %-10s | %-11s | %-10s | %-10s | %-10s | %-10s",
             "Checkpoint", "Contexto", "KV Cache", "TTFT (ms)", "tok/s", "VRAM MiB", "Meta >=100")
    for r in results:
        ctx_s = str(r.get("context_positions") or r.get("target_tokens"))
        kv_s = f"{r.get('actual_kv_mib', r.get('expected_kv_mib')):.1f} MiB"
        ttft_s = f"{r.get('ttft_ms', 0):.0f}" if r.get('ttft_ms') else "N/A"
        toks_s = f"{r.get('tok_s', 0):.1f}" if r.get('tok_s') else "ERR"
        vram_s = str(r.get("vram_peak_mib", "N/A"))
        meta_s = "SIM" if r.get("meets_min_100_toks") else "NAO"
        log.info("%-18s | %-10s | %-11s | %-10s | %-10s | %-10s | %-10s",
                 r["checkpoint"], ctx_s, kv_s, ttft_s, toks_s, vram_s, meta_s)

    log.info("Arquivo de resultados final salvo em: %s", out_file)
    return 0

if __name__ == "__main__":
    sys.exit(main())
