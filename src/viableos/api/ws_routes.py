"""SSE — eventos em tempo real da CDA para a Sala de Operação.

Eventos emitidos:
  - heartbeat:  tick de clock de cada nível
  - decisao:     nova decisão pendente
  - sinal:       novo sinal algêdonico
  - bargain:     nova negociação
  - status:      status agregado (a cada 30s)
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from viableos.cda.fabrica import fabrica
from viableos.cda.algedonic import GravidadeSinal
from viableos.cda.agente import StatusAgente
from viableos.cda.recursao.clock import sistema_clocks
from viableos.cda.recursao.bargain import protocolo_bargain

ws_router = APIRouter(prefix="/api/cda", tags=["cda-sse"])

# Controle de últimos IDs vistos (evita re-envio)
_ultimos: dict[str, str] = {}


def _contar_sinais():
    if not fabrica.raiz:
        return 0, 0
    sp = 0
    sv = 0

    def _c(n):
        nonlocal sp, sv
        sp += len(n.canal.pendentes())
        sv += len(n.canal.pendentes(GravidadeSinal.VERMELHO))
        for s in n.listar_subniveis():
            _c(s)

    _c(fabrica.raiz)
    return sp, sv


async def gerar_eventos(request: Request):
    """Gera stream SSE com eventos da CDA."""
    client_id = f"client_{datetime.now(timezone.utc).timestamp()}"

    while True:
        if await request.is_disconnected():
            break

        eventos: list[dict[str, Any]] = []

        # 1. Status agregado (a cada evento)
        if fabrica.raiz:
            agentes = fabrica.raiz.listar_agentes()
            sp, sv = _contar_sinais()
            dp = 0

            def _cd(n):
                nonlocal dp
                dp += len(n.motor.pendentes())
                for s in n.listar_subniveis():
                    _cd(s)

            _cd(fabrica.raiz)

            eventos.append({
                "tipo": "status",
                "dados": {
                    "total_agentes": len(agentes),
                    "online": sum(1 for a in agentes if a.status in (StatusAgente.ONLINE, StatusAgente.TRABALHANDO)),
                    "decisoes_pendentes": dp,
                    "sinais_pendentes": sp,
                    "sinais_vermelhos": sv,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            })

        # 2. Heartbeats dos clocks
        for c in sistema_clocks.status_todos():
            hb_id = f"hb_{c['nivel']}_{c['tick_atual']}"
            if _ultimos.get(f"hb_{c['nivel']}") != str(c['tick_atual']):
                _ultimos[f"hb_{c['nivel']}"] = str(c['tick_atual'])
                eventos.append({
                    "tipo": "heartbeat",
                    "dados": c,
                })

        # 3. Bargain pendentes
        bp = protocolo_bargain.pendentes()
        for n in bp:
            e_id = f"bg_{n.id}"
            if _ultimos.get(e_id) != n.status.value:
                _ultimos[e_id] = n.status.value
                eventos.append({
                    "tipo": "bargain",
                    "dados": {
                        "id": n.id,
                        "subnivel": n.subnivel,
                        "status": n.status.value,
                        "recursos": [f"{r.quantidade}x {r.tipo}" for r in n.recursos],
                    },
                })

        if eventos:
            yield f"data: {json.dumps(eventos, ensure_ascii=False)}\n\n"

        await asyncio.sleep(5)


@ws_router.get("/events")
async def sse_events(request: Request):
    return StreamingResponse(
        gerar_eventos(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
