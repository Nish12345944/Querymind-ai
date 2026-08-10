from fastapi import APIRouter
from sqlalchemy import text
from app.db.database import AsyncSessionLocal


router = APIRouter(
    prefix="/database",
    tags=["Database"]
)


@router.get("/test")
async def test_database_connection():

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text("SELECT current_database();")
        )

        database_name = result.scalar_one()

        return {
            "status": "connected",
            "database": database_name
        }