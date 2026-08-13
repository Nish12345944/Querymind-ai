from fastapi import APIRouter
from pydantic import BaseModel, Field

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

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=15,
    )


# ============================================================
# INDEX DATABASE SCHEMA
# ============================================================

@router.post("/index")
async def index_schema():

    result = await index_database_schema()

    return result


# ============================================================
# SEARCH SCHEMA
# ============================================================

@router.post("/search")
async def search_schema_endpoint(
    request: SchemaSearchRequest,
):

    results = retrieve_relevant_schema(
        request.question.strip(),
        request.top_k,
    )

    return {
        "question": request.question.strip(),
        "results": results,
    }