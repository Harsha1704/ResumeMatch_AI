"""
Multimodal Resume Parsing Engine for PDF, DOCX, and TXT Documents.
Extracts clean text, preserves technical punctuation tokens, and detects section layout.
Handles scanned PDFs, corrupted files, and encoding variations safely without OCR dependencies.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import io
import re
import zipfile
import pymupdf  # PyMuPDF
import docx  # python-docx
from docx.text.paragraph import Paragraph
from docx.table import Table

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

        # Preserve the original order of paragraphs and tables. Reading all
        # paragraphs first and all tables second can scramble section boundaries
        # in resumes that use tables for education or work history.
        text_lines = []
        for child in doc.element.body.iterchildren():
            if child.tag.endswith("}p"):
                paragraph = Paragraph(child, doc)
                if paragraph.text.strip():
                    text_lines.append(paragraph.text.strip())
            elif child.tag.endswith("}tbl"):
                table = Table(child, doc)
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


def _read_resume_bytes(file_input: Union[str, Path, bytes, io.BytesIO]) -> Tuple[Optional[bytes], Optional[str]]:
    """Read supported input safely, enforcing the size limit before loading paths."""
    if isinstance(file_input, bytes):
        payload = file_input
    elif isinstance(file_input, io.BytesIO):
        payload = file_input.getvalue()
    elif isinstance(file_input, (str, Path)):
        path = Path(file_input)
        try:
            if not path.is_file():
                return None, "Resume file path does not exist or is not a regular file."
            if path.stat().st_size > MAX_FILE_SIZE:
                return None, "File size exceeds 16 MB limit."
            payload = path.read_bytes()
        except OSError:
            return None, "Resume file could not be read."
    else:
        return None, "Unsupported resume input type."

    if len(payload) > MAX_FILE_SIZE:
        return None, "File size exceeds 16 MB limit."
    return payload, None


def parse_resume(
    file_input: Union[str, Path, bytes, io.BytesIO],
    filename: Optional[str] = None
) -> Dict:
    """
    Master parser for uploaded candidate resumes:
    - Identifies document format from filename or file signature
    - Enforces size and content-signature validation for every input type
    - Preserves interleaved paragraph/table order in DOCX resumes
    - Extracts raw and cleaned text and structural metadata
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

    ext = Path(filename).suffix.lower() if filename else ""
    if not ext and isinstance(file_input, (str, Path)):
        ext = Path(file_input).suffix.lower()

    payload, read_error = _read_resume_bytes(file_input)
    if read_error:
        result["status"] = "error"
        result["error_message"] = read_error
        return result

    if not ext:
        if payload.startswith(b"%PDF-"):
            ext = ".pdf"
        elif payload.startswith(b"PK\\x03\\x04"):
            ext = ".docx"
        else:
            ext = ".txt"

    if ext not in SUPPORTED_EXTENSIONS:
        result["status"] = "error"
        result["error_message"] = (
            f"Unsupported file format '{ext}'. Please upload a PDF, DOCX, or TXT file."
        )
        return result

    # Defense-in-depth format validation also protects direct parser/API use.
    if ext == ".pdf" and not payload.startswith(b"%PDF-"):
        result["status"] = "error"
        result["error_message"] = "Invalid PDF file: missing the standard %PDF- header."
        return result
    if ext == ".docx":
        if not payload.startswith(b"PK\\x03\\x04"):
            result["status"] = "error"
            result["error_message"] = "Invalid DOCX file: missing the standard ZIP/OpenXML header."
            return result
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise zipfile.BadZipFile("Missing word/document.xml")
                if archive.testzip() is not None:
                    raise zipfile.BadZipFile("Corrupt DOCX archive member")
        except (zipfile.BadZipFile, OSError):
            result["status"] = "error"
            result["error_message"] = "Invalid or corrupted DOCX document."
            return result
    if ext == ".txt" and b"\\x00" in payload:
        result["status"] = "error"
        result["error_message"] = "Invalid TXT file: binary null bytes were detected."
        return result

    if ext == ".pdf":
        raw_text, meta = extract_text_from_pdf(payload)
    elif ext == ".docx":
        raw_text, meta = extract_text_from_docx(payload)
    else:
        raw_text, meta = extract_text_from_txt(payload)

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

    cleaned = clean_text(raw_text)
    struct = parse_structural_features(raw_text)

    result["raw_text"] = raw_text
    result["cleaned_text"] = cleaned
    result["structural_features"] = struct
    return result
