"""Environment model — the external world that VSM agents observe and act upon.

Provides a scenario-driven environment where events unfold over ticks.
S4 (Scout) scans this environment for signals. S1 units interact with
domain-specific aspects.  Events are pre-scripted per scenario but
can also be injected dynamically (e.g., by human input).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentEvent:
    """An event that occurs in the external environment at a specific tick."""

    tick: int
    category: str  # "legislation", "publication", "data", "technology", "crisis"
    title: str
    description: str
    relevance: int = 3  # 1-5, where 5 = highly relevant
    metadata: dict[str, Any] = field(default_factory=dict)


class Environment:
    """Shared environment model for the VSM simulation.

    Maintains a timeline of events and provides per-tick observation
    to agents.  Events can be pre-loaded from a scenario or injected
    dynamically.
    """

    def __init__(self, scenario: list[dict[str, Any]] | None = None) -> None:
        self._events: list[EnvironmentEvent] = []
        self._active_signals: list[EnvironmentEvent] = []
        self._history: list[EnvironmentEvent] = []

        if scenario:
            for evt in scenario:
                self._events.append(EnvironmentEvent(**evt))
            self._events.sort(key=lambda e: e.tick)

    @property
    def new_signals(self) -> list[dict[str, Any]]:
        """Current tick's active signals (consumed by S4 agent)."""
        return [
            {
                "category": e.category,
                "title": e.title,
                "description": e.description,
                "relevance": e.relevance,
            }
            for e in self._active_signals
        ]

    def step(self, tick: int) -> list[EnvironmentEvent]:
        """Advance environment to this tick. Returns new events."""
        new_events = [e for e in self._events if e.tick == tick]
        self._active_signals = new_events
        self._history.extend(new_events)
        return new_events

    def inject_event(self, event: EnvironmentEvent) -> None:
        """Inject a dynamic event into the timeline."""
        self._events.append(event)
        self._events.sort(key=lambda e: e.tick)

    def get_state(self) -> dict[str, Any]:
        """Return current environment state for agent observation."""
        return {
            "new_signals": self.new_signals,
            "total_events_so_far": len(self._history),
            "categories_seen": list({e.category for e in self._history}),
        }


# ── Pre-built scenarios ───────────────────────────────────────


def policy_research_scenario(total_ticks: int = 100) -> list[dict[str, Any]]:
    """Scenario for IPEA DIEST policy research.

    Simulates a realistic timeline of legislative, academic, and
    data events relevant to digital government research.
    """
    events: list[dict[str, Any]] = []

    # Steady stream of legislation monitoring
    legislation_events = [
        ("Decreto altera EGD 2024-2027", "Mudanças nos pilares de governo digital", 4),
        ("ANPD publica guia de IA no setor público", "Orientações para uso de IA em órgãos federais", 5),
        ("PPA 2024-2027: revisão de meio período", "Atualização das metas de transformação digital", 3),
        ("CGU lança painel de transparência algorítmica", "Nova ferramenta de accountability para IA", 4),
        ("Decreto institui Comitê de IA do Governo Federal", "Governança de IA no executivo federal", 5),
        ("OECD publica Digital Government Index 2026", "Brasil sobe 3 posições no ranking", 5),
        ("TCU audita plataforma gov.br", "Relatório de auditoria sobre identidade digital", 4),
        ("Projeto de Lei sobre dados abertos governamentais", "Novo marco para abertura de dados", 3),
    ]

    # Distribute legislation events across the timeline
    for i, (title, desc, relevance) in enumerate(legislation_events):
        tick = max(2, int(total_ticks * (i + 1) / (len(legislation_events) + 1)))
        events.append({
            "tick": tick,
            "category": "legislation",
            "title": title,
            "description": desc,
            "relevance": relevance,
        })

    # Academic publication events
    publication_events = [
        ("Novo TD IPEA sobre capacidade estatal digital", "publication", 3),
        ("Artigo Scielo: IA e administração pública", "publication", 2),
        ("Relatório CETIC.br: TIC Governo Eletrônico 2025", "data", 4),
        ("IBGE atualiza dados de governo eletrônico municipal", "data", 3),
        ("Tese UnB: neo-institucionalismo e governo digital", "publication", 2),
    ]

    for i, (title, category, relevance) in enumerate(publication_events):
        tick = max(3, int(total_ticks * (i + 0.5) / len(publication_events)))
        events.append({
            "tick": tick,
            "category": category,
            "title": title,
            "description": f"Disponível para análise: {title}",
            "relevance": relevance,
        })

    # Crisis event (if simulation is long enough)
    if total_ticks >= 50:
        events.append({
            "tick": int(total_ticks * 0.7),
            "category": "crisis",
            "title": "Vazamento de dados em sistema federal",
            "description": "Incidente de segurança afeta plataforma gov.br. "
                          "Impacto direto na pesquisa sobre governo digital e LGPD.",
            "relevance": 5,
        })

    # Technology signals
    if total_ticks >= 30:
        events.append({
            "tick": int(total_ticks * 0.4),
            "category": "technology",
            "title": "LLM multilíngue open-source supera GPT-4 em português",
            "description": "Modelo open-source com desempenho superior "
                          "em tarefas de análise de texto legislativo em PT-BR.",
            "relevance": 4,
        })

    return events


def minimal_scenario(total_ticks: int = 100) -> list[dict[str, Any]]:
    """Minimal scenario for testing — just a few events."""
    return [
        {
            "tick": 5,
            "category": "legislation",
            "title": "New policy announced",
            "description": "A new government policy affects research scope.",
            "relevance": 4,
        },
        {
            "tick": 15,
            "category": "data",
            "title": "Dataset updated",
            "description": "Key data source updated with new figures.",
            "relevance": 3,
        },
        {
            "tick": 30,
            "category": "crisis",
            "title": "Critical finding",
            "description": "Audit reveals data integrity issue.",
            "relevance": 5,
        },
    ]
