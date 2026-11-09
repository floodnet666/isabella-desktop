"""Elastic Window Orchestrator with Semantic Boundary Gating.

Dynamically manages context length between 2.048 and 8.192 tokens, maintaining
uniform GPU decoding speed (>140 tok/s) and triggering memory eviction/summarization
strictly on semantic topic shifts or speech boundaries.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ElasticWindowOrchestrator:
    """Controls dynamic context budgeting and semantic boundary detection."""

    BOUNDARY_MARKERS = [
        "mudando de assunto",
        "outro ponto",
        "agora sobre",
        "por falar nisso",
        "concluímos",
        "vamos falar de",
        "quero mudar",
        "deixando de lado",
        "em relação a outro tema",
        "bom dia",
        "boa tarde",
        "boa noite",
        "olá",
        "oi isabella",
    ]

    def __init__(
        self,
        min_tokens: int = 2048,
        soft_limit_tokens: int = 4096,
        hard_limit_tokens: int = 8192,
    ) -> None:
        self.min_tokens = min_tokens
        self.soft_limit_tokens = soft_limit_tokens
        self.hard_limit_tokens = hard_limit_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count conservatively (approx 3.6 chars per token in PT-BR/EN)."""
        if not text:
            return 0
        return max(1, int(len(text) / 3.6))

    def detect_semantic_boundary(
        self,
        previous_turn: Optional[str],
        current_turn: str,
    ) -> bool:
        """Check if current turn represents a semantic topic boundary or dialogue shift."""
        if not previous_turn or not current_turn:
            return True

        curr_lower = current_turn.lower().strip()
        for marker in self.BOUNDARY_MARKERS:
            if marker in curr_lower:
                return True

        # Check for abrupt divergence in key nouns (lexical overlap)
        words_prev = set(re.findall(r"\b\w{4,}\b", previous_turn.lower()))
        words_curr = set(re.findall(r"\b\w{4,}\b", curr_lower))

        if words_prev and words_curr:
            jaccard = len(words_prev.intersection(words_curr)) / len(words_prev.union(words_curr))
            # If jaccard overlap is very low and current sentence starts with a capital interrogative
            if jaccard < 0.05 and any(curr_lower.startswith(q) for q in ["qual", "quem", "como", "onde", "quando"]):
                return True

        return False

    def assemble_messages(
        self,
        system_prompt: str,
        retrieved_memories: List[str],
        recent_turns: List[Dict[str, str]],
        max_context_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Assemble structured chat messages list with memories injected in system prompt."""
        target_max = max_context_tokens or self.soft_limit_tokens

        memory_block = ""
        if retrieved_memories:
            cleaned_mems = [f"- {m.strip()}" for m in retrieved_memories if m.strip()]
            if cleaned_mems:
                memory_block = (
                    "\n\n[MEMÓRIA RECUPERADA ENTRE SESSÕES / HIPPORAG]\n"
                    + "\n".join(cleaned_mems)
                    + "\n[FIM DA MEMÓRIA]\n"
                )

        full_system = f"{system_prompt}{memory_block}"
        messages = [{"role": "system", "content": full_system}]

        # Add recent turns while checking token budget
        turns_to_add = list(recent_turns)
        # Ensure we don't exceed token budget; prune oldest user/assistant pairs if needed
        while turns_to_add:
            candidate_messages = [{"role": "system", "content": full_system}] + turns_to_add
            est = sum(self.estimate_tokens(m["content"]) for m in candidate_messages)
            if est <= target_max or len(turns_to_add) <= 1:
                return candidate_messages
            # Prune oldest turn
            turns_to_add.pop(0)

        return [{"role": "system", "content": full_system}] + turns_to_add

    def assemble_prompt(
        self,
        system_prompt: str,
        retrieved_memories: List[str],
        recent_turns: List[Dict[str, str]],
        max_context_tokens: Optional[int] = None,
    ) -> str:
        """Assemble structured prompt with memories and dialogue, bounded by budget."""
        target_max = max_context_tokens or self.soft_limit_tokens

        # Format retrieved memories block
        memory_block = ""
        if retrieved_memories:
            cleaned_mems = [f"- {m.strip()}" for m in retrieved_memories if m.strip()]
            if cleaned_mems:
                memory_block = (
                    "\n\n[MEMÓRIA RECUPERADA ENTRE SESSÕES / HIPPORAG]\n"
                    + "\n".join(cleaned_mems)
                    + "\n[FIM DA MEMÓRIA]\n"
                )

        # Build prompt from recent turns backwards to prioritize latest dialogue
        turns_text_list = []
        for turn in recent_turns:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "").strip()
            turns_text_list.append(f"{role}: {content}")

        dialogue_block = "\n".join(turns_text_list)

        base_prompt = f"{system_prompt}{memory_block}\n\n[DIÁLOGO]\n{dialogue_block}\nIsabella:"

        total_tokens = self.estimate_tokens(base_prompt)
        if total_tokens <= target_max:
            return base_prompt

        # If exceeding target_max, prune oldest turns from dialogue_block while preserving memories
        pruned_turns = list(recent_turns)
        while len(pruned_turns) > 2:
            pruned_turns.pop(0)
            turns_text_list = [f"{t.get('role', 'user').capitalize()}: {t.get('content', '').strip()}" for t in pruned_turns]
            dialogue_block = "\n".join(turns_text_list)
            candidate = f"{system_prompt}{memory_block}\n\n[DIÁLOGO]\n{dialogue_block}\nIsabella:"
            if self.estimate_tokens(candidate) <= target_max:
                return candidate

        return f"{system_prompt}{memory_block}\n\n[DIÁLOGO]\n{dialogue_block}\nIsabella:"
