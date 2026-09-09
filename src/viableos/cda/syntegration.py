"""Protocolo Team Syntegrity para a CDA — deliberação não-hierárquica.

Baseado em Beer's Team Syntegrity, adaptado para agentes de IA.
5 fases: OSI → Jostle → Auction → Reverberação ×3 → Resolução.

Integração LLM + trigger manual para Diretora.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FaseSyntegration(str, Enum):
    PROPOSTA = "proposta"
    OSI = "osi"
    JOSTLE = "jostle"
    LEILAO = "leilao"
    REVERB_1 = "reverb_1"
    REVERB_2 = "reverb_2"
    REVERB_3 = "reverb_3"
    RESOLUCAO = "resolucao"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


_PROXIMA_FASE: dict[FaseSyntegration, FaseSyntegration] = {
    FaseSyntegration.PROPOSTA: FaseSyntegration.OSI,
    FaseSyntegration.OSI: FaseSyntegration.JOSTLE,
    FaseSyntegration.JOSTLE: FaseSyntegration.LEILAO,
    FaseSyntegration.LEILAO: FaseSyntegration.REVERB_1,
    FaseSyntegration.REVERB_1: FaseSyntegration.REVERB_2,
    FaseSyntegration.REVERB_2: FaseSyntegration.REVERB_3,
    FaseSyntegration.REVERB_3: FaseSyntegration.RESOLUCAO,
    FaseSyntegration.RESOLUCAO: FaseSyntegration.CONCLUIDO,
}


@dataclass
class ResultadoTopico:
    """Resultado da deliberação sobre um tópico."""
    topico: str
    declaracao: str = ""
    recomendacoes: list[str] = field(default_factory=list)
    players: list[str] = field(default_factory=list)
    critics: list[str] = field(default_factory=list)


@dataclass
class ProtocoloSyntegration:
    """Máquina de estados para um evento Syntegration."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gatilho: str = ""
    proposto_por: str = ""
    inicio_tick: int = 0
    conclusao_tick: int | None = None
    fase: FaseSyntegration = FaseSyntegration.PROPOSTA

    participantes: list[str] = field(default_factory=list)
    nivel_participantes: dict[str, str] = field(default_factory=dict)

    declaracoes_importancia: dict[str, str] = field(default_factory=dict)

    topicos: list[str] = field(default_factory=list)

    papeis: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    # {nome_agente: [{"topico": "X", "papel": "player"}, ...]}

    log_reverberacao: list[dict[str, Any]] = field(default_factory=list)

    resultados: list[ResultadoTopico] = field(default_factory=list)

    max_topicos: int = 4
    ciclos_reverberacao: int = 3

    @property
    def esta_ativo(self) -> bool:
        return self.fase not in (
            FaseSyntegration.CONCLUIDO,
            FaseSyntegration.CANCELADO,
            FaseSyntegration.PROPOSTA,
        )

    @property
    def esta_concluido(self) -> bool:
        return self.fase in (FaseSyntegration.CONCLUIDO, FaseSyntegration.CANCELADO)

    def avancar(self, agentes: list[dict[str, Any]], tick: int = 0) -> FaseSyntegration:
        """Avança para a próxima fase, executando a lógica da fase atual."""
        if self.fase in (FaseSyntegration.CONCLUIDO, FaseSyntegration.CANCELADO):
            return self.fase

        if self.fase == FaseSyntegration.PROPOSTA:
            self._iniciar(agentes, tick)
        elif self.fase == FaseSyntegration.OSI:
            self._executar_osi(agentes)
        elif self.fase == FaseSyntegration.JOSTLE:
            self._executar_jostle()
        elif self.fase == FaseSyntegration.LEILAO:
            self._executar_leilao()
        elif self.fase in (
            FaseSyntegration.REVERB_1,
            FaseSyntegration.REVERB_2,
            FaseSyntegration.REVERB_3,
        ):
            self._executar_reverberacao()
        elif self.fase == FaseSyntegration.RESOLUCAO:
            self._executar_resolucao()

        proxima = _PROXIMA_FASE.get(self.fase)
        if proxima:
            self.fase = proxima
            logger.info("Syntegration %s → fase %s", self.id, self.fase.value)

        if self.fase == FaseSyntegration.CONCLUIDO:
            self.conclusao_tick = tick

        return self.fase

    # ── Handlers de fase ──────────────────────────────────────

    def _iniciar(self, agentes: list[dict[str, Any]], tick: int) -> None:
        self.inicio_tick = tick
        self.participantes = [a.get("nome", a.get("name", "?")) for a in agentes]
        self.nivel_participantes = {
            a.get("nome", a.get("name", "?")): a.get("tipo", a.get("system_level", "?"))
            for a in agentes
        }
        logger.info(
            "Syntegration %s iniciada: %d participantes, gatilho=%s",
            self.id, len(self.participantes), self.gatilho,
        )

    def _executar_osi(self, agentes: list[dict[str, Any]]) -> None:
        """OSI: cada agente produz uma declaração de importância."""
        for agente in agentes:
            nome = agente.get("nome", agente.get("name", "?"))
            tipo = agente.get("tipo", agente.get("system_level", "?"))
            proposito = agente.get("proposito", agente.get("purpose", ""))
            declaracao = f"[{tipo.upper()}] {proposito}"
            self.declaracoes_importancia[nome] = declaracao

        logger.info("OSI completa: %d declarações coletadas", len(self.declaracoes_importancia))

    def _executar_jostle(self) -> None:
        """Jostle: agrupa declarações em N tópicos via extração de palavras-chave."""
        palavras: list[str] = []
        stop_words = {
            "para", "como", "com", "que", "uma", "dos", "das", "pelo",
            "sobre", "entre", "todos", "todo", "toda", "esta", "este",
            "isso", "esse", "essa", "aqui", "onde", "quando", "porque",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "and", "or", "but",
            "in", "on", "at", "to", "for", "of", "with", "by", "from",
            "current", "state:", "|",
        }

        for declaracao in self.declaracoes_importancia.values():
            palavras_topico = [
                w.strip("[](),.:;'\"").lower()
                for w in declaracao.split()
                if len(w) > 3 and w.strip("[](),.:;'\"").lower() not in stop_words
            ]
            palavras.extend(palavras_topico)

        counter = Counter(palavras)
        top_keywords = [word for word, _ in counter.most_common(self.max_topicos * 2)]

        topicos: list[str] = []
        vistos: set[str] = set()
        for kw in top_keywords:
            if kw not in vistos and len(topicos) < self.max_topicos:
                topicos.append(kw.title())
                vistos.add(kw)

        if len(topicos) < 2:
            topicos = ["Operações", "Estratégia"]

        self.topicos = topicos
        logger.info("Jostle completa: %d tópicos — %s", len(topicos), topicos)

    def _executar_leilao(self) -> None:
        """Leilão: atribui agentes a tópicos como Player ou Critic."""
        n_topicos = len(self.topicos)

        for nome in self.participantes:
            self.papeis[nome] = []

        for i, nome in enumerate(self.participantes):
            idx_topico = i % n_topicos
            self.papeis[nome].append({
                "topico": self.topicos[idx_topico],
                "papel": "player",
            })

        for i, nome in enumerate(self.participantes):
            idx_critic = (i + 1) % n_topicos
            if self.topicos[idx_critic] != self.papeis[nome][0]["topico"]:
                self.papeis[nome].append({
                    "topico": self.topicos[idx_critic],
                    "papel": "critic",
                })

        for nome, lista in self.papeis.items():
            papel_str = ", ".join(f"{r['papel']} em '{r['topico']}'" for r in lista)
            logger.debug("  %s: %s", nome, papel_str)

        logger.info(
            "Leilão completo: %d agentes atribuídos a %d tópicos",
            len(self.participantes), n_topicos,
        )

    def _executar_reverberacao(self) -> None:
        """Reverberação: Players discutem, Critics desafiam."""
        ciclo = {
            FaseSyntegration.REVERB_1: 1,
            FaseSyntegration.REVERB_2: 2,
            FaseSyntegration.REVERB_3: 3,
        }.get(self.fase, 0)

        log_ciclo: dict[str, Any] = {"ciclo": ciclo, "topicos": {}}

        for topico in self.topicos:
            players = [
                nome for nome, papeis in self.papeis.items()
                if any(r["topico"] == topico and r["papel"] == "player" for r in papeis)
            ]
            critics = [
                nome for nome, papeis in self.papeis.items()
                if any(r["topico"] == topico and r["papel"] == "critic" for r in papeis)
            ]

            posicao = f"Ciclo {ciclo} posição sobre '{topico}' por {', '.join(players)}"
            critica = f"Crítica de {', '.join(critics)}" if critics else "Sem crítica"

            log_ciclo["topicos"][topico] = {
                "players": players,
                "critics": critics,
                "posicao": posicao,
                "critica": critica,
            }

        self.log_reverberacao.append(log_ciclo)
        logger.info("Reverberação ciclo %d completa para %d tópicos", ciclo, len(self.topicos))

    def _executar_resolucao(self) -> None:
        """Resolução: sintetiza resultados por tópico."""
        for topico in self.topicos:
            posicoes: list[str] = []
            for log in self.log_reverberacao:
                dados_topico = log.get("topicos", {}).get(topico, {})
                if dados_topico.get("posicao"):
                    posicoes.append(dados_topico["posicao"])

            players = [
                nome for nome, papeis in self.papeis.items()
                if any(r["topico"] == topico and r["papel"] == "player" for r in papeis)
            ]
            critics = [
                nome for nome, papeis in self.papeis.items()
                if any(r["topico"] == topico and r["papel"] == "critic" for r in papeis)
            ]

            resultado = ResultadoTopico(
                topico=topico,
                declaracao=f"Consenso sobre '{topico}' após {len(posicoes)} ciclos de reverberação",
                recomendacoes=[f"Ação para '{topico}'"],
                players=players,
                critics=critics,
            )
            self.resultados.append(resultado)

        logger.info(
            "Resolução completa: %d resultados produzidos", len(self.resultados),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "gatilho": self.gatilho,
            "proposto_por": self.proposto_por,
            "fase": self.fase.value,
            "participantes": len(self.participantes),
            "topicos": self.topicos,
            "resultados": [
                {
                    "topico": r.topico,
                    "declaracao": r.declaracao,
                    "recomendacoes": r.recomendacoes,
                    "players": r.players,
                    "critics": r.critics,
                }
                for r in self.resultados
            ],
            "log_reverberacao": self.log_reverberacao,
        }


