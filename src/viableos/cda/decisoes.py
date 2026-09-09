"""Motor de decisões — define autonomia, escalação e workflow da CDA."""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from viableos.cda.provenancia import PapelProveniencia, carimbo_constituicao, papel_por_tipo

logger = logging.getLogger(__name__)


class NivelAutonomia(str, enum.Enum):
    TOTAL = "total"          # Decide sem consultar ninguém
    LIMITADA = "limitada"    # Decide mas informa S3
    RECOMENDACAO = "recomendacao"  # Recomenda ao S5, que aprova
    NENHUMA = "nenhuma"      # Só executa ordens do S5


class StatusDecisao(str, enum.Enum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    REJEITADA = "rejeitada"
    DELEGADA = "delegada"  # Devolvida ao agente para decidir


# Autonomia por tipo organizacional.
# Decisão técnica registrada na docs/audits/2026-09-03-coerencia-cda.md §2.4:
# TOTAL (auto-aprovação sem humano) fica reservada a papéis de auditoria —
# s1_desenvolvedor sai da lista (escrever código é operação reversível pelo
# envelope R2, mas decidir sem humano não é alçada de S1).
AUTONOMIA_POR_TIPO: dict[str, NivelAutonomia] = {
    "s5_diretor": NivelAutonomia.TOTAL,
    "s4_inteligencia": NivelAutonomia.RECOMENDACAO,
    "s3_gestao": NivelAutonomia.LIMITADA,
    "s3_auditoria": NivelAutonomia.TOTAL,
    "s2_coordenacao": NivelAutonomia.LIMITADA,
    "s1_desenvolvedor": NivelAutonomia.RECOMENDACAO,
    "s1_executor": NivelAutonomia.RECOMENDACAO,
    "s1_analista": NivelAutonomia.RECOMENDACAO,
}


@dataclass
class DecisaoWorkflow:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    assunto: str = ""
    solicitante: str = ""
    tipo_solicitante: str = ""
    contexto: str = ""
    urgencia: str = "media"
    opcoes: list[str] = field(default_factory=list)
    autonomia: NivelAutonomia = NivelAutonomia.RECOMENDACAO
    status: StatusDecisao = StatusDecisao.PENDENTE
    justificativa: str = ""
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolvido_em: str | None = None
    resolvido_por: str | None = None
    resolucao: str | None = None
    feedback: str | None = None
    # Proveniência organizacional (docs/audits/2026-09-03-coerencia-cda.md §2.5)
    papel_origem: str = ""        # papel do solicitante no ato de criar
    papel_aprovacao: str = ""     # papel de quem resolveu (S5 humano via API)
    resolvido_por_sub: str = ""   # identidade do JWT de quem resolveu (R5)
    constituicao_hash: str = ""   # hash da constituição vigente no ato
    intencao_id: str = ""         # compromisso Bratman ao qual a decisão se refere


class MotorDecisoes:
    """Gerencia o workflow de decisões da CDA.

    Cada agente tem um nível de autonomia. Se a decisão estiver dentro
    da alçada, o motor resolve automaticamente. Caso contrário, sobe
    para o S5.

    R6 imposta na entrada: decisão sem cascata (contexto, opções,
    justificativa) é nula — solicitar() levanta ValueError.
    """

    def __init__(self):
        self._decisoes: list[DecisaoWorkflow] = []
        self._historico: list[DecisaoWorkflow] = []
        self.nivel_nome: str = ""

    def solicitar(
        self,
        solicitante: str,
        tipo_solicitante: str,
        assunto: str,
        contexto: str,
        opcoes: list[str],
        urgencia: str = "media",
        justificativa: str = "",
        intencao_id: str = "",
    ) -> DecisaoWorkflow:
        if not contexto or not opcoes or not justificativa:
            raise ValueError(
                "R6 (cascata rastreável): decisão sem cascata é nula — "
                "contexto, opções e justificativa são obrigatórios"
            )
        autonomia = AUTONOMIA_POR_TIPO.get(tipo_solicitante, NivelAutonomia.RECOMENDACAO)
        dec = DecisaoWorkflow(
            assunto=assunto,
            solicitante=solicitante,
            tipo_solicitante=tipo_solicitante,
            contexto=contexto,
            urgencia=urgencia,
            opcoes=opcoes,
            autonomia=autonomia,
            justificativa=justificativa,
            papel_origem=papel_por_tipo(tipo_solicitante).value,
            constituicao_hash=carimbo_constituicao()["hash_sha256"],
            intencao_id=intencao_id,
        )

        if autonomia == NivelAutonomia.TOTAL:
            dec.status = StatusDecisao.APROVADA
            dec.resolvido_em = datetime.now(timezone.utc).isoformat()
            dec.resolvido_por = solicitante
            dec.resolucao = opcoes[0]
            dec.feedback = "Decisão tomada por autonomia total do agente."
            dec.papel_aprovacao = papel_por_tipo(tipo_solicitante).value
            self._historico.append(dec)
            self._registrar_ledger(dec)
            return dec

        if autonomia == NivelAutonomia.LIMITADA:
            dec.status = StatusDecisao.APROVADA
            dec.resolvido_em = datetime.now(timezone.utc).isoformat()
            dec.resolvido_por = solicitante
            dec.resolucao = opcoes[0]
            dec.feedback = "Decisão tomada dentro da alçada do agente. S3 notificado."
            dec.papel_aprovacao = papel_por_tipo(tipo_solicitante).value
            self._historico.append(dec)
            self._registrar_ledger(dec)
            return dec

        if autonomia == NivelAutonomia.NENHUMA:
            dec.feedback = (
                "Autonomia nenhuma: decisão sobe ao S5 — "
                "o agente só executa ordens."
            )
            self._decisoes.append(dec)
            self._registrar_ledger(dec)
            return dec

        self._decisoes.append(dec)
        self._registrar_ledger(dec)
        return dec

    def resolver(
        self,
        decisao_id: str,
        resolucao: str,
        resolvido_por: str = "Diretora",
        resolvido_por_sub: str = "",
    ) -> bool:
        for d in self._decisoes:
            if d.id == decisao_id:
                d.status = StatusDecisao.APROVADA
                d.resolvido_em = datetime.now(timezone.utc).isoformat()
                d.resolvido_por = resolvido_por
                d.resolucao = resolucao
                d.resolvido_por_sub = resolvido_por_sub
                d.papel_aprovacao = PapelProveniencia.S5_HUMANO_APROVOU.value
                d.feedback = f"Decisão aprovada por {resolvido_por}."
                self._decisoes.remove(d)
                self._historico.append(d)
                self._registrar_ledger(d)
                return True
        return False

    def rejeitar(self, decisao_id: str, feedback: str) -> bool:
        for d in self._decisoes:
            if d.id == decisao_id:
                d.status = StatusDecisao.REJEITADA
                d.resolvido_em = datetime.now(timezone.utc).isoformat()
                d.feedback = feedback
                d.papel_aprovacao = PapelProveniencia.S5_HUMANO_APROVOU.value
                self._decisoes.remove(d)
                self._historico.append(d)
                self._registrar_ledger(d)
                return True
        return False

    def delegar(self, decisao_id: str) -> bool:
        for d in self._decisoes:
            if d.id == decisao_id:
                d.status = StatusDecisao.DELEGADA
                d.resolvido_em = datetime.now(timezone.utc).isoformat()
                d.feedback = "Delegada de volta ao agente para decisão autônoma."
                d.papel_aprovacao = PapelProveniencia.S5_HUMANO_APROVOU.value
                self._decisoes.remove(d)
                self._historico.append(d)
                self._registrar_ledger(d)
                return True
        return False

    def pendentes(self) -> list[DecisaoWorkflow]:
        return sorted(self._decisoes, key=lambda d: d.criado_em, reverse=True)

    def historico(self, limite: int = 20) -> list[DecisaoWorkflow]:
        return sorted(self._historico, key=lambda d: d.criado_em or "", reverse=True)[:limite]

    def _registrar_ledger(self, dec: DecisaoWorkflow) -> None:
        """Anexa o estado da decisão ao ledger (se habilitado via CDA_STATE_DIR)."""
        try:
            from viableos.cda.provenancia import ledger
            papel = dec.papel_aprovacao if dec.papel_aprovacao else dec.papel_origem
            ledger.registrar(
                "decisao_estado",
                {"nivel": self.nivel_nome, "decisao": asdict(dec)},
                papel=papel,
            )
        except Exception as e:  # o núcleo nunca quebra por falha de ledger
            logger.warning("Ledger: falha ao registrar decisão: %s", e)

    def _aplicar_estado(self, dados: dict[str, Any]) -> None:
        """Replay do ledger — reconstrói decisão a partir do estado persistido."""
        from viableos.cda.provenancia import _decisao_de_dict

        dec = _decisao_de_dict(dados)
        for lista in (self._decisoes, self._historico):
            for i, d in enumerate(lista):
                if d.id == dec.id:
                    lista[i] = dec
                    # Upsert pode mover pendente → resolvido
                    if lista is self._decisoes and dec.status != StatusDecisao.PENDENTE:
                        self._decisoes.remove(dec)
                        self._historico.append(dec)
                    return
        if dec.status == StatusDecisao.PENDENTE:
            self._decisoes.append(dec)
        else:
            self._historico.append(dec)

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "id": d.id,
                "assunto": d.assunto,
                "solicitante": d.solicitante,
                "tipo_solicitante": d.tipo_solicitante,
                "contexto": d.contexto,
                "urgencia": d.urgencia,
                "opcoes": d.opcoes,
                "justificativa": d.justificativa,
                "autonomia": d.autonomia.value,
                "status": d.status.value,
                "criado_em": d.criado_em,
                "papel_origem": d.papel_origem,
                "intencao_id": d.intencao_id,
            }
            for d in self.pendentes()
        ]


# Singleton de compatibilidade — a árvore usa motor por nível (NivelVSM.motor).
motor = MotorDecisoes()
