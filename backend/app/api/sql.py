from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sql_generator import generate_sql


router = APIRouter(
    prefix="/sql",
    tags=["SQL Generation"],
)


class SQLGenerationRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=15,
    )


@router.post("/generate")
async def generate_sql_endpoint(
    request: SQLGenerationRequest,
):

    result = await generate_sql(
        question=request.question.strip(),
        top_k=request.top_k,
    )

    return result