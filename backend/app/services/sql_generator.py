from app.services.schema_retriever import (
    retrieve_relevant_schema
)

from app.services.groq_service import (
    generate_completion
)


async def generate_sql(
    question: str,
    top_k: int = 5
):

    relevant_schema = retrieve_relevant_schema(
        question,
        top_k=top_k
    )

    schema_text = "\n\n".join(
        item["document"]
        for item in relevant_schema
    )

    system_prompt = """
You are an expert PostgreSQL Text-to-SQL system.

Your job is to convert a user's natural-language
question into a PostgreSQL SELECT query.

STRICT RULES:

1. Only use tables and columns present in the provided schema.

2. Never invent tables.

3. Never invent columns.

4. Only generate SELECT statements.

5. Never generate:
   INSERT
   UPDATE
   DELETE
   DROP
   ALTER
   TRUNCATE
   CREATE
   GRANT
   REVOKE

6. Use the provided foreign-key relationships
   when constructing JOINs.

7. Never assume a relationship that is not present
   in the schema.

8. Use PostgreSQL syntax.

9. If aggregation is required, use appropriate
   GROUP BY clauses.

10. If ranking is requested, use ORDER BY and LIMIT
    appropriately.

11. If the user asks about revenue, use the appropriate
    sales fields from the schema.

12. If the question cannot be answered using the
    provided schema, return exactly:

UNSUPPORTED

13. Return ONLY SQL.

14. Do not use markdown code fences.

15. Do not explain the SQL.
"""

    user_prompt = f"""
DATABASE SCHEMA:

{schema_text}


USER QUESTION:

{question}


Generate the PostgreSQL SELECT query.
"""

    sql = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    return {
        "question": question,
        "sql": sql,
        "retrieved_schema": relevant_schema
    }