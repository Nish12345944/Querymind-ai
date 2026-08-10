from sqlalchemy import text

from app.db.database import AsyncSessionLocal


MAX_ROWS = 100


async def execute_readonly_sql(sql: str):

    async with AsyncSessionLocal() as session:

        try:

            result = await session.execute(
                text(sql)
            )

            rows = result.mappings().all()

            rows = rows[:MAX_ROWS]

            return {
                "success": True,
                "row_count": len(rows),
                "rows": [dict(row) for row in rows]
            }

        except Exception as exc:

            return {
                "success": False,
                "row_count": 0,
                "rows": [],
                "error": str(exc)
            }