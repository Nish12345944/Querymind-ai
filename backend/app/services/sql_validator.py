import sqlglot
from sqlglot import exp

from app.services.schema_service import (
    get_database_schema
)


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Truncate,
    exp.Merge,
    exp.Grant,
    exp.Revoke,
)


async def validate_sql(sql: str):

    sql = sql.strip()

    # ---------------------------------------------------------
    # 1. Empty query
    # ---------------------------------------------------------

    if not sql:

        return {
            "valid": False,
            "reason": "Empty SQL query.",
            "checks": {}
        }

    # ---------------------------------------------------------
    # 2. Handle unsupported response
    # ---------------------------------------------------------

    if sql.upper() == "UNSUPPORTED":

        return {
            "valid": False,
            "reason": (
                "The question cannot be answered "
                "using the available database schema."
            ),
            "checks": {
                "unsupported": True
            }
        }

    # ---------------------------------------------------------
    # 3. Parse SQL
    # ---------------------------------------------------------

    try:

        statements = sqlglot.parse(
            sql,
            dialect="postgres"
        )

    except Exception as exc:

        return {
            "valid": False,
            "reason": f"SQL syntax error: {str(exc)}",
            "checks": {
                "syntax": False
            }
        }

    # ---------------------------------------------------------
    # 4. One statement only
    # ---------------------------------------------------------

    if len(statements) != 1:

        return {
            "valid": False,
            "reason": "Only one SQL statement is allowed.",
            "checks": {
                "syntax": True,
                "single_statement": False
            }
        }

    statement = statements[0]

    # ---------------------------------------------------------
    # 5. SELECT only
    # ---------------------------------------------------------

    if not isinstance(statement, exp.Select):

        return {
            "valid": False,
            "reason": "Only SELECT statements are allowed.",
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": False
            }
        }

    # ---------------------------------------------------------
    # 6. Check forbidden operations
    # ---------------------------------------------------------

    for forbidden_type in FORBIDDEN_EXPRESSIONS:

        if statement.find(forbidden_type):

            return {
                "valid": False,
                "reason": (
                    "Forbidden SQL operation: "
                    f"{forbidden_type.__name__}"
                ),
                "checks": {
                    "syntax": True,
                    "single_statement": True,
                    "select_only": True,
                    "forbidden_operations": False
                }
            }

    # ---------------------------------------------------------
    # 7. Get real database schema
    # ---------------------------------------------------------

    schema = await get_database_schema()

    valid_tables = set(schema.keys())

    table_columns = {
        table_name: {
            column["name"]
            for column in table_info["columns"]
        }
        for table_name, table_info in schema.items()
    }

    # ---------------------------------------------------------
    # 8. Validate tables
    # ---------------------------------------------------------

    referenced_tables = {
        table.name
        for table in statement.find_all(exp.Table)
    }

    unknown_tables = (
        referenced_tables - valid_tables
    )

    if unknown_tables:

        return {
            "valid": False,
            "reason": (
                "Unknown table(s): "
                + ", ".join(
                    sorted(unknown_tables)
                )
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "tables": False
            }
        }

    # ---------------------------------------------------------
    # 9. Build table aliases
    # ---------------------------------------------------------

    aliases = {}

    for table in statement.find_all(exp.Table):

        aliases[table.alias_or_name] = table.name

    # ---------------------------------------------------------
    # 10. Validate columns
    # ---------------------------------------------------------

    unknown_columns = []

    for column in statement.find_all(exp.Column):

        column_name = column.name

        # SELECT *
        if column_name == "*":
            continue

        table_reference = column.table

        # -----------------------------------------------------
        # Qualified column:
        # p.product_name
        # -----------------------------------------------------

        if table_reference:

            actual_table = aliases.get(
                table_reference
            )

            if actual_table is None:

                unknown_columns.append(
                    f"{table_reference}.{column_name}"
                )

                continue

            valid_columns = table_columns.get(
                actual_table,
                set()
            )

            if column_name not in valid_columns:

                unknown_columns.append(
                    f"{actual_table}.{column_name}"
                )

        # -----------------------------------------------------
        # Unqualified column:
        # product_name
        # -----------------------------------------------------

        else:

            matching_tables = [
                table_name
                for table_name, columns in table_columns.items()
                if column_name in columns
                and table_name in referenced_tables
            ]

            if not matching_tables:

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
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "tables": True,
                "columns": False
            }
        }

    # ---------------------------------------------------------
    # 11. Everything passed
    # ---------------------------------------------------------

    return {
        "valid": True,
        "reason": "SQL passed all validation checks.",
        "checks": {
            "syntax": True,
            "single_statement": True,
            "select_only": True,
            "tables": True,
            "columns": True
        }
    }