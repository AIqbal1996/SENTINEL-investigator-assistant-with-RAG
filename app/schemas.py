"""Pydantic schemas for request validation, structured responses, and citation verification."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExplainRequest(BaseModel):
    """Investigation request payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier of the transaction to investigate",
        examples=["TXN00001"],
    )


class CitedSource(BaseModel):
    """Citation linking a recommendation or risk finding to a retrieved policy chunk."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document: str = Field(
        ...,
        min_length=1,
        description="Policy document name or document identifier",
        examples=["Device_Fraud_Policy"],
    )
    chunk_id: str = Field(
        ...,
        min_length=1,
        description="Specific chunk identifier in the policy collection",
        examples=["POL002_CHUNK001"],
    )


class ExplainResponse(BaseModel):
    """Grounded, structured risk explanation response."""

    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_id: str = Field(..., description="Transaction identifier investigated")
    risk_summary: str = Field(..., min_length=1, description="Concise investigation summary")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Deterministic fraud risk reason codes fired by rule evaluation",
    )
    recommended_action: str = Field(..., min_length=1, description="Actionable investigator recommendation")
    cited_sources: list[CitedSource] = Field(
        default_factory=list,
        description="Verified citations from the retrieved policy chunks",
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok", examples=["ok"])
    version: str = Field(default="1.0.0")
    timestamp: str | None = None
    services: dict[str, str] = Field(default_factory=dict)

