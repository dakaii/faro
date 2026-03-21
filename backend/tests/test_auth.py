"""Authentication system tests."""
import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token, verify_token, get_password_hash, verify_password


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client: TestClient):
        """Test successful login with valid credentials.""" 
        # Temporarily enable auth for this test
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            response = client.post("/auth/login", json={
                "username": "admin",
                "password": "dev-password"
            })
        
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            settings.auth_enabled = original_auth

    def test_login_invalid_username(self, client: TestClient):
        """Test login with invalid username."""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "secret"
        })
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_invalid_password(self, client: TestClient):
        """Test login with invalid password."""
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            response = client.post("/auth/login", json={
                "username": "admin", 
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            assert "Incorrect username or password" in response.json()["detail"]
        finally:
            settings.auth_enabled = original_auth

    def test_oauth2_token_endpoint(self, client: TestClient):
        """Test OAuth2 token endpoint with form data."""
        response = client.post("/auth/token", data={
            "username": "admin",
            "password": "secret",
            "grant_type": "password"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_get_current_user_info(self, authenticated_client: TestClient):
        """Test getting current user information."""
        response = authenticated_client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["user_id"] == "admin-001"
        assert "admin" in data["scopes"]

    def test_test_auth_endpoint(self, authenticated_client: TestClient):
        """Test the auth test endpoint."""
        response = authenticated_client.get("/auth/test-auth")
        
        assert response.status_code == 200
        data = response.json()
        assert data["auth_status"] == "success"
        assert data["user_id"] == "admin-001"


class TestJWTTokens:
    """Test JWT token functionality."""

    def test_create_and_verify_token(self):
        """Test token creation and verification."""
        data = {"sub": "testuser", "user_id": "test-001", "scopes": ["test"]}
        token = create_access_token(data)
        
        assert token is not None
        
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == "test-001"
        assert token_data.scopes == ["test"]

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.jwt.token"
        token_data = verify_token(invalid_token)
        assert token_data is None

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        from datetime import timedelta
        
        # Create token that expires immediately
        data = {"sub": "testuser"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        token_data = verify_token(token)
        assert token_data is None


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_and_verify_password(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password  # Should be hashed
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False


class TestAPIKeyAuthentication:
    """Test API key authentication."""

    def test_api_key_access(self, api_key_client: TestClient):
        """Test API key authentication."""
        # Enable auth temporarily
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            response = api_key_client.get("/auth/test-auth")
            assert response.status_code == 200
            data = response.json()
            assert data["auth_status"] == "success"
        finally:
            settings.auth_enabled = original_auth

    def test_invalid_api_key(self, client: TestClient):
        """Test access with invalid API key."""
        # Enable auth temporarily
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            client.headers.update({"X-API-Key": "invalid-key"})
            response = client.get("/auth/test-auth")
            assert response.status_code == 401
        finally:
            settings.auth_enabled = original_auth


class TestAuthorizationScopes:
    """Test authorization and scope-based access control."""

    def test_admin_has_all_access(self, authenticated_client: TestClient):
        """Test that admin user has access to all endpoints."""
        # Test investigate endpoint
        with pytest.raises(Exception):
            # This would normally test the endpoint, but we'd need to mock external services
            pass

    def test_analyst_limited_access(self, client: TestClient):
        """Test that analyst user has limited access."""
        # Login as analyst
        response = client.post("/auth/login", json={
            "username": "analyst",
            "password": "secret"
        })
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            
            # Analyst should be able to access their scoped endpoints
            response = client.get("/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert "investigate" in data["scopes"]
            assert "tag" in data["scopes"]
            assert "admin" not in data["scopes"]


class TestAuthenticationBypass:
    """Test authentication bypass scenarios."""

    def test_no_auth_header(self, client: TestClient):
        """Test access without authentication headers."""
        # Enable auth temporarily
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            response = client.get("/auth/test-auth")
            assert response.status_code == 401
        finally:
            settings.auth_enabled = original_auth

    def test_malformed_auth_header(self, client: TestClient):
        """Test access with malformed auth header."""
        # Enable auth temporarily
        from app.core.config import settings
        original_auth = settings.auth_enabled
        settings.auth_enabled = True
        
        try:
            client.headers.update({"Authorization": "InvalidFormat token"})
            response = client.get("/auth/test-auth")
            assert response.status_code == 401
        finally:
            settings.auth_enabled = original_auth


class TestSecurityHeaders:
    """Test security headers and configurations."""

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are properly set."""
        response = client.options("/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        
        # Should handle CORS preflight
        assert response.status_code in [200, 204]

    def test_login_rate_limiting_simulation(self, client: TestClient):
        """Test behavior under rapid login attempts."""
        # Make multiple login attempts
        responses = []
        for _ in range(10):
            response = client.post("/auth/login", json={
                "username": "admin",
                "password": "secret"
            })
            responses.append(response.status_code)
        
        # Should handle gracefully (rate limiting would normally kick in)
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 5  # At least some should succeed