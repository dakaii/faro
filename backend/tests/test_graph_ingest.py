"""Unit tests for graph ingest (tx normalization)."""
import pytest

from app.services.graph_ingest import _normalize_tx_for_ingest

from tests.factories import tx_etherscan


def test_normalize_valid():
    row = _normalize_tx_for_ingest(
        tx_etherscan(tx_hash="0xhash", value="1000000"),
        chain_id=1,
    )
    assert row is not None
    assert row["from_address"] == tx_etherscan()["from"]
    assert row["to_address"] == tx_etherscan()["to"]
    assert row["tx_hash"] == "0xhash"
    assert row["value_wei"] == 1000000
    assert row["timestamp"] == 1704067200
    assert row["chain_id"] == 1


def test_normalize_contract_creation():
    row = _normalize_tx_for_ingest(
        tx_etherscan(from_addr="0xabc" + "0" * 36, to_addr="", tx_hash="0xh1", value="0", time_stamp="0"),
        chain_id=1,
    )
    assert row is not None
    assert row["to_address"] == "0x0"


def test_normalize_invalid_from():
    assert _normalize_tx_for_ingest(tx_etherscan(from_addr="", to_addr="0xto"), 1) is None
    assert _normalize_tx_for_ingest(tx_etherscan(from_addr="not0x", to_addr="0xto"), 1) is None


def test_normalize_missing_hash():
    assert _normalize_tx_for_ingest(tx_etherscan(from_addr="0xabc", to_addr="0xto", tx_hash=""), 1) is None
