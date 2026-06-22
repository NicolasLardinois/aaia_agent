"""Baut die FastAPI-App. CORS-Origins: localhost-Dev + optional aus Env (Render-Frontend)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.api.routes_cockpit import build_router
from adapters.api.run_manager import RunManager

_DEV_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def _allowed_origins(env: str | None) -> list[str]:
    """Dev-Origins + optionale, kommagetrennte Origins aus AAIA_CORS_ORIGINS (leere ignoriert)."""
    extra = [o.strip() for o in (env or "").split(",") if o.strip()]
    return _DEV_ORIGINS + extra


def create_app(run_manager: RunManager) -> FastAPI:
    app = FastAPI(title="AAIA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(os.environ.get("AAIA_CORS_ORIGINS")),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router(run_manager))
    return app
