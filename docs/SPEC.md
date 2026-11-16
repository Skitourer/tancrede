# Tancrède — SPEC V1.39

Single development reference for the public repository; overrides any other document. Project name: Tancrède (display), `tancrede` (repo, PyPI package, import name). License: MIT. This repo must never contain organization-specific content (employer names, internal AI service names, internal marking labels, internal hosts).

## 1. Product
Single-user Windows desktop assistant: work organization, knowledge, cognitive load. Orchestrates sources chosen by the user (notes, local documents, project memory; email later) and language models through pluggable gateways (local model, OpenAI-compatible API, or organization-specific adapters shipped as separate packages).
Principles: conversation-centric; sourced answers; nothing invented; no business write without confirmation.
Two installation modes (§4): `enclave` (confidentiality guardrails enforced in code) and `open` (no restriction, user warned).
Security level = personal tool. Only non-negotiable safeguards: §4, §5 and §11.

## 2. Scope
MVP:
1. Central conversation (large prompt area + sidebar), keyboard navigation, cancel.
2. Versioned free notes: original never rewritten, history kept.
3. Project memory: projects, tasks, deadlines, versioned events.
4. Lexical search (SQLite FTS5) across notes and documents in allowed folders.
5. Verifiable citations, built by the app from sources actually retrieved.
6. Contradictions detected and shown, never resolved.
7. Action proposals, applied only after confirmation.
8. Classification filter (§5) and allowed folders.
9. `enclave` / `open` modes with their guardrails (§4).
10. Model access through `ModelRouter` only; `OpenAICompatibleGateway` (Ollama, llama.cpp, LM Studio, vLLM, cloud APIs) and `MockModelGateway`; external gateways via plugins (§6).
11. Degraded mode without model: search and notes still work.
12. Evaluation journal (§10), off by default.

Out of MVP, do not build unless asked: per-task routing to several providers, English UI (`locales/en.toml`), Outlook connector (read), configurable personality, cognitive load manager, assisted archiving, Markdown/JSON export, dictation and screenshots, quick palette, drag-and-drop, natural-language settings, active-context indicator, macOS/Linux; then V2 (handwriting, semantic search, multi-device…).

Permanent prohibitions: processing content carrying an excluded label (§5); in `enclave`, any network call outside allowed endpoints (§4); sending email or invitations, deleting a mail item; exposing real data to the coding assistant (§11).

## 3. Rules
- R1 Excluded labels removed before indexing by deterministic code; no prompt, source or model can lift an exclusion.
- R2 Read-only, and only within the allowed folders listed in config.
- R3 Business write = confirmation + check that the target version has not changed.
- R4 Citation = source actually retrieved; without evidence: abstain or give a flagged partial answer.
- R5 Contradictions visible; "most recent wins" is not a rule.
- R6 Source or model text = data; never triggers an action (everything goes through R3).
- R7 Source removed from allowed folders → removed from the index.
- R8 Dev / real data isolation (§11).
- R9 Services never call a gateway directly; only `ModelRouter` does. All gateways receive the same data scope (§5).
- R10 Mode guardrails (§4) are enforced in code at startup and at every gateway call, not only in the UI.

Do not implement: rights engine, revocation of derived data, multi-stream audit, OS-level network blocking, database encryption, risk levels, approval idempotence or expiry, model training or fine-tuning, telemetry of any kind.

## 4. Modes
Set at install in `config.toml` (`mode = "enclave" | "open"`); default `enclave`.

`enclave` (private, secured environment):
- Gateways may only reach `localhost` or hosts listed in `enclave.allowed_hosts`; any other endpoint → startup refused or call refused (`ModeViolation`).
- Every gateway declares its endpoint host(s); a plugin that cannot declare them is refused.
- Classification filter mandatory: startup refused if `classification.excluded_labels` is empty.
- No outbound network from the app other than allowed gateway endpoints (no update check, no telemetry, no remote fonts or assets).
- Switching to `open` requires editing config and confirming a blocking dialog at next startup; the switch is recorded in the profile database.

