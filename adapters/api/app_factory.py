"""Baut die FastAPI-App. CORS-Origins: aus Env (Render-Frontend) ODER localhost-Dev."""
import logging
import os

from fastapi import FastAPI

_logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware

from adapters.api.routes_cockpit import build_router
from adapters.api.run_manager import RunManager

_DEV_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def _allowed_origins(env: str | None) -> list[str]:
    """Sind Origins in AAIA_CORS_ORIGINS (kommagetrennt) gesetzt, gelten NUR diese
    (Produktion); sonst die localhost-Dev-Origins. So steht localhost nie in der
    Prod-Allowlist (leere/whitespace-Eintraege werden ignoriert)."""
    configured = [o.strip() for o in (env or "").split(",") if o.strip()]
    return configured if configured else list(_DEV_ORIGINS)


def create_app(run_manager: RunManager) -> FastAPI:
    if not os.environ.get("AAIA_ACCESS_TOKEN"):
        _logger.warning("AAIA_ACCESS_TOKEN ist leer -> API ist UNGESCHUETZT (nur fuer lokale Entwicklung).")
    app = FastAPI(title="AAIA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(os.environ.get("AAIA_CORS_ORIGINS")),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router(run_manager))
    return app
