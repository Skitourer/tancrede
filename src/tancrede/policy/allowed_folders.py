"""Allowed folders and manual exclusions (R2, SPEC §5)."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path


def _within(path: Path, parent: Path) -> bool:
    return path == parent or path.is_relative_to(parent)


class AllowedFolders:
    def __init__(self, folders: Iterable[Path], excluded: Iterable[Path] = ()) -> None:
        self._folders = [Path(f).resolve() for f in folders]
        self._excluded = [Path(e).resolve() for e in excluded]

    @property
    def folders(self) -> list[Path]:
        return list(self._folders)

    def contains(self, path: Path) -> bool:
        """True if `path` (symlinks resolved) is inside an allowed folder and not excluded."""
        resolved = Path(path).resolve()
        if any(_within(resolved, e) for e in self._excluded):
            return False
        return any(_within(resolved, f) for f in self._folders)

    def iter_files(self) -> Iterator[Path]:
        """Walk allowed folders without following symlinks out of them."""
        seen: set[Path] = set()
        for folder in self._folders:
            if not folder.is_dir():
                continue
            for root, dirs, files in os.walk(folder, followlinks=False):
                root_path = Path(root)
                dirs[:] = [d for d in dirs if self.contains(root_path / d)]
                for name in files:
                    candidate = root_path / name
                    if not self.contains(candidate):
                        continue
                    resolved = candidate.resolve()
                    if resolved not in seen and resolved.is_file():
                        seen.add(resolved)
                        yield resolved
