import logging
import time
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

from app.services.query_history_service import (
    save_query_history
)

from app.services.intent_router import (
    IntentType,
    route_intent
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# LOGGING HELPER
# ============================================================

def _log_stage(
    request_id: str,
    stage: str,
    status: str,
    start_time: float,
    **extra
):
    """
    Log one pipeline stage with execution time.

    This helper intentionally avoids logging SQL results,
    database rows, API keys, or other potentially sensitive
    information.
    """

    duration_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2
    )

    log_data = {
        "request_id": request_id,
        "stage": stage,
        "status": status,
        "duration_ms": duration_ms
    }

    log_data.update(extra)

    logger.info(
        "QueryMind pipeline | %s",
        log_data
    )


# ============================================================
# SAVE QUERY HISTORY
# ============================================================

async def _save_history(
    *,
    request_id: str,
    question: str,
    sql: str | None = None,
    status: str,
    row_count: int = 0,
    answer: str | None = None,
    error: str | None = None,
    duration_ms: float | None = None,
):
    """
    Persist query execution history.

    History persistence must never break the main query pipeline.
    """

    try:

        await save_query_history(
            request_id=request_id,
            question=question,
            sql=sql,
            status=status,
            row_count=row_count,
            answer=answer,
            error=error,
            duration_ms=duration_ms,
        )

    except Exception:

        logger.exception(
            "Failed to persist query history | request_id=%s",
            request_id,
        )


# ============================================================
# INTERNAL QUERY PIPELINE
# ============================================================

