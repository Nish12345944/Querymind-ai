from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.query_orchestrator import (
    process_query,
    process_clarification,
)

from app.services.query_history_service import (
    get_query_history,
    get_query_history_by_id,
)


router = APIRouter(
    prefix="/query",
    tags=["Query"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about the database.",
    )


class ClarificationRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=1,
    )

    answer: str = Field(
        ...,
        min_length=1,
    )


# ============================================================
# QUERY
# ============================================================

@router.post("/")
async def query(
    request: QueryRequest,
):
    return await process_query(
        request.question
    )


# ============================================================
# CLARIFICATION
# ============================================================

@router.post("/clarify")
async def clarify(
    request: ClarificationRequest,
):
    return await process_clarification(
        conversation_id=request.conversation_id,
        answer=request.answer,
    )


# ============================================================
# QUERY HISTORY
# ============================================================

@router.get("/history")
async def query_history(
    limit: int = 50,
):
    """
    Return recent QueryMind requests.

    Maximum history records returned: 100.
    """

    history = await get_query_history(
        limit=limit
    )

    return {
        "count": len(history),
        "items": [
            {
                "id": item.id,
                "request_id": item.request_id,
                "question": item.question,
                "sql": item.sql,
                "status": item.status,
                "row_count": item.row_count,
                "answer": item.answer,
                "error": item.error,
                "duration_ms": item.duration_ms,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at
                    else None
                ),
            }
            for item in history
        ],
    }


# ============================================================
# SINGLE HISTORY RECORD
# ============================================================

@router.get("/history/{history_id}")
async def query_history_detail(
    history_id: int,
):
    """
    Return one query-history record.
    """

    history = await get_query_history_by_id(
        history_id
    )

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Query history record not found.",
        )

    return {
        "id": history.id,
        "request_id": history.request_id,
        "question": history.question,
        "sql": history.sql,
        "status": history.status,
        "row_count": history.row_count,
        "answer": history.answer,
        "error": history.error,
        "duration_ms": history.duration_ms,
        "created_at": (
            history.created_at.isoformat()
            if history.created_at
            else None
        ),
    }