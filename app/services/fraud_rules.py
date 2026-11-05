"""Deterministic fraud rule evaluation for SENTINEL.

Rules evaluate transaction features and graph context signals to fire
standardized, auditable fraud reason codes. Ground-truth labels are never
used in rule calculations.
"""

from __future__ import annotations

from typing import Any

# Standardized reason codes per SENTINEL specification
CODE_HIGH_AMOUNT = "HIGH_TRANSACTION_AMOUNT"
CODE_HIGH_VELOCITY = "HIGH_TRANSACTION_VELOCITY"
CODE_NEW_DEVICE = "NEW_DEVICE"
CODE_SHARED_DEVICE = "SHARED_SUSPICIOUS_DEVICE"
CODE_UNUSUAL_LOCATION = "UNUSUAL_LOCATION"
CODE_HIGH_DEVICE_RISK = "HIGH_DEVICE_RISK"

# Configurable default thresholds
AMOUNT_THRESHOLD = 5000.00
VELOCITY_THRESHOLD = 5.0
DEVICE_RISK_THRESHOLD = 0.70
HIGH_RISK_LOCATIONS = {"NIGERIA", "RUSSIA", "VIETNAM", "UNKNOWN", "FOREIGN"}


def evaluate_fraud_rules(
    transaction: dict[str, Any],
    graph_context: dict[str, Any] | None = None,
) -> list[str]:
    """Evaluate deterministic fraud rules against transaction and graph context.
    
    Args:
        transaction: Dictionary containing transaction features.
        graph_context: Optional graph neighbourhood signals (customer, device, relationships).
        
    Returns:
        List of fired reason code strings (sorted for determinism).
    """
    fired: set[str] = set()
    graph = graph_context or {}

    # 1. High Transaction Amount
    raw_amount = transaction.get("amount")
    if raw_amount is not None:
        try:
            amount_val = float(raw_amount)
            if amount_val >= AMOUNT_THRESHOLD:
                fired.add(CODE_HIGH_AMOUNT)
        except (ValueError, TypeError):
            pass

    # 2. High Transaction Velocity
    raw_velocity = transaction.get("velocity_1h") or transaction.get("velocity")
    if raw_velocity is not None:
        try:
            velocity_val = float(raw_velocity)
            if velocity_val >= VELOCITY_THRESHOLD:
                fired.add(CODE_HIGH_VELOCITY)
        except (ValueError, TypeError):
            pass

    # 3. New Device
    # Fired if flag is set, or if graph/transaction signals first-time device
    is_new = transaction.get("is_new_device")
    customer_device_count = graph.get("customer_device_count", 0)
    if is_new is True or transaction.get("device_status") == "NEW":
        fired.add(CODE_NEW_DEVICE)

    # 4. Shared Suspicious Device
    # Fired if device is linked to multiple customer accounts in graph or marked shared
    shared_customers = graph.get("shared_customer_count", 0)
    is_shared = transaction.get("is_shared_device")
    if (isinstance(shared_customers, (int, float)) and shared_customers > 1) or is_shared is True:
        fired.add(CODE_SHARED_DEVICE)

    # 5. Unusual Location
    raw_location = transaction.get("location") or transaction.get("country") or ""
    is_foreign = transaction.get("is_foreign_transaction") is True
    if is_foreign or str(raw_location).strip().upper() in HIGH_RISK_LOCATIONS:
        fired.add(CODE_UNUSUAL_LOCATION)

    # 6. High Device Risk Score
    raw_device_risk = transaction.get("device_risk_score")
    if raw_device_risk is not None:
        try:
            risk_val = float(raw_device_risk)
            if risk_val >= DEVICE_RISK_THRESHOLD:
                fired.add(CODE_HIGH_DEVICE_RISK)
        except (ValueError, TypeError):
            pass
    elif transaction.get("device_compromised") is True:
        fired.add(CODE_HIGH_DEVICE_RISK)

    # Also respect explicit reason codes already calculated in transaction data if present
    explicit_codes = transaction.get("reason_codes")
    if isinstance(explicit_codes, list):
        for code in explicit_codes:
            if isinstance(code, str) and code.strip():
                fired.add(code.strip())

    return sorted(fired)

