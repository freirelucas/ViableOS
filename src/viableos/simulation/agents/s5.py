"""S5 Policy Guardian Agent — identity enforcement and value alignment."""

from __future__ import annotations

from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S5Agent(VSMAgent):
    """S5 Policy Guardian: enforces values, manages identity, handles algedonic signals.

    Lowest tick rate — normative decisions are slow and deliberate.
    """

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s5",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s5"]),
            llm_fn=kwargs.get("llm_fn"),
        )
        identity = config.get("identity", {})
        self.values: list[str] = identity.get("values", [])
        self.never_do: list[str] = identity.get("never_do", [])
        self.algedonic_alerts_received: int = 0
        self.policy_decisions: int = 0

    def perceive(self) -> None:
        """Override: S5 always checks for algedonic alerts, even off-cycle."""
        super().perceive()

        # Count algedonic alerts
        alerts = [m for m in self.inbox if m.performative == "alert"]
        self.algedonic_alerts_received += len(alerts)

        if alerts:
            self.beliefs["pending_alerts"] = [
                {"from": m.sender, "content": m.content} for m in alerts
            ]

    def deliberate(self) -> None:
        """Process alerts, check value alignment, enforce policy."""
        # Handle algedonic alerts (high priority)
        pending = self.beliefs.get("pending_alerts", [])
        for alert in pending:
            self.policy_decisions += 1
            # In production: LLM evaluates alert against values/never_do
            self.beliefs.setdefault("alert_log", []).append({
                "tick": self.model.tick,
                "from": alert["from"],
                "content": alert["content"],
                "action": "acknowledged",
            })

        self.beliefs.pop("pending_alerts", None)

        # Periodic identity broadcast to S3
        intelligence = [m for m in self.inbox if m.sender_level == "s4"]
        if intelligence:
            self.beliefs["latest_intelligence"] = [m.content for m in intelligence]

        # Send policy guidance to S3
        self.send_message(
            receiver=self._find_agent("s3"),
            receiver_level="s3",
            performative="inform",
            content=f"Policy check (tick {self.model.tick}): "
                    f"{self.algedonic_alerts_received} total alerts, "
                    f"{self.policy_decisions} decisions made",
            protocol="coordination",
        )

    def _find_agent(self, level: str) -> str:
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == level:
                return agent.name
        return f"{level}_agent"
