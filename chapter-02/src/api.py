"""
api.py – FastAPI HTTP server for the Product Recommendation Agent.

Endpoints:
    GET  /health          – liveness check
    POST /recommend       – single-turn product recommendation
    POST /chat            – multi-turn conversation (session_id scoped)

Start the server locally:
    uvicorn src.api:app --reload --port 8000

Or via Docker:
    docker-compose up
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.product_catalog import get_recommendations, list_all_products, search_products

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AcmeCorp Product Recommendation API",
    description=(
        "REST API backed by the AcmeCorp Product Recommendation Agent. "
        "Demonstrates tool use with the Microsoft Agent Framework SDK."
    ),
    version="1.0.0",
)

# In-memory session store: maps session_id -> RecommendationAgent instance.
# In production this would be replaced by a distributed session store.
_sessions: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    """Request body for POST /recommend."""

    query: str = Field(..., min_length=1, description="Product search query or scenario description.")


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str = Field(..., min_length=1, description="User message text.")
    session_id: str | None = Field(
        default=None,
        description="Session identifier for multi-turn conversation. "
        "Omit (or pass null) to start a new session.",
    )


class ProductSummary(BaseModel):
    """Lightweight product representation returned in API responses."""

    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    price: float


class RecommendResponse(BaseModel):
    """Response body for POST /recommend."""

    query: str
    results: list[ProductSummary]
    total: int


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    session_id: str
    reply: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    version: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_product_summary(product: dict[str, Any]) -> ProductSummary:
    """Convert a raw product dict to a ``ProductSummary`` instance."""
    return ProductSummary(
        id=product["id"],
        name=product["name"],
        description=product["description"],
        category=product["category"],
        tags=product.get("tags", []),
        price=float(product.get("price", 0.0)),
    )


def _get_or_create_session(session_id: str | None) -> tuple[str, Any]:
    """Return ``(session_id, agent)`` for an existing or new session.

    Lazily imports ``RecommendationAgent`` so that tests that only exercise
    the catalog tool don't require Azure credentials.
    """
    from src.recommendation_agent import RecommendationAgent  # noqa: PLC0415

    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    agent = RecommendationAgent()
    _sessions[new_id] = agent
    return new_id, agent


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["operations"])
async def health_check() -> HealthResponse:
    """Liveness check.  Returns ``{"status": "ok"}`` when the service is up."""
    return HealthResponse(status="ok", version=app.version)


@app.post("/recommend", response_model=RecommendResponse, tags=["catalog"])
async def recommend(request: RecommendRequest) -> RecommendResponse:
    """Search the product catalog and return matching recommendations.

    This endpoint uses the pure-Python product catalog tool directly, so it
    works without Azure credentials and returns results instantly.

    - Matches on product name, description, category, and tags.
    - Returns results ordered by relevance (most matches first).
    """
    try:
        products = search_products(request.query)
        summaries = [_to_product_summary(p) for p in products]
        return RecommendResponse(
            query=request.query,
            results=summaries,
            total=len(summaries),
        )
    except FileNotFoundError as exc:
        logger.error("Product catalog file not found: %s", exc)
        raise HTTPException(status_code=503, detail="Product catalog unavailable.") from exc
    except ValueError as exc:
        logger.error("Invalid catalog format: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Multi-turn chat with the Product Recommendation Agent.

    The agent uses the product_lookup tool internally and composes natural
    language responses.  Pass the returned ``session_id`` in subsequent
    requests to continue the same conversation.

    **Requires** Azure credentials (``AZURE_AI_PROJECT_ENDPOINT`` and
    ``AZURE_OPENAI_DEPLOYMENT`` must be set).
    """
    try:
        session_id, agent = _get_or_create_session(request.session_id)
        reply = await agent.chat(request.message)
        return ChatResponse(session_id=session_id, reply=reply)
    except ValueError as exc:
        # Missing environment variables
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/catalog", response_model=list[ProductSummary], tags=["catalog"])
async def get_catalog() -> list[ProductSummary]:
    """Return the full AcmeCorp product catalog."""
    try:
        products = list_all_products()
        return [_to_product_summary(p) for p in products]
    except FileNotFoundError as exc:
        logger.error("Product catalog file not found: %s", exc)
        raise HTTPException(status_code=503, detail="Product catalog unavailable.") from exc
    except ValueError as exc:
        logger.error("Invalid catalog format: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/catalog/{product_id}/recommendations",
    response_model=list[ProductSummary],
    tags=["catalog"],
)
async def product_recommendations(product_id: str) -> list[ProductSummary]:
    """Return recommended companion products for a given product ID.

    Args:
        product_id: The exact product ID (e.g., ``ACME-MON-001``).
    """
    try:
        products = get_recommendations(product_id)
        if not products:
            # Return empty list rather than 404 – the product may exist but have no related items
            return []
        return [_to_product_summary(p) for p in products]
    except FileNotFoundError as exc:
        logger.error("Product catalog file not found: %s", exc)
        raise HTTPException(status_code=503, detail="Product catalog unavailable.") from exc
    except ValueError as exc:
        logger.error("Invalid catalog format: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
