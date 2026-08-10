from fastapi import FastAPI

from app.api.database import router as database_router
from app.api.schema import router as schema_router
from app.api.rag import router as rag_router
from app.api.schema_documents import (
    router as schema_documents_router
)
from app.api.sql import router as sql_router
from app.api.validation import (
    router as validation_router
)
from app.api.clarification import (
    router as clarification_router
)



app = FastAPI(
    title="QueryMind AI",
    description="Enterprise Text-to-SQL Copilot with Clarification Engine",
    version="0.1.0"
)


app.include_router(database_router)
app.include_router(schema_router)
app.include_router(schema_documents_router)
app.include_router(rag_router)
app.include_router(sql_router)
app.include_router(validation_router)
app.include_router(clarification_router)


@app.get("/")
async def root():
    return {
        "message": "QueryMind AI is running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }