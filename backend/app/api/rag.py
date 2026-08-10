from fastapi import APIRouter
from pydantic import BaseModel

from app.services.schema_indexer import (
    index_database_schema
)

from app.services.schema_retriever import (
    retrieve_relevant_schema
)


router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)


class SchemaSearchRequest(BaseModel):

    question: str

    top_k: int = 5


@router.post("/index")
async def index_schema():

    result = await index_database_schema()

    return result


@router.post("/search")
async def search_schema_endpoint(
    request: SchemaSearchRequest
):

    results = retrieve_relevant_schema(
        request.question,
        request.top_k
    )

    return {
        "question": request.question,
        "results": results
    }