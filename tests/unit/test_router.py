from __future__ import annotations

import pytest

from tancrede.domain.errors import ConfigError, ModelUnavailable, ModeViolation
from tancrede.domain.task_kind import TaskKind
from tancrede.models import ModelGateway, ModelRequest, ModelRouter
from tancrede.models.mock import MockModelGateway


def _req(kind: TaskKind = TaskKind.ANSWER) -> ModelRequest:
    return ModelRequest(task_kind=kind, prompt="fictitious prompt")


def test_routes_by_task_kind() -> None:
    main, small = MockModelGateway("main"), MockModelGateway("small")
    router = ModelRouter({"main": main, "small": small}, "main", {TaskKind.TAG: "small"})
    assert router.complete(_req(TaskKind.TAG)).gateway == "small"
    assert router.complete(_req(TaskKind.ANSWER)).gateway == "main"


def test_t_llm_02_falls_back_to_default() -> None:
    main, small = MockModelGateway("main"), MockModelGateway("small", available=False)
    router = ModelRouter({"main": main, "small": small}, "main", {TaskKind.TAG: "small"})
    assert router.complete(_req(TaskKind.TAG)).gateway == "main"


def test_t_llm_02_all_down_raises_model_unavailable() -> None:
    main = MockModelGateway("main", available=False)
    small = MockModelGateway("small", available=False)
    router = ModelRouter({"main": main, "small": small}, "main", {TaskKind.TAG: "small"})
    with pytest.raises(ModelUnavailable):
        router.complete(_req(TaskKind.TAG))


class _DenyGuard:
    def __init__(self, deny: str, *, at_startup: bool = True) -> None:
        self.deny = deny
        self.active = at_startup

    def check(self, gateway: ModelGateway) -> None:
        if self.active and gateway.name == self.deny:
            raise ModeViolation(f"gateway {gateway.name} not allowed")


def test_guard_refuses_at_startup() -> None:
    with pytest.raises(ModeViolation):
        ModelRouter({"bad": MockModelGateway("bad")}, "bad", guard=_DenyGuard("bad"))


def test_guard_violation_is_never_swallowed_by_fallback() -> None:
    guard = _DenyGuard("small", at_startup=False)
    router = ModelRouter(
        {"main": MockModelGateway("main"), "small": MockModelGateway("small")},
        "main",
        {TaskKind.TAG: "small"},
        guard=guard,
    )
    guard.active = True  # endpoint changed at runtime
    with pytest.raises(ModeViolation):
        router.complete(_req(TaskKind.TAG))


def test_bad_wiring_is_refused() -> None:
    with pytest.raises(ConfigError):
        ModelRouter({"a": MockModelGateway("a")}, "missing")
    with pytest.raises(ConfigError):
        ModelRouter({"a": MockModelGateway("a")}, "a", {TaskKind.TAG: "missing"})
