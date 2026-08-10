import json

from app.services.groq_service import (
    generate_completion
)


async def analyze_question(question: str):

    system_prompt = """
You are an ambiguity detection engine for an
enterprise Text-to-SQL system.

Your job is NOT to generate SQL.

Your job is to determine whether the user's
question contains ambiguity that could cause
the system to generate an incorrect query.

Examples of ambiguous questions:

"Show me sales."

Possible meanings:
- total revenue
- number of orders
- units sold
- profit

"Show me customers in the north."

Potential ambiguity:
- geographic region
- store region
- customer region

"Which products are performing best?"

Potential ambiguity:
- revenue
- units sold
- profit
- order count

A question should be considered CLEAR if the
requested metric, entity, filters, and time period
are sufficiently specified.

A question should be considered AMBIGUOUS if
different reasonable interpretations would produce
different SQL queries.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
    "needs_clarification": true or false,
    "reason": "short explanation",
    "question": "clarification question or null",
    "options": [
        {
            "label": "short option",
            "description": "meaning of option"
        }
    ]
}

If clarification is not needed:

{
    "needs_clarification": false,
    "reason": null,
    "question": null,
    "options": []
}
"""

    user_prompt = f"""
USER QUESTION:

{question}

Analyze whether clarification is required.
"""

    response = await generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    try:

        result = json.loads(response)

    except json.JSONDecodeError:

        return {
            "needs_clarification": True,
            "reason": "The ambiguity detector returned an invalid response.",
            "question": "Could you clarify what you want to know?",
            "options": []
        }

    return result