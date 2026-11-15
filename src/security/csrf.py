"""
src/security/csrf.py
CSRF (Cross-Site Request Forgery) protection:
- Issues secure cryptographic tokens stored in user session.
- Validates tokens on all state-changing HTML form POST requests.
- Protects against cross-origin form forgery while permitting headless JSON API routes.
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


def validate_csrf_token(form_token: Optional[str]) -> bool:
    """
    Validates submitted CSRF token against active session token.
    Uses constant-time comparison to prevent timing attacks.
    """
    expected = session.get("csrf_token")
    if not expected or not form_token:
        return False
    return secrets.compare_digest(expected, form_token)