async def _process_query(
    question: str
):
    """
    Main QueryMind query pipeline.

    Flow:

    User question
          ↓
    Intent Classification
          ↓
    ┌──────────────┬──────────────┬──────────────┐
    CLEAR          AMBIGUOUS      UNSUPPORTED
      │                │               │
      ↓                ↓               ↓
    SQL             Clarify          Reject
      │
      ↓
    Schema RAG
      │
      ↓
    Groq
      │
      ↓
    SQL Validation
      │
      ↓
    Read-only PostgreSQL
      │
      ↓
    Natural-language answer
    """

    request_id = str(uuid.uuid4())

    logger.info(
        "QueryMind request started | request_id=%s",
        request_id
    )

    # ========================================================
    # 1. Analyze user intent
    # ========================================================

    stage_start = time.perf_counter()

    try:

        intent = await analyze_question(
            question
        )

        # ----------------------------------------------------
        # Route intent through centralized Intent Router
        # ----------------------------------------------------

        intent_type = route_intent(
            intent
        )

        _log_stage(
            request_id,
            "intent_analysis",
            "success",
            stage_start,
            intent=intent_type.value
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "intent_analysis",
            "failed",
            stage_start,
            error=str(exc)
        )

        return {
            "status": "error",
            "question": question,
            "reason": str(exc)
        }

    # ========================================================
    # 2. UNSUPPORTED
    # ========================================================

    if intent_type == IntentType.UNSUPPORTED:

        _log_stage(
            request_id,
            "intent_analysis",
            "unsupported",
            stage_start
        )

        return {
            "status": "unsupported",
            "question": question,
            "reason": intent.get(
                "reason",
                "The requested information "
                "is not available in the database."
            )
        }

    # ========================================================
    # 3. AMBIGUOUS
    # ========================================================

    if intent_type == IntentType.AMBIGUOUS:

        conversation_id = str(
            uuid.uuid4()
        )

        create_conversation(
            conversation_id=conversation_id,
            question=question
        )

        update_conversation(
            conversation_id,
            clarification=intent,
            status="awaiting_clarification"
        )

        logger.info(
            "QueryMind clarification required | "
            "request_id=%s conversation_id=%s",
            request_id,
            conversation_id
        )

        return {
            "status": "clarification_required",
            "conversation_id": conversation_id,
            "question": intent.get(
                "question"
            ),
            "options": intent.get(
                "options",
                []
            ),
            "reason": intent.get(
                "reason"
            )
        }

    # ========================================================
    # 4. CLEAR
    # ========================================================

    if intent_type != IntentType.CLEAR:

        logger.warning(
            "QueryMind unknown intent | request_id=%s intent=%s",
            request_id,
            intent_type
        )

        return {
            "status": "error",
            "question": question,
            "reason": (
                "Unable to determine the "
                "intent of the question."
            )
        }

    # ========================================================
    # 5. Generate SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        sql_result = await generate_sql(
            question=question
        )

        _log_stage(
            request_id,
            "sql_generation",
            "success",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "sql_generation",
            "failed",
            stage_start,
            error=str(exc)
        )

        return {
            "status": "sql_generation_failed",
            "question": question,
            "error": str(exc)
        }

    # ========================================================
    # 5.1 Validate SQL generator response structure
    # ========================================================

    if not isinstance(
        sql_result,
        dict
    ):

        logger.error(
            "SQL generator returned invalid response | "
            "request_id=%s",
            request_id
        )

        return {
            "status": "sql_generation_failed",
            "question": question,
            "error": (
                "SQL generator returned "
                "an invalid response."
            )
        }

    sql = sql_result.get(
        "sql"
    )

    if not sql:

        logger.error(
            "SQL generator returned no SQL | request_id=%s",
            request_id
        )

        return {
            "status": "sql_generation_failed",
            "question": question,
            "error": (
                "SQL generator did not "
                "return SQL."
            )
        }

    # ========================================================
    # 6. Handle unsupported SQL generated by model
    # ========================================================

    if sql.strip().upper() == "UNSUPPORTED":

        logger.info(
            "SQL generation determined query unsupported | "
            "request_id=%s",
            request_id
        )

        return {
            "status": "unsupported",
            "question": question,
            "reason": (
                "The database schema does not "
                "contain enough information to "
                "answer this question."
            )
        }

    # ========================================================
    # 7. Validate generated SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        validation = await validate_sql(
            sql
        )

        _log_stage(
            request_id,
            "sql_validation",
            "success"
            if validation.get("valid")
            else "rejected",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "sql_validation",
            "failed",
            stage_start,
            error=str(exc)
        )

        return {
            "status": "sql_validation_failed",
            "question": question,
            "sql": sql,
            "error": str(exc)
        }

    # ========================================================
    # 8. Reject invalid SQL
    # ========================================================

    if not validation.get(
        "valid",
        False
    ):

        return {
            "status": "sql_rejected",
            "question": question,
            "reason": validation.get(
                "reason",
                "SQL validation failed."
            ),
            "sql": sql,
            "validation": validation
        }

    # ========================================================
    # 9. Execute validated SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        execution = await execute_readonly_sql(
            sql
        )

        _log_stage(
            request_id,
            "sql_execution",
            "success"
            if execution.get("success")
            else "failed",
            stage_start,
            row_count=execution.get(
                "row_count",
                0
            )
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "sql_execution",
            "failed",
            stage_start,
            error=str(exc)
        )

        return {
            "status": "execution_failed",
            "question": question,
            "sql": sql,
            "validation": validation,
            "error": str(exc)
        }

    # ========================================================
    # 10. Handle execution failure
    # ========================================================

    if not execution.get(
        "success",
        False
    ):

        return {
            "status": "execution_failed",
            "question": question,
            "sql": sql,
            "validation": validation,
            "error": execution.get(
                "error",
                "Database execution failed."
            )
        }

    # ========================================================
    # 11. Generate natural-language answer
    # ========================================================

    stage_start = time.perf_counter()

    try:

        answer = await generate_answer(
            question=question,
            sql=sql,
            rows=execution.get(
                "rows",
                []
            )
        )

        _log_stage(
            request_id,
            "answer_generation",
            "success",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "answer_generation",
            "failed",
            stage_start,
            error=str(exc)
        )

        return {
            "status": "answer_generation_failed",
            "question": question,
            "sql": sql,
            "validation": validation,
            "row_count": execution.get(
                "row_count",
                0
            ),
            "rows": execution.get(
                "rows",
                []
            ),
            "error": str(exc)
        }

    # ========================================================
    # 12. Return final result
    # ========================================================

    logger.info(
        "QueryMind request completed | "
        "request_id=%s row_count=%s",
        request_id,
        execution.get(
            "row_count",
            0
        )
    )

    return {
        "status": "query_executed",
        "question": question,
        "sql": sql,
        "validation": validation,
        "row_count": execution.get(
            "row_count",
            0
        ),
        "rows": execution.get(
            "rows",
            []
        ),
        "answer": answer,
        "retrieved_schema": sql_result.get(
            "retrieved_schema",
            []
        )
    }


