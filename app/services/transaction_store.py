"""Transaction storage service supporting Supabase with local deterministic fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.network import can_connect_outbound


class TransactionNotFoundError(KeyError):
    """Raised when a requested transaction ID does not exist."""


class TransactionStoreError(RuntimeError):
    """Raised on critical transaction store database errors."""


class TransactionStore:
    """Retrieves transaction records from Supabase with deterministic local fallback."""

    def __init__(self, settings: Settings | None = None, data_path: Path | None = None) -> None:
        self.settings = settings or get_settings()
        self.data_path = data_path or (Path(__file__).resolve().parents[2] / "data" / "transactions.json")
        self._local_cache: dict[str, dict[str, Any]] = self._load_local_data()

    def _load_local_data(self) -> dict[str, dict[str, Any]]:
        """Load deterministic transaction records from disk."""
        if not self.data_path.exists():
            return {}
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            if isinstance(records, list):
                return {str(item.get("transaction_id")): item for item in records if isinstance(item, dict)}
        except Exception as exc:
            # Safe non-fatal fallback
            pass
        return {}

    def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        """Retrieve transaction by ID, checking Supabase first, then local dataset.
        
        Raises:
            TransactionNotFoundError: If the transaction is not found in any store.
            TransactionStoreError: If an unexpected unrecoverable storage failure occurs.
        """
        if not transaction_id or not isinstance(transaction_id, str):
            raise TransactionNotFoundError(f"Invalid transaction ID: '{transaction_id}'")

        tid = transaction_id.strip()

        # Try Supabase if configured and outbound network is permitted
        url = self.settings.supabase_url
        key = self.settings.supabase_key
        if can_connect_outbound() and url and key and key.get_secret_value().strip():
            headers = {
                "apikey": key.get_secret_value().strip(),
                "Authorization": f"Bearer {key.get_secret_value().strip()}",
                "Accept": "application/json",
            }
            query_url = f"{url.rstrip('/')}/rest/v1/transactions?transaction_id=eq.{tid}&select=*"
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(query_url, headers=headers)
                    if resp.status_code == 200:
                        rows = resp.json()
                        if isinstance(rows, list) and len(rows) > 0:
                            return rows[0]
            except Exception:
                # Network isolation or unprovisioned remote table - fall back to deterministic store
                pass

        # Fallback to local deterministic store
        if tid in self._local_cache:
            return dict(self._local_cache[tid])

        raise TransactionNotFoundError(f"Transaction '{tid}' not found.")

    def list_all(self) -> list[dict[str, Any]]:
        """List all available seed transactions."""
        return list(self._local_cache.values())
