"""T-DEV-03: `real` logs carry no source, prompt or answer text."""

from __future__ import annotations

import logging
from pathlib import Path

from tancrede.app.logging_setup import configure_logging
from tancrede.config.profiles import Profile, resolve_paths

PRIVATE_TEXT = "Orion prototype review moved to 2027-04-01"


def _emit_everything(log: logging.Logger) -> None:
    log.info("router.call", extra={"gateway": "local", "duration_ms": 42, "task_kind": "answer"})
    log.info("user asked: %s", PRIVATE_TEXT)
    log.warning(PRIVATE_TEXT)
    log.info("search.done", extra={"code": PRIVATE_TEXT, "count": 3})
    try:
        raise ValueError(f"cannot parse {PRIVATE_TEXT}")
    except ValueError:
        log.exception("index.failed")
    log.error("prompt.sent", stack_info=True)


def test_t_dev_03_real_logs_are_redacted(tmp_path: Path) -> None:
    paths = resolve_paths(Profile.REAL, {"TANCREDE_HOME": str(tmp_path)}, None)
    configure_logging(Profile.REAL, paths)
    log = logging.getLogger("tancrede.test")
    _emit_everything(log)
    for handler in logging.getLogger("tancrede").handlers:
        handler.flush()

    content = (paths.logs_dir / "tancrede.log").read_text(encoding="utf-8")
    assert "Orion" not in content
    assert "2027" not in content
    assert "Traceback" not in content
    assert "event=router.call" in content
    assert "duration_ms=42" in content
    assert "event=redacted" in content
    assert "code=redacted" in content
    assert "exc=ValueError" in content


def test_dev_logs_are_not_redacted(repo: Path, capsys) -> None:
    paths = resolve_paths(Profile.DEV, {}, repo)
    configure_logging(Profile.DEV, paths)
    logging.getLogger("tancrede.test").warning("visible %s", "text")
    assert "visible text" in capsys.readouterr().err
