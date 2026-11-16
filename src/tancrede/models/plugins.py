"""Plugin discovery through Python entry points (SPEC §6).

A gateway plugin registers, in its own package::

    [project.entry-points."tancrede.gateways"]
    my-gateway = "my_package.module:factory"

where `factory(name: str, config: GatewayConfig) -> ModelGateway`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Collection
from importlib.metadata import entry_points

from tancrede.config.settings import GatewayConfig
from tancrede.models.types import ModelGateway

GATEWAY_GROUP = "tancrede.gateways"
LABEL_GROUP = "tancrede.labels"

GatewayFactory = Callable[[str, GatewayConfig], ModelGateway]

log = logging.getLogger(__name__)


def discover_gateway_factories(allowed: Collection[str] | None = None) -> dict[str, GatewayFactory]:
    """Load gateway plugins; with `allowed` (enclave), skip any other plugin (T-MODE-04)."""
    factories: dict[str, GatewayFactory] = {}
    for ep in entry_points(group=GATEWAY_GROUP):
        if allowed is not None and ep.name not in allowed:
            log.warning("plugin.skipped", extra={"id": ep.name})
            continue
        factories[ep.name] = ep.load()
    return factories
