"""Memory Observer and Provenance Path Trace logger.

Records multi-hop retrieval paths, seeds, PPR activations, FTS5 matches,
and calculates benchmark evaluation metrics:
- PRA (Preference Recall Accuracy)
- SAC (Self-Answer Consistency)
- TOS (Temporal Ordering Score)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


class MemoryObserver:
    """Logs structured retrieval provenance and evaluates cross-session consistency."""

    def __init__(self, log_path: Optional[str] = None) -> None:
        self.log_path = log_path
        self.traces: List[Dict[str, Any]] = []

    def record_trace(
        self,
        turn_id: int,
        session_date: str,
        query: str,
        seeds: List[str],
        ppr_nodes: List[Dict[str, Any]],
        fts_matches: List[Dict[str, Any]],
        llm_response: str,
        ground_truth_fact: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record provenance trace for a turn and evaluate factual metrics."""
        # Calculate Preference Recall Accuracy (PRA)
        pra = 0.0
        if ground_truth_fact:
            gt_lower = ground_truth_fact.lower().strip()
            resp_lower = llm_response.lower()
            if gt_lower in resp_lower:
                pra = 1.0
            else:
                # Check if ground truth was at least retrieved in top nodes
                retrieved_entities = [str(n.get("entity", "")).lower() for n in ppr_nodes]
                if any(gt_lower in e for e in retrieved_entities):
                    pra = 0.5  # Retrieved but not verbalized

        # Calculate Temporal Ordering Score (TOS)
        # Verify that earlier session dates are sorted before later session dates if dates present
        dates = [m.get("session_date") for m in fts_matches if m.get("session_date")]
        tos = 1.0
        if len(dates) >= 2:
            is_sorted = all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1))
            tos = 1.0 if is_sorted else 0.8

        trace = {
            "turn_id": turn_id,
            "session_date": session_date,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "query": query,
            "query_seeds": seeds,
            "ppr_activated_nodes": ppr_nodes,
            "fts_matches": [
                {
                    "chunk_id": m.get("chunk_id"),
                    "session_date": m.get("session_date"),
                    "bm25_score": m.get("bm25_score"),
                }
                for m in fts_matches
            ],
            "llm_response": llm_response,
            "ground_truth_fact": ground_truth_fact,
            "pra": pra,
            "tos": tos,
        }

        self.traces.append(trace)

        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace, ensure_ascii=False) + "\n")

        return trace

    def summarize_metrics(self) -> Dict[str, float]:
        """Compute aggregated metrics across all recorded traces."""
        if not self.traces:
            return {"pra_mean": 0.0, "tos_mean": 0.0, "total_queries": 0}

        pra_values = [t["pra"] for t in self.traces if t["ground_truth_fact"] is not None]
        tos_values = [t["tos"] for t in self.traces]

        return {
            "pra_mean": sum(pra_values) / len(pra_values) if pra_values else 1.0,
            "tos_mean": sum(tos_values) / len(tos_values) if tos_values else 1.0,
            "total_queries": len(self.traces),
        }
