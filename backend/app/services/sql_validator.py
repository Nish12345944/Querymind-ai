import sqlglot
from sqlglot import exp


# ============================================================
# QUERYMIND DATABASE SCHEMA
# ============================================================

DATABASE_SCHEMA = {
    "customers": {
        "customer_id",
        "first_name",
        "last_name",
        "email",
        "city",
        "region_id",
        "registration_date",
        "customer_segment",
    },

    "orders": {
        "order_id",
        "customer_id",
        "store_id",
        "order_date",
        "order_status",
        "sales_channel",
        "total_amount",
    },

    "order_items": {
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount",
    },

    "products": {
        "product_id",
        "product_name",
        "category_id",
        "supplier_id",
        "unit_price",
        "cost_price",
        "launch_date",
        "status",
    },

    "categories": {
        "category_id",
        "category_name",
    },

    "suppliers": {
        "supplier_id",
        "supplier_name",
        "region_id",
        "rating",
    },

    "stores": {
        "store_id",
        "store_name",
        "region_id",
    },

    "regions": {
        "region_id",
        "region_name",
    },

    "inventory": {
        "inventory_id",
        "product_id",
        "store_id",
        "quantity_available",
        "reorder_level",
        "last_restocked",
    },

    "payments": {
        "payment_id",
        "order_id",
        "payment_date",
        "payment_method",
        "amount",
        "payment_status",
    },

    "returns": {
        "return_id",
        "order_id",
        "product_id",
        "return_date",
        "quantity",
        "reason",
        "refund_amount",
    },

    "shipments": {
        "shipment_id",
        "order_id",
        "shipment_date",
        "delivery_date",
        "shipping_method",
        "shipping_status",
    },

    "employees": {
        "employee_id",
        "first_name",
        "last_name",
        "store_id",
        "role",
        "hire_date",
    },
}


# ============================================================
# VALID FOREIGN-KEY RELATIONSHIPS
# ============================================================

VALID_RELATIONSHIPS = {
    (("orders", "customer_id"), ("customers", "customer_id")),
    (("customers", "customer_id"), ("orders", "customer_id")),

    (("orders", "store_id"), ("stores", "store_id")),
    (("stores", "store_id"), ("orders", "store_id")),

    (("order_items", "order_id"), ("orders", "order_id")),
    (("orders", "order_id"), ("order_items", "order_id")),

    (("order_items", "product_id"), ("products", "product_id")),
    (("products", "product_id"), ("order_items", "product_id")),

    (("products", "category_id"), ("categories", "category_id")),
    (("categories", "category_id"), ("products", "category_id")),

    (("products", "supplier_id"), ("suppliers", "supplier_id")),
    (("suppliers", "supplier_id"), ("products", "supplier_id")),

    (("stores", "region_id"), ("regions", "region_id")),
    (("regions", "region_id"), ("stores", "region_id")),

    (("inventory", "product_id"), ("products", "product_id")),
    (("products", "product_id"), ("inventory", "product_id")),

    (("inventory", "store_id"), ("stores", "store_id")),
    (("stores", "store_id"), ("inventory", "store_id")),

    (("payments", "order_id"), ("orders", "order_id")),
    (("orders", "order_id"), ("payments", "order_id")),

    (("returns", "order_id"), ("orders", "order_id")),
    (("orders", "order_id"), ("returns", "order_id")),

    (("returns", "product_id"), ("products", "product_id")),
    (("products", "product_id"), ("returns", "product_id")),

    (("shipments", "order_id"), ("orders", "order_id")),
    (("orders", "order_id"), ("shipments", "order_id")),

    (("customers", "region_id"), ("regions", "region_id")),
    (("regions", "region_id"), ("customers", "region_id")),

    (("suppliers", "region_id"), ("regions", "region_id")),
    (("regions", "region_id"), ("suppliers", "region_id")),

    (("employees", "store_id"), ("stores", "store_id")),
    (("stores", "store_id"), ("employees", "store_id")),
}


# ============================================================
# CHECK STRUCTURE
# ============================================================

def make_checks(
    syntax=True,
    single_statement=True,
    select_only=True,
    tables=True,
    columns=True,
    join_relationships=True,
):
    return {
        "syntax": syntax,
        "single_statement": single_statement,
        "select_only": select_only,
        "tables": tables,
        "columns": columns,
        "join_relationships": join_relationships,
    }


# ============================================================
# SELECT ALIAS COLLECTION
# ============================================================

def collect_select_aliases(statement):

    aliases = set()

    for expression in statement.expressions:

        alias = expression.alias

        if alias:
            aliases.add(alias.lower())

    return aliases


# ============================================================
# TABLE ALIAS MAP
# ============================================================

def collect_table_aliases(statement):

    aliases = {}

    for table in statement.find_all(exp.Table):

        actual_table = table.name.lower()
        alias = table.alias_or_name.lower()

        aliases[alias] = actual_table

        # Also allow direct table references.
        aliases[actual_table] = actual_table

    return aliases


# ============================================================
# TABLE VALIDATION
# ============================================================

