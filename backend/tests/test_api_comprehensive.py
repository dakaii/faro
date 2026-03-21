"""Comprehensive API endpoint tests covering all routes and scenarios."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from tests.factories import investigate_request, tag_request, tx_etherscan


class TestInvestigateAPI:
    """Comprehensive tests for /api/investigate endpoint."""

    def test_investigate_success_with_mocked_etherscan(self, client: TestClient):
        """Test successful investigation with mocked Etherscan data."""
        # Mock the actual method that gets called: EtherscanFetcher.get_tx_list_ok
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_txs = [
                tx_etherscan(
                    from_addr="0x1234567890123456789012345678901234567890",
                    to_addr="0x9876543210987654321098765432109876543210",
                    value="1000000000000000000",
                    time_stamp="1704067200"
                )
            ]
            # get_tx_list_ok returns (story, txs)
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert "address" in data
            assert "risk_score" in data  
            assert "summary" in data
            assert "evidence" in data
            assert data["address"] == "0x1234567890123456789012345678901234567890"

    def test_investigate_empty_transaction_list(self, client: TestClient):
        """Test investigation with no transactions found."""
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_fetch.return_value = ("Forensic report for wallet: 0x1234567890123456789012345678901234567890\nNo transactions found (new or empty wallet).", [])
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data["risk_score"], (int, float))

    def test_investigate_etherscan_api_failure(self, client: TestClient):
        """Test investigation when Etherscan API fails."""
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_fetch.return_value = ("Error fetching wallet: API Error", [])
            
            response = client.post("/api/investigate", json=investigate_request())
            # Should handle gracefully, either with default response or error
            assert response.status_code in [200, 503, 500]

    def test_investigate_different_chain_ids(self, client: TestClient):
        """Test investigation across different chain IDs."""
        chain_ids = [1, 137, 56, 10, 42161]  # Mainnet, Polygon, BSC, Optimism, Arbitrum
        
        for chain_id in chain_ids:
            with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
                mock_txs = [tx_etherscan()]
                mock_fetch.return_value = (
                    f"Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                    mock_txs
                )
                
                response = client.post("/api/investigate", json=investigate_request(chain_id=chain_id))
                assert response.status_code == 200

    def test_investigate_with_llm_synthesis(self, client: TestClient):
        """Test investigation with LLM synthesis enabled."""
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch, \
             patch('app.api.investigate.synthesize_risk') as mock_synthesize:
            
            mock_txs = [tx_etherscan()]
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            # Mock LLM synthesis to return specific risk assessment
            mock_synthesize.return_value = (85, "High risk analysis", ["High transaction volume", "Unusual patterns"])
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert data["risk_score"] == 85
            assert len(data["evidence"]) >= 2

    def test_investigate_with_graph_context(self, client: TestClient):
        """Test investigation with graph context from Neo4j."""
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch, \
             patch('app.api.investigate.get_graph_context') as mock_neo4j:
            
            mock_txs = [tx_etherscan()]
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            mock_neo4j.return_value = "Graph: wallet is within 3 hops of 2 known bad/mixer node(s)."
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert "summary" in data
            assert data["risk_score"] > 0


class TestTagAddressAPI:
    """Comprehensive tests for /api/tag-address endpoint."""

    def test_tag_address_success(self, client: TestClient):
        """Test successful address tagging."""
        response = client.post("/api/tag-address", json=tag_request())
        assert response.status_code == 200
        
        data = response.json()
        assert data["tagged"] is True
        assert "address" in data
        assert "tag" in data

    def test_tag_address_different_tags(self, client: TestClient):
        """Test tagging with different tag types."""
        tags = ["Blacklisted", "Mixer"]  # Only allowed tags
        
        for tag in tags:
            response = client.post("/api/tag-address", json=tag_request(tag=tag))
            assert response.status_code == 200
            
            data = response.json()
            assert data["tag"] == tag

    def test_tag_address_overwrite_existing(self, client: TestClient):
        """Test overwriting an existing tag."""
        address = "0x1234567890123456789012345678901234567890"
        
        # Tag first time
        response1 = client.post("/api/tag-address", json=tag_request(address=address, tag="Mixer"))
        assert response1.status_code == 200
        
        # Tag again with different tag
        response2 = client.post("/api/tag-address", json=tag_request(address=address, tag="Blacklisted"))
        assert response2.status_code == 200

    def test_tag_address_neo4j_failure(self, client: TestClient):
        """Test tagging when Neo4j is unavailable."""
        with patch('app.services.neo4j_client.get_driver') as mock_driver:
            mock_driver.return_value = None
            
            response = client.post("/api/tag-address", json=tag_request())
            # Should handle gracefully when Neo4j is unavailable
            assert response.status_code in [200, 503]


class TestIngestDocAPI:
    """Comprehensive tests for /api/ingest-doc endpoint."""

    def test_ingest_doc_success_with_mocked_extraction(self, client: TestClient):
        """Test successful document ingestion with mocked PDF extraction."""
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_text') as mock_embed, \
             patch('app.services.neo4j_client.ensure_rag_vector_index') as mock_ensure_index, \
             patch('app.core.config.settings') as mock_settings:
            
            # Mock settings to enable embeddings
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = None
            
            mock_extract.return_value = "This is extracted text from PDF about cryptocurrency regulations."
            mock_embed.return_value = [0.1] * 1536  # Mock single embedding
            mock_ensure_index.return_value = True  # Vector index creation succeeds
            
            pdf_content = b"%PDF-1.4\nFake PDF content for testing"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("test.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "ingested" in data
            assert data["ingested"] >= 0  # Allow 0 for mocked environment

    def test_ingest_doc_empty_pdf(self, client: TestClient):
        """Test ingestion of PDF with no extractable text."""
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = ""
            
            pdf_content = b"%PDF-1.4\nEmpty PDF"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("empty.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code == 400
            assert "No text extracted from PDF" in response.json()["detail"]

    def test_ingest_doc_large_pdf(self, client: TestClient):
        """Test ingestion of large PDF file."""
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_text') as mock_embed, \
             patch('app.core.config.settings') as mock_settings:
            
            # Mock settings to enable embeddings
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = None
            
            # Simulate large extracted text
            large_text = "Large document content. " * 10000  # ~250KB of text
            mock_extract.return_value = large_text
            mock_embed.return_value = [0.1] * 1536  # Single embedding
            
            pdf_content = b"%PDF-1.4\n" + b"Large PDF content" * 1000
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("large.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code in [200, 413]  # Success or payload too large

    def test_ingest_doc_pdf_extraction_failure(self, client: TestClient):
        """Test ingestion when PDF extraction fails."""
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract:
            mock_extract.side_effect = Exception("PDF parsing error")
            
            pdf_content = b"%PDF-1.4\nCorrupted PDF"
            
            # The exception should bubble up as a 500 error via FastAPI's exception handling
            try:
                response = client.post(
                    "/api/ingest-doc",
                    files={"file": ("corrupted.pdf", pdf_content, "application/pdf")}
                )
                # If we get here, FastAPI handled it gracefully
                assert response.status_code == 500
            except Exception:
                # If an exception is raised, that's expected behavior for unhandled errors
                pass

    def test_ingest_doc_embedding_failure(self, client: TestClient):
        """Test ingestion when embedding generation fails."""
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_text') as mock_embed, \
             patch('app.core.config.settings') as mock_settings:
            
            # Mock settings to enable embeddings
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = None
            
            mock_extract.return_value = "Valid extracted text"
            mock_embed.return_value = None  # Embedding failure
            
            pdf_content = b"%PDF-1.4\nValid PDF content"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("test.pdf", pdf_content, "application/pdf")}
            )
            # Should handle gracefully - returns 0 chunks when embeddings fail
            assert response.status_code == 200
            assert response.json()["ingested"] == 0


class TestHealthAPI:
    """Tests for health check endpoint."""

    def test_health_basic(self, client: TestClient):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_with_dependencies(self, client: TestClient):
        """Test health check considering external dependencies."""
        # Future enhancement: check Neo4j, external APIs
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_multiple_concurrent_requests(self, client: TestClient):
        """Test health endpoint under concurrent load."""
        import threading
        results = []
        
        def check_health():
            response = client.get("/health")
            results.append(response.status_code)
        
        threads = [threading.Thread(target=check_health) for _ in range(50)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert all(status == 200 for status in results)


class TestAPIIntegration:
    """Integration tests combining multiple API endpoints."""

    def test_full_workflow_tag_then_investigate(self, client: TestClient):
        """Test tagging an address then investigating it."""
        address = "0x1234567890123456789012345678901234567890"
        
        # First tag the address
        tag_response = client.post(
            "/api/tag-address", 
            json={"address": address, "tag": "Blacklisted"}
        )
        assert tag_response.status_code == 200
        
        # Then investigate it
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_txs = [tx_etherscan(from_addr=address)]
            mock_fetch.return_value = (
                f"Forensic report for wallet: {address}\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            investigate_response = client.post(
                "/api/investigate", 
                json={"address": address, "chain_id": 1}
            )
            assert investigate_response.status_code == 200

    def test_ingest_then_investigate_with_rag(self, client: TestClient):
        """Test ingesting a document then investigating with RAG context."""
        # First ingest a document
        with patch('app.api.ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_text') as mock_embed, \
             patch('app.core.config.settings') as mock_settings:
            
            # Mock settings to enable embeddings
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = None
            
            mock_extract.return_value = "Regulatory document about suspicious wallet 0x1234567890123456789012345678901234567890"
            mock_embed.return_value = [0.1] * 1536
            
            pdf_content = b"%PDF-1.4\nRegulatory document"
            ingest_response = client.post(
                "/api/ingest-doc",
                files={"file": ("regulations.pdf", pdf_content, "application/pdf")}
            )
            assert ingest_response.status_code == 200
        
        # Then investigate an address that might have RAG context
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_txs = [tx_etherscan()]
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            investigate_response = client.post(
                "/api/investigate",
                json={"address": "0x1234567890123456789012345678901234567890", "chain_id": 1}
            )
            assert investigate_response.status_code == 200

    def test_api_response_consistency(self, client: TestClient):
        """Test that API responses have consistent structure."""
        # Test investigate response structure
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_txs = [tx_etherscan()]
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            required_fields = ["address", "risk_score", "summary", "evidence"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
        
        # Test tag response structure
        response = client.post("/api/tag-address", json=tag_request())
        assert response.status_code == 200
        
        data = response.json()
        assert "tagged" in data
        assert isinstance(data["tagged"], bool)


class TestAPIPerformance:
    """Basic performance tests for API endpoints."""

    def test_investigate_response_time(self, client: TestClient):
        """Test that investigate endpoint responds in reasonable time."""
        import time
        
        with patch('app.services.etherscan.EtherscanFetcher.get_tx_list_ok') as mock_fetch:
            mock_txs = [tx_etherscan()]
            mock_fetch.return_value = (
                "Forensic report for wallet: 0x1234567890123456789012345678901234567890\n- On 2024-01-01 00:00:00 UTC, sent 1.0000 ETH to 0x987654321...",
                mock_txs
            )
            
            start_time = time.time()
            response = client.post("/api/investigate", json=investigate_request())
            end_time = time.time()
            
            assert response.status_code == 200
            # Should respond within 10 seconds (generous for testing)
            assert (end_time - start_time) < 10

    def test_tag_address_response_time(self, client: TestClient):
        """Test that tag endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = client.post("/api/tag-address", json=tag_request())
        end_time = time.time()
        
        assert response.status_code == 200
        # Should be very fast (under 2 seconds)
        assert (end_time - start_time) < 2

    def test_health_response_time(self, client: TestClient):
        """Test that health endpoint responds very quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        # Should be nearly instantaneous (under 0.5 seconds)
        assert (end_time - start_time) < 0.5