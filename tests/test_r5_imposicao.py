"""R5 (S5 é humano) como imposição técnica — testes da dependência require_s5.

Antes da revisão de coerência 2026-09-03, resolver decisão não exigia
autenticação e `resolvido_por` vinha do payload (spoofável).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from viableos.api.auth import create_token, require_s5


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_sem_token_exige_autenticacao():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_s5(None))
    assert exc.value.status_code == 401
    assert "R5" in exc.value.detail


def test_token_sem_escopo_s5_recusado():
    token = create_token("visitante", scopes=["tr:write"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_s5(_creds(token)))
    assert exc.value.status_code == 403


def test_escopo_admin_aceito():
    token = create_token("diretora@ipea", scopes=["admin"])
    payload = asyncio.run(require_s5(_creds(token)))
    assert payload.sub == "diretora@ipea"


def test_escopo_cda_s5_aceito():
    token = create_token("substituta", scopes=["cda:s5"])
    payload = asyncio.run(require_s5(_creds(token)))
    assert payload.sub == "substituta"


def test_token_expirado_recusado():
    from datetime import datetime, timedelta, timezone

    import jwt as pyjwt

    from viableos.api import auth as auth_mod

    payload = {
        "sub": "expirada",
        "scopes": ["admin"],
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = pyjwt.encode(payload, auth_mod.SECRET_KEY, algorithm=auth_mod.ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_s5(_creds(token)))
    assert exc.value.status_code == 401
