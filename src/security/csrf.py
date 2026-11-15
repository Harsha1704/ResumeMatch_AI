"""
src/security/csrf.py
CSRF (Cross-Site Request Forgery) protection:
- Issues cryptographically secure tokens stored in user session.
- Validates tokens on state-changing HTML form and browser API requests (JSON and multipart).
- Uses constant-time comparison (secrets.compare_digest) to prevent timing side-channel attacks.
- Protects against cross-origin forgery while permitting explicitly documented headless API endpoints.
"""

import secrets
from typing import Optional
from flask import session, request


class CSRFError(Exception):
    """Raised when CSRF token is missing or invalid."""
    pass


def generate_csrf_token() -> str:
    """Generates or retrieves existing CSRF token for the active session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(token: Optional[str]) -> bool:
    """
    Validates submitted CSRF token against active session token.
    Uses constant-time comparison to prevent timing attacks.
    """
    expected = session.get("csrf_token")
    if not expected or not token or not isinstance(token, str):
        return False
    return secrets.compare_digest(expected, token.strip())


def get_submitted_csrf_token() -> Optional[str]:
    """
    Extracts CSRF token from request headers (preferred for APIs),
    JSON body, or multipart/urlencoded form data.
    """
    # 1. Custom request headers (standard in SPA / React fetch)
    token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
    if token:
        return token

    # 2. Form data (multipart or urlencoded)
    if request.form and "csrf_token" in request.form:
        return request.form.get("csrf_token")

    # 3. JSON body
    if request.is_json:
        try:
            body = request.get_json(silent=True)
            if isinstance(body, dict) and "csrf_token" in body:
                return body.get("csrf_token")
        except Exception:
            pass

    return None


def validate_request_csrf() -> bool:
    """
    Inspects current incoming request and validates its CSRF token against session.
    Returns True if valid, False if missing or invalid.
    """
    token = get_submitted_csrf_token()
    return validate_csrf_token(token)