`open`:
- Any gateway and endpoint allowed.
- Blocking warning at first launch (data may leave the machine; no confidentiality guarantee); persistent mode indicator in the UI.
- Classification filter optional (applied if labels are configured).

## 5. Classification
- Labels are configuration, not code: `classification.excluded_labels` (list of label names + detection patterns) and `classification.included_labels`. The repo ships no real label, only fictitious ones in `fixtures/`.
- Excluded from index and models: any excluded label, non-extractable text (scanned PDF, unreadable file).
- Local pattern detection (metadata, header, footer, body) before indexing; an exclusion label always wins over an included one.
- Unknown or missing label = no label (indexed).
- Manual exclusion of a file or folder possible; no automatic reinstatement.
- Excluded content: no trace in the index, nothing revealed in answers.
- Accepted limitation: excluded content without a readable label is not detected (mitigation: chosen folders only).
- Organization label sets may be shipped by an external plugin (`tancrede.labels` entry point).

## 6. Architecture
Components (`typing.Protocol` interfaces, manual injection in `app/bootstrap.py`, no singletons):
- UI `ui/`: `DesktopShell`, `ConversationView`, `NotesView`, `ProposalView`, `ModeIndicator` — presenters, no direct source access.
- Services `services/`: `ConversationService`, `NoteService`, `ProjectService`, `ProposalService`, `ConflictDetector` — keep facts, proposals and writes separate.
- Policy `policy/`: `ClassificationFilter`, `AllowedFolders`, `ModeGuard` — deterministic; `ModeGuard` checks every gateway endpoint against §4.
- Sources `adapters/`: `SourceRepository` → `LocalFolderRepository`, `SyntheticSourceRepository` — read-only.
- Search: `IndexService`, `SearchService`, `EvidenceService` — citations built from results.
- Models `models/`: `ModelRouter` (sole entry point; picks a gateway per `TaskKind` from config, falls back to the default gateway if the chosen one is unavailable, checks `ModeGuard` before each call) → `ModelGateway` → `OpenAICompatibleGateway`, `MockModelGateway`, plugin gateways. `EvalRecorder` called by the router. The model triggers no action.
- Plugins: Python entry points `tancrede.gateways` and `tancrede.labels`, discovered at startup, listed in the UI; in `enclave`, only plugins named in `enclave.allowed_plugins` are loaded.
- Write: `ConfirmationService` — confirmation + version check.
- Persistence: `NoteRepository`, `ProjectRepository`, `EvalRepository`, versioned SQLite migrations.
- Logging: standard `logging` (constraints in §11).

`TaskKind`: `answer` (question with evidence), `summarize`, `extract`, `classify_topic`, `tag`. Routing table in config: `TaskKind → gateway name`; MVP: all → default gateway.

Flows:
- Indexing: allowed folder → text extraction → `ClassificationFilter` → index | exclusion.
- Question: prompt → `SearchService` → `EvidenceService` → `ConflictDetector` → context (best excerpts) → `ModelRouter` (`answer`) → citation check → answer (facts, uncertainties, contradictions, limits).
- Action: suggestion → readable proposal → confirmation → re-read target version → execute | new proposal if changed.

Data:
```text
SourceRecord(id, kind, label, path_ref, version)
Evidence(id, source_id, source_version, locator)
Note(id, text, version, created_at, updated_at)
NoteRevision(id, note_id, version, snapshot, created_at)
Project(id, title, status, version)
Task(id, project_id, title, status, due, version, provenance)
ProjectEvent(id, project_id, version, kind, evidence_ids, event_date, discovered_at)
FactClaim(id, subject, value, state=observed|inferred|user_confirmed|superseded, evidence_id)
Proposal(id, target, target_version, action, state)
EvalRecord(id, task_kind, gateway, model, prompt, response, latency_ms, created_at, rating?)
ModeChange(id, from_mode, to_mode, confirmed_at)
```

