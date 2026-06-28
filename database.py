from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

import ssl

_ssl_ctx = ssl.create_default_context()

# Neon.tech and other managed Postgres providers require SSL.
# We pass ssl= only when the URL contains a known cloud host.
_url = settings.database_url
_connect_args: dict = {}
if any(h in _url for h in ("neon.tech", "supabase", "railway.app", "render.com")):
    _connect_args = {"ssl": _ssl_ctx}

engine = create_async_engine(
    _url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
