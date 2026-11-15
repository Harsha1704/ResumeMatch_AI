"""WSGI entry point used by the Render Gunicorn service."""

from app import app

__all__ = ["app"]
