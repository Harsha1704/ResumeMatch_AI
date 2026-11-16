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
MAX_PAGE_COUNT = 30  # Maximum allowed PDF page count
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# DOCX archive safety limits against zip bombs / decompressed bombs
MAX_DOCX_MEMBER_COUNT = 500  # Maximum number of entries in DOCX ZIP container
MAX_DOCX_UNCOMPRESSED_SIZE = 64 * 1024 * 1024  # 64 MB maximum uncompressed size
MAX_DOCX_SINGLE_MEMBER_SIZE = 32 * 1024 * 1024  # 32 MB maximum size for any single member
MAX_DOCX_COMPRESSION_RATIO = 100.0  # Maximum uncompressed/compressed ratio for entries > 10KB


def validate_docx_archive_safety(payload: bytes) -> Optional[str]:
    """
    Validates DOCX OpenXML ZIP container against archive bombs:
    - Verifies valid ZIP structure and required 'word/document.xml' entry.
    - Limits total entry count (MAX_DOCX_MEMBER_COUNT).
    - Limits individual member uncompressed size (MAX_DOCX_SINGLE_MEMBER_SIZE).
    - Limits total uncompressed archive size (MAX_DOCX_UNCOMPRESSED_SIZE).
    - Rejects suspicious compression ratios exceeding MAX_DOCX_COMPRESSION_RATIO.
    Returns error string if safety policy is violated, otherwise None.
    """
    if not payload.startswith(b"PK\x03\x04"):
        return "Invalid DOCX file: missing the standard ZIP/OpenXML header."

    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCX_MEMBER_COUNT:
                return f"Security violation: DOCX member count ({len(members)}) exceeds maximum allowable limit of {MAX_DOCX_MEMBER_COUNT} (archive bomb protection)."

            total_uncompressed = 0
            has_word_doc = False

            for info in members:
                if info.filename == "word/document.xml":
                    has_word_doc = True

                # Check single member size
                if info.file_size > MAX_DOCX_SINGLE_MEMBER_SIZE:
                    return f"Security violation: DOCX member '{info.filename}' size ({info.file_size} bytes) exceeds maximum allowable limit of {MAX_DOCX_SINGLE_MEMBER_SIZE} bytes (archive bomb protection)."

                total_uncompressed += info.file_size
                if total_uncompressed > MAX_DOCX_UNCOMPRESSED_SIZE:
                    return f"Security violation: Total uncompressed DOCX size ({total_uncompressed} bytes) exceeds maximum allowable limit of {MAX_DOCX_UNCOMPRESSED_SIZE} bytes (archive bomb protection)."

                # Check compression ratio on non-trivial files
                if info.file_size > 10240 and info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > MAX_DOCX_COMPRESSION_RATIO:
                        return f"Security violation: Suspicious compression ratio ({ratio:.1f}:1) detected in DOCX member '{info.filename}' (archive bomb protection)."

            if not has_word_doc:
                return "Invalid or corrupted DOCX document: missing 'word/document.xml'."

            if archive.testzip() is not None:
                return "Invalid or corrupted DOCX document: archive member failed integrity test."

    except (zipfile.BadZipFile, OSError):
        return "Invalid or corrupted DOCX document."

    return None


