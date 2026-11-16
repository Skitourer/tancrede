"""`tancrede check-gateway` end to end, including the W0 gate on a local
OpenAI-compatible server (simulated here by a tiny HTTP server)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tancrede.app.cli import main


class _FakeOpenAI(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert self.path == "/v1/chat/completions"
        payload = {"model": body["model"], "choices": [{"message": {"content": "pong"}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def fake_server() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_dev_profile_uses_mock(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--profile", "dev", "check-gateway"]) == 0
    out = capsys.readouterr().out
    assert "Passerelle mock" in out and "OK" in out


def test_dev_refuses_config_with_real_gateway(tmp_path: Path) -> None:
    cfg = tmp_path / "dev.toml"
    cfg.write_text(
        'default_gateway = "local"\n[gateways.local]\ntype = "openai"\n'
        'base_url = "http://localhost:1/v1"\nmodel = "m"\n',
        encoding="utf-8",
    )
    assert main(["--profile", "dev", "--config", str(cfg), "check-gateway"]) == 2


def _clean_env(tmp_path: Path) -> dict[str, str]:
    keep = ("PATH", "SYSTEMROOT", "HOME", "PYTHONPATH")
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["LOCALAPPDATA"] = str(tmp_path)
    return env


def _run_real(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tancrede.app.cli", "--profile", "real", "check-gateway"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_w0_gate_real_profile_calls_local_openai_server(tmp_path: Path, fake_server: str) -> None:
    root = tmp_path / "Tancrede"
    root.mkdir()
    (root / "config.toml").write_text(
        f'mode = "enclave"\ndefault_gateway = "local"\n'
        f'[gateways.local]\ntype = "openai"\nbase_url = "{fake_server}"\nmodel = "tiny"\n',
        encoding="utf-8",
    )
    result = _run_real(_clean_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "Passerelle local (127.0.0.1) : OK" in result.stdout
    assert "pong" in result.stdout
    log = (root / "logs" / "tancrede.log").read_text(encoding="utf-8")
    assert "event=router.call" in log and "pong" not in log


def test_t_dev_02_real_refused_from_claude_code_terminal(tmp_path: Path) -> None:
    env = {**_clean_env(tmp_path), "CLAUDECODE": "1"}
    result = _run_real(env)
    assert result.returncode == 2
    assert "VS Code or Claude Code" in result.stderr
    assert not (tmp_path / "Tancrede" / "logs").exists()
