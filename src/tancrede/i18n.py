"""UI strings (French, SPEC §7)."""

from __future__ import annotations

import tomllib
from functools import cache
from importlib.resources import files


@cache
def _strings(locale: str) -> dict[str, str]:
    data = tomllib.loads(files("tancrede").joinpath(f"locales/{locale}.toml").read_text("utf-8"))
    flat: dict[str, str] = {}

    def walk(prefix: str, node: dict) -> None:
        for key, value in node.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                walk(full, value)
            else:
                flat[full] = str(value)

    walk("", data)
    return flat


def t(key: str, locale: str = "fr", **kwargs: object) -> str:
    template = _strings(locale).get(key, key)
    return template.format(**kwargs) if kwargs else template
