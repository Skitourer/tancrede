"""Model request / response types and the gateway protocol (SPEC §6, §10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from tancrede.domain.task_kind import TaskKind


@dataclass(frozen=True)
class ModelRequest:
    task_kind: TaskKind
    prompt: str
    system: str | None = None
    max_tokens: int = 512
    temperature: float = 0.2


@dataclass(frozen=True)
class ModelResponse:
    text: str
    gateway: str
    model: str
    latency_ms: int


@runtime_checkable
class ModelGateway(Protocol):
    """A way to reach a language model.

    Implementations raise `ModelUnavailable` when the model cannot answer, with
    a message that never contains prompt or answer text.
    """

    @property
    def name(self) -> str: ...

    @property
    def endpoint_hosts(self) -> frozenset[str]:
        """Hosts this gateway connects to; empty for in-process gateways."""
        ...

    def complete(self, request: ModelRequest) -> ModelResponse: ...
