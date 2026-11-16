"""`dev` / `real` profiles: the development safeguard (SPEC §11).

`dev` works only on the synthetic corpus inside the repository, with mock
gateways. `real` works on the user's data, outside any coding-assistant
terminal, with its data under `%LOCALAPPDATA%\\Tancrede`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from tancrede.config.settings import ClassificationConfig, GatewayConfig, LabelRule, Settings
from tancrede.domain.errors import ProfileViolation

APP_DIR_NAME = "Tancrede"
DEV_DATA_DIR = ".dev-data"
DEV_CONFIG_FILE = "dev.toml"

# Environment variables revealing a VS Code or Claude Code terminal (open point DEV-O-06).
# (name, expected value) — `None` means "present with any value".
CODING_ASSISTANT_MARKERS: tuple[tuple[str, str | None], ...] = (
    ("TERM_PROGRAM", "vscode"),
    ("VSCODE_PID", None),
    ("VSCODE_IPC_HOOK_CLI", None),
    ("VSCODE_GIT_IPC_HANDLE", None),
    ("VSCODE_INJECTION", None),
    ("CLAUDECODE", None),
    ("CLAUDE_CODE_ENTRYPOINT", None),
)


class Profile(StrEnum):
    DEV = "dev"
    REAL = "real"


@dataclass(frozen=True)
class ProfilePaths:
    root: Path
    config_file: Path
    database: Path
    logs_dir: Path


def repo_root() -> Path | None:
    """The source checkout this package runs from, if any."""
    candidate = Path(__file__).resolve().parents[3]
    pyproject = candidate / "pyproject.toml"
    if pyproject.is_file() and 'name = "tancrede"' in pyproject.read_text(encoding="utf-8"):
        return candidate
    return None


def real_root(environ: Mapping[str, str]) -> Path:
    local_app_data = environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIR_NAME
    # Non-Windows fallback, only useful to run the tool elsewhere than its target platform.
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def resolve_paths(profile: Profile, environ: Mapping[str, str], repo: Path | None) -> ProfilePaths:
    if profile is Profile.DEV:
        if repo is None:
            raise ProfileViolation("the dev profile only runs from a source checkout")
        root = repo / DEV_DATA_DIR
        config_file = repo / DEV_CONFIG_FILE
    else:
        root = real_root(environ)
        config_file = root / "config.toml"
    return ProfilePaths(
        root=root,
        config_file=config_file,
        database=root / "tancrede.db",
        logs_dir=root / "logs",
    )


def coding_assistant_markers(environ: Mapping[str, str]) -> list[str]:
    found = []
    for name, expected in CODING_ASSISTANT_MARKERS:
        value = environ.get(name)
        if value is None:
            continue
        if expected is None or value.lower() == expected:
            found.append(name)
    return found


def ensure_real_allowed_here(environ: Mapping[str, str]) -> None:
    """T-DEV-02: `real` never starts from a VS Code or Claude Code terminal."""
    markers = coding_assistant_markers(environ)
    if markers:
        raise ProfileViolation(
            "the real profile cannot start from a VS Code or Claude Code terminal "
            f"(detected: {', '.join(markers)})"
        )


def _is_within(path: Path, parent: Path) -> bool:
    return path.resolve().is_relative_to(parent.resolve())


def check_profile(
    profile: Profile, settings: Settings, paths: ProfilePaths, repo: Path | None
) -> None:
    """Startup checks for the selected profile (T-DEV-01)."""
    if profile is Profile.DEV:
        assert repo is not None  # guaranteed by resolve_paths
        outside = [p for p in settings.allowed_folders if not _is_within(p, repo)]
        if outside:
            raise ProfileViolation(
                f"the dev profile refuses folders outside the repository ({len(outside)} found)"
            )
        not_mock = sorted(n for n, g in settings.gateways.items() if g.type != "mock")
        if not_mock:
            raise ProfileViolation(
                f"the dev profile only allows mock gateways (refused: {', '.join(not_mock)})"
            )
    else:
        if repo is not None and _is_within(paths.root, repo):
            raise ProfileViolation("real profile data must not live inside the repository")


def default_dev_settings(repo: Path) -> Settings:
    """Settings used by `dev` when no `dev.toml` exists."""
    return Settings(
        mode="enclave",
        allowed_folders=[repo / "fixtures" / "synthetic"],
        default_gateway="mock",
        gateways={"mock": GatewayConfig(type="mock")},
        classification=ClassificationConfig(
            excluded_labels=[LabelRule(name="FICTIVE-SECRET", patterns=["FICTIVE-SECRET"])],
            included_labels=[LabelRule(name="FICTIVE-INTERNAL", patterns=["FICTIVE-INTERNAL"])],
        ),
    )


def profile_from_env(environ: Mapping[str, str] = os.environ) -> Profile:
    return Profile(environ.get("TANCREDE_PROFILE", Profile.DEV.value))
