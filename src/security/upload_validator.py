"""
src/security/upload_validator.py
Security validation for resume uploads:
- File type and extension whitelisting (.pdf, .docx, .txt).
- Magic bytes content inspection to prevent executable masquerading.
- Strict file size constraints (max 16 MB).
- Filename sanitization and path traversal prevention.
- Zero untrusted filesystem writes.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024  # 16 MB


class UploadSecurityError(ValueError):
    """Raised when an uploaded document violates security or validation policies."""
    pass


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitizes filename and prevents directory traversal attacks:
    - Strips leading/trailing whitespace
    - Rejects null bytes, path traversal sequences ('..', '/', '\\')
    - Applies werkzeug secure_filename
    """
    if not filename:
        return "uploaded_resume.txt"

    # Reject null bytes and path traversal patterns
    if "\0" in filename or ".." in filename or "/" in filename or "\\" in filename:
        clean = Path(filename).name
    else:
        clean = filename

    secured = secure_filename(clean)
    if not secured:
        return "uploaded_resume.txt"
    return secured


def validate_file_content(content_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Performs deep validation on uploaded file:
    1. Size verification.
    2. Extension whitelisting.
    3. Magic byte signature verification.
    Returns (is_valid, sanitized_filename). Raises UploadSecurityError on violation.
    """
    if not content_bytes:
        raise UploadSecurityError("Uploaded file is empty (0 bytes).")

    size = len(content_bytes)
    if size > MAX_FILE_SIZE_BYTES:
        raise UploadSecurityError(f"File size exceeds maximum allowable limit of 16 MB (received {size / (1024*1024):.2f} MB).")

    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise UploadSecurityError(f"Disallowed file extension '{ext}'. Only .pdf, .docx, and .txt files are accepted.")

    # Magic Bytes / Content Sniffing
    if ext == ".pdf":
        if not content_bytes.startswith(b"%PDF-"):
            raise UploadSecurityError("Invalid PDF file: Missing standard %PDF- header signature.")
    elif ext == ".docx":
        # DOCX is an OpenXML ZIP container starting with PK\x03\x04
        if not content_bytes.startswith(b"PK\x03\x04"):
            raise UploadSecurityError("Invalid DOCX file: Missing standard ZIP/OpenXML PK header signature.")
    elif ext == ".txt":
        # TXT must decode cleanly without null bytes
        if b"\x00" in content_bytes:
            raise UploadSecurityError("Invalid TXT file: Contains binary null bytes.")
        try:
            content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_bytes.decode("latin-1")
            except Exception:
                raise UploadSecurityError("Invalid TXT file: Content is not valid text encoding.")

    return True, safe_name
