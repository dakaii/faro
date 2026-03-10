"""Integration tests for investigate and tag endpoints."""
from unittest.mock import patch

import pytest

from tests.factories import DEFAULT_ADDRESS, investigate_request, tag_request


def test_investigate_invalid_address(client):
    resp = client.post("/api/investigate", json=investigate_request(address="not-valid"))
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


def test_investigate_short_address(client):
    resp = client.post("/api/investigate", json=investigate_request(address="0xabc"))
    assert resp.status_code == 400


def test_investigate_success_heuristic(client):
    wallet_story = f"Forensic report for wallet: {DEFAULT_ADDRESS}\nNo transactions found."
    with (
        patch("app.api.investigate.EtherscanFetcher") as mock_fetcher_cls,
        patch("app.api.investigate.ingest_wallet_transactions"),
        patch("app.api.investigate.get_graph_context", return_value="Graph: no path to known blacklisted or mixer nodes."),
        patch("app.api.investigate.get_rag_context", return_value=[]),
    ):
        mock_fetcher = mock_fetcher_cls.return_value
        mock_fetcher.get_tx_list_ok.return_value = (wallet_story, [])
        resp = client.post("/api/investigate", json=investigate_request())
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"] == DEFAULT_ADDRESS
    assert 0 <= data["risk_score"] <= 100
    assert "summary" in data
    assert "evidence" in data
    assert isinstance(data["evidence"], list)


def test_tag_address_invalid_address(client):
    resp = client.post("/api/tag-address", json=tag_request(address="not-valid"))
    assert resp.status_code == 400


def test_tag_address_invalid_tag(client):
    resp = client.post("/api/tag-address", json=tag_request(tag="Unknown"))
    assert resp.status_code == 400
    assert "Blacklisted" in resp.json()["detail"] and "Mixer" in resp.json()["detail"]


def test_tag_address_success(client):
    with patch("app.api.tags.tag_wallet", return_value=True):
        resp = client.post("/api/tag-address", json=tag_request(tag="Mixer"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["tagged"] is True
    assert data["tag"] == "Mixer"
    assert data["address"] == DEFAULT_ADDRESS
