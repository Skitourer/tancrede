# Tancrède — Active decisions

U = maintainer; D = delegated, reversible technical choice. One line per decision, newest last.

- 2026-11-13 D-GEL (U) V1 functional freeze.
- 2026-11-13 ADR-001 (D) Python 3.13 throughout, PySide6 6.12 LTS.
- 2026-11-14 D-SIMPL (U) Security at personal-tool level; heavy mechanisms dropped (SPEC §3).
- 2026-11-14 D-DEV (U) Coding assistant never accesses real data or gateway parameters; separate `dev`/`real` profiles (SPEC §11).
- 2026-11-14 D-OUTIL (D) uv, Ruff, pytest, pre-commit; no nox, strict mypy, hypothesis or coverage threshold.
- 2026-11-14 D-TOK (U) Compact spec in English to cut coding-assistant token use; conversation with the maintainer in French.
- 2026-11-16 D-LLM (U) All model calls through `ModelRouter` and a single gateway protocol; local models allowed with the same data scope as any gateway (SPEC §6, §10).
- 2026-11-16 D-ROUTE (U) Routing by `TaskKind`; evaluation journal (off by default) to compare gateways, not to train (SPEC §10).
- 2026-11-16 D-OSS (U) Public GitHub repo, MIT license, developed on personal time; name Tancrède / `tancrede`; no organization-specific content in the repo; organization adapters (gateway, labels) in separate, possibly private, plugin packages (SPEC §1, §6).
- 2026-11-16 D-MODE (U) Two install modes: `enclave` (guardrails in code: allowed endpoints only, mandatory classification, no outbound network, allowed plugins only) and `open` (no restriction, user warned) (SPEC §4).
- 2026-11-16 D-LABEL (U) Classification labels are configuration; unknown label = no label; exclusion wins (SPEC §5).
- 2026-11-16 D-AUTHOR (U) Author and copyright holder: `skitourer` (GitHub and PyPI handle); no real name in the repo, `LICENSE` or package metadata.
- 2026-11-16 W0-01 (D) PySide6 added in W3, when the UI starts; W0 depends only on httpx and Pydantic.
- 2026-11-16 W0-02 (D) Locale files live in `src/tancrede/locales/` (packaged), not at repo root.
- 2026-11-16 W0-03 (D) `dev` refuses any non-mock gateway, in addition to folders outside the repo; optional `dev.toml` (git-ignored) at repo root, data in `.dev-data/`.
- 2026-11-16 W0-04 (D) Extra errors `ConfigError`, `ProfileViolation`; error messages never carry source, prompt or answer text.
- 2026-11-16 W0-05 (D) `real` logs: event code + whitelisted fields (`id`, `code`, `gateway`, `task_kind`, `count`, `duration_ms`) + exception type only.
- 2026-11-16 W0-06 (D) Loopback gateways ignore system proxy settings; enclave plugin allow-list applied at discovery.
- 2026-11-16 W0-07 (D) CI on GitHub Actions, Windows and Ubuntu, Python 3.13.
- 2026-11-16 D-OS (U) Windows and Linux both supported and tested in CI; macOS untested. Real data directory from `platformdirs` (`TANCREDE_HOME` overrides) (SPEC §7, §11).
- 2026-11-16 W1-01 (D) Label pattern = plain string, case-insensitive, whole token, spaces match any whitespace; a rule without pattern uses its name (closes CLS-01).
- 2026-11-16 W1-02 (D) Extraction: Markdown/text (UTF-8 then cp1252, `key: value` front matter as metadata), PDF via `pypdf`, DOCX via zip + `defusedxml` (body, headers, footers, document properties); any parser failure = non-extractable.
- 2026-11-16 W1-03 (D) Every refresh re-classifies every file (label config may change); excluded files are never stored, not even their path; previously indexed ones are removed.
- 2026-11-16 W1-04 (D) One `LocalFolderRepository`; `dev` points it at `fixtures/synthetic/` (no separate synthetic class). Symlinks leaving allowed folders are ignored.
- 2026-11-16 W1-05 (D) SQLite in autocommit with explicit transactions; schema version in `PRAGMA user_version`; FTS5 `unicode61 remove_diacritics 2`; user queries quoted (no FTS syntax).
- 2026-11-16 W1-06 (D) `tancrede index` command; `ModeGuard` checks loopback or `enclave.allowed_hosts` (case-insensitive) at startup and before each call.
- 2026-11-16 D-PUB (U) PyPI publishing via GitHub trusted publishing: `publish.yml` on release published, environment `pypi`, tag must equal `v` + version, tests run before build.
