"""Deterministic extraction fallback for MiroFish v2."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

from .research_ingestion import _markdown_inline_links, _markdown_reference_links
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
    "improve", "improved", "improvement", "reliability", "benefit", "benefits",
    "readiness", "ready", "reduce", "reduced", "reduction", "loss", "losses",
    "delay", "delayed", "failure", "failed", "capacity", "feasible", "strong",
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
    sentences = []
    for piece in pieces:
        normalized = piece.strip(" -\t\r\n")
        while normalized:
            links = _markdown_inline_links(normalized)
            if not links or links[0][2] != 0:
                break
            normalized = normalized[links[0][3] :].lstrip(" \t-—:;,.")
        if len(normalized) < 25 or normalized.startswith("#") or _is_citation_only(normalized):
            continue
        sentences.append(normalized)
    return sentences


def _is_citation_only(text: str) -> bool:
    value = text.strip().rstrip(".,;:!?").rstrip()
    inline = _markdown_inline_links(value)
    if inline and inline[0][2] == 0 and inline[0][3] == len(value):
        return True
    references = _markdown_reference_links(value)
    if references and references[0][2] == 0 and references[0][3] == len(value):
        return True
    return bool(re.fullmatch(r"https?://\S+", value))


def _visible_markdown_text(
    text: str,
    bound_markers: Iterable[str | None] = (),
) -> str:
    """Remove link destinations and citation-only labels from claim semantics."""
    visible = text
    link_uses = [
        (label, start, end)
        for label, _url, start, end in _markdown_inline_links(text)
    ]
    link_uses.extend(
        (match.group(1).strip(), match.start(), match.end())
        for match in re.finditer(r"\[([^\]\n]+)\]\[([^\]\n]+)\]", text)
    )
    for label, start, end in sorted(link_uses, key=lambda item: item[1], reverse=True):
        before = text[:start].rstrip()
        after = text[end:].strip()
        source_like_label = bool(
            re.search(
                r"\b(?:source|citation|reference|benchmark|report|study|research|"
                r"analysis|review|evidence|article|paper|table|appendix)\b",
                label,
                re.IGNORECASE,
            )
        )
        grammatical_object = bool(
            re.search(
                r"\b(?:to|for|from|with|about|of|by|at|in|on|as|via|choose|"
                r"chooses|chose|chosen|select|selects|selected|adopt|adopts|"
                r"adopted|use|uses|used|using|recommend|recommends|recommended|"
                r"provider|vendor|platform|option|product|service|solution)\s*$",
                before.rstrip(" \t,;:"),
                re.IGNORECASE,
            )
        )
        substantive_terminal_clause = bool(
            len(before) >= 25
            and len(re.findall(r"\b\w+\b", before)) >= 5
            and not grammatical_object
        )
        trailing_citation = bool(
            before
            and not after.strip(" \t\r\n.,;:!?)]}")
            and (_has_claim_signal(before) or substantive_terminal_clause)
        )
        replacement = "" if source_like_label or trailing_citation else label
        visible = visible[:start] + replacement + visible[end:]
    for marker in bound_markers:
        normalized_marker = (marker or "").strip()
        if re.fullmatch(r"\[[^\]\n]+\]", normalized_marker):
            visible = visible.replace(normalized_marker, "")
    visible = re.sub(r"https?://\S+", "", visible)
    visible = re.sub(r"\(\s*\)", "", visible)
    visible = re.sub(r"\s+([.,;:!?])", r"\1", visible)
    return re.sub(r"\s+", " ", visible).strip(" -\t,;:")


def _has_claim_signal(text: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE)
        for keyword in CLAIM_KEYWORDS
    )


def _substantive_quote_match(quote: str, sentence: str) -> bool:
    """Match support quotes without treating short entity labels as evidence.

    Imported PDF/structured citations can carry a supporting excerpt instead
    of an inline marker. A two-word label such as ``Alpha Cloud`` is too vague
    to support every statement that names that entity, so containment is
    accepted only when the overlapping statement is substantial and covers a
    meaningful share of the quote (or one sentence within a longer excerpt).
    """

    def normalized(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:!?\"'()[]{}").casefold()

    def tokens(value: str) -> List[str]:
        return re.findall(r"\b\w+(?:[.'’%-]\w+)*\b", value, re.UNICODE)

    sentence_value = normalized(sentence)
    if not sentence_value:
        return False
    quote_candidates = [normalized(quote)]
    quote_candidates.extend(
        normalized(part)
        for part in re.split(r"(?<=[.!?。！？])\s+|\n+", quote)
        if normalized(part)
    )
    for quote_value in dict.fromkeys(quote_candidates):
        if not quote_value:
            continue
        if quote_value not in sentence_value and sentence_value not in quote_value:
            continue
        shorter = min((quote_value, sentence_value), key=len)
        quote_tokens = tokens(quote_value)
        sentence_tokens = tokens(sentence_value)
        shorter_tokens = tokens(shorter)
        if len(shorter) < 18 or len(shorter_tokens) < 4:
            continue
        coverage = min(len(quote_tokens), len(sentence_tokens)) / max(
            len(quote_tokens), len(sentence_tokens), 1
        )
        if quote_value == sentence_value or coverage >= 0.5:
            return True
    return False


def _sentence_sources(
    sentence: str,
    chunk,
    sentence_start: int | None = None,
) -> List[SourceCitation]:
    """Resolve only citations that can be tied to this statement.

    Page-level membership is deliberately insufficient: a page may contain many
    sources. A citation must share a marker/quote with the sentence or appear as
    the immediately following Markdown citation line.
    """
    resolved: List[SourceCitation] = []
    normalized_sentence = re.sub(r"\s+", " ", sentence).strip()
    if sentence_start is None:
        sentence_start = chunk.text.find(sentence)
    sentence_end = sentence_start + len(sentence) if sentence_start >= 0 else -1
    inline_links = _markdown_inline_links(chunk.text)
    sentence_links = _markdown_inline_links(sentence)
    bare_links = []
    for match in re.finditer(r"https?://[^\s<>\]]+", chunk.text):
        raw_url = match.group(0).rstrip(".,;:!?")
        while raw_url.endswith(")") and raw_url.count(")") > raw_url.count("("):
            raw_url = raw_url[:-1]
        bare_end = match.start() + len(raw_url)
        if any(
            link_start <= match.start() < link_end
            for _label, _url, link_start, link_end in inline_links
        ):
            continue
        bare_links.append((raw_url, match.start(), bare_end))

    def only_citations_between(start: int, end: int) -> bool:
        if start < 0 or end < start:
            return False
        gap = chunk.text[start:end]
        if "\n\n" in gap:
            return False
        # Multiple independent citations may be listed consecutively after one
        # statement. Remove those complete links before checking for prose.
        contained = [
            (link_start - start, link_end - start)
            for _label, _url, link_start, link_end in inline_links
            if start <= link_start and link_end <= end
        ]
        contained.extend(
            (link_start - start, link_end - start)
            for _url, link_start, link_end in bare_links
            if start <= link_start and link_end <= end
        )
        for local_start, local_end in sorted(contained, reverse=True):
            gap = gap[:local_start] + gap[local_end:]
        return not gap.strip(" \t\r\n-—:;,.")

    for citation in chunk.citations:
        marker = (citation.original_marker or "").strip()
        quote = re.sub(r"\s+", " ", citation.quote or "").strip()
        matching_sentence_link = any(
            url == citation.url and marker in {f"[{label}]", label}
            for label, url, _start, _end in sentence_links
        )
        url_is_markdown_destination = any(
            url == citation.url for _label, url, _start, _end in sentence_links
        )
        direct = bool(
            (
                citation.url
                and citation.url in sentence
                and (matching_sentence_link or not url_is_markdown_destination)
            )
            or (
                marker
                and marker in sentence
                and (marker.startswith("[") or marker.startswith("http"))
            )
            or (quote and _substantive_quote_match(quote, normalized_sentence))
        )
        nearest_markdown = False
        nearest_bare = False
        if citation.page_number is None and citation.url and sentence_end >= 0:
            nearest_markdown = any(
                url == citation.url
                and marker in {f"[{label}]", label}
                and link_start >= sentence_end
                and only_citations_between(sentence_end, link_start)
                for label, url, link_start, _link_end in inline_links
            )
            for url, url_start, url_end in bare_links:
                if url != citation.url or url_start < sentence_end:
                    continue
                line_end = chunk.text.find("\n", url_end)
                if line_end < 0:
                    line_end = len(chunk.text)
                tail = chunk.text[url_end:line_end]
                if (
                    only_citations_between(sentence_end, url_start)
                    and not tail.strip(" \t\r.,;:!?")
                ):
                    nearest_bare = True
                    break
        if direct or nearest_markdown or nearest_bare:
            copied = citation.model_copy(deep=True)
            copied.chunk_id = chunk.chunk_id
            resolved.append(copied)

    unique: List[SourceCitation] = []
    seen = set()
    for citation in resolved:
        key = citation.citation_id or (
            citation.url,
            citation.original_marker,
            citation.quote,
            citation.page_number,
        )
        if key not in seen:
            seen.add(key)
            unique.append(citation)
    return unique


def _citation(
    document_id: str,
    chunk_id: str,
    quote: str,
    page_number: int | None = None,
) -> SourceCitation:
    return SourceCitation(
        source_id=document_id,
        chunk_id=chunk_id,
        label=f"{document_id}:{chunk_id.split('_')[-1]}",
        quote=quote[:240],
        source_type="imported_report",
        provenance_status="report_anchor",
        page_number=page_number,
    )


def _citation_identity(citation: SourceCitation):
    return citation.citation_id or (
        citation.source_id,
        citation.chunk_id,
        citation.url,
        citation.original_source_id,
        citation.original_marker,
        citation.quote,
        citation.page_number,
        citation.section,
    )


def _merged_citations(*groups: Iterable[SourceCitation]) -> List[SourceCitation]:
    merged: List[SourceCitation] = []
    seen = set()
    for group in groups:
        for citation in group:
            key = _citation_identity(citation)
            if key in seen:
                continue
            seen.add(key)
            merged.append(citation)
    return merged


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
        corroboration_target_by_text: Dict[str, ExtractedClaim] = {}
        seen_texts_by_document: Dict[str, List[str]] = defaultdict(list)
        structured_texts_by_document: Dict[str, set[str]] = defaultdict(set)
        for doc in documents:
            structured_claims = doc.metadata.get("structured_claims") or []
            for structured_index, structured in enumerate(structured_claims, 1):
                if not isinstance(structured, dict):
                    continue
                claim_text = str(structured.get("text") or "").strip()
                if not claim_text:
                    continue
                chunk = next((item for item in doc.chunks if claim_text in item.text), None)
                if chunk is None and doc.chunks:
                    chunk = doc.chunks[0]
                if chunk is None:
                    continue
                structured_sources = self._structured_sources(doc, structured, chunk.chunk_id)
                normalized = _visible_markdown_text(
                    claim_text,
                    [citation.original_marker for citation in structured_sources],
                )
                if not normalized:
                    continue
                text_key = normalized.lower()
                structured_texts_by_document[doc.document_id].add(text_key)
                seen_texts_by_document[doc.document_id].append(text_key)
                report_anchor = _citation(
                    doc.document_id,
                    chunk.chunk_id,
                    normalized,
                    chunk.page_number,
                )
                timestamp_match = DATE_PATTERN.search(normalized)
                extracted = ExtractedClaim(
                    claim_id=_stable_id(
                        "claim",
                        f"{doc.document_id}:"
                        f"{structured.get('original_claim_id') or structured.get('id') or structured_index}:"
                        f"{normalized}",
                    ),
                    original_claim_id=structured.get("original_claim_id") or structured.get("id"),
                    text=normalized,
                    source_document_id=doc.document_id,
                    source_chunk_id=chunk.chunk_id,
                    confidence=0.86 if structured_sources else 0.72,
                    timestamp=timestamp_match.group(0) if timestamp_match else None,
                    citations=_merged_citations(structured_sources, [report_anchor]),
                    kind="sourced_fact",
                    provenance_status=(
                        "external_citation_preserved" if structured_sources else "report_only"
                    ),
                    is_generated=False,
                )
                # Distinct structured IDs are distinct evidence records even
                # when their normalized claim text is identical.
                claims.append(extracted)
                corroboration_target_by_text.setdefault(text_key, extracted)
            for chunk in doc.chunks:
                sentence_cursor = 0
                for sentence in _sentences(chunk.text):
                    local_start = chunk.text.find(sentence, sentence_cursor)
                    if local_start < 0:
                        local_start = chunk.text.find(sentence)
                    if local_start >= 0:
                        sentence_cursor = local_start + len(sentence)
                    if local_start == 0 and chunk.start_char > 0:
                        preceding = doc.text[: chunk.start_char].rstrip()
                        if preceding and preceding[-1] not in ".!?。！？\n":
                            continue
                    has_signal = _has_claim_signal(sentence)
                    preserved_sources = _sentence_sources(
                        sentence,
                        chunk,
                        local_start if local_start >= 0 else None,
                    )
                    normalized = _visible_markdown_text(
                        sentence,
                        [citation.original_marker for citation in preserved_sources],
                    )
                    if len(normalized) < 25:
                        continue
                    key = normalized.lower()
                    if key in structured_texts_by_document[doc.document_id]:
                        continue
                    timestamp_match = DATE_PATTERN.search(normalized)
                    confidence = 0.62 + (0.1 if has_signal else 0) + (0.08 if timestamp_match else 0)
                    confidence = min(round(confidence, 2), 0.9)
                    report_anchor = _citation(
                        doc.document_id,
                        chunk.chunk_id,
                        normalized,
                        chunk.page_number,
                    )
                    citations = _merged_citations(preserved_sources, [report_anchor])
                    existing = corroboration_target_by_text.get(key)
                    if existing is not None:
                        existing.citations = _merged_citations(existing.citations, citations)
                        if preserved_sources:
                            existing.provenance_status = "external_citation_preserved"
                            existing.confidence = max(existing.confidence, confidence)
                        continue
                    if any(
                        min(len(key), len(previous)) >= 70
                        and (key in previous or previous in key)
                        for previous in seen_texts_by_document[doc.document_id]
                    ):
                        continue
                    seen_texts_by_document[doc.document_id].append(key)
                    extracted = ExtractedClaim(
                        claim_id=_stable_id("claim", f"{doc.document_id}:{chunk.chunk_id}:{normalized}"),
                        text=normalized,
                        source_document_id=doc.document_id,
                        source_chunk_id=chunk.chunk_id,
                        confidence=confidence,
                        timestamp=timestamp_match.group(0) if timestamp_match else None,
                        citations=citations,
                        kind="sourced_fact",
                        provenance_status=(
                            "external_citation_preserved" if preserved_sources else "report_only"
                        ),
                        is_generated=False,
                    )
                    claims.append(extracted)
                    corroboration_target_by_text[key] = extracted
        return claims

    def _structured_sources(
        self,
        document: ResearchDocument,
        structured_claim: Dict,
        chunk_id: str,
    ) -> List[SourceCitation]:
        references = structured_claim.get("citations") or []
        matched: List[SourceCitation] = []
        for reference in references:
            if isinstance(reference, str):
                ref_id = reference
                ref_url = reference if reference.startswith(("http://", "https://")) else None
                ref_quote = None
                ref_label = None
            elif isinstance(reference, dict):
                ref_id = reference.get("id") or reference.get("source_id")
                ref_url = reference.get("url") or reference.get("source_url") or reference.get("link")
                ref_quote = reference.get("quote") or reference.get("excerpt")
                ref_label = (
                    reference.get("label")
                    or reference.get("title")
                    or reference.get("name")
                    or reference.get("marker")
                )
            else:
                continue
            for citation in document.imported_citations:
                if ref_id:
                    matches = ref_id in {
                        citation.original_source_id,
                        citation.original_marker,
                    }
                elif ref_url and ref_quote:
                    matches = ref_url == citation.url and ref_quote == citation.quote
                elif ref_url:
                    matches = ref_url == citation.url
                elif ref_quote:
                    matches = ref_quote == citation.quote
                elif ref_label:
                    matches = ref_label in {
                        citation.label,
                        citation.original_marker,
                    }
                else:
                    matches = False
                if matches:
                    copied = citation.model_copy(deep=True)
                    copied.chunk_id = chunk_id
                    matched.append(copied)
        unique: List[SourceCitation] = []
        seen = set()
        for citation in matched:
            key = citation.citation_id or citation.url
            if key not in seen:
                seen.add(key)
                unique.append(citation)
        return unique

    def extract_entities(self, documents: Iterable[ResearchDocument], claims: List[ExtractedClaim]) -> List[Entity]:
        counts: Counter[str] = Counter()
        citations_by_name: Dict[str, List[SourceCitation]] = defaultdict(list)

        for doc in documents:
            for chunk in doc.chunks:
                for name in self._candidate_entities(chunk.text):
                    counts[name] += 1
                    citations_by_name[name].append(_citation(doc.document_id, chunk.chunk_id, name))

        for claim in claims:
            for name in self._candidate_entities(claim.text):
                counts[name] += 2
                if claim.citations:
                    citations_by_name[name].extend(claim.citations)

        entities: List[Entity] = []
        for name, _count in counts.most_common():
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
                    citations=_merged_citations(citations_by_name[name]),
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
        return events

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
