import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, dashboard, documents, messages, notifications, processes, projects, uploads, ws, ai, regulatory
from app.core.config import settings
from app.db.base import Base, engine
from app.models import models  # noqa: F401  (register models)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

app = FastAPI(
    title="QMS / SMQ Document Management API",
    version="1.0.0",
    description="Quality Management System backend — projects, processes, documents, chat.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/api/health", tags=["meta"])
async def health():
    return {"status": "ok"}


api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(projects.router, prefix=api_prefix)
app.include_router(processes.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(messages.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
from app.api import auth, dashboard, documents, messages, notifications, processes, projects, uploads, ws, ai, regulatory, gap_analysis
app.include_router(ai.router, prefix=api_prefix)
app.include_router(regulatory.router, prefix=api_prefix + "/regulatory-watch", tags=["regulatory"])
app.include_router(gap_analysis.router, prefix=api_prefix + "/gap-analysis", tags=["gap_analysis"])
app.include_router(ws.router, prefix=api_prefix)

@app.get("/api/storage/{file_key:path}", tags=["storage"])
async def serve_file(file_key: str):
    from app.services.storage import ensure_local_file
    import asyncio
    loop = asyncio.get_running_loop()
    local_path = await loop.run_in_executor(None, ensure_local_file, file_key)
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(local_path)

# Serve local storage in dev if S3 is not used
app.mount("/api/storage", StaticFiles(directory="storage"), name="storage")


from app.modules.regulatory_watch.workers import start_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    # Trigger an immediate background fetch at startup to ensure latest updates are loaded
    import asyncio
    from app.modules.regulatory_watch.workers import fetch_regulatory_updates
    asyncio.create_task(fetch_regulatory_updates())


async def _ensure_columns(conn) -> None:
    def _sync(c):
        dialect = c.dialect.name

        def cols(table: str) -> set[str]:
            if dialect == "sqlite":
                return {r[1] for r in c.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            return {r[0] for r in c.exec_driver_sql(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
            ).fetchall()}

        proj = cols("projects")
        if "is_validated" not in proj:
            c.exec_driver_sql(
                "ALTER TABLE projects ADD COLUMN is_validated BOOLEAN NOT NULL DEFAULT 0"
                if dialect == "sqlite"
                else "ALTER TABLE projects ADD COLUMN is_validated BOOLEAN NOT NULL DEFAULT FALSE"
            )
        if "validated_at" not in proj:
            c.exec_driver_sql("ALTER TABLE projects ADD COLUMN validated_at TIMESTAMP NULL")

        proc = cols("processes")
        for col in ("process_owner",):
            if col not in proc:
                c.exec_driver_sql(f"ALTER TABLE processes ADD COLUMN {col} VARCHAR(255) NOT NULL DEFAULT ''")
        for col in ("objective", "inputs", "outputs", "activities", "resources",
                    "kpis", "risks_opportunities", "related_documents"):
            if col not in proc:
                c.exec_driver_sql(f"ALTER TABLE processes ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
    await conn.run_sync(_sync)


_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    _ASSETS_DIR = _FRONTEND_DIST / "assets"
    if _ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "ws/")):
            raise HTTPException(status_code=404)
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
