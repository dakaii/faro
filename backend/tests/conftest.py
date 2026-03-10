"""Pytest fixtures for Faro backend."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """HTTP client for testing API endpoints."""
    return TestClient(app)


@pytest.fixture
def neo4j_driver():
    """
    Neo4j driver for integration tests. Skips the test if Neo4j is not configured
    or not reachable (e.g. run `make up` first).
    """
    from app.services.neo4j_client import get_driver

    driver = get_driver(None)
    if not driver:
        pytest.skip("Neo4j not configured (set NEO4J_PASSWORD in backend/.env)")
    try:
        driver.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j not reachable (start with: make up)")
    yield driver
    driver.close()
