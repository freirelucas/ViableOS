"""Multi-rate VSM scheduler with event-driven interrupts."""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Beer's tempo hierarchy: S2 (nervous system) is faster than S1 (organs).
DEFAULT_TICK_RATES: dict[str, int] = {
    "s2": 1,  # Coordination: every tick (fastest)
    "s1": 2,  # Operations: every 2 ticks
    "s4": 4,  # Intelligence: every 4 ticks
    "s3star": 8,  # Audit: every 8 ticks
    "s3": 14,  # Control: every 14 ticks (~weekly)
    "s5": 50,  # Policy: every 50 ticks (normative, slow)
}


@dataclass(order=True)
class ScheduledEvent:
    """An event scheduled for a specific tick."""

    tick: int
    priority: int = 0
    event_type: str = field(compare=False, default="")
    target_agent: str = field(compare=False, default="")
    data: dict[str, Any] = field(compare=False, default_factory=dict)


class VSMScheduler:
    """Multi-rate scheduler that activates agents at different frequencies.

    Each agent has a ``tick_rate`` — it is activated only when
    ``tick % tick_rate == 0``.  Within each tick, agents are activated
    in priority order (S5 first, S1 last) so that policy decisions
    propagate downward within the same tick.

    An event queue allows out-of-cycle activations (algedonic signals,
    syntegration triggers).
    """

    def __init__(self) -> None:
        self._agents: list[Any] = []
        self._event_queue: list[ScheduledEvent] = []

    def add(self, agent: Any) -> None:
        self._agents.append(agent)

    def remove(self, agent: Any) -> None:
        self._agents = [a for a in self._agents if a is not agent]

    @property
    def agents(self) -> list[Any]:
        return list(self._agents)

    def schedule_event(self, event: ScheduledEvent) -> None:
        """Schedule an event for a future tick."""
        heapq.heappush(self._event_queue, event)

    def step(self, tick: int) -> None:
        """Activate agents for this tick, processing events first."""
        # 1. Process events scheduled for this tick
        while self._event_queue and self._event_queue[0].tick <= tick:
            event = heapq.heappop(self._event_queue)
            self._handle_event(event)

        # 2. Regular multi-rate activation (priority order: S5 → S1)
        for agent in sorted(self._agents, key=lambda a: a.priority):
            if tick % agent.tick_rate == 0:
                agent.step()

    def _handle_event(self, event: ScheduledEvent) -> None:
        """Handle an event-driven activation."""
        if event.target_agent:
            for agent in self._agents:
                if agent.name == event.target_agent:
                    logger.info(
                        "Event %s → activating %s (out-of-cycle)",
                        event.event_type, agent.name,
                    )
                    agent.step()
                    return
            logger.warning("Event target %r not found", event.target_agent)
        else:
            logger.info("Broadcast event %s", event.event_type)
