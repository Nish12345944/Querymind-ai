import re

from app.services.schema_service import (
    get_database_schema
)


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def normalize_question(question: str) -> str:
    """
    Normalize user input for deterministic checks.
    """

    question = question.lower()

    question = re.sub(
        r"\s+",
        " ",
        question
    )

    return question.strip()


# ============================================================
# GET TABLE COLUMNS
# ============================================================

def get_columns(
    schema: dict,
    table_name: str
) -> set:
    """
    Return the set of column names for a table.
    """

    if table_name not in schema:
        return set()

    return {
        column["name"]
        for column in schema[table_name].get(
            "columns",
            []
        )
    }


# ============================================================
# CHECK TABLE EXISTS
# ============================================================

def has_table(
    schema: dict,
    table_name: str
) -> bool:
    return table_name in schema


# ============================================================
# CHECK MULTIPLE REQUIRED COLUMNS
# ============================================================

def has_columns(
    schema: dict,
    table_name: str,
    required_columns: set
) -> bool:

    columns = get_columns(
        schema,
        table_name
    )

    return required_columns.issubset(columns)


# ============================================================
# DETERMINISTIC SUPPORTED-QUESTION CHECK
# ============================================================

def is_definitely_supported(
    question: str,
    schema: dict
) -> bool:
    """
    Detect questions that are definitely answerable from
    the current database schema.

    These checks happen BEFORE Groq.

    This prevents the LLM from incorrectly classifying
    supported questions as UNSUPPORTED or AMBIGUOUS.
    """

    q = normalize_question(question)



        # ========================================================
    # AMBIGUOUS "BEST PRODUCTS"
    # ========================================================
    #
    # "best products" is ambiguous because the user has not
    # specified the metric:
    #
    # - revenue
    # - sales quantity
    # - profit
    # - rating
    # - etc.
    #
    # Therefore this must NOT be treated as a definitely
    # supported SQL question.
    #
    # The clarification layer should ask the user which
    # metric they mean.
    # ========================================================

    if (
        "best product" in q
        or "best products" in q
    ):
        if not any(
            metric in q
            for metric in [
                "revenue",
                "sales",
                "quantity",
                "units",
                "profit",
                "price",
                "rating"
            ]
        ):
            return False

    # ========================================================
    # Q001
    # Top products by revenue
    # ========================================================

    if (
        "product" in q
        and "revenue" in q
        and any(
            word in q
            for word in [
                "top",
                "best",
                "highest",
                "most"
            ]
        )
    ):

        required_products = {
            "product_id",
            "product_name"
        }

        required_order_items = {
            "product_id",
            "quantity",
            "unit_price"
        }

        required_orders = {
            "order_id"
        }

        if (
            has_columns(
                schema,
                "products",
                required_products
            )
            and
            has_columns(
                schema,
                "order_items",
                required_order_items
            )
            and
            has_columns(
                schema,
                "orders",
                required_orders
            )
        ):
            return True

    # ========================================================
    # Q002
    # Count customers
    # ========================================================

    if (
        "customer" in q
        and any(
            phrase in q
            for phrase in [
                "how many",
                "number of",
                "count"
            ]
        )
    ):

        if has_table(
            schema,
            "customers"
        ):
            return True

    # ========================================================
    # Q003
    # Count orders
    # ========================================================

    if (
        "order" in q
        and any(
            phrase in q
            for phrase in [
                "how many",
                "number of",
                "count"
            ]
        )
    ):

        if has_table(
            schema,
            "orders"
        ):
            return True

    # ========================================================
    # Q004
    # Total revenue
    # ========================================================

    if (
        "revenue" in q
        and "total" in q
    ):

        if has_columns(
            schema,
            "orders",
            {
                "total_amount"
            }
        ):
            return True

    # ========================================================
    # Q005
    # Average product price
    # ========================================================

    if (
        "product" in q
        and "price" in q
        and (
            "average" in q
            or "avg" in q
        )
    ):

        if has_columns(
            schema,
            "products",
            {
                "unit_price"
            }
        ):
            return True

    # ========================================================
    # Q006
    # Products in categories
    # ========================================================

    if (
        "product" in q
        and "categor" in q
    ):

        if (
            has_columns(
                schema,
                "products",
                {
                    "product_id",
                    "product_name",
                    "category_id"
                }
            )
            and
            has_columns(
                schema,
                "categories",
                {
                    "category_id",
                    "category_name"
                }
            )
        ):
            return True

    # ========================================================
    # Q007
    # Orders with customer names
    # ========================================================

    if (
        "order" in q
        and (
            "customer name" in q
            or "customer names" in q
            or (
                "customer" in q
                and "name" in q
            )
        )
    ):

        if (
            has_columns(
                schema,
                "orders",
                {
                    "order_id",
                    "customer_id"
                }
            )
            and
            has_columns(
                schema,
                "customers",
                {
                    "customer_id",
                    "first_name",
                    "last_name"
                }
            )
        ):
            return True

    # ========================================================
    # Q008
    # Stores in regions
    # ========================================================

    if (
        "store" in q
        and "region" in q
    ):

        if (
            has_columns(
                schema,
                "stores",
                {
                    "store_id",
                    "store_name",
                    "region_id"
                }
            )
            and
            has_columns(
                schema,
                "regions",
                {
                    "region_id",
                    "region_name"
                }
            )
        ):
            return True

    # ========================================================
    # Q009
    # Orders in a specific year
    # ========================================================

    if (
        "order" in q
        and (
            "how many" in q
            or "number of" in q
            or "count" in q
        )
        and re.search(
            r"\b20\d{2}\b",
            q
        )
    ):

        if has_columns(
            schema,
            "orders",
            {
                "order_id",
                "order_date"
            }
        ):
            return True

    # ========================================================
    # Q010
    # Revenue in a specific year
    # ========================================================

    if (
        "revenue" in q
        and re.search(
            r"\b20\d{2}\b",
            q
        )
    ):

        if has_columns(
            schema,
            "orders",
            {
                "total_amount",
                "order_date"
            }
        ):
            return True

    # ========================================================
    # Q020
    # Show all products
    # ========================================================

    if (
        "product" in q
        and any(
            phrase in q
            for phrase in [
                "show me all",
                "show all",
                "list all",
                "list the",
                "show the products",
                "show products",
                "all products"
            ]
        )
    ):

        if has_table(
            schema,
            "products"
        ):
            return True

    # ========================================================
    # Generic product listing
    # ========================================================

    if (
        "product" in q
        and has_table(
            schema,
            "products"
        )
        and any(
            phrase in q
            for phrase in [
                "show",
                "list",
                "display"
            ]
        )
    ):
        return True

    # ========================================================
    # Nothing matched
    # ========================================================

    return False


