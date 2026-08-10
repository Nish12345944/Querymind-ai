import sqlglot
from sqlglot import exp

from app.services.schema_service import (
    get_database_schema
)


async def validate_sql(sql: str):

    sql = sql.strip()

    if not sql:

        return {
            "valid": False,
            "reason": "Empty SQL query."
        }

    # ---------------------------------------------------------
    # 1. Parse SQL
    # ---------------------------------------------------------

    try:

        statements = sqlglot.parse(
            sql,
            dialect="postgres"
        )

    except Exception as exc:

        return {
            "valid": False,
            "reason": f"SQL syntax error: {str(exc)}"
        }

    # ---------------------------------------------------------
    # 2. One statement only
    # ---------------------------------------------------------

    if len(statements) != 1:

        return {
            "valid": False,
            "reason": "Only one SQL statement is allowed."
        }

    statement = statements[0]

    # ---------------------------------------------------------
    # 3. SELECT only
    # ---------------------------------------------------------

    if not isinstance(statement, exp.Select):

        return {
            "valid": False,
            "reason": "Only SELECT queries are allowed."
        }

    # ---------------------------------------------------------
    # 4. Load actual database schema
    # ---------------------------------------------------------

    schema = await get_database_schema()

    valid_tables = set(schema.keys())

    # ---------------------------------------------------------
    # 5. Validate referenced tables
    # ---------------------------------------------------------

    referenced_tables = set()

    for table in statement.find_all(exp.Table):

        referenced_tables.add(
            table.name
        )

    unknown_tables = (
        referenced_tables - valid_tables
    )

    if unknown_tables:

        return {
            "valid": False,
            "reason": (
                "Unknown table(s): "
                + ", ".join(sorted(unknown_tables))
            )
        }

    # ---------------------------------------------------------
    # 6. Validate columns
    # ---------------------------------------------------------

    table_columns = {}

    for table_name, table_info in schema.items():

        table_columns[table_name] = {
            column["name"]
            for column in table_info["columns"]
        }

    # Build a global set of valid column names.
    # This is useful for simple unqualified columns.
    all_columns = set()

    for columns in table_columns.values():
        all_columns.update(columns)

    unknown_columns = []

    for column in statement.find_all(exp.Column):

        column_name = column.name

        # Ignore wildcard:
        # SELECT *
        if column_name == "*":
            continue

        table_alias = column.table

        # -----------------------------------------------------
        # Qualified column:
        # orders.total_amount
        # -----------------------------------------------------

        if table_alias:

            matching_table = None

            for table in statement.find_all(exp.Table):

                if table.alias_or_name == table_alias:

                    matching_table = table.name
                    break

            if matching_table:

                valid_columns = table_columns.get(
                    matching_table,
                    set()
                )

                if column_name not in valid_columns:

                    unknown_columns.append(
                        f"{table_alias}.{column_name}"
                    )

        # -----------------------------------------------------
        # Unqualified column:
        # total_amount
        # -----------------------------------------------------

        else:

            if column_name not in all_columns:

                unknown_columns.append(
                    column_name
                )

    if unknown_columns:

        return {
            "valid": False,
            "reason": (
                "Unknown column(s): "
                + ", ".join(
                    sorted(set(unknown_columns))
                )
            )
        }

    # ---------------------------------------------------------
    # Everything passed
    # ---------------------------------------------------------

    return {
        "valid": True,
        "reason": "SQL passed validation."
    }