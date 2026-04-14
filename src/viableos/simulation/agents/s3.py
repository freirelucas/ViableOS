"""S3 Optimizer Agent — resource allocation and performance control."""

from __future__ import annotations

from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S3Agent(VSMAgent):
    """S3 Optimizer: monitors performance, allocates resources, generates reports."""

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s3",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s3"]),
            llm_fn=kwargs.get("llm_fn"),
        )
        self.resource_allocation: str = config.get("resource_allocation", "")
        self.reporting_rhythm: str = config.get("reporting_rhythm", "weekly")
        self.kpi_list: list[str] = config.get("kpi_list", [])
        self.reports_generated: int = 0

    def deliberate(self) -> None:
        """Collect S1 statuses (via S2), analyze, and issue directives."""
        # Collect reports from S2 escalations and S1 statuses
        escalations = [m for m in self.inbox if "escalation" in m.content.lower()]
        status_reports = [m for m in self.inbox if m.performative == "inform" and m not in escalations]

        # Update beliefs with current system state
        self.beliefs["escalation_count"] = len(escalations)
        self.beliefs["status_reports"] = len(status_reports)

        # Generate periodic report
        self.reports_generated += 1
        self.beliefs["last_report_tick"] = self.model.tick

        # If escalations detected, consider mode switch
        if len(escalations) >= 3:
            self.send_message(
                receiver=self._find_agent("s5"),
                receiver_level="s5",
                performative="alert",
                content=f"Multiple escalations ({len(escalations)}) — consider elevated mode",
                protocol="algedonic",
            )

    def _find_agent(self, level: str) -> str:
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == level:
                return agent.name
        return f"{level}_agent"
