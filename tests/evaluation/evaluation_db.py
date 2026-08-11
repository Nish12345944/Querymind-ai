import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BACKEND_DIR = PROJECT_ROOT / "backend"

ENV_FILE = BACKEND_DIR / ".env"


# ============================================================
# Make backend importable
# ============================================================

sys.path.insert(
    0,
    str(BACKEND_DIR)
)


# ============================================================
# Load environment variables
# ============================================================

load_dotenv(
    ENV_FILE
)


# ============================================================
# Database URL
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:

    raise RuntimeError(
        "DATABASE_URL was not found in "
        "backend/.env"
    )


# ============================================================
# Execute evaluation SQL
# ============================================================

async def execute_evaluation_sql(
    sql: str
):
    """
    Execute ground-truth SQL using a dedicated
    short-lived evaluation database engine.

    A new engine is created for every evaluation call
    to prevent asyncpg connections from being reused
    across different asyncio event loops.
    """

    evaluation_engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True
    )

    try:

        async with evaluation_engine.connect() as connection:

            result = await connection.execute(
                text(sql)
            )

            rows = result.mappings().all()

            return [
                dict(row)
                for row in rows
            ]

    finally:

        await evaluation_engine.dispose()


# ============================================================
# Synchronous wrapper
# ============================================================

def execute_sql(
    sql: str
):
    """
    Synchronous interface used by evaluation_runner.py.

    Each call gets its own asyncio event loop and its own
    short-lived SQLAlchemy engine, preventing event-loop
    conflicts with asyncpg.
    """

    return asyncio.run(
        execute_evaluation_sql(sql)
    )