# ── Funções de trigger ──────────────────────────────────────────


def verificar_gatilho_sinais_convergentes_s4(
    agentes: list[dict[str, Any]], limiar: int = 3,
) -> str | None:
    """Verifica se S4 detectou sinais convergentes (suficientes para Syntegration)."""
    for agente in agentes:
        tipo = agente.get("tipo", agente.get("system_level", ""))
        if "s4" in tipo.lower():
            sinais = agente.get("sinais_detectados", agente.get("signals_detected", 0))
            if sinais >= limiar:
                return "s4_converging_signals"
    return None


def verificar_gatilho_falhas_coordenacao(
    agentes: list[dict[str, Any]], limiar: int = 3,
) -> str | None:
    """Verifica se S2 detectou muitas falhas de coordenação."""
    for agente in agentes:
        tipo = agente.get("tipo", agente.get("system_level", ""))
        if "s2" in tipo.lower():
            conflitos = agente.get("conflitos_detectados", agente.get("conflicts_detected", 0))
            if conflitos >= limiar:
                return "s3_coordination_failures"
    return None


def verificar_gatilho_erros_correlacionados(
    agentes: list[dict[str, Any]], limiar: int = 3,
) -> str | None:
    """Verifica se S3* detectou erros correlacionados (mesmo provider)."""
    for agente in agentes:
        tipo = agente.get("tipo", agente.get("system_level", ""))
        if "s3" in tipo.lower() and "audit" in tipo.lower():
            achados = agente.get("achados_auditoria", agente.get("audit_results", []))
            nao_passaram = [r for r in achados if r.get("status") != "pass"]
            if len(nao_passaram) >= limiar:
                return "s3star_correlated_errors"
    return None