def validate_tables(statement):

    referenced_tables = set()

    for table in statement.find_all(exp.Table):

        referenced_tables.add(
            table.name.lower()
        )

    unknown_tables = (
        referenced_tables
        - set(DATABASE_SCHEMA.keys())
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
            "referenced_tables": referenced_tables,
        }

    return {
        "valid": True,
        "reason": "All tables are valid.",
        "referenced_tables": referenced_tables,
    }


# ============================================================
# COLUMN VALIDATION
# ============================================================

def validate_columns(
    statement,
    aliases,
    select_aliases,
):
    referenced_tables = {
        table.name.lower()
        for table in statement.find_all(exp.Table)
    }

    # Build a mapping:
    #
    # column_name -> tables that contain that column
    #
    # Example:
    # customer_id -> {"customers", "orders"}
    # first_name  -> {"customers"}
    #
    # This lets us detect ambiguous unqualified columns.
    column_to_tables = {}

    for table_name in referenced_tables:
        table_columns = DATABASE_SCHEMA.get(
            table_name,
            set(),
        )

        for column_name in table_columns:
            column_name = column_name.lower()

            column_to_tables.setdefault(
                column_name,
                set(),
            ).add(table_name)

    unknown_columns = []
    ambiguous_columns = []

    for column in statement.find_all(exp.Column):

        column_name = column.name.lower()

        # --------------------------------------------------------
        # SELECT *
        # --------------------------------------------------------

        if column_name == "*":
            continue

        table_reference = (
            column.table or ""
        ).lower()

        # --------------------------------------------------------
        # SELECT alias
        #
        # Example:
        #
        # SELECT
        #     SUM(total_amount) AS revenue
        # FROM orders
        # ORDER BY revenue DESC
        # --------------------------------------------------------

        if (
            not table_reference
            and column_name in select_aliases
        ):
            continue

        # --------------------------------------------------------
        # Qualified column
        #
        # Example:
        #
        # c.customer_id
        # o.customer_id
        # --------------------------------------------------------

        if table_reference:

            actual_table = aliases.get(
                table_reference
            )

            if actual_table is None:

                unknown_columns.append(
                    f"{table_reference}.{column_name}"
                )

                continue

            valid_columns = {
                value.lower()
                for value in DATABASE_SCHEMA.get(
                    actual_table,
                    set(),
                )
            }

            if column_name not in valid_columns:

                unknown_columns.append(
                    f"{actual_table}.{column_name}"
                )

        # --------------------------------------------------------
        # Unqualified column
        #
        # Example:
        #
        # SELECT customer_id
        #
        # If only one referenced table contains customer_id,
        # the column is valid.
        #
        # If multiple referenced tables contain customer_id,
        # the column is ambiguous and must be rejected.
        # --------------------------------------------------------

        else:

            matching_tables = column_to_tables.get(
                column_name,
                set(),
            )

            if not matching_tables:

                unknown_columns.append(
                    column_name
                )

            elif len(matching_tables) > 1:

                ambiguous_columns.append(
                    f"{column_name} "
                    f"({', '.join(sorted(matching_tables))})"
                )

    # ------------------------------------------------------------
    # Unknown columns
    # ------------------------------------------------------------

    if unknown_columns:

        return {
            "valid": False,
            "reason": (
                "Unknown column(s): "
                + ", ".join(
                    sorted(
                        set(unknown_columns)
                    )
                )
            ),
        }

    # ------------------------------------------------------------
    # Ambiguous columns
    # ------------------------------------------------------------

    if ambiguous_columns:

        return {
            "valid": False,
            "reason": (
                "Ambiguous column(s): "
                + ", ".join(
                    sorted(
                        set(ambiguous_columns)
                    )
                )
                + ". Qualify ambiguous columns "
                  "with their table alias."
            ),
        }

    return {
        "valid": True,
        "reason": "All columns are valid.",
    }


# ============================================================
# JOIN RELATIONSHIP VALIDATION
# ============================================================

def validate_join_relationships(
    statement,
    aliases,
):

    for join in statement.find_all(
        exp.Join
    ):

        on_expression = join.args.get(
            "on"
        )

        # ----------------------------------------------------
        # JOIN must have ON condition
        # ----------------------------------------------------

        if on_expression is None:

            return {
                "valid": False,
                "reason": (
                    "JOIN without an ON condition "
                    "is not allowed."
                ),
            }

        found_valid_relationship = False

        for equality in on_expression.find_all(
            exp.EQ
        ):

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

            left_alias = (
                left.table or ""
            ).lower()

            right_alias = (
                right.table or ""
            ).lower()

            left_table = aliases.get(
                left_alias
            )

            right_table = aliases.get(
                right_alias
            )

            if (
                left_table is None
                or right_table is None
            ):
                continue

            left_reference = (
                left_table,
                left.name.lower()
            )

            right_reference = (
                right_table,
                right.name.lower()
            )

            if (
                left_reference,
                right_reference
            ) in VALID_RELATIONSHIPS:

                found_valid_relationship = True
                break

        if not found_valid_relationship:

            return {
                "valid": False,
                "reason": (
                    "JOIN does not match a known "
                    "database relationship."
                ),
            }

    return {
        "valid": True,
        "reason": (
            "JOIN relationships are valid."
        ),
    }


