from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# Validation Response
# ============================================================

class ValidationChecks(BaseModel):
    syntax: bool
    single_statement: bool
    select_only: bool
    tables: bool
    columns: bool
    join_relationships: bool
    unsupported: bool | None = None


class ValidationResult(BaseModel):
    valid: bool
    reason: str
    checks: ValidationChecks


# ============================================================
# Query Response
# ============================================================

class QueryResponse(BaseModel):
    status: str
    question: str

    sql: str | None = None

    validation: ValidationResult | None = None

    row_count: int | None = None

    rows: list[dict[str, Any]] = Field(
        default_factory=list
    )

    answer: str | None = None

    retrieved_schema: list[dict[str, Any]] = Field(
        default_factory=list
    )

    reason: str | None = None

    error: str | None = None

    conversation_id: str | None = None

    clarification: str | None = None

    original_question: str | None = None

    options: list[dict[str, Any]] = Field(
        default_factory=list
    )


# ============================================================
# Clarification Response
# ============================================================

class ClarificationResponse(BaseModel):
    status: str

    conversation_id: str

    original_question: str | None = None

    clarification: str | None = None

    sql: str | None = None

    validation: ValidationResult | None = None

    row_count: int | None = None

    rows: list[dict[str, Any]] = Field(
        default_factory=list
    )

    answer: str | None = None

    retrieved_schema: list[dict[str, Any]] = Field(
        default_factory=list
    )

    reason: str | None = None

    error: str | None = None