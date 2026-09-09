"""FastAPI application for ViableOS."""

from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from viableos.api.routes import router
from viableos.api.chat_routes import chat_router
from viableos.api.ops_routes import ops_router
from viableos.api.simulation_routes import sim_router
from viableos.api.tr_routes import tr_router
from viableos.api.auth_routes import auth_router
from viableos.api.cda_routes import cda_router
from viableos.api.dev_routes import dev_router
from viableos.api.agente_chat_routes import agente_chat_router
from viableos.api.ws_routes import ws_router
from viableos.cda.seed import seed_all
from viableos.cda.recursao.clock import sistema_clocks, FrequenciaClock

app = FastAPI(
    title="ViableOS API",
    version="0.3.0rc1",
    description="REST API for the ViableOS multi-agent design tool",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://10.100.33.75:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(chat_router)
app.include_router(ops_router)
app.include_router(sim_router)
app.include_router(tr_router)
app.include_router(auth_router)
app.include_router(cda_router)
app.include_router(dev_router)
app.include_router(agente_chat_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup_all() -> None:
    from viableos.cda import provenancia
    from viableos.cda.budget_monitor import budget_monitor
    from viableos.cda.fabrica import fabrica

    # Gatilho R4-2 conectado: monitor de orçamento dispara no canal da raiz.
    if fabrica.raiz:
        budget_monitor.definir_canal(fabrica.raiz.canal)
        orcamento = float(os.environ.get("CDA_ORCAMENTO_USD", "0") or "0")
        if orcamento > 0:
            budget_monitor.definir_orcamento("CDA", orcamento)

    if provenancia.ledger.habilitado:
        # Regra 2 do handout: intenção persiste fora do runner —
        # estado volta por replay do ledger; seed só em modo demo.
        provenancia.ledger.reconstruir(raiz=fabrica.raiz)
    else:
        seed_all()

    # Clocks iniciam em background (async def garante event loop ativo)
    asyncio.create_task(sistema_clocks.iniciar_todos())

@app.get("/health")
def health_check() -> dict[str, str]:
    from viableos.cda import provenancia
    return {
        "status": "ok",
        "version": "0.3.0rc1",
        "modo": "ledger" if provenancia.ledger.habilitado else "demo",
    }
