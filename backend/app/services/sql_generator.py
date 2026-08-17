from typing import Any

from app.services.schema_retriever import (
    retrieve_relevant_schema,
)

from app.services.groq_service import (
    generate_completion,
)


DEFAULT_TOP_K = 7


# ============================================================
# DETERMINISTIC SQL
# ============================================================

def _deterministic_sql(
    question: str,
) -> str | None:
    """
    Return deterministic SQL for common, well-defined
    retail analytics questions.

    These queries do not need an LLM. This prevents a valid
    supported question from being incorrectly classified as
    UNSUPPORTED by the SQL-generation model.
    """

    q = " ".join(
        question.strip().lower().split()
    )

    # --------------------------------------------------------
    # Customer count
    # --------------------------------------------------------

    if (
        "how many customers" in q
        or "number of customers" in q
        or "count of customers" in q
        or "total number of customers" in q
    ):
        return """
SELECT COUNT(*) AS customer_count
FROM customers
""".strip()

    # --------------------------------------------------------
    # Order count
    # --------------------------------------------------------

    if (
        "how many orders" in q
        or "number of orders" in q
        or "count of orders" in q
        or "total number of orders" in q
    ):

        # 2025 order count
        if "2025" in q:
            return """
SELECT COUNT(*) AS order_count
FROM orders
WHERE order_date >= '2025-01-01'
  AND order_date < '2026-01-01'
""".strip()

        return """
SELECT COUNT(*) AS order_count
FROM orders
""".strip()

    # --------------------------------------------------------
    # Total revenue
    # --------------------------------------------------------

    if (
        "total revenue" in q
        or "total sales revenue" in q
    ):

        # 2025 revenue
        if "2025" in q:
            return """
SELECT SUM(total_amount) AS revenue
FROM orders
WHERE order_date >= '2025-01-01'
  AND order_date < '2026-01-01'
""".strip()

        return """
SELECT SUM(total_amount) AS total_revenue
FROM orders
""".strip()

    # --------------------------------------------------------
    # Average product price
    # --------------------------------------------------------

    if (
        "average product price" in q
        or "average price of products" in q
        or "average product prices" in q
    ):
        return """
SELECT AVG(unit_price) AS average_product_price
FROM products
""".strip()

    # --------------------------------------------------------
    # Products by category
    # --------------------------------------------------------

    if (
        "which products are in each category" in q
        or "products in each category" in q
        or "products by category" in q
    ):
        return """
SELECT
    p.product_name,
    c.category_name
FROM products p
JOIN categories c
    ON p.category_id = c.category_id
ORDER BY
    c.category_name,
    p.product_name
""".strip()

    # --------------------------------------------------------
    # Stores by region
    # --------------------------------------------------------

    if (
        "which stores are located in each region" in q
        or "stores in each region" in q
        or "stores by region" in q
    ):
        return """
SELECT
    s.store_name,
    r.region_name
FROM stores s
JOIN regions r
    ON s.region_id = r.region_id
ORDER BY
    r.region_name,
    s.store_name
""".strip()

    # --------------------------------------------------------
    # Orders with customer names
    # --------------------------------------------------------

    if (
        "orders with customer names" in q
        or "orders with customer name" in q
    ):
        return """
SELECT
    o.order_id,
    c.first_name,
    c.last_name
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
ORDER BY o.order_id
""".strip()

    # --------------------------------------------------------
    # Product revenue
    # --------------------------------------------------------

    if (
        "product revenue" in q
        or "revenue by product" in q
        or "products by revenue" in q
    ):

        # Top N product revenue
        import re

        match = re.search(
            r"\btop\s+(\d+)\b",
            q,
        )

        limit_clause = ""

        if match:
            limit_clause = (
                f"\nLIMIT {int(match.group(1))}"
            )

        return f"""
SELECT
    p.product_name,
    SUM(
        oi.quantity
        * oi.unit_price
        * (1 - COALESCE(oi.discount, 0))
    ) AS revenue
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY
    p.product_id,
    p.product_name
ORDER BY revenue DESC{limit_clause}
""".strip()

    # --------------------------------------------------------
    # Product sales / units sold
    # --------------------------------------------------------

    if (
        "product sales" in q
        or "sales by product" in q
        or "units sold by product" in q
        or "how many units of each product were sold" in q
    ):

        import re

        match = re.search(
            r"\btop\s+(\d+)\b",
            q,
        )

        limit_clause = ""

        if match:
            limit_clause = (
                f"\nLIMIT {int(match.group(1))}"
            )

        # If user explicitly asks only for units, don't add
        # revenue.
        if (
            "units sold" in q
            and "revenue" not in q
        ):
            return f"""
SELECT
    p.product_name,
    SUM(oi.quantity) AS units_sold
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY
    p.product_id,
    p.product_name
ORDER BY units_sold DESC{limit_clause}
""".strip()

        return f"""
SELECT
    p.product_name,
    SUM(oi.quantity) AS units_sold,
    SUM(
        oi.quantity
        * oi.unit_price
        * (1 - COALESCE(oi.discount, 0))
    ) AS revenue
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY
    p.product_id,
    p.product_name
ORDER BY revenue DESC{limit_clause}
""".strip()

    return None


# ============================================================
# LLM SQL GENERATION
# ============================================================

