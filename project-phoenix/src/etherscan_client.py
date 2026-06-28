"""Minimal Etherscan client for Project Phoenix.

Reads ETHERSCAN_API_KEY from the environment. Do not hard-code keys.
"""

from __future__ import annotations

import os
from typing import Any

import requests


BASE_URL = "https://api.etherscan.io/api"


class EtherscanClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing ETHERSCAN_API_KEY environment variable")

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        payload = {**params, "apikey": self.api_key}
        response = requests.get(BASE_URL, params=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def normal_transactions(self, address: str, start_block: int = 0, end_block: int = 99999999) -> dict[str, Any]:
        return self._get(
            {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": end_block,
                "sort": "asc",
            }
        )

    def erc20_transfers(self, address: str, start_block: int = 0, end_block: int = 99999999) -> dict[str, Any]:
        return self._get(
            {
                "module": "account",
                "action": "tokentx",
                "address": address,
                "startblock": start_block,
                "endblock": end_block,
                "sort": "asc",
            }
        )
