"""Monitor de orçamento — ponte entre budget.py e algedonic.py.

Rastreia uso real de tokens por sistema (S1-S5) e compara com o plano
de orçamento. Dispara sinais algêdonicos DESVIO_ORCAMENTO quando:
- uso/orçado > 80% → AMARELO (warn)
- uso/orçado > 95% → VERMELHO (auto-downgrade)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from viableos.cda.algedonic import CanalAlgedonico, GravidadeSinal, TipoGatilho

logger = logging.getLogger(__name__)


@dataclass
class UsoSistema:
    """Uso acumulado de tokens para um sistema."""
    sistema: str
    tokens_utilizados: int = 0
    chamadas: int = 0
    custo_usd: float = 0.0


@dataclass
class AlertaOrcamento:
    """Alerta de desvio orçamentário."""
    sistema: str
    uso: float
    orcado: float
    percentual: float
    gravidade: str  # "amarelo" ou "vermelho"


class BudgetMonitor:
    """Monitora uso de tokens vs. orçamento e dispara sinais algêdonicos.

    Integra com:
    - budget.py: BudgetPlan (plano de alocação)
    - algedonic.py: CanalAlgedonico (sinais algêdonicos)

    Uso:
        monitor = BudgetMonitor(canal_algedonico)
        monitor.registrar_uso("S1", tokens=1500, chamadas=3, custo=0.05)
        monitor.verificar_desvio(tick=100)
    """

    WARN_THRESHOLD = 0.80
    CRITICAL_THRESHOLD = 0.95

    def __init__(self, canal: CanalAlgedonico | None = None):
        self._canal = canal
        self._uso: dict[str, UsoSistema] = {}
        self._orcamento: dict[str, float] = {}  # sistema → monthly_usd
        self._alertas: list[AlertaOrcamento] = []
        self._alertas_disparados: set[str] = set()  # evitar duplicatas

    def definir_canal(self, canal: CanalAlgedonico) -> None:
        """Conecta o monitor ao canal algédonico (sinais de desvio).

        Sem canal, o monitor loga mas nenhum sinal sobe ao S5 —
        bug triplo registrado na docs/audits/2026-09-03-coerencia-cda.md §2.3.
        """
        self._canal = canal

    def definir_orcamento(self, sistema: str, monthly_usd: float) -> None:
        """Define o orçamento mensal para um sistema."""
        self._orcamento[sistema] = monthly_usd

    def definir_plano(self, allocations: list) -> None:
        """Define orçamentos a partir de um BudgetPlan (budget.py)."""
        for alloc in allocations:
            # Mapear nomes do budget.py para níveis da CDA
            sistema = alloc.system.split(":")[0]  # "S1:Gestor" → "S1"
            self._orcamento[sistema] = alloc.monthly_usd

    def registrar_uso(
        self,
        sistema: str,
        tokens: int = 0,
        chamadas: int = 1,
        custo_usd: float = 0.0,
    ) -> None:
        """Registra uso de tokens para um sistema."""
        if sistema not in self._uso:
            self._uso[sistema] = UsoSistema(sistema=sistema)
        uso = self._uso[sistema]
        uso.tokens_utilizados += tokens
        uso.chamadas += chamadas
        uso.custo_usd += custo_usd

    def verificar_desvio(self, tick: int = 0) -> list[AlertaOrcamento]:
        """Verifica desvio orçamentário e dispara sinais algêdonicos.

        Returns:
            Lista de alertas disparados neste tick.
        """
        alertas_novos: list[AlertaOrcamento] = []

        for sistema, uso in self._uso.items():
            orcado = self._orcamento.get(sistema, 0)
            if orcado <= 0:
                continue

            percentual = uso.custo_usd / orcado if orcado > 0 else 0

            if percentual >= self.CRITICAL_THRESHOLD:
                chave = f"{sistema}_vermelho"
                if chave not in self._alertas_disparados:
                    alerta = AlertaOrcamento(
                        sistema=sistema,
                        uso=uso.custo_usd,
                        orcado=orcado,
                        percentual=round(percentual * 100, 1),
                        gravidade="vermelho",
                    )
                    alertas_novos.append(alerta)
                    self._alertas_disparados.add(chave)
                    self._disparar_sinal(sistema, uso, orcado, percentual, GravidadeSinal.VERMELHO)

            elif percentual >= self.WARN_THRESHOLD:
                chave = f"{sistema}_amarelo"
                if chave not in self._alertas_disparados:
                    alerta = AlertaOrcamento(
                        sistema=sistema,
                        uso=uso.custo_usd,
                        orcado=orcado,
                        percentual=round(percentual * 100, 1),
                        gravidade="amarelo",
                    )
                    alertas_novos.append(alerta)
                    self._alertas_disparados.add(chave)
                    self._disparar_sinal(sistema, uso, orcado, percentual, GravidadeSinal.AMARELO)

        self._alertas.extend(alertas_novos)
        return alertas_novos

    def _disparar_sinal(
        self,
        sistema: str,
        uso: UsoSistema,
        orcado: float,
        percentual: float,
        gravidade: GravidadeSinal,
    ) -> None:
        """Dispara sinal algédonico de desvio orçamentário."""
        if not self._canal:
            logger.warning("BudgetMonitor sem canal algédonico — sinal não disparado")
            return

        self._canal.disparar(
            fonte=f"BudgetMonitor:{sistema}",
            gravidade=gravidade,
            gatilho=TipoGatilho.DESVIO_ORCAMENTO,
            assunto=f"Desvio orçamentário: {sistema}",
            mensagem=(
                f"{sistema}: uso ${uso.custo_usd:.2f} / orçado ${orcado:.2f} "
                f"({percentual*100:.0f}%). "
                f"{'CRÍTICO — considere downgrade de modelo.' if gravidade == GravidadeSinal.VERMELHO else 'Atenção — próximo do limite.'}"
            ),
            contexto={
                "sistema": sistema,
                "tokens": uso.tokens_utilizados,
                "chamadas": uso.chamadas,
                "custo_usd": uso.custo_usd,
                "orcado_usd": orcado,
                "percentual": round(percentual * 100, 1),
            },
        )
        logger.info(
            "Sinal algédonico disparado: %s %s (%.0f%%)",
            gravidade.value, sistema, percentual * 100,
        )

    def obter_uso(self, sistema: str | None = None) -> dict | list[dict]:
        """Retorna uso registrado."""
        if sistema:
            uso = self._uso.get(sistema)
            return {
                "sistema": uso.sistema,
                "tokens": uso.tokens_utilizados,
                "chamadas": uso.chamadas,
                "custo_usd": round(uso.custo_usd, 4),
                "orcado_usd": self._orcamento.get(sistema, 0),
                "percentual": round(
                    (uso.custo_usd / self._orcamento.get(sistema, 1)) * 100, 1
                ),
            } if uso else None
        return [
            {
                "sistema": u.sistema,
                "tokens": u.tokens_utilizados,
                "chamadas": u.chamadas,
                "custo_usd": round(u.custo_usd, 4),
                "orcado_usd": self._orcamento.get(u.sistema, 0),
                "percentual": round(
                    (u.custo_usd / self._orcamento.get(u.sistema, 1)) * 100, 1
                ),
            }
            for u in self._uso.values()
        ]

    def obter_alertas(self) -> list[dict]:
        """Retorna alertas disparados."""
        return [
            {
                "sistema": a.sistema,
                "uso": round(a.uso, 4),
                "orcado": round(a.orcado, 4),
                "percentual": a.percentual,
                "gravidade": a.gravidade,
            }
            for a in self._alertas
        ]

    def resetar(self) -> None:
        """Reseta uso e alertas (novo mês/ciclo)."""
        self._uso.clear()
        self._alertas.clear()
        self._alertas_disparados.clear()


# Singleton
budget_monitor = BudgetMonitor()
