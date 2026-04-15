"""VSM communication channels — typed message bus with channel constraints."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single message between VSM agents."""

    sender: str
    sender_level: str  # "s1", "s2", "s3", "s3star", "s4", "s5"
    receiver: str  # agent name or "broadcast"
    receiver_level: str
    performative: str  # "inform", "request", "alert", "ack", "cfp", "propose"
    content: str
    protocol: str = ""  # "execution", "algedonic", "coordination"
    tick: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# VSM channel rules: (sender_level, receiver_level) → allowed?
# Beer's model: S1 units never talk to each other directly.
# Algedonic channel: any agent can alert S5.
_CHANNEL_RULES: dict[tuple[str, str], bool] = {
    ("s1", "s2"): True,  # S1 reports to S2 (coordination)
    ("s2", "s1"): True,  # S2 routes to S1
    ("s2", "s3"): True,  # S2 escalates to S3
    ("s3", "s1"): True,  # S3 directs S1 (resource bargain)
    ("s3", "s2"): True,  # S3 instructs S2
    ("s3star", "s3"): True,  # S3* reports audit findings to S3
    ("s3star", "s5"): True,  # S3* can report directly to S5
    ("s4", "s5"): True,  # S4 briefs S5 (outside-in intelligence)
    ("s5", "s3"): True,  # S5 sends policy to S3
    ("s5", "s4"): True,  # S5 can direct S4 (inside-out)
    ("s1", "s1"): False,  # S1 units NEVER talk directly (must go via S2)
}


def is_channel_allowed(sender_level: str, receiver_level: str) -> bool:
    """Check if a VSM communication channel is allowed."""
    # Algedonic: any agent can send alerts to S5
    if receiver_level == "s5":
        return True
    return _CHANNEL_RULES.get((sender_level, receiver_level), False)


class MessageBus:
    """Routes messages between agents, enforcing VSM channel constraints."""

    def __init__(self) -> None:
        self._pending: list[Message] = []
        self._mailboxes: dict[str, list[Message]] = defaultdict(list)

        # Metrics
        self.total_sent = 0
        self.total_delivered = 0
        self.total_blocked = 0
        self.escalation_count = 0
        self.algedonic_count = 0

    def send(self, msg: Message) -> bool:
        """Queue a message for delivery. Returns False if channel not allowed."""
        if not is_channel_allowed(msg.sender_level, msg.receiver_level):
            logger.warning(
                "Blocked message %s(%s) → %s(%s): channel not allowed",
                msg.sender, msg.sender_level, msg.receiver, msg.receiver_level,
            )
            self.total_blocked += 1
            return False

        self._pending.append(msg)
        self.total_sent += 1

        if msg.performative == "alert":
            self.algedonic_count += 1

        return True

    def deliver(self) -> int:
        """Deliver all pending messages to recipient mailboxes. Returns count."""
        delivered = 0
        for msg in self._pending:
            self._mailboxes[msg.receiver].append(msg)
            delivered += 1

        self._pending.clear()
        self.total_delivered += delivered
        return delivered

    def collect(self, agent_name: str) -> list[Message]:
        """Collect all messages for an agent (empties mailbox)."""
        messages = self._mailboxes.pop(agent_name, [])
        return messages

    def peek(self, agent_name: str) -> list[Message]:
        """Peek at messages without removing them."""
        return list(self._mailboxes.get(agent_name, []))

    def reset_metrics(self) -> None:
        self.total_sent = 0
        self.total_delivered = 0
        self.total_blocked = 0
        self.escalation_count = 0
        self.algedonic_count = 0
