"""Base VSM agent with BDI structure."""

from __future__ import annotations

import logging
from typing import Any, Callable

import mesa

from viableos.simulation.channels import Message

logger = logging.getLogger(__name__)

# Priority order: S5 decides policy first, then S4, S3, S3*, S2, S1.
PRIORITY = {"s5": 0, "s4": 1, "s3": 2, "s3star": 3, "s2": 4, "s1": 5}


class VSMAgent(mesa.Agent):
    """Base VSM agent with Beliefs-Desires-Intentions structure.

    Subclasses override ``deliberate()`` to implement system-specific logic.
    When ``llm_fn`` is None the agent uses a no-op deliberation (useful for tests).
    """

    def __init__(
        self,
        model: mesa.Model,
        *,
        config: dict[str, Any],
        system_level: str,
        tick_rate: int,
        llm_fn: Callable[..., str] | None = None,
    ) -> None:
        super().__init__(model)
        self.system_level = system_level
        self.tick_rate = tick_rate
        self.priority = PRIORITY[system_level]
        self.llm_fn = llm_fn

        # BDI
        self.beliefs: dict[str, Any] = {}
        self.goals: list[str] = []
        self.current_plan: str | None = None

        # Communication
        self.inbox: list[Message] = []
        self.outbox: list[Message] = []

        # Identity (from config)
        self.name: str = config.get("name", f"{system_level}_agent")
        self.purpose: str = config.get("purpose", "")
        self.tools: list[str] = config.get("tools", [])

        # Counters
        self.step_count: int = 0
        self.tasks_completed: int = 0

    # ── BDI cycle ─────────────────────────────────────────────

    def step(self) -> None:
        """Execute one BDI cycle: perceive → deliberate → act."""
        self.step_count += 1
        self.perceive()
        self.deliberate()
        self.act()

    def perceive(self) -> None:
        """Read inbox and update beliefs."""
        messages = self.model.message_bus.collect(self.name)
        self.inbox = messages
        if messages:
            self.beliefs["last_messages"] = [
                {"from": m.sender, "performative": m.performative, "content": m.content}
                for m in messages
            ]

    def deliberate(self) -> None:
        """Decide what to do next. Override in subclasses."""
        # Default: no-op. Subclasses implement LLM-based or rule-based logic.
        pass

    def _llm_deliberate(self, task_prompt: str) -> str | None:
        """Call the LLM for deliberation. Returns response or None if no LLM."""
        if not self.llm_fn:
            return None

        context = (
            f"You are {self.name} ({self.system_level.upper()}).\n"
            f"Purpose: {self.purpose}\n"
            f"Current tick: {self.model.tick}\n"
            f"Mode: {self.model.mode}\n"
        )
        if self.beliefs:
            beliefs_str = "\n".join(f"- {k}: {v}" for k, v in list(self.beliefs.items())[:5])
            context += f"\nCurrent beliefs:\n{beliefs_str}\n"
        if self.inbox:
            msgs_str = "\n".join(
                f"- [{m.performative}] from {m.sender}: {m.content[:100]}"
                for m in self.inbox[:5]
            )
            context += f"\nInbox:\n{msgs_str}\n"

        full_prompt = f"{context}\nTask: {task_prompt}"

        try:
            return self.llm_fn(full_prompt)
        except Exception as exc:
            logger.warning("LLM call failed for %s: %s", self.name, exc)
            return None

    def act(self) -> None:
        """Execute plan and send outbox messages."""
        for msg in self.outbox:
            msg.tick = self.model.tick
            self.model.message_bus.send(msg)
        self.outbox.clear()

    # ── Helpers ────────────────────────────────────────────────

    def send_message(
        self,
        receiver: str,
        receiver_level: str,
        performative: str,
        content: str,
        protocol: str = "",
    ) -> None:
        """Queue a message for the next act() phase."""
        self.outbox.append(Message(
            sender=self.name,
            sender_level=self.system_level,
            receiver=receiver,
            receiver_level=receiver_level,
            performative=performative,
            content=content,
            protocol=protocol,
        ))

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name} ({self.system_level})>"
