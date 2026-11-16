"""Storage of indexed sources and their full-text chunks."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from tancrede.persistence.database import transaction


@dataclass(frozen=True)
class SourceRecord:
    id: int
    path_ref: str
    kind: str
    label: str | None
    fingerprint: str
    version: int


@dataclass(frozen=True)
class Chunk:
    locator: str
    text: str


@dataclass(frozen=True)
class ChunkHit:
    source_id: int
    path_ref: str
    locator: str
    text: str


class IndexRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, path_ref: str) -> SourceRecord | None:
        row = self._conn.execute(
            "SELECT id, path_ref, kind, label, fingerprint, version FROM sources"
            " WHERE path_ref = ?",
            (path_ref,),
        ).fetchone()
        return SourceRecord(**dict(row)) if row else None

    def known_paths(self) -> set[str]:
        return {r[0] for r in self._conn.execute("SELECT path_ref FROM sources")}

    def upsert(
        self,
        path_ref: str,
        kind: str,
        label: str | None,
        fingerprint: str,
        chunks: Sequence[Chunk],
    ) -> SourceRecord:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with transaction(self._conn):
            existing = self.get(path_ref)
            if existing is None:
                cur = self._conn.execute(
                    "INSERT INTO sources (path_ref, kind, label, fingerprint, version, indexed_at)"
                    " VALUES (?, ?, ?, ?, 1, ?)",
                    (path_ref, kind, label, fingerprint, now),
                )
                source_id = cur.lastrowid
            else:
                source_id = existing.id
                new_version = existing.version + (existing.fingerprint != fingerprint)
                self._conn.execute(
                    "UPDATE sources SET kind = ?, label = ?, fingerprint = ?, version = ?,"
                    " indexed_at = ? WHERE id = ?",
                    (kind, label, fingerprint, new_version, now, source_id),
                )
                self._conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            self._conn.executemany(
                "INSERT INTO chunks (text, source_id, locator) VALUES (?, ?, ?)",
                [(c.text, source_id, c.locator) for c in chunks],
            )
        record = self.get(path_ref)
        assert record is not None
        return record

    def remove(self, path_ref: str) -> bool:
        with transaction(self._conn):
            existing = self.get(path_ref)
            if existing is None:
                return False
            self._conn.execute("DELETE FROM chunks WHERE source_id = ?", (existing.id,))
            self._conn.execute("DELETE FROM sources WHERE id = ?", (existing.id,))
        return True

    def search(self, query: str, limit: int = 20) -> list[ChunkHit]:
        """Plain full-text match: every word of `query` must appear (quoted, no FTS syntax)."""
        terms = [t.replace('"', '""') for t in query.split()]
        if not terms:
            return []
        match = " ".join(f'"{t}"' for t in terms)
        rows = self._conn.execute(
            "SELECT c.source_id, s.path_ref, c.locator, c.text FROM chunks c"
            " JOIN sources s ON s.id = c.source_id"
            " WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
            (match, limit),
        ).fetchall()
        return [ChunkHit(int(r[0]), r[1], r[2], r[3]) for r in rows]
