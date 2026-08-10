from fastapi import APIRouter
from pydantic import BaseModel

from app.services.clarification_service import (
    analyze_question
)


router = APIRouter(
    prefix="/clarification",
    tags=["Clarification"]
)


class ClarificationRequest(BaseModel):

    question: str


@router.post("/analyze")
async def analyze_clarification(
    request: ClarificationRequest
):

    result = await analyze_question(
        request.question
    )

    return {
        "question": request.question,
        **result
    }