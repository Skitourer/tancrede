"""Manual dependency injection (SPEC §6): the one place where things are wired."""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tancrede.adapters.sources import LocalFolderRepository
from tancrede.app.logging_setup import configure_logging
from tancrede.config.profiles import (
    Profile,
    ProfilePaths,
    check_profile,
    default_dev_settings,
    ensure_real_allowed_here,
    repo_root,
    resolve_paths,
)
from tancrede.config.settings import Settings, load_settings
from tancrede.domain.errors import ConfigError
from tancrede.models import ModelRouter
from tancrede.models.factory import build_router
from tancrede.models.plugins import discover_gateway_factories
from tancrede.persistence.database import open_database
from tancrede.persistence.index_repository import IndexRepository
from tancrede.policy.allowed_folders import AllowedFolders
from tancrede.policy.classification import ClassificationFilter
from tancrede.policy.mode_guard import ModeGuard, check_settings
from tancrede.services.index_service import IndexService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppContext:
    profile: Profile
    paths: ProfilePaths
    settings: Settings
    router: ModelRouter
    database: sqlite3.Connection
    index: IndexService

    def close(self) -> None:
        self.database.close()


def _load_settings(
    profile: Profile, paths: ProfilePaths, repo: Path | None, config_path: Path | None
) -> Settings:
    if config_path is not None:
        if profile is not Profile.DEV:
            raise ConfigError("an explicit configuration file is only allowed with the dev profile")
        return load_settings(config_path)
    if profile is Profile.DEV and not paths.config_file.is_file():
        assert repo is not None
        return default_dev_settings(repo)
    return load_settings(paths.config_file)


def bootstrap(
    profile: Profile,
    *,
    environ: Mapping[str, str] = os.environ,
    config_path: Path | None = None,
) -> AppContext:
    repo = repo_root()
    if profile is Profile.REAL:
        ensure_real_allowed_here(environ)  # before reading anything real (T-DEV-02)
    paths = resolve_paths(profile, environ, repo)
    settings = _load_settings(profile, paths, repo, config_path)
    check_profile(profile, settings, paths, repo)  # T-DEV-01
    check_settings(settings)  # T-MODE-03

    paths.root.mkdir(parents=True, exist_ok=True)
    configure_logging(profile, paths)

    factories = {}
    if settings.plugin_gateway_types:
        allowed = settings.enclave.allowed_plugins if settings.mode == "enclave" else None
        factories = discover_gateway_factories(allowed)  # T-MODE-04
    guard = ModeGuard.from_settings(settings)
    router = build_router(settings, plugin_factories=factories, guard=guard)  # T-MODE-01

    database = open_database(paths.database)
    classifier = ClassificationFilter(
        settings.classification.excluded_labels, settings.classification.included_labels
    )
    sources = LocalFolderRepository(
        AllowedFolders(settings.allowed_folders, settings.excluded_paths)
    )
    index = IndexService(sources, classifier, IndexRepository(database))

    log.info("app.started", extra={"code": profile.value, "count": len(router.gateway_names)})
    return AppContext(
        profile=profile,
        paths=paths,
        settings=settings,
        router=router,
        database=database,
        index=index,
    )
