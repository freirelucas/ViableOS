"""Canal algédonico — comunicação direta ao S5 pulando hierarquia.

Quatro gatilhos específicos (R4 da Constituição S5 local — a lista vive em
GATILHOS_R4, tabela constante única; emenda proposta em
docs/propostas/emenda-r4-gatilhos.md aguarda decisão S5):
1. TIMEOUT_DECISAO: decisão não resolvida no prazo (determinístico)
2. DESVIO_ORCAMENTO: gasto excede orçamento (determinístico)
3. CONFLITO_AGENTES: agentes com intenções conflitantes (semântico)
4. OPORTUNIDADE_ESTRATEGICA: oportunidade não prevista (semântico)

Sob a constituição local vigente, todos os quatro são "notifica-e-aguarda".
A fonte-mãe (handout, regra 5) exige 2 bloqueantes ("bloqueia-então-notifica")
— divergência registrada na docs/audits/2026-09-03-coerencia-cda.md §1.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class GravidadeSinal(str, enum.Enum):
    VERMELHO = "vermelho"
    AMARELO = "amarelo"
    VERDE = "verde"


class TipoGatilho(str, enum.Enum):
    TIMEOUT_DECISAO = "timeout_decisao"
    DESVIO_ORCAMENTO = "desvio_orcamento"
    CONFLITO_AGENTES = "conflito_agentes"
    OPORTUNIDADE_ESTRATEGICA = "oportunidade_estrategica"


# Tabela constante única da R4 — fonte da verdade para disparos, API e auditoria.
# A emenda R4 proposta (docs/propostas/emenda-r4-gatilhos.md) altera esta tabela
# após decisão S5; nenhum outro ponto do código enumera gatilhos.
GATILHOS_R4: dict[TipoGatilho, dict[str, Any]] = {
    TipoGatilho.TIMEOUT_DECISAO: {
        "semantica": "notifica",
        "bloqueia": False,
        "gravidade_padrao": GravidadeSinal.VERMELHO,
    },
    TipoGatilho.DESVIO_ORCAMENTO: {
        "semantica": "notifica",
        "bloqueia": False,
        "gravidade_padrao": GravidadeSinal.AMARELO,
    },
    TipoGatilho.CONFLITO_AGENTES: {
        "semantica": "notifica",
        "bloqueia": False,
        "gravidade_padrao": GravidadeSinal.AMARELO,
    },
    TipoGatilho.OPORTUNIDADE_ESTRATEGICA: {
        "semantica": "notifica",
        "bloqueia": False,
        "gravidade_padrao": GravidadeSinal.VERDE,
    },
}


PRAZO_RESPOSTA_HORAS: dict[GravidadeSinal, int] = {
    GravidadeSinal.VERMELHO: 24,
    GravidadeSinal.AMARELO: 48,
    GravidadeSinal.VERDE: 0,
}


@dataclass
class SinalAlgedonico:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    fonte: str = ""
    nivel: str = ""
    gravidade: GravidadeSinal = GravidadeSinal.AMARELO
    gatilho: TipoGatilho = TipoGatilho.TIMEOUT_DECISAO
    assunto: str = ""
    mensagem: str = ""
    contexto: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    respondido_em: str | None = None
    resolucao: str | None = None
    # Níveis para os quais o sinal já foi propagado (evita duplicação por tick;
    # serializado no ledger para sobreviver a restarts — ver orquestrador.py).
    propagado_para: list[str] = field(default_factory=list)


class CanalAlgedonico:
    """Gerencia os sinais algêdonicos da CDA.

    Qualquer agente pode disparar um sinal que sobe DIRETAMENTE ao S5
    do nível superior, pulando S2 e S3.

    Prazos de resposta:
    - Vermelho: 24h
    - Amarelo: 48h
    - Verde: informativo, sem prazo
    """

    def __init__(self):
        self._sinais: list[SinalAlgedonico] = []
        self.nivel_nome: str = ""

    def disparar(
        self,
        fonte: str,
        gravidade: GravidadeSinal,
        assunto: str,
        mensagem: str,
        gatilho: TipoGatilho = TipoGatilho.TIMEOUT_DECISAO,
        contexto: dict[str, Any] | None = None,
        nivel: str = "",
    ) -> SinalAlgedonico:
        if gatilho not in GATILHOS_R4:
            # A API valida na entrada; este guard protege chamadas internas.
            logger.warning("Gatilho fora da tabela R4 rejeitado: %s", gatilho)
            gatilho = TipoGatilho.TIMEOUT_DECISAO
        sinal = SinalAlgedonico(
            fonte=fonte,
            nivel=nivel or self.nivel_nome,
            gravidade=gravidade,
            gatilho=gatilho,
            assunto=assunto,
            mensagem=mensagem,
            contexto=contexto or {},
        )
        self._sinais.append(sinal)
        self._registrar_ledger(sinal)
        return sinal

    def disparar_timeout(self, fonte: str, decisao_id: str, assunto: str, prazo_horas: int):
        return self.disparar(
            fonte=fonte,
            gravidade=GravidadeSinal.VERMELHO,
            gatilho=TipoGatilho.TIMEOUT_DECISAO,
            assunto=f"Timeout: {assunto}",
            mensagem=f"Decisão {decisao_id} não resolvida em {prazo_horas}h",
            contexto={"decisao_id": decisao_id, "prazo_horas": prazo_horas},
        )

    def disparar_desvio_orcamento(
        self, fonte: str, recurso: str, orcado: float, gasto: float, nivel_nome: str,
    ):
        return self.disparar(
            fonte=fonte,
            gravidade=GravidadeSinal.AMARELO,
            gatilho=TipoGatilho.DESVIO_ORCAMENTO,
            assunto=f"Desvio orçamentário: {recurso}",
            mensagem=f"{recurso}: orçado {orcado}, gasto {gasto} ({nivel_nome})",
            contexto={"recurso": recurso, "orcado": orcado, "gasto": gasto, "nivel": nivel_nome},
        )

    def disparar_conflito(
        self,
        fonte: str,
        agentes: list[str],
        recurso: str,
        contexto_extra: dict[str, Any] | None = None,
    ):
        contexto = {"agentes": agentes, "recurso": recurso}
        if contexto_extra:
            contexto.update(contexto_extra)
        return self.disparar(
            fonte=fonte,
            gravidade=GravidadeSinal.AMARELO,
            gatilho=TipoGatilho.CONFLITO_AGENTES,
            assunto=f"Conflito entre agentes: {recurso}",
            mensagem=f"Agentes {', '.join(agentes)} disputam recurso: {recurso}",
            contexto=contexto,
        )

    def disparar_oportunidade(
        self, fonte: str, oportunidade: str, impacto: str,
    ):
        return self.disparar(
            fonte=fonte,
            gravidade=GravidadeSinal.VERDE,
            gatilho=TipoGatilho.OPORTUNIDADE_ESTRATEGICA,
            assunto=f"Oportunidade: {oportunidade}",
            mensagem=impacto,
            contexto={"oportunidade": oportunidade, "impacto": impacto},
        )

    def responder(self, sinal_id: str, resolucao: str) -> bool:
        for s in self._sinais:
            if s.id == sinal_id:
                s.respondido_em = datetime.now(timezone.utc).isoformat()
                s.resolucao = resolucao
                self._registrar_ledger(s)
                return True
        return False

    def pendentes(self, gravidade: GravidadeSinal | None = None) -> list[SinalAlgedonico]:
        filtrados = [s for s in self._sinais if s.resolucao is None]
        if gravidade:
            filtrados = [s for s in filtrados if s.gravidade == gravidade]
        return sorted(filtrados, key=lambda s: s.timestamp, reverse=True)

    def todos(self) -> list[SinalAlgedonico]:
        return sorted(self._sinais, key=lambda s: s.timestamp, reverse=True)

    def verificar_timeouts(self, decisoes_pendentes: list[Any]) -> list[SinalAlgedonico]:
        """Dispara TIMEOUT_DECISAO uma única vez por decisão expirada."""
        ja_sinalizadas = {
            s.contexto.get("decisao_id")
            for s in self._sinais
            if s.gatilho == TipoGatilho.TIMEOUT_DECISAO
        }
        disparados = []
        for d in decisoes_pendentes:
            if d.id in ja_sinalizadas:
                continue
            delta = datetime.now(timezone.utc) - datetime.fromisoformat(d.criado_em)
            if delta.total_seconds() > PRAZO_RESPOSTA_HORAS[GravidadeSinal.VERMELHO] * 3600:
                s = self.disparar_timeout(d.solicitante, d.id, d.assunto, PRAZO_RESPOSTA_HORAS[GravidadeSinal.VERMELHO])
                disparados.append(s)
        return disparados

    def _registrar_ledger(self, sinal: SinalAlgedonico) -> None:
        """Anexa o estado do sinal ao ledger (se habilitado via CDA_STATE_DIR)."""
        try:
            from viableos.cda.provenancia import ledger
            ledger.registrar("sinal_estado", {
                "nivel": self.nivel_nome,
                "sinal": asdict(sinal),
            })
        except Exception as e:  # o núcleo nunca quebra por falha de ledger
            logger.warning("Ledger: falha ao registrar sinal: %s", e)

    def _aplicar_estado(self, dados: dict[str, Any]) -> None:
        """Replay do ledger — reconstrói sinal a partir do estado persistido."""
        from viableos.cda.provenancia import _sinal_de_dict

        sinal = _sinal_de_dict(dados)
        for i, s in enumerate(self._sinais):
            if s.id == sinal.id:
                self._sinais[i] = sinal
                return
        self._sinais.append(sinal)

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "id": s.id,
                "fonte": s.fonte,
                "nivel": s.nivel,
                "gravidade": s.gravidade.value,
                "gatilho": s.gatilho.value,
                "assunto": s.assunto,
                "mensagem": s.mensagem,
                "timestamp": s.timestamp,
                "respondido": s.resolucao is not None,
            }
            for s in self.todos()
        ]


# Singleton de compatibilidade — a árvore usa canal por nível (NivelVSM.canal);
# novos código devem escrever no canal do nível, não aqui (ver seed.py).
canal = CanalAlgedonico()
