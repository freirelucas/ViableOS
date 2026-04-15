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
        self.reports_generated += 1
        self.beliefs["last_report_tick"] = self.model.tick

        # ── The S3→S2→S1 directive loop ──
        # S3 issues work directives to S1 units via S2 (the resource bargain).
        # Each activation, S3 picks an S1 unit and assigns a task based on
        # environment signals and current needs.
        s1_agents = [
            a for a in self.model.agents
            if getattr(a, "system_level", "") == "s1"
        ]
        s2_name = self._find_agent("s2")

        # Check if S4 has detected signals we should act on
        s4_signals = self.beliefs.get("s4_intelligence", [])
        for msg in self.inbox:
            if msg.sender_level == "s4" or (msg.sender_level == "s5" and "intelligence" in msg.content.lower()):
                s4_signals.append(msg.content)
        self.beliefs["s4_intelligence"] = s4_signals[-5:]  # keep last 5

        # Round-robin directives to S1 units
        if s1_agents:
            target_idx = self.reports_generated % len(s1_agents)
            target = s1_agents[target_idx]

            # Build directive based on what we know
            if s4_signals:
                latest_signal = s4_signals[-1][:80]
                directive = f"Analyze and respond to: {latest_signal}"
            else:
                directive = f"Continue routine work on: {target.purpose[:60]}"

            self.send_message(
                receiver=s2_name,
                receiver_level="s2",
                performative="request",
                content=directive,
                protocol="coordination",
            )
            # Tell S2 which S1 to route this to
            self.outbox[-1].metadata["target_s1"] = target.name

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
