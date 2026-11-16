"""Build gateways and the router from settings.

This module and the gateway modules are the only places that know concrete
gateway classes (T-LLM-01).
"""

from __future__ import annotations

from collections.abc import Mapping

from tancrede.config.settings import GatewayConfig, Settings
from tancrede.domain.errors import ConfigError
from tancrede.models.mock import MockModelGateway
from tancrede.models.openai_compat import OpenAICompatibleGateway
from tancrede.models.plugins import GatewayFactory
from tancrede.models.router import EndpointGuard, ModelRouter
from tancrede.models.types import ModelGateway


def build_gateway(
    name: str, config: GatewayConfig, plugin_factories: Mapping[str, GatewayFactory]
) -> ModelGateway:
    if config.type == "mock":
        return MockModelGateway(name)
    if config.type == "openai":
        if not config.base_url or not config.model:
            raise ConfigError(f"gateway {name}: base_url and model are required")
        return OpenAICompatibleGateway(
            name,
            config.base_url,
            config.model,
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            timeout_s=config.timeout_s,
        )
    factory = plugin_factories.get(config.type)
    if factory is None:
        raise ConfigError(f"gateway {name}: no plugin named '{config.type}' is available")
    gateway = factory(name, config)
    if not isinstance(gateway, ModelGateway):
        raise ConfigError(f"gateway {name}: plugin '{config.type}' returned an invalid gateway")
    return gateway


def build_router(
    settings: Settings,
    *,
    plugin_factories: Mapping[str, GatewayFactory] | None = None,
    guard: EndpointGuard | None = None,
) -> ModelRouter:
    if not settings.gateways or settings.default_gateway is None:
        raise ConfigError("at least one gateway and a default_gateway are required")
    factories = plugin_factories or {}
    gateways = {
        name: build_gateway(name, cfg, factories) for name, cfg in settings.gateways.items()
    }
    return ModelRouter(gateways, settings.default_gateway, settings.routing, guard)
