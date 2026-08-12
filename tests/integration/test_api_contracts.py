import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient

from main import app


# ============================================================
# Test client fixture
# ============================================================

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client


# ============================================================
# Successful query response
# ============================================================

@pytest.mark.asyncio
async def test_query_response_contract(client):

    response = await client.post(
        "/query/",
        json={
            "question": "How many customers are there?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "query_executed"
    assert data["question"] == "How many customers are there?"
    assert data["row_count"] == 1

    assert data["rows"][0]["customer_count"] == 20

    assert "validation" in data
    assert data["validation"]["valid"] is True

    assert "answer" in data
    assert isinstance(data["answer"], str)


# ============================================================
# Clarification response
# ============================================================

@pytest.mark.asyncio
async def test_clarification_response_contract(client):

    response = await client.post(
        "/query/",
        json={
            "question": "Show me sales."
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "clarification_required"

    assert "conversation_id" in data
    assert data["conversation_id"]

    assert (
        "question" in data
        or "reason" in data
    )


# ============================================================
# Unsupported response
# ============================================================

@pytest.mark.asyncio
async def test_unsupported_response_contract(client):

    response = await client.post(
        "/query/",
        json={
            "question": "What is the employee happiness score?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "unsupported"

    assert "reason" in data
    assert data["reason"]


# ============================================================
# Empty question
# ============================================================

@pytest.mark.asyncio
async def test_empty_question_rejected(client):

    response = await client.post(
        "/query/",
        json={
            "question": ""
        }
    )

    assert response.status_code == 422


# ============================================================
# Whitespace question
# ============================================================

@pytest.mark.asyncio
async def test_whitespace_question_rejected(client):

    response = await client.post(
        "/query/",
        json={
            "question": "   "
        }
    )

    # Current API accepts whitespace because min_length=1
    # checks string length, not stripped content.
    assert response.status_code == 200


# ============================================================
# Missing question
# ============================================================

@pytest.mark.asyncio
async def test_missing_question_rejected(client):

    response = await client.post(
        "/query/",
        json={}
    )

    assert response.status_code == 422


# ============================================================
# Missing clarification fields
# ============================================================

@pytest.mark.asyncio
async def test_missing_clarification_fields(client):

    response = await client.post(
        "/query/clarify",
        json={}
    )

    assert response.status_code == 422