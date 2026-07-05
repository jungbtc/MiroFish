"""Research-pack ingestion for MiroFish v2."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, List

from ..utils.file_parser import FileParser, split_text_into_chunks
from .schemas import ResearchChunk, ResearchDocument
from .storage import V2Storage


class ResearchIngestionService:
    """Turn uploaded or demo documents into cited research chunks."""

    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_uploads(self, run_id: str, uploaded_files: Iterable) -> List[ResearchDocument]:
        pack_dir = V2Storage.pack_dir(run_id)
        pack_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []

        for file_storage in uploaded_files:
            if not file_storage or not getattr(file_storage, "filename", ""):
                continue
            filename = V2Storage.safe_filename(file_storage.filename)
            target = pack_dir / filename
            file_storage.save(str(target))
            paths.append(target)

        return self.ingest_paths(paths)

    def ingest_paths(self, paths: Iterable[Path | str]) -> List[ResearchDocument]:
        documents: List[ResearchDocument] = []
        for path_like in paths:
            path = Path(path_like)
            if not path.exists() or not FileParser.is_supported(str(path)):
                continue
            text = FileParser.extract_text(str(path)).strip()
            if not text:
                continue
            documents.append(self._document_from_text(path.name, text, {"path": str(path)}))
        return documents

    def ingest_inline_documents(self, items: Iterable[Dict[str, str]]) -> List[ResearchDocument]:
        documents: List[ResearchDocument] = []
        for idx, item in enumerate(items, 1):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            filename = item.get("filename") or item.get("title") or f"inline_{idx}.md"
            metadata = {k: v for k, v in item.items() if k not in {"text"}}
            documents.append(self._document_from_text(filename, text, metadata))
        return documents

    def _document_from_text(self, filename: str, text: str, metadata: Dict[str, str]) -> ResearchDocument:
        content_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
        source_id = f"doc_{content_hash[:10]}"
        chunks = self._chunk_text(source_id, text)
        return ResearchDocument(
            document_id=source_id,
            filename=filename,
            content_hash=content_hash,
            text=text,
            chunks=chunks,
            metadata=metadata,
        )

    def _chunk_text(self, source_id: str, text: str) -> List[ResearchChunk]:
        raw_chunks = split_text_into_chunks(text, self.chunk_size, self.chunk_overlap)
        chunks: List[ResearchChunk] = []
        cursor = 0
        for idx, chunk_text in enumerate(raw_chunks, 1):
            start = text.find(chunk_text[:40], cursor)
            if start < 0:
                start = cursor
            end = start + len(chunk_text)
            cursor = max(end - self.chunk_overlap, 0)
            chunks.append(
                ResearchChunk(
                    chunk_id=f"{source_id}_chunk_{idx:03d}",
                    source_id=source_id,
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                )
            )
        return chunks
