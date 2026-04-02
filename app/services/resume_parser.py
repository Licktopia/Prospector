"""Extract text from resume PDF files using PyMuPDF."""

import logging
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract all text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text content as a single string.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        RuntimeError: If text extraction fails.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume PDF not found: {path}")

    try:
        doc = pymupdf.open(path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()

        full_text = "\n".join(text_parts).strip()
        logger.info("Extracted %d characters from %s", len(full_text), path.name)
        return full_text
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {path}: {e}") from e