Repository:
```text
tancrede/ pyproject.toml uv.lock .pre-commit-config.yaml .gitignore LICENSE README.md CLAUDE.md
  src/tancrede/{app,ui,domain,services,policy,adapters,models,persistence,config}/
  tests/{unit,integration}/   fixtures/synthetic/   locales/fr.toml   docs/{SPEC.md,DECISIONS.md}
```

## 7. Stack and conventions
- Python 3.13, PySide6 6.12 LTS, SQLite + FTS5, Pydantic v2 at boundaries, frozen dataclasses for the domain; `httpx` for `OpenAICompatibleGateway`.
- uv, Ruff (format + lint, line 100), pytest, headless `pytest-qt`; pre-commit: Ruff + `detect-secrets`.
- Careful tests on `policy/`, modes and profiles; elsewhere useful tests, no coverage threshold.
- Code, identifiers, comments, commits, README in English; UI strings in French in `locales/fr.toml`.
- Short-lived trunk, conventional commits `feat(L04): …`. Public GitHub repo, MIT `LICENSE` from the first commit.
- Forbidden: `eval`/`exec`, `pickle` on external data, `subprocess(shell=True)`.
- Services off the UI thread via `QThreadPool`, cancellation by token.
- Errors: `TancredeError` → `ExcludedByClassification`, `StaleVersion`, `SourceUnavailable`, `ModelUnavailable`, `ModeViolation`.
- Packaging: standalone `pyside6-deploy`, per-user install without admin rights; also `pip install tancrede`.

## 8. Synthetic corpus `fixtures/synthetic/`
Invented identities, paths and labels (e.g. `FICTIVE-SECRET`, `FICTIVE-INTERNAL`). Required cases:
1. Two sources disagreeing on a deadline.
2. Documents carrying an excluded label (in header, footer, body, metadata), an included label, no label.
3. File with non-extractable text.
4. Document containing a prompt injection.
5. Proposal whose target changes before execution.
6. Note edited several times.

## 9. Blocking tests
- T-CLS-01 Excluded label (header, footer, body, metadata) → not indexed, nothing sent to any model.
- T-CLS-02 Excluded and included labels on the same document → excluded.
- T-CLS-03 Included label or no label → indexed, sendable.
- T-CLS-04 Non-extractable text → not indexed.
- T-CLS-05 "Lift the exclusion" in a prompt or document → exclusion unchanged.
- T-CLS-06 File outside allowed folders → never read.
- T-MODE-01 `enclave` with a gateway pointing to a non-allowed host → startup refused.
- T-MODE-02 `enclave`, endpoint changed at runtime to a non-allowed host → call refused, `ModeViolation`.
- T-MODE-03 `enclave` with empty `excluded_labels` → startup refused.
- T-MODE-04 `enclave` with a plugin not in `allowed_plugins` → plugin not loaded.
- T-MODE-05 `open` first launch → blocking warning; indicator always visible.
- T-MODE-06 `enclave` → `open` without confirmation → stays `enclave`; with confirmation → `ModeChange` recorded.
- T-DEV-01 `dev` profile pointed at a real folder → startup refused.
- T-DEV-02 `real` profile launched from VS Code or Claude Code → startup refused.
- T-DEV-03 `real` logs after full scenario + forced error → no source, prompt or answer text (evaluation journal excluded: it is a database, not a log).
- T-DEV-04 Fake secret committed → rejected by pre-commit.
- T-REL-01 Question without evidence → abstain or partial answer, no invented citation.
- T-CONFL-01 Two different deadlines → both dates and their sources shown.
- T-ACT-01 Target modified between proposal and execution → write blocked, new proposal.
- T-ACT-02 Request to send email; prompt injection → nothing sent, no action without confirmation.
- T-NOTE-01 Entry, edit, search without model → original kept, versions, local search.
- T-OFF-01 No gateway available → visible degraded mode, search works.
- T-LLM-01 No module other than `models/` imports a concrete gateway; services use only `ModelRouter`.
- T-LLM-02 Routing table sends a task kind to an unavailable gateway → falls back to default; default also down → T-OFF-01 behaviour.
- T-EVAL-01 Journal off → nothing recorded; on in `dev` → only synthetic content, stored in the `dev` database.