# ============================================================
# PUBLIC QUERY ENTRYPOINT WITH HISTORY
# ============================================================

async def process_query(
    question: str
):
    """
    Public query entrypoint.

    Executes the existing QueryMind pipeline and persists
    the final pipeline outcome to query_history.
    """

    request_id = str(
        uuid.uuid4()
    )

    start_time = time.perf_counter()

    try:

        result = await _process_query(
            question
        )

    except Exception as exc:

        duration_ms = round(
            (
                time.perf_counter()
                - start_time
            ) * 1000,
            2
        )

        await _save_history(
            request_id=request_id,
            question=question,
            status="error",
            error=str(exc),
            duration_ms=duration_ms,
        )

        raise

    duration_ms = round(
        (
            time.perf_counter()
            - start_time
        ) * 1000,
        2
    )

    await _save_history(
        request_id=request_id,
        question=question,
        sql=result.get("sql"),
        status=result.get(
            "status",
            "unknown"
        ),
        row_count=result.get(
            "row_count"
        ) or 0,
        answer=result.get(
            "answer"
        ),
        error=result.get(
            "error"
        ),
        duration_ms=duration_ms,
    )

    return result


# ============================================================
# PROCESS CLARIFICATION
# ============================================================

async def process_clarification(
    conversation_id: str,
    answer: str
):
    """
    Continue a query after the user answers
    a clarification question.
    """

    request_id = str(
        uuid.uuid4()
    )

    logger.info(
        "QueryMind clarification request started | "
        "request_id=%s conversation_id=%s",
        request_id,
        conversation_id
    )

    # ========================================================
    # 1. Retrieve conversation
    # ========================================================

    conversation = get_conversation(
        conversation_id
    )

    if conversation is None:

        logger.warning(
            "Conversation not found | "
            "request_id=%s conversation_id=%s",
            request_id,
            conversation_id
        )

        return {
            "status": "error",
            "reason": "Conversation not found."
        }

    # ========================================================
    # 2. Check conversation state
    # ========================================================

    if conversation.get(
        "status"
    ) != "awaiting_clarification":

        return {
            "status": "error",
            "reason": (
                "Conversation is not awaiting "
                "clarification."
            )
        }

    # ========================================================
    # 3. Get original question
    # ========================================================

    original_question = conversation.get(
        "original_question"
    )

    if not original_question:

        return {
            "status": "error",
            "reason": (
                "Original question was not "
                "found in the conversation."
            )
        }

    # ========================================================
    # 4. Combine original question + clarification
    # ========================================================

    clarified_question = (
        f"{original_question}\n\n"
        f"User clarification: {answer}"
    )

    # ========================================================
    # 5. Generate SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        sql_result = await generate_sql(
            question=clarified_question
        )

        _log_stage(
            request_id,
            "clarification_sql_generation",
            "success",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "clarification_sql_generation",
            "failed",
            stage_start,
            error=str(exc)
        )

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_generation_failed"
        )

        return {
            "status": "sql_generation_failed",
            "conversation_id": conversation_id,
            "error": str(exc)
        }

    # ========================================================
    # 5.1 Validate SQL generator response
    # ========================================================

    if not isinstance(
        sql_result,
        dict
    ):

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_generation_failed"
        )

        return {
            "status": "sql_generation_failed",
            "conversation_id": conversation_id,
            "error": (
                "SQL generator returned "
                "an invalid response."
            )
        }

    sql = sql_result.get(
        "sql"
    )

    if not sql:

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_generation_failed"
        )

        return {
            "status": "sql_generation_failed",
            "conversation_id": conversation_id,
            "error": (
                "SQL generator did not "
                "return SQL."
            )
        }

    # ========================================================
    # 6. Handle unsupported SQL
    # ========================================================

    if sql.strip().upper() == "UNSUPPORTED":

        update_conversation(
            conversation_id,
            clarification=answer,
            status="unsupported",
            generated_sql=sql
        )

        return {
            "status": "unsupported",
            "conversation_id": conversation_id,
            "reason": (
                "The database schema does not "
                "contain enough information to "
                "answer this question."
            )
        }

    # ========================================================
    # 7. Validate generated SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        validation = await validate_sql(
            sql
        )

        _log_stage(
            request_id,
            "clarification_sql_validation",
            "success"
            if validation.get("valid")
            else "rejected",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "clarification_sql_validation",
            "failed",
            stage_start,
            error=str(exc)
        )

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_validation_failed",
            generated_sql=sql
        )

        return {
            "status": "sql_validation_failed",
            "conversation_id": conversation_id,
            "sql": sql,
            "error": str(exc)
        }

    # ========================================================
    # 8. Reject invalid SQL
    # ========================================================

    if not validation.get(
        "valid",
        False
    ):

        update_conversation(
            conversation_id,
            clarification=answer,
            status="sql_rejected",
            generated_sql=sql
        )

        return {
            "status": "sql_rejected",
            "conversation_id": conversation_id,
            "reason": validation.get(
                "reason",
                "SQL validation failed."
            ),
            "sql": sql,
            "validation": validation
        }

    # ========================================================
    # 9. Execute validated SQL
    # ========================================================

    stage_start = time.perf_counter()

    try:

        execution = await execute_readonly_sql(
            sql
        )

        _log_stage(
            request_id,
            "clarification_sql_execution",
            "success"
            if execution.get("success")
            else "failed",
            stage_start,
            row_count=execution.get(
                "row_count",
                0
            )
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "clarification_sql_execution",
            "failed",
            stage_start,
            error=str(exc)
        )

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
            "error": str(exc)
        }

    # ========================================================
    # 10. Handle execution failure
    # ========================================================

    if not execution.get(
        "success",
        False
    ):

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
            "error": execution.get(
                "error",
                "Database execution failed."
            )
        }

    # ========================================================
    # 11. Generate final answer
    # ========================================================

    stage_start = time.perf_counter()

    try:

        final_answer = await generate_answer(
            question=clarified_question,
            sql=sql,
            rows=execution.get(
                "rows",
                []
            )
        )

        _log_stage(
            request_id,
            "clarification_answer_generation",
            "success",
            stage_start
        )

    except Exception as exc:

        _log_stage(
            request_id,
            "clarification_answer_generation",
            "failed",
            stage_start,
            error=str(exc)
        )

        update_conversation(
            conversation_id,
            clarification=answer,
            status="answer_generation_failed",
            generated_sql=sql,
            rows=execution.get(
                "rows",
                []
            )
        )

        return {
            "status": "answer_generation_failed",
            "conversation_id": conversation_id,
            "sql": sql,
            "validation": validation,
            "row_count": execution.get(
                "row_count",
                0
            ),
            "rows": execution.get(
                "rows",
                []
            ),
            "error": str(exc)
        }

    # ========================================================
    # 12. Update conversation
    # ========================================================

    update_conversation(
        conversation_id,
        clarification=answer,
        status="completed",
        generated_sql=sql,
        rows=execution.get(
            "rows",
            []
        ),
        final_answer=final_answer
    )

    # ========================================================
    # 13. Return final result
    # ========================================================

    logger.info(
        "QueryMind clarification completed | "
        "request_id=%s conversation_id=%s row_count=%s",
        request_id,
        conversation_id,
        execution.get(
            "row_count",
            0
        )
    )

    return {
        "status": "query_executed",
        "conversation_id": conversation_id,
        "original_question": original_question,
        "clarification": answer,
        "sql": sql,
        "validation": validation,
        "row_count": execution.get(
            "row_count",
            0
        ),
        "rows": execution.get(
            "rows",
            []
        ),
        "answer": final_answer,
        "retrieved_schema": sql_result.get(
            "retrieved_schema",
            []
        )
    }