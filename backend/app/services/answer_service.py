from app.services.groq_service import generate_completion


MAX_ROWS_FOR_LLM = 50


async def generate_answer(
    question: str,
    sql: str,
    rows: list[dict]
):
    # =========================================================
    # 1. Handle empty result
    # =========================================================

    if not rows:
        return "No matching records were found."

    # =========================================================
    # 2. Basic result information
    # =========================================================

    total_rows = len(rows)

    # Only send a limited number of rows to the LLM.
    # The actual database result is never modified.
    display_rows = rows[:MAX_ROWS_FOR_LLM]

    # =========================================================
    # 3. Handle simple single-value aggregate results
    #    deterministically
    # =========================================================

    if len(rows) == 1 and len(rows[0]) == 1:

        key, value = next(iter(rows[0].items()))

        key_lower = str(key).lower()

        if key_lower == "customer_count":
            return f"There are {value} customers."

        if key_lower == "order_count":
            return f"There were {value} orders placed."

        if key_lower == "total_revenue":
            return f"The total revenue was {value}."

        if key_lower == "revenue":
            return f"The revenue was {value}."

        if key_lower == "average_product_price":
            return f"The average product price was {value}."

        if key_lower.startswith("count"):
            return f"The result is {value}."

        if key_lower.startswith("avg"):
            return f"The average is {value}."

        if key_lower.startswith("sum"):
            return f"The total is {value}."

        if key_lower.startswith("min"):
            return f"The minimum is {value}."

        if key_lower.startswith("max"):
            return f"The maximum is {value}."

    # =========================================================
    # 4. System prompt
    # =========================================================

    system_prompt = """
You are QueryMind AI, an enterprise database assistant.

Your task is to explain the result of an already executed
SQL query in clear, concise natural language.

STRICT RULES:

1. Answer ONLY from the supplied query results.

2. NEVER invent values, records, counts, names, dates,
   prices, or other facts.

3. The value of TOTAL_ROWS_RETURNED is authoritative.

4. If TOTAL_ROWS_RETURNED is 100, say 100 if you need to
   describe the number of returned records.

5. NEVER confuse the number of rows shown to you with the
   total number of rows returned by the database.

6. The displayed rows may be only a subset of the complete
   result. Do not claim that the displayed rows are the
   complete result when they are not.

7. If the result contains many records, summarize the records
   without inventing additional records.

8. For COUNT, SUM, AVG, MIN, or MAX queries, use the exact
   returned value.

9. Preserve numeric values accurately.

10. Do not generate SQL.

11. Do not mention internal implementation details.

12. Do not mention truncation, LLMs, prompts, or token limits
    unless explicitly asked by the user.

13. For list queries, summarize what was returned rather than
    reproducing every row.

14. If TOTAL_ROWS_RETURNED is greater than the number of
    DISPLAYED_ROWS, understand that only a subset of the
    records is displayed to you.

15. When describing the number of records returned, ALWAYS
    use TOTAL_ROWS_RETURNED, never DISPLAYED_ROWS.

16. Keep the answer concise and professional.
"""

    # =========================================================
    # 5. Build result representation
    # =========================================================

    user_prompt = f"""
USER QUESTION:

{question}

SQL QUERY:

{sql}

DISPLAYED QUERY RESULTS:

{display_rows}

DISPLAYED ROWS:

{len(display_rows)}

TOTAL_ROWS_RETURNED:

{total_rows}

IMPORTANT:

TOTAL_ROWS_RETURNED is the authoritative number of rows
returned by the database.

DISPLAYED ROWS may be smaller because only a subset of the
database result is provided for explanation.

Never use DISPLAYED ROWS as the total result count.

Answer the user's question using ONLY the information above.

Do not generate SQL.
Do not invent information.
"""

    # =========================================================
    # 6. Generate natural-language answer
    # =========================================================

    answer = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    return answer.strip()