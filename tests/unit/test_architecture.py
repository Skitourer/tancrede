"""T-LLM-01: only `models/` knows concrete gateways; everything else uses `ModelRouter`."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "tancrede"
MODELS = SRC / "models"
CONCRETE_MODULES = {"tancrede.models.mock", "tancrede.models.openai_compat"}
CONCRETE_NAMES = {"MockModelGateway", "OpenAICompatibleGateway"}


def _violations(path: Path) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name in CONCRETE_MODULES]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in CONCRETE_MODULES:
                found.append(module)
            found += [a.name for a in node.names if a.name in CONCRETE_NAMES]
    return found


def test_t_llm_01_no_concrete_gateway_outside_models() -> None:
    offenders = {
        str(p.relative_to(SRC)): v
        for p in SRC.rglob("*.py")
        if not p.is_relative_to(MODELS) and (v := _violations(p))
    }
    assert offenders == {}
