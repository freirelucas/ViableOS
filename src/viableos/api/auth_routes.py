"""Authentication routes for ViableOS API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from viableos.api.auth import (
    LoginRequest,
    TokenPayload,
    TokenResponse,
    authenticate,
    require_auth,
)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=TokenResponse)
def login(login: LoginRequest):
    return authenticate(login)


@auth_router.get("/me")
def me(payload: TokenPayload | None = Depends(require_auth)):
    if payload is None:
        return {"authenticated": False}
    return {"authenticated": True, "username": payload.sub, "scopes": payload.scopes}
