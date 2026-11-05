"""Network connectivity helper to differentiate live network environments from offline/sandboxed environments."""

from __future__ import annotations

import socket


def can_connect_outbound() -> bool:
    """Fast check whether outbound network sockets are permitted in the current runtime environment."""
    try:
        with socket.create_connection(("8.8.8.8", 53), timeout=0.2):
            return True
    except (OSError, socket.error):
        return False

