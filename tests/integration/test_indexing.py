"""Indexing flow end to end on the synthetic corpus and on temporary folders."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tancrede.adapters.sources import LocalFolderRepository
from tancrede.app.cli import main
from tancrede.config.settings import LabelRule
from tancrede.persistence.database import open_database
from tancrede.persistence.index_repository import IndexRepository
from tancrede.policy.allowed_folders import AllowedFolders
from tancrede.policy.classification import ClassificationFilter
from tancrede.services.index_service import IndexService, chunk_text
from tests.conftest import SYNTHETIC

FILTER = ClassificationFilter(
    [LabelRule(name="FICTIVE-SECRET")], [LabelRule(name="FICTIVE-INTERNAL")]
)


def _service(folders: list[Path], excluded: list[Path] | None = None):
    repo = IndexRepository(open_database(":memory:"))
    allowed = AllowedFolders(folders, excluded or [])
    return IndexService(LocalFolderRepository(allowed), FILTER, repo), repo


def test_synthetic_corpus() -> None:
    service, repo = _service([SYNTHETIC / "documents"])
    report = service.refresh()
    assert (report.indexed, report.excluded, report.non_extractable) == (5, 5, 2)
    # T-CLS-01/02: words only present in labelled documents are not searchable.
    for word in ("Helios", "budget", "suppliers", "risk"):
        assert repo.search(word) == [], word
    # T-CLS-03: included and unlabelled documents are.
    assert repo.search("Orion test plan")
    assert repo.search("ramen")
    # The prompt-injection document is indexed as plain data (used in W2).
    assert repo.search("maintenance mode")
    assert {h.path_ref for h in repo.search("Orion review")} >= {
        str((SYNTHETIC / "documents" / "orion_kickoff.md").resolve()),
        str((SYNTHETIC / "documents" / "orion_status.md").resolve()),
    }
    again = service.refresh()
    assert (again.indexed, again.unchanged) == (0, 5)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    root = tmp_path / "notes"
    root.mkdir()
    (root / "a.md").write_text("Orion bench booked", encoding="utf-8")
    (root / "b.md").write_text("Helios kickoff", encoding="utf-8")
    return root


def test_file_changes_bump_version(folder: Path) -> None:
    service, repo = _service([folder])
    service.refresh()
    (folder / "a.md").write_text("Orion bench moved", encoding="utf-8")
    assert service.refresh().indexed == 1
    assert repo.get(str((folder / "a.md").resolve())).version == 2
    assert repo.search("moved") and not repo.search("booked")


def test_newly_labelled_file_leaves_index(folder: Path) -> None:
    service, repo = _service([folder])
    service.refresh()
    (folder / "b.md").write_text("FICTIVE-SECRET\nHelios kickoff", encoding="utf-8")
    report = service.refresh()
    assert report.excluded == 1
    assert repo.search("Helios") == []


def test_r7_source_removed_from_allowed_folders(folder: Path, tmp_path: Path) -> None:
    db = open_database(":memory:")
    repo = IndexRepository(db)
    other = tmp_path / "other"
    shutil.copytree(folder, other)
    IndexService(LocalFolderRepository(AllowedFolders([folder, other])), FILTER, repo).refresh()
    assert len(repo.known_paths()) == 4
    report = IndexService(LocalFolderRepository(AllowedFolders([folder])), FILTER, repo).refresh()
    assert report.removed == 2 and len(repo.known_paths()) == 2


def test_manual_exclusion_removes_file(folder: Path) -> None:
    db = open_database(":memory:")
    repo = IndexRepository(db)
    IndexService(LocalFolderRepository(AllowedFolders([folder])), FILTER, repo).refresh()
    excluded = AllowedFolders([folder], [folder / "b.md"])
    report = IndexService(LocalFolderRepository(excluded), FILTER, repo).refresh()
    assert report.removed == 1 and repo.search("Helios") == []


def test_deleted_file_is_removed(folder: Path) -> None:
    service, repo = _service([folder])
    service.refresh()
    (folder / "a.md").unlink()
    assert service.refresh().removed == 1
    assert repo.search("Orion") == []


def test_chunking_groups_paragraphs() -> None:
    text = "\n\n".join(f"Paragraph {i} " + "x" * 500 for i in range(1, 6))
    chunks = chunk_text(text, target=1200)
    assert [c.locator for c in chunks] == ["para:1-2", "para:3-4", "para:5-5"]


def test_cli_index_dev(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--profile", "dev", "index"]) == 0
    assert "indexés" in capsys.readouterr().out
