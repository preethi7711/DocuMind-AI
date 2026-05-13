"""
Phase 1 — Foundation Tests
============================
WHY TESTS FROM DAY ONE?
    Writing tests after building the entire system is the #1 mistake
    junior engineers make. By the time you're "done," fixing tests is painful.

    Testing the foundation early gives you:
    1. Confidence that config loading works
    2. A safety net — if you break settings.py, this test fails immediately
    3. Documentation — tests describe expected behavior in code

HOW TO RUN:
    From the project root:
        pytest tests/ -v

WHAT WE'RE TESTING HERE:
    - Settings object loads without errors
    - Computed properties return correct types
    - Health check endpoint returns 200
    - Response follows our standard envelope structure
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config.settings import get_settings, Settings


# ─── Settings Tests ───────────────────────────────────────────────────────────

class TestSettings:
    """Tests for centralized configuration loading."""

    def test_settings_loads_successfully(self):
        """Settings should load from .env without raising exceptions."""
        s = get_settings()
        assert isinstance(s, Settings)

    def test_app_name_is_set(self):
        """App name should be loaded from .env."""
        s = get_settings()
        assert s.app_name  # Not empty string
        assert isinstance(s.app_name, str)

    def test_computed_paths_are_path_objects(self):
        """Computed path properties should return Path objects."""
        from pathlib import Path
        s = get_settings()
        assert isinstance(s.upload_path, Path)
        assert isinstance(s.processed_path, Path)
        assert isinstance(s.chromadb_path, Path)

    def test_max_upload_size_bytes_conversion(self):
        """max_upload_size_bytes should equal MB * 1024 * 1024."""
        s = get_settings()
        expected = s.max_upload_size_mb * 1024 * 1024
        assert s.max_upload_size_bytes == expected

    def test_cors_origins_returns_list(self):
        """CORS origins should be parsed into a list."""
        s = get_settings()
        assert isinstance(s.cors_origins_list, list)
        assert len(s.cors_origins_list) >= 1


# ─── Health Endpoint Tests ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """Tests for the /api/v1/health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should always return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_has_standard_envelope(self, client):
        """Response should follow our standard envelope structure."""
        response = client.get("/api/v1/health")
        body = response.json()
        assert "success" in body
        assert "message" in body
        assert "data" in body

    def test_health_success_is_true(self, client):
        """success field should be True for a healthy app."""
        response = client.get("/api/v1/health")
        assert response.json()["success"] is True

    def test_health_data_has_required_fields(self, client):
        """Health data should contain status, app_name, version, environment."""
        response = client.get("/api/v1/health")
        data = response.json()["data"]
        assert "status" in data
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data

    def test_health_status_is_valid_value(self, client):
        """Status should be one of: healthy, degraded, unhealthy."""
        response = client.get("/api/v1/health")
        status = response.json()["data"]["status"]
        assert status in {"healthy", "degraded", "unhealthy"}
