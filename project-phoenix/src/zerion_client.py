"""Minimal Zerion client for Project Phoenix.

Reads ZERION_API_KEY from the environment. Do not hard-code keys.
"""

from __future__ import annotations

import os
from typing import Any

import requests


BASE_URL = "https://api.zerion.io/v1"


class ZerionClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ZERION_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing ZERION_API_KEY environment variable")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Basic {self.api_key}"}
        response = requests.get(f"{BASE_URL}{path}", headers=headers, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def wallet_portfolio(self, address: str) -> dict[str, Any]:
        return self._get(f"/wallets/{address}/portfolio")
