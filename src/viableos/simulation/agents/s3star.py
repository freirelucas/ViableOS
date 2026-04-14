"""S3* Auditor Agent — independent verification of S1 outputs."""

from __future__ import annotations

import random
from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S3StarAgent(VSMAgent):
    """S3* Auditor: samples and cross-verifies S1 outputs.

    Uses a DIFFERENT LLM model than S1 to prevent correlated hallucinations.
    """

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s3star",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s3star"]),
            llm_fn=kwargs.get("llm_fn"),
        )
        self.checks: list[dict[str, str]] = config.get("checks", [])
        self.audit_results: list[dict[str, Any]] = []
        self.audits_performed: int = 0

    def deliberate(self) -> None:
        """Sample S1 outputs and audit them."""
        # Find all S1 agents
        s1_agents = [
            a for a in self.model.agents
            if getattr(a, "system_level", "") == "s1"
        ]

        if not s1_agents:
            return

        # Sample 1-2 random S1 agents
        sample = random.sample(s1_agents, min(2, len(s1_agents)))

        for agent in sample:
            result = self._audit_agent(agent)
            self.audit_results.append(result)
            self.audits_performed += 1

        # Report findings to S3
        findings = [r for r in self.audit_results[-len(sample):] if r.get("status") != "pass"]
        if findings:
            self.send_message(
                receiver=self._find_agent("s3"),
                receiver_level="s3",
                performative="inform",
                content=f"Audit findings: {len(findings)} issues in {len(sample)} samples",
                protocol="coordination",
            )

    def _audit_agent(self, agent: Any) -> dict[str, Any]:
        """Audit a single S1 agent's recent output."""
        return {
            "tick": self.model.tick,
            "target": agent.name,
            "tasks_completed": agent.tasks_completed,
            "beliefs_count": len(agent.beliefs),
            "status": "pass",  # In real implementation: LLM cross-verification
        }

    def _find_agent(self, level: str) -> str:
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == level:
                return agent.name
        return f"{level}_agent"
