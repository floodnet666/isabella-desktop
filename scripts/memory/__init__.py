"""Isabella Desktop Memory Subsystem (2026 Frontier Architecture).

Components:
- ContextualFTS5: SQLite FTS5 episodic storage with context prefixes.
- HippoRAGEngine: Bipartite Hippocampal Knowledge Graph with Personalized PageRank (PPR).
- ElasticWindowOrchestrator: Dynamic context window (2k-8k tokens) with semantic boundary gating.
- SleepDreamer: Asynchronous background memory consolidator.
- MemoryObserver: Provenance path trace logger and evaluation metrics (PRA, SAC, TOS).
"""

from scripts.memory.contextual_fts5 import ContextualFTS5
from scripts.memory.hipporag_engine import HippoRAGEngine
from scripts.memory.elastic_window import ElasticWindowOrchestrator
from scripts.memory.sleep_dreamer import SleepDreamer
from scripts.memory.memory_observer import MemoryObserver

__all__ = [
    "ContextualFTS5",
    "HippoRAGEngine",
    "ElasticWindowOrchestrator",
    "SleepDreamer",
    "MemoryObserver",
]
