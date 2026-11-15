"""
Unit tests for Flask application routes and scaffolding.
Multimodal Resume-Job Matching & Skill Gap Analysis System.
"""

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check_endpoint(client):
    """Verify /health returns 200 and healthy JSON payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_main_routes_render(client):
    """Verify primary web routes render without template or routing errors."""
    routes = [
        "/",
        "/analyze",
        "/results",
        "/skill-gap",
        "/model-performance",
        "/datasets"
    ]
    for r in routes:
        response = client.get(r, follow_redirects=True)
        assert response.status_code == 200, f"Route {r} failed with status {response.status_code}"
