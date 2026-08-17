from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.rate_limit import rate_limit
from app.core.security import require_api_key

from app.services.query_history_service import (
    get_query_history,
    get_query_history_by_id,
)

from app.services.query_orchestrator import (
    process_clarification,
    process_query,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/query",
    tags=["Query"],
    dependencies=[
        Depends(require_api_key)
    ],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language question about the database.",
    )


class ClarificationRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    answer: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )


# ============================================================
# QUERY
# ============================================================

@router.post(
    "/",
    dependencies=[
        Depends(rate_limit)
    ],
)
async def query(
    request: QueryRequest,
):
    """
    Process a natural-language database question.
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    return await process_query(
        question=question,
    )


# ============================================================
# CLARIFICATION
# ============================================================

@router.post("/clarify")
async def clarify(
    request: ClarificationRequest,
):
    """
    Process a user's clarification response.
    """

    conversation_id = request.conversation_id.strip()
    answer = request.answer.strip()

    if not conversation_id:
        raise HTTPException(
            status_code=422,
            detail="Conversation ID cannot be empty.",
        )

    if not answer:
        raise HTTPException(
            status_code=422,
            detail="Clarification answer cannot be empty.",
        )

    return await process_clarification(
        conversation_id=conversation_id,
        answer=answer,
    )


# ============================================================
# QUERY HISTORY
# ============================================================

@router.get("/history")
async def query_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of recent records to return.",
    ),
):
    """
    Return recent query history.
    """

    history = await get_query_history(
        limit=limit,
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
    Return one query history record.
    """

    history = await get_query_history_by_id(
        history_id,
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