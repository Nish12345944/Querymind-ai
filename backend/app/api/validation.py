from fastapi import APIRouter
from pydantic import BaseModel

from app.services.sql_validator import (
    validate_sql
)


router = APIRouter(
    prefix="/validation",
    tags=["SQL Validation"]
)


class SQLValidationRequest(BaseModel):

    sql: str


@router.post("/validate")
async def validate_sql_endpoint(
    request: SQLValidationRequest
):

    result = await validate_sql(
        request.sql
    )

    return result