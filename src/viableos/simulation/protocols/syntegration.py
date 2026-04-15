"""Syntegration protocol — Beer's non-hierarchical deliberation for agent consensus.

Implements the 5-phase Team Syntegrity protocol adapted for AI agents:
  1. OSI (Opening Statement of Importance) — each agent states what matters
  2. Jostle — S2 clusters statements into N topics
  3. Auction — agents bid for topics (Player or Critic roles)
  4. Reverberation ×3 — Players discuss, Critics challenge, info propagates
  5. Resolution — S3 collects outcomes, S5 validates, human approves

The protocol runs as an event-driven state machine inside the VSMScheduler.
Normal heartbeats are paused during reverberation cycles.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    PROPOSED = "proposed"
    OSI = "osi"
    JOSTLE = "jostle"
    AUCTION = "auction"
    REVERB_1 = "reverb_1"
    REVERB_2 = "reverb_2"
    REVERB_3 = "reverb_3"
    RESOLUTION = "resolution"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Phase transitions
_NEXT_PHASE: dict[Phase, Phase] = {
    Phase.PROPOSED: Phase.OSI,
    Phase.OSI: Phase.JOSTLE,
    Phase.JOSTLE: Phase.AUCTION,
    Phase.AUCTION: Phase.REVERB_1,
    Phase.REVERB_1: Phase.REVERB_2,
    Phase.REVERB_2: Phase.REVERB_3,
    Phase.REVERB_3: Phase.RESOLUTION,
    Phase.RESOLUTION: Phase.COMPLETED,
}


@dataclass
class TopicOutcome:
    """Result of deliberation on one topic."""

    topic: str
    statement: str = ""
    recommendations: list[str] = field(default_factory=list)
    players: list[str] = field(default_factory=list)
    critics: list[str] = field(default_factory=list)


@dataclass
class SyntegrationProtocol:
    """State machine for a single Syntegration event.

    Manages the 5 phases of Beer's Team Syntegrity protocol,
    adapted for AI agents operating at different VSM system levels.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trigger: str = ""
    proposed_by: str = ""
    started_at_tick: int = 0
    completed_at_tick: int | None = None
    phase: Phase = Phase.PROPOSED

    # Participants
    participants: list[str] = field(default_factory=list)
    participant_levels: dict[str, str] = field(default_factory=dict)

    # OSI results
    importance_statements: dict[str, str] = field(default_factory=dict)

    # Topics (after Jostle)
    topics: list[str] = field(default_factory=list)

    # Role assignments (after Auction)
    roles: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    # {agent_name: [{"topic": "X", "role": "player"}, {"topic": "Y", "role": "critic"}]}

    # Reverberation outputs (per cycle per topic)
    reverberation_log: list[dict[str, Any]] = field(default_factory=list)

    # Final outcomes
    outcomes: list[TopicOutcome] = field(default_factory=list)

    # Config
    max_topics: int = 4
    reverberation_cycles: int = 3

    @property
    def is_active(self) -> bool:
        return self.phase not in (Phase.COMPLETED, Phase.CANCELLED, Phase.PROPOSED)

    @property
    def is_complete(self) -> bool:
        return self.phase in (Phase.COMPLETED, Phase.CANCELLED)

    def advance(self, model: Any) -> Phase:
        """Advance to the next phase, executing the current phase logic.

        Returns the new phase after advancement.
        """
        if self.phase == Phase.COMPLETED or self.phase == Phase.CANCELLED:
            return self.phase

        handler = {
            Phase.PROPOSED: self._start,
            Phase.OSI: self._run_osi,
            Phase.JOSTLE: self._run_jostle,
            Phase.AUCTION: self._run_auction,
            Phase.REVERB_1: self._run_reverberation,
            Phase.REVERB_2: self._run_reverberation,
            Phase.REVERB_3: self._run_reverberation,
            Phase.RESOLUTION: self._run_resolution,
        }.get(self.phase)

        if handler:
            handler(model)

        next_phase = _NEXT_PHASE.get(self.phase)
        if next_phase:
            self.phase = next_phase
            logger.info("Syntegration %s → phase %s", self.id, self.phase.value)

        if self.phase == Phase.COMPLETED:
            self.completed_at_tick = model.tick

        return self.phase

    # ── Phase handlers ────────────────────────────────────────

    def _start(self, model: Any) -> None:
        """Initialize: gather all agent names as participants."""
        self.started_at_tick = model.tick
        self.participants = [a.name for a in model.scheduler.agents]
        self.participant_levels = {
            a.name: a.system_level for a in model.scheduler.agents
        }
        logger.info(
            "Syntegration %s started: %d participants, trigger=%s",
            self.id, len(self.participants), self.trigger,
        )

    def _run_osi(self, model: Any) -> None:
        """OSI: each agent produces a statement of importance.

        In production, this would be an LLM call per agent.
        For now, generates statements from agent beliefs + purpose.
        """
        for agent in model.scheduler.agents:
            # Build statement from agent's current knowledge
            beliefs_summary = ", ".join(
                f"{k}={v}" for k, v in list(agent.beliefs.items())[:3]
            )
            statement = (
                f"[{agent.system_level.upper()}] {agent.purpose}"
            )
            if beliefs_summary:
                statement += f" | Current state: {beliefs_summary}"

            self.importance_statements[agent.name] = statement

        logger.info(
            "OSI complete: %d statements collected", len(self.importance_statements),
        )

    def _run_jostle(self, model: Any) -> None:
        """Jostle: cluster statements into N topics.

        S2 (coordinator) facilitates. In production, an LLM would cluster.
        For now, uses keyword extraction heuristic.
        """
        # Extract keywords from all statements
        all_words: list[str] = []
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "and", "or", "but",
            "in", "on", "at", "to", "for", "of", "with", "by", "from",
            "current", "state:", "|",
        }

        for statement in self.importance_statements.values():
            words = [
                w.strip("[](),.:;'\"").lower()
                for w in statement.split()
                if len(w) > 3 and w.strip("[](),.:;'\"").lower() not in stop_words
            ]
            all_words.extend(words)

        # Top N keywords become topic seeds
        counter = Counter(all_words)
        top_keywords = [word for word, _ in counter.most_common(self.max_topics * 2)]

        # Deduplicate similar keywords and form topics
        topics: list[str] = []
        seen: set[str] = set()
        for kw in top_keywords:
            if kw not in seen and len(topics) < self.max_topics:
                topics.append(kw.title())
                seen.add(kw)

        # Ensure at least 2 topics
        if len(topics) < 2:
            topics = ["Operations", "Strategy"]

        self.topics = topics
        logger.info("Jostle complete: %d topics — %s", len(topics), topics)

    def _run_auction(self, model: Any) -> None:
        """Auction: assign agents to topics as Player or Critic.

        Each agent gets 1 topic as Player, 1 as Critic (if enough topics).
        Assignment is round-robin for fairness.
        """
        agents = list(model.scheduler.agents)
        n_topics = len(self.topics)

        for agent in agents:
            self.roles[agent.name] = []

        # Assign Players: distribute agents across topics
        for i, agent in enumerate(agents):
            topic_idx = i % n_topics
            self.roles[agent.name].append({
                "topic": self.topics[topic_idx],
                "role": "player",
            })

        # Assign Critics: offset by 1 topic
        for i, agent in enumerate(agents):
            critic_idx = (i + 1) % n_topics
            # Don't assign critic on same topic as player
            if self.topics[critic_idx] != self.roles[agent.name][0]["topic"]:
                self.roles[agent.name].append({
                    "topic": self.topics[critic_idx],
                    "role": "critic",
                })

        # Log assignments
        for agent_name, role_list in self.roles.items():
            role_str = ", ".join(f"{r['role']} on '{r['topic']}'" for r in role_list)
            logger.debug("  %s: %s", agent_name, role_str)

        logger.info(
            "Auction complete: %d agents assigned across %d topics",
            len(agents), n_topics,
        )

    def _run_reverberation(self, model: Any) -> None:
        """Reverberation: Players discuss, Critics challenge.

        Each reverberation cycle:
        1. Players on each topic produce a position
        2. Critics provide feedback
        3. Information propagates through shared agents

        In production, each step is an LLM call. For now, simulated.
        """
        cycle = {
            Phase.REVERB_1: 1,
            Phase.REVERB_2: 2,
            Phase.REVERB_3: 3,
        }.get(self.phase, 0)

        cycle_log: dict[str, Any] = {"cycle": cycle, "topics": {}}

        for topic in self.topics:
            # Find players and critics for this topic
            players = [
                name for name, roles in self.roles.items()
                if any(r["topic"] == topic and r["role"] == "player" for r in roles)
            ]
            critics = [
                name for name, roles in self.roles.items()
                if any(r["topic"] == topic and r["role"] == "critic" for r in roles)
            ]

            # Simulate discussion (in production: LLM group chat)
            position = f"Cycle {cycle} position on '{topic}' by {', '.join(players)}"
            critique = f"Critique from {', '.join(critics)}" if critics else "No critique"

            cycle_log["topics"][topic] = {
                "players": players,
                "critics": critics,
                "position": position,
                "critique": critique,
            }

        self.reverberation_log.append(cycle_log)
        logger.info("Reverberation cycle %d complete for %d topics", cycle, len(self.topics))

    def _run_resolution(self, model: Any) -> None:
        """Resolution: synthesize outcomes per topic.

        S3 collects, S5 validates against values.
        """
        for topic in self.topics:
            # Gather all positions from reverberation
            positions: list[str] = []
            for cycle_log in self.reverberation_log:
                topic_data = cycle_log.get("topics", {}).get(topic, {})
                if topic_data.get("position"):
                    positions.append(topic_data["position"])

            players = [
                name for name, roles in self.roles.items()
                if any(r["topic"] == topic and r["role"] == "player" for r in roles)
            ]
            critics = [
                name for name, roles in self.roles.items()
                if any(r["topic"] == topic and r["role"] == "critic" for r in roles)
            ]

            outcome = TopicOutcome(
                topic=topic,
                statement=f"Consensus on '{topic}' after {len(positions)} reverberation cycles",
                recommendations=[f"Action item for '{topic}'"],
                players=players,
                critics=critics,
            )
            self.outcomes.append(outcome)

        logger.info(
            "Resolution complete: %d topic outcomes produced", len(self.outcomes),
        )

    # ── Trigger evaluation ────────────────────────────────────

    @staticmethod
    def evaluate_triggers(model: Any, trigger_config: list[dict]) -> str | None:
        """Check if any syntegration trigger condition is met.

        Returns the trigger name if fired, None otherwise.
        """
        for trigger in trigger_config:
            condition = trigger.get("condition", "")
            threshold = trigger.get("threshold", 3)

            if condition == "s4_converging_signals":
                s4_agents = [
                    a for a in model.scheduler.agents
                    if getattr(a, "system_level", "") == "s4"
                ]
                for s4 in s4_agents:
                    signals = getattr(s4, "signals_detected", 0)
                    if signals >= threshold:
                        return condition

            elif condition == "s3_coordination_failures":
                s2_agents = [
                    a for a in model.scheduler.agents
                    if getattr(a, "system_level", "") == "s2"
                ]
                for s2 in s2_agents:
                    conflicts = getattr(s2, "conflicts_detected", 0)
                    if conflicts >= threshold:
                        return condition

            elif condition == "s3star_correlated_errors":
                s3star_agents = [
                    a for a in model.scheduler.agents
                    if getattr(a, "system_level", "") == "s3star"
                ]
                for s3star in s3star_agents:
                    findings = [
                        r for r in getattr(s3star, "audit_results", [])
                        if r.get("status") != "pass"
                    ]
                    if len(findings) >= threshold:
                        return condition

            elif condition == "s5_balance_alert":
                if model.message_bus.algedonic_count >= threshold:
                    return condition

        return None
