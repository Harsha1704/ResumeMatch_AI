"""
Multimodal Resume Parsing Engine for PDF, DOCX, and TXT Documents.
Extracts clean text, preserves technical punctuation tokens, and detects section layout.
Handles scanned PDFs, corrupted files, and encoding variations safely without OCR dependencies.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import io
import re
import pymupdf  # PyMuPDF
import docx  # python-docx

from src.preprocessing.text_cleaner import clean_text, parse_structural_features


MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB limit
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text_from_pdf(stream_or_path: Union[str, Path, bytes, io.BytesIO]) -> Tuple[str, Dict]:
    """
    Extracts text and page layout metadata from PDF using PyMuPDF.
    Detects scanned PDFs with no extractable text.
    """
    metadata = {"format": "PDF", "page_count": 0, "is_scanned": False, "warnings": []}

    try:
        if isinstance(stream_or_path, (str, Path)):
            doc = pymupdf.open(stream_or_path)
        elif isinstance(stream_or_path, bytes):
            doc = pymupdf.open(stream=stream_or_path, filetype="pdf")
        elif isinstance(stream_or_path, io.BytesIO):
            doc = pymupdf.open(stream=stream_or_path.getvalue(), filetype="pdf")
        else:
            raise ValueError("Unsupported input stream type for PDF extraction.")

        metadata["page_count"] = len(doc)
        text_blocks = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                text_blocks.append(text)

        full_text = "\n".join(text_blocks).strip()

        # If zero or extremely few characters extracted from a multi-page PDF, flag as scanned
        if len(full_text) < 40 and metadata["page_count"] > 0:
            metadata["is_scanned"] = True
            metadata["warnings"].append(
                "Scanned or image-only PDF detected. PyMuPDF found no digital text layer."
            )

        return full_text, metadata

    except Exception as e:
        metadata["warnings"].append(f"PDF extraction error: {str(e)}")
        return "", metadata


def extract_text_from_docx(stream_or_path: Union[str, Path, bytes, io.BytesIO]) -> Tuple[str, Dict]:
    """
    Extracts text, paragraphs, and tables from DOCX documents using python-docx.
    """
    metadata = {"format": "DOCX", "paragraph_count": 0, "table_count": 0, "warnings": []}

    try:
        if isinstance(stream_or_path, (str, Path)):
            doc = docx.Document(stream_or_path)
        elif isinstance(stream_or_path, bytes):
            doc = docx.Document(io.BytesIO(stream_or_path))
        elif isinstance(stream_or_path, io.BytesIO):
            doc = docx.Document(stream_or_path)
        else:
            raise ValueError("Unsupported input stream type for DOCX extraction.")

        metadata["paragraph_count"] = len(doc.paragraphs)
        metadata["table_count"] = len(doc.tables)

        text_lines = []
        for p in doc.paragraphs:
            if p.text.strip():
                text_lines.append(p.text.strip())

        # Extract text from tables if any
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_lines.append(" | ".join(row_text))

        full_text = "\n".join(text_lines).strip()
        return full_text, metadata

    except Exception as e:
        metadata["warnings"].append(f"DOCX extraction error: {str(e)}")
        return "", metadata


def extract_text_from_txt(stream_or_path: Union[str, Path, bytes, io.BytesIO]) -> Tuple[str, Dict]:
    """
    Extracts text from plain text files with UTF-8 / Latin-1 fallback decoding.
    """
    metadata = {"format": "TXT", "warnings": []}

    try:
        if isinstance(stream_or_path, (str, Path)):
            with open(stream_or_path, "rb") as f:
                content_bytes = f.read()
        elif isinstance(stream_or_path, bytes):
            content_bytes = stream_or_path
        elif isinstance(stream_or_path, io.BytesIO):
            content_bytes = stream_or_path.getvalue()
        else:
            raise ValueError("Unsupported input stream type for TXT extraction.")

        # Attempt UTF-8 with fallback to Latin-1
        try:
            full_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            full_text = content_bytes.decode("latin-1", errors="replace")
            metadata["warnings"].append("Decoded using Latin-1 fallback due to non-UTF-8 characters.")

        return full_text.strip(), metadata

    except Exception as e:
        metadata["warnings"].append(f"TXT extraction error: {str(e)}")
        return "", metadata


def parse_resume(
    file_input: Union[str, Path, bytes, io.BytesIO],
    filename: Optional[str] = None
) -> Dict:
    """
    Master parser for uploaded candidate resumes:
    - Identifies document format from filename or file signature
    - Extracts raw and cleaned text
    - Identifies structural sections and layout indicators
    - Returns structured extraction metadata and validation status
    """
    result = {
        "filename": filename or "resume_input",
        "raw_text": "",
        "cleaned_text": "",
        "structural_features": {},
        "metadata": {},
        "status": "success",
        "error_message": None,
        "warnings": []
    }

    # Determine extension
    ext = ""
    if filename:
        ext = Path(filename).suffix.lower()
    elif isinstance(file_input, (str, Path)):
        ext = Path(file_input).suffix.lower()

    if not ext:
        # Try detection from bytes magic numbers if possible
        if isinstance(file_input, bytes):
            if file_input.startswith(b"%PDF"):
                ext = ".pdf"
            elif file_input.startswith(b"PK\x03\x04"):
                ext = ".docx"
            else:
                ext = ".txt"
        else:
            ext = ".txt"

    if ext not in SUPPORTED_EXTENSIONS:
        result["status"] = "error"
        result["error_message"] = (
            f"Unsupported file format '{ext}'. Please upload a PDF, DOCX, or TXT file."
        )
        return result

    # Check size
    if isinstance(file_input, bytes) and len(file_input) > MAX_FILE_SIZE:
        result["status"] = "error"
        result["error_message"] = "File size exceeds 16 MB limit."
        return result

    # Perform format-specific extraction
    if ext == ".pdf":
        raw_text, meta = extract_text_from_pdf(file_input)
    elif ext == ".docx":
        raw_text, meta = extract_text_from_docx(file_input)
    elif ext == ".txt":
        raw_text, meta = extract_text_from_txt(file_input)
    else:
        result["status"] = "error"
        result["error_message"] = f"Unsupported file type: {ext}"
        return result

    result["metadata"] = meta
    result["warnings"].extend(meta.get("warnings", []))

    if meta.get("is_scanned", False):
        result["status"] = "scanned_pdf"
        result["error_message"] = (
            "The uploaded PDF appears to be a scanned image with no readable text layer. "
            "Please upload a digitally created PDF, DOCX, or text resume."
        )
        return result

    if not raw_text.strip():
        result["status"] = "empty"
        result["error_message"] = "The document is empty or text extraction returned no content."
        return result

    # Clean text and extract structure
    cleaned = clean_text(raw_text)
    struct = parse_structural_features(raw_text)

    result["raw_text"] = raw_text
    result["cleaned_text"] = cleaned
    result["structural_features"] = struct
    return result
