"""Command line: `tancrede check-gateway`, `tancrede index`, `tancrede --version`."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from tancrede import __version__
from tancrede.app.bootstrap import AppContext, bootstrap
from tancrede.config.profiles import Profile
from tancrede.domain.errors import ConfigError, ModelUnavailable, TancredeError
from tancrede.domain.task_kind import TaskKind
from tancrede.i18n import t
from tancrede.models import ModelRequest

REPLY_PREVIEW_CHARS = 60


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tancrede", description=t("cli.description"))
    parser.add_argument("--version", action="version", version=f"tancrede {__version__}")
    parser.add_argument("--profile", choices=[p.value for p in Profile], help=t("cli.profile_help"))
    parser.add_argument("--config", type=Path, help=t("cli.config_help"))
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-gateway", help=t("cli.check_help"))
    check.add_argument("--gateway", help=t("cli.gateway_help"))
    sub.add_parser("index", help=t("cli.index_help"))
    return parser


def _check_gateway(ctx: AppContext, only: str | None) -> int:
    router = ctx.router
    names = [only] if only else router.gateway_names
    print(t("check.header", profile=ctx.profile.value, mode=ctx.settings.mode, count=len(names)))
    request = ModelRequest(task_kind=TaskKind.ANSWER, prompt=t("check.prompt"), max_tokens=16)
    failures = 0
    for name in names:
        if name not in router.gateway_names:
            print(t("check.unknown", name=name))
            failures += 1
            continue
        hosts = ", ".join(sorted(router.endpoint_hosts(name))) or t("check.no_hosts")
        try:
            response = router.complete_with(name, request)
        except ModelUnavailable as exc:
            print(t("check.failed", name=name, hosts=hosts, error=exc))
            failures += 1
            continue
        reply = " ".join(response.text.split())[:REPLY_PREVIEW_CHARS]
        print(
            t(
                "check.ok",
                name=name,
                hosts=hosts,
                ms=response.latency_ms,
                model=response.model,
                reply=reply,
            )
        )
    return 1 if failures else 0


def _index(ctx: AppContext) -> int:
    report = ctx.index.refresh()
    print(
        t(
            "index.report",
            profile=ctx.profile.value,
            indexed=report.indexed,
            unchanged=report.unchanged,
            excluded=report.excluded,
            non_extractable=report.non_extractable,
            removed=report.removed,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    raw_profile = args.profile or os.environ.get("TANCREDE_PROFILE", Profile.DEV.value)
    try:
        profile = Profile(raw_profile)
    except ValueError:
        print(t("error.bad_profile", value=raw_profile), file=sys.stderr)
        return 2
    if args.config is not None and profile is not Profile.DEV:
        print(t("error.config_only_dev"), file=sys.stderr)
        return 2
    try:
        ctx = bootstrap(profile, config_path=args.config)
        try:
            if args.command == "check-gateway":
                return _check_gateway(ctx, args.gateway)
            if args.command == "index":
                return _index(ctx)
        finally:
            ctx.close()
    except (ConfigError, TancredeError) as exc:
        print(t("error.startup", message=exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
