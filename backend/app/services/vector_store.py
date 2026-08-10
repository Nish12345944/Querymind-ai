import chromadb


CHROMA_PATH = "./vector_store"

COLLECTION_NAME = "novamart_schema"


client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={
        "description": "NovaMart database schema documents"
    }
)


def add_schema_documents(
    documents: list[dict],
    embeddings: list[list[float]]
):

    ids = [
        f"table_{document['table_name']}"
        for document in documents
    ]

    texts = [
        document["content"]
        for document in documents
    ]

    metadatas = [
        {
            "table_name": document["table_name"]
        }
        for document in documents
    ]

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )


def search_schema(
    query_embedding: list[float],
    top_k: int = 5
):

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results