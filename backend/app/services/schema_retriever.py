from app.services.embedding_service import (
    generate_embeddings
)

from app.services.vector_store import (
    search_schema
)


def retrieve_relevant_schema(
    question: str,
    top_k: int = 5
):

    query_embedding = generate_embeddings(
        [question]
    )[0]

    results = search_schema(
        query_embedding,
        top_k=top_k
    )

    retrieved_documents = results.get(
        "documents",
        [[]]
    )[0]

    retrieved_metadata = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    results_list = []

    for document, metadata, distance in zip(
        retrieved_documents,
        retrieved_metadata,
        distances
    ):

        results_list.append({
            "table_name": metadata["table_name"],
            "distance": distance,
            "document": document
        })

    return results_list