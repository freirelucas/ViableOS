"""VSM viability metrics collector built on Mesa's DataCollector."""

from __future__ import annotations

from typing import Any

import mesa


class VSMDataCollector(mesa.DataCollector):
    """Collects viability metrics per tick as pandas DataFrames."""

    def __init__(self, model: Any) -> None:
        super().__init__(
            model_reporters={
                "tick": lambda m: m.tick,
                "mode": lambda m: m.mode,
                "messages_sent": lambda m: m.message_bus.total_sent,
                "messages_delivered": lambda m: m.message_bus.total_delivered,
                "messages_blocked": lambda m: m.message_bus.total_blocked,
                "algedonic_signals": lambda m: m.message_bus.algedonic_count,
                "active_agents": lambda m: sum(
                    1 for a in m.agents if getattr(a, "step_count", 0) > 0
                ),
            },
            agent_reporters={
                "name": "name",
                "system_level": "system_level",
                "step_count": "step_count",
                "inbox_size": lambda a: len(a.inbox),
                "beliefs_count": lambda a: len(a.beliefs),
                "tasks_completed": lambda a: getattr(a, "tasks_completed", 0),
            },
        )