def extract_text_from_pdf(
    stream_or_path: Union[str, Path, bytes, io.BytesIO],
    filename_hint: Optional[str] = None
) -> Tuple[str, Dict]:
    """
    Extracts text and page layout metadata from PDF using PyMuPDF.
    Detects scanned PDFs with no extractable text, password-protected/encrypted PDFs,
    and enforces page count constraints.
    """
    metadata = {
        "format": "PDF",
        "page_count": 0,
        "is_scanned": False,
        "is_blank": False,
        "has_images": False,
        "has_drawings": False,
        "is_encrypted": False,
        "warnings": []
    }
    doc = None
    filename = ""
    if isinstance(stream_or_path, (str, Path)):
        filename = str(stream_or_path)
    elif filename_hint:
        filename = filename_hint

    try:
        if isinstance(stream_or_path, (str, Path)):
            doc = pymupdf.open(stream_or_path)
        elif isinstance(stream_or_path, bytes):
            doc = pymupdf.open(stream=stream_or_path, filetype="pdf")
        elif isinstance(stream_or_path, io.BytesIO):
            doc = pymupdf.open(stream=stream_or_path.getvalue(), filetype="pdf")
        else:
            raise ValueError("Unsupported input stream type for PDF extraction.")

        # Check for encrypted or password-protected PDF
        if getattr(doc, "is_encrypted", False) or getattr(doc, "needs_pass", False):
            metadata["is_encrypted"] = True
            metadata["warnings"].append("PDF is encrypted or password-protected.")
            return "", metadata

        page_count = len(doc)
        metadata["page_count"] = page_count

        if page_count > MAX_PAGE_COUNT:
            metadata["warnings"].append(
                f"Document exceeds maximum allowable page limit of {MAX_PAGE_COUNT} pages (received {page_count} pages)."
            )
            return "", metadata

        has_images = False
        has_drawings = False
        text_blocks = []
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                text_blocks.append(text)
            if not has_images and len(page.get_images()) > 0:
                has_images = True
            if not has_drawings and len(page.get_drawings()) > 0:
                has_drawings = True

        full_text = "\n".join(text_blocks).strip()
        metadata["has_images"] = has_images
        metadata["has_drawings"] = has_drawings

        is_scanned_indicator = (
            has_images
            or has_drawings
            or ("scanned" in filename.lower() and len(full_text) == 0)
        )

        # Refined scanned PDF detection:
        # Distinguish genuine image-only scans from short digital-text PDFs containing logos or profile images
        words = [w for w in re.split(r"\s+", full_text) if re.search(r"[a-zA-Z0-9]", w)]
        has_meaningful_text = len(words) >= 2 or len(full_text.strip()) >= 15

        if len(full_text.strip()) == 0 and is_scanned_indicator:
            metadata["is_scanned"] = True
            metadata["warnings"].append(
                "Scanned or image-only PDF detected. PyMuPDF found no digital text layer."
            )
        elif len(full_text.strip()) == 0:
            metadata["is_blank"] = True
            metadata["warnings"].append("The PDF document contains blank pages with no text content.")
        elif not has_meaningful_text and has_images:
            metadata["is_scanned"] = True
            metadata["warnings"].append(
                "Scanned or image-only PDF detected. The document contains images but lacks readable digital text."
            )

        return full_text, metadata

    except Exception as e:
        metadata["warnings"].append(f"PDF extraction error: {str(e)}")
        return "", metadata
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


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
        "candidate_profile": {},
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

    if len(payload) == 0:
        result["status"] = "empty"
        result["error_message"] = "The document is empty or contains 0 bytes."
        return result

    if not ext:
        if payload.startswith(b"%PDF-"):
            ext = ".pdf"
        elif payload.startswith(b"PK\x03\x04"):
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
        docx_err = validate_docx_archive_safety(payload)
        if docx_err:
            result["status"] = "error"
            result["error_message"] = docx_err
            return result
    if ext == ".txt" and b"\x00" in payload:
        result["status"] = "error"
        result["error_message"] = "Invalid TXT file: binary null bytes were detected."
        return result

    if ext == ".pdf":
        raw_text, meta = extract_text_from_pdf(payload, filename_hint=filename)
    elif ext == ".docx":
        raw_text, meta = extract_text_from_docx(payload)
    else:
        raw_text, meta = extract_text_from_txt(payload)

    result["metadata"] = meta
    result["warnings"].extend(meta.get("warnings", []))

    if meta.get("is_encrypted", False):
        result["status"] = "password_protected"
        result["error_message"] = (
            "The uploaded PDF is password-protected or encrypted. Please provide an unencrypted document."
        )
        return result

    if meta.get("page_count", 0) > MAX_PAGE_COUNT:
        result["status"] = "error"
        result["error_message"] = (
            f"Document exceeds maximum allowable page limit of {MAX_PAGE_COUNT} pages (received {meta['page_count']} pages)."
        )
        return result

    if meta.get("is_scanned", False):
        result["status"] = "scanned_pdf"
        result["error_message"] = (
            "The uploaded PDF appears to be a scanned image with no readable text layer. "
            "Please upload a digitally created PDF, DOCX, or text resume."
        )
        return result

    if meta.get("is_blank", False) or not raw_text.strip():
        result["status"] = "empty"
        result["error_message"] = "The document is empty or text extraction returned no content."
        return result

    cleaned = clean_text(raw_text)
    struct = parse_structural_features(raw_text)

    from src.analysis.candidate_profile_extractor import extract_candidate_profile
    candidate_profile = extract_candidate_profile(raw_text, cleaned_text=cleaned)

    result["raw_text"] = raw_text
    result["cleaned_text"] = cleaned
    result["structural_features"] = struct
    result["candidate_profile"] = candidate_profile
    return result
