from app.services.schema_service import get_database_schema


TABLE_DESCRIPTIONS = {
    "categories": (
        "Contains product categories used to group products."
    ),

    "customers": (
        "Contains customer information including location, "
        "registration date, and customer segment."
    ),

    "employees": (
        "Contains employees working at NovaMart stores, "
        "including their department and job title."
    ),

    "inventory": (
        "Contains current inventory quantities for products "
        "at individual stores."
    ),

    "order_items": (
        "Contains individual products included in each customer order. "
        "Used to calculate product-level sales and revenue."
    ),

    "orders": (
        "Contains customer purchase transactions, including "
        "order date, store, customer, sales channel, status, "
        "and total amount."
    ),

    "payments": (
        "Contains payment transactions associated with customer orders."
    ),

    "products": (
        "Contains products sold by NovaMart, including category, "
        "supplier, selling price, cost price, launch date, and status."
    ),

    "regions": (
        "Contains geographical regions used to organize stores, "
        "customers, and suppliers."
    ),

    "returns": (
        "Contains products returned by customers, including "
        "return reason, quantity, and refund amount."
    ),

    "shipments": (
        "Contains shipment and delivery information for customer orders."
    ),

    "stores": (
        "Contains NovaMart physical stores, including their city, "
        "region, and store type."
    ),

    "suppliers": (
        "Contains suppliers that provide products to NovaMart."
    ),
}


async def build_schema_documents():

    schema = await get_database_schema()

    documents = []

    for table_name, table_info in schema.items():

        description = TABLE_DESCRIPTIONS.get(
            table_name,
            "Contains business data used by NovaMart."
        )

        lines = []

        lines.append(f"TABLE: {table_name}")
        lines.append("")
        lines.append(f"PURPOSE: {description}")
        lines.append("")
        lines.append("COLUMNS:")

        for column in table_info["columns"]:

            nullable = (
                "nullable"
                if column["nullable"]
                else "required"
            )

            lines.append(
                f"- {column['name']} "
                f"({column['type']}, {nullable})"
            )

        if table_info["primary_keys"]:

            lines.append("")
            lines.append("PRIMARY KEYS:")

            for key in table_info["primary_keys"]:
                lines.append(f"- {key}")

        if table_info["foreign_keys"]:

            lines.append("")
            lines.append("FOREIGN KEY RELATIONSHIPS:")

            for foreign_key in table_info["foreign_keys"]:

                lines.append(
                    f"- {foreign_key['column']} -> "
                    f"{foreign_key['references_table']}."
                    f"{foreign_key['references_column']}"
                )

        document = "\n".join(lines)

        documents.append({
            "table_name": table_name,
            "content": document
        })

    return documents