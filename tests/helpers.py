"""Builders for test documents (fictitious content only)."""

from __future__ import annotations

import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _paragraphs(lines: list[str]) -> str:
    return "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in lines)


def make_docx(
    path: Path,
    body: list[str],
    header: list[str] | None = None,
    footer: list[str] | None = None,
    keywords: str | None = None,
) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{W}"><w:body>{_paragraphs(body)}</w:body></w:document>',
        )
        if header:
            z.writestr("word/header1.xml", f'<w:hdr xmlns:w="{W}">{_paragraphs(header)}</w:hdr>')
        if footer:
            z.writestr("word/footer1.xml", f'<w:ftr xmlns:w="{W}">{_paragraphs(footer)}</w:ftr>')
        if keywords:
            z.writestr(
                "docProps/core.xml",
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
                f'metadata/core-properties"><cp:keywords>{keywords}</cp:keywords>'
                "</cp:coreProperties>",
            )
    return path


def make_text_pdf(path: Path, text: str, keywords: str | None = None) -> Path:
    """Minimal one-page PDF with a real text layer."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    info = f"<< /Keywords ({keywords}) >>" if keywords else "<< >>"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        info.encode(),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))
    return path
