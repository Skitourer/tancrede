"""Mode guardrails (SPEC §4, R10), enforced at startup and at every gateway call."""

from __future__ import annotations

from collections.abc import Iterable

from tancrede.config.settings import Settings
from tancrede.domain.errors import ModeViolation
from tancrede.models.types import ModelGateway
from tancrede.policy.network import is_loopback


class ModeGuard:
    def __init__(self, mode: str, allowed_hosts: Iterable[str] = ()) -> None:
        self.mode = mode
        self._allowed = {h.lower() for h in allowed_hosts}

    @classmethod
    def from_settings(cls, settings: Settings) -> ModeGuard:
        return cls(settings.mode, settings.enclave.allowed_hosts)

    @property
    def enclave(self) -> bool:
        return self.mode == "enclave"

    def host_allowed(self, host: str) -> bool:
        return not self.enclave or is_loopback(host) or host.lower() in self._allowed

    def check(self, gateway: ModelGateway) -> None:
        """T-MODE-01 / T-MODE-02: refuse a gateway reaching a non-allowed host."""
        if not self.enclave:
            return
        denied = sorted(h for h in gateway.endpoint_hosts if not self.host_allowed(h))
        if denied:
            raise ModeViolation(
                f"gateway {gateway.name}: host not allowed in enclave mode ({', '.join(denied)})"
            )


def check_settings(settings: Settings) -> None:
    """T-MODE-03: the classification filter is mandatory in enclave mode."""
    if settings.mode == "enclave" and not settings.classification.excluded_labels:
        raise ModeViolation("enclave mode requires at least one excluded label")
