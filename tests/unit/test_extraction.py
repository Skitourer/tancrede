from __future__ import annotations

from pathlib import Path

from tancrede.adapters.extraction import extract
from tests.conftest import SYNTHETIC
from tests.helpers import make_docx, make_text_pdf

DOCS = SYNTHETIC / "documents"


def test_markdown_front_matter_goes_to_metadata() -> None:
    doc = extract(DOCS / "label_metadata.md")
    assert doc is not None
    assert doc.metadata["label"] == "FICTIVE-SECRET"
    assert "Helios risk register" in doc.text
    assert "label:" not in doc.text


def test_text_in_windows_encoding(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_bytes("Réunion prévue à Grenoble".encode("cp1252"))
    doc = extract(path)
    assert doc is not None and doc.text == "Réunion prévue à Grenoble"


def test_pdf_with_text_layer(tmp_path: Path) -> None:
    doc = extract(make_text_pdf(tmp_path / "a.pdf", "Orion bench booked", keywords="FICTIVE-X"))
    assert doc is not None
    assert "Orion bench booked" in doc.text
    assert doc.metadata["Keywords"] == "FICTIVE-X"


def test_docx_body_header_footer_and_properties(tmp_path: Path) -> None:
    path = make_docx(
        tmp_path / "a.docx", ["Body line"], header=["Top"], footer=["Bottom"], keywords="kw"
    )
    doc = extract(path)
    assert doc is not None
    for part in ("Body line", "Top", "Bottom"):
        assert part in doc.text
    assert doc.metadata["keywords"] == "kw"


def test_non_extractable_files_return_none(tmp_path: Path) -> None:
    assert extract(DOCS / "scanned_report.pdf") is None
    assert extract(DOCS / "corrupted.docx") is None
    empty = tmp_path / "empty.md"
    empty.write_text("   \n", encoding="utf-8")
    assert extract(empty) is None
    binary = tmp_path / "x.txt"
    binary.write_bytes(b"abc\x00def")
    assert extract(binary) is None


def test_unsupported_suffix(tmp_path: Path) -> None:
    other = tmp_path / "a.xlsx"
    other.write_bytes(b"data")
    assert extract(other) is None
