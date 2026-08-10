from fastapi import APIRouter
from pydantic import BaseModel

from app.services.sql_generator import generate_sql


router = APIRouter(
    prefix="/sql",
    tags=["SQL Generation"]
)


class SQLGenerationRequest(BaseModel):

    question: str

    top_k: int = 5


@router.post("/generate")
async def generate_sql_endpoint(
    request: SQLGenerationRequest
):

    result = await generate_sql(
        question=request.question,
        top_k=request.top_k
    )

    return result