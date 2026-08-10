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


async def process_query(
    question: str
):

    # ---------------------------------------------------------
    # 1. Analyze ambiguity
    # ---------------------------------------------------------

    clarification = await analyze_question(
        question
    )

    # ---------------------------------------------------------
    # 2. If ambiguous, create conversation
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
    # 4. Validate SQL
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
    # 5. Stop here for now.
    # SQL execution comes in Step 13.
    # ---------------------------------------------------------

    return {
        "status": "sql_ready",
        "question": question,
        "sql": sql,
        "validation": validation,
        "retrieved_schema": sql_result[
            "retrieved_schema"
        ]
    }


async def process_clarification(
    conversation_id: str,
    answer: str
):

    conversation = get_conversation(
        conversation_id
    )

    if conversation is None:

        return {
            "status": "error",
            "reason": "Conversation not found."
        }

    if conversation["status"] != "awaiting_clarification":

        return {
            "status": "error",
            "reason": "Conversation is not awaiting clarification."
        }

    original_question = conversation[
        "original_question"
    ]

    # ---------------------------------------------------------
    # Combine original question + clarification
    # ---------------------------------------------------------

    clarified_question = (
        f"{original_question}\n\n"
        f"User clarification: {answer}"
    )

    # ---------------------------------------------------------
    # Generate SQL using clarified intent
    # ---------------------------------------------------------

    sql_result = await generate_sql(
        question=clarified_question
    )

    sql = sql_result["sql"]

    # ---------------------------------------------------------
    # Validate SQL
    # ---------------------------------------------------------

    validation = await validate_sql(
        sql
    )

    if not validation["valid"]:

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_rejected"
        )

        return {
            "status": "sql_rejected",
            "reason": validation["reason"],
            "sql": sql
        }

    update_conversation(
        conversation_id,
        clarification=answer,
        status="sql_ready",
        generated_sql=sql
    )

    return {
        "status": "sql_ready",
        "conversation_id": conversation_id,
        "original_question": original_question,
        "clarification": answer,
        "sql": sql,
        "validation": validation
    }