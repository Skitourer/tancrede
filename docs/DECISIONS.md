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
