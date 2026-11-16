from __future__ import annotations

from pathlib import Path

import pytest

from tancrede.config.settings import load_settings, parse_settings
from tancrede.domain.errors import ConfigError
from tancrede.domain.task_kind import TaskKind

EXAMPLE = """
mode = "enclave"
default_gateway = "local"
eval_journal = false

[routing]
tag = "local"

[gateways.local]
type = "openai"
base_url = "http://localhost:11434/v1"
model = "llama3.1:8b"

[enclave]
allowed_hosts = []

[[classification.excluded_labels]]
name = "FICTIVE-SECRET"
patterns = ["FICTIVE-SECRET"]
"""


def test_load_example(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(EXAMPLE, encoding="utf-8")
    settings = load_settings(path)
    assert settings.mode == "enclave"
    assert settings.routing == {TaskKind.TAG: "local"}
    assert settings.gateways["local"].model == "llama3.1:8b"
    assert settings.classification.excluded_labels[0].name == "FICTIVE-SECRET"


def test_api_key_is_never_echoed() -> None:
    settings = parse_settings(
        {
            "default_gateway": "cloud",
            "gateways": {
                "cloud": {
                    "type": "openai",
                    "base_url": "https://x.example",
                    "model": "m",
                    "api_key": "sk-test-not-real",  # pragma: allowlist secret
                },
            },
        }
    )
    assert "sk-test-not-real" not in repr(settings)


@pytest.mark.parametrize(
    "data, fragment",
    [
        ({"default_gateway": "missing"}, "not declared"),
        ({"gateways": {"a": {"type": "mock"}}, "routing": {"tag": "b"}}, "undeclared gateway"),
        ({"mode": "wide-open"}, "mode"),
        ({"unknown_key": 1}, "unknown_key"),
    ],
)
def test_invalid_settings(data: dict, fragment: str) -> None:
    with pytest.raises(ConfigError, match=fragment):
        parse_settings(data)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "nope.toml")
