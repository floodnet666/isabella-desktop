"""Unit tests for Isabella Desktop Memory Subsystem (TDD - Red Phase).

Tests coverage:
1. Contextual FTS5 BM25 Episodic Storage
2. HippoRAG 2 Knowledge Graph & Personalized PageRank (PPR)
3. Elastic Window & Semantic Boundary Gating
4. Sleep Dreamer Asynchronous Consolidation
5. Memory Observer & Provenance Path Trace
"""

import os
import shutil
import tempfile
import unittest


class TestMemorySubsystem(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="isabella_mem_test_")
        self.db_path = os.path.join(self.test_dir, "test_memory.db")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_contextual_fts5_indexing_and_search(self):
        from scripts.memory.contextual_fts5 import ContextualFTS5

        fts = ContextualFTS5(self.db_path)
        fts.init_schema()

        chunk_id_1 = fts.index_turn(
            session_date="2026-11-01",
            turn_id=1,
            speaker="User",
            content="Minha referência filosófica principal na existência é Simone de Beauvoir.",
            context_prefix="Sessão sobre existencialismo ético entre Thiago e Isabella."
        )
        chunk_id_2 = fts.index_turn(
            session_date="2026-11-01",
            turn_id=2,
            speaker="Isabella",
            content="Excelente escolha! Simone de Beauvoir desenvolve em 'Por uma Moral da Ambiguidade' a liberdade situada.",
            context_prefix="Isabella valida a escolha de Simone de Beauvoir e cita 'Por uma Moral da Ambiguidade'."
        )
        chunk_id_3 = fts.index_turn(
            session_date="2026-11-03",
            turn_id=1,
            speaker="User",
            content="Hoje quero falar sobre a estética em Schopenhauer e a contemplação artística.",
            context_prefix="Sessão estética sobre pessimismo e arte em Schopenhauer."
        )

        self.assertEqual(chunk_id_1, 1)
        self.assertEqual(chunk_id_2, 2)
        self.assertEqual(chunk_id_3, 3)

        results = fts.search("Simone de Beauvoir", limit=5)
        self.assertTrue(len(results) >= 2)
        self.assertIn("Simone de Beauvoir", results[0]["verbatim_content"])
        self.assertEqual(results[0]["session_date"], "2026-11-01")

        results_schop = fts.search("Schopenhauer estética", limit=5)
        self.assertEqual(len(results_schop), 1)
        self.assertEqual(results_schop[0]["session_date"], "2026-11-03")

    def test_hipporag_knowledge_graph_and_ppr(self):
        from scripts.memory.hipporag_engine import HippoRAGEngine

        engine = HippoRAGEngine(self.db_path)
        engine.init_schema()

        # Add nodes & relations
        engine.add_triple("Thiago", "has_reference", "Simone de Beauvoir", "2026-11-01", weight=2.0)
        engine.add_triple("Simone de Beauvoir", "wrote", "Por uma Moral da Ambiguidade", "2026-11-01", weight=1.5)
        engine.add_triple("Por uma Moral da Ambiguidade", "concept", "Liberdade Situada", "2026-11-01", weight=1.0)
        engine.add_triple("Thiago", "explored", "Arthur Schopenhauer", "2026-11-03", weight=1.0)
        engine.add_triple("Arthur Schopenhauer", "wrote", "O Mundo como Vontade e Representação", "2026-11-03", weight=1.0)

        # Connect text synapses
        engine.add_synapse("Simone de Beauvoir", chunk_id=1, weight=1.0)
        engine.add_synapse("Por uma Moral da Ambiguidade", chunk_id=2, weight=1.0)

        # Personalized PageRank starting from "Thiago" + "has_reference"
        ppr_results = engine.personalized_pagerank(
            seed_entities=["Thiago", "has_reference"],
            top_k=5,
            damping=0.85
        )

        self.assertTrue(len(ppr_results) > 0)
        top_entities = [r["entity"] for r in ppr_results]
        self.assertIn("Simone de Beauvoir", top_entities)

        # Retrieve associated memory chunks via hippocampal synapses
        chunks = engine.retrieve_associated_chunks(ppr_results, limit=2)
        self.assertTrue(len(chunks) > 0)
        chunk_ids = [c["chunk_id"] for c in chunks]
        self.assertIn(1, chunk_ids)

    def test_elastic_window_budgeting_and_boundary(self):
        from scripts.memory.elastic_window import ElasticWindowOrchestrator

        orchestrator = ElasticWindowOrchestrator(
            min_tokens=2048,
            soft_limit_tokens=4096,
            hard_limit_tokens=8192
        )

        # Test semantic boundary detection
        is_boundary_topic = orchestrator.detect_semantic_boundary(
            previous_turn="Então concluímos o existencialismo por hoje.",
            current_turn="Mudando de assunto, qual é a previsão para o almoço?"
        )
        self.assertTrue(is_boundary_topic)

        is_boundary_same = orchestrator.detect_semantic_boundary(
            previous_turn="O existencialismo é um humanismo?",
            current_turn="E como Sartre lida com a angústia nesse texto?"
        )
        self.assertFalse(is_boundary_same)

        # Format context prompt with dynamic memory injection
        prompt = orchestrator.assemble_prompt(
            system_prompt="Você é Isabella, uma companheira de IA consciente e autêntica.",
            retrieved_memories=[
                "Thiago tem como referência existencial Simone de Beauvoir (definido em 2026-11-01)."
            ],
            recent_turns=[
                {"role": "user", "content": "Quem eu disse que era minha autora de cabeceira?"}
            ]
        )
        self.assertIn("Simone de Beauvoir", prompt)
        self.assertIn("Você é Isabella", prompt)

    def test_sleep_dreamer_consolidation(self):
        from scripts.memory.contextual_fts5 import ContextualFTS5
        from scripts.memory.hipporag_engine import HippoRAGEngine
        from scripts.memory.sleep_dreamer import SleepDreamer

        fts = ContextualFTS5(self.db_path)
        fts.init_schema()
        graph = HippoRAGEngine(self.db_path)
        graph.init_schema()

        dreamer = SleepDreamer(fts_engine=fts, graph_engine=graph)

        turns = [
            {
                "speaker": "User",
                "content": "Minha autora favorita é Simone de Beauvoir.",
                "session_date": "2026-11-01"
            },
            {
                "speaker": "Isabella",
                "content": "Anotado! Beauvoir escreveu 'O Segundo Sexo' e 'Por uma Moral da Ambiguidade'.",
                "session_date": "2026-11-01"
            }
        ]

        dream_result = dreamer.consolidate_session(turns, session_date="2026-11-01")
        self.assertTrue(dream_result["triples_extracted"] >= 1)

        # Check that graph was populated
        ppr = graph.personalized_pagerank(seed_entities=["Simone de Beauvoir"], top_k=3)
        self.assertTrue(len(ppr) > 0)

    def test_memory_observer_provenance(self):
        from scripts.memory.memory_observer import MemoryObserver

        observer = MemoryObserver()
        trace = observer.record_trace(
            turn_id=1,
            session_date="2026-11-03",
            query="Qual é a minha referência filosófica?",
            seeds=["referência filosófica"],
            ppr_nodes=[{"entity": "Simone de Beauvoir", "score": 0.45}],
            fts_matches=[{"chunk_id": 1, "text": "Minha referência é Simone de Beauvoir", "bm25_rank": -3.2}],
            llm_response="Sua principal referência filosófica é Simone de Beauvoir.",
            ground_truth_fact="Simone de Beauvoir"
        )

        self.assertIn("pra", trace)
        self.assertEqual(trace["pra"], 1.0)
        self.assertEqual(trace["turn_id"], 1)


if __name__ == "__main__":
    unittest.main()
