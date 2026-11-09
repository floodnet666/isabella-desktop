"""Contextual FTS5 BM25 episodic memory module.

Stores conversation turns with situational contextual prefixes (Anthropic-style
Contextual Retrieval) and enables fast BM25 lexical search via SQLite FTS5.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List, Optional


class ContextualFTS5:
    """Manages full-text search index over conversational episodic chunks."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Initialize tables for episodic chunks and FTS5 index."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT NOT NULL,
                    turn_id INTEGER NOT NULL,
                    speaker TEXT NOT NULL,
                    context_prefix TEXT,
                    verbatim_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
                    chunk_id UNINDEXED,
                    context_prefix,
                    verbatim_content,
                    tokenize = 'unicode61 remove_diacritics 2'
                );
                """
            )
            conn.commit()

    def index_turn(
        self,
        session_date: str,
        turn_id: int,
        speaker: str,
        content: str,
        context_prefix: str = "",
    ) -> int:
        """Insert a dialogue turn into episodic storage and index in FTS5."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodic_chunks (session_date, turn_id, speaker, context_prefix, verbatim_content)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_date, turn_id, speaker, context_prefix, content),
            )
            chunk_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO episodic_fts (chunk_id, context_prefix, verbatim_content)
                VALUES (?, ?, ?);
                """,
                (str(chunk_id), context_prefix, content),
            )
            conn.commit()
            return int(chunk_id)

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Sanitize query string for SQLite FTS5 matching."""
        # Remove characters that can break FTS5 grammar
        clean = re.sub(r'[^\w\s]', ' ', query)
        tokens = [t.strip() for t in clean.split() if t.strip()]
        if not tokens:
            return ""
        # Match tokens with OR or prefix matching
        return " OR ".join(f'"{t}"*' for t in tokens)

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search episodic memories using BM25 ranking."""
        fts_query = self._sanitize_query(query)
        if not fts_query:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT 
                        c.id AS chunk_id,
                        c.session_date,
                        c.turn_id,
                        c.speaker,
                        c.context_prefix,
                        c.verbatim_content,
                        bm25(episodic_fts) AS bm25_score
                    FROM episodic_fts f
                    JOIN episodic_chunks c ON c.id = CAST(f.chunk_id AS INTEGER)
                    WHERE episodic_fts MATCH ?
                    ORDER BY bm25_score ASC
                    LIMIT ?;
                    """,
                    (fts_query, limit),
                )
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "chunk_id": r["chunk_id"],
                        "session_date": r["session_date"],
                        "turn_id": r["turn_id"],
                        "speaker": r["speaker"],
                        "context_prefix": r["context_prefix"],
                        "verbatim_content": r["verbatim_content"],
                        "bm25_score": float(r["bm25_score"]),
                    })
                return results
            except sqlite3.OperationalError:
                # Fallback to simple LIKE search if MATCH encounters unexpected syntax
                cursor.execute(
                    """
                    SELECT id AS chunk_id, session_date, turn_id, speaker, context_prefix, verbatim_content, 0.0 AS bm25_score
                    FROM episodic_chunks
                    WHERE verbatim_content LIKE ? OR context_prefix LIKE ?
                    LIMIT ?;
                    """,
                    (f"%{query}%", f"%{query}%", limit),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
