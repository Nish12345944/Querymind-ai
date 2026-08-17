import json
import re
import uuid
from typing import Any

from app.services.groq_service import generate_completion
from app.services.schema_service import get_database_schema


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def normalize_question(question: str) -> str:
    """
    Normalize whitespace and casing while preserving word
    boundaries.
    """

    if not isinstance(question, str):
        return ""

    question = question.replace("\u00a0", " ")

    return re.sub(
        r"\s+",
        " ",
        question.strip().lower(),
    )


# ============================================================
# SCHEMA HELPERS
# ============================================================

def has_table(
    schema: dict[str, Any],
    table_name: str,
) -> bool:
    return table_name in schema


def has_column(
    schema: dict[str, Any],
    table_name: str,
    column_name: str,
) -> bool:

    table = schema.get(table_name)

    if not isinstance(table, dict):
        return False

    columns = table.get("columns", [])

    return any(
        isinstance(column, dict)
        and column.get("name") == column_name
        for column in columns
    )


# ============================================================
# SCHEMA FORMATTER
# ============================================================

def format_schema_for_llm(
    schema: dict[str, Any],
) -> str:
    """
    Convert the database schema into a compact text format
    suitable for the intent classifier.
    """

    if not schema:
        return "No database schema is available."

    lines: list[str] = []

    for table_name, table_info in schema.items():

        lines.append(
            f"TABLE: {table_name}"
        )

        if not isinstance(table_info, dict):
            continue

        columns = table_info.get(
            "columns",
            [],
        )

        for column in columns:

            if not isinstance(column, dict):
                continue

            column_name = column.get(
                "name",
                "",
            )

            column_type = column.get(
                "type",
                "",
            )

            lines.append(
                f"  - {column_name} ({column_type})"
            )

        primary_keys = table_info.get(
            "primary_keys",
            [],
        )

        if primary_keys:
            lines.append(
                "  PRIMARY KEY: "
                + ", ".join(primary_keys)
            )

        foreign_keys = table_info.get(
            "foreign_keys",
            [],
        )

        for foreign_key in foreign_keys:

            if not isinstance(
                foreign_key,
                dict,
            ):
                continue

            lines.append(
                "  FOREIGN KEY: "
                f"{foreign_key.get('column')} -> "
                f"{foreign_key.get('references_table')}."
                f"{foreign_key.get('references_column')}"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# DETERMINISTIC CLARIFICATION
# ============================================================

def get_deterministic_clarification(
    question: str,
) -> dict[str, Any] | None:
    """
    Handle questions whose intent is clearly database-related
    but whose requested business metric is ambiguous.
    """

    q = normalize_question(question)

    # --------------------------------------------------------
    # Generic sales question
    # --------------------------------------------------------

    if re.search(
        r"\bsales?\b",
        q,
    ):

        # If the user specifies a concrete sales metric,
        # don't ask for clarification.
        if any(
            phrase in q
            for phrase in [
                "revenue",
                "orders",
                "order count",
                "units sold",
                "product sales",
            ]
        ):
            return None

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "The term 'sales' could refer to revenue, "
                "orders, or product-level sales."
            ),
            "question": (
                "What would you like to see for sales?"
            ),
            "options": [
                "Revenue",
                "Orders",
                "Product sales",
            ],
        }

    # --------------------------------------------------------
    # Generic performance question
    # --------------------------------------------------------

    if any(
        phrase in q
        for phrase in [
            "best performing",
            "top performing",
            "poor performing",
            "performance",
        ]
    ):

        if not any(
            keyword in q
            for keyword in [
                "product",
                "store",
                "region",
                "customer",
            ]
        ):

            return {
                "intent": "AMBIGUOUS",
                "needs_clarification": True,
                "is_unsupported": False,
                "reason": (
                    "The subject of performance is unclear."
                ),
                "question": (
                    "What would you like to compare?"
                ),
                "options": [
                    "Products",
                    "Stores",
                    "Regions",
                    "Customers",
                ],
            }

    return None


# ============================================================
# DEFINITELY SUPPORTED
# ============================================================

def is_definitely_supported(
    question: str,
    schema: dict[str, Any],
) -> bool:

    q = normalize_question(question)

    # --------------------------------------------------------
    # Customer count
    # --------------------------------------------------------

    if (
        re.search(
            r"how\s*many\s*customers?",
            q,
        )
        or re.search(
            r"(number|count|total\s+number)\s*(of)?\s*customers?",
            q,
        )
    ):
        return has_table(
            schema,
            "customers",
        )

    # --------------------------------------------------------
    # Order count
    # --------------------------------------------------------

    if (
        re.search(
            r"how\s*many\s*orders?",
            q,
        )
        or re.search(
            r"(number|count|total\s+number)\s*(of)?\s*orders?",
            q,
        )
    ):
        return has_table(
            schema,
            "orders",
        )

    # --------------------------------------------------------
    # Total revenue
    # --------------------------------------------------------

    if (
        "revenue" in q
        and any(
            phrase in q
            for phrase in [
                "total",
                "sum",
                "how much",
            ]
        )
    ):
        return (
            has_table(
                schema,
                "orders",
            )
            and has_column(
                schema,
                "orders",
                "total_amount",
            )
        )

    # --------------------------------------------------------
    # Product/category query
    # --------------------------------------------------------

    if (
        "product" in q
        and (
            "category" in q
            or "categories" in q
        )
    ):
        return (
            has_table(
                schema,
                "products",
            )
            and has_table(
                schema,
                "categories",
            )
        )

    # --------------------------------------------------------
    # Store/region query
    # --------------------------------------------------------

    if (
        "store" in q
        and (
            "region" in q
            or "regions" in q
        )
    ):
        return (
            has_table(
                schema,
                "stores",
            )
            and has_table(
                schema,
                "regions",
            )
        )

    # --------------------------------------------------------
    # Product revenue
    # --------------------------------------------------------

    if (
        "product" in q
        and "revenue" in q
    ):
        return (
            has_table(
                schema,
                "products",
            )
            and has_table(
                schema,
                "order_items",
            )
            and has_table(
                schema,
                "orders",
            )
        )

    return False


# ============================================================
# DEFINITELY UNSUPPORTED
# ============================================================

def is_definitely_unsupported(
    question: str,
    schema: dict[str, Any],
) -> bool:

    q = normalize_question(question)

    # --------------------------------------------------------
    # Employee happiness / unsupported employee metrics
    # --------------------------------------------------------

    if any(
        phrase in q
        for phrase in [
            "employee happiness",
            "employee happiness score",
            "employee satisfaction score",
            "employee happiness rating",
        ]
    ):
        if not has_column(
            schema,
            "employees",
            "happiness_score",
        ):
            return True

    # --------------------------------------------------------
    # Explicitly unknown employee metrics
    # --------------------------------------------------------

    if (
        "employee" in q
        and any(
            phrase in q
            for phrase in [
                "happiness score",
                "satisfaction score",
                "happiness rating",
            ]
        )
    ):
        return True

    # --------------------------------------------------------
    # Completely unrelated topics
    # --------------------------------------------------------

    unrelated_keywords = [
        "weather",
        "movie",
        "football",
        "cricket",
        "politics",
        "bitcoin price",
        "stock price",
        "recipe",
    ]

    if any(
        keyword in q
        for keyword in unrelated_keywords
    ):
        return True

    return False


# ============================================================
# LLM CLASSIFIER
# ============================================================

async def classify_with_llm(
    question: str,
    schema: dict[str, Any],
) -> dict[str, Any]:

    schema_text = format_schema_for_llm(
        schema
    )

    system_prompt = f"""
You are the intent classifier for QueryMind AI,
an enterprise retail Text-to-SQL system.

Classify the user's question into exactly one of:

CLEAR
AMBIGUOUS
UNSUPPORTED

CLEAR:
The database contains enough information to answer
the question.

AMBIGUOUS:
The question is related to the database, but the
business meaning or requested metric is unclear.

UNSUPPORTED:
The requested information cannot be answered using
the available database schema.

DATABASE SCHEMA:

{schema_text}

IMPORTANT RULES:

1. Do not classify a question as UNSUPPORTED merely
   because the wording is informal.

2. Questions asking for customer counts are CLEAR when
   the customers table exists.

3. Questions asking for order counts are CLEAR when
   the orders table exists.

4. Questions asking for total revenue are CLEAR when
   orders.total_amount exists.

5. Generic questions such as "Show me sales" are
   AMBIGUOUS because sales could mean revenue, orders,
   or product sales.

Return ONLY JSON in this exact structure:

{{
    "intent": "CLEAR",
    "needs_clarification": false,
    "is_unsupported": false,
    "reason": null,
    "question": null,
    "options": []
}}
"""

    user_prompt = f"""
User question:

{question}
"""

    response = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    try:
        result = json.loads(
            response
        )

    except json.JSONDecodeError:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "Unable to reliably classify "
                "the question."
            ),
            "question": (
                "Could you clarify what you "
                "would like to know?"
            ),
            "options": [],
        }

    if not isinstance(
        result,
        dict,
    ):
        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": (
                "Invalid classifier response."
            ),
            "question": (
                "Could you clarify what you "
                "would like to know?"
            ),
            "options": [],
        }

    return result


# ============================================================
# QUESTION ANALYSIS
# ============================================================

async def analyze_question(
    question: str,
) -> dict[str, Any]:
    """
    Analyze a natural-language database question.

    Deterministic rules run before the LLM.
    """

    normalized_question = normalize_question(
        question
    )

    # ========================================================
    # EMPTY QUESTION
    # ========================================================

    if not normalized_question:

        return {
            "intent": "AMBIGUOUS",
            "needs_clarification": True,
            "is_unsupported": False,
            "reason": "Question cannot be empty.",
            "question": (
                "Please provide a database question."
            ),
            "options": [],
        }

    # ========================================================
    # CUSTOMER COUNT FAST PATH
    # ========================================================

    if (
        re.search(
            r"how\s*many\s*customers?",
            normalized_question,
        )
        or re.search(
            r"(number|count|total\s+number)\s*(of)?\s*customers?",
            normalized_question,
        )
    ):

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": None,
            "question": None,
            "options": [],
        }

    # ========================================================
    # ORDER COUNT FAST PATH
    # ========================================================

    if (
        re.search(
            r"how\s*many\s*orders?",
            normalized_question,
        )
        or re.search(
            r"(number|count|total\s+number)\s*(of)?\s*orders?",
            normalized_question,
        )
    ):

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": None,
            "question": None,
            "options": [],
        }

    # ========================================================
    # LOAD SCHEMA
    # ========================================================

    schema = await get_database_schema()

    # ========================================================
    # DETERMINISTIC CLARIFICATION
    # ========================================================

    clarification = (
        get_deterministic_clarification(
            normalized_question
        )
    )

    if clarification:
        return clarification

    # ========================================================
    # DEFINITELY UNSUPPORTED
    # ========================================================

    if is_definitely_unsupported(
        normalized_question,
        schema,
    ):

        return {
            "intent": "UNSUPPORTED",
            "needs_clarification": False,
            "is_unsupported": True,
            "reason": (
                "The requested information is not "
                "available in the database schema."
            ),
            "question": None,
            "options": [],
        }

    # ========================================================
    # DEFINITELY SUPPORTED
    # ========================================================

    if is_definitely_supported(
        normalized_question,
        schema,
    ):

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": None,
            "question": None,
            "options": [],
        }

    # ========================================================
    # LLM FALLBACK
    # ========================================================

    result = await classify_with_llm(
        question=normalized_question,
        schema=schema,
    )

    # ========================================================
    # NORMALIZE RESULT
    # ========================================================

    raw_intent = result.get(
        "intent",
        "AMBIGUOUS",
    )

    if not isinstance(
        raw_intent,
        str,
    ):
        raw_intent = "AMBIGUOUS"

    intent = raw_intent.upper().strip()

    if intent not in {
        "CLEAR",
        "AMBIGUOUS",
        "UNSUPPORTED",
    }:
        intent = "AMBIGUOUS"

    # ========================================================
    # CLEAR
    # ========================================================

    if intent == "CLEAR":

        return {
            "intent": "CLEAR",
            "needs_clarification": False,
            "is_unsupported": False,
            "reason": result.get(
                "reason"
            ),
            "question": None,
            "options": [],
        }

    # ========================================================
    # UNSUPPORTED
    # ========================================================

    if intent == "UNSUPPORTED":

        return {
            "intent": "UNSUPPORTED",
            "needs_clarification": False,
            "is_unsupported": True,
            "reason": (
                result.get("reason")
                or (
                    "The requested information is "
                    "not available in the database."
                )
            ),
            "question": None,
            "options": [],
        }

    # ========================================================
    # AMBIGUOUS
    # ========================================================

    return {
        "intent": "AMBIGUOUS",
        "needs_clarification": True,
        "is_unsupported": False,
        "reason": (
            result.get("reason")
            or "The question is ambiguous."
        ),
        "question": (
            result.get("question")
            or (
                "Could you clarify what you "
                "would like to know?"
            )
        ),
        "options": (
            result.get("options")
            if isinstance(
                result.get("options"),
                list,
            )
            else []
        ),
    }


# ============================================================
# CONVERSATION ID
# ============================================================

def create_conversation_id() -> str:
    """
    Generate a unique conversation ID.
    """

    return str(uuid.uuid4())