"""Unit tests for embeddings service."""
from unittest.mock import MagicMock, patch

from app.services.embeddings import embed_text, embed_texts


def test_embed_text_empty_returns_none():
    assert embed_text("") is None
    assert embed_text("   ") is None


def test_embed_text_no_api_key_returns_none():
    with patch("app.services.embeddings.settings") as s:
        s.openai_api_key = ""
        s.openai_base_url = ""
        s.openai_embedding_model = "text-embedding-3-small"
        s.openai_embedding_dimensions = 1536
        assert embed_text("hello") is None


def test_embed_text_success_returns_embedding():
    fake_embedding = [0.1] * 10
    with (
        patch("app.services.embeddings.settings") as s,
        patch("app.services.embeddings._embed_client") as mock_client_fn,
    ):
        s.openai_api_key = "sk-test"
        s.openai_base_url = ""
        s.openai_embedding_model = "text-embedding-3-small"
        s.openai_embedding_dimensions = 1536
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=fake_embedding)]
        )
        mock_client_fn.return_value = mock_client
        result = embed_text("hello")
    assert result == fake_embedding


def test_embed_texts_delegates():
    with (
        patch("app.services.embeddings.settings") as s,
        patch("app.services.embeddings._embed_client") as mock_client_fn,
    ):
        s.openai_api_key = "sk-test"
        s.openai_base_url = ""
        s.openai_embedding_model = "text-embedding-3-small"
        s.openai_embedding_dimensions = 1536
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2])]
        )
        mock_client_fn.return_value = mock_client
        results = embed_texts(["a", "b"])
    assert len(results) == 2
    assert results[0] == [0.1, 0.2]
    assert results[1] == [0.1, 0.2]