# ============================================================
# SECURITY VALIDATION
# ============================================================

def validate_security(statement):

    # --------------------------------------------------------
    # SELECT INTO
    # --------------------------------------------------------

    if statement.args.get("into") is not None:

        return {
            "valid": False,
            "reason": (
                "SELECT INTO statements are not allowed."
            ),
        }

    # --------------------------------------------------------
    # Row locking
    #
    # Examples:
    #
    # SELECT ... FOR UPDATE
    # SELECT ... FOR SHARE
    # --------------------------------------------------------

    if statement.args.get("locks"):

        return {
            "valid": False,
            "reason": (
                "Row-locking SELECT statements "
                "are not allowed."
            ),
        }

    # --------------------------------------------------------
    # Dangerous AST operations
    # --------------------------------------------------------

    forbidden_node_types = {
        "Insert",
        "Update",
        "Delete",
        "Drop",
        "Alter",
        "Create",
        "Merge",
        "Grant",
        "Revoke",
        "Truncate",
        "TruncateTable",
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
            }

    return {
        "valid": True,
        "reason": "SQL passed security checks.",
    }


# ============================================================
# MAIN SQL VALIDATOR
# ============================================================

async def validate_sql(
    sql: str
):

    # ========================================================
    # 1. Normalize input
    # ========================================================

    if sql is None:
        sql = ""

    sql = str(sql).strip()

    # ========================================================
    # 2. Empty SQL
    # ========================================================

    if not sql:

        return {
            "valid": False,
            "reason": "Empty SQL query.",
            "checks": make_checks(
                syntax=False,
                single_statement=True,
                select_only=True,
                tables=True,
                columns=True,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 3. UNSUPPORTED
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
            },
        }

    # ========================================================
    # 4. Parse SQL
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
            "checks": make_checks(
                syntax=False,
                single_statement=True,
                select_only=True,
                tables=True,
                columns=True,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 5. Exactly one statement
    # ========================================================

    if len(statements) != 1:

        return {
            "valid": False,
            "reason": (
                "Only one SQL statement is allowed."
            ),
            "checks": make_checks(
                syntax=True,
                single_statement=False,
                select_only=True,
                tables=True,
                columns=True,
                join_relationships=True,
            ),
        }

    statement = statements[0]

    # ========================================================
    # 6. SELECT only
    # ========================================================

    if not isinstance(
        statement,
        exp.Select
    ):

        return {
            "valid": False,
            "reason": (
                "Only SELECT statements are allowed."
            ),
            "checks": make_checks(
                syntax=True,
                single_statement=True,
                select_only=False,
                tables=True,
                columns=True,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 7. Security validation
    # ========================================================

    security_result = validate_security(
        statement
    )

    if not security_result["valid"]:

        return {
            "valid": False,
            "reason": security_result["reason"],
            "checks": make_checks(
                syntax=True,
                single_statement=True,
                select_only=False,
                tables=True,
                columns=True,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 8. Validate tables
    # ========================================================

    table_result = validate_tables(
        statement
    )

    if not table_result["valid"]:

        return {
            "valid": False,
            "reason": table_result["reason"],
            "checks": make_checks(
                syntax=True,
                single_statement=True,
                select_only=True,
                tables=False,
                columns=True,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 9. Collect table aliases
    # ========================================================

    aliases = collect_table_aliases(
        statement
    )

    # ========================================================
    # 10. Collect SELECT aliases
    # ========================================================

    select_aliases = (
        collect_select_aliases(
            statement
        )
    )

    # ========================================================
    # 11. Validate columns
    # ========================================================

    column_result = validate_columns(
        statement=statement,
        aliases=aliases,
        select_aliases=select_aliases,
    )

    if not column_result["valid"]:

        return {
            "valid": False,
            "reason": column_result["reason"],
            "checks": make_checks(
                syntax=True,
                single_statement=True,
                select_only=True,
                tables=True,
                columns=False,
                join_relationships=True,
            ),
        }

    # ========================================================
    # 12. Validate JOIN relationships
    # ========================================================

    join_result = (
        validate_join_relationships(
            statement=statement,
            aliases=aliases,
        )
    )

    if not join_result["valid"]:

        return {
            "valid": False,
            "reason": join_result["reason"],
            "checks": make_checks(
                syntax=True,
                single_statement=True,
                select_only=True,
                tables=True,
                columns=True,
                join_relationships=False,
            ),
        }

    # ========================================================
    # 13. SUCCESS
    # ========================================================

    return {
        "valid": True,
        "reason": (
            "SQL passed all validation checks."
        ),
        "checks": make_checks(
            syntax=True,
            single_statement=True,
            select_only=True,
            tables=True,
            columns=True,
            join_relationships=True,
        ),
    }