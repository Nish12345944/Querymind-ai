from typing import Any

from app.services.embedding_service import (
    generate_embeddings
)

from app.services.vector_store import (
    search_schema
)


DEFAULT_TOP_K = 7
MAX_TOP_K = 15


def retrieve_relevant_schema(
    question: str,
    top_k: int = DEFAULT_TOP_K
) -> list[dict[str, Any]]:

    question = question.strip()

    if not question:
        return []

    top_k = max(
        1,
        min(top_k, MAX_TOP_K)
    )

    query_embedding = generate_embeddings(
        [question]
    )[0]

    results = search_schema(
        query_embedding,
        top_k=top_k
    )

    if not results:
        return []

    documents = results.get(
        "documents",
        [[]]
    )

    metadatas = results.get(
        "metadatas",
        [[]]
    )

    distances = results.get(
        "distances",
        [[]]
    )

    retrieved_documents = (
        documents[0]
        if documents and documents[0]
        else []
    )

    retrieved_metadata = (
        metadatas[0]
        if metadatas and metadatas[0]
        else []
    )

    retrieved_distances = (
        distances[0]
        if distances and distances[0]
        else []
    )

    results_list: list[dict[str, Any]] = []

    for index, document in enumerate(
        retrieved_documents
    ):

        metadata = (
            retrieved_metadata[index]
            if index < len(retrieved_metadata)
            else {}
        )

        distance = (
            retrieved_distances[index]
            if index < len(retrieved_distances)
            else None
        )

        if not isinstance(metadata, dict):
            metadata = {}

        results_list.append({
            "table_name": metadata.get(
                "table_name"
            ),
            "distance": distance,
            "document": document
        })

    return results_list