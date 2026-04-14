"""S1 Operational Agent — does the actual work."""

from __future__ import annotations

from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S1Agent(VSMAgent):
    """Operational unit that performs domain-specific tasks.

    Uses LLM for deliberation when ``llm_fn`` is provided.
    Falls back to simple rule-based behavior otherwise.
    """

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s1",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s1"]),
            llm_fn=kwargs.get("llm_fn"),
        )
        self.autonomy = config.get("autonomy", "")
        self.weight = config.get("weight", 5)

    def deliberate(self) -> None:
        """Process inbox and decide on next action."""
        # Handle incoming directives from S3 (via S2)
        for msg in self.inbox:
            if msg.performative == "request":
                self.current_plan = f"Execute: {msg.content}"
                self.beliefs["active_task"] = msg.content

        # If we have a plan, report progress to S2
        if self.current_plan:
            self.send_message(
                receiver=self._find_s2_name(),
                receiver_level="s2",
                performative="inform",
                content=f"Status: working on '{self.current_plan}'",
                protocol="coordination",
            )
            self.tasks_completed += 1
            self.current_plan = None

    def _find_s2_name(self) -> str:
        """Find the S2 coordinator agent name."""
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == "s2":
                return agent.name
        return "s2_coordinator"
