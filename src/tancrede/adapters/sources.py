"""Read-only access to local sources, limited to allowed folders (R2, T-CLS-06)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from tancrede.adapters.extraction import ExtractedDocument, extract, is_supported
from tancrede.domain.errors import SourceUnavailable
from tancrede.policy.allowed_folders import AllowedFolders


class SourceRepository(Protocol):
    def list_sources(self) -> Iterator[Path]: ...

    def fingerprint(self, path: Path) -> str: ...

    def read(self, path: Path) -> ExtractedDocument | None: ...


class LocalFolderRepository:
    """Local folders; `dev` points it at `fixtures/synthetic/` (synthetic repository)."""

    def __init__(self, allowed: AllowedFolders) -> None:
        self._allowed = allowed

    def list_sources(self) -> Iterator[Path]:
        return (p for p in self._allowed.iter_files() if is_supported(p))

    def _check(self, path: Path) -> Path:
        if not self._allowed.contains(path):
            raise SourceUnavailable("path outside allowed folders")
        return Path(path).resolve()

    def fingerprint(self, path: Path) -> str:
        resolved = self._check(path)
        digest = hashlib.sha256()
        with resolved.open("rb") as fh:
            for block in iter(lambda: fh.read(1 << 16), b""):
                digest.update(block)
        return digest.hexdigest()

    def read(self, path: Path) -> ExtractedDocument | None:
        return extract(self._check(path))
