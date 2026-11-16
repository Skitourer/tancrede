"""Indexing flow: allowed folder → extraction → classification → index | exclusion (SPEC §6)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from tancrede.adapters.sources import SourceRepository
from tancrede.persistence.index_repository import Chunk, IndexRepository
from tancrede.policy.classification import ClassificationFilter, Reason

log = logging.getLogger(__name__)

CHUNK_TARGET_CHARS = 1200


@dataclass
class IndexReport:
    indexed: int = 0
    unchanged: int = 0
    excluded: int = 0
    non_extractable: int = 0
    removed: int = 0


def chunk_text(text: str, target: int = CHUNK_TARGET_CHARS) -> list[Chunk]:
    """Group paragraphs into chunks of about `target` characters."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    buffer: list[str] = []
    first = 1
    for number, para in enumerate(paragraphs, start=1):
        if buffer and sum(len(b) for b in buffer) + len(para) > target:
            chunks.append(Chunk(f"para:{first}-{number - 1}", "\n\n".join(buffer)))
            buffer, first = [], number
        buffer.append(para)
    if buffer:
        chunks.append(Chunk(f"para:{first}-{len(paragraphs)}", "\n\n".join(buffer)))
    return chunks


class IndexService:
    def __init__(
        self,
        sources: SourceRepository,
        classifier: ClassificationFilter,
        repository: IndexRepository,
    ) -> None:
        self._sources = sources
        self._classifier = classifier
        self._repo = repository

    def refresh(self) -> IndexReport:
        report = IndexReport()
        seen: set[str] = set()
        for path in self._sources.list_sources():
            key = str(path)
            seen.add(key)
            # Classified on every refresh: label configuration may have changed.
            document = self._sources.read(path)
            decision = self._classifier.classify(document)
            if not decision.allowed:
                self._repo.remove(key)  # a newly labelled file leaves the index
                if decision.reason is Reason.NON_EXTRACTABLE:
                    report.non_extractable += 1
                else:
                    report.excluded += 1
                continue
            fingerprint = self._sources.fingerprint(path)
            existing = self._repo.get(key)
            if (
                existing
                and existing.fingerprint == fingerprint
                and existing.label == decision.label
            ):
                report.unchanged += 1
                continue
            assert document is not None  # allowed implies extractable
            self._repo.upsert(
                key, document.kind, decision.label, fingerprint, chunk_text(document.text)
            )
            report.indexed += 1
        for stale in self._repo.known_paths() - seen:  # R7
            self._repo.remove(stale)
            report.removed += 1
        log.info(
            "index.refresh",
            extra={"count": report.indexed + report.unchanged, "code": "ok"},
        )
        return report
