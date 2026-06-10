"""Document parsing utilities."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_document(file_path: str) -> str:
    """Parse a document file and return its text content."""
    ext = Path(file_path).suffix.lower().lstrip(".")

    parsers = {
        "txt": _parse_txt,
        "md": _parse_txt,
        "html": _parse_html,
        "pdf": _parse_pdf,
        "docx": _parse_docx,
    }

    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: .{ext}")

    return parser(file_path)


def _parse_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _parse_html(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # Simple HTML tag stripping
    import re

    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_pdf(file_path: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required to parse PDF files")

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _parse_docx(file_path: str) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ImportError("python-docx is required to parse DOCX files")

    doc = DocxDocument(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
