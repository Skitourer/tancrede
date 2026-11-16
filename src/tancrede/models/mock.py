"""In-process mock gateway: the only gateway allowed in `dev` and in tests."""

from __future__ import annotations

from collections.abc import Mapping

from tancrede.domain.errors import ModelUnavailable
from tancrede.domain.task_kind import TaskKind
from tancrede.models.types import ModelRequest, ModelResponse


class MockModelGateway:
    def __init__(
        self,
        name: str = "mock",
        responses: Mapping[TaskKind, str] | None = None,
        *,
        available: bool = True,
    ) -> None:
        self._name = name
        self._responses = dict(responses or {})
        self.available = available
        self.calls: list[ModelRequest] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def endpoint_hosts(self) -> frozenset[str]:
        return frozenset()

    def complete(self, request: ModelRequest) -> ModelResponse:
        if not self.available:
            raise ModelUnavailable(f"gateway {self._name}: unavailable")
        self.calls.append(request)
        text = self._responses.get(request.task_kind, "pong")
        return ModelResponse(text=text, gateway=self._name, model="mock", latency_ms=0)
