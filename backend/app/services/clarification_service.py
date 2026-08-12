import json
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
# SCHEMA HELPERS
# ============================================================

def get_columns(
    schema: dict,
    table_name: str
) -> set:
    """
    Return the column names for a table.
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


def has_table(
    schema: dict,
    table_name: str
) -> bool:
    """
    Check whether a table exists.
    """

    return table_name in schema


def has_columns(
    schema: dict,
    table_name: str,
    required_columns: set
) -> bool:
    """
    Check whether a table contains all required columns.
    """

    return required_columns.issubset(
        get_columns(
            schema,
            table_name
        )
    )


# ============================================================
# DETERMINISTIC SUPPORTED CHECK
# ============================================================

def is_definitely_supported(
    question: str,
    schema: dict
) -> bool:
    """
    Detect questions that are definitely answerable from
    the current database schema.

    These checks happen BEFORE Groq.
    """

    q = normalize_question(question)

    # ========================================================
    # IMPORTANT:
    # "best products" without a metric is ambiguous.
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
    # TOP PRODUCTS BY REVENUE
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
        if (
            has_columns(
                schema,
                "products",
                {
                    "product_id",
                    "product_name"
                }
            )
            and
            has_columns(
                schema,
                "order_items",
                {
                    "product_id",
                    "quantity",
                    "unit_price"
                }
            )
            and
            has_columns(
                schema,
                "orders",
                {
                    "order_id"
                }
            )
        ):
            return True

    # ========================================================
    # COUNT CUSTOMERS
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
    # COUNT ORDERS
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
    # TOTAL REVENUE
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

        if has_columns(
            schema,
            "order_items",
            {
                "quantity",
                "unit_price"
            }
        ):
            return True

    # ========================================================
    # AVERAGE PRODUCT PRICE
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
    # PRODUCTS IN CATEGORIES
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
    # ORDERS WITH CUSTOMER NAMES
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
    # STORES IN REGIONS
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
    # ORDERS IN SPECIFIC YEAR
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
    # REVENUE IN SPECIFIC YEAR
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
    # SHOW ALL PRODUCTS
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
    # GENERIC PRODUCT LISTING
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

    return False


# ============================================================
# DETERMINISTIC UNSUPPORTED CHECK
# ============================================================

def is_definitely_unsupported(
    question: str,
    schema: dict
) -> bool:
    """
    Detect questions that clearly request information
    that does not exist in the database.
    """

    q = normalize_question(question)

    # ========================================================
    # EMPLOYEE HAPPINESS
    # ========================================================

    if (
        "employee happiness" in q
        or "employee satisfaction" in q
    ):
        employee_columns = get_columns(
            schema,
            "employees"
        )

        if not any(
            column in employee_columns
            for column in [
                "happiness_score",
                "satisfaction_score",
                "happiness",
                "satisfaction"
            ]
        ):
            return True

    # ========================================================
    # CUSTOMER SATISFACTION
    # ========================================================

    if (
        "customer satisfaction" in q
        or "customer happiness" in q
    ):
        customer_columns = get_columns(
            schema,
            "customers"
        )

        if not any(
            column in customer_columns
            for column in [
                "satisfaction_score",
                "happiness_score",
                "satisfaction",
                "happiness"
            ]
        ):
            return True

    # ========================================================
    # EMPLOYEE PERFORMANCE
    # ========================================================

    if (
        "employee performance" in q
        or "employee performance rating" in q
        or "employee performance ratings" in q
    ):
        employee_columns = get_columns(
            schema,
            "employees"
        )

        if not any(
            column in employee_columns
            for column in [
                "performance_rating",
                "performance_score",
                "rating",
                "score"
            ]
        ):
            return True

    # ========================================================
    # EMPLOYEE REVIEWS TABLE
    # ========================================================

    if "employee_reviews" in q:
        if not has_table(
            schema,
            "employee_reviews"
        ):
            return True

    return False


# ============================================================
# DETERMINISTIC AMBIGUOUS OPTIONS
# ============================================================

def get_deterministic_clarification(
    question: str
) -> dict | None:
    """
    Return deterministic clarification responses for common
    ambiguous business terms.

    This avoids relying on the LLM to invent UI options.
    """

    q = normalize_question(question)

    # ========================================================
    # SALES
    # ========================================================

    if (
        q == "show me sales."
        or q == "show me sales"
        or q == "sales"
        or q == "show sales"
        or "what are sales" in q
    ):
        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "The term 'sales' is ambiguous and could "
                "refer to revenue, orders, or product sales."
            ),
            "question": (
                "What do you mean by 'sales'?"
            ),
            "options": [
                {
                    "label": "Revenue",
                    "description": (
                        "Total monetary revenue from orders."
                    )
                },
                {
                    "label": "Orders",
                    "description": (
                        "Number of orders placed."
                    )
                },
                {
                    "label": "Product sales",
                    "description": (
                        "Products sold and their quantities."
                    )
                }
            ]
        }

    # ========================================================
    # BEST PRODUCTS
    # ========================================================

    if (
        "best product" in q
        or "best products" in q
    ):
        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "The term 'best products' is ambiguous "
                "because products can be ranked by different metrics."
            ),
            "question": (
                "How would you like to rank the products?"
            ),
            "options": [
                {
                    "label": "Revenue",
                    "description": (
                        "Rank products by total revenue."
                    )
                },
                {
                    "label": "Quantity sold",
                    "description": (
                        "Rank products by units sold."
                    )
                },
                {
                    "label": "Price",
                    "description": (
                        "Rank products by selling price."
                    )
                }
            ]
        }

    # ========================================================
    # BEST STORE
    # ========================================================

    if (
        "best store" in q
        or "best stores" in q
        or "store is performing best" in q
        or "stores are performing best" in q
    ):
        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "Store performance can be measured using "
                "different metrics."
            ),
            "question": (
                "How would you like to measure store performance?"
            ),
            "options": [
                {
                    "label": "Revenue",
                    "description": (
                        "Rank stores by total revenue."
                    )
                },
                {
                    "label": "Number of orders",
                    "description": (
                        "Rank stores by order count."
                    )
                }
            ]
        }

    return None


# ============================================================
# FORMAT DATABASE SCHEMA
# ============================================================

def format_schema_for_llm(
    schema: dict
) -> str:
    """
    Convert database schema into compact text for Groq.
    """

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

    Deterministic supported, unsupported, and common
    clarification checks happen before Groq.
    """

    # ========================================================
    # 1. Load schema
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
    # 2. Known ambiguous questions
    # ========================================================

    deterministic_clarification = (
        get_deterministic_clarification(
            question
        )
    )

    if deterministic_clarification:
        return deterministic_clarification

    # ========================================================
    # 3. Definitely supported
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
    # 4. Definitely unsupported
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
    # 5. Groq fallback
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

Revenue can be calculated from:

orders.total_amount

or product-level revenue can be calculated from:

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
information, but the user's intended metric or meaning
is unclear.

Examples:

"Show me sales."
"Which products are performing best?"
"Which store is performing best?"
"How are things looking?"

For AMBIGUOUS questions ALWAYS provide useful options.

For example, for "sales", options may include:

[
    {{
        "label": "Revenue",
        "description": "Total monetary revenue from orders."
    }},
    {{
        "label": "Orders",
        "description": "Number of orders placed."
    }},
    {{
        "label": "Product sales",
        "description": "Products sold and their quantities."
    }}
]

============================================================
UNSUPPORTED
============================================================

UNSUPPORTED means the requested information genuinely
cannot be obtained from the database schema.

Examples:

"What is the employee happiness score?"
"What is the customer satisfaction score?"
"Show me employee performance ratings."
"What is the average customer happiness score?"

Do NOT classify something as unsupported merely because:

- it requires a JOIN
- it requires aggregation
- it requires a derived calculation
- the exact metric is not stored physically

============================================================
OUTPUT
============================================================

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
    "options": [
        {{
            "label": "short option",
            "description": "meaning"
        }}
    ]
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
    # 6. Groq call
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
    # 7. Parse Groq response
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

        result = json.loads(
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
    # 8. Normalize intent
    # ========================================================

    intent = str(
        result.get(
            "intent",
            ""
        )
    ).upper().strip()

    # ========================================================
    # 9. Validate intent
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
    # 10. CLEAR
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
    # 11. UNSUPPORTED
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
    # 12. AMBIGUOUS
    # ========================================================

    options = result.get(
        "options",
        []
    )

    if not isinstance(
        options,
        list
    ):
        options = []

    # Normalize malformed options returned by the LLM.
    normalized_options = []

    for option in options:

        if not isinstance(
            option,
            dict
        ):
            continue

        label = option.get(
            "label"
        )

        description = option.get(
            "description",
            ""
        )

        if label:
            normalized_options.append(
                {
                    "label": str(label),
                    "description": str(
                        description
                    )
                }
            )

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
        "options": normalized_options
    }