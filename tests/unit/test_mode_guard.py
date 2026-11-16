"""T-MODE-01 … T-MODE-03 (SPEC §4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tancrede.app.bootstrap import bootstrap
from tancrede.config.profiles import Profile
from tancrede.config.settings import GatewayConfig, Settings
from tancrede.domain.errors import ModeViolation
from tancrede.domain.task_kind import TaskKind
from tancrede.models import ModelRequest, ModelRouter
from tancrede.models.factory import build_router
from tancrede.models.mock import MockModelGateway
from tancrede.policy.mode_guard import ModeGuard, check_settings

LABELS = {"excluded_labels": [{"name": "FICTIVE-SECRET"}]}


def _settings(mode: str, base_url: str, allowed_hosts: list[str] | None = None) -> Settings:
    return Settings.model_validate(
        {
            "mode": mode,
            "default_gateway": "g",
            "gateways": {"g": {"type": "openai", "base_url": base_url, "model": "m"}},
            "enclave": {"allowed_hosts": allowed_hosts or []},
            "classification": LABELS,
        }
    )


def _router(settings: Settings) -> ModelRouter:
    return build_router(settings, guard=ModeGuard.from_settings(settings))


@pytest.mark.parametrize(
    "url", ["http://localhost:11434/v1", "http://127.0.0.1:8080/v1", "http://[::1]:8000/v1"]
)
def test_enclave_allows_loopback(url: str) -> None:
    _router(_settings("enclave", url))


def test_t_mode_01_enclave_refuses_non_allowed_host() -> None:
    with pytest.raises(ModeViolation, match="api.example.com"):
        _router(_settings("enclave", "https://api.example.com/v1"))


def test_enclave_accepts_allowed_host_case_insensitively() -> None:
    _router(_settings("enclave", "https://AI.example.org/v1", ["ai.example.org"]))


def test_open_mode_accepts_any_host() -> None:
    _router(_settings("open", "https://api.example.com/v1"))


class _MovingGateway(MockModelGateway):
    def __init__(self) -> None:
        super().__init__("moving")
        self.hosts = frozenset({"localhost"})

    @property
    def endpoint_hosts(self) -> frozenset[str]:
        return self.hosts


def test_t_mode_02_runtime_endpoint_change_is_refused() -> None:
    gateway = _MovingGateway()
    router = ModelRouter({"moving": gateway}, "moving", guard=ModeGuard("enclave"))
    request = ModelRequest(TaskKind.ANSWER, "fictitious")
    assert router.complete(request).text == "pong"
    gateway.hosts = frozenset({"api.example.com"})
    with pytest.raises(ModeViolation):
        router.complete(request)
    assert len(gateway.calls) == 1


def test_t_mode_03_enclave_requires_excluded_labels() -> None:
    settings = Settings(default_gateway="m", gateways={"m": GatewayConfig(type="mock")})
    with pytest.raises(ModeViolation, match="excluded label"):
        check_settings(settings)
    check_settings(settings.model_copy(update={"mode": "open"}))


def _write_real_config(home: Path, body: str) -> None:
    home.mkdir(parents=True)
    (home / "config.toml").write_text(body, encoding="utf-8")


def test_t_mode_01_startup_refused(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_real_config(
        home,
        'default_gateway = "g"\n[gateways.g]\ntype = "openai"\n'
        'base_url = "https://api.example.com/v1"\nmodel = "m"\n'
        '[[classification.excluded_labels]]\nname = "FICTIVE-SECRET"\n',
    )
    with pytest.raises(ModeViolation):
        bootstrap(Profile.REAL, environ={"TANCREDE_HOME": str(home)})


def test_t_mode_03_startup_refused(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_real_config(home, 'default_gateway = "g"\n[gateways.g]\ntype = "mock"\n')
    with pytest.raises(ModeViolation):
        bootstrap(Profile.REAL, environ={"TANCREDE_HOME": str(home)})
    assert not (home / "tancrede.db").exists()
