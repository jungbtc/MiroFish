"""Deterministic extraction fallback for MiroFish v2."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

from .schemas import Entity, Event, ExtractedClaim, Relationship, ResearchDocument, SourceCitation


DATE_PATTERN = re.compile(
    r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+20\d{2})\b",
    re.IGNORECASE,
)

CLAIM_KEYWORDS = {
    "expects", "forecast", "risk", "reported", "said", "announced", "filed",
    "deadline", "debt", "liquidity", "revenue", "court", "regulator",
    "supplier", "creditor", "investor", "customer", "layoff", "restructuring",
    "lawsuit", "approval", "decline", "growth", "increase", "decrease",
}

EVENT_KEYWORDS = {
    "announced", "filed", "approved", "rejected", "signed", "reported",
    "launched", "defaulted", "missed", "deadline", "hearing", "vote",
    "meeting", "strike", "settlement", "restructuring",
}

ENTITY_TYPE_HINTS = {
    "bank": "creditor",
    "capital": "investor",
    "fund": "investor",
    "court": "court/legal actor",
    "ministry": "regulator",
    "commission": "regulator",
    "union": "employee group",
    "employees": "employee group",
    "media": "media/advertiser",
    "advertiser": "media/advertiser",
    "customer": "customer/audience",
    "supplier": "company",
    "competitor": "competitor",
}


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


def _sentences(text: str) -> List[str]:
    pieces = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return [p.strip(" -\t\r\n") for p in pieces if len(p.strip()) >= 25]


def _citation(document_id: str, chunk_id: str, quote: str) -> SourceCitation:
    return SourceCitation(
        source_id=document_id,
        chunk_id=chunk_id,
        label=f"{document_id}:{chunk_id.split('_')[-1]}",
        quote=quote[:240],
    )


class ExtractionService:
    """Extract claims, entities, events, and relationships with heuristics."""

    def extract(self, documents: Iterable[ResearchDocument]) -> Tuple[List[ExtractedClaim], List[Entity], List[Event], List[Relationship]]:
        docs = list(documents)
        claims = self.extract_claims(docs)
        entities = self.extract_entities(docs, claims)
        events = self.extract_events(claims, entities)
        relationships = self.extract_relationships(claims, entities)
        return claims, entities, events, relationships

    def extract_claims(self, documents: Iterable[ResearchDocument]) -> List[ExtractedClaim]:
        claims: List[ExtractedClaim] = []
        seen = set()
        for doc in documents:
            for chunk in doc.chunks:
                for sentence in _sentences(chunk.text):
                    lower = sentence.lower()
                    has_signal = any(keyword in lower for keyword in CLAIM_KEYWORDS)
                    if not has_signal and len(sentence) < 80:
                        continue
                    normalized = re.sub(r"\s+", " ", sentence)
                    key = normalized.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    timestamp_match = DATE_PATTERN.search(normalized)
                    confidence = 0.62 + (0.1 if has_signal else 0) + (0.08 if timestamp_match else 0)
                    confidence = min(round(confidence, 2), 0.9)
                    claims.append(
                        ExtractedClaim(
                            claim_id=_stable_id("claim", f"{doc.document_id}:{chunk.chunk_id}:{normalized}"),
                            text=normalized,
                            source_document_id=doc.document_id,
                            source_chunk_id=chunk.chunk_id,
                            confidence=confidence,
                            timestamp=timestamp_match.group(0) if timestamp_match else None,
                            citations=[_citation(doc.document_id, chunk.chunk_id, normalized)],
                        )
                    )
        return claims[:160]

    def extract_entities(self, documents: Iterable[ResearchDocument], claims: List[ExtractedClaim]) -> List[Entity]:
        counts: Counter[str] = Counter()
        citations_by_name: Dict[str, List[SourceCitation]] = defaultdict(list)

        for doc in documents:
            for chunk in doc.chunks:
                for name in self._candidate_entities(chunk.text):
                    counts[name] += 1
                    if len(citations_by_name[name]) < 3:
                        citations_by_name[name].append(_citation(doc.document_id, chunk.chunk_id, name))

        for claim in claims:
            for name in self._candidate_entities(claim.text):
                counts[name] += 2
                if claim.citations and len(citations_by_name[name]) < 3:
                    citations_by_name[name].append(claim.citations[0])

        entities: List[Entity] = []
        for name, _count in counts.most_common(80):
            if len(name) < 3:
                continue
            entity_type = self._guess_entity_type(name)
            source_ids = sorted({c.source_id for c in citations_by_name[name]})
            entities.append(
                Entity(
                    entity_id=_stable_id("ent", name.lower()),
                    name=name,
                    type=entity_type,
                    source_ids=source_ids,
                    citations=citations_by_name[name][:3],
                )
            )
        return entities

    def extract_events(self, claims: List[ExtractedClaim], entities: List[Entity]) -> List[Event]:
        events: List[Event] = []
        entity_lookup = {entity.name: entity.entity_id for entity in entities}
        for claim in claims:
            lower = claim.text.lower()
            timestamp_match = DATE_PATTERN.search(claim.text)
            if not timestamp_match and not any(keyword in lower for keyword in EVENT_KEYWORDS):
                continue
            involved = [
                entity_id for name, entity_id in entity_lookup.items()
                if name.lower() in lower
            ][:8]
            title = claim.text[:96].rstrip()
            events.append(
                Event(
                    event_id=_stable_id("event", claim.claim_id),
                    title=title,
                    description=claim.text,
                    timestamp=timestamp_match.group(0) if timestamp_match else claim.timestamp,
                    involved_entities=involved,
                    citations=claim.citations,
                )
            )
        return events[:80]

    def extract_relationships(self, claims: List[ExtractedClaim], entities: List[Entity]) -> List[Relationship]:
        relationships: Dict[str, Relationship] = {}
        entity_pairs = [(entity.name.lower(), entity) for entity in entities]
        for claim in claims:
            present = [entity for name, entity in entity_pairs if name in claim.text.lower()]
            for idx, source in enumerate(present[:8]):
                for target in present[idx + 1:8]:
                    rel_type = self._guess_relationship_type(claim.text)
                    key = "|".join(sorted([source.entity_id, target.entity_id]) + [rel_type])
                    if key in relationships:
                        continue
                    relationships[key] = Relationship(
                        relationship_id=_stable_id("rel", key),
                        source_entity_id=source.entity_id,
                        target_entity_id=target.entity_id,
                        type=rel_type,
                        description=claim.text,
                        citations=claim.citations,
                    )
                    if len(relationships) >= 140:
                        return list(relationships.values())
        return list(relationships.values())

    def _candidate_entities(self, text: str) -> List[str]:
        candidates = set()
        for match in re.finditer(r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,4}\b", text):
            value = match.group(0).strip(" .,'")
            if value.lower() in {"the", "a", "an", "on", "in", "for", "and", "but"}:
                continue
            if len(value) >= 3:
                candidates.add(value)
        for phrase in ENTITY_TYPE_HINTS:
            if phrase in text.lower():
                candidates.add(phrase.title())
        return sorted(candidates)

    def _guess_entity_type(self, name: str) -> str:
        lower = name.lower()
        for hint, entity_type in ENTITY_TYPE_HINTS.items():
            if hint in lower:
                return entity_type
        if any(term in lower for term in {"inc", "corp", "ltd", "group", "holdings"}):
            return "company"
        return "company" if len(name.split()) >= 2 else "unknown"

    def _guess_relationship_type(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in {"debt", "loan", "creditor", "liquidity"}):
            return "financial_exposure"
        if any(word in lower for word in {"court", "lawsuit", "hearing", "legal"}):
            return "legal_pressure"
        if any(word in lower for word in {"supplier", "customer", "contract"}):
            return "commercial_dependency"
        if any(word in lower for word in {"media", "reported", "advertiser"}):
            return "information_flow"
        return "related_to"
