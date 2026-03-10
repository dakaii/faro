"""Unit tests for Etherscan service."""
import pytest

from app.services.etherscan import format_timestamp, wallet_story_from_txs

from tests.factories import tx_etherscan


def test_format_timestamp_valid():
    assert "1970" in format_timestamp("0")
    assert "2024" in format_timestamp("1704067200")  # 2024-01-01 00:00:00 UTC


def test_format_timestamp_invalid():
    assert format_timestamp("") == ""
    assert format_timestamp("not-a-number") == "not-a-number"


def test_wallet_story_from_txs_empty():
    out = wallet_story_from_txs("0xabc", [])
    assert "0xabc" in out
    assert "No transactions found" in out


def test_wallet_story_from_txs_one():
    txs = [
        tx_etherscan(
            from_addr="0xfrom",
            to_addr="0xto123456789012",
            value="1000000000000000000",
            time_stamp="1704067200",
            tx_hash="0xhash123",
        )
    ]
    out = wallet_story_from_txs("0xfrom", txs)
    assert "Forensic report for wallet: 0xfrom" in out
    assert "1.0000" in out
    assert "0xto1234567" in out
    assert "0xhash12" in out


def test_wallet_story_from_txs_contract_creation():
    txs = [tx_etherscan(from_addr="0xa", to_addr="", value="0", time_stamp="0", tx_hash="0xh")]
    out = wallet_story_from_txs("0xa", txs)
    # to_addr is truncated to 14 chars so we get "contract creat..."
    assert "contract creat" in out
