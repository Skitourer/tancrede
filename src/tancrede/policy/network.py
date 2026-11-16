"""Network helpers shared by gateways and the mode guard."""

from __future__ import annotations

import ipaddress

LOOPBACK_NAMES = frozenset({"localhost"})


def is_loopback(host: str) -> bool:
    host = host.lower().strip("[]")
    if host in LOOPBACK_NAMES or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
