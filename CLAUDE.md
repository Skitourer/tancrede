# Tancrède — Claude Code

Single reference: `docs/SPEC.md`. Read only the sections relevant to the task (current wave: §12). Open `docs/DECISIONS.md` only to understand a past choice. No other spec document exists in the repo; do not ask for one. Talk to the maintainer in French.

## Non-negotiable
- Public MIT repo: never write organization-specific content (employer names, internal AI services, internal marking labels, internal hosts) or the maintainer's real name in code, tests, docs or commits. Fixtures use fictitious labels only.
- `dev` profile only (`fixtures/synthetic/`, `MockModelGateway`). Never the `real` profile; never `%LOCALAPPDATA%\Tancrede` or any real folder of the maintainer.
- Never ask for real content, `real` logs, the evaluation journal or gateway parameters; for a real-data bug, ask for a fictitious repro. Real data spotted (repo, terminal, conversation) → stop and report.
- No gateway configuration value (URL, key, model of a real service) in the repo.
- Classification (SPEC §5) and mode guardrails (SPEC §4) in deterministic code, enforced at startup and at every gateway call.
- Every model call through `ModelRouter`. No email or invitation sending. No business write without confirmation.
- Do not reintroduce anything under "Do not implement" (SPEC §3).

## Work
- One wave at a time; nothing out of MVP unless asked.
- Before commit: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`; no blocking test (SPEC §9) failing.
- Flag any change to `policy/`, modes or profiles for the maintainer's review.
- Structural decision or technical choice → one line in `docs/DECISIONS.md`.
- Economy: targeted searches (`rg`, partial reads) over full-file reads; don't re-read an unchanged file; short replies, no echo of written code or of the spec.
