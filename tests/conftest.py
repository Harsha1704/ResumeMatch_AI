import pytest
from app import app

@pytest.fixture(autouse=True)
def enable_testing_mode():
    """Ensure Flask application is in testing mode during pytest runs."""
    prev = app.config.get("TESTING", False)
    app.config["TESTING"] = True
    yield
    app.config["TESTING"] = prev
