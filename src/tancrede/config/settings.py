"""Settings schema, loaded from `config.toml` (SPEC §4, §5, §10)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from tancrede.domain.errors import ConfigError
from tancrede.domain.task_kind import TaskKind

BUILTIN_GATEWAY_TYPES = frozenset({"mock", "openai"})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GatewayConfig(_Strict):
    """One model gateway. `type` is `mock`, `openai` or the name of a plugin."""

    type: str
    base_url: str | None = None
    model: str | None = None
    api_key: SecretStr | None = None
    timeout_s: float = Field(default=60.0, gt=0)
    options: dict[str, Any] = Field(default_factory=dict)


class LabelRule(_Strict):
    name: str
    patterns: list[str] = Field(default_factory=list)


class ClassificationConfig(_Strict):
    excluded_labels: list[LabelRule] = Field(default_factory=list)
    included_labels: list[LabelRule] = Field(default_factory=list)


class EnclaveConfig(_Strict):
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_plugins: list[str] = Field(default_factory=list)


class Settings(_Strict):
    mode: Literal["enclave", "open"] = "enclave"
    allowed_folders: list[Path] = Field(default_factory=list)
    default_gateway: str | None = None
    routing: dict[TaskKind, str] = Field(default_factory=dict)
    gateways: dict[str, GatewayConfig] = Field(default_factory=dict)
    enclave: EnclaveConfig = Field(default_factory=EnclaveConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    eval_journal: bool = False

    @model_validator(mode="after")
    def _check_references(self) -> Settings:
        if self.default_gateway is not None and self.default_gateway not in self.gateways:
            raise ValueError(f"default_gateway '{self.default_gateway}' is not declared")
        for kind, name in self.routing.items():
            if name not in self.gateways:
                raise ValueError(f"routing for '{kind}' targets undeclared gateway '{name}'")
        return self

    @property
    def plugin_gateway_types(self) -> set[str]:
        return {g.type for g in self.gateways.values() if g.type not in BUILTIN_GATEWAY_TYPES}


def parse_settings(data: dict[str, Any]) -> Settings:
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        # Field locations and messages only; values are not echoed.
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ConfigError(f"invalid configuration ({details})") from None


def load_settings(path: Path) -> Settings:
    if not path.is_file():
        raise ConfigError(f"configuration file not found: {path}")
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"configuration file is not valid TOML: {path} ({exc})") from None
    return parse_settings(data)
