"""VSM Simulation Engine — runs a viable system organization as a multi-agent simulation."""

from __future__ import annotations

import logging
from typing import Any, Callable

import mesa

from viableos.simulation.agents.s1 import S1Agent
from viableos.simulation.agents.s2 import S2Agent
from viableos.simulation.agents.s3 import S3Agent
from viableos.simulation.agents.s3star import S3StarAgent
from viableos.simulation.agents.s4 import S4Agent
from viableos.simulation.agents.s5 import S5Agent
from viableos.simulation.channels import MessageBus
from viableos.simulation.environment import Environment, policy_research_scenario
from viableos.simulation.metrics import VSMDataCollector
from viableos.simulation.protocols.syntegration import Phase, SyntegrationProtocol
from viableos.simulation.scheduler import VSMScheduler

logger = logging.getLogger(__name__)


class VSMSimulation(mesa.Model):
    """Runs a VSM organization simulation from a ViableOS config.

    Takes the same ``viable_system`` config dict that the wizard produces.
    Creates agents from system_1 units + metasystem config.  Uses a
    multi-rate scheduler (Beer's tempo hierarchy) and typed message bus.
    """

    def __init__(
        self,
        config: dict[str, Any],
        *,
        llm_fn: Callable[..., str] | None = None,
        scenario: list[dict[str, Any]] | None = None,
        ticks: int = 100,
    ) -> None:
        super().__init__()
        self.tick: int = 0
        self.mode: str = "normal"
        self.message_bus = MessageBus()
        self.scheduler = VSMScheduler()
        self._llm_fn = llm_fn

        # Syntegration
        self.active_syntegration: SyntegrationProtocol | None = None
        self.syntegration_history: list[SyntegrationProtocol] = []
        self._syntegration_cooldown: int = 0

        vs = config.get("viable_system", config)
        self._syntegration_config = vs.get("syntegration", {})

        # Environment (scenario-driven or empty)
        scenario_events = scenario or policy_research_scenario(ticks)
        self.environment = Environment(scenario_events)

        self._build_from_config(vs)

        self.datacollector = VSMDataCollector(self)

    # ── Config → Agents ───────────────────────────────────────

    def _build_from_config(self, vs: dict[str, Any]) -> None:
        """Create all VSM agents from a viable_system config."""
        identity = vs.get("identity", {})
        s1_units = vs.get("system_1", [])
        s2_cfg = vs.get("system_2", {})
        s3_cfg = vs.get("system_3", {})
        s3star_cfg = vs.get("system_3_star", {})
        s4_cfg = vs.get("system_4", {})
        hitl = vs.get("human_in_the_loop", {})

        # S1 operational units
        for unit in s1_units:
            agent = S1Agent(self, config=unit, llm_fn=self._llm_fn)
            self.scheduler.add(agent)

        # S2 coordinator (rule-based, no LLM)
        s2_config = {
            "name": "s2_coordinator",
            "purpose": "Route information between S1 units, prevent conflicts",
            "coordination_rules": s2_cfg.get("coordination_rules", []),
        }
        s2 = S2Agent(self, config=s2_config)
        self.scheduler.add(s2)

        # S3 optimizer
        s3_config = {
            "name": "s3_optimizer",
            "purpose": "Monitor performance, allocate resources",
            "resource_allocation": s3_cfg.get("resource_allocation", ""),
            "reporting_rhythm": s3_cfg.get("reporting_rhythm", "weekly"),
            "kpi_list": s3_cfg.get("kpi_list", []),
        }
        s3 = S3Agent(self, config=s3_config, llm_fn=self._llm_fn)
        self.scheduler.add(s3)

        # S3* auditor
        s3star_config = {
            "name": "s3star_auditor",
            "purpose": "Independent verification of agent outputs",
            "checks": s3star_cfg.get("checks", []),
        }
        s3star = S3StarAgent(self, config=s3star_config, llm_fn=self._llm_fn)
        self.scheduler.add(s3star)

        # S4 scout
        s4_config = {
            "name": "s4_scout",
            "purpose": "Monitor external environment",
            "monitoring": s4_cfg.get("monitoring", {}),
        }
        s4 = S4Agent(self, config=s4_config, llm_fn=self._llm_fn)
        self.scheduler.add(s4)

        # S5 policy guardian
        s5_config = {
            "name": "s5_policy",
            "purpose": "Enforce values and policies",
            "identity": identity,
        }
        s5 = S5Agent(self, config=s5_config, llm_fn=self._llm_fn)
        self.scheduler.add(s5)

        logger.info(
            "Built VSM simulation: %d S1 units + 5 metasystem agents = %d total",
            len(s1_units), len(s1_units) + 5,
        )

    # ── Simulation Loop ───────────────────────────────────────

    def step(self) -> None:
        """Advance the simulation by one tick."""
        self.tick += 1

        # Advance environment (produces new signals for S4 to observe)
        self.environment.step(self.tick)

        # Check syntegration triggers (if not already in one, and cooldown expired)
        if not self.active_syntegration and self._syntegration_cooldown <= 0:
            self._check_syntegration_triggers()

        # Advance active syntegration (one phase per tick)
        if self.active_syntegration and self.active_syntegration.is_active:
            self.active_syntegration.advance(self)
            if self.active_syntegration.is_complete:
                self.syntegration_history.append(self.active_syntegration)
                cooldown = self._parse_duration(
                    self._syntegration_config.get("cooldown", "50")
                )
                self._syntegration_cooldown = cooldown
                self.active_syntegration = None

        if self._syntegration_cooldown > 0:
            self._syntegration_cooldown -= 1

        # Normal VSM cycle
        self.scheduler.step(self.tick)
        self.message_bus.deliver()
        self.datacollector.collect(self)

    def run(self, ticks: int) -> None:
        """Run the simulation for N ticks."""
        for _ in range(ticks):
            self.step()

    # ── Syntegration ──────────────────────────────────────────

    def trigger_syntegration(self, trigger: str, proposed_by: str = "human") -> SyntegrationProtocol:
        """Manually trigger a Syntegration event."""
        protocol = SyntegrationProtocol(
            trigger=trigger,
            proposed_by=proposed_by,
            max_topics=self._syntegration_config.get("max_topics", 4),
            reverberation_cycles=self._syntegration_config.get("reverberation_cycles", 3),
        )
        protocol.advance(self)  # PROPOSED → OSI
        self.active_syntegration = protocol
        logger.info("Syntegration triggered: %s (by %s)", trigger, proposed_by)
        return protocol

    def _check_syntegration_triggers(self) -> None:
        """Evaluate automatic syntegration trigger conditions."""
        triggers = self._syntegration_config.get("system_triggers", [])
        if not triggers:
            return

        fired = SyntegrationProtocol.evaluate_triggers(self, triggers)
        if fired:
            self.trigger_syntegration(fired, proposed_by="system")

    @staticmethod
    def _parse_duration(d: str) -> int:
        """Parse a duration string to tick count. Simple: just return int or default."""
        try:
            return int(d)
        except (ValueError, TypeError):
            return 50  # default cooldown

    # ── Mode Management ───────────────────────────────────────

    def switch_mode(self, new_mode: str) -> None:
        """Switch operational mode (normal / elevated / crisis).

        Adjusts tick_rates for all agents according to Beer's mode-dependent
        tempo hierarchy.
        """
        if new_mode == self.mode:
            return

        logger.info("Mode switch: %s → %s (tick %d)", self.mode, new_mode, self.tick)
        self.mode = new_mode

        multipliers = {
            "normal": 1.0,
            "elevated": 0.5,  # everything runs 2× faster
            "crisis": 0.25,  # everything runs 4× faster
        }
        m = multipliers.get(new_mode, 1.0)

        for agent in self.scheduler.agents:
            from viableos.simulation.scheduler import DEFAULT_TICK_RATES
            base = DEFAULT_TICK_RATES.get(agent.system_level, 2)
            agent.tick_rate = max(1, int(base * m))