def verificar_gatilho_alerta_s5(
    contagem_algedonica: int, limiar: int = 3,
) -> str | None:
    """Verifica se S5 recebeu muitos sinais algêdonicos."""
    if contagem_algedonica >= limiar:
        return "s5_balance_alert"
    return None


# ── Gerenciador de Syntegration ────────────────────────────────


class GerenciadorSyntegration:
    """Gerencia protocolos Syntegration na CDA.

    Suporta:
    - Trigger automático (4 condições)
    - Trigger manual (Diretora inicia)
    - Integração com LLM para OSI/reverberação reais
    """

    def __init__(self):
        self._protocolos: dict[str, ProtocoloSyntegration] = {}
        self._historico: list[dict[str, Any]] = []

    def iniciar_manual(
        self,
        gatilho: str,
        proposto_por: str,
        agentes: list[dict[str, Any]],
        tick: int = 0,
    ) -> ProtocoloSyntegration:
        """Diretora inicia Syntegration manualmente."""
        protocolo = ProtocoloSyntegration(
            gatilho=gatilho,
            proposto_por=proposto_por,
        )
        self._protocolos[protocolo.id] = protocolo
        protocolo.avancar(agentes, tick)
        return protocolo

    def verificar_automatico(
        self,
        agentes: list[dict[str, Any]],
        contagem_algedonica: int = 0,
        limiar: int = 3,
        tick: int = 0,
    ) -> ProtocoloSyntegration | None:
        """Verifica se alguma condição de trigger automático é atingida."""
        gatilho = (
            verificar_gatilho_sinais_convergentes_s4(agentes, limiar)
            or verificar_gatilho_falhas_coordenacao(agentes, limiar)
            or verificar_gatilho_erros_correlacionados(agentes, limiar)
            or verificar_gatilho_alerta_s5(contagem_algedonica, limiar)
        )

        if gatilho:
            return self.iniciar_manual(gatilho, "auto", agentes, tick)
        return None

    def avancar(self, protocolo_id: str, agentes: list[dict[str, Any]], tick: int = 0) -> FaseSyntegration | None:
        """Avança protocolo existente."""
        protocolo = self._protocolos.get(protocolo_id)
        if protocolo:
            resultado = protocolo.avancar(agentes, tick)
            if protocolo.esta_concluido:
                self._historico.append(protocolo.to_dict())
            return resultado
        return None

    def cancelar(self, protocolo_id: str) -> bool:
        """Cancela protocolo em andamento."""
        protocolo = self._protocolos.get(protocolo_id)
        if protocolo and not protocolo.esta_concluido:
            protocolo.fase = FaseSyntegration.CANCELADO
            self._historico.append(protocolo.to_dict())
            return True
        return False

    def obter_ativos(self) -> list[dict[str, Any]]:
        """Retorna protocolos ativos."""
        return [
            p.to_dict() for p in self._protocolos.values()
            if p.esta_ativo
        ]

    def obter_historico(self) -> list[dict[str, Any]]:
        """Retorna histórico de protocolos concluídos."""
        return self._historico.copy()

    def limpar_concluidos(self) -> int:
        """Remove protocolos concluídos/cancelados. Retorna quantos foram removidos."""
        ids_remover = [
            pid for pid, p in self._protocolos.items()
            if p.esta_concluido
        ]
        for pid in ids_remover:
            del self._protocolos[pid]
        return len(ids_remover)


# Singleton
gerenciador_syntegration = GerenciadorSyntegration()
