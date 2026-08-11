import sqlglot

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000


async def execute_readonly_sql(sql: str):

    sql = sql.strip()

    # ---------------------------------------------------------
    # 1. Basic SQL parsing
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. Only one statement
    # ---------------------------------------------------------

    if len(statements) != 1:

        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": "Only one SQL statement is allowed."
        }

    statement = statements[0]

    # ---------------------------------------------------------
    # 3. SELECT only
    # ---------------------------------------------------------

    if not isinstance(statement, sqlglot.exp.Select):

        return {
            "success": False,
            "row_count": 0,
            "rows": [],
            "error": "Only SELECT statements are allowed."
        }

    # ---------------------------------------------------------
    # 4. Enforce maximum result size
    #
    # IMPORTANT:
    # Do NOT overwrite an existing LIMIT.
    #
    # Example:
    #
    #     LIMIT 5
    #
    # must remain LIMIT 5.
    #
    # Only add LIMIT 100 when the query has no LIMIT.
    # ---------------------------------------------------------

    if statement.args.get("limit") is None:

        statement = statement.limit(MAX_ROWS)

    safe_sql = statement.sql(
        dialect="postgres"
    )

    # ---------------------------------------------------------
    # 5. Execute with timeout
    # ---------------------------------------------------------

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

            # -------------------------------------------------
            # Safety guard
            #
            # Existing LIMIT values are preserved, but never
            # allow more than MAX_ROWS to leave the service.
            # -------------------------------------------------

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