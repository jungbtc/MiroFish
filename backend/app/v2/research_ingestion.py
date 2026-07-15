"""Research-pack ingestion for MiroFish v2."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urlsplit, urlunsplit

from ..utils.file_parser import FileParser, split_text_into_chunks
from .schemas import ResearchChunk, ResearchDocument, SourceCitation
from .storage import V2Storage


def _validated_external_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if len(url) > 4096:
        raise ValueError("Citation URL exceeds the 4096-character safety limit.")
    if any(ord(character) < 32 or character.isspace() for character in url):
        raise ValueError("Citation URL contains invalid whitespace or control characters.")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Citation URLs must use http or https.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Citation URL contains an invalid port.") from exc
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Citation URLs must not contain embedded credentials.")
    return url


def _trim_bare_url(value: str) -> str:
    """Trim prose punctuation without damaging balanced URL parentheses."""
    url = value.strip()
    while url and url[-1] in ".,;:!?":
        url = url[:-1]
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


def _canonical_url_identity(url: str) -> str:
    """Canonicalize only case-insensitive URL components for identity.

    HTTP path, query, and fragment values can be case-sensitive. Lowercasing
    the full URL silently merges distinct cited sources.
    """
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = parsed.port
    if port is not None and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        host = f"{host}:{port}"
    return urlunsplit(
        (parsed.scheme.lower(), host, parsed.path, parsed.query, parsed.fragment)
    )


def _markdown_inline_links(text: str) -> List[Tuple[str, str, int, int]]:
    """Return Markdown links, including balanced and angle-bracket destinations.

    A regex such as ``[^)]+`` truncates valid destinations like
    ``https://example.test/report_(final)``. This small scanner tracks nested
    parentheses and also accepts CommonMark's ``(<destination>)`` form.
    """
    links: List[Tuple[str, str, int, int]] = []
    cursor = 0
    opener = re.compile(r"\[([^\]\n]+)\]\(")
    while True:
        match = opener.search(text, cursor)
        if match is None:
            break
        label = match.group(1).strip()
        destination_start = match.end()
        while destination_start < len(text) and text[destination_start] in " \t":
            destination_start += 1
        url = ""
        closing_index = -1
        if destination_start < len(text) and text[destination_start] == "<":
            destination_end = text.find(">", destination_start + 1)
            if destination_end >= 0:
                url = text[destination_start + 1 : destination_end]
                closing_index = text.find(")", destination_end + 1)
        else:
            index = destination_start
            depth = 0
            while index < len(text):
                character = text[index]
                if character == "(" and (index == 0 or text[index - 1] != "\\"):
                    depth += 1
                elif character == ")" and (index == 0 or text[index - 1] != "\\"):
                    if depth == 0:
                        closing_index = index
                        break
                    depth -= 1
                elif character in " \t\r\n" and depth == 0:
                    # Optional Markdown link title begins after the destination.
                    closing_index = text.find(")", index)
                    break
                index += 1
            url = text[destination_start:index]
        if closing_index < 0:
            cursor = match.end()
            continue
        if url.startswith(("http://", "https://")):
            links.append((label, url, match.start(), closing_index + 1))
        cursor = closing_index + 1
    return links


def _markdown_reference_links(text: str) -> List[Tuple[str, str, int, int]]:
    """Return reference definitions with raw or angle-bracket URLs."""
    references: List[Tuple[str, str, int, int]] = []
    pattern = re.compile(r"(?m)^[ \t]{0,3}\[([^\]\n]+)\]:[ \t]*(.+)$")
    for match in pattern.finditer(text):
        remainder = match.group(2).strip()
        if remainder.startswith("<"):
            end = remainder.find(">", 1)
            url = remainder[1:end] if end >= 0 else ""
        else:
            url = _trim_bare_url(remainder.split(None, 1)[0]) if remainder else ""
        if url.startswith(("http://", "https://")):
            references.append((match.group(1).strip(), url, match.start(), match.end()))
    return references


def _bare_urls(text: str) -> List[str]:
    """Find prose URLs while preserving balanced terminal parentheses."""
    return [
        _trim_bare_url(match.group(0))
        for match in re.finditer(r"https?://[^\s<>\]]+", text)
    ]


def _pdf_link_context(page: Any, link_rect: Any) -> Tuple[str, str]:
    """Find the annotation label and nearest supporting PDF text line.

    PDF URI annotations have geometry but no semantic claim relationship. We
    exclude lines overlapped by a short source label, then select the closest
    preceding line (with a small same-column preference). If the hyperlink is
    embedded in a substantive sentence, that overlapping sentence is itself
    the support quote.
    """
    if not link_rect:
        return "", ""

    lines: List[Dict[str, Any]] = []
    page_dict = page.get_text("dict")
    for block_index, block in enumerate(page_dict.get("blocks") or []):
        for line_index, line in enumerate(block.get("lines") or []):
            spans = line.get("spans") or []
            text = "".join(str(span.get("text") or "") for span in spans).strip()
            bbox = line.get("bbox")
            if not text or not bbox or len(bbox) < 4:
                continue
            lines.append(
                {
                    "text": text,
                    "bbox": tuple(float(value) for value in bbox[:4]),
                    "block": block_index,
                    "line": line_index,
                }
            )

    def overlaps(bbox: Tuple[float, float, float, float]) -> bool:
        x0, y0, x1, y1 = bbox
        return not (
            x1 <= float(link_rect.x0)
            or x0 >= float(link_rect.x1)
            or y1 <= float(link_rect.y0)
            or y0 >= float(link_rect.y1)
        )

    def supporting_statement(anchor: Dict[str, Any]) -> str:
        same_block = sorted(
            (
                line
                for line in lines
                if line["block"] == anchor["block"] and line["line"] <= anchor["line"]
            ),
            key=lambda line: line["line"],
        )
        collected: List[str] = []
        for line in reversed(same_block):
            if collected and re.search(r"[.!?。！？]\s*$", line["text"]):
                break
            collected.insert(0, line["text"])
            if sum(len(part) for part in collected) >= 600:
                break
        return re.sub(r"\s+", " ", " ".join(collected)).strip()

    overlapping = [line for line in lines if overlaps(line["bbox"])]
    link_text = " ".join(line["text"] for line in overlapping).strip()
    substantive_overlap = [
        line
        for line in overlapping
        if re.search(
            r"\b(?:reported|said|found|shows?|showed|indicates?|expects?|forecast|"
            r"increased?|decreased?|declined?|is|are|was|were|has|have|had)\b",
            line["text"],
            re.IGNORECASE,
        )
    ]
    if substantive_overlap:
        support = min(
            substantive_overlap,
            key=lambda line: abs(line["bbox"][1] - float(link_rect.y0)),
        )
        return link_text, supporting_statement(support)

    preceding = [
        line
        for line in lines
        if line not in overlapping and line["bbox"][3] <= float(link_rect.y0) + 1.5
    ]
    if preceding:
        support = min(
            preceding,
            key=lambda line: (
                max(float(link_rect.y0) - line["bbox"][3], 0.0)
                + 0.03 * abs(float(link_rect.x0) - line["bbox"][0])
            ),
        )
        return link_text, supporting_statement(support)

    nearby = [line for line in lines if line not in overlapping]
    if nearby:
        support = min(
            nearby,
            key=lambda line: abs(line["bbox"][1] - float(link_rect.y0)),
        )
        return link_text, supporting_statement(support)
    return link_text, ""


class ResearchIngestionService:
    """Turn uploaded or demo documents into cited research chunks."""

    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_uploads(self, run_id: str, uploaded_files: Iterable) -> List[ResearchDocument]:
        uploads = list(uploaded_files)
        if not uploads:
            raise ValueError("At least one research-pack upload is required.")

        validated: List[Tuple[Any, str]] = []
        for index, file_storage in enumerate(uploads, 1):
            raw_filename = getattr(file_storage, "filename", "") if file_storage else ""
            if not raw_filename:
                raise ValueError(f"Upload {index} is missing a filename.")
            filename = V2Storage.safe_filename(raw_filename)
            if not filename or not FileParser.is_supported(filename):
                suffix = Path(filename or raw_filename).suffix.lower() or "(none)"
                raise ValueError(f"Unsupported research-pack upload format: {suffix}.")
            stream = getattr(file_storage, "stream", None)
            if stream is None:
                raise ValueError(f"Upload {filename} has no readable content stream.")
            try:
                original_position = stream.tell()
                stream.seek(0, 2)
                byte_count = stream.tell()
                stream.seek(original_position)
            except (AttributeError, OSError):
                byte_count = getattr(file_storage, "content_length", None)
            if not isinstance(byte_count, int) or byte_count <= 0:
                raise ValueError(f"Research-pack upload {filename} is empty.")
            validated.append((file_storage, filename))

        pack_dir = V2Storage.pack_dir(run_id)
        pack_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []

        for file_storage, filename in validated:
            target = pack_dir / filename
            duplicate = 2
            while target.exists():
                target = pack_dir / f"{Path(filename).stem}_{duplicate}{Path(filename).suffix}"
                duplicate += 1
            file_storage.save(str(target))
            try:
                target.chmod(0o600)
            except OSError:  # pragma: no cover - permission bits are platform-specific
                pass
            paths.append(target)

        return self.ingest_paths(paths)

    def ingest_paths(self, paths: Iterable[Path | str]) -> List[ResearchDocument]:
        requested_paths = [Path(path_like) for path_like in paths]
        if not requested_paths:
            raise ValueError("At least one research-pack path is required.")
        for path in requested_paths:
            if not path.exists() or not path.is_file():
                raise ValueError(f"Research-pack path does not exist or is not a file: {path}")
            if not FileParser.is_supported(str(path)):
                raise ValueError(f"Unsupported research-pack format: {path.suffix.lower() or '(none)'}.")
            if path.stat().st_size == 0:
                raise ValueError(f"Research-pack file is empty: {path.name}")

        documents: List[ResearchDocument] = []
        for path in requested_paths:
            metadata: Dict[str, Any] = {
                "source_filename": path.name,
                "format": path.suffix.lower().lstrip("."),
            }
            provided_citations: List[Any] = []
            if path.suffix.lower() == ".pdf":
                text, pdf_metadata, provided_citations = self._extract_pdf_with_provenance(path)
                metadata.update(pdf_metadata)
            else:
                text = FileParser.extract_text(str(path)).strip()
            if not text:
                raise ValueError(f"Research-pack file contains no extractable report text: {path.name}")
            if path.suffix.lower() == ".json":
                text, structured_metadata, provided_citations = self._parse_structured_payload(text)
                metadata.update(structured_metadata)
            documents.append(
                self._document_from_text(path.name, text, metadata, provided_citations)
            )
        return documents

    def ingest_inline_documents(self, items: Iterable[Dict[str, Any]]) -> List[ResearchDocument]:
        inline_items = list(items)
        if not inline_items:
            raise ValueError("At least one inline research document is required.")
        documents: List[ResearchDocument] = []
        for idx, item in enumerate(inline_items, 1):
            if not isinstance(item, dict):
                raise ValueError(f"Inline research document {idx} must be an object.")
            text = str(item.get("text") or item.get("report") or item.get("content") or "").strip()
            citation_items = item.get("citations")
            if citation_items is None:
                citation_items = item.get("sources")
            if citation_items is None:
                provided_citations: List[Any] = []
            elif isinstance(citation_items, list):
                provided_citations = list(citation_items)
            else:
                raise ValueError(
                    f"Inline research document {idx} citations must be an array."
                )
            structured_metadata: Dict[str, Any] = {}
            if any(key in item for key in ("sections", "claims", "statements")):
                text, structured_metadata, embedded_citations = self._structured_mapping_to_text(item)
                provided_citations = embedded_citations
            if not text:
                raise ValueError(f"Inline research document {idx} contains no report text or claims.")
            filename = item.get("filename") or item.get("title") or f"inline_{idx}.md"
            metadata = {
                k: v
                for k, v in item.items()
                if k not in {
                    "text",
                    "report",
                    "content",
                    "sections",
                    "claims",
                    "statements",
                    "citations",
                    "sources",
                }
            }
            metadata["format"] = item.get("format") or Path(str(filename)).suffix.lower().lstrip(".") or "structured"
            metadata.update(structured_metadata)
            documents.append(
                self._document_from_text(str(filename), text, metadata, provided_citations)
            )
        return documents

    def _document_from_text(
        self,
        filename: str,
        text: str,
        metadata: Dict[str, Any],
        provided_citations: Optional[Iterable[Any]] = None,
    ) -> ResearchDocument:
        content_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
        provisional_id = f"doc_{content_hash[:10]}"
        imported_citations = self._extract_citations(provisional_id, text, provided_citations or [])
        citation_manifest = [
            {
                "url": citation.url,
                "marker": citation.original_marker,
                "original_source_id": citation.original_source_id,
                "quote": citation.quote,
                "page": citation.page_number,
                "section": citation.section,
            }
            for citation in imported_citations
        ]
        instance_material = json.dumps(
            {"filename": filename, "content_hash": content_hash, "citations": citation_manifest},
            ensure_ascii=False,
            sort_keys=True,
        )
        instance_hash = hashlib.sha1(instance_material.encode("utf-8")).hexdigest()
        source_id = f"doc_{content_hash[:8]}_{instance_hash[:6]}"
        chunks = self._chunk_text(
            source_id,
            text,
            imported_citations,
            metadata.get("page_spans") or [],
        )
        document_format = str(metadata.get("format") or Path(filename).suffix.lower().lstrip(".") or "text")
        direct_sources = len(imported_citations)
        linked_sources = sum(1 for citation in imported_citations if citation.url)
        return ResearchDocument(
            document_id=source_id,
            filename=filename,
            content_hash=content_hash,
            text=text,
            chunks=chunks,
            imported_citations=imported_citations,
            document_format=document_format,
            provenance_summary=(
                f"Imported {document_format} Deep Research output with {direct_sources} preserved "
                f"source citation(s), including {linked_sources} external link(s)."
                if direct_sources
                else f"Imported {document_format} Deep Research output; claims retain report chunk anchors."
            ),
            metadata=metadata,
        )

    def _chunk_text(
        self,
        source_id: str,
        text: str,
        imported_citations: Optional[List[SourceCitation]] = None,
        page_spans: Optional[List[Dict[str, int]]] = None,
    ) -> List[ResearchChunk]:
        located_chunks: List[Tuple[str, int, int, Optional[int]]] = []
        if page_spans:
            for span in page_spans:
                span_start = int(span.get("start_char", 0))
                span_end = int(span.get("end_char", 0))
                page_number = int(span.get("page_number", 0)) or None
                page_text = text[span_start:span_end]
                local_cursor = 0
                for chunk_text in split_text_into_chunks(
                    page_text,
                    self.chunk_size,
                    self.chunk_overlap,
                ):
                    local_start = page_text.find(chunk_text[:40], local_cursor)
                    if local_start < 0:
                        local_start = local_cursor
                    start = span_start + local_start
                    end = start + len(chunk_text)
                    local_cursor = max(local_start + len(chunk_text) - self.chunk_overlap, 0)
                    located_chunks.append((chunk_text, start, end, page_number))
        else:
            cursor = 0
            for chunk_text in split_text_into_chunks(text, self.chunk_size, self.chunk_overlap):
                start = text.find(chunk_text[:40], cursor)
                if start < 0:
                    start = cursor
                end = start + len(chunk_text)
                cursor = max(end - self.chunk_overlap, 0)
                located_chunks.append((chunk_text, start, end, None))

        chunks: List[ResearchChunk] = []
        citations = imported_citations or []
        for idx, (chunk_text, start, end, page_number) in enumerate(located_chunks, 1):
            chunk_citations = [
                citation
                for citation in citations
                if (
                    (citation.url and citation.url in chunk_text)
                    or (citation.original_marker and citation.original_marker in chunk_text)
                    or (citation.quote and citation.quote in chunk_text)
                    or (
                        page_number is not None
                        and citation.page_number is not None
                        and citation.page_number == page_number
                    )
                )
            ]
            chunks.append(
                ResearchChunk(
                    chunk_id=f"{source_id}_chunk_{idx:03d}",
                    source_id=source_id,
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                    citations=chunk_citations,
                    page_number=page_number,
                )
            )
        return chunks

    def _extract_citations(
        self,
        document_id: str,
        text: str,
        provided_citations: Iterable[Any],
    ) -> List[SourceCitation]:
        provided = list(provided_citations)
        provided_source_ids: set[str] = set()
        for item in provided:
            if isinstance(item, str):
                if not item.strip():
                    raise ValueError("Citations cannot be empty.")
                continue
            if not isinstance(item, dict):
                raise ValueError("Citations must be text or objects.")
            if not any(
                item.get(key)
                for key in (
                    "id",
                    "source_id",
                    "url",
                    "source_url",
                    "link",
                    "label",
                    "title",
                    "name",
                    "marker",
                    "quote",
                    "excerpt",
                )
            ):
                raise ValueError("Citation objects must include a source identity.")
            source_key = item.get("id") or item.get("source_id")
            if source_key is None:
                continue
            key = str(source_key).strip()
            if not key:
                raise ValueError("Citation source IDs cannot be empty.")
            if key in provided_source_ids:
                raise ValueError(f"Duplicate citation source ID: {key}")
            provided_source_ids.add(key)

        candidates: List[
            Tuple[
                str,
                str,
                Optional[str],
                Optional[str],
                Optional[int],
                Optional[str],
                Optional[str],
            ]
        ] = []

        captured_text_urls = set()
        for label, url, _start, _end in _markdown_inline_links(text):
            candidates.append((label, url, f"[{label}]", None, None, None, None))
            captured_text_urls.add(_canonical_url_identity(url))
        reference_source_ids: set[str] = set()
        for label, url, _start, _end in _markdown_reference_links(text):
            reference_key = label.casefold()
            if reference_key in reference_source_ids:
                raise ValueError(f"Duplicate Markdown citation source ID: {label}")
            reference_source_ids.add(reference_key)
            candidates.append((label, url, f"[{label}]", None, None, None, None))
            captured_text_urls.add(_canonical_url_identity(url))
        for url in _bare_urls(text):
            if not url or _canonical_url_identity(url) in captured_text_urls:
                continue
            candidates.append((url, url, url, None, None, None, None))

        for index, item in enumerate(provided, 1):
            if isinstance(item, str):
                value = item.strip()
                url = (
                    _validated_external_url(value)
                    if value.lower().startswith(("http://", "https://"))
                    else ""
                )
                candidates.append((value or f"Source {index}", url, value, None, None, None, None))
                continue
            if not isinstance(item, dict):
                continue
            url = _validated_external_url(
                item.get("url") or item.get("source_url") or item.get("link") or ""
            )
            label = str(item.get("label") or item.get("title") or item.get("name") or f"Source {index}").strip()
            marker = str(item.get("marker") or item.get("id") or label).strip()
            original_source_id = str(item.get("id") or item.get("source_id") or "").strip() or None
            quote = str(item.get("quote") or item.get("excerpt") or "").strip() or None
            page_value = item.get("page_number") or item.get("page")
            try:
                page_number = int(page_value) if page_value is not None else None
            except (TypeError, ValueError):
                page_number = None
            section = str(item.get("section") or "").strip() or None
            candidates.append(
                (label, url, marker, quote, page_number, original_source_id, section)
            )

        result: List[SourceCitation] = []
        seen = set()
        for label, url, marker, quote, page_number, original_source_id, section in candidates:
            if not any((url, label, marker, quote, original_source_id)):
                continue
            if url:
                url = _validated_external_url(url)
            canonical_url = _canonical_url_identity(url) if url else ""
            key = (
                canonical_url,
                (marker or "").strip().lower(),
                (quote or "").strip().lower(),
                page_number,
                (original_source_id or "").strip().lower(),
                (section or "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            source_identity = (
                canonical_url
                or (original_source_id or "").strip().lower()
                or (label or marker or quote or "").strip().lower()
            )
            source_hash = hashlib.sha1(source_identity.encode("utf-8")).hexdigest()[:12]
            citation_hash = hashlib.sha1(repr(key).encode("utf-8")).hexdigest()[:12]
            result.append(
                SourceCitation(
                    source_id=f"external_{source_hash}",
                    citation_id=f"cite_{citation_hash}",
                    label=label or url,
                    url=url or None,
                    quote=quote,
                    source_type="external_source",
                    provenance_status="preserved_from_import",
                    original_marker=marker,
                    original_source_id=original_source_id,
                    page_number=page_number,
                    section=section,
                )
            )
        return result

    def _extract_pdf_with_provenance(
        self,
        path: Path,
    ) -> Tuple[str, Dict[str, Any], List[Any]]:
        """Extract PDF text, page locators, and embedded outbound source links."""
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover - dependency declared by the backend
            raise ImportError("PyMuPDF is required to import Deep Research PDF reports") from exc

        page_texts: List[str] = []
        page_spans: List[Dict[str, int]] = []
        provided_citations: List[Any] = []
        cursor = 0
        page_count = 0
        try:
            with fitz.open(path) as document:
                page_count = document.page_count
                for page_index, page in enumerate(document, 1):
                    page_text = page.get_text().strip()
                    if page_text:
                        if page_texts:
                            cursor += 2
                        start = cursor
                        page_texts.append(page_text)
                        cursor += len(page_text)
                        page_spans.append(
                            {
                                "page_number": page_index,
                                "start_char": start,
                                "end_char": cursor,
                            }
                        )
                    for link_index, link in enumerate(page.get_links(), 1):
                        url = link.get("uri")
                        if not url:
                            continue
                        link_rect = link.get("from")
                        link_text, support_quote = _pdf_link_context(page, link_rect)
                        provided_citations.append(
                            {
                                "label": link_text or f"PDF page {page_index} source {link_index}",
                                "url": url,
                                "marker": link_text or url,
                                "quote": support_quote or link_text or None,
                                "page_number": page_index,
                            }
                        )
        except Exception as exc:
            raise ValueError(f"Invalid or unreadable PDF: {path.name}") from exc

        return (
            "\n\n".join(page_texts).strip(),
            {"page_count": page_count, "page_spans": page_spans},
            provided_citations,
        )

    def _parse_structured_payload(self, payload: str) -> Tuple[str, Dict[str, Any], List[Any]]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid structured Deep Research JSON: {exc.msg}") from exc
        if isinstance(data, list):
            data = {"sections": data}
        if not isinstance(data, dict):
            raise ValueError("Structured Deep Research JSON must be an object or a list of sections.")
        return self._structured_mapping_to_text(data)

    def _structured_mapping_to_text(
        self,
        data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any], List[Any]]:
        if not isinstance(data, dict):
            raise ValueError("Structured Deep Research content must be an object.")

        def collection(container: Dict[str, Any], primary: str, alternate: str) -> List[Any]:
            value = container.get(primary)
            if value is None:
                value = container.get(alternate)
            if value is None:
                return []
            if not isinstance(value, list):
                raise ValueError(
                    f"Structured Deep Research field '{primary}' must be an array."
                )
            return list(value)

        parts: List[str] = []
        title = data.get("title") or data.get("name")
        if title:
            parts.append(f"# {title}")

        direct_text = data.get("text") or data.get("report") or data.get("content") or data.get("markdown")
        if direct_text:
            parts.append(str(direct_text))

        sections_value = data.get("sections")
        if sections_value is None:
            sections: List[Any] = []
        elif isinstance(sections_value, list):
            sections = list(sections_value)
        else:
            raise ValueError("Structured Deep Research field 'sections' must be an array.")

        section_records: List[Tuple[Optional[str], Dict[str, Any]]] = []
        claim_records: List[Tuple[Optional[str], Any]] = []

        def walk_sections(items: List[Any], parent: Optional[str] = None) -> None:
            for index, section in enumerate(items, 1):
                if isinstance(section, str):
                    parts.append(section)
                    continue
                if not isinstance(section, dict):
                    raise ValueError(
                        f"Structured Deep Research section {index} must be text or an object."
                    )
                heading = section.get("title") or section.get("heading")
                section_name = str(heading).strip() if heading else f"Section {index}"
                section_path = f"{parent} / {section_name}" if parent else section_name
                body = section.get("text") or section.get("content") or section.get("body")
                if heading:
                    parts.append(f"## {heading}")
                if body:
                    parts.append(str(body))
                section_records.append((section_path, section))
                for claim in collection(section, "claims", "statements"):
                    claim_records.append((section_path, claim))
                    if isinstance(claim, str):
                        parts.append(f"- {claim}")
                    elif isinstance(claim, dict):
                        claim_text = claim.get("text") or claim.get("claim") or claim.get("statement")
                        if claim_text:
                            parts.append(f"- {claim_text}")
                nested = section.get("sections")
                if nested is not None:
                    if not isinstance(nested, list):
                        raise ValueError("Nested structured sections must be an array.")
                    walk_sections(nested, section_path)

        walk_sections(sections)

        top_claims = collection(data, "claims", "statements")
        for claim in top_claims:
            claim_records.append((None, claim))
            if isinstance(claim, str):
                parts.append(f"- {claim}")
            elif isinstance(claim, dict):
                claim_text = claim.get("text") or claim.get("claim") or claim.get("statement")
                if claim_text:
                    parts.append(f"- {claim_text}")

        citation_registry: Dict[str, Dict[str, Any]] = {}
        embedded_citations: List[Any] = []

        def normalized_citation(item: Any, section: Optional[str]) -> Any:
            if isinstance(item, str):
                value = item.strip()
                if not value:
                    raise ValueError("Structured citations cannot be empty.")
                if value.lower().startswith(("http://", "https://")):
                    return {
                        "label": value,
                        "url": value,
                        "marker": value,
                        "section": section,
                    }
                return {"label": value, "marker": value, "section": section}
            if not isinstance(item, dict):
                raise ValueError("Structured citations must be text or objects.")
            copied = dict(item)
            if section and not copied.get("section"):
                copied["section"] = section
            return copied

        def is_reference_only(item: Any) -> bool:
            return isinstance(item, dict) and bool(item.get("id") or item.get("source_id")) and not any(
                value
                for key, value in item.items()
                if key not in {"id", "source_id", "section"}
            )

        def register_source(item: Any, section: Optional[str], context: str) -> Dict[str, Any]:
            citation = normalized_citation(item, section)
            if not any(
                citation.get(key)
                for key in (
                    "id",
                    "source_id",
                    "url",
                    "source_url",
                    "link",
                    "label",
                    "title",
                    "name",
                    "marker",
                    "quote",
                    "excerpt",
                )
            ):
                raise ValueError(f"Structured citation in {context} has no source identity.")
            source_key = citation.get("id") or citation.get("source_id")
            if source_key:
                key = str(source_key).strip()
                if not key:
                    raise ValueError(f"Structured citation in {context} has an empty source ID.")
                if key in citation_registry:
                    raise ValueError(f"Duplicate structured source ID: {key}")
                citation_registry[key] = citation
            embedded_citations.append(citation)
            return citation

        for citation in collection(data, "citations", "sources"):
            register_source(citation, None, "top-level citations")
        for section_name, section in section_records:
            for citation in collection(section, "citations", "sources"):
                register_source(citation, section_name, f"section {section_name}")

        # Inline source declarations are registered before references are
        # resolved so a section-local claim may cite a declaration that occurs
        # later in the structured payload.
        inline_declarations: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for claim_index, (section_name, claim) in enumerate(claim_records):
            if not isinstance(claim, dict):
                continue
            for citation_index, citation in enumerate(collection(claim, "citations", "sources")):
                if isinstance(citation, str):
                    if citation.lower().startswith(("http://", "https://")):
                        inline_declarations[(claim_index, citation_index)] = register_source(
                            citation, section_name, "inline claim citation"
                        )
                elif isinstance(citation, dict) and not is_reference_only(citation):
                    inline_declarations[(claim_index, citation_index)] = register_source(
                        citation, section_name, "inline claim citation"
                    )

        structured_claims: List[Dict[str, Any]] = []
        dangling_references: List[str] = []
        seen_claim_ids: set[str] = set()
        for claim_index, (section_name, claim) in enumerate(claim_records):
            if isinstance(claim, str):
                claim_text = claim.strip()
                if not claim_text:
                    raise ValueError("Structured claims cannot be empty.")
                structured_claims.append(
                    {
                        "id": None,
                        "original_claim_id": None,
                        "text": claim_text,
                        "citations": [],
                        "section": section_name,
                    }
                )
                continue
            if not isinstance(claim, dict):
                raise ValueError("Structured claims must be text or objects.")
            claim_text = claim.get("text") or claim.get("claim") or claim.get("statement")
            if not str(claim_text or "").strip():
                raise ValueError("Structured claim objects must include non-empty text.")
            claim_id = claim.get("id") or claim.get("claim_id")
            if claim_id is not None:
                claim_id = str(claim_id).strip()
                if not claim_id:
                    raise ValueError("Structured claim IDs cannot be empty.")
                if claim_id in seen_claim_ids:
                    raise ValueError(f"Duplicate structured claim ID: {claim_id}")
                seen_claim_ids.add(claim_id)
            resolved_claim_citations: List[Any] = []
            for citation_index, citation in enumerate(collection(claim, "citations", "sources")):
                if isinstance(citation, str) and not citation.lower().startswith(("http://", "https://")):
                    resolved = citation_registry.get(citation)
                    if resolved is None:
                        dangling_references.append(citation)
                        continue
                    citation = resolved
                elif is_reference_only(citation):
                    reference = citation.get("id") or citation.get("source_id")
                    resolved = citation_registry.get(str(reference)) if reference else None
                    if resolved is None:
                        if reference:
                            dangling_references.append(str(reference))
                        continue
                    citation = resolved
                else:
                    citation = inline_declarations.get((claim_index, citation_index), citation)
                resolved_claim_citations.append(citation)
            structured_claims.append(
                {
                    "id": claim_id,
                    "original_claim_id": claim_id,
                    "text": str(claim_text).strip(),
                    "citations": resolved_claim_citations,
                    "section": section_name,
                }
            )

        if dangling_references:
            missing = ", ".join(sorted(set(dangling_references)))
            raise ValueError(f"Structured Deep Research JSON has dangling citation reference(s): {missing}")

        text = "\n\n".join(part.strip() for part in parts if str(part).strip()).strip()
        if not text:
            raise ValueError("Structured Deep Research JSON contains no report text, sections, or claims.")
        metadata = {
            "format": "structured_json",
            "structured_keys": sorted(data.keys()),
            "source_system": data.get("source_system") or data.get("provider") or "OpenAI Deep Research",
            "structured_claims": structured_claims,
        }
        return text, metadata, embedded_citations
