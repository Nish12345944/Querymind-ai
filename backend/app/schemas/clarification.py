from pydantic import BaseModel, Field


class ClarificationOption(BaseModel):
    label: str
    description: str


class ClarificationResult(BaseModel):

    needs_clarification: bool

    reason: str | None = None

    question: str | None = None

    options: list[ClarificationOption] = Field(
        default_factory=list
    )