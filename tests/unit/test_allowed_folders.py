"""T-CLS-06 and manual exclusions (R2, SPEC §5)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tancrede.adapters import sources as sources_module
from tancrede.adapters.sources import LocalFolderRepository
from tancrede.domain.errors import SourceUnavailable
from tancrede.policy.allowed_folders import AllowedFolders


@pytest.fixture
def tree(tmp_path: Path) -> dict[str, Path]:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    (allowed / "sub").mkdir(parents=True)
    (allowed / "private").mkdir()
    outside.mkdir()
    files = {
        "a": allowed / "a.md",
        "b": allowed / "sub" / "b.md",
        "private": allowed / "private" / "p.md",
        "skip": allowed / "sub" / "skip.md",
        "out": outside / "o.md",
    }
    for path in files.values():
        path.write_text("fictitious", encoding="utf-8")
    return {"allowed": allowed, "outside": outside, **files}


def _repo(tree: dict[str, Path]) -> LocalFolderRepository:
    return LocalFolderRepository(
        AllowedFolders([tree["allowed"]], excluded=[tree["allowed"] / "private", tree["skip"]])
    )


def test_lists_only_allowed_and_not_excluded(tree: dict[str, Path]) -> None:
    listed = set(_repo(tree).list_sources())
    assert listed == {tree["a"].resolve(), tree["b"].resolve()}


def test_t_cls_06_file_outside_allowed_folders_is_never_read(
    tree: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[Path] = []
    monkeypatch.setattr(sources_module, "extract", lambda p: opened.append(p))
    repo = _repo(tree)
    for path in (tree["out"], tree["private"], tree["allowed"] / ".." / "outside" / "o.md"):
        with pytest.raises(SourceUnavailable):
            repo.read(path)
        with pytest.raises(SourceUnavailable):
            repo.fingerprint(path)
    assert opened == []


@pytest.mark.skipif(os.name == "nt", reason="symlinks need extra rights on Windows")
def test_symlink_escaping_allowed_folder_is_ignored(tree: dict[str, Path]) -> None:
    (tree["allowed"] / "link.md").symlink_to(tree["out"])
    (tree["allowed"] / "linkdir").symlink_to(tree["outside"], target_is_directory=True)
    listed = set(_repo(tree).list_sources())
    assert tree["out"].resolve() not in listed
    with pytest.raises(SourceUnavailable):
        _repo(tree).read(tree["allowed"] / "link.md")
