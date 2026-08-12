from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def init_database():
    from app.db.models import Base

    async with engine.begin() as connection:

        await connection.run_sync(
            Base.metadata.create_all
        )