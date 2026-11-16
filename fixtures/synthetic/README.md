# Synthetic corpus

Invented people, projects, paths and labels only. Used by the `dev` profile and the tests
(SPEC §8). Labels: `FICTIVE-SECRET` (excluded), `FICTIVE-INTERNAL` (included).

| Case | Files |
|---|---|
| 1. Two sources disagree on a deadline | `documents/orion_kickoff.md`, `documents/orion_status.md` |
| 2. Labels: excluded (header, footer, body, metadata), included, none, both | `documents/label_*.md` |
| 3. Non-extractable text | `documents/scanned_report.pdf`, `documents/corrupted.docx` |
| 4. Prompt injection | `documents/vendor_reply.md` |
| 5. Proposal whose target changes | `proposals/stale_target.json` |
| 6. Note edited several times | `notes/note_revisions.json` |
