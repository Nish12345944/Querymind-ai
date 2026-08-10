from fastapi import APIRouter

from app.services.schema_service import get_database_schema


router = APIRouter(
    prefix="/schema",
    tags=["Schema"]
)


@router.get("/")
async def database_schema():

    schema = await get_database_schema()

    return {
        "database": "novamart",
        "tables": schema
    }