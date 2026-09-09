"""Protocolo de Bargain entre níveis VSM.

S3(N) negocia recursos com S3(N+1) de cada subnível.
O bargain é o mecanismo que alinha capacidade aos propósitos.

Fluxo:
  1. Subnível N+1 enuncia: recursos necessários + justificativa
  2. Nível N avalia: disponibilidade vs prioridade estratégica
  3. Negociação: N pode contrapor, reduzir, realocar
  4. Fecho: acordo registrado em ambos os níveis

O bargain ocorre a cada ciclo do clock do nível N.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StatusBargain(str, Enum):
    SOLICITADO = "solicitado"
    EM_NEGOCIACAO = "em_negociacao"
    APROVADO = "aprovado"
    PARCIAL = "parcial"
    REJEITADO = "rejeitado"


@dataclass
class Recurso:
    tipo: str = ""        # ex: "agente", "tempo_gpu", "api_calls", "orcamento"
    quantidade: int = 1
    unidade: str = ""      # ex: "horas/semana", "unidades", "R$"
    prioridade: int = 3    # 1 (crítico) a 5 (desejável)


@dataclass
class Negociacao:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    subnivel: str = ""
    nivel_pai: str = ""
    recursos: list[Recurso] = field(default_factory=list)
    justificativa: str = ""
    status: StatusBargain = StatusBargain.SOLICITADO
    contraproposta: str = ""
    alocacao_final: dict[str, int] = field(default_factory=dict)  # recurso -> qtd aprovada
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolvido_em: str | None = None


class ProtocoloBargain:
    """Gerencia o bargain entre níveis pai e filho.

    O pai (nível N) tem a palavra final, mas o filho (nível N+1)
    pode recorrer ao S4 do pai se discordar (via canal algêdonico).
    """

    def __init__(self):
        self._negociacoes: list[Negociacao] = []

    def solicitar(
        self,
        subnivel: str,
        nivel_pai: str,
        recursos: list[dict[str, Any]],
        justificativa: str = "",
    ) -> Negociacao:
        recos = [Recurso(**r) if isinstance(r, dict) else r for r in recursos]
        n = Negociacao(
            subnivel=subnivel,
            nivel_pai=nivel_pai,
            recursos=recos,
            justificativa=justificativa,
        )
        self._negociacoes.append(n)
        return n

    def avaliar(
        self,
        negociacao_id: str,
        alocacao: dict[str, int],
        contraproposta: str = "",
    ) -> bool:
        """Pai avalia e responde à solicitação."""
        for n in self._negociacoes:
            if n.id == negociacao_id and n.status == StatusBargain.SOLICITADO:
                n.alocacao_final = alocacao
                n.contraproposta = contraproposta

                total_solicitado = sum(r.quantidade for r in n.recursos)
                total_alocado = sum(alocacao.values())

                if total_alocado >= total_solicitado:
                    n.status = StatusBargain.APROVADO
                elif total_alocado > 0:
                    n.status = StatusBargain.PARCIAL
                else:
                    n.status = StatusBargain.REJEITADO

                n.resolvido_em = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def pendentes(self, subnivel: str | None = None) -> list[Negociacao]:
        filtrados = [n for n in self._negociacoes if n.status == StatusBargain.SOLICITADO]
        if subnivel:
            filtrados = [n for n in filtrados if n.subnivel == subnivel]
        return filtrados

    def historico(self) -> list[Negociacao]:
        return list(self._negociacoes)

    def to_dict(self, apenas_pendentes: bool = False) -> list[dict[str, Any]]:
        fonte = self.pendentes() if apenas_pendentes else self._negociacoes
        return [
            {
                "id": n.id,
                "subnivel": n.subnivel,
                "nivel_pai": n.nivel_pai,
                "recursos": [
                    {"tipo": r.tipo, "quantidade": r.quantidade, "unidade": r.unidade}
                    for r in n.recursos
                ],
                "justificativa": n.justificativa,
                "status": n.status.value,
                "alocacao_final": n.alocacao_final,
                "criado_em": n.criado_em,
                "resolvido_em": n.resolvido_em,
            }
            for n in fonte
        ]


# Singleton global
protocolo_bargain = ProtocoloBargain()
