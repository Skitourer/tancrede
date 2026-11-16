"""SQLite connection and versioned migrations (`PRAGMA user_version`)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS: tuple[str, ...] = (
    # 1 — indexed sources and full-text chunks. Excluded content is never stored.
    """
    CREATE TABLE sources (
        id INTEGER PRIMARY KEY,
        path_ref TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL,
        label TEXT,
        fingerprint TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        indexed_at TEXT NOT NULL
    );
    CREATE VIRTUAL TABLE chunks USING fts5(
        text,
        source_id UNINDEXED,
        locator UNINDEXED,
        tokenize = 'unicode61 remove_diacritics 2'
    );
    """,
)


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection) -> None:
    current = schema_version(conn)
    for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def open_database(path: Path | str) -> sqlite3.Connection:
    # Autocommit mode; writes are grouped with `transaction()`.
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn
