from app.services.groq_service import generate_completion


async def generate_answer(
    question: str,
    sql: str,
    rows: list[dict]
):

    system_prompt = """
You are QueryMind AI, an enterprise database
assistant.

Your job is to explain SQL query results to the
user in clear, concise natural language.

Rules:

1. Answer ONLY using the provided query results.
2. Never invent values.
3. Never invent facts that are not present in the results.
4. If the result set is empty, clearly say that no matching
   records were found.
5. Do not mention internal implementation details unless
   necessary.
6. Do not generate SQL.
7. Do not claim that something exists if it is not present
   in the results.
8. Preserve important numbers accurately.
9. Use a concise professional response.
10. If multiple rows are returned, summarize them clearly.
"""

    user_prompt = f"""
USER QUESTION:

{question}


SQL QUERY:

{sql}


QUERY RESULTS:

{rows}


Provide the answer to the user's question using ONLY
the query results.
"""

    answer = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    return answer