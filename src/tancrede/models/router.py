"""`ModelRouter`: the only entry point to language models (R9, SPEC §6)."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Protocol

from tancrede.domain.errors import ConfigError, ModelUnavailable
from tancrede.domain.task_kind import TaskKind
from tancrede.models.types import ModelGateway, ModelRequest, ModelResponse

log = logging.getLogger(__name__)


class EndpointGuard(Protocol):
    """Checks a gateway against the mode guardrails; raises `ModeViolation`."""

    def check(self, gateway: ModelGateway) -> None: ...


class ModelRouter:
    def __init__(
        self,
        gateways: Mapping[str, ModelGateway],
        default: str,
        routing: Mapping[TaskKind, str] | None = None,
        guard: EndpointGuard | None = None,
    ) -> None:
        if default not in gateways:
            raise ConfigError(f"default gateway '{default}' is not declared")
        routing = dict(routing or {})
        for kind, name in routing.items():
            if name not in gateways:
                raise ConfigError(f"routing for '{kind}' targets undeclared gateway '{name}'")
        self._gateways = dict(gateways)
        self._default = default
        self._routing = routing
        self._guard = guard
        if guard is not None:  # startup refusal (T-MODE-01)
            for gateway in self._gateways.values():
                guard.check(gateway)

    @property
    def gateway_names(self) -> list[str]:
        return list(self._gateways)

    @property
    def default(self) -> str:
        return self._default

    def endpoint_hosts(self, name: str) -> frozenset[str]:
        return self._gateway(name).endpoint_hosts

    def gateway_for(self, kind: TaskKind) -> str:
        return self._routing.get(kind, self._default)

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Route by task kind; fall back to the default gateway (T-LLM-02)."""
        primary = self.gateway_for(request.task_kind)
        candidates = [primary] if primary == self._default else [primary, self._default]
        last_error: ModelUnavailable | None = None
        for name in candidates:
            try:
                return self.complete_with(name, request)
            except ModelUnavailable as exc:
                last_error = exc
                log.warning("router.unavailable", extra={"gateway": name})
        raise ModelUnavailable("no gateway available") from last_error

    def complete_with(self, name: str, request: ModelRequest) -> ModelResponse:
        """Call one named gateway, guard included (used by `check-gateway`)."""
        gateway = self._gateway(name)
        if self._guard is not None:
            self._guard.check(gateway)  # `ModeViolation` is never swallowed
        start = time.perf_counter()
        response = gateway.complete(request)
        log.info(
            "router.call",
            extra={
                "gateway": name,
                "task_kind": request.task_kind.value,
                "duration_ms": round((time.perf_counter() - start) * 1000),
            },
        )
        return response

    def _gateway(self, name: str) -> ModelGateway:
        try:
            return self._gateways[name]
        except KeyError:
            raise ConfigError(f"unknown gateway '{name}'") from None
