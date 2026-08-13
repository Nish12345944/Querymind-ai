from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.clarification_service import (
    analyze_question
)


router = APIRouter(
    prefix="/clarification",
    tags=["Clarification"]
)


class ClarificationRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )


@router.post("/analyze")
async def analyze_clarification(
    request: ClarificationRequest,
):

    question = request.question.strip()

    return {
        "question": question,
        **await analyze_question(question),
    }