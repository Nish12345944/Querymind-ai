from typing import Any

from app.services.embedding_service import (
    generate_embeddings
)

from app.services.vector_store import (
    search_schema
)


# ============================================================
# Configuration
# ============================================================

DEFAULT_TOP_K = 7
MAX_TOP_K = 15


# ============================================================
# Retrieve relevant schema
# ============================================================

def retrieve_relevant_schema(
    question: str,
    top_k: int = DEFAULT_TOP_K
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant database schema documents
    for a natural-language question.

    The function is intentionally synchronous because the
    current embedding and vector-store implementations are
    synchronous.
    """

    question = question.strip()

    if not question:
        return []

    # --------------------------------------------------------
    # Protect against unreasonable top_k values
    # --------------------------------------------------------

    top_k = max(
        1,
        min(top_k, MAX_TOP_K)
    )

    # --------------------------------------------------------
    # Generate query embedding
    # --------------------------------------------------------

    query_embedding = generate_embeddings(
        [question]
    )[0]

    # --------------------------------------------------------
    # Search vector store
    # --------------------------------------------------------

    results = search_schema(
        query_embedding,
        top_k=top_k
    )

    if not results:
        return []

    # --------------------------------------------------------
    # Safely extract vector-store results
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Build normalized result
    # --------------------------------------------------------

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

        table_name = metadata.get(
            "table_name"
        )

        results_list.append(
            {
                "table_name": table_name,
                "distance": distance,
                "document": document
            }
        )

    return results_list