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

        # If we have a plan, use LLM for execution (if available)
        if self.current_plan:
            llm_result = self._llm_deliberate(
                f"You received a task: '{self.current_plan}'. "
                f"Describe briefly (1-2 sentences) what you would do and what the output would be."
            )
            status = llm_result or f"Completed: '{self.current_plan}'"

            self.send_message(
                receiver=self._find_s2_name(),
                receiver_level="s2",
                performative="inform",
                content=f"Status: {status}",
                protocol="coordination",
            )
            self.beliefs["last_output"] = status
            self.tasks_completed += 1
            self.current_plan = None
        elif self.llm_fn and self.model.tick % 10 == 0:
            # Periodic autonomous work (every 10 ticks if LLM available)
            llm_result = self._llm_deliberate(
                f"Given your purpose ('{self.purpose}'), what proactive "
                f"work should you do right now? Be specific and brief."
            )
            if llm_result:
                self.send_message(
                    receiver=self._find_s2_name(),
                    receiver_level="s2",
                    performative="inform",
                    content=f"Proactive output: {llm_result}",
                    protocol="coordination",
                )
                self.beliefs["last_output"] = llm_result
                self.tasks_completed += 1

    def _find_s2_name(self) -> str:
        """Find the S2 coordinator agent name."""
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == "s2":
                return agent.name
        return "s2_coordinator"
