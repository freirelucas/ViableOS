"""S2 Coordination Agent — rule-based, no LLM.

S2 is the nervous system: it must be FASTER than S1 (Beer).
It routes messages between S1 units, detects conflicts,
and applies anti-oscillation dampening.  Pure rules, no LLM call.
"""

from __future__ import annotations

from typing import Any

import mesa

from viableos.simulation.agents.base import VSMAgent
from viableos.simulation.channels import Message
from viableos.simulation.scheduler import DEFAULT_TICK_RATES


class S2Agent(VSMAgent):
    """Coordination agent — routes messages, detects conflicts.

    Rule-based (no LLM) to guarantee faster-than-S1 response.
    """

    def __init__(self, model: mesa.Model, *, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            model,
            config=config,
            system_level="s2",
            tick_rate=kwargs.get("tick_rate", DEFAULT_TICK_RATES["s2"]),
            llm_fn=None,  # Never uses LLM
        )
        self.coordination_rules: list[dict[str, str]] = config.get("coordination_rules", [])
        self.conflicts_detected: int = 0
        self.messages_routed: int = 0

    def deliberate(self) -> None:
        """Route S1 status updates, detect conflicts, escalate if needed."""
        s1_statuses: dict[str, str] = {}

        for msg in self.inbox:
            if msg.sender_level == "s1" and msg.performative == "inform":
                # Track S1 statuses
                s1_statuses[msg.sender] = msg.content
                self.messages_routed += 1

                # Forward S1 reports to S3 (the upward channel)
                s3_name = self._find_s3_name()
                self.send_message(
                    receiver=s3_name,
                    receiver_level="s3",
                    performative="inform",
                    content=f"[{msg.sender}] {msg.content}",
                    protocol="coordination",
                )

            elif msg.sender_level == "s3" and msg.performative == "request":
                # S3 directive → route to target S1
                target = msg.metadata.get("target_s1", "")
                if target:
                    self.send_message(
                        receiver=target,
                        receiver_level="s1",
                        performative="request",
                        content=msg.content,
                        protocol="coordination",
                    )
                    self.messages_routed += 1

        # Detect conflicts: multiple S1 units working on overlapping tasks
        if len(s1_statuses) > 1:
            contents = list(s1_statuses.values())
            for i, c1 in enumerate(contents):
                for c2 in contents[i + 1:]:
                    if self._detect_overlap(c1, c2):
                        self.conflicts_detected += 1
                        self._escalate_to_s3(
                            f"Potential conflict: {c1} vs {c2}"
                        )

    def _detect_overlap(self, status_a: str, status_b: str) -> bool:
        """Simple overlap detection: shared keywords between statuses."""
        words_a = set(status_a.lower().split())
        words_b = set(status_b.lower().split())
        overlap = words_a & words_b - {"status:", "working", "on", "the", "a", "an"}
        return len(overlap) >= 3

    def _find_s3_name(self) -> str:
        for agent in self.model.agents:
            if getattr(agent, "system_level", "") == "s3":
                return agent.name
        return "s3_optimizer"

    def _escalate_to_s3(self, reason: str) -> None:
        """Escalate a coordination issue to S3."""
        s3_name = self._find_s3_name()
        self.send_message(
            receiver=s3_name,
            receiver_level="s3",
            performative="inform",
            content=f"Escalation: {reason}",
            protocol="coordination",
        )
