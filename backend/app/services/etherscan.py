"""
Etherscan V2 API client. Fetches transaction list and formats a "forensic story" for the LLM.
Docs: https://docs.etherscan.io/
"""
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ServiceLogger

logger = ServiceLogger("etherscan")


class EtherscanAPIError(Exception):
    """Raised when Etherscan API calls fail."""
    pass


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
        
        logger.debug(
            "fetching_transactions",
            address=address,
            chain_id=chain_id,
            offset=offset,
            page=page
        )
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                logger.info(
                    "transactions_fetched",
                    address=address,
                    chain_id=chain_id,
                    status=data.get("status"),
                    tx_count=len(data.get("result", [])),
                    message=data.get("message")
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "etherscan_api_http_error",
                error=e,
                status_code=e.response.status_code,
                address=address,
                chain_id=chain_id
            )
            raise EtherscanAPIError(f"HTTP {e.response.status_code}: {str(e)}") from e
            
        except httpx.TimeoutException as e:
            logger.error(
                "etherscan_api_timeout",
                error=e,
                address=address,
                chain_id=chain_id
            )
            raise EtherscanAPIError("Request timeout") from e
            
        except Exception as e:
            logger.error(
                "etherscan_api_unexpected_error",
                error=e,
                address=address,
                chain_id=chain_id
            )
            raise EtherscanAPIError(f"Unexpected error: {str(e)}") from e

    def get_wallet_summary(
        self,
        address: str,
        chain_id: int = 1,
        max_txs: int = 10,
    ) -> str:
        """
        Fetch the last N transactions and format them into a 'forensic story' for the LLM.
        """
        try:
            data = self.get_tx_list(address, chain_id=chain_id, offset=max_txs)
            if data.get("status") != "1":
                msg = data.get("message", "Unknown error")
                logger.warning(
                    "etherscan_api_error_status",
                    address=address,
                    chain_id=chain_id,
                    status=data.get("status"),
                    message=msg
                )
                return f"Error fetching wallet: {msg}"

            txs = data.get("result") or []
            story = wallet_story_from_txs(address, txs)
            
            logger.info(
                "wallet_story_generated",
                address=address,
                chain_id=chain_id,
                tx_count=len(txs),
                story_length=len(story)
            )
            
            return story
            
        except EtherscanAPIError as e:
            logger.error(
                "wallet_summary_failed",
                error=e,
                address=address,
                chain_id=chain_id
            )
            return f"Error fetching wallet: {str(e)}"

    def get_tx_list_ok(
        self,
        address: str,
        chain_id: int = 1,
        max_txs: int = 10,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Fetch tx list and return (wallet_story, txs). Use when you need both
        the story and raw txs (e.g. for graph ingestion) to avoid double fetch.
        """
        try:
            data = self.get_tx_list(address, chain_id=chain_id, offset=max_txs)
            if data.get("status") != "1":
                msg = data.get("message", "Unknown error")
                logger.warning(
                    "etherscan_api_error_status_with_txs",
                    address=address,
                    chain_id=chain_id,
                    status=data.get("status"),
                    message=msg
                )
                return f"Error fetching wallet: {msg}", []
                
            txs = data.get("result") or []
            story = wallet_story_from_txs(address, txs)
            
            logger.info(
                "tx_list_with_story_generated",
                address=address,
                chain_id=chain_id,
                tx_count=len(txs)
            )
            
            return story, txs
            
        except EtherscanAPIError as e:
            logger.error(
                "tx_list_fetch_failed",
                error=e,
                address=address,
                chain_id=chain_id
            )
            return f"Error fetching wallet: {str(e)}", []


def wallet_story_from_txs(address: str, txs: list[dict[str, Any]]) -> str:
    """Build forensic story string from a list of tx dicts (from Etherscan)."""
    if not txs:
        logger.info("generating_empty_wallet_story", address=address)
        return f"Forensic report for wallet: {address}\nNo transactions found (new or empty wallet)."
    
    logger.debug("processing_transactions_for_story", address=address, tx_count=len(txs))
    
    lines = [f"Forensic report for wallet: {address}\n"]
    total_value_eth = 0.0
    
    for tx in txs:
        try:
            value_eth = _wei_to_eth(tx.get("value", "0"))
            total_value_eth += value_eth
            to_addr = (tx.get("to") or "contract creation")[:14]
            date = format_timestamp(tx.get("timeStamp", "0"))
            tx_hash = (tx.get("hash") or "")[:10]
            lines.append(
                f"- On {date}, sent {value_eth:.4f} ETH to {to_addr}... (Hash: {tx_hash}...)\n"
            )
        except Exception as e:
            logger.warning(
                "transaction_processing_failed",
                address=address,
                tx_hash=tx.get("hash"),
                error=str(e)
            )
            continue
    
    logger.info(
        "wallet_story_completed",
        address=address,
        tx_count=len(txs),
        total_value_eth=total_value_eth,
        story_line_count=len(lines)
    )
    
    return "".join(lines)
