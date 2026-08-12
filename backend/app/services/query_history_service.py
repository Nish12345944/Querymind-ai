from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.db.database import AsyncSessionLocal
from app.db.models import QueryHistory


# ============================================================
# SAVE QUERY HISTORY
# ============================================================

async def save_query_history(
    *,
    request_id: str,
    question: str,
    sql: str | None,
    status: str,
    row_count: int = 0,
    answer: str | None = None,
    error: str | None = None,
    duration_ms: float | None = None,
):
    async with AsyncSessionLocal() as session:

        history = QueryHistory(
            request_id=request_id,
            question=question,
            sql=sql,
            status=status,
            row_count=row_count,
            answer=answer,
            error=error,
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )

        session.add(history)

        await session.commit()

        await session.refresh(history)

        return history


# ============================================================
# GET QUERY HISTORY
# ============================================================

async def get_query_history(
    limit: int = 50,
):
    limit = max(1, min(limit, 100))

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(QueryHistory)
            .order_by(desc(QueryHistory.created_at))
            .limit(limit)
        )

        return result.scalars().all()


# ============================================================
# GET QUERY HISTORY BY ID
# ============================================================

async def get_query_history_by_id(
    history_id: int,
):
    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(QueryHistory).where(
                QueryHistory.id == history_id
            )
        )

        return result.scalar_one_or_none()