from fastapi import APIRouter, Query
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


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class ClarificationRequest(BaseModel):
    conversation_id: str
    answer: str = Field(..., min_length=1)


@router.post("/")
async def query(request: QueryRequest):
    return await process_query(request.question)


@router.post("/clarify")
async def clarify(request: ClarificationRequest):
    return await process_clarification(
        conversation_id=request.conversation_id,
        answer=request.answer,
    )


@router.get("/history")
async def query_history(
    limit: int = Query(default=20, ge=1, le=100),
):
    history = await get_query_history(limit)

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
                "created_at": item.created_at.isoformat(),
            }
            for item in history
        ],
    }


@router.get("/history/{history_id}")
async def query_history_detail(history_id: int):
    item = await get_query_history_by_id(history_id)

    if item is None:
        return {
            "status": "not_found",
            "history_id": history_id,
        }

    return {
        "id": item.id,
        "request_id": item.request_id,
        "question": item.question,
        "sql": item.sql,
        "status": item.status,
        "row_count": item.row_count,
        "answer": item.answer,
        "error": item.error,
        "duration_ms": item.duration_ms,
        "created_at": item.created_at.isoformat(),
    }