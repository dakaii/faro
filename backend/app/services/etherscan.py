"""
Etherscan V2 API client. Fetches transaction list and formats a "forensic story" for the LLM.
Docs: https://docs.etherscan.io/
"""
import time
from typing import Any

import httpx

from app.core.config import settings


def _wei_to_eth(wei: str) -> float:
    return int(wei) / 10**18


def format_timestamp(ts: str) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(int(ts)))
    except (ValueError, TypeError):
        return ts


class EtherscanFetcher:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.etherscan_api_key
        self.base_url = base_url or settings.etherscan_base_url

    def get_tx_list(
        self,
        address: str,
        chain_id: int = 1,
        page: int = 1,
        offset: int = 10,
        sort: str = "desc",
    ) -> dict[str, Any]:
        """Fetch normal transaction list for an address."""
        params = {
            "chainid": chain_id,
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": page,
            "offset": offset,
            "sort": sort,
            "apikey": self.api_key,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(self.base_url, params=params)
            return resp.json()

    def get_wallet_summary(
        self,
        address: str,
        chain_id: int = 1,
        max_txs: int = 10,
    ) -> str:
        """
        Fetch the last N transactions and format them into a 'forensic story' for the LLM.
        """
        data = self.get_tx_list(address, chain_id=chain_id, offset=max_txs)
        if data.get("status") != "1":
            msg = data.get("message", "Unknown error")
            return f"Error fetching wallet: {msg}"

        txs = data.get("result") or []
        if not txs:
            return f"Forensic report for wallet: {address}\nNo transactions found (new or empty wallet)."

        lines = [f"Forensic report for wallet: {address}\n"]
        for tx in txs:
            value_eth = _wei_to_eth(tx.get("value", "0"))
            to_addr = (tx.get("to") or "contract creation")[:14]
            date = format_timestamp(tx.get("timeStamp", "0"))
            tx_hash = (tx.get("hash") or "")[:10]
            lines.append(
                f"- On {date}, sent {value_eth:.4f} ETH to {to_addr}... (Hash: {tx_hash}...)\n"
            )
        return "".join(lines)
