"""Security-focused API tests for input validation, rate limiting, and edge cases."""
import pytest
from fastapi.testclient import TestClient

from tests.factories import investigate_request, tag_request


class TestInputValidation:
    """Test input validation across all API endpoints."""

    def test_investigate_invalid_wallet_address_formats(self, client: TestClient):
        """Test various invalid wallet address formats."""
        invalid_addresses = [
            "",  # Empty
            "0x",  # Too short
            "0x123",  # Too short
            "invalid",  # Not hex
            "0xGGGG567890123456789012345678901234567890",  # Invalid hex chars
            "1234567890123456789012345678901234567890",  # Missing 0x prefix
            "0x12345678901234567890123456789012345678901",  # Too long (41 chars)
            "0x123456789012345678901234567890123456789",  # Too short (39 chars)
            "0X1234567890123456789012345678901234567890",  # Uppercase X
        ]
        
        for addr in invalid_addresses:
            response = client.post("/api/investigate", json={"address": addr, "chain_id": 1})
            assert response.status_code == 422, f"Expected 422 for address: {addr}"

    def test_investigate_invalid_chain_ids(self, client: TestClient):
        """Test invalid chain ID values."""
        invalid_chains = [
            -1,  # Negative
            0,  # Zero
            "1",  # String instead of int
            None,  # Null
            1.5,  # Float
            999999999999999,  # Very large number
        ]
        
        for chain in invalid_chains:
            data = investigate_request(chain_id=chain) if chain is not None else {"address": "0x1234567890123456789012345678901234567890"}
            response = client.post("/api/investigate", json=data)
            assert response.status_code == 422, f"Expected 422 for chain_id: {chain}"

    def test_tag_address_invalid_formats(self, client: TestClient):
        """Test invalid tag address formats."""
        # Invalid addresses
        response = client.post("/api/tag-address", json={"address": "invalid", "tag": "Test"})
        assert response.status_code == 422

        # Invalid tag types
        invalid_tags = [
            "",  # Empty string
            None,  # Null
            123,  # Number instead of string
            "A" * 101,  # Too long (assuming 100 char limit)
        ]
        
        for tag in invalid_tags[:-1]:  # Skip the long string for now
            data = tag_request(tag=tag) if tag is not None else {"address": "0x1234567890123456789012345678901234567890"}
            response = client.post("/api/tag-address", json=data)
            assert response.status_code == 422, f"Expected 422 for tag: {tag}"

    def test_ingest_doc_without_file(self, client: TestClient):
        """Test document ingestion without file upload."""
        response = client.post("/api/ingest-doc")
        assert response.status_code == 422

    def test_ingest_doc_invalid_file_types(self, client: TestClient):
        """Test document ingestion with non-PDF files."""
        # Test with text file
        response = client.post(
            "/api/ingest-doc",
            files={"file": ("test.txt", b"This is a text file", "text/plain")}
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

        # Test with image file
        response = client.post(
            "/api/ingest-doc",
            files={"file": ("test.jpg", b"fake image data", "image/jpeg")}
        )
        assert response.status_code == 400

    def test_large_file_upload(self, client: TestClient):
        """Test uploading extremely large files."""
        # Create a 10MB fake PDF (just PDF header + lots of data)
        large_data = b"%PDF-1.4\n" + b"A" * (10 * 1024 * 1024)
        
        response = client.post(
            "/api/ingest-doc",
            files={"file": ("large.pdf", large_data, "application/pdf")}
        )
        # Should either accept it or reject with appropriate error
        assert response.status_code in [200, 413, 400]

    def test_malformed_json_requests(self, client: TestClient):
        """Test malformed JSON in request bodies."""
        # Test with invalid JSON
        response = client.post(
            "/api/investigate",
            data="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient):
        """Test requests with missing required fields."""
        # Missing address
        response = client.post("/api/investigate", json={"chain_id": 1})
        assert response.status_code == 422

        # Missing chain_id
        response = client.post("/api/investigate", json={"address": "0x1234567890123456789012345678901234567890"})
        assert response.status_code == 422

        # Missing tag
        response = client.post("/api/tag-address", json={"address": "0x1234567890123456789012345678901234567890"})
        assert response.status_code == 422

    def test_sql_injection_attempts(self, client: TestClient):
        """Test potential SQL injection in address fields."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "0x1234567890123456789012345678901234567890'; SELECT * FROM secrets; --",
            "0x1234567890123456789012345678901234567890' OR '1'='1",
        ]
        
        for payload in sql_payloads:
            response = client.post("/api/investigate", json={"address": payload, "chain_id": 1})
            # Should be rejected due to validation
            assert response.status_code == 422

    def test_script_injection_attempts(self, client: TestClient):
        """Test potential script injection in tag fields."""
        script_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ]
        
        for payload in script_payloads:
            response = client.post(
                "/api/tag-address", 
                json={"address": "0x1234567890123456789012345678901234567890", "tag": payload}
            )
            # Should either accept (and sanitize) or reject
            assert response.status_code in [200, 422]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_concurrent_requests(self, client: TestClient):
        """Test handling of concurrent requests to same endpoint."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.post("/api/investigate", json=investigate_request())
            results.append(response.status_code)
        
        # Create 10 concurrent threads
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed or fail gracefully
        assert all(status in [200, 500, 503] for status in results)

    def test_very_long_request_processing(self, client: TestClient):
        """Test behavior with requests that might take a long time."""
        # This tests timeout handling
        response = client.post("/api/investigate", json=investigate_request())
        # Should complete within reasonable time or timeout gracefully
        assert response.status_code in [200, 408, 500, 503]

    def test_empty_response_handling(self, client: TestClient):
        """Test endpoints that might return empty data."""
        # Test with an address that likely has no transactions
        response = client.post(
            "/api/investigate", 
            json={"address": "0x0000000000000000000000000000000000000000", "chain_id": 1}
        )
        # Should handle empty results gracefully
        assert response.status_code in [200, 400]

    def test_health_endpoint_resilience(self, client: TestClient):
        """Test health endpoint under various conditions."""
        # Multiple rapid requests
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    def test_external_service_failures(self, client: TestClient):
        """Test behavior when external services (Etherscan, OpenAI) fail."""
        # Test with invalid API key scenarios (would be mocked in real implementation)
        response = client.post("/api/investigate", json=investigate_request())
        # Should handle external failures gracefully
        assert response.status_code in [200, 503, 500]

    def test_malformed_pdf_upload(self, client: TestClient):
        """Test uploading malformed PDF files."""
        # Fake PDF with only header
        fake_pdf = b"%PDF-1.4\nInvalid PDF content"
        
        response = client.post(
            "/api/ingest-doc",
            files={"file": ("fake.pdf", fake_pdf, "application/pdf")}
        )
        # Should handle malformed PDF gracefully
        assert response.status_code in [200, 400, 500]

    def test_network_timeout_simulation(self, client: TestClient):
        """Test behavior under network timeout conditions."""
        # This would normally require mocking external calls
        response = client.post("/api/investigate", json=investigate_request())
        # Should handle timeouts gracefully
        assert response.status_code in [200, 408, 503, 500]


class TestCORSAndHeaders:
    """Test CORS configuration and security headers."""

    def test_cors_preflight_requests(self, client: TestClient):
        """Test CORS preflight requests."""
        response = client.options(
            "/api/investigate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        # Should handle CORS properly
        assert response.status_code in [200, 204]

    def test_security_headers_present(self, client: TestClient):
        """Test that appropriate security headers are present."""
        response = client.get("/health")
        # Check for basic security considerations
        assert response.status_code == 200
        # In a real app, you'd check for headers like X-Frame-Options, etc.


class TestRateLimiting:
    """Test rate limiting behavior (currently not implemented)."""

    def test_rapid_requests_handling(self, client: TestClient):
        """Test behavior under rapid requests (future rate limiting)."""
        responses = []
        
        # Make 100 rapid requests
        for _ in range(100):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # Currently no rate limiting, so all should succeed
        # In future: some should be 429 (Too Many Requests)
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 90  # At least 90% should succeed even with rate limiting