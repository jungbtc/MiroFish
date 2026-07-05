"""Follow-up Q&A over v2 evidence, graph, simulation logs, and report."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .schemas import SourceCitation, V2RunState


class FollowupQAService:
    def answer(self, state: V2RunState, question: str) -> Dict[str, Any]:
        keywords = self._keywords(question)
        claim_hits = self._rank_claims(state, keywords)
        round_hits = self._rank_rounds(state, keywords)
        chunk_hits = self._rank_chunks(state, keywords)

        citations: List[SourceCitation] = []
        answer_parts: List[str] = []

        if claim_hits:
            top_claim = claim_hits[0]
            citations.extend(top_claim.citations)
            answer_parts.append(f"The closest extracted claim says: {top_claim.text}")

        if round_hits:
            top_round = round_hits[0]
            citations.extend(top_round.citations)
            answer_parts.append(f"In simulation {top_round.round_id}, {top_round.summary}")

        if chunk_hits:
            chunk, doc_filename = chunk_hits[0]
            citations.append(SourceCitation(source_id=chunk.source_id, chunk_id=chunk.chunk_id, label=f"{chunk.source_id}:{chunk.chunk_id.split('_')[-1]}", quote=chunk.text[:220]))
            answer_parts.append(f"The strongest source chunk is from {doc_filename}: {chunk.text[:240]}")

        if not answer_parts:
            answer_parts.append(
                "I could not find a strong match in the uploaded chunks, extracted claims, or simulation logs. "
                "Try asking about a named stakeholder, scenario, risk, or citation."
            )

        unique_citations = []
        seen = set()
        for citation in citations:
            key = (citation.source_id, citation.chunk_id, citation.quote)
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)

        return {
            "question": question,
            "answer": "\n\n".join(answer_parts),
            "citations": [c.model_dump(mode="json") for c in unique_citations[:8]],
        }

    def _keywords(self, question: str) -> List[str]:
        return [
            word.lower()
            for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", question)
            if word.lower() not in {"what", "which", "where", "when", "does", "about", "with", "from", "that", "this"}
        ]

    def _score(self, text: str, keywords: List[str]) -> int:
        lower = text.lower()
        return sum(lower.count(keyword) for keyword in keywords)

    def _rank_claims(self, state: V2RunState, keywords: List[str]):
        scored = [(self._score(claim.text, keywords), claim) for claim in state.claims]
        return [claim for score, claim in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:5]

    def _rank_rounds(self, state: V2RunState, keywords: List[str]):
        scored = [(self._score(round_state.summary, keywords), round_state) for round_state in state.rounds]
        return [round_state for score, round_state in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:5]

    def _rank_chunks(self, state: V2RunState, keywords: List[str]):
        scored = []
        for document in state.documents:
            for chunk in document.chunks:
                scored.append((self._score(chunk.text, keywords), chunk, document.filename))
        return [(chunk, filename) for score, chunk, filename in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:5]
