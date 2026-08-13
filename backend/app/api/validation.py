from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sql_validator import (
    validate_sql
)


router = APIRouter(
    prefix="/validation",
    tags=["SQL Validation"],
)


class SQLValidationRequest(BaseModel):

    sql: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


@router.post("/validate")
async def validate_sql_endpoint(
    request: SQLValidationRequest,
):

    result = await validate_sql(
        request.sql.strip()
    )

    return result