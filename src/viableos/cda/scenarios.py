"""Cenários IPEA + simulador de cenários para a CDA.

Permite que a Diretora teste decisões antes de executar.
Baseado em simulation/environment.py (sem dependência Mesa).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EventoCenario:
    """Um evento que ocorre no ambiente externo em tick específico."""
    tick: int
    categoria: str  # "legislacao", "publicacao", "dados", "tecnologia", "crise"
    titulo: str
    descricao: str
    relevancia: int = 3  # 1-5, onde 5 = altamente relevante
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultadoSimulacao:
    """Resultado de uma simulação de cenário."""
    cenario_nome: str
    ticks_simulados: int
    eventos_processados: int
    sinais_gerados: int
    decisoes_necessarias: int
    metricas: dict[str, Any] = field(default_factory=dict)
    log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cenario": self.cenario_nome,
            "ticks": self.ticks_simulados,
            "eventos": self.eventos_processados,
            "sinais": self.sinais_gerados,
            "decisoes": self.decisoes_necessarias,
            "metricas": self.metricas,
            "log": self.log[-20:],  # Últimas 20 entradas
        }


class CenarioIPEA:
    """Cenário realista para operações da CDA no contexto IPEA."""

    def __init__(self, nome: str, eventos: list[dict[str, Any]] | None = None):
        self.nome = nome
        self._eventos: list[EventoCenario] = []
        if eventos:
            for evt in eventos:
                self._eventos.append(EventoCenario(**evt))
            self._eventos.sort(key=lambda e: e.tick)

    @property
    def total_eventos(self) -> int:
        return len(self._eventos)

    def eventos_em(self, tick: int) -> list[EventoCenario]:
        """Retorna eventos que ocorrem neste tick."""
        return [e for e in self._eventos if e.tick == tick]

    def injetar_evento(self, evento: dict[str, Any]) -> None:
        """Injeta um evento dinâmico no cenário."""
        self._eventos.append(EventoCenario(**evento))
        self._eventos.sort(key=lambda e: e.tick)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "total_eventos": self.total_eventos,
            "eventos": [
                {
                    "tick": e.tick,
                    "categoria": e.categoria,
                    "titulo": e.titulo,
                    "relevancia": e.relevancia,
                }
                for e in self._eventos
            ],
        }


class SimuladorCenarios:
    """Simulador de cenários para a CDA.

    Roda N ticks com um cenário e coleta métricas.
    A Diretora pode testar decisões antes de executar.
    """

    def __init__(self):
        self._cenarios: dict[str, CenarioIPEA] = {}
        self._simulacoes: list[ResultadoSimulacao] = []
        self._cenario_ativo: CenarioIPEA | None = None
        self._registrar_cenarios_padrao()

    def _registrar_cenarios_padrao(self) -> None:
        """Registra cenários pré-definidos para IPEA."""
        self._cenarios["ipea_digital"] = _cenario_ipea_digital()
        self._cenarios["crise_seguranca"] = _cenario_crise_seguranca()
        self._cenarios["legislacao_ia"] = _cenario_legislacao_ia()

    def obter_cenario(self, nome: str) -> CenarioIPEA | None:
        return self._cenarios.get(nome)

    def listar_cenarios(self) -> list[dict[str, Any]]:
        return [
            {"nome": c.nome, "eventos": c.total_eventos}
            for c in self._cenarios.values()
        ]

    def simular(
        self,
        nome_cenario: str,
        ticks: int = 100,
        agentes: list[dict[str, Any]] | None = None,
    ) -> ResultadoSimulacao:
        """Roda simulação de cenário por N ticks.

        Args:
            nome_cenario: nome do cenário a simular
            ticks: número de ticks a simular
            agentes: lista de agentes da CDA (para simular comportamento)
        """
        cenario = self._cenarios.get(nome_cenario)
        if not cenario:
            raise ValueError(f"Cenário '{nome_cenario}' não encontrado")

        resultado = ResultadoSimulacao(
            cenario_nome=nome_cenario,
            ticks_simulados=ticks,
            eventos_processados=0,
            sinais_gerados=0,
            decisoes_necessarias=0,
        )

        sinais_por_tick: dict[int, list] = {}
        decisoes_por_tick: dict[int, list] = {}

        for tick in range(1, ticks + 1):
            eventos = cenario.eventos_em(tick)
            resultado.eventos_processados += len(eventos)

            for evento in eventos:
                # Sinais de alta relevância (>= 4) geram sinais algêdonicos
                if evento.relevancia >= 4:
                    resultado.sinais_gerados += 1
                    if tick not in sinais_por_tick:
                        sinais_por_tick[tick] = []
                    sinais_por_tick[tick].append({
                        "evento": evento.titulo,
                        "relevancia": evento.relevancia,
                        "categoria": evento.categoria,
                    })

                # Eventos de crise geram decisões
                if evento.categoria == "crise":
                    resultado.decisoes_necessarias += 1
                    if tick not in decisoes_por_tick:
                        decisoes_por_tick[tick] = []
                    decisoes_por_tick[tick].append({
                        "evento": evento.titulo,
                        "urgencia": "alta" if evento.relevancia >= 5 else "media",
                    })

            # Log de atividade
            if eventos or tick % 10 == 0:
                resultado.log.append({
                    "tick": tick,
                    "eventos": len(eventos),
                    "sinais_acumulados": resultado.sinais_gerados,
                    "decisoes_acumuladas": resultado.decisoes_necessarias,
                })

        # Métricas consolidadas
        resultado.metricas = {
            "densidade_eventos": round(resultado.eventos_processados / ticks, 2),
            "taxa_sinais": round(resultado.sinais_gerados / ticks, 4),
            "taxa_decisoes": round(resultado.decisoes_necessarias / ticks, 4),
            "pico_sinais": max((len(s) for s in sinais_por_tick.values()), default=0),
            "pico_decisoes": max((len(d) for d in decisoes_por_tick.values()), default=0),
        }

        self._simulacoes.append(resultado)
        return resultado

    def inyectar_evento(self, nome_cenario: str, evento: dict[str, Any]) -> None:
        """Injeta evento dinâmico em cenário."""
        cenario = self._cenarios.get(nome_cenario)
        if cenario:
            cenario.injetar_evento(evento)

    def obter_historico(self) -> list[dict[str, Any]]:
        """Retorna histórico de simulações."""
        return [r.to_dict() for r in self._simulacoes]


# ── Cenários pré-definidos ──────────────────────────────────────


def _cenario_ipea_digital() -> CenarioIPEA:
    """Cenário: transformação digital do IPEA."""
    eventos = [
        {"tick": 5, "categoria": "legislacao", "titulo": "Decreto altera EGD 2024-2027",
         "descricao": "Mudanças nos pilares de governo digital", "relevancia": 4},
        {"tick": 12, "categoria": "legislacao", "titulo": "ANPD publica guia de IA no setor público",
         "descricao": "Orientações para uso de IA em órgãos federais", "relevancia": 5},
        {"tick": 20, "categoria": "dados", "titulo": "CETIC.br: TIC Governo Eletrônico 2025",
         "descricao": "Disponível para análise", "relevancia": 4},
        {"tick": 30, "categoria": "publicacao", "titulo": "TD IPEA sobre capacidade estatal digital",
         "descricao": "Novo documento técnico disponível", "relevancia": 3},
        {"tick": 40, "categoria": "tecnologia", "titulo": "LLM multilíngue open-source supera GPT-4 em PT",
         "descricao": "Modelo com desempenho superior em análise legislativa", "relevancia": 4},
        {"tick": 55, "categoria": "crise", "titulo": "Vazamento de dados em sistema federal",
         "descricao": "Incidente de segurança afeta plataforma gov.br", "relevancia": 5},
        {"tick": 70, "categoria": "legislacao", "titulo": "CGU lança painel de transparência algorítmica",
         "descricao": "Nova ferramenta de accountability para IA", "relevancia": 4},
        {"tick": 85, "categoria": "legislacao", "titulo": "OECD publica Digital Government Index 2026",
         "descricao": "Brasil sobe 3 posições no ranking", "relevancia": 5},
    ]
    return CenarioIPEA("ipea_digital", eventos)


def _cenario_crise_seguranca() -> CenarioIPEA:
    """Cenário: crise de segurança da informação."""
    eventos = [
        {"tick": 3, "categoria": "crise", "titulo": "Tentativa de phishing em servidores IPEA",
         "descricao": "Ataque direcionado a pesquisadores", "relevancia": 4},
        {"tick": 8, "categoria": "crise", "titulo": "Vulnerabilidade em biblioteca Python usada pela CDA",
         "descricao": "CVE crítica publicada", "relevancia": 5},
        {"tick": 15, "categoria": "legislacao", "titulo": "ANPD notifica IPEA sobre incidente",
         "descricao": "Notificação de violação de dados pessoais", "relevancia": 5},
        {"tick": 25, "categoria": "dados", "titulo": "Auditoria revela dados expostos",
         "descricao": "Dados de bolsistas acessíveis publicamente", "relevancia": 5},
    ]
    return CenarioIPEA("crise_seguranca", eventos)


def _cenario_legislacao_ia() -> CenarioIPEA:
    """Cenário: regulação de IA no Brasil."""
    eventos = [
        {"tick": 10, "categoria": "legislacao", "titulo": "Marco Legal da IA avança no Senado",
         "descricao": "Projeto de lei sobre IA é aprovado em comissão", "relevancia": 4},
        {"tick": 25, "categoria": "legislacao", "titulo": "Regulamentação de IA no setor público",
         "descricao": "Decreto define regras para uso de IA em órgãos federais", "relevancia": 5},
        {"tick": 40, "categoria": "publicacao", "titulo": "Relatório FGV: Impacto da IA no serviço público",
         "descricao": "Estudo revela potencial de automação de 30% dos processos", "relevancia": 4},
        {"tick": 60, "categoria": "legislacao", "titulo": "Comitê de IA do Governo Federal publica diretrizes",
         "descricao": "Diretrizes para uso responsável de IA na administração pública", "relevancia": 5},
        {"tick": 80, "categoria": "tecnologia", "titulo": "Modelo brasileiro de IA para governo",
         "descricao": "Projeto de LLM treinado em dados públicos brasileiros", "relevancia": 4},
    ]
    return CenarioIPEA("legislacao_ia", eventos)


# Singleton
simulador = SimuladorCenarios()
