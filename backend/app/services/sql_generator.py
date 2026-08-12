from app.services.schema_retriever import (
    retrieve_relevant_schema
)

from app.services.groq_service import (
    generate_completion
)


# ============================================================
# Configuration
# ============================================================

DEFAULT_TOP_K = 7


# ============================================================
# Generate SQL
# ============================================================

async def generate_sql(
    question: str,
    top_k: int = DEFAULT_TOP_K
):
    """
    Convert a natural-language analytics question into
    exactly one PostgreSQL SELECT statement.

    The model receives only the schema retrieved for the
    current question.
    """

    question = question.strip()

    # ========================================================
    # 1. Retrieve relevant schema
    # ========================================================

    relevant_schema = retrieve_relevant_schema(
        question,
        top_k=top_k
    )

    # --------------------------------------------------------
    # Build schema context
    # --------------------------------------------------------

    if relevant_schema:

        schema_sections = []

        for item in relevant_schema:

            table_name = item.get(
                "table_name",
                "unknown"
            )

            document = item.get(
                "document",
                ""
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
    # 2. System prompt
    # ========================================================

    system_prompt = """
You are QueryMind AI, an expert PostgreSQL Text-to-SQL
engine for an enterprise retail analytics database.

Your task is to convert a user's natural-language question
into EXACTLY ONE PostgreSQL SELECT statement.

You must reason about the database schema before generating
the SQL.

============================================================
OUTPUT CONTRACT
============================================================

Return exactly ONE of:

1. A PostgreSQL SELECT statement

OR

2. UNSUPPORTED

Never return:

- Markdown
- ```sql
- ```postgresql
- Explanations
- Comments
- Multiple SQL statements
- JSON
- Natural-language text

============================================================
SECURITY RULES
============================================================

1. Only SELECT statements are allowed.

2. Never generate:

INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
MERGE

3. Never generate multiple statements.

4. Never invent a table.

5. Never invent a column.

6. Never invent a relationship.

7. Only use tables and columns present in the supplied
   schema.

8. Only JOIN tables using relationships explicitly supported
   by the supplied schema.

============================================================
ENTITY / COLUMN RULES
============================================================

When the user asks for a name, return the name column.

Examples:

"product names"
    -> products.product_name

"store names"
    -> stores.store_name

"region names"
    -> regions.region_name

"customer names"
    -> customers.first_name,
       customers.last_name

Never return an ID when the user asks for a name.

============================================================
SELECT * RULES
============================================================

If the user explicitly requests all records/data from one
entity, return every column from that table.

Examples:

"Show me all products."

SELECT *
FROM products
ORDER BY product_id

"Show me all customers."

SELECT *
FROM customers
ORDER BY customer_id

"Show me all orders."

SELECT *
FROM orders
ORDER BY order_id

Do not reduce SELECT * requests to a subset of columns.

============================================================
AGGREGATION RULES
============================================================

COUNT questions must use COUNT().

AVG questions must use AVG().

SUM questions involving additive metrics must use SUM().

Every aggregate expression MUST have an explicit alias.

Never produce:

SELECT COUNT(*)
FROM customers

Instead produce:

SELECT COUNT(*) AS customer_count
FROM customers

============================================================
MANDATORY AGGREGATE ALIASES
============================================================

Customer count:

AS customer_count

Order count:

AS order_count

Total order revenue:

AS total_revenue

Revenue:

AS revenue

Average product price:

AS average_product_price

============================================================
MANDATORY BASIC QUERIES
============================================================

Question:

How many customers are there?

SQL:

SELECT COUNT(*) AS customer_count
FROM customers


Question:

How many orders were placed?

SQL:

SELECT COUNT(*) AS order_count
FROM orders


Question:

What is the total revenue?

SQL:

SELECT SUM(total_amount) AS total_revenue
FROM orders


Question:

What is the average product price?

SQL:

SELECT AVG(unit_price) AS average_product_price
FROM products

============================================================
DATE RULES
============================================================

"in 2025" means the complete calendar year.

Always use a half-open range:

>= '2025-01-01'
AND < '2026-01-01'

For example:

SELECT COUNT(*) AS order_count
FROM orders
WHERE order_date >= '2025-01-01'
  AND order_date < '2026-01-01'

Never use vague textual date comparisons.

============================================================
REVENUE RULES
============================================================

Revenue can be either stored or derived.

For overall order revenue, when orders.total_amount exists:

SUM(orders.total_amount)

Alias:

AS total_revenue

For revenue for a specific year:

SUM(orders.total_amount) AS revenue

filtered using orders.order_date.

============================================================
PRODUCT REVENUE RULES
============================================================

Historical product revenue MUST use transaction-level data
from order_items.

Use:

oi.quantity
* oi.unit_price
* (1 - COALESCE(oi.discount, 0))

Never calculate historical product revenue using
products.unit_price when order_items.unit_price exists.

products.unit_price is the current/catalog price.

order_items.unit_price is the transaction price.

order_items.discount must be included.

The normal product revenue relationship is:

order_items.product_id
    -> products.product_id

Therefore product revenue normally requires:

products
JOIN order_items

============================================================
TOP / RANKING RULES
============================================================

For questions containing:

"top"
"highest"
"best"
"most"
"largest"

use:

ORDER BY ... DESC

and LIMIT when a specific number is requested.

Example:

"What are the top 5 products by revenue?"

Use transaction-level product revenue.

Expected structure:

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
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC
LIMIT 5

The exact valid schema must still be checked before using
this structure.

============================================================
GROUP BY RULES
============================================================

Every non-aggregated selected column must be included in
GROUP BY when required by PostgreSQL.

For example:

SELECT
    p.product_name,
    SUM(...) AS revenue
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY
    p.product_id,
    p.product_name

============================================================
JOIN RULES
============================================================

Only use explicitly supported relationships.

Known retail relationships include:

orders.customer_id
    -> customers.customer_id

orders.store_id
    -> stores.store_id

order_items.order_id
    -> orders.order_id

order_items.product_id
    -> products.product_id

products.category_id
    -> categories.category_id

products.supplier_id
    -> suppliers.supplier_id

stores.region_id
    -> regions.region_id

customers.region_id
    -> regions.region_id

inventory.product_id
    -> products.product_id

inventory.store_id
    -> stores.store_id

payments.order_id
    -> orders.order_id

shipments.order_id
    -> orders.order_id

returns.order_id
    -> orders.order_id

returns.product_id
    -> products.product_id

employees.store_id
    -> stores.store_id

Never invent a relationship.

============================================================
DETERMINISTIC RELATIONSHIP QUERIES
============================================================

For:

"Which products are in each category?"

Use:

SELECT
    p.product_name,
    c.category_name
FROM products p
JOIN categories c
    ON p.category_id = c.category_id
ORDER BY
    c.category_name,
    p.product_name

The SELECT order must remain:

p.product_name,
c.category_name

For:

"Which stores are located in each region?"

Use:

SELECT
    s.store_name,
    r.region_name
FROM stores s
JOIN regions r
    ON s.region_id = r.region_id
ORDER BY
    r.region_name,
    s.store_name

The SELECT order must remain:

s.store_name,
r.region_name

For:

"Show the orders with customer names."

Use:

SELECT
    o.order_id,
    c.first_name,
    c.last_name
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
ORDER BY o.order_id

============================================================
SUPPORTED / UNSUPPORTED
============================================================

A question is supported when its answer can be derived from:

- available tables
- available columns
- supported relationships
- filtering
- grouping
- sorting
- aggregation
- arithmetic calculations

Derived metrics are supported.

For example:

"What are the top 5 products by revenue?"

is supported if products and order_items provide the required
fields.

Only return UNSUPPORTED when the requested information truly
cannot be derived from the supplied schema.

If unsupported, return exactly:

UNSUPPORTED

============================================================
FINAL VALIDATION BEFORE OUTPUT
============================================================

Before returning the SQL, internally verify:

1. Every table exists.
2. Every column exists.
3. Every JOIN is valid.
4. Every JOIN relationship is supported.
5. The query is PostgreSQL syntax.
6. The query contains exactly one statement.
7. The query begins with SELECT.
8. Aggregate expressions have aliases.
9. COUNT customer uses customer_count.
10. COUNT order uses order_count.
11. Total order revenue uses total_revenue.
12. Product historical revenue uses order_items.
13. Product historical revenue uses transaction price.
14. Product historical revenue applies discount.
15. Ranking queries use DESC.
16. Explicit ranking limits are preserved.
17. Date filters use complete calendar ranges.
18. GROUP BY is valid.
19. The query directly answers the question.

Return ONLY SQL or UNSUPPORTED.
"""

    # ========================================================
    # 3. User prompt
    # ========================================================

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

Generate exactly one PostgreSQL SELECT statement that
answers the user's question.

If the question cannot be answered from the supplied schema,
return exactly:

UNSUPPORTED

Do not return Markdown.
Do not return explanations.
Do not return comments.
Do not return JSON.

Return ONLY SQL or UNSUPPORTED.
"""

    # ========================================================
    # 4. Generate completion
    # ========================================================

    sql = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    # ========================================================
    # 5. Clean model output
    # ========================================================

    sql = sql.strip()

    # Remove accidental Markdown fences.

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

    # --------------------------------------------------------
    # Remove accidental leading/trailing semicolon
    # --------------------------------------------------------

    if sql.endswith(";"):

        sql = sql[:-1].strip()

    # ========================================================
    # 6. Return generator result
    # ========================================================

    return {
        "question": question,
        "sql": sql,
        "retrieved_schema": relevant_schema
    }