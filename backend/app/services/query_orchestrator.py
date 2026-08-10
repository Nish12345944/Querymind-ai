import uuid

from app.services.clarification_service import (
    analyze_question
)

from app.services.conversation_service import (
    create_conversation,
    get_conversation,
    update_conversation
)

from app.services.sql_generator import (
    generate_sql
)

from app.services.sql_validator import (
    validate_sql
)

from app.services.sql_executor import (
    execute_readonly_sql
)

from app.services.answer_service import (
    generate_answer
)

async def process_query(
    question: str
):
    """
    Main QueryMind query pipeline.

    Flow:

    User question
        ↓
    Clarification Engine
        ↓
    Schema RAG
        ↓
    Groq
        ↓
    SQL Validation
        ↓
    Read-only PostgreSQL
    """

    # ---------------------------------------------------------
    # 1. Analyze whether the question is ambiguous
    # ---------------------------------------------------------

    clarification = await analyze_question(
        question
    )

    # ---------------------------------------------------------
    # 2. If ambiguous, create a conversation
    # ---------------------------------------------------------

    if clarification.get(
        "needs_clarification",
        False
    ):

        conversation_id = str(
            uuid.uuid4()
        )

        create_conversation(
            conversation_id=conversation_id,
            question=question
        )

        update_conversation(
            conversation_id,
            clarification=clarification,
            status="awaiting_clarification"
        )

        return {
            "status": "clarification_required",
            "conversation_id": conversation_id,
            "question": clarification.get(
                "question"
            ),
            "options": clarification.get(
                "options",
                []
            )
        }

    # ---------------------------------------------------------
    # 3. Generate SQL
    # ---------------------------------------------------------

    sql_result = await generate_sql(
        question=question
    )

    sql = sql_result["sql"]

    # ---------------------------------------------------------
    # 4. Validate generated SQL
    # ---------------------------------------------------------

    validation = await validate_sql(
        sql
    )

    if not validation["valid"]:

        return {
            "status": "sql_rejected",
            "reason": validation["reason"],
            "sql": sql
        }

    # ---------------------------------------------------------
    # 5. Execute validated SQL
    # ---------------------------------------------------------

    execution = await execute_readonly_sql(
        sql
    )

    if not execution["success"]:

        return {
            "status": "execution_failed",
            "sql": sql,
            "validation": validation,
            "error": execution["error"]
        }

    # ---------------------------------------------------------
    # 6. Generate natural-language answer
    # ---------------------------------------------------------
    answer = await generate_answer(
        question=question,
        sql=sql,
        rows=execution["rows"]
    )


    # ---------------------------------------------------------
    # 7. Return final result
    # ---------------------------------------------------------
    
    return {
        "status": "query_executed",
        "question": question,
        "sql": sql,
        "validation": validation,
        "row_count": execution["row_count"],
        "rows": execution["rows"],
        "answer": answer,
        "retrieved_schema": sql_result[
            "retrieved_schema"
        ]
    }


async def process_clarification(
    conversation_id: str,
    answer: str
):
    """
    Continue a query after the user answers
    a clarification question.
    """

    # ---------------------------------------------------------
    # 1. Retrieve conversation
    # ---------------------------------------------------------

    conversation = get_conversation(
        conversation_id
    )

    if conversation is None:

        return {
            "status": "error",
            "reason": "Conversation not found."
        }

    # ---------------------------------------------------------
    # 2. Check conversation state
    # ---------------------------------------------------------

    if conversation["status"] != "awaiting_clarification":

        return {
            "status": "error",
            "reason": (
                "Conversation is not awaiting clarification."
            )
        }

    # ---------------------------------------------------------
    # 3. Get original question
    # ---------------------------------------------------------

    original_question = conversation[
        "original_question"
    ]

    # ---------------------------------------------------------
    # 4. Combine original question + clarification
    # ---------------------------------------------------------

    clarified_question = (
        f"{original_question}\n\n"
        f"User clarification: {answer}"
    )

    # ---------------------------------------------------------
    # 5. Generate SQL using clarified question
    # ---------------------------------------------------------

    sql_result = await generate_sql(
        question=clarified_question
    )

    sql = sql_result["sql"]

    # ---------------------------------------------------------
    # 6. Validate generated SQL
    # ---------------------------------------------------------

    validation = await validate_sql(
        sql
    )

    if not validation["valid"]:

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_rejected",
            generated_sql=sql
        )

        return {
            "status": "sql_rejected",
            "conversation_id": conversation_id,
            "reason": validation["reason"],
            "sql": sql
        }

    # ---------------------------------------------------------
    # 7. Execute validated SQL
    # ---------------------------------------------------------

    execution = await execute_readonly_sql(
        sql
    )

    if not execution["success"]:

        update_conversation(
            conversation_id,
            clarification=answer,
            status="execution_failed",
            generated_sql=sql
        )

        return {
            "status": "execution_failed",
            "conversation_id": conversation_id,
            "sql": sql,
            "validation": validation,
            "error": execution["error"]
        }

    # ---------------------------------------------------------
    # 8. Update conversation state
    # ---------------------------------------------------------

    update_conversation(
        conversation_id,
        clarification=answer,
        status="query_executed",
        generated_sql=sql,
        rows=execution["rows"]
    )

    # ---------------------------------------------------------
    # 9.  Generate natural-language answer
    # ---------------------------------------------------------

    final_answer = await generate_answer(
        question=clarified_question,
        sql=sql,
        rows=execution["rows"]
    )


    # ---------------------------------------------------------
    # 10. Update conversation
    # ---------------------------------------------------------

    update_conversation(
        conversation_id,
        clarification=answer,
        status="completed",
        generated_sql=sql,
        rows=execution["rows"],
        final_answer=final_answer
    )

    # ---------------------------------------------------------
    # 11. Return final result
    # ---------------------------------------------------------

    return {
        "status": "completed",
        "conversation_id": conversation_id,
        "original_question": original_question,
        "clarification": answer,
        "sql": sql,
        "validation": validation,
        "row_count": execution["row_count"],
        "rows": execution["rows"],
        "answer": final_answer,
        "retrieved_schema": sql_result[
            "retrieved_schema"
        ]
    }