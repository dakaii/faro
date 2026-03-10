"""Unit tests for LLM synthesis service."""
from unittest.mock import MagicMock, patch

from app.services.llm_synthesis import synthesize_risk


def test_synthesize_risk_no_api_key_returns_none():
    with patch("app.services.llm_synthesis.settings") as s:
        s.openai_api_key = ""
        s.openai_base_url = ""
        result = synthesize_risk("0xabc", "story", "graph", [])
    assert result is None


def test_synthesize_risk_success_returns_tuple():
    json_content = '{"risk_score": 42, "summary": "Medium risk.", "evidence": ["a", "b", "c"]}'
    with (
        patch("app.services.llm_synthesis.settings") as s,
        patch("app.services.llm_synthesis._llm_client") as mock_client_fn,
    ):
        s.openai_api_key = "sk-test"
        s.openai_base_url = ""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json_content))]
        )
        mock_client_fn.return_value = mock_client
        result = synthesize_risk("0xabc", "story", "graph", [])
    assert result is not None
    score, summary, evidence = result
    assert score == 42
    assert summary == "Medium risk."
    assert evidence == ["a", "b", "c"]
