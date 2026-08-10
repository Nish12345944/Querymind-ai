from fastapi import APIRouter
from pydantic import BaseModel

from app.services.query_orchestrator import (
    process_query,
    process_clarification
)


router = APIRouter(
    prefix="/query",
    tags=["Query"]
)


class QueryRequest(BaseModel):

    question: str


class ClarificationRequest(BaseModel):

    conversation_id: str

    answer: str


@router.post("/")
async def query(
    request: QueryRequest
):

    return await process_query(
        request.question
    )


@router.post("/clarify")
async def clarify(
    request: ClarificationRequest
):

    return await process_clarification(
        conversation_id=request.conversation_id,
        answer=request.answer
    )