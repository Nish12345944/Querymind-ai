import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


MAX_REQUESTS = 30
WINDOW_SECONDS = 60


_requests: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"

    now = time.monotonic()
    request_times = _requests[client_ip]

    while (
        request_times
        and now - request_times[0] >= WINDOW_SECONDS
    ):
        request_times.popleft()

    if len(request_times) >= MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )

    request_times.append(now)