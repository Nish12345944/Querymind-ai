import sqlglot

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


# ============================================================
# CONFIGURATION
# ============================================================

MAX_ROWS = 100

STATEMENT_TIMEOUT_MS = 5000

LOCK_TIMEOUT_MS = 3000


# ============================================================
# STANDARD ERROR RESPONSE
# ============================================================

def _error_response(
    message: str
):
    return {
        "success": False,
        "row_count": 0,
        "rows": [],
        "error": message
    }


# ============================================================
# EXECUTE READ-ONLY SQL
# ============================================================

async def execute_readonly_sql(
    sql: str
):
    """
    Safely execute one read-only PostgreSQL SELECT statement.

    Safety guarantees:

    - Rejects empty SQL.
    - Rejects invalid SQL.
    - Allows exactly one statement.
    - Allows SELECT statements only.
    - Rejects SELECT INTO.
    - Enforces a maximum result size.
    - Adds LIMIT when the query has no LIMIT.
    - Caps an explicitly oversized literal LIMIT.
    - Uses PostgreSQL transaction_read_only mode.
    - Applies statement and lock timeouts.
    - Rolls back failed transactions.
    """

    # ========================================================
    # 1. Normalize input
    # ========================================================

    if not isinstance(sql, str):
        return _error_response(
            "SQL query must be a string."
        )

    sql = sql.strip()

    if not sql:
        return _error_response(
            "SQL query cannot be empty."
        )

    # ========================================================
    # 2. Parse SQL
    # ========================================================

    try:

        statements = sqlglot.parse(
            sql,
            dialect="postgres"
        )

    except Exception as exc:

        return _error_response(
            f"Invalid SQL syntax: {str(exc)}"
        )

    # ========================================================
    # 3. Exactly one statement
    # ========================================================

    if len(statements) != 1:

        return _error_response(
            "Only one SQL statement is allowed."
        )

    statement = statements[0]

    # ========================================================
    # 4. SELECT only
    # ========================================================

    if not isinstance(
        statement,
        sqlglot.exp.Select
    ):

        return _error_response(
            "Only SELECT statements are allowed."
        )

    # ========================================================
    # 5. Reject SELECT INTO
    # ========================================================
    #
    # PostgreSQL SELECT INTO creates a table and therefore
    # violates the read-only contract.
    #
    # ========================================================

    if statement.args.get("into") is not None:

        return _error_response(
            "SELECT INTO statements are not allowed."
        )

    # ========================================================
    # 6. Reject row-locking SELECT statements
    # ========================================================
    #
    # Examples:
    #
    # SELECT ... FOR UPDATE
    # SELECT ... FOR SHARE
    #
    # These can acquire database locks and are unnecessary
    # for QueryMind analytical queries.
    #
    # ========================================================

    if statement.args.get("locks"):

        return _error_response(
            "Row-locking SELECT statements are not allowed."
        )

    # ========================================================
    # 7. Enforce maximum LIMIT
    # ========================================================

    limit_expression = statement.args.get(
        "limit"
    )

    if limit_expression is None:

        statement = statement.limit(
            MAX_ROWS
        )

    else:

        limit_value = None

        try:

            expression = limit_expression.expression

            if isinstance(
                expression,
                sqlglot.exp.Literal
            ) and expression.is_int:

                limit_value = int(
                    expression.this
                )

        except Exception:
            limit_value = None

        # ----------------------------------------------------
        # Reject unsupported dynamic LIMIT expressions.
        # ----------------------------------------------------

        if limit_value is None:

            return _error_response(
                "LIMIT must use a numeric literal."
            )

        # ----------------------------------------------------
        # Reject invalid LIMIT values.
        # ----------------------------------------------------

        if limit_value <= 0:

            return _error_response(
                "LIMIT must be greater than zero."
            )

        # ----------------------------------------------------
        # Cap oversized LIMIT.
        # ----------------------------------------------------

        if limit_value > MAX_ROWS:

            statement = statement.limit(
                MAX_ROWS
            )

    # ========================================================
    # 8. Generate normalized PostgreSQL SQL
    # ========================================================

    safe_sql = statement.sql(
        dialect="postgres"
    )

    # ========================================================
    # 9. Execute inside database session
    # ========================================================

    async with AsyncSessionLocal() as session:

        try:

            # ------------------------------------------------
            # Force transaction to read-only.
            # ------------------------------------------------

            await session.execute(
                text(
                    "SET LOCAL transaction_read_only = true"
                )
            )

            # ------------------------------------------------
            # Prevent long-running queries.
            # ------------------------------------------------

            await session.execute(
                text(
                    "SET LOCAL statement_timeout = "
                    f"'{STATEMENT_TIMEOUT_MS}ms'"
                )
            )

            # ------------------------------------------------
            # Prevent long lock waits.
            # ------------------------------------------------

            await session.execute(
                text(
                    "SET LOCAL lock_timeout = "
                    f"'{LOCK_TIMEOUT_MS}ms'"
                )
            )

            # ------------------------------------------------
            # Execute normalized SQL.
            # ------------------------------------------------

            result = await session.execute(
                text(safe_sql)
            )

            # ------------------------------------------------
            # Convert result rows to dictionaries.
            # ------------------------------------------------

            rows = result.mappings().all()

            # ------------------------------------------------
            # Defensive application-level limit.
            # ------------------------------------------------

            rows = rows[:MAX_ROWS]

            normalized_rows = [
                dict(row)
                for row in rows
            ]

            # ------------------------------------------------
            # Explicitly complete read-only transaction.
            # ------------------------------------------------

            await session.commit()

            return {
                "success": True,
                "row_count": len(
                    normalized_rows
                ),
                "rows": normalized_rows,
                "executed_sql": safe_sql
            }

        except Exception as exc:

            # ------------------------------------------------
            # Always rollback failed transaction.
            # ------------------------------------------------

            await session.rollback()

            return {
                "success": False,
                "row_count": 0,
                "rows": [],
                "error": str(exc)
            }