"""NivelVSM — um nível completo de recursão VSM (S1-S5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from viableos.cda.agente import AgenteGLM, StatusAgente, TipoAgente
from viableos.cda.algedonic import CanalAlgedonico, GravidadeSinal
from viableos.cda.decisoes import MotorDecisoes, NivelAutonomia
from viableos.cda.glm import system_prompt_agente


class NivelVSM:
    """Um nível completo de recursão VSM.
    
    Cada nível tem S5-S1, canal algêdonico próprio, motor de decisões
    próprio, e identidade. As unidades S1 são recursivamente NivelVSM.
    """

    def __init__(
        self,
        nome: str,
        nivel: int,
        proposito: str,
        parent: NivelVSM | None = None,
    ):
        self.id = uuid.uuid4().hex[:8]
        self.nome = nome
        self.nivel = nivel
        self.proposito = proposito
        self.parent = parent
        self.canal = CanalAlgedonico()
        self.motor = MotorDecisoes()
        self.canal.nivel_nome = nome
        self.motor.nivel_nome = nome
        self.criado_em = datetime.now(timezone.utc).isoformat()

        # Agentes deste nível (S5-S2 + representantes S1)
        self._agentes: dict[str, AgenteGLM] = {}
        self._s1_subniveis: list[NivelVSM] = []

    # ─── Agentes ─────────────────────────────────────────

    def adicionar_agente(self, agente: AgenteGLM) -> None:
        self._agentes[agente.nome] = agente

    def obter_agente(self, nome: str) -> AgenteGLM | None:
        # Procura neste nível
        a = self._agentes.get(nome)
        if a:
            return a
        # Procura nos subníveis S1
        for sub in self._s1_subniveis:
            a = sub.obter_agente(nome)
            if a:
                return a
        return None

    def listar_agentes(self) -> list[AgenteGLM]:
        resultado = list(self._agentes.values())
        for sub in self._s1_subniveis:
            resultado.extend(sub.listar_agentes())
        return resultado

    # ─── Subníveis S1 ────────────────────────────────────

    def adicionar_subnivel(self, sub: NivelVSM) -> None:
        sub.parent = self
        self._s1_subniveis.append(sub)

    def listar_subniveis(self) -> list[NivelVSM]:
        return list(self._s1_subniveis)

    def obter_subnivel(self, nome: str) -> NivelVSM | None:
        for s in self._s1_subniveis:
            if s.nome == nome:
                return s
            # Recursão profunda
            encontrado = s.obter_subnivel(nome)
            if encontrado:
                return encontrado
        return None

    def obter_nivel_por_nome(self, nome: str) -> NivelVSM | None:
        if self.nome == nome:
            return self
        return self.obter_subnivel(nome)

    # ─── Cadeia de identidade ─────────────────────────────

    def proposito_completo(self) -> str:
        """Propósito herdado: nível N + específico do nível N+1."""
        if self.parent:
            return f"{self.parent.proposito_completo()} → {self.proposito}"
        return self.proposito

    def system_prompt_para(self, nome_agente: str, proposito_agente: str) -> str:
        return system_prompt_agente(nome_agente, proposito_agente, [])

    # ─── Estatísticas ─────────────────────────────────────

    def total_agentes(self) -> int:
        return len(self.listar_agentes())

    def total_subniveis(self) -> int:
        return len(self._s1_subniveis)

    def decisoes_pendentes(self) -> int:
        return len(self.motor.pendentes())

    def sinais_pendentes(self) -> int:
        return len(self.canal.pendentes())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "nivel": self.nivel,
            "proposito": self.proposito,
            "proposito_completo": self.proposito_completo(),
            "agentes": self.total_agentes(),
            "subniveis": self.total_subniveis(),
            "decisoes_pendentes": self.decisoes_pendentes(),
            "sinais_pendentes": self.sinais_pendentes(),
            "parent": self.parent.nome if self.parent else None,
        }

    def to_dict_profundo(self) -> dict[str, Any]:
        """Serialização recursiva completa para a Sala de Operação."""
        return {
            "id": self.id,
            "nome": self.nome,
            "nivel": self.nivel,
            "proposito": self.proposito,
            "proposito_completo": self.proposito_completo(),
            "agentes": [a.to_dict() for a in self._agentes.values()],
            "subniveis": [s.to_dict_profundo() for s in self._s1_subniveis],
            "decisoes": self.motor.to_dict(),
            "sinais": self.canal.to_dict(),
            "parent": self.parent.nome if self.parent else None,
        }
