"""JWT authentication for the ViableOS API.

Environment variables:
  JWT_SECRET_KEY  — HMAC key for signing tokens (default: dev-only fallback)
  JWT_ALGORITHM   — algorithm (default: HS256)
  JWT_EXPIRE_MINUTES — token lifetime (default: 480 = 8h)
  USERS_JSON      — path to JSON file with users: {"username": {"password_hash": "...", "scopes": [...]}}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pydantic import BaseModel

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "viableos-dev-insecure-change-me")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))
USERS_PATH = os.environ.get("USERS_JSON", "")

bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str
    scopes: list[str]
    exp: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _load_users() -> dict[str, dict[str, Any]]:
    if USERS_PATH and os.path.isfile(USERS_PATH):
        with open(USERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def create_token(username: str, scopes: list[str] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"sub": username, "scopes": scopes or [], "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def authenticate(login: LoginRequest) -> TokenResponse:
    users = _load_users()
    user = users.get(login.username)
    if not user or not verify_password(login.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_token(login.username, user.get("scopes", []))
    return TokenResponse(access_token=token)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> TokenPayload | None:
    """Dependency that returns TokenPayload if valid, or None if no auth header."""
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


async def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> TokenPayload:
    """Dependency that requires a valid token with admin scope."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    if "admin" not in payload.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")
    return payload


async def require_s5(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> TokenPayload:
    """R5 (S5 é humano) como imposição técnica, não convenção.

    Veredito sobre decisões e resposta a sinais algêdonicos exigem humano
    autenticado com escopo admin ou cda:s5. A identidade (`sub`) registrada
    na decisão vem daqui — nunca do payload spoofável.
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação S5 necessária (R5)")
    payload = decode_token(credentials.credentials)
    if not ({"admin", "cda:s5"} & set(payload.scopes)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Escopo S5 necessário (admin ou cda:s5)")
    return payload
