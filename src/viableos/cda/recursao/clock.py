"""Sistema de clocks assimétricos por nível VSM.

Cada nível recursivo tem seu próprio clock com frequência diferente.
A assimetria de frequências é o que isola os níveis — ruído operacional
(N3, 30s) não sobe como ruído estratégico (N1, 60min).

  Nível 1 (CDA):      60 min   — estratégico
  Nível 2 (Projeto):  15 min   — tático
  Nível 3 (Usuário):  30 seg   — operacional

A cada tick, o clock executa:
  1. Processar decisões pendentes (dentro da alçada → auto-aprova)
  2. Propagar sinais algêdonicos ao nível pai
  3. Verificar autonomia dos agentes
  4. Registrar heartbeat no histórico

Spiral buffer: decisões de N1 só afetam N2 no próximo tick de N2.
              decisões de N2 só afetam N3 no próximo tick de N3.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger = logging.getLogger("cda.clock")


class FrequenciaClock(str, enum.Enum):
    OPERACIONAL = "operacional"    # 30s  — N3
    TATICO = "tatico"             # 15min — N2
    ESTRATEGICO = "estrategico"   # 60min — N1


FREQUENCIA_SEGUNDOS: dict[FrequenciaClock, int] = {
    FrequenciaClock.OPERACIONAL: 30,
    FrequenciaClock.TATICO: 900,
    FrequenciaClock.ESTRATEGICO: 3600,
}


@dataclass
class Heartbeat:
    nivel: str = ""
    tick: int = 0
    timestamp: str = ""
    decisoes_processadas: int = 0
    sinais_propagados: int = 0
    agentes_ativos: int = 0
    duracao_ms: float = 0.0
    erros: int = 0


class Clock:
    """Clock assimétrico de um nível VSM.

    Cada nível roda seu próprio loop asyncio com frequência independente.
    A diferença de frequência isola os níveis — decisões estratégicas
    não se confundem com execução operacional.
    """

    def __init__(
        self,
        nivel_nome: str,
        frequencia: FrequenciaClock,
        on_tick: Callable[[int], Awaitable[dict[str, Any]]] | None = None,
    ):
        self.nivel_nome = nivel_nome
        self.frequencia = frequencia
        self.intervalo = FREQUENCIA_SEGUNDOS[frequencia]
        self.on_tick = on_tick
        self.tick_atual = 0
        self._task: asyncio.Task | None = None
        self._rodando = False
        self._heartbeats: list[Heartbeat] = []
        self._iniciado_em: str | None = None

    @property
    def segundos_por_tick(self) -> int:
        return self.intervalo

    @property
    def minutos_por_tick(self) -> float:
        return self.intervalo / 60

    async def iniciar(self) -> None:
        """Inicia o loop do clock em background."""
        if self._rodando:
            return
        self._rodando = True
        self._iniciado_em = datetime.now(timezone.utc).isoformat()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "Clock %s iniciado: %ds por tick (%.1f min)",
            self.nivel_nome, self.intervalo, self.minutos_por_tick,
        )

    async def parar(self) -> None:
        """Para o loop do clock."""
        self._rodando = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Clock %s parado após %d ticks", self.nivel_nome, self.tick_atual)

    async def _loop(self) -> None:
        while self._rodando:
            inicio = time.monotonic()
            self.tick_atual += 1
            erros = 0

            try:
                if self.on_tick:
                    resultado = await self.on_tick(self.tick_atual)
                else:
                    resultado = {}
            except Exception as e:
                logger.error("Erro no tick %d do clock %s: %s", self.tick_atual, self.nivel_nome, e)
                resultado = {"erro": str(e)}
                erros = 1

            # Health check periódico (a cada 10 ticks)
            if self.tick_atual % 10 == 0:
                try:
                    from viableos.cda.health_check import health_check_periodico
                    from viableos.cda.fabrica import fabrica
                    if fabrica.raiz:
                        estado_cda = {
                            "agentes": [a.to_dict() for a in fabrica.raiz.listar_agentes()],
                            "sinais_pendentes": [],
                            "budget_usage": [],
                        }
                        relatorio = health_check_periodico(estado_cda)
                        if not relatorio.saudavel:
                            logger.warning(
                                "Health check %s: %d critical, %d warnings",
                                self.nivel_nome, relatorio.criticals, relatorio.warnings,
                            )
                except Exception as e:
                    logger.debug("Health check skip: %s", e)

            # Budget monitor (a cada 5 ticks) — o uso é registrado pelo glm.py
            # a cada chamada; aqui apenas dispara a verificação de desvio (R4-2).
            if self.tick_atual % 5 == 0:
                try:
                    from viableos.cda.budget_monitor import budget_monitor
                    desvios = budget_monitor.verificar_desvio(tick=self.tick_atual)
                    if desvios:
                        logger.info("Budget monitor: %d desvio(s) detectado(s)", len(desvios))
                except Exception as e:
                    logger.debug("Budget monitor skip: %s", e)

            duracao = (time.monotonic() - inicio) * 1000

            self._heartbeats.append(Heartbeat(
                nivel=self.nivel_nome,
                tick=self.tick_atual,
                timestamp=datetime.now(timezone.utc).isoformat(),
                decisoes_processadas=resultado.get("decisoes", 0),
                sinais_propagados=resultado.get("sinais", 0),
                agentes_ativos=resultado.get("agentes", 0),
                duracao_ms=round(duracao, 1),
                erros=erros,
            ))

            # Mantém só últimos 100 heartbeats
            if len(self._heartbeats) > 100:
                self._heartbeats = self._heartbeats[-100:]

            await asyncio.sleep(self.intervalo)

    def status(self) -> dict[str, Any]:
        return {
            "nivel": self.nivel_nome,
            "frequencia": self.frequencia.value,
            "intervalo_segundos": self.intervalo,
            "tick_atual": self.tick_atual,
            "rodando": self._rodando,
            "iniciado_em": self._iniciado_em,
            "heartbeats": len(self._heartbeats),
            "ultimo_heartbeat": self._heartbeats[-1].timestamp if self._heartbeats else None,
        }

    def ultimos_heartbeats(self, n: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "tick": h.tick,
                "timestamp": h.timestamp,
                "decisoes": h.decisoes_processadas,
                "sinais": h.sinais_propagados,
                "agentes": h.agentes_ativos,
                "duracao_ms": h.duracao_ms,
                "erros": h.erros,
            }
            for h in self._heartbeats[-n:]
        ]


class SistemaClocks:
    """Gerencia todos os clocks da árvore recursiva.

    Inicia/para clocks de todos os níveis simultaneamente.
    Mantém o fuso espiralar: cada nível no seu tempo.
    """

    def __init__(self):
        self._clocks: dict[str, Clock] = {}

    def registrar(self, nivel_nome: str, frequencia: FrequenciaClock,
                  on_tick: Callable | None = None) -> Clock:
        clock = Clock(nivel_nome, frequencia, on_tick)
        self._clocks[nivel_nome] = clock
        return clock

    def obter(self, nivel_nome: str) -> Clock | None:
        return self._clocks.get(nivel_nome)

    async def iniciar_todos(self) -> None:
        for nome, clock in self._clocks.items():
            await clock.iniciar()
            logger.info("Clock %s rodando a cada %ds", nome, clock.intervalo)

    async def parar_todos(self) -> None:
        for nome, clock in self._clocks.items():
            await clock.parar()

    def status_todos(self) -> list[dict[str, Any]]:
        return [c.status() for c in self._clocks.values()]

    def espiral_info(self) -> dict[str, Any]:
        """Informações sobre o tempo espiralar dos clocks."""
        clocks = self.status_todos()
        if len(clocks) < 2:
            return {"mensagem": "menos de 2 clocks rodando"}

        # Razão de frequência entre níveis adjacentes
        razao = 0
        if len(clocks) >= 2:
            try:
                mais_lento = max(clocks, key=lambda c: c["intervalo_segundos"])
                mais_rapido = min(clocks, key=lambda c: c["intervalo_segundos"])
                razao = mais_lento["intervalo_segundos"] / mais_rapido["intervalo_segundos"]
            except Exception:
                razao = 0

        return {
            "clocks": clocks,
            "razao_maior_menor": round(razao, 1),
            # Quantas vezes o clock mais rápido roda enquando o mais lento roda 1x
            "velocidade_relativa": round(razao, 1),
        }


# Singleton global
sistema_clocks = SistemaClocks()
