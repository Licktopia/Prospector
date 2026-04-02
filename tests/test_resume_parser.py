"""Tests for resume PDF parser."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.resume_parser import extract_text_from_pdf


def test_extract_text_file_not_found():
    """Should raise FileNotFoundError for missing PDF."""
    with pytest.raises(FileNotFoundError, match="Resume PDF not found"):
        extract_text_from_pdf("/nonexistent/resume.pdf")


@patch("app.services.resume_parser.pymupdf")
def test_extract_text_success(mock_pymupdf):
    """Should extract and join text from all pages."""
    # Mock the PDF document
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Page 1 content"
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Page 2 content"

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))

    mock_pymupdf.open.return_value = mock_doc

    # Need to patch Path.exists to return True
    with patch("app.services.resume_parser.Path") as mock_path_cls:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "test.pdf"
        mock_path.__str__ = lambda self: "/fake/test.pdf"
        mock_path_cls.return_value = mock_path

        result = extract_text_from_pdf("/fake/test.pdf")

    assert "Page 1 content" in result
    assert "Page 2 content" in result
    mock_doc.close.assert_called_once()


@patch("app.services.resume_parser.pymupdf")
def test_extract_text_runtime_error(mock_pymupdf):
    """Should wrap extraction errors in RuntimeError."""
    mock_pymupdf.open.side_effect = Exception("corrupt file")

    with patch("app.services.resume_parser.Path") as mock_path_cls:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_cls.return_value = mock_path

        with pytest.raises(RuntimeError, match="Failed to extract text"):
            extract_text_from_pdf("/fake/bad.pdf")
