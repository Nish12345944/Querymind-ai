from typing import Any


conversations: dict[str, dict[str, Any]] = {}


def create_conversation(
    conversation_id: str,
    question: str
):
    conversations[conversation_id] = {
        "original_question": question,
        "clarification": None,
        "status": "pending"
    }


def get_conversation(
    conversation_id: str
):
    return conversations.get(conversation_id)


def update_conversation(
    conversation_id: str,
    **updates
):
    if conversation_id not in conversations:
        return None

    conversations[conversation_id].update(
        updates
    )

    return conversations[conversation_id]


def delete_conversation(
    conversation_id: str
):
    conversations.pop(
        conversation_id,
        None
    )