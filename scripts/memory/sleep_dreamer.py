"""Sleep Dreamer asynchronous background memory consolidator.

Processes completed dialogues during mic inactivity or between sessions, extracting
entities, inferring relational triples, connecting synapses, and resolving temporal validity.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from scripts.memory.contextual_fts5 import ContextualFTS5
from scripts.memory.hipporag_engine import HippoRAGEngine


class SleepDreamer:
    """Consolidates conversational history into associative knowledge graph during idle time."""

    # Patterns to extract user preferences and existential relations
    PREFERENCE_PATTERNS = [
        (r"(?:minha|meu)\s+(?:autora?|referência|filósofo?|livro)\s+(?:principal|favorita?|de cabeceira)?\s+(?:é|seria|foi)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)+)", "has_reference"),
        (r"(?:prefiro|gosto mais de|admiro)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)+)", "prefers"),
        (r"([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)+)\s+(?:escreveu|publicou|autor[a]? de)\s+['\"]?([^'\"\.\,\n]+)['\"]?", "wrote"),
        (r"(?:conceito|noção|ideia)\s+de\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)", "concept"),
    ]

    def __init__(
        self,
        fts_engine: ContextualFTS5,
        graph_engine: HippoRAGEngine,
    ) -> None:
        self.fts = fts_engine
        self.graph = graph_engine

    def extract_triples_from_text(
        self,
        speaker: str,
        text: str,
        session_date: str,
    ) -> List[Tuple[str, str, str, float]]:
        """Extract associative triples from dialogue text via heuristic patterns."""
        triples: List[Tuple[str, str, str, float]] = []

        for pattern, rel_type in self.PREFERENCE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                groups = m.groups()
                if rel_type in ("has_reference", "prefers"):
                    entity = groups[0].strip()
                    triples.append(("Thiago", rel_type, entity, 2.0))
                elif rel_type == "wrote" and len(groups) >= 2:
                    author = groups[0].strip()
                    work = groups[1].strip()
                    triples.append((author, "wrote", work, 1.5))
                elif rel_type == "concept" and len(groups) >= 1:
                    concept_name = groups[0].strip()
                    triples.append((speaker, "discussed_concept", concept_name, 1.0))

        # Direct known entity scanner
        known_entities = [
            "Simone de Beauvoir",
            "Jean-Paul Sartre",
            "Arthur Schopenhauer",
            "Friedrich Nietzsche",
            "Albert Camus",
            "Por uma Moral da Ambiguidade",
            "O Existencialismo é um Humanismo",
            "O Mundo como Vontade e Representação",
            "Liberdade Situada",
            "Ética Existencialista",
        ]
        for ent in known_entities:
            if ent.lower() in text.lower():
                triples.append((speaker, "mentioned", ent, 1.0))

        return triples

    def consolidate_session(
        self,
        turns: List[Dict[str, Any]],
        session_date: str,
    ) -> Dict[str, Any]:
        """Process all turns of a session, storing episodic chunks and updating KG."""
        triples_count = 0
        synapses_count = 0

        for i, turn in enumerate(turns, start=1):
            speaker = turn.get("speaker", "User")
            content = turn.get("content", "")
            context_prefix = turn.get("context_prefix", f"Sessão em {session_date} - Turno {i}")

            chunk_id = self.fts.index_turn(
                session_date=session_date,
                turn_id=i,
                speaker=speaker,
                content=content,
                context_prefix=context_prefix,
            )

            # Extract triples
            extracted = self.extract_triples_from_text(speaker, content, session_date)
            for src, rel, tgt, weight in extracted:
                self.graph.add_triple(src, rel, tgt, session_date, weight=weight)
                triples_count += 1
                # Link synapse between target entity and chunk_id
                self.graph.add_synapse(tgt, chunk_id, weight=weight)
                synapses_count += 1

        return {
            "session_date": session_date,
            "turns_processed": len(turns),
            "triples_extracted": triples_count,
            "synapses_created": synapses_count,
        }
