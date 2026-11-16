"""Gateway for any OpenAI-compatible chat-completions endpoint.

Covers local servers (Ollama, llama.cpp server, LM Studio, vLLM) and cloud
APIs. Error messages never include prompt or answer text.
"""

from __future__ import annotations

import ipaddress
import time
from urllib.parse import urlsplit

import httpx

from tancrede.domain.errors import ConfigError, ModelUnavailable
from tancrede.models.types import ModelRequest, ModelResponse

LOOPBACK_NAMES = frozenset({"localhost"})


def is_loopback(host: str) -> bool:
    if host.lower() in LOOPBACK_NAMES or host.lower().endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OpenAICompatibleGateway:
    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        timeout_s: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ConfigError(f"gateway {name}: base_url must be an http(s) URL with a host")
        if not model:
            raise ConfigError(f"gateway {name}: model is required")
        self._name = name
        self._host = parts.hostname
        self._model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout_s,
            transport=transport,
            # Never route loopback traffic through a system proxy.
            trust_env=not is_loopback(self._host),
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def endpoint_hosts(self) -> frozenset[str]:
        return frozenset({self._host})

    def complete(self, request: ModelRequest) -> ModelResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        start = time.perf_counter()
        try:
            response = self._client.post("chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise ModelUnavailable(
                f"gateway {self._name}: connection failed ({type(exc).__name__})"
            ) from None
        latency_ms = round((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            raise ModelUnavailable(f"gateway {self._name}: HTTP {response.status_code}")
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise ModelUnavailable(f"gateway {self._name}: invalid response") from None
        if not isinstance(text, str):
            raise ModelUnavailable(f"gateway {self._name}: invalid response")
        return ModelResponse(
            text=text,
            gateway=self._name,
            model=str(data.get("model") or self._model),
            latency_ms=latency_ms,
        )

    def close(self) -> None:
        self._client.close()
