from app.services.schema_service import (
    get_database_schema
)


# ============================================================
# KNOWN ENTERPRISE RELATIONSHIPS
# ============================================================
#
# These represent the intended relationships in the
# QueryMind enterprise database.
#
# Format:
#
# (
#     source_table,
#     source_column,
#     target_table,
#     target_column
# )
#
# ============================================================

KNOWN_RELATIONSHIPS = [

    # --------------------------------------------------------
    # Customers
    # --------------------------------------------------------

    (
        "customers",
        "region_id",
        "regions",
        "region_id"
    ),

    # --------------------------------------------------------
    # Employees
    # --------------------------------------------------------

    (
        "employees",
        "store_id",
        "stores",
        "store_id"
    ),

    # --------------------------------------------------------
    # Inventory
    # --------------------------------------------------------

    (
        "inventory",
        "product_id",
        "products",
        "product_id"
    ),

    (
        "inventory",
        "store_id",
        "stores",
        "store_id"
    ),

    # --------------------------------------------------------
    # Order Items
    # --------------------------------------------------------

    (
        "order_items",
        "order_id",
        "orders",
        "order_id"
    ),

    (
        "order_items",
        "product_id",
        "products",
        "product_id"
    ),

    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    (
        "orders",
        "customer_id",
        "customers",
        "customer_id"
    ),

    (
        "orders",
        "store_id",
        "stores",
        "store_id"
    ),

    # --------------------------------------------------------
    # Payments
    # --------------------------------------------------------

    (
        "payments",
        "order_id",
        "orders",
        "order_id"
    ),

    # --------------------------------------------------------
    # Products
    # --------------------------------------------------------

    (
        "products",
        "category_id",
        "categories",
        "category_id"
    ),

    (
        "products",
        "supplier_id",
        "suppliers",
        "supplier_id"
    ),

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    (
        "returns",
        "order_id",
        "orders",
        "order_id"
    ),

    (
        "returns",
        "product_id",
        "products",
        "product_id"
    ),

    # --------------------------------------------------------
    # Shipments
    # --------------------------------------------------------

    (
        "shipments",
        "order_id",
        "orders",
        "order_id"
    ),

    # --------------------------------------------------------
    # Stores
    # --------------------------------------------------------

    (
        "stores",
        "region_id",
        "regions",
        "region_id"
    ),

    # --------------------------------------------------------
    # Suppliers
    # --------------------------------------------------------

    (
        "suppliers",
        "region_id",
        "regions",
        "region_id"
    )
]


# ============================================================
# GET VALID RELATIONSHIPS
# ============================================================

async def get_valid_relationships():
    """
    Return valid table-column relationships.

    The function first checks the actual database schema
    and then adds the known enterprise relationships only
    when both sides actually exist.

    Each relationship is stored in both directions so
    either JOIN orientation can be validated.
    """

    schema = await get_database_schema()

    relationships = set()

    # ========================================================
    # 1. Add relationships from actual PostgreSQL FKs
    # ========================================================

    for table_name, table_info in schema.items():

        for foreign_key in table_info.get(
            "foreign_keys",
            []
        ):

            source = (
                table_name,
                foreign_key["column"]
            )

            target = (
                foreign_key["references_table"],
                foreign_key["references_column"]
            )

            relationships.add(
                (source, target)
            )

            relationships.add(
                (target, source)
            )

    # ========================================================
    # 2. Add known enterprise relationships
    #
    # Only add them if both tables and columns actually
    # exist in the current database.
    # ========================================================

    for (
        source_table,
        source_column,
        target_table,
        target_column
    ) in KNOWN_RELATIONSHIPS:

        # ----------------------------------------------------
        # Check source table
        # ----------------------------------------------------

        if source_table not in schema:

            continue

        # ----------------------------------------------------
        # Check target table
        # ----------------------------------------------------

        if target_table not in schema:

            continue

        # ----------------------------------------------------
        # Get source columns
        # ----------------------------------------------------

        source_columns = {
            column["name"]
            for column in schema[
                source_table
            ].get(
                "columns",
                []
            )
        }

        # ----------------------------------------------------
        # Get target columns
        # ----------------------------------------------------

        target_columns = {
            column["name"]
            for column in schema[
                target_table
            ].get(
                "columns",
                []
            )
        }

        # ----------------------------------------------------
        # Only add relationship when the actual columns
        # exist.
        # ----------------------------------------------------

        if source_column not in source_columns:

            continue

        if target_column not in target_columns:

            continue

        source = (
            source_table,
            source_column
        )

        target = (
            target_table,
            target_column
        )

        # ----------------------------------------------------
        # Add both directions
        # ----------------------------------------------------

        relationships.add(
            (source, target)
        )

        relationships.add(
            (target, source)
        )

    return relationships