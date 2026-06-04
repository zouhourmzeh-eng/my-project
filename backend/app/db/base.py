from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_async_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        url = "sqlite+aiosqlite://" + url[len("sqlite://"):]
    return url


_db_url = _normalize_async_url(settings.DATABASE_URL)
_engine_kwargs: dict = {"future": True}
if _db_url.startswith("postgresql"):
    _engine_kwargs["pool_pre_ping"] = True
    if "?" in _db_url and "sslmode=" in _db_url:
        # asyncpg doesn't accept sslmode query param; strip it.
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
        parts = urlsplit(_db_url)
        q = [(k, v) for k, v in parse_qsl(parts.query) if k != "sslmode"]
        _db_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))

engine = create_async_engine(_db_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
