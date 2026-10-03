"""Liveness and readiness. NFR-6: readiness reports a degraded dependency
rather than failing, because retrieval is useful during an LLM outage."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.db import get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        async with get_sessionmaker()() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — readiness reports, never raises
        checks["database"] = f"error: {type(exc).__name__}"

    from app.ingestion.worker import worker_status

    checks["ingestion_worker"] = worker_status()
    ready = checks["database"] == "ok"
    return {"status": "ready" if ready else "degraded", "checks": checks}
