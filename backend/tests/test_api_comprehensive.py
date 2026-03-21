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
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = [
                tx_etherscan(
                    from_addr="0x1234567890123456789012345678901234567890",
                    to_addr="0x9876543210987654321098765432109876543210",
                    value="1000000000000000000",
                    time_stamp="1704067200"
                )
            ]
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert "address" in data
            assert "chain_id" in data
            assert "transactions_analyzed" in data
            assert "risk_score" in data
            assert "risk_factors" in data
            assert "story" in data

    def test_investigate_empty_transaction_list(self, client: TestClient):
        """Test investigation with no transactions found."""
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = []
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert data["transactions_analyzed"] == 0
            assert isinstance(data["risk_score"], (int, float))

    def test_investigate_etherscan_api_failure(self, client: TestClient):
        """Test investigation when Etherscan API fails."""
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            response = client.post("/api/investigate", json=investigate_request())
            # Should handle gracefully, either with default response or error
            assert response.status_code in [200, 503, 500]

    def test_investigate_different_chain_ids(self, client: TestClient):
        """Test investigation across different chain IDs."""
        chain_ids = [1, 137, 56, 10, 42161]  # Mainnet, Polygon, BSC, Optimism, Arbitrum
        
        for chain_id in chain_ids:
            with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
                mock_fetch.return_value = [tx_etherscan()]
                
                response = client.post("/api/investigate", json=investigate_request(chain_id=chain_id))
                assert response.status_code == 200
                
                data = response.json()
                assert data["chain_id"] == chain_id

    def test_investigate_with_llm_synthesis(self, client: TestClient):
        """Test investigation with LLM synthesis enabled."""
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch, \
             patch('app.services.llm_synthesis.synthesize_risk') as mock_llm:
            
            mock_fetch.return_value = [tx_etherscan()]
            mock_llm.return_value = (85, ["High transaction volume", "Unusual patterns"])
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert data["risk_score"] == 85
            assert len(data["risk_factors"]) >= 2

    def test_investigate_with_graph_context(self, client: TestClient):
        """Test investigation with graph context from Neo4j."""
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch, \
             patch('app.services.neo4j_client.find_shortest_path_to_tagged') as mock_neo4j:
            
            mock_fetch.return_value = [tx_etherscan()]
            mock_neo4j.return_value = [
                {"address": "0xtagged123", "tag": "Blacklisted", "distance": 2}
            ]
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            assert "graph_context" in data
            assert len(data["graph_context"]) > 0


class TestTagAddressAPI:
    """Comprehensive tests for /api/tag-address endpoint."""

    def test_tag_address_success(self, client: TestClient):
        """Test successful address tagging."""
        response = client.post("/api/tag-address", json=tag_request())
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "address" in data
        assert "tag" in data

    def test_tag_address_different_tags(self, client: TestClient):
        """Test tagging with different tag types."""
        tags = ["Blacklisted", "Exchange", "DeFi Protocol", "Scammer", "Whale"]
        
        for tag in tags:
            response = client.post("/api/tag-address", json=tag_request(tag=tag))
            assert response.status_code == 200
            
            data = response.json()
            assert data["tag"] == tag

    def test_tag_address_overwrite_existing(self, client: TestClient):
        """Test overwriting an existing tag."""
        address = "0x1234567890123456789012345678901234567890"
        
        # Tag first time
        response1 = client.post("/api/tag-address", json=tag_request(address=address, tag="Exchange"))
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
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_texts') as mock_embed:
            
            mock_extract.return_value = "This is extracted text from PDF about cryptocurrency regulations."
            mock_embed.return_value = [[0.1] * 1536]  # Mock embedding
            
            pdf_content = b"%PDF-1.4\nFake PDF content for testing"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("test.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
            assert "chunks_created" in data
            assert data["chunks_created"] > 0

    def test_ingest_doc_empty_pdf(self, client: TestClient):
        """Test ingestion of PDF with no extractable text."""
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = ""
            
            pdf_content = b"%PDF-1.4\nEmpty PDF"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("empty.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code == 400
            assert "No text could be extracted" in response.json()["detail"]

    def test_ingest_doc_large_pdf(self, client: TestClient):
        """Test ingestion of large PDF file."""
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_texts') as mock_embed:
            
            # Simulate large extracted text
            large_text = "Large document content. " * 10000  # ~250KB of text
            mock_extract.return_value = large_text
            mock_embed.return_value = [[0.1] * 1536] * 100  # Many embeddings
            
            pdf_content = b"%PDF-1.4\n" + b"Large PDF content" * 1000
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("large.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code in [200, 413]  # Success or payload too large

    def test_ingest_doc_pdf_extraction_failure(self, client: TestClient):
        """Test ingestion when PDF extraction fails."""
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract:
            mock_extract.side_effect = Exception("PDF parsing error")
            
            pdf_content = b"%PDF-1.4\nCorrupted PDF"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("corrupted.pdf", pdf_content, "application/pdf")}
            )
            assert response.status_code == 500

    def test_ingest_doc_embedding_failure(self, client: TestClient):
        """Test ingestion when embedding generation fails."""
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_texts') as mock_embed:
            
            mock_extract.return_value = "Valid extracted text"
            mock_embed.return_value = None  # Embedding failure
            
            pdf_content = b"%PDF-1.4\nValid PDF content"
            
            response = client.post(
                "/api/ingest-doc",
                files={"file": ("test.pdf", pdf_content, "application/pdf")}
            )
            # Should handle gracefully, possibly storing without embeddings
            assert response.status_code in [200, 500]


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
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = [tx_etherscan(from_addr=address)]
            
            investigate_response = client.post(
                "/api/investigate", 
                json={"address": address, "chain_id": 1}
            )
            assert investigate_response.status_code == 200

    def test_ingest_then_investigate_with_rag(self, client: TestClient):
        """Test ingesting a document then investigating with RAG context."""
        # First ingest a document
        with patch('app.services.rag_ingest.extract_text_from_pdf') as mock_extract, \
             patch('app.services.embeddings.embed_texts') as mock_embed:
            
            mock_extract.return_value = "Regulatory document about suspicious wallet 0x1234567890123456789012345678901234567890"
            mock_embed.return_value = [[0.1] * 1536]
            
            pdf_content = b"%PDF-1.4\nRegulatory document"
            ingest_response = client.post(
                "/api/ingest-doc",
                files={"file": ("regulations.pdf", pdf_content, "application/pdf")}
            )
            assert ingest_response.status_code == 200
        
        # Then investigate an address that might have RAG context
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = [tx_etherscan()]
            
            investigate_response = client.post(
                "/api/investigate",
                json={"address": "0x1234567890123456789012345678901234567890", "chain_id": 1}
            )
            assert investigate_response.status_code == 200

    def test_api_response_consistency(self, client: TestClient):
        """Test that API responses have consistent structure."""
        # Test investigate response structure
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = [tx_etherscan()]
            
            response = client.post("/api/investigate", json=investigate_request())
            assert response.status_code == 200
            
            data = response.json()
            required_fields = ["address", "chain_id", "transactions_analyzed", "risk_score", "risk_factors", "story"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
        
        # Test tag response structure
        response = client.post("/api/tag-address", json=tag_request())
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert isinstance(data["success"], bool)


class TestAPIPerformance:
    """Basic performance tests for API endpoints."""

    def test_investigate_response_time(self, client: TestClient):
        """Test that investigate endpoint responds in reasonable time."""
        import time
        
        with patch('app.services.etherscan.fetch_account_txs') as mock_fetch:
            mock_fetch.return_value = [tx_etherscan()]
            
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