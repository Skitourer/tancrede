from __future__ import annotations

from pathlib import Path

from tancrede.persistence.database import MIGRATIONS, open_database, schema_version
from tancrede.persistence.index_repository import Chunk, IndexRepository


def test_migrations_reach_latest_version_and_are_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    conn = open_database(db)
    assert schema_version(conn) == len(MIGRATIONS)
    conn.close()
    conn = open_database(db)
    assert schema_version(conn) == len(MIGRATIONS)
    conn.close()


def test_upsert_versions_and_search() -> None:
    repo = IndexRepository(open_database(":memory:"))
    first = repo.upsert("a.md", "markdown", None, "fp1", [Chunk("para:1-1", "Réunion à Grenoble")])
    assert first.version == 1
    same = repo.upsert("a.md", "markdown", None, "fp1", [Chunk("para:1-1", "Réunion à Grenoble")])
    assert same.version == 1
    changed = repo.upsert("a.md", "markdown", None, "fp2", [Chunk("para:1-1", "Orion bench")])
    assert changed.version == 2
    assert repo.search("orion")[0].path_ref == "a.md"
    assert repo.search("Grenoble") == []  # old chunks replaced


def test_search_ignores_accents_and_fts_syntax() -> None:
    repo = IndexRepository(open_database(":memory:"))
    repo.upsert("a.md", "markdown", None, "fp", [Chunk("para:1-1", "Réunion prévue")])
    assert len(repo.search("reunion PREVUE")) == 1
    assert repo.search('" OR * NEAR(') == []


def test_remove() -> None:
    repo = IndexRepository(open_database(":memory:"))
    repo.upsert("a.md", "markdown", None, "fp", [Chunk("para:1-1", "Orion")])
    assert repo.remove("a.md") and not repo.remove("a.md")
    assert repo.search("Orion") == [] and repo.known_paths() == set()