## 10. Models
Gateways:
- `OpenAICompatibleGateway`: base URL, model, optional key in `config.toml` outside the repo; covers local servers (Ollama, llama.cpp, LM Studio, vLLM) and cloud APIs.
- Plugin gateways (entry point `tancrede.gateways`): same `ModelGateway` protocol, must declare endpoint hosts.
- Verification command `tancrede check-gateway` (fictitious prompt), run by the user outside VS Code.
- Real data indexed and sent only once T-CLS-01…06, T-MODE-01…04 and T-DEV-01…03 pass.
- Automated tests: always `MockModelGateway`.
- Inference only: no training or fine-tuning.

Evaluation journal:
- `EvalRecorder` stores each routed call as `EvalRecord` in the profile database, never in logs.
- Off by default; `eval_journal = true` in config to enable. The user checks that the provider's terms allow keeping its outputs.
- Purpose: compare gateways per `TaskKind` (optional 1–5 rating) to decide routing. Evaluation set, not training data.

## 11. Profiles (development safeguard)
The coding assistant never sees data processed by the tool nor any gateway parameter.
- `dev` (default): run by the coding assistant or the developer; `fixtures/synthetic/` only; `MockModelGateway`.
- `real`: run by the user only, outside the VS Code terminal; real allowed folders; configured gateways.

Rules:
1. `real` database (journal included), index, logs and config under `%LOCALAPPDATA%\Tancrede`, never in the repo.
2. `dev` refuses any path outside the repo (T-DEV-01).
3. `real` refuses to start if environment variables reveal a VS Code or Claude Code terminal (T-DEV-02).
4. `real` logs: IDs, error codes, durations only; no source, prompt or answer text, exception traces included (T-DEV-03).
5. Second barrier: read-deny rule on `%LOCALAPPDATA%\Tancrede` in Claude Code settings.
6. Bug on real data: reproduce it on a fictitious case; never real content in the conversation.

## 12. Waves
Moving to the next wave = gate tests green.
- W0 Repo (public, MIT), uv, Ruff, pytest, pre-commit; synthetic corpus; `dev`/`real` profiles; `ModelRouter`, `MockModelGateway`, `OpenAICompatibleGateway`, plugin discovery; `check-gateway`. Gate: T-DEV-01…04, T-LLM-01, successful call to a local OpenAI-compatible server.
- W1 `ClassificationFilter`, allowed folders, `ModeGuard`, SQLite + migrations, FTS5 index. Gate: T-CLS-01…06, T-MODE-01…04 → real data allowed in `real`.
- W2 Search, evidence, contradictions, answers via router, no-model mode, evaluation journal. Gate: T-REL-01, T-CONFL-01, T-OFF-01, T-LLM-02, T-EVAL-01.
- W3 UI, mode indicator and warnings, notes, projects, proposals and confirmation. Gate: T-ACT-01/02, T-NOTE-01, T-MODE-05/06.
- W4 Packaging (`pyside6-deploy`, PyPI), README, end-to-end walkthrough, gap list. Gate: full scenario passes.

## 13. Open points
- CLS-01 (W1): label pattern syntax in config (plain strings, regex, or both).
- DEV-O-06 (W0): VS Code / Claude Code detection variables; deny-rule syntax.
- PUB-O-01 (W0): reserve `tancrede` on PyPI (empty 0.0.0 release).
