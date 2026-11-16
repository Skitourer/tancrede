from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SYNTHETIC = REPO / "fixtures" / "synthetic"


@pytest.fixture
def repo() -> Path:
    return REPO


@pytest.fixture
def clean_env(tmp_path: Path) -> dict[str, str]:
    """An environment without any coding-assistant marker, real data under tmp."""
    return {"LOCALAPPDATA": str(tmp_path / "LocalAppData")}
