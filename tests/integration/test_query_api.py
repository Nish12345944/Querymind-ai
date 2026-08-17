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
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "X-API-Key": settings.api_key
        }
    ) as client:
        yield client


# ============================================================
# PUBLIC ENDPOINTS
# ============================================================

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "QueryMind AI is running"
    assert data["version"] == "0.1.0"


# ============================================================
# API AUTHENTICATION
# ============================================================

@pytest.mark.asyncio
async def test_query_requires_api_key(client):
    response = await client.post(
        "/query/",
        json={
            "question": "How many customers are there?"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "API key required."


@pytest.mark.asyncio
async def test_query_rejects_invalid_api_key(client):
    response = await client.post(
        "/query/",
        json={
            "question": "How many customers are there?"
        },
        headers={
            "X-API-Key": "invalid-api-key"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."


# ============================================================
# AUTHENTICATED QUERY TESTS
# ============================================================

@pytest.mark.asyncio
async def test_customer_count_query(authenticated_client):
    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "How many customers are there?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["row_count"] == 1
    assert data["rows"][0]["customer_count"] == 20


@pytest.mark.asyncio
async def test_order_count_query(authenticated_client):
    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "How many orders were placed?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] in {
        "query_executed",
        "clarification_required",
    }

    if data["status"] == "query_executed":
        assert data["row_count"] == 1
        assert data["rows"][0]["order_count"] == 1000


@pytest.mark.asyncio
async def test_total_revenue_query(authenticated_client):
    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "What is the total revenue?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] in {
        "query_executed",
        "clarification_required",
    }

    if data["status"] == "query_executed":
        assert data["row_count"] == 1
        assert "total_revenue" in data["rows"][0]


@pytest.mark.asyncio
async def test_clarification_query(authenticated_client):
    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "Show me sales."
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "clarification_required"


@pytest.mark.asyncio
async def test_unsupported_query(authenticated_client):
    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "What is the employee happiness score?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] in {
        "unsupported",
        "clarification_required",
    }

# ============================================================
# RATE LIMITING
# ============================================================

@pytest.mark.asyncio
async def test_query_rate_limit(authenticated_client):

    for _ in range(30):
        response = await authenticated_client.post(
            "/query/",
            json={
                "question": "How many customers are there?"
            }
        )

        assert response.status_code == 200

    response = await authenticated_client.post(
        "/query/",
        json={
            "question": "How many customers are there?"
        }
    )

    assert response.status_code == 429
    assert (
        response.json()["detail"]
        == "Rate limit exceeded. Try again later."
    )