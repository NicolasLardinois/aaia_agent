"""Gemeinsames Zugangs-Token (Shared Secret) fuer die API.

Leeres AAIA_ACCESS_TOKEN -> Auth deaktiviert (nur lokale Entwicklung).
Konstanter Zeitvergleich gegen Timing-Angriffe.
"""
import os
import secrets

from fastapi import Header, HTTPException, status


def _expected_token() -> str:
    return os.environ.get("AAIA_ACCESS_TOKEN", "")


def token_valid(provided: str | None) -> bool:
    expected = _expected_token()
    if not expected:
        return True  # kein Token gesetzt -> Auth aus (nur lokal sinnvoll)
    if not provided:
        return False
    return secrets.compare_digest(provided, expected)


def _bearer(authorization: str | None) -> str | None:
    # "Bearer <token>" -> "<token>"
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def require_token(authorization: str | None = Header(default=None)) -> None:
    """FastAPI-Dependency: prueft den Bearer-Token, sonst 401."""
    if not token_valid(_bearer(authorization)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges oder fehlendes Token",
        )
