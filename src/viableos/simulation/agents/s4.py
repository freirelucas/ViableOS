"""S4 Scout Agent — environmental scanning and intelligence."""

from __future__ import annotations

from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S4Agent(VSMAgent):
    """S4 Scout: monitors external environment (competitors, tech, regulation).

    Generates strategic intelligence briefs for S5.
    """

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s4",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s4"]),
            llm_fn=kwargs.get("llm_fn"),
        )
        monitoring = config.get("monitoring", {})
        self.competitors: list[str] = monitoring.get("competitors", [])
        self.technology: list[str] = monitoring.get("technology", [])
        self.regulation: list[str] = monitoring.get("regulation", [])
        self.signals_detected: int = 0
        self.briefs_sent: int = 0

    def deliberate(self) -> None:
        """Scan environment model and generate intelligence."""
        env = getattr(self.model, "environment", None)
        new_signals: list[dict] = []
        if env is not None and hasattr(env, "consume_signals"):
            new_signals = env.consume_signals()  # consume clears the buffer
        elif env is not None and hasattr(env, "new_signals"):
            new_signals = env.new_signals
        elif isinstance(env, dict):
            new_signals = env.get("new_signals", [])

        if new_signals:
            self.signals_detected += len(new_signals)
            self.beliefs["recent_signals"] = new_signals

            # High-relevance signals get sent as alerts
            critical = [s for s in new_signals if s.get("relevance", 0) >= 5]
            if critical:
                for sig in critical:
                    self.send_message(
                        receiver=self._find_agent("s5"),
                        receiver_level="s5",
                        performative="alert",
                        content=f"CRITICAL: {sig['title']} — {sig['description']}",
                        protocol="algedonic",
                    )

        # Send periodic strategic brief to S5
        self.briefs_sent += 1
        brief_content = (
            f"Strategic brief (tick {self.model.tick}): "
            f"{self.signals_detected} signals detected, "
            f"monitoring {len(self.competitors)} competitors, "
            f"{len(self.technology)} tech trends, "
            f"{len(self.regulation)} regulation items"
        )
        if new_signals:
            titles = [s.get("title", "?") for s in new_signals[:3]]
            brief_content += f" | New: {'; '.join(titles)}"

        self.send_message(
            receiver=self._find_agent("s5"),
            receiver_level="s5",
            performative="inform",
            content=brief_content,
            protocol="coordination",
        )

    def _find_agent(self, level: str) -> str:
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == level:
                return agent.name
        return f"{level}_agent"
