"""
End-to-end tests.

These tests exercise the full pipeline:
  HTTP request -> intent -> SQL generation -> validation
  -> execution -> answer generation -> HTTP response

Requires a live database and a valid GROQ_API_KEY.
Run with: pytest tests/e2e -v
"""

import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient

from main import app
from app.core.config import settings


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": settings.api_key},
    ) as c:
        yield c


# ============================================================
# FULL PIPELINE - DETERMINISTIC QUERIES
# ============================================================

@pytest.mark.asyncio
async def test_e2e_customer_count(client):
    response = await client.post(
        "/query/",
        json={"question": "How many customers are there?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["row_count"] == 1
    assert "customer_count" in data["rows"][0]
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert data["validation"]["valid"] is True
    assert data["sql"] is not None


@pytest.mark.asyncio
async def test_e2e_total_revenue(client):
    response = await client.post(
        "/query/",
        json={"question": "What is the total revenue?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["row_count"] == 1
    assert "total_revenue" in data["rows"][0]
    assert data["rows"][0]["total_revenue"] is not None


@pytest.mark.asyncio
async def test_e2e_top_products(client):
    response = await client.post(
        "/query/",
        json={"question": "Show me the top 5 products by revenue."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["row_count"] == 5
    assert "product_name" in data["rows"][0]
    assert "revenue" in data["rows"][0]


@pytest.mark.asyncio
async def test_e2e_stores_by_region(client):
    response = await client.post(
        "/query/",
        json={"question": "Which stores are in each region?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["row_count"] > 0
    assert "store_name" in data["rows"][0]
    assert "region_name" in data["rows"][0]


# ============================================================
# FULL PIPELINE - CLARIFICATION FLOW
# ============================================================

@pytest.mark.asyncio
async def test_e2e_clarification_flow(client):
    response = await client.post(
        "/query/",
        json={"question": "Show me sales."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "clarification_required"
    assert "conversation_id" in data
    assert data["conversation_id"]

    conversation_id = data["conversation_id"]

    clarify_response = await client.post(
        "/query/clarify",
        json={
            "conversation_id": conversation_id,
            "answer": "Revenue",
        },
    )

    assert clarify_response.status_code == 200

    clarify_data = clarify_response.json()

    assert clarify_data["status"] in {
        "completed",
        "query_executed",
    }

    assert clarify_data["row_count"] >= 1
    assert clarify_data["sql"] is not None


# ============================================================
# FULL PIPELINE - UNSUPPORTED
# ============================================================

@pytest.mark.asyncio
async def test_e2e_unsupported_query(client):
    response = await client.post(
        "/query/",
        json={"question": "What is the employee happiness score?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "unsupported"
    assert "reason" in data


# ============================================================
# RESPONSE HEADERS
# ============================================================

@pytest.mark.asyncio
async def test_e2e_request_id_header(client):
    response = await client.post(
        "/query/",
        json={"question": "How many customers are there?"},
    )

    assert response.status_code == 200
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_e2e_custom_request_id_echoed(client):
    custom_id = "test-request-abc123"

    response = await client.post(
        "/query/",
        json={"question": "How many customers are there?"},
        headers={"X-Request-ID": custom_id},
    )

    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


# ============================================================
# HISTORY PERSISTENCE
# ============================================================

@pytest.mark.asyncio
async def test_e2e_query_persisted_to_history(client):
    await client.post(
        "/query/",
        json={"question": "How many customers are there?"},
    )

    history_response = await client.get("/query/history?limit=1")

    assert history_response.status_code == 200

    data = history_response.json()

    assert data["count"] >= 1
    assert data["items"][0]["question"] is not None
    assert data["items"][0]["status"] is not None


# ============================================================
# READINESS
# ============================================================

@pytest.mark.asyncio
async def test_e2e_ready_endpoint(client):
    response = await client.get("/ready")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["database"] == "connected"
