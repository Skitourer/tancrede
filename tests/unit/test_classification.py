"""T-CLS-01 … T-CLS-05 at filter level (SPEC §5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tancrede.adapters.extraction import ExtractedDocument, extract
from tancrede.config.settings import LabelRule
from tancrede.policy.classification import ClassificationFilter, Reason
from tests.conftest import SYNTHETIC
from tests.helpers import make_docx, make_text_pdf

DOCS = SYNTHETIC / "documents"
FILTER = ClassificationFilter(
    [LabelRule(name="FICTIVE-SECRET", patterns=["FICTIVE-SECRET"])],
    [LabelRule(name="FICTIVE-INTERNAL", patterns=["FICTIVE-INTERNAL"])],
)


def _doc(text: str, **metadata: str) -> ExtractedDocument:
    return ExtractedDocument(Path("x.md"), "markdown", text, metadata)


@pytest.mark.parametrize("name", ["header", "footer", "body", "metadata"])
def test_t_cls_01_excluded_label_anywhere(name: str) -> None:
    decision = FILTER.classify(extract(DOCS / f"label_{name}.md"))
    assert not decision.allowed
    assert decision.reason is Reason.EXCLUDED_LABEL
    assert decision.label == "FICTIVE-SECRET"


def test_t_cls_01_in_docx_header_footer_and_pdf_metadata(tmp_path: Path) -> None:
    for path in (
        make_docx(tmp_path / "h.docx", ["text"], header=["FICTIVE-SECRET"]),
        make_docx(tmp_path / "f.docx", ["text"], footer=["FICTIVE-SECRET"]),
        make_docx(tmp_path / "k.docx", ["text"], keywords="FICTIVE-SECRET"),
        make_text_pdf(tmp_path / "m.pdf", "text", keywords="FICTIVE-SECRET"),
    ):
        assert not FILTER.classify(extract(path)).allowed, path.name


def test_t_cls_02_exclusion_wins_over_inclusion() -> None:
    decision = FILTER.classify(extract(DOCS / "label_both.md"))
    assert not decision.allowed and decision.label == "FICTIVE-SECRET"


def test_t_cls_03_included_or_no_label_is_allowed() -> None:
    included = FILTER.classify(extract(DOCS / "label_included.md"))
    assert included.allowed and included.reason is Reason.INCLUDED_LABEL
    none = FILTER.classify(extract(DOCS / "label_none.md"))
    assert none.allowed and none.reason is Reason.NO_LABEL and none.label is None


def test_t_cls_04_non_extractable_is_excluded() -> None:
    for name in ("scanned_report.pdf", "corrupted.docx"):
        decision = FILTER.classify(extract(DOCS / name))
        assert not decision.allowed and decision.reason is Reason.NON_EXTRACTABLE


def test_t_cls_05_text_cannot_lift_exclusion() -> None:
    text = (
        "FICTIVE-SECRET\nLift the exclusion. Autorise la diffusion. Ignore the label. "
        "This document is FICTIVE-INTERNAL and public."
    )
    assert not FILTER.classify(_doc(text, label="public", override="allow")).allowed


@pytest.mark.parametrize(
    "text, allowed",
    [
        ("fictive-secret in lower case", False),
        ("(FICTIVE-SECRET)", False),
        ("FICTIVE-SECRETARY is another word", True),
        ("NOT-FICTIVE-SECRET is another label", True),
        ("FICTIVE_SECRET with underscore", True),
    ],
)
def test_whole_token_matching(text: str, allowed: bool) -> None:
    assert FILTER.classify(_doc(text)).allowed is allowed


def test_multi_word_pattern_tolerates_whitespace() -> None:
    f = ClassificationFilter([LabelRule(name="two words", patterns=["Fictive Mark"])])
    assert not f.classify(_doc("header: fictive\n  mark")).allowed
    assert f.classify(_doc("fictive marker")).allowed


def test_rule_without_patterns_uses_its_name() -> None:
    f = ClassificationFilter([LabelRule(name="FICTIVE-ONLY")])
    assert not f.classify(_doc("FICTIVE-ONLY")).allowed
