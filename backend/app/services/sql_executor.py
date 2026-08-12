import sqlglot

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000


async def execute_readonly_sql(sql: str):

    sql = sql.strip()

    # =========================================================
    # 1. Empty SQL
    # =========================================================

    if not sql:
        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": "SQL query cannot be empty."
        }

    # =========================================================
    # 2. Parse SQL
    # =========================================================

    try:
        statements = sqlglot.parse(
            sql,
            dialect="postgres"
        )

    except Exception as exc:
        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": f"Invalid SQL syntax: {str(exc)}"
        }

    # =========================================================
    # 3. Exactly one statement
    # =========================================================

    if len(statements) != 1:
        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": "Only one SQL statement is allowed."
        }

    statement = statements[0]

    # =========================================================
    # 4. SELECT only
    # =========================================================

    if not isinstance(statement, sqlglot.exp.Select):
        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": "Only SELECT statements are allowed."
        }

    # =========================================================
    # 5. Add LIMIT only when missing
    # =========================================================

    if statement.args.get("limit") is None:
        statement = statement.limit(MAX_ROWS)

    safe_sql = statement.sql(
        dialect="postgres"
    )

    # =========================================================
    # 6. Execute query
    # =========================================================

    async with AsyncSessionLocal() as session:

        try:

            await session.execute(
                text(
                    f"SET LOCAL statement_timeout = "
                    f"'{STATEMENT_TIMEOUT_MS}ms'"
                )
            )

            result = await session.execute(
                text(safe_sql)
            )

            rows = result.mappings().all()

            rows = rows[:MAX_ROWS]

            return {
                "success": True,
                "row_count": len(rows),
                "rows": [
                    dict(row)
                    for row in rows
                ],
                "executed_sql": safe_sql
            }

        except Exception as exc:

            return {
                "success": False,
                "row_count": 0,
                "rows": [],
                "error": str(exc)
            }