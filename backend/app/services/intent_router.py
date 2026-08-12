from enum import Enum


# ============================================================
# INTENT TYPES
# ============================================================

class IntentType(str, Enum):
    CLEAR = "CLEAR"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"


# ============================================================
# ROUTER
# ============================================================

def route_intent(intent: dict) -> IntentType:
    """
    Convert the intent classifier response into a safe,
    deterministic routing decision.
    """

    if not isinstance(intent, dict):
        return IntentType.AMBIGUOUS

    raw_intent = intent.get(
        "intent",
        ""
    )

    if not isinstance(
        raw_intent,
        str
    ):
        return IntentType.AMBIGUOUS

    normalized = raw_intent.upper().strip()

    if normalized == "CLEAR":
        return IntentType.CLEAR

    if normalized == "AMBIGUOUS":
        return IntentType.AMBIGUOUS

    if normalized == "UNSUPPORTED":
        return IntentType.UNSUPPORTED

    # Fail closed.
    #
    # Never allow an unknown LLM response to proceed
    # into SQL generation.
    return IntentType.AMBIGUOUS