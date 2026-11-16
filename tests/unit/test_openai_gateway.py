from __future__ import annotations

import json

import httpx
import pytest

from tancrede.domain.errors import ConfigError, ModelUnavailable
from tancrede.domain.task_kind import TaskKind
from tancrede.models import ModelRequest
from tancrede.models.openai_compat import OpenAICompatibleGateway
from tancrede.policy.network import is_loopback

PROMPT = "fictitious question about Orion"


def _gateway(handler, **kwargs) -> OpenAICompatibleGateway:
    return OpenAICompatibleGateway(
        "local",
        "http://localhost:11434/v1",
        "llama3.1:8b",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_sends_chat_completion_and_parses_answer() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"model": "llama3.1:8b", "choices": [{"message": {"content": "pong"}}]}
        )

    gw = _gateway(handler, api_key="sk-test-not-real")
    resp = gw.complete(ModelRequest(TaskKind.ANSWER, PROMPT, system="be brief"))
    assert resp.text == "pong"
    assert resp.gateway == "local"
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test-not-real"
    assert seen["body"]["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": PROMPT},
    ]
    assert gw.endpoint_hosts == frozenset({"localhost"})


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text=f"server error while handling {PROMPT}"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
    ],
)
def test_errors_become_model_unavailable_without_content(response: httpx.Response) -> None:
    gw = _gateway(lambda _req: response)
    with pytest.raises(ModelUnavailable) as info:
        gw.complete(ModelRequest(TaskKind.ANSWER, PROMPT))
    assert "Orion" not in str(info.value)


def test_connection_error_becomes_model_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ModelUnavailable, match="connection failed"):
        _gateway(handler).complete(ModelRequest(TaskKind.ANSWER, PROMPT))


@pytest.mark.parametrize("url", ["ftp://localhost/v1", "localhost:11434", "http:///v1"])
def test_invalid_base_url(url: str) -> None:
    with pytest.raises(ConfigError):
        OpenAICompatibleGateway("x", url, "m")


@pytest.mark.parametrize(
    "host, expected",
    [("localhost", True), ("127.0.0.1", True), ("::1", True), ("api.example.com", False)],
)
def test_is_loopback(host: str, expected: bool) -> None:
    assert is_loopback(host) is expected
