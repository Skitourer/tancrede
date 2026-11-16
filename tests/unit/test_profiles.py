"""T-DEV-01, T-DEV-02 and related profile rules (SPEC §11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tancrede.config.profiles import (
    Profile,
    check_profile,
    coding_assistant_markers,
    default_dev_settings,
    ensure_real_allowed_here,
    repo_root,
    resolve_paths,
)
from tancrede.config.settings import GatewayConfig, Settings
from tancrede.domain.errors import ProfileViolation


def test_repo_root_is_detected(repo: Path) -> None:
    assert repo_root() == repo


def test_default_dev_settings_pass(repo: Path, clean_env: dict[str, str]) -> None:
    paths = resolve_paths(Profile.DEV, clean_env, repo)
    check_profile(Profile.DEV, default_dev_settings(repo), paths, repo)
    assert paths.root == repo / ".dev-data"


def test_t_dev_01_dev_refuses_real_folder(
    repo: Path, tmp_path: Path, clean_env: dict[str, str]
) -> None:
    settings = default_dev_settings(repo).model_copy(
        update={"allowed_folders": [repo / "fixtures" / "synthetic", tmp_path / "Documents"]}
    )
    paths = resolve_paths(Profile.DEV, clean_env, repo)
    with pytest.raises(ProfileViolation, match="outside the repository"):
        check_profile(Profile.DEV, settings, paths, repo)


def test_t_dev_01_dev_refuses_parent_traversal(repo: Path, clean_env: dict[str, str]) -> None:
    settings = default_dev_settings(repo).model_copy(
        update={"allowed_folders": [repo / "fixtures" / ".." / ".." / "elsewhere"]}
    )
    with pytest.raises(ProfileViolation):
        check_profile(Profile.DEV, settings, resolve_paths(Profile.DEV, clean_env, repo), repo)


def test_dev_refuses_non_mock_gateways(repo: Path, clean_env: dict[str, str]) -> None:
    settings = Settings(
        default_gateway="local",
        gateways={"local": GatewayConfig(type="openai", base_url="http://localhost:1", model="m")},
    )
    with pytest.raises(ProfileViolation, match="only allows mock"):
        check_profile(Profile.DEV, settings, resolve_paths(Profile.DEV, clean_env, repo), repo)


@pytest.mark.parametrize(
    "env",
    [
        {"TERM_PROGRAM": "vscode"},
        {"TERM_PROGRAM": "VSCode"},
        {"VSCODE_PID": "1234"},
        {"VSCODE_IPC_HOOK_CLI": "vscode-ipc.sock"},
        {"CLAUDECODE": "1"},
        {"CLAUDE_CODE_ENTRYPOINT": "cli"},
    ],
)
def test_t_dev_02_real_refused_from_coding_assistant(env: dict[str, str]) -> None:
    assert coding_assistant_markers(env)
    with pytest.raises(ProfileViolation, match="VS Code or Claude Code"):
        ensure_real_allowed_here(env)


def test_t_dev_02_real_allowed_from_plain_terminal(clean_env: dict[str, str]) -> None:
    ensure_real_allowed_here({**clean_env, "TERM_PROGRAM": "WindowsTerminal"})


def test_real_paths_under_localappdata(clean_env: dict[str, str], repo: Path) -> None:
    paths = resolve_paths(Profile.REAL, clean_env, repo)
    assert paths.root == Path(clean_env["LOCALAPPDATA"]) / "Tancrede"
    assert paths.config_file.name == "config.toml"


def test_real_data_never_inside_repo(repo: Path) -> None:
    env = {"LOCALAPPDATA": str(repo / "inside")}
    paths = resolve_paths(Profile.REAL, env, repo)
    with pytest.raises(ProfileViolation, match="inside the repository"):
        check_profile(Profile.REAL, default_dev_settings(repo), paths, repo)
