import pytest
from fastapi import HTTPException

from app.core.rate_limit import (
    MAX_REQUESTS,
    _requests,
    rate_limit,
)


class MockClient:
    host = "test-rate-limit-client"


class MockRequest:
    client = MockClient()


@pytest.fixture(autouse=True)
def clear_rate_limits():
    _requests.clear()


def test_rate_limit_allows_requests():

    request = MockRequest()

    for _ in range(MAX_REQUESTS):
        rate_limit(request)


def test_rate_limit_rejects_excess_requests():

    request = MockRequest()

    for _ in range(MAX_REQUESTS):
        rate_limit(request)

    with pytest.raises(HTTPException) as exc_info:
        rate_limit(request)

    assert exc_info.value.status_code == 429
    assert (
        exc_info.value.detail
        == "Rate limit exceeded. Try again later."
    )