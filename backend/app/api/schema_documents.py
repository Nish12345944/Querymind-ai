from fastapi import APIRouter

from app.services.schema_documentation import (
    build_schema_documents
)


router = APIRouter(
    prefix="/schema-documents",
    tags=["Schema Documents"]
)


@router.get("/")
async def get_schema_documents():

    documents = await build_schema_documents()

    return {
        "document_count": len(documents),
        "documents": documents
    }