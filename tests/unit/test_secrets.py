"""T-DEV-04: a fake secret is caught by the pre-commit secret scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

detect_secrets = pytest.importorskip("detect_secrets")
from detect_secrets.core.secrets_collection import SecretsCollection  # noqa: E402
from detect_secrets.settings import default_settings  # noqa: E402

FAKE_KEY = "AKIA" + "ZQ3DT7EXAMPLE7KEY"  # split so this test file is not flagged itself


def test_t_dev_04_fake_secret_is_detected(tmp_path: Path) -> None:
    leaked = tmp_path / "config.toml"
    leaked.write_text(f'aws_access_key_id = "{FAKE_KEY}"\n', encoding="utf-8")
    secrets = SecretsCollection()
    with default_settings():
        secrets.scan_file(str(leaked))
    assert list(secrets), "the fake key must be flagged"


def test_pre_commit_runs_detect_secrets(repo: Path) -> None:
    config = (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "detect-secrets" in config
    assert (repo / ".secrets.baseline").is_file()
