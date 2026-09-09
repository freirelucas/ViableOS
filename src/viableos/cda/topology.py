"""Validação topológica VSM — controla quem pode falar com quem.

Baseado na matriz de comunicação de coordination.py e na topologia
do VSM de Beer: S1 fala APENAS com S2, S2 roteia para todos,
S3* tem read-only em S1, S4 fala com S2 e S5.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── Matriz de canais permitidos (VSM de Beer) ──────────────────

# Chave = (remetente_level, destinatário_level)
# True = permitido, False = bloqueado, None = não mapeado (= bloqueado)
CANAIS_VSM: dict[tuple[str, str], bool] = {
    # S1 → S2: coordenação (reporta status)
    ("s1", "s2"): True,
    # S1 → S1: NUNCA diretamente (deve ir via S2)
    ("s1", "s1"): False,
    # S2 → S1: roteio de diretrizes
    ("s2", "s1"): True,
    # S2 → S3: escala para cima
    ("s2", "s3"): True,
    # S2 → S3*: relatório de auditoria
    ("s2", "s3*"): True,
    # S2 → S4: repasse de informação
    ("s2", "s4"): True,
    # S2 → S5: escalação
    ("s2", "s5"): True,
    # S3 → S1: bargain de recursos (via S2)
    ("s3", "s1"): True,
    # S3 → S2: instruções
    ("s3", "s2"): True,
    # S3* → S1: auditoria (read-only)
    ("s3*", "s1"): True,
    # S3* → S3: achados de auditoria
    ("s3*", "s3"): True,
    # S3* → S5: relatório direto ao topo
    ("s3*", "s5"): True,
    # S4 → S2: inteligência outside-in
    ("s4", "s2"): True,
    # S4 → S5: inteligência outside-in
    ("s4", "s5"): True,
    # S5 → S2: política
    ("s5", "s2"): True,
    # S5 → S3: política
    ("s5", "s3"): True,
    # S5 → S4: direcionamento inside-out
    ("s5", "s4"): True,
    # S5 → S3*: direcionamento de auditoria
    ("s5", "s3*"): True,
}

# Níveis VSM conhecidos
NIVEIS_VSM = {"s1", "s2", "s3", "s3*", "s4", "s5"}


@dataclass
class ResultadoValidacao:
    """Resultado da validação de uma mensagem."""
    permitido: bool
    remetente: str
    destinatario: str
    nivel_remetente: str
    nivel_destinatario: str
    motivo: str = ""


class TopologyValidator:
    """Valida mensagens contra a topologia VSM de Beer.

    Uso:
        validator = TopologyValidator()
        resultado = validator.validar("s1_gestor_bolsas", "s2_coordenacao", "s1", "s2")
        if not resultado.permitido:
            print(f"Bloqueado: {resultado.motivo}")
    """

    def __init__(self, canais: dict[tuple[str, str], bool] | None = None):
        self._canais = canais or CANAIS_VSM
        self._blocos: list[dict] = []

    def validar(
        self,
        remetente: str,
        destinatario: str,
        nivel_remetente: str,
        nivel_destinatario: str,
    ) -> ResultadoValidacao:
        """Valida se uma mensagem é permitida pela topologia VSM.

        Args:
            remetente: nome/ID do agente remetente
            destinatario: nome/ID do agente destinatário
            nivel_remetente: nível VSM do remetente (s1, s2, s3, s3*, s4, s5)
            nivel_destinatario: nível VSM do destinatário
        """
        nivel_r = nivel_remetente.lower().strip()
        nivel_d = nivel_destinatario.lower().strip()

        # Normalizar nomes de nível
        nivel_r = nivel_r.replace("star", "*").replace("_star", "*")
        nivel_d = nivel_d.replace("star", "*").replace("_star", "*")

        # Validar níveis conhecidos
        if nivel_r not in NIVEIS_VSM:
            return ResultadoValidacao(
                permitido=True,
                remetente=remetente,
                destinatario=destinatario,
                nivel_remetente=nivel_r,
                nivel_destinatario=nivel_d,
                motivo=f"Nível '{nivel_r}' não mapeado — permitido por padrão",
            )
        if nivel_d not in NIVEIS_VSM:
            return ResultadoValidacao(
                permitido=True,
                remetente=remetente,
                destinatario=destinatario,
                nivel_remetente=nivel_r,
                nivel_destinatario=nivel_d,
                motivo=f"Nível '{nivel_d}' não mapeado — permitido por padrão",
            )

        # Canal algédonico: qualquer agente pode alertar S5
        if nivel_d == "s5":
            return ResultadoValidacao(
                permitido=True,
                remetente=remetente,
                destinatario=destinatario,
                nivel_remetente=nivel_r,
                nivel_destinatario=nivel_d,
                motivo="Canal algêdonico: qualquer agente pode alertar S5",
            )

        # Verificar matriz
        chave = (nivel_r, nivel_d)
        permitido = self._canais.get(chave, False)

        if not permitido:
            motivo = (
                f"Topologia VSM bloqueada: {nivel_r} → {nivel_d}. "
                f"Regra: S1 fala APENAS com S2; comunicação entre pares "
                f"do mesmo nível é proibida."
            )
            logger.warning(
                "Mensagem bloqueada: %s (%s) → %s (%s): %s",
                remetente, nivel_r, destinatario, nivel_d, motivo,
            )
            self._blocos.append({
                "remetente": remetente,
                "destinatario": destinatario,
                "nivel_remetente": nivel_r,
                "nivel_destinatario": nivel_d,
                "motivo": motivo,
            })
        else:
            motivo = f"Canal permitido: {nivel_r} → {nivel_d}"

        return ResultadoValidacao(
            permitido=permitido,
            remetente=remetente,
            destinatario=destinatario,
            nivel_remetente=nivel_r,
            nivel_destinatario=nivel_d,
            motivo=motivo,
        )

    def validar_por_tipo(
        self,
        remetente: str,
        destinatario: str,
        tipo_remetente: str,
        tipo_destinatario: str,
    ) -> ResultadoValidacao:
        """Valida usando TipoAgente em vez de nível VSM direto.

        Mapeia tipos do fabrica.py para níveis VSM:
        - S1_DESENVOLVEDOR, S1_EXECUTOR, S1_ANALISTA → s1
        - S2_COORDENACAO → s2
        - S3_GESTAO → s3
        - S3_AUDITORIA → s3*
        - S4_INTELIGENCIA → s4
        """
        mapeamento = {
            "s1_desenvolvedor": "s1",
            "s1_executor": "s1",
            "s1_analista": "s1",
            "s2_coordenacao": "s2",
            "s3_gestao": "s3",
            "s3_auditoria": "s3*",
            "s4_inteligencia": "s4",
            "s5": "s5",
        }
        nivel_r = mapeamento.get(tipo_remetente.lower(), tipo_remetente.lower())
        nivel_d = mapeamento.get(tipo_destinatario.lower(), tipo_destinatario.lower())
        return self.validar(remetente, destinatario, nivel_r, nivel_d)

    @property
    def total_blocos(self) -> int:
        return len(self._blocos)

    @property
    def blocos_recentes(self) -> list[dict]:
        return self._blocos[-10:]

    def resetar(self) -> None:
        self._blocos.clear()


# Singleton
topology_validator = TopologyValidator()
