"""Baut die FastAPI-App. Dev-CORS fuer das lokale Frontend (Vite/CRA)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.api.routes_cockpit import build_router
from adapters.api.run_manager import RunManager


def create_app(run_manager: RunManager) -> FastAPI:
    app = FastAPI(title="AAIA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router(run_manager))
    return app
