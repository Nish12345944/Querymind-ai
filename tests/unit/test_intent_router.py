from app.services.intent_router import (
    IntentType,
    route_intent
)


def test_clear_intent():
    result = route_intent({
        "intent": "CLEAR"
    })

    assert result == IntentType.CLEAR


def test_ambiguous_intent():
    result = route_intent({
        "intent": "AMBIGUOUS"
    })

    assert result == IntentType.AMBIGUOUS


def test_unsupported_intent():
    result = route_intent({
        "intent": "UNSUPPORTED"
    })

    assert result == IntentType.UNSUPPORTED


def test_lowercase_intent():
    result = route_intent({
        "intent": "clear"
    })

    assert result == IntentType.CLEAR


def test_whitespace_intent():
    result = route_intent({
        "intent": "  CLEAR  "
    })

    assert result == IntentType.CLEAR


def test_unknown_intent_fails_closed():
    result = route_intent({
        "intent": "UNKNOWN"
    })

    assert result == IntentType.AMBIGUOUS


def test_missing_intent_fails_closed():
    result = route_intent({})

    assert result == IntentType.AMBIGUOUS


def test_invalid_input_fails_closed():
    result = route_intent(None)

    assert result == IntentType.AMBIGUOUS