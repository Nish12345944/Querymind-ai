from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

from app.core.config import settings
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
    *([settings.frontend_url] if settings.frontend_url else []),
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST ID MIDDLEWARE
# ============================================================

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4()),
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


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


# ============================================================
# READINESS ENDPOINT
# ============================================================

@app.get("/ready")
async def ready():
    """
    Readiness probe — returns 200 only when the database
    is reachable and the app is ready to serve traffic.
    Returns 503 otherwise so load balancers / orchestrators
    can withhold traffic until the service is truly ready.
    """

    from fastapi import Response

    try:

        async with AsyncSessionLocal() as session:

            await session.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected",
        }

    except Exception:

        return Response(
            content='{"status":"not_ready","database":"unavailable"}',
            status_code=503,
            media_type="application/json",
        )