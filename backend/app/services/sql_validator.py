import sqlglot
from sqlglot import exp

from app.services.schema_service import (
    get_database_schema
)

from app.services.relationship_validator import (
    get_valid_relationships
)


# ============================================================
# JOIN RELATIONSHIP VALIDATION
# ============================================================

def validate_join_relationships(
    statement,
    valid_relationships
):
    """
    Validate that JOIN conditions correspond to
    actual foreign-key relationships in the database.
    """

    aliases = {}

    for table in statement.find_all(exp.Table):

        aliases[table.alias_or_name] = table.name

    for join in statement.find_all(exp.Join):

        if join.args.get("on") is None:

            return {
                "valid": False,
                "reason": (
                    "JOIN without an ON condition "
                    "is not allowed."
                )
            }

        on_expression = join.args["on"]

        found_valid_relationship = False

        for equality in on_expression.find_all(exp.EQ):

            left = equality.left
            right = equality.right

            if not isinstance(
                left,
                exp.Column
            ):
                continue

            if not isinstance(
                right,
                exp.Column
            ):
                continue

            left_alias = left.table
            right_alias = right.table

            left_table = aliases.get(
                left_alias
            )

            right_table = aliases.get(
                right_alias
            )

            if not left_table or not right_table:

                continue

            left_column = left.name
            right_column = right.name

            left_reference = (
                left_table,
                left_column
            )

            right_reference = (
                right_table,
                right_column
            )

            if (
                left_reference,
                right_reference
            ) in valid_relationships:

                found_valid_relationship = True
                break

        if not found_valid_relationship:

            return {
                "valid": False,
                "reason": (
                    "JOIN does not match a known "
                    "database relationship."
                )
            }

    return {
        "valid": True,
        "reason": (
            "JOIN relationships are valid."
        )
    }


# ============================================================
# COLLECT SELECT ALIASES
# ============================================================

def collect_select_aliases(
    statement
):
    """
    Collect aliases created in the SELECT list.

    Example:

        SUM(oi.quantity * oi.unit_price) AS revenue

    creates the valid SQL alias:

        revenue

    PostgreSQL allows that alias to be referenced by
    ORDER BY, so the validator must not treat it as an
    unknown database column.
    """

    aliases = set()

    for expression in statement.expressions:

        if not isinstance(
            expression,
            exp.Expression
        ):
            continue

        alias = expression.alias

        if alias:

            aliases.add(
                alias
            )

    return aliases


# ============================================================
# CHECK WHETHER A COLUMN IS A SELECT ALIAS
# ============================================================

def is_select_alias_reference(
    column,
    select_aliases
):
    """
    Determine whether an unqualified column reference
    corresponds to a SELECT alias.

    Example:

        SELECT
            SUM(...) AS revenue
        FROM order_items
        ORDER BY revenue DESC

    'revenue' in ORDER BY is a SELECT alias.
    """

    if column.table:

        return False

    return (
        column.name in select_aliases
    )


# ============================================================
# MAIN SQL VALIDATOR
# ============================================================

async def validate_sql(
    sql: str
):
    """
    Validate generated SQL before execution.

    Validation includes:

    1. Empty query detection
    2. UNSUPPORTED detection
    3. SQL syntax validation
    4. Single-statement validation
    5. SELECT-only validation
    6. Dangerous-operation detection
    7. Table validation
    8. Column validation
    9. SELECT-alias validation
    10. JOIN relationship validation
    """

    # ========================================================
    # 1. Clean SQL
    # ========================================================

    sql = sql.strip()

    if not sql:

        return {
            "valid": False,
            "reason": "Empty SQL query.",
            "checks": {
                "syntax": False
            }
        }

    # ========================================================
    # 2. Handle UNSUPPORTED response
    # ========================================================

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

    # ========================================================
    # 3. Parse SQL
    # ========================================================

    try:

        statements = sqlglot.parse(
            sql,
            dialect="postgres"
        )

    except Exception as exc:

        return {
            "valid": False,
            "reason": (
                f"SQL syntax error: {str(exc)}"
            ),
            "checks": {
                "syntax": False
            }
        }

    # ========================================================
    # 4. Only one statement allowed
    # ========================================================

    if len(statements) != 1:

        return {
            "valid": False,
            "reason": (
                "Only one SQL statement "
                "is allowed."
            ),
            "checks": {
                "syntax": True,
                "single_statement": False
            }
        }

    statement = statements[0]

    # ========================================================
    # 5. SELECT only
    # ========================================================

    if not isinstance(
        statement,
        exp.Select
    ):

        return {
            "valid": False,
            "reason": (
                "Only SELECT statements "
                "are allowed."
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": False
            }
        }

    # ========================================================
    # 6. Detect forbidden SQL operations
    # ========================================================

    forbidden_node_types = {
        "Insert",
        "Update",
        "Delete",
        "Drop",
        "Create",
        "Alter",
        "Merge",
        "Grant",
        "Revoke",
        "Truncate",
        "TruncateTable"
    }

    for node in statement.walk():

        node_type = type(node).__name__

        if node_type in forbidden_node_types:

            return {
                "valid": False,
                "reason": (
                    "Forbidden SQL operation: "
                    f"{node_type}"
                ),
                "checks": {
                    "syntax": True,
                    "single_statement": True,
                    "select_only": True,
                    "forbidden_operations": False
                }
            }

    # ========================================================
    # 7. Load actual database schema
    # ========================================================

    try:

        schema = await get_database_schema()

    except Exception as exc:

        return {
            "valid": False,
            "reason": (
                "Could not load database schema: "
                f"{str(exc)}"
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "schema_loaded": False
            }
        }

    # ========================================================
    # 8. Get valid table names
    # ========================================================

    valid_tables = set(
        schema.keys()
    )

    # ========================================================
    # 9. Build table -> columns mapping
    # ========================================================

    table_columns = {}

    for table_name, table_info in schema.items():

        table_columns[table_name] = {
            column["name"]
            for column in table_info.get(
                "columns",
                []
            )
        }

    # ========================================================
    # 10. Find referenced tables
    # ========================================================

    referenced_tables = set()

    for table in statement.find_all(
        exp.Table
    ):

        referenced_tables.add(
            table.name
        )

    # ========================================================
    # 11. Check unknown tables
    # ========================================================

    unknown_tables = (
        referenced_tables - valid_tables
    )

    if unknown_tables:

        return {
            "valid": False,
            "reason": (
                "Unknown table(s): "
                + ", ".join(
                    sorted(
                        unknown_tables
                    )
                )
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "tables": False
            }
        }

    # ========================================================
    # 12. Build table aliases
    # ========================================================

    aliases = {}

    for table in statement.find_all(
        exp.Table
    ):

        aliases[
            table.alias_or_name
        ] = table.name

    # ========================================================
    # 13. Collect SELECT aliases
    # ========================================================
    #
    # Example:
    #
    # SUM(...) AS revenue
    #
    # creates:
    #
    # select_aliases = {"revenue"}
    #
    # ========================================================

    select_aliases = (
        collect_select_aliases(
            statement
        )
    )

    # ========================================================
    # 14. Validate columns
    # ========================================================

    unknown_columns = []

    # --------------------------------------------------------
    # Collect every column available in referenced tables
    # --------------------------------------------------------

    referenced_columns = set()

    for table_name in referenced_tables:

        referenced_columns.update(
            table_columns.get(
                table_name,
                set()
            )
        )

    # --------------------------------------------------------
    # Inspect every column
    # --------------------------------------------------------

    for column in statement.find_all(
        exp.Column
    ):

        column_name = column.name

        # ----------------------------------------------------
        # SELECT *
        # ----------------------------------------------------

        if column_name == "*":

            continue

        table_reference = column.table

        # ====================================================
        # SELECT ALIAS
        #
        # Example:
        #
        # ORDER BY revenue
        #
        # where:
        #
        # SUM(...) AS revenue
        #
        # ====================================================

        if is_select_alias_reference(
            column,
            select_aliases
        ):

            continue

        # ====================================================
        # Qualified column
        #
        # Example:
        #
        # p.product_name
        # ====================================================

        if table_reference:

            actual_table = aliases.get(
                table_reference
            )

            if actual_table is None:

                unknown_columns.append(
                    f"{table_reference}."
                    f"{column_name}"
                )

                continue

            valid_columns = (
                table_columns.get(
                    actual_table,
                    set()
                )
            )

            if column_name not in valid_columns:

                unknown_columns.append(
                    f"{actual_table}."
                    f"{column_name}"
                )

        # ====================================================
        # Unqualified column
        #
        # Example:
        #
        # product_name
        #
        # OR:
        #
        # revenue
        # ====================================================

        else:

            if (
                column_name
                not in referenced_columns
            ):

                unknown_columns.append(
                    column_name
                )

    # ========================================================
    # 15. Return unknown column error
    # ========================================================

    if unknown_columns:

        return {
            "valid": False,
            "reason": (
                "Unknown column(s): "
                + ", ".join(
                    sorted(
                        set(
                            unknown_columns
                        )
                    )
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

    # ========================================================
    # 16. Validate JOIN relationships
    # ========================================================

    try:

        valid_relationships = (
            await get_valid_relationships()
        )

        join_validation = (
            validate_join_relationships(
                statement,
                valid_relationships
            )
        )

    except Exception as exc:

        return {
            "valid": False,
            "reason": (
                "Could not validate JOIN "
                f"relationships: {str(exc)}"
            ),
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "tables": True,
                "columns": True,
                "join_relationships": False
            }
        }

    # ========================================================
    # 17. Reject invalid JOIN
    # ========================================================

    if not join_validation["valid"]:

        return {
            "valid": False,
            "reason": join_validation["reason"],
            "checks": {
                "syntax": True,
                "single_statement": True,
                "select_only": True,
                "tables": True,
                "columns": True,
                "join_relationships": False
            }
        }

    # ========================================================
    # 18. Everything passed
    # ========================================================

    return {
        "valid": True,
        "reason": (
            "SQL passed all validation checks."
        ),
        "checks": {
            "syntax": True,
            "single_statement": True,
            "select_only": True,
            "tables": True,
            "columns": True,
            "join_relationships": True
        }
    }