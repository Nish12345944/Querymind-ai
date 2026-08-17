from app.services.schema_documentation import (
    build_schema_documents
)

from app.services.embedding_service import (
    generate_embeddings
)

from app.services.vector_store import (
    add_schema_documents
)

from app.services.schema_service import (
    invalidate_schema_cache
)


async def index_database_schema():

    invalidate_schema_cache()

    documents = await build_schema_documents()

    if not documents:
        return {
            "indexed_documents": 0
        }

    texts = [
        document["content"]
        for document in documents
    ]

    embeddings = generate_embeddings(
        texts
    )

    add_schema_documents(
        documents,
        embeddings
    )

    return {
        "indexed_documents": len(documents)
    }