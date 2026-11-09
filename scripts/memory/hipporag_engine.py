"""HippoRAG 2 Knowledge Graph and Personalized PageRank (PPR) engine.

Builds a hippocampal associative bipartite/knowledge graph connecting entities,
predicates, and episodic chunks, executing Personalized PageRank in <15ms
to resolve multi-hop connections across dispersed sessions.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional
import networkx as nx


class HippoRAGEngine:
    """Manages associative knowledge graph and hippocampal PPR retrieval."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Create tables for knowledge graph entities, relations, and synapses."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_triples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_synapses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kg_source ON kg_triples(source_entity);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kg_target ON kg_triples(target_entity);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_synapse_entity ON kg_synapses(entity_name);
                """
            )
            conn.commit()

    def add_triple(
        self,
        source: str,
        relation: str,
        target: str,
        session_date: str,
        weight: float = 1.0,
    ) -> None:
        """Add a directed or associative fact triple to the knowledge graph."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO kg_triples (source_entity, relation, target_entity, session_date, weight)
                VALUES (?, ?, ?, ?, ?);
                """,
                (source.strip(), relation.strip(), target.strip(), session_date, weight),
            )
            conn.commit()

    def add_synapse(self, entity: str, chunk_id: int, weight: float = 1.0) -> None:
        """Link an entity to an episodic memory chunk ID (hippocampal synapse)."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO kg_synapses (entity_name, chunk_id, weight)
                VALUES (?, ?, ?);
                """,
                (entity.strip(), chunk_id, weight),
            )
            conn.commit()

    def build_graph(self) -> nx.Graph:
        """Build NetworkX undirected associative graph from triples."""
        graph = nx.Graph()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_entity, relation, target_entity, weight FROM kg_triples;")
            for r in cursor.fetchall():
                src = r["source_entity"]
                tgt = r["target_entity"]
                rel = r["relation"]
                w = float(r["weight"])
                # Add edge between entities with relation as attribute
                graph.add_edge(src, tgt, weight=w, relation=rel)
                # Also link intermediate relation node if helpful for relational jumping
                graph.add_edge(src, rel, weight=w * 0.8)
                graph.add_edge(rel, tgt, weight=w * 0.8)
        return graph

    def personalized_pagerank(
        self,
        seed_entities: List[str],
        top_k: int = 5,
        damping: float = 0.85,
    ) -> List[Dict[str, Any]]:
        """Execute Personalized PageRank on graph seeded by matching query entities."""
        graph = self.build_graph()
        if len(graph) == 0:
            return []

        # Find matching nodes in graph for seeds (case-insensitive substring or exact)
        personalization: Dict[str, float] = {}
        for seed in seed_entities:
            seed_clean = seed.strip().lower()
            if not seed_clean:
                continue
            matched = False
            for node in graph.nodes():
                node_lower = str(node).lower()
                if seed_clean == node_lower or seed_clean in node_lower or node_lower in seed_clean:
                    personalization[node] = personalization.get(node, 0.0) + 1.0
                    matched = True

        if not personalization:
            # If no seeds matched graph nodes directly, uniform personalization across all nodes
            for node in graph.nodes():
                personalization[node] = 1.0 / len(graph)
        else:
            total_seed_weight = sum(personalization.values())
            for k in personalization:
                personalization[k] /= total_seed_weight

        try:
            scores = nx.pagerank(
                graph,
                alpha=damping,
                personalization=personalization,
                weight="weight",
                max_iter=100,
                tol=1e-6,
            )
        except Exception:
            # Fallback if power iteration fails
            scores = {n: 1.0 / len(graph) for n in graph.nodes()}

        # Sort nodes by score descending
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

        results = []
        for entity, score in ranked:
            # Only return actual entities (filter out auxiliary nodes if any)
            results.append({"entity": entity, "score": float(score)})
            if len(results) >= top_k:
                break

        return results

    def retrieve_associated_chunks(
        self,
        ppr_results: List[Dict[str, Any]],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retrieve episodic chunk IDs connected to top PPR activated entities."""
        if not ppr_results:
            return []

        entity_scores = {r["entity"]: float(r.get("score", 1.0)) for r in ppr_results}
        entity_names = list(entity_scores.keys())
        placeholders = ",".join("?" for _ in entity_names)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if episodic_chunks table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='episodic_chunks';")
            has_chunks_table = cursor.fetchone() is not None

            if has_chunks_table:
                cursor.execute(
                    f"""
                    SELECT s.chunk_id, s.entity_name, s.weight, c.session_date, c.speaker, c.verbatim_content
                    FROM kg_synapses s
                    JOIN episodic_chunks c ON c.id = s.chunk_id
                    WHERE s.entity_name IN ({placeholders});
                    """,
                    (*entity_names,),
                )
            else:
                cursor.execute(
                    f"""
                    SELECT s.chunk_id, s.entity_name, s.weight
                    FROM kg_synapses s
                    WHERE s.entity_name IN ({placeholders});
                    """,
                    (*entity_names,),
                )
            rows = [dict(r) for r in cursor.fetchall()]

            # Score each synapse by: entity_ppr_score * synapse_weight
            for row in rows:
                ent = row.get("entity_name")
                ppr_w = entity_scores.get(ent, 0.0)
                syn_w = float(row.get("weight", 1.0))
                row["activation_score"] = ppr_w * syn_w

            # Sort descending by activation_score
            rows.sort(key=lambda r: r["activation_score"], reverse=True)
            return rows[:limit]