async def _generate_with_llm(
    question: str,
    schema_text: str,
) -> str:

    system_prompt = """
You are QueryMind AI, an expert PostgreSQL Text-to-SQL
engine for an enterprise retail analytics database.

Convert the user's natural-language question into exactly
ONE PostgreSQL SELECT statement.

Return ONLY:

1. A PostgreSQL SELECT statement

OR

2. UNSUPPORTED

Never return Markdown, JSON, explanations, comments,
multiple statements, INSERT, UPDATE, DELETE, DROP, ALTER,
TRUNCATE, CREATE, GRANT, REVOKE, or MERGE.

SECURITY RULES:

- Only SELECT statements are allowed.
- Never invent tables.
- Never invent columns.
- Never invent relationships.
- Only use tables and columns present in the supplied schema.
- Only JOIN using supported relationships.

AGGREGATION:

- COUNT questions use COUNT().
- AVG questions use AVG().
- SUM questions use SUM().
- Every aggregate requires an explicit alias.

Mandatory aliases:

Customer count:
AS customer_count

Order count:
AS order_count

Total revenue:
AS total_revenue

Revenue:
AS revenue

Average product price:
AS average_product_price

DATE RULES:

For a question about 2025, use:

>= '2025-01-01'
AND < '2026-01-01'

REVENUE:

Overall order revenue should use:

SUM(orders.total_amount)

Historical product revenue must use order_items:

oi.quantity
* oi.unit_price
* (1 - COALESCE(oi.discount, 0))

Never use products.unit_price for historical product revenue
when order_items.unit_price is available.

PRODUCT SALES:

Product sales use order_items as the transaction source.

Use:

SUM(oi.quantity) AS units_sold

for units sold.

Use transaction-level price and discount for revenue.

JOIN RELATIONSHIPS:

orders.customer_id -> customers.customer_id
orders.store_id -> stores.store_id
order_items.order_id -> orders.order_id
order_items.product_id -> products.product_id
products.category_id -> categories.category_id
products.supplier_id -> suppliers.supplier_id
stores.region_id -> regions.region_id
customers.region_id -> regions.region_id
inventory.product_id -> products.product_id
inventory.store_id -> stores.store_id
payments.order_id -> orders.order_id
shipments.order_id -> orders.order_id
returns.order_id -> orders.order_id
returns.product_id -> products.product_id
employees.store_id -> stores.store_id

Return ONLY SQL or UNSUPPORTED.
"""

    user_prompt = f"""
DATABASE SCHEMA
============================================================

{schema_text}

============================================================
USER QUESTION
============================================================

{question}

============================================================
TASK
============================================================

Generate exactly one PostgreSQL SELECT statement.

If the question cannot be answered from the supplied schema,
return exactly:

UNSUPPORTED

Return ONLY SQL or UNSUPPORTED.
"""

    sql = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    return sql.strip()


# ============================================================
# SQL GENERATOR
# ============================================================

async def generate_sql(
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:

    question = question.strip()

    if not question:
        return {
            "question": question,
            "sql": "UNSUPPORTED",
            "retrieved_schema": [],
        }

    # ========================================================
    # 1. DETERMINISTIC COMMON QUERIES
    # ========================================================

    deterministic_sql = _deterministic_sql(
        question
    )

    if deterministic_sql is not None:

        return {
            "question": question,
            "sql": deterministic_sql,
            "retrieved_schema": [],
        }

    # ========================================================
    # 2. RETRIEVE RELEVANT SCHEMA
    # ========================================================

    relevant_schema = retrieve_relevant_schema(
        question,
        top_k=top_k,
    )

    # ========================================================
    # 3. BUILD SCHEMA CONTEXT
    # ========================================================

    if relevant_schema:

        schema_sections = []

        for item in relevant_schema:

            table_name = item.get(
                "table_name",
                "unknown",
            )

            document = item.get(
                "document",
                "",
            )

            schema_sections.append(
                f"TABLE: {table_name}\n"
                f"{document}"
            )

        schema_text = "\n\n".join(
            schema_sections
        )

    else:

        schema_text = (
            "No relevant schema was retrieved."
        )

    # ========================================================
    # 4. GENERATE USING GROQ
    # ========================================================

    sql = await _generate_with_llm(
        question=question,
        schema_text=schema_text,
    )

    # ========================================================
    # 5. CLEAN OUTPUT
    # ========================================================

    sql = sql.strip()

    if sql.startswith("```"):

        lines = sql.splitlines()

        cleaned_lines = []

        for line in lines:

            stripped = line.strip()

            if stripped.startswith("```"):
                continue

            cleaned_lines.append(line)

        sql = "\n".join(
            cleaned_lines
        ).strip()

    # Remove trailing semicolon because the SQL validator
    # handles one statement without needing it.

    if sql.endswith(";"):
        sql = sql[:-1].strip()

    # ========================================================
    # 6. FAIL CLOSED
    # ========================================================

    if not sql:
        sql = "UNSUPPORTED"

    if sql.upper() == "UNSUPPORTED":
        sql = "UNSUPPORTED"

    # ========================================================
    # 7. RETURN
    # ========================================================

    return {
        "question": question,
        "sql": sql,
        "retrieved_schema": relevant_schema,
    }