from __future__ import annotations

from importlib.metadata import EntryPoint

import pytest

from tancrede.config.settings import GatewayConfig, Settings
from tancrede.domain.errors import ConfigError
from tancrede.models import plugins
from tancrede.models.factory import build_router
from tancrede.models.mock import MockModelGateway


def make_gateway(name: str, config: GatewayConfig) -> MockModelGateway:
    return MockModelGateway(name)


def make_invalid(name: str, config: GatewayConfig) -> object:
    return object()


def _fake_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    eps = [
        EntryPoint("acme", f"{__name__}:make_gateway", plugins.GATEWAY_GROUP),
        EntryPoint("other", f"{__name__}:make_gateway", plugins.GATEWAY_GROUP),
    ]
    monkeypatch.setattr(plugins, "entry_points", lambda group: eps)


def test_discovers_all_plugins_in_open_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch)
    assert set(plugins.discover_gateway_factories()) == {"acme", "other"}


def test_t_mode_04_only_allowed_plugins_are_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch)
    assert set(plugins.discover_gateway_factories(allowed=["acme"])) == {"acme"}


def _settings(plugin_type: str) -> Settings:
    return Settings(default_gateway="org", gateways={"org": GatewayConfig(type=plugin_type)})


def test_plugin_gateway_is_built() -> None:
    router = build_router(_settings("acme"), plugin_factories={"acme": make_gateway})
    assert router.gateway_names == ["org"]


def test_missing_plugin_is_refused() -> None:
    with pytest.raises(ConfigError, match="no plugin named 'acme'"):
        build_router(_settings("acme"), plugin_factories={})


def test_invalid_plugin_gateway_is_refused() -> None:
    with pytest.raises(ConfigError, match="invalid gateway"):
        build_router(_settings("acme"), plugin_factories={"acme": make_invalid})
