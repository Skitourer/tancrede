"""The synthetic corpus covers the six required cases (SPEC §8)."""

from __future__ import annotations

import json
import tomllib

from tests.conftest import SYNTHETIC

DOCS = SYNTHETIC / "documents"


def test_deadline_disagreement() -> None:
    a = (DOCS / "orion_kickoff.md").read_text(encoding="utf-8")
    b = (DOCS / "orion_status.md").read_text(encoding="utf-8")
    assert "2027-03-15" in a and "2027-04-01" in b


def test_label_cases() -> None:
    for name in ("header", "footer", "body", "metadata", "both"):
        assert "FICTIVE-SECRET" in (DOCS / f"label_{name}.md").read_text(encoding="utf-8")
    assert "FICTIVE-INTERNAL" in (DOCS / "label_included.md").read_text(encoding="utf-8")
    none = (DOCS / "label_none.md").read_text(encoding="utf-8")
    assert "FICTIVE" not in none
    labels = tomllib.loads((SYNTHETIC / "labels.toml").read_text(encoding="utf-8"))
    assert labels["classification"]["excluded_labels"][0]["name"] == "FICTIVE-SECRET"


def test_non_extractable_files() -> None:
    pdf = (DOCS / "scanned_report.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and b"/Font" not in pdf  # image only, no text layer
    assert not (DOCS / "corrupted.docx").read_bytes().startswith(b"PK\x03\x04")


def test_prompt_injection_present() -> None:
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in (DOCS / "vendor_reply.md").read_text("utf-8")


def test_stale_proposal_and_note_revisions() -> None:
    stale = json.loads((SYNTHETIC / "proposals" / "stale_target.json").read_text("utf-8"))
    assert stale["proposal"]["target_version"] < stale["task_before_execution"]["version"]
    note = json.loads((SYNTHETIC / "notes" / "note_revisions.json").read_text("utf-8"))
    assert [r["version"] for r in note["revisions"]] == [1, 2, 3]
