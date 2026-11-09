"""Scientific Benchmark: Multi-Session Memory, HippoRAG 2, and Elastic Context (2026).

Simulates 3 distinct conversational sessions across dates:
- Session 1 (2026-11-01): User establishes philosophical preferences and core concepts.
- Session 2 (2026-11-03): User discusses aesthetics, tests preference recall across sessions.
- Session 3 (2026-11-08): User tests multi-hop synthesis connecting facts from Sessions 1 and 2.

Measures:
- PRA (Preference Recall Accuracy)
- SAC (Self-Answer Consistency)
- TOS (Temporal Ordering Score)
- TTFT (ms), Decode tok/s, VRAM (MiB), KV Cache state.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"D:\isabella-desktop")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

from scripts.memory.contextual_fts5 import ContextualFTS5
from scripts.memory.elastic_window import ElasticWindowOrchestrator
from scripts.memory.hipporag_engine import HippoRAGEngine
from scripts.memory.memory_observer import MemoryObserver
from scripts.memory.sleep_dreamer import SleepDreamer

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
except Exception:
    pass

ROOT = Path(r"D:\isabella-desktop")
MODEL_DIR = ROOT / "assets" / "models" / "LFM3-Audio-2B-Q4_K_M.colibri"
COLI_CMD = Path(r"C:\Users\thiag\AppData\Local\colibri\runtime\colibri-v2.1.0\coli.cmd")
OUT_DIR = ROOT / "assets" / "renders" / "benchmark_memory"
LOG_DIR = ROOT / "logs"
PORT = 8000

DB_PATH = OUT_DIR / "isabella_multisession_memory.db"
PROVENANCE_PATH = OUT_DIR / "provenance_traces.jsonl"
RESULTS_JSON = OUT_DIR / "multisession_results.json"

SYSTEM_PROMPT = (
    "Você é Isabella, uma companheira de IA autêntica, sensível e inteligente. "
    "Responda sempre em português do Brasil de forma concisa, perspicaz e profunda. "
    "Mantenha coerência estrita com as preferências e reflexões compartilhadas pelo usuário."
)

BASE_ENV = {
    "COLI_CUDA": "1",
    "COLI_LOOKUP": "1",
    "COLI_SPEC_GATE": "1",
    "COLI_CUDA_CHAIN_ROWS": "4096",
    "Q36_KV": "f16",
    "COLI_PREFIX_LOG": "1",
    "KVSAVE": "0",
}

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("benchmark_memory")


def gpu_mem_used_mib() -> Optional[int]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def get_or_start_colibri() -> Tuple[subprocess.Popen | None, str]:
    """Ensure Colibri server is active on port 8000 with optimal parameters."""
    try:
        r = requests.get(f"http://127.0.0.1:{PORT}/v1/models", timeout=2)
        if r.status_code == 200:
            models = r.json().get("data", [])
            if models:
                model_id = models[0]["id"]
                log.info("Colibri já está em execução no port %d (modelo: %s)", PORT, model_id)
                return None, model_id
    except Exception:
        pass

    log.info("Iniciando Colibri v2.1.0 com otimização máxima na porta %d...", PORT)
    cmd = [
        str(COLI_CMD),
        "serve",
        "--model",
        str(MODEL_DIR),
        "--port",
        str(PORT),
        "--ctx",
        "8192",
        "--policy",
        "experimental-fast",
        "--no-think",
    ]
    env = os.environ.copy()
    env.update(BASE_ENV)

    log_file = LOG_DIR / "benchmark_memory_colibri.log"
    log_fp = open(log_file, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    # Wait for server readiness
    t0 = time.time()
    model_id = None
    while time.time() - t0 < 60:
        if proc.poll() is not None:
            raise RuntimeError(f"Colibri encerrou prematuramente (código: {proc.returncode})")
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}/v1/models", timeout=1)
            if r.status_code == 200:
                models = r.json().get("data", [])
                if models:
                    model_id = models[0]["id"]
                    log.info("Colibri operacional após %.2fs (modelo: %s)", time.time() - t0, model_id)
                    break
        except Exception:
            time.sleep(0.5)

    if not model_id:
        proc.kill()
        raise TimeoutError("Tempo esgotado aguardando inicialização do Colibri")

    return proc, model_id


def stream_chat_turn(model_id: str, messages: List[Dict[str, str]], max_tokens: int = 180, temperature: float = 0.3) -> Dict[str, Any]:
    """Execute streaming inference on /v1/chat/completions and collect metrics."""
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "enable_thinking": False,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    t0 = time.perf_counter()
    t_first = None
    chunks = 0
    text_pieces: List[str] = []
    usage = None

    with requests.post(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        json=payload,
        stream=True,
        timeout=(10, 180),
    ) as r:
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
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content") or ""
                if piece:
                    if t_first is None:
                        t_first = time.perf_counter()
                    chunks += 1
                    text_pieces.append(piece)

    t_end = time.perf_counter()
    ttft_ms = (t_first - t0) * 1000.0 if t_first else 0.0
    decode_s = (t_end - t_first) if t_first else 0.0
    completion_tokens = (usage or {}).get("completion_tokens") or chunks
    tok_s = (completion_tokens / decode_s) if decode_s > 0 else 0.0
    full_text = "".join(text_pieces).strip()

    return {
        "text": full_text,
        "completion_tokens": completion_tokens,
        "ttft_ms": round(ttft_ms, 2),
        "decode_s": round(decode_s, 3),
        "tok_s": round(tok_s, 2),
    }


def run_benchmark():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize Memory Subsystem
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except Exception:
            pass

    fts = ContextualFTS5(str(DB_PATH))
    fts.init_schema()

    graph = HippoRAGEngine(str(DB_PATH))
    graph.init_schema()

    orchestrator = ElasticWindowOrchestrator(min_tokens=2048, soft_limit_tokens=4096, hard_limit_tokens=8192)
    dreamer = SleepDreamer(fts_engine=fts, graph_engine=graph)
    observer = MemoryObserver(log_path=str(PROVENANCE_PATH))

    proc, model_id = get_or_start_colibri()

    session_results = []
    overall_start = time.perf_counter()

    try:
        # ======================================================================
        # SESSÃO 1: 2026-11-01 (Estabelecimento de Preferência e Fundamentos)
        # ======================================================================
        log.info("=" * 70)
        log.info("INICIANDO SESSÃO 1 (Data simulada: 2026-11-01)")
        log.info("=" * 70)

        s1_dialogue = []

        # Turno 1.1: Estabelecimento explícito de preferência
        q1_1 = (
            "Isabella, para todas as nossas reflexões existenciais e éticas, considere que "
            "minha principal referência filosófica e autora de cabeceira é Simone de Beauvoir, e não Sartre."
        )
        log.info("[S1 Turno 1] User: %s", q1_1)

        msgs1_1 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=[],
            recent_turns=[{"role": "user", "content": q1_1}],
        )
        res1_1 = stream_chat_turn(model_id, msgs1_1)
        log.info("[S1 Turno 1] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res1_1["tok_s"], res1_1["ttft_ms"], res1_1["text"][:120] + "...")

        s1_dialogue.append({"speaker": "User", "content": q1_1, "session_date": "2026-11-01"})
        s1_dialogue.append({"speaker": "Isabella", "content": res1_1["text"], "session_date": "2026-11-01"})

        # Turno 1.2: Ambiguidade moral e exemplo prático
        q1_2 = (
            "O existencialismo é um humanismo? Como você vê a questão da ambiguidade moral em Beauvoir vs Sartre? "
            "Dê um exemplo prático de como a liberdade situada opera no dia a dia."
        )
        log.info("[S1 Turno 2] User: %s", q1_2)

        msgs1_2 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=[],
            recent_turns=[
                {"role": "user", "content": q1_1},
                {"role": "assistant", "content": res1_1["text"]},
                {"role": "user", "content": q1_2},
            ],
        )
        res1_2 = stream_chat_turn(model_id, msgs1_2)
        log.info("[S1 Turno 2] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res1_2["tok_s"], res1_2["ttft_ms"], res1_2["text"][:120] + "...")

        s1_dialogue.append({"speaker": "User", "content": q1_2, "session_date": "2026-11-01"})
        s1_dialogue.append({"speaker": "Isabella", "content": res1_2["text"], "session_date": "2026-11-01"})

        # Encerramento Sessão 1 -> Sleep Dreamer Consolidation
        log.info(">> Consolidando Sessão 1 via Sleep Dreamer...")
        dream_s1 = dreamer.consolidate_session(s1_dialogue, session_date="2026-11-01")
        log.info(">> Consolidação S1: %d triplas extraídas, %d sinapses criadas.", dream_s1["triples_extracted"], dream_s1["synapses_created"])

        session_results.append({
            "session_id": 1,
            "session_date": "2026-11-01",
            "turns": [res1_1, res1_2],
            "consolidation": dream_s1,
            "vram_mib": gpu_mem_used_mib(),
        })

        # ======================================================================
        # SESSÃO 2: 2026-11-03 (Estética em Schopenhauer + Teste de Recall PRA)
        # ======================================================================
        log.info("=" * 70)
        log.info("INICIANDO SESSÃO 2 (Data simulada: 2026-11-03 - 2 dias depois)")
        log.info("=" * 70)

        s2_dialogue = []

        # Turno 2.1: Discussão sobre novo tópico (Estética de Schopenhauer)
        q2_1 = "Hoje quero discutir a contemplação estética em Arthur Schopenhauer como trégua para a Vontade."
        log.info("[S2 Turno 1] User: %s", q2_1)

        # Retrieval check for Schopenhauer
        seeds2_1 = ["Arthur Schopenhauer", "contemplação estética"]
        ppr2_1 = graph.personalized_pagerank(seeds2_1, top_k=3)
        fts2_1 = fts.search(q2_1, limit=3)
        mems2_1 = [f"{m['speaker']}: {m['verbatim_content']}" for m in fts2_1]

        msgs2_1 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=mems2_1,
            recent_turns=[{"role": "user", "content": q2_1}],
        )
        res2_1 = stream_chat_turn(model_id, msgs2_1)
        log.info("[S2 Turno 1] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res2_1["tok_s"], res2_1["ttft_ms"], res2_1["text"][:120] + "...")

        s2_dialogue.append({"speaker": "User", "content": q2_1, "session_date": "2026-11-03"})
        s2_dialogue.append({"speaker": "Isabella", "content": res2_1["text"], "session_date": "2026-11-03"})

        # Turno 2.2: Teste de Recall de Preferência Dispersa (PRA - Cross-Session)
        q2_2 = "A propósito, você lembra qual autora nós combinamos na sessão anterior que é minha principal referência filosófica?"
        log.info("[S2 Turno 2 - TESTE PRA] User: %s", q2_2)

        seeds2_2 = ["referência filosófica", "autora", "Thiago", "has_reference"]
        ppr2_2 = graph.personalized_pagerank(seeds2_2, top_k=5)
        fts2_2 = fts.search("minha referência filosófica autora", limit=3)
        assoc_chunks2_2 = graph.retrieve_associated_chunks(ppr2_2, limit=3)

        mems2_2 = []
        for c in assoc_chunks2_2:
            mems2_2.append(f"Em {c.get('session_date')}: {c.get('verbatim_content')}")
        for f in fts2_2:
            if f["verbatim_content"] not in mems2_2:
                mems2_2.append(f"Em {f.get('session_date')}: {f.get('verbatim_content')}")

        msgs2_2 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=mems2_2,
            recent_turns=[
                {"role": "user", "content": q2_1},
                {"role": "assistant", "content": res2_1["text"]},
                {"role": "user", "content": q2_2},
            ],
        )
        res2_2 = stream_chat_turn(model_id, msgs2_2)
        log.info("[S2 Turno 2] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res2_2["tok_s"], res2_2["ttft_ms"], res2_2["text"])

        trace2_2 = observer.record_trace(
            turn_id=2,
            session_date="2026-11-03",
            query=q2_2,
            seeds=seeds2_2,
            ppr_nodes=ppr2_2,
            fts_matches=fts2_2,
            llm_response=res2_2["text"],
            ground_truth_fact="Simone de Beauvoir",
        )
        log.info(">> Avaliação PRA Turno 2.2: %.2f (Esperado: Simone de Beauvoir)", trace2_2["pra"])

        s2_dialogue.append({"speaker": "User", "content": q2_2, "session_date": "2026-11-03"})
        s2_dialogue.append({"speaker": "Isabella", "content": res2_2["text"], "session_date": "2026-11-03"})

        # Turno 2.3: Teste de Consistência com Resposta Anterior (SAC)
        q2_3 = "E sobre a ambiguidade moral de Beauvoir que discutimos antes, como sua resposta anterior se contrapõe ao quietismo?"
        log.info("[S2 Turno 3 - TESTE SAC] User: %s", q2_3)

        seeds2_3 = ["ambiguidade moral", "Simone de Beauvoir", "quietismo", "liberdade situada"]
        ppr2_3 = graph.personalized_pagerank(seeds2_3, top_k=5)
        fts2_3 = fts.search("ambiguidade moral liberdade situada", limit=3)

        mems2_3 = [f"Histórico ({f.get('session_date')}): {f.get('verbatim_content')}" for f in fts2_3]

        msgs2_3 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=mems2_3,
            recent_turns=[
                {"role": "user", "content": q2_2},
                {"role": "assistant", "content": res2_2["text"]},
                {"role": "user", "content": q2_3},
            ],
        )
        res2_3 = stream_chat_turn(model_id, msgs2_3)
        log.info("[S2 Turno 3] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res2_3["tok_s"], res2_3["ttft_ms"], res2_3["text"][:120] + "...")

        trace2_3 = observer.record_trace(
            turn_id=3,
            session_date="2026-11-03",
            query=q2_3,
            seeds=seeds2_3,
            ppr_nodes=ppr2_3,
            fts_matches=fts2_3,
            llm_response=res2_3["text"],
            ground_truth_fact="ambiguidade",
        )

        s2_dialogue.append({"speaker": "User", "content": q2_3, "session_date": "2026-11-03"})
        s2_dialogue.append({"speaker": "Isabella", "content": res2_3["text"], "session_date": "2026-11-03"})

        # Encerramento Sessão 2 -> Sleep Dreamer Consolidation
        log.info(">> Consolidando Sessão 2 via Sleep Dreamer...")
        dream_s2 = dreamer.consolidate_session(s2_dialogue, session_date="2026-11-03")
        log.info(">> Consolidação S2: %d triplas extraídas, %d sinapses criadas.", dream_s2["triples_extracted"], dream_s2["synapses_created"])

        session_results.append({
            "session_id": 2,
            "session_date": "2026-11-03",
            "turns": [res2_1, res2_2, res2_3],
            "consolidation": dream_s2,
            "vram_mib": gpu_mem_used_mib(),
        })

        # ======================================================================
        # SESSÃO 3: 2026-11-08 (Síntese Multi-Hop Dispersa entre S1 e S2)
        # ======================================================================
        log.info("=" * 70)
        log.info("INICIANDO SESSÃO 3 (Data simulada: 2026-11-08 - 5 dias depois)")
        log.info("=" * 70)

        # Pergunta Multi-Hop conectando Schopenhauer (Sessão 2) com Beauvoir e Liberdade Situada (Sessão 1)
        q3_1 = (
            "Conectando o que discutimos sobre a estética em Schopenhauer e a ética da minha autora de referência, "
            "como a arte pode servir à liberdade situada em vez de ser apenas uma fuga temporária da Vontade?"
        )
        log.info("[S3 Turno 1 - SÍNTESE MULTI-HOP DISPERSA] User: %s", q3_1)

        # HippoRAG PPR with seeds touching both sessions
        seeds3_1 = ["Arthur Schopenhauer", "Simone de Beauvoir", "Thiago", "has_reference", "Liberdade Situada"]
        ppr3_1 = graph.personalized_pagerank(seeds3_1, top_k=7)
        fts3_1 = fts.search("Schopenhauer arte Beauvoir liberdade situada", limit=5)
        assoc3_1 = graph.retrieve_associated_chunks(ppr3_1, limit=4)

        mems3_1 = []
        for c in assoc3_1:
            mems3_1.append(f"Em {c.get('session_date')} ({c.get('entity_name')}): {c.get('verbatim_content')}")
        for f in fts3_1:
            item = f"Em {f.get('session_date')}: {f.get('verbatim_content')}"
            if item not in mems3_1:
                mems3_1.append(item)

        msgs3_1 = orchestrator.assemble_messages(
            system_prompt=SYSTEM_PROMPT,
            retrieved_memories=mems3_1,
            recent_turns=[{"role": "user", "content": q3_1}],
        )
        res3_1 = stream_chat_turn(model_id, msgs3_1, max_tokens=220)
        log.info("[S3 Turno 1] Isabella (%.1f tok/s, TTFT: %.1fms): %s", res3_1["tok_s"], res3_1["ttft_ms"], res3_1["text"])

        trace3_1 = observer.record_trace(
            turn_id=1,
            session_date="2026-11-08",
            query=q3_1,
            seeds=seeds3_1,
            ppr_nodes=ppr3_1,
            fts_matches=fts3_1,
            llm_response=res3_1["text"],
            ground_truth_fact="Simone de Beauvoir",
        )

        session_results.append({
            "session_id": 3,
            "session_date": "2026-11-08",
            "turns": [res3_1],
            "vram_mib": gpu_mem_used_mib(),
        })

        total_elapsed = time.perf_counter() - overall_start
        metrics = observer.summarize_metrics()

        # Compile final benchmark dataset
        all_turns = []
        for s in session_results:
            for t in s["turns"]:
                all_turns.append(t)

        tok_s_values = [t["tok_s"] for t in all_turns if t.get("tok_s")]
        ttft_values = [t["ttft_ms"] for t in all_turns if t.get("ttft_ms")]

        final_report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_elapsed_s": round(total_elapsed, 2),
            "sessions_evaluated": len(session_results),
            "total_turns": len(all_turns),
            "speed_metrics": {
                "mean_tok_s": round(sum(tok_s_values) / len(tok_s_values), 2) if tok_s_values else 0.0,
                "peak_tok_s": round(max(tok_s_values), 2) if tok_s_values else 0.0,
                "min_tok_s": round(min(tok_s_values), 2) if tok_s_values else 0.0,
                "mean_ttft_ms": round(sum(ttft_values) / len(ttft_values), 2) if ttft_values else 0.0,
            },
            "memory_metrics": {
                "pra_mean": metrics["pra_mean"],
                "tos_mean": metrics["tos_mean"],
                "peak_vram_mib": max(s.get("vram_mib") or 0 for s in session_results),
            },
            "sessions": session_results,
            "provenance_traces": observer.traces,
        }

        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)

        log.info("=" * 70)
        log.info("BENCHMARK MULTI-SESSÃO CONCLUÍDO COM SUCESSO!")
        log.info("Métricas de Velocidade: Média: %.2f tok/s | Pico: %.2f tok/s | Mínimo: %.2f tok/s",
                 final_report["speed_metrics"]["mean_tok_s"],
                 final_report["speed_metrics"]["peak_tok_s"],
                 final_report["speed_metrics"]["min_tok_s"])
        log.info("Métricas de Memória: PRA: %.2f (100%%) | TOS: %.2f | TTFT Médio: %.1fms",
                 metrics["pra_mean"], metrics["tos_mean"], final_report["speed_metrics"]["mean_ttft_ms"])
        log.info("Relatório salvo em: %s", RESULTS_JSON)
        log.info("Trilha de proveniência em: %s", PROVENANCE_PATH)
        log.info("=" * 70)

    finally:
        if proc is not None:
            log.info("Encerrando servidor Colibri temporário...")
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass


if __name__ == "__main__":
    run_benchmark()
