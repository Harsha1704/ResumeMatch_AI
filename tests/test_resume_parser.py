"""
Unit tests for resume document parser (PDF, DOCX, TXT).
Verifies format extraction, layout indicators, corrupted files, and scanned document detection.
"""

from pathlib import Path
import io
import pytest
import pymupdf
import docx

from src.analysis.resume_parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    parse_resume
)


def test_txt_resume_parsing(tmp_path):
    """Verify standard text resume parsing and character extraction."""
    txt_content = (
        "John Doe\n"
        "Senior Software Engineer\n"
        "Skills: Python, C++, Docker, SQL\n"
        "Experience: 5+ years of experience in distributed systems.\n"
    )
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text(txt_content, encoding="utf-8")

    res = parse_resume(txt_file, filename="resume.txt")
    assert res["status"] == "success"
    assert "John Doe" in res["raw_text"]
    assert "python" in res["cleaned_text"].lower()
    assert res["structural_features"]["explicit_years_exp"] == 5.0


def test_pdf_resume_parsing(tmp_path):
    """Generate and parse a valid digital PDF using PyMuPDF."""
    pdf_path = tmp_path / "candidate_resume.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Jane Smith - Machine Learning Engineer\n"
        "Experience: 4 years of experience with PyTorch, Scikit-learn, and AWS.\n"
        "Education: Bachelor of Science in Computer Science.\n"
    )
    doc.save(str(pdf_path))
    doc.close()

    res = parse_resume(pdf_path, filename="candidate_resume.pdf")
    assert res["status"] == "success"
    assert "Jane Smith" in res["raw_text"]
    assert res["metadata"]["page_count"] == 1
    assert not res["metadata"]["is_scanned"]
    assert res["structural_features"]["explicit_years_exp"] == 4.0


def test_docx_resume_parsing(tmp_path):
    """Generate and parse a valid DOCX document using python-docx."""
    docx_path = tmp_path / "test_resume.docx"
    doc = docx.Document()
    doc.add_heading("Alex Johnson", level=1)
    doc.add_paragraph("Full Stack Developer with 3 years exp in React, Node.js, and MongoDB.")
    doc.save(str(docx_path))

    res = parse_resume(docx_path, filename="test_resume.docx")
    assert res["status"] == "success"
    assert "Alex Johnson" in res["raw_text"]
    assert res["metadata"]["paragraph_count"] >= 2
    assert "node.js" in res["cleaned_text"].lower()


def test_invalid_extension_rejection():
    """Verify unsupported extensions (.exe, .jpg, .zip) are rejected gracefully."""
    res = parse_resume(b"binary data", filename="resume.exe")
    assert res["status"] == "error"
    assert "Unsupported file format" in res["error_message"]


def test_empty_document_handling(tmp_path):
    """Verify empty documents return an informative status."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    res = parse_resume(empty_file, filename="empty.txt")
    assert res["status"] == "empty"
    assert "empty" in res["error_message"].lower()


def test_corrupted_pdf_handling(tmp_path):
    """Verify corrupted PDF bytes do not crash the system."""
    corrupted_pdf = tmp_path / "broken.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.4 corrupted invalid bytes here \x00\x01\x02")

    res = parse_resume(corrupted_pdf, filename="broken.pdf")
    # PyMuPDF will either catch error or return empty text with warning
    assert res["status"] in ["empty", "error", "scanned_pdf"]


def test_scanned_pdf_detection(tmp_path):
    """Verify multi-page PDF with zero text characters is flagged as scanned."""
    scanned_pdf = tmp_path / "scanned_invoice.pdf"
    doc = pymupdf.open()
    doc.new_page()  # Page with no text
    doc.save(str(scanned_pdf))
    doc.close()

    res = parse_resume(scanned_pdf, filename="scanned_invoice.pdf")
    assert res["status"] == "scanned_pdf"
    assert "scanned" in res["error_message"].lower()



def test_docx_preserves_interleaved_paragraph_and_table_order(tmp_path):
    """DOCX extraction must not move tables after all paragraphs."""
    docx_path = tmp_path / "ordered_resume.docx"
    document = docx.Document()
    document.add_paragraph("EXPERIENCE")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Example Corp — Software Engineer"
    document.add_paragraph("PROJECTS")
    document.save(str(docx_path))

    parsed = parse_resume(docx_path, filename="ordered_resume.docx")
    assert parsed["status"] == "success"
    text = parsed["raw_text"]
    assert text.index("EXPERIENCE") < text.index("Example Corp")
    assert text.index("Example Corp") < text.index("PROJECTS")


def test_parser_rejects_wrong_file_signature():
    """A valid extension must not allow unrelated content through the parser."""
    result = parse_resume(b"this is not a pdf document", filename="resume.pdf")
    assert result["status"] == "error"
    assert "Invalid PDF" in result["error_message"]


def test_parser_rejects_binary_txt_content():
    result = parse_resume(b"resume\x00binary", filename="resume.txt")
    assert result["status"] == "error"
    assert "null bytes" in result["error_message"]


def test_parser_enforces_size_limit_for_bytesio():
    from src.analysis.resume_parser import MAX_FILE_SIZE
    result = parse_resume(io.BytesIO(b"x" * (MAX_FILE_SIZE + 1)), filename="large.txt")
    assert result["status"] == "error"
    assert "16 MB" in result["error_message"]
