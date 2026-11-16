"""Read-only text extraction (R2). Returns `None` when no text can be extracted (SPEC §5)."""

from __future__ import annotations

import logging
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from defusedxml import ElementTree
from pypdf import PdfReader

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".pdf": "pdf",
    ".docx": "docx",
}
TEXT_ENCODINGS = ("utf-8-sig", "cp1252")
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class ExtractedDocument:
    path: Path
    kind: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def extract(path: Path) -> ExtractedDocument | None:
    kind = SUPPORTED_SUFFIXES.get(path.suffix.lower())
    if kind is None:
        return None
    try:
        if kind in {"markdown", "text"}:
            text, metadata = _plain(path)
        elif kind == "pdf":
            text, metadata = _pdf(path)
        else:
            text, metadata = _docx(path)
    except Exception as exc:  # any parser failure = non-extractable, never a crash
        log.info("extract.failed", extra={"code": type(exc).__name__})
        return None
    text = unicodedata.normalize("NFC", text)
    if not text.strip():
        return None
    metadata = {k: unicodedata.normalize("NFC", v) for k, v in metadata.items() if v}
    return ExtractedDocument(path=path, kind=kind, text=text, metadata=metadata)


def _plain(path: Path) -> tuple[str, dict[str, str]]:
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise ValueError("binary content")
    for encoding in TEXT_ENCODINGS:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - cp1252 decodes almost anything
        raise ValueError("unknown encoding")
    return _split_front_matter(text.replace("\r\n", "\n"))


def _split_front_matter(text: str) -> tuple[str, dict[str, str]]:
    """Simple `key: value` front matter between `---` lines."""
    if not text.startswith("---\n"):
        return text, {}
    end = text.find("\n---", 4)
    if end == -1:
        return text, {}
    metadata = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip():
            metadata[key.strip()] = value.strip()
    body = text[end + 4 :].lstrip("-").lstrip("\n")
    return body, metadata


def _pdf(path: Path) -> tuple[str, dict[str, str]]:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    metadata = {str(k).lstrip("/"): str(v) for k, v in (reader.metadata or {}).items()}
    return "\n\n".join(pages), metadata


def _docx(path: Path) -> tuple[str, dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        parts = ["word/document.xml"]
        parts += sorted(n for n in names if n.startswith(("word/header", "word/footer")))
        texts = [_docx_text(archive.read(p)) for p in parts if p in names]
        metadata: dict[str, str] = {}
        for meta_part in ("docProps/core.xml", "docProps/custom.xml", "docProps/app.xml"):
            if meta_part in names:
                metadata.update(_xml_leaf_values(archive.read(meta_part)))
    return "\n\n".join(t for t in texts if t), metadata


def _docx_text(xml: bytes) -> str:
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for para in root.iter(f"{W_NS}p"):
        paragraphs.append("".join(node.text or "" for node in para.iter(f"{W_NS}t")))
    return "\n".join(paragraphs)


def _xml_leaf_values(xml: bytes) -> dict[str, str]:
    values = {}
    for element in ElementTree.fromstring(xml).iter():
        if len(element) == 0 and element.text and element.text.strip():
            name = element.get("name") or element.tag.rpartition("}")[2]
            values[name] = element.text.strip()
    return values
