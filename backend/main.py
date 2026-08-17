from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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

from app.api.query import (
    router as query_router
)

from app.db.database import (
    init_database,
    AsyncSessionLocal,
)

from app.core.logging import configure_logging

configure_logging()


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_database()

    yield


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="QueryMind AI",
    description=(
        "Enterprise Text-to-SQL Copilot "
        "with RAG-powered schema retrieval, "
        "clarification, SQL validation, and "
        "read-only query execution."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://querymind-frontend-cyrb.onrender.com",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    database_router
)

app.include_router(
    schema_router
)

app.include_router(
    schema_documents_router
)

app.include_router(
    rag_router
)

app.include_router(
    sql_router
)

app.include_router(
    validation_router
)

app.include_router(
    clarification_router
)

app.include_router(
    query_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "message": "QueryMind AI is running",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    try:

        async with AsyncSessionLocal() as session:

            await session.execute(
                text("SELECT 1")
            )

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:

        return {
            "status": "degraded",
            "database": "unavailable",
        }