# ============================================================
# DETERMINISTIC UNSUPPORTED-QUESTION CHECK
# ============================================================

def is_definitely_unsupported(
    question: str,
    schema: dict
) -> bool:
    """
    Detect questions that clearly request information that
    does not exist in the database.
    """

    q = normalize_question(question)

    # ========================================================
    # Employee happiness / satisfaction
    # ========================================================

    if (
        "employee happiness" in q
        or "employee satisfaction" in q
    ):

        employees_columns = get_columns(
            schema,
            "employees"
        )

        if not any(
            column in employees_columns
            for column in [
                "happiness_score",
                "satisfaction_score",
                "happiness",
                "satisfaction"
            ]
        ):
            return True

    # ========================================================
    # Customer satisfaction / happiness
    # ========================================================

    if (
        "customer satisfaction" in q
        or "customer happiness" in q
    ):

        customers_columns = get_columns(
            schema,
            "customers"
        )

        if not any(
            column in customers_columns
            for column in [
                "satisfaction_score",
                "happiness_score",
                "satisfaction",
                "happiness"
            ]
        ):
            return True

    # ========================================================
    # Employee performance ratings
    # ========================================================

    if (
        "employee performance" in q
        or "employee performance rating" in q
        or "employee performance ratings" in q
    ):

        employees_columns = get_columns(
            schema,
            "employees"
        )

        if not any(
            column in employees_columns
            for column in [
                "performance_rating",
                "performance_score",
                "rating",
                "score"
            ]
        ):
            return True

    # ========================================================
    # employee_reviews table
    # ========================================================

    if "employee_reviews" in q:

        if not has_table(
            schema,
            "employee_reviews"
        ):
            return True

    return False


# ============================================================
# FORMAT DATABASE SCHEMA
# ============================================================

def format_schema_for_llm(
    schema: dict
) -> str:

    lines = []

    for table_name in sorted(
        schema.keys()
    ):

        lines.append(
            f"TABLE: {table_name}"
        )

        columns = schema[
            table_name
        ].get(
            "columns",
            []
        )

        for column in columns:

            lines.append(
                f"  - {column['name']} "
                f"({column['type']})"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN INTENT ANALYZER
# ============================================================

async def analyze_question(
    question: str
):
    """
    Analyze a user question.

    Deterministic supported/unsupported checks happen first.
    Groq is used only for genuinely ambiguous questions.
    """

    # ========================================================
    # 1. Load database schema
    # ========================================================

    try:

        schema = await get_database_schema()

    except Exception as exc:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "Unable to inspect the database schema: "
                f"{str(exc)}"
            ),
            "question": (
                "Could you clarify what you want to know?"
            ),
            "options": []
        }

    # ========================================================
    # 2. Deterministic SUPPORTED
    # ========================================================

    if is_definitely_supported(
        question,
        schema
    ):

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": None,
            "question": None,
            "options": []
        }

    # ========================================================
    # 3. Deterministic UNSUPPORTED
    # ========================================================

    if is_definitely_unsupported(
        question,
        schema
    ):

        return {
            "intent": "UNSUPPORTED",
            "needs_clarification": False,
            "is_unsupported": True,
            "reason": (
                "The requested information is not available "
                "in the database schema."
            ),
            "question": None,
            "options": []
        }

    # ========================================================
    # 4. Only now use Groq
    # ========================================================

    schema_text = format_schema_for_llm(
        schema
    )

    system_prompt = f"""
You are the intent classifier for an enterprise
retail Text-to-SQL system.

Classify the user's question as exactly one of:

CLEAR
AMBIGUOUS
UNSUPPORTED

DATABASE SCHEMA:

{schema_text}

============================================================
CLEAR
============================================================

CLEAR means the database contains enough information to
answer the question directly or through:

- JOINs
- COUNT
- SUM
- AVG
- MIN
- MAX
- filtering
- grouping
- sorting
- derived calculations

Derived metrics are supported.

Revenue is supported when it can be calculated from:

orders.total_amount

or, for product-level revenue:

order_items.quantity
order_items.unit_price
order_items.discount

Examples of CLEAR questions:

"What are the top 5 products by revenue?"

"How many customers are there?"

"How many orders were placed?"

"What is the total revenue?"

"What is the average product price?"

"Show me all products."

"Which products are in each category?"

"Show the orders with customer names."

"Which stores are located in each region?"

"What was the revenue in 2025?"

"How many orders were placed in 2025?"

============================================================
AMBIGUOUS
============================================================

AMBIGUOUS means the database may contain relevant
information, but the requested business meaning is unclear.

Examples:

"Show me sales."

"Which store is performing best?"

"Show me the best products."

"How are things looking?"

============================================================
UNSUPPORTED
============================================================

UNSUPPORTED means the requested information genuinely
cannot be obtained from the database.

Examples:

"What is the employee happiness score?"

"What is the customer satisfaction score?"

"Show me employee performance ratings."

"What is the average customer happiness score?"

"Show me data from employee_reviews."

Do NOT classify something as unsupported merely because:

- it requires a JOIN
- it requires aggregation
- it requires a derived calculation
- the exact metric is not stored physically

Return ONLY valid JSON.

CLEAR:

{{
    "intent": "CLEAR",
    "needs_clarification": false,
    "is_unsupported": false,
    "reason": null,
    "question": null,
    "options": []
}}

AMBIGUOUS:

{{
    "intent": "AMBIGUOUS",
    "needs_clarification": true,
    "is_unsupported": false,
    "reason": "short explanation",
    "question": "clarification question",
    "options": []
}}

UNSUPPORTED:

{{
    "intent": "UNSUPPORTED",
    "needs_clarification": false,
    "is_unsupported": true,
    "reason": "short explanation",
    "question": null,
    "options": []
}}
"""

    user_prompt = f"""
USER QUESTION:

{question}

Classify the question using the database schema.

Return ONLY JSON.
"""

    # ========================================================
    # 5. Groq call
    # ========================================================

    try:

        from app.services.groq_service import (
            generate_completion
        )

        response = await generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

    except Exception as exc:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "Intent classification failed: "
                f"{str(exc)}"
            ),
            "question": (
                "Could you clarify what you want to know?"
            ),
            "options": []
        }

    # ========================================================
    # 6. Parse response
    # ========================================================

    try:

        response = response.strip()

        if response.startswith("```"):

            response = response.replace(
                "```json",
                ""
            )

            response = response.replace(
                "```",
                ""
            )

            response = response.strip()

        result = __import__(
            "json"
        ).loads(
            response
        )

    except Exception:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "The intent classifier returned "
                "invalid JSON."
            ),
            "question": (
                "Could you clarify what you want to know?"
            ),
            "options": []
        }

    # ========================================================
    # 7. Normalize intent
    # ========================================================

    intent = str(
        result.get(
            "intent",
            ""
        )
    ).upper().strip()

    # ========================================================
    # 8. Validate intent
    # ========================================================

    if intent not in {
        "CLEAR",
        "AMBIGUOUS",
        "UNSUPPORTED"
    }:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "The classifier returned "
                "an invalid intent."
            ),
            "question": (
                "Could you clarify what you want to know?"
            ),
            "options": []
        }

    # ========================================================
    # 9. CLEAR
    # ========================================================

    if intent == "CLEAR":

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": None,
            "question": None,
            "options": []
        }

    # ========================================================
    # 10. UNSUPPORTED
    # ========================================================

    if intent == "UNSUPPORTED":

        return {
            "intent": "UNSUPPORTED",
            "needs_clarification": False,
            "is_unsupported": True,
            "reason": result.get(
                "reason",
                "The requested information is "
                "not available in the database."
            ),
            "question": None,
            "options": []
        }

    # ========================================================
    # 11. AMBIGUOUS
    # ========================================================

    return {
        "intent": "AMBIGUOUS",
        "needs_clarification": True,
        "is_unsupported": False,
        "reason": result.get(
            "reason"
        ),
        "question": result.get(
            "question"
        ),
        "options": result.get(
            "options",
            []
        )
    }