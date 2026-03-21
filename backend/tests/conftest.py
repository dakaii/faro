"""Pytest fixtures for Faro backend."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def disable_auth_and_rate_limiting():
    """Disable authentication and rate limiting for tests."""
    # Store original values
    original_auth = settings.auth_enabled
    # Disable auth for most tests
    settings.auth_enabled = False
    
    # Mock rate limiting to always pass
    from app.middleware.rate_limit import rate_limiter
    import app.middleware.rate_limit as rl
    
    # Store original method
    original_is_allowed = rate_limiter.is_allowed
    # Replace with always-true method
    rate_limiter.is_allowed = lambda *args, **kwargs: True
    
    yield
    
    # Restore original values
    settings.auth_enabled = original_auth
    rate_limiter.is_allowed = original_is_allowed


@pytest.fixture
def client() -> TestClient:
    """HTTP client for testing API endpoints."""
    return TestClient(app)


@pytest.fixture
def authenticated_client() -> TestClient:
    """HTTP client with authentication headers."""
    client = TestClient(app)
    
    # Temporarily enable auth for this test
    original_auth = settings.auth_enabled
    settings.auth_enabled = True
    
    try:
        # Get authentication token with development password
        response = client.post("/auth/login", json={
            "username": "admin",
            "password": "dev-password"
        })
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
    finally:
        # Restore auth setting
        settings.auth_enabled = original_auth
    
    return client


@pytest.fixture
def api_key_client() -> TestClient:
    """HTTP client with API key authentication."""
    client = TestClient(app)
    client.headers.update({"X-API-Key": "your-api-key-for-service-access"})
    return client


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
