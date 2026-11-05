"""SENTINEL Fraud Investigator Assistant FastAPI Application.

Exposes endpoints for transaction risk explanation (/explain) and health checking (/health).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.schemas import ExplainRequest, ExplainResponse, HealthResponse
from app.services.investigation_service import InvestigationService
from app.services.transaction_store import TransactionNotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application initialization."""
    # Ensure configuration is loaded
    settings = get_settings()
    app.state.settings = settings
    app.state.investigation_service = InvestigationService(settings)
    yield


app = FastAPI(
    title="SENTINEL Fraud Investigator API",
    description=(
        "Production-grade Fraud Investigator Assistant using FastAPI, RAG, "
        "Qdrant vector policy search, Neo4j graph relationships, and Gemini models."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend or local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_investigation_service(
    settings: Settings = Depends(get_settings),
) -> InvestigationService:
    """Dependency injection provider for InvestigationService."""
    return InvestigationService(settings)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """System health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        services={
            "api": "healthy",
            "qdrant": "ready" if settings.qdrant_url else "unconfigured",
            "neo4j": "ready" if settings.neo4j_uri else "unconfigured",
            "transaction_store": "ready",
            "llm": settings.euri_llm_model,
        },
    )


@app.post(
    "/explain",
    response_model=ExplainResponse,
    status_code=status.HTTP_200_OK,
    tags=["Investigation"],
    summary="Explain transaction risk and policy citations",
    responses={
        404: {
            "description": "Transaction not found",
            "content": {"application/json": {"example": {"detail": "Transaction 'UNKNOWN' not found."}}},
        },
        422: {"description": "Validation error in request payload"},
    },
)
async def explain_transaction(
    request: ExplainRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> ExplainResponse:
    """Explain fraud risk signals, reason codes, and policy evidence for a transaction."""
    try:
        response = await service.investigate_transaction(request.transaction_id)
        return response
    except TransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation pipeline error: {exc}",
        ) from exc

