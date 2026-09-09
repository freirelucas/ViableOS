"""Ciclo de vida da CDA — o tick real da fábrica e o startup com ledger.

Lacuna registrada: gatilhos testados isoladamente, mas o tick_cda real
(propagação + timeout + conflito + budget no mesmo relógio) nunca rodou
(nums/testes) e o caminho de startup com CDA_STATE_DIR nunca foi
exercitado pelo main.py de verdade.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from viableos.api.auth import create_token
from viableos.api.main import app
from viableos.cda.algedonic import TipoGatilho
from viableos.cda.bratman import agenda_bratman
from viableos.cda.fabrica import fabrica
from viableos.cda.recursao.clock import sistema_clocks

Nome_S4 = "Inteligência Estratégica (S4)"


def _solicitar_no_raiz(assunto: str):
    return fabrica.raiz.motor.solicitar(
        solicitante=Nome_S4,
        tipo_solicitante="s4_inteligencia",
        assunto=assunto,
        contexto="Contexto do tick real",
        opcoes=["Opção A", "Opção B"],
        justificativa="Ciclo de vida: cascata completa.",
    )


def _tick(n: int) -> dict:
    clock = sistema_clocks.obter("CDA")
    assert clock is not None and clock.on_tick is not None
    return asyncio.run(clock.on_tick(n))


# ─── Tick real: os gatilhos disparam e não duplicam ────────────────


def test_tick_real_dispara_timeout_e_conflito_sem_duplicar():
    raiz = fabrica.raiz
    decisao = _solicitar_no_raiz("Decisão que expira no tick")
    decisao.criado_em = (
        datetime.now(timezone.utc) - timedelta(hours=25)
    ).isoformat()

    motor_dev = agenda_bratman.obter_motor("Agente Desenvolvedor")
    motor_gestor = agenda_bratman.obter_motor("Gestor de Bolsas")
    i1 = motor_dev.adotar("Treinar modelo", "Usar GPU", [{"descricao": "p1", "recursos": ["gpu-ciclo-vida"]}])
    i2 = motor_gestor.adotar("Processar lote", "Usar GPU", [{"descricao": "p1", "recursos": ["gpu-ciclo-vida"]}])
    assert i1 is not None and i2 is not None

    sinais_tick1 = _tick(1)["sinais"]
    sinais_tick2 = _tick(2)["sinais"]

    timeouts = [
        s for s in raiz.canal.todos()
        if s.gatilho == TipoGatilho.TIMEOUT_DECISAO
        and s.contexto.get("decisao_id") == decisao.id
    ]
    conflitos = [
        s for s in raiz.canal.todos()
        if s.gatilho == TipoGatilho.CONFLITO_AGENTES
        and "gpu-ciclo-vida" in s.contexto.get("recurso", "")
    ]
    try:
        assert len(timeouts) == 1, "timeout dispara uma vez, não a cada tick"
        assert len(conflitos) == 1, "conflito dispara uma vez por par de intenções"
        assert sinais_tick1 >= 2
        assert sinais_tick2 == 0, "segundo tick não re-dispara o que já sinalizou"
    finally:
        # limpeza: não vazar estado para outros arquivos de teste
        raiz.canal._sinais = [
            s for s in raiz.canal._sinais
            if s.contexto.get("decisao_id") != decisao.id
            and "gpu-ciclo-vida" not in (s.contexto.get("recurso") or "")
            and s.contexto.get("recurso") != "gpu-ciclo-vida"
        ]
        raiz.motor._decisoes = [d for d in raiz.motor._decisoes if d.id != decisao.id]
        raiz.motor._historico = [d for d in raiz.motor._historico if d.id != decisao.id]
        motor_dev._intencoes = []
        motor_gestor._intencoes = []


# ─── Startup com ledger: replay substitui seed (caminho do main.py) ──


def test_startup_ledger_substitui_seed_e_replay_restaura(tmp_path):
    from viableos.cda import provenancia

    diretorio = str(tmp_path / "estado")
    headers = {"Authorization": f"Bearer {create_token('diretora@ipea', ['admin'])}"}
    provenancia.ledger.habilitar(diretorio)
    try:
        # ── "Boot 1": com ledger ativo o startup NÃO roda seed ──
        # (processo pytest compartilhado: assertamos ausência do SEED, não lista vazia)
        with TestClient(app) as c1:
            pendentes = c1.get("/api/cda/decisoes").json()
            assuntos = {d["assunto"] for d in pendentes}
            assert "Priorizar sprint 3 vs Projeto 2" not in assuntos, \
                "com CDA_STATE_DIR ativo o seed demo fica desligado"
            assert "Definir escopo de digitalização do fluxo de contratação" not in assuntos

            resp = c1.post(
                f"/api/cda/agentes/{Nome_S4}/decisao",
                json={
                    "assunto": "Decisão que deve sobreviver ao restart",
                    "contexto": "Teste de replay pelo startup real",
                    "opcoes": ["Sobreviver", "Evaporar"],
                    "justificativa": "Regra 2 do handout: intenção persiste fora do runner.",
                },
            )
            decisao_id = resp.json()["decisao_id"]

        # ── "Boot 2": mesmo diretório — startup faz replay do ledger ──
        with TestClient(app) as c2:
            pendentes = c2.get("/api/cda/decisoes").json()
            alvo = [d for d in pendentes if d["id"] == decisao_id]
            assert alvo, "decisão tinha que voltar pelo replay"
            assert alvo[0]["assunto"] == "Decisão que deve sobreviver ao restart"

            # e o ciclo se completa: resolver com token após restart
            resp = c2.post(
                f"/api/cda/decisoes/{decisao_id}/resolver",
                json={"resolucao": "Sobreviver"},
                headers=headers,
            )
            assert resp.json()["status"] == "ok"
    finally:
        provenancia.ledger.desabilitar()
        # limpeza do singleton da fábrica contaminado pelo replay
        fabrica.raiz.motor._decisoes = []
        fabrica.raiz.motor._historico = []
        fabrica.raiz.canal._sinais = []
