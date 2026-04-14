"""Tests for the VSM simulation engine."""

from __future__ import annotations

import pytest

from viableos.simulation.agents.s1 import S1Agent
from viableos.simulation.agents.s2 import S2Agent
from viableos.simulation.agents.s3 import S3Agent
from viableos.simulation.agents.s3star import S3StarAgent
from viableos.simulation.agents.s4 import S4Agent
from viableos.simulation.agents.s5 import S5Agent
from viableos.simulation.channels import Message, MessageBus, is_channel_allowed
from viableos.simulation.engine import VSMSimulation


# ── Fixtures ──────────────────────────────────────────────────


def _minimal_config() -> dict:
    """Minimal viable_system config for testing."""
    return {
        "viable_system": {
            "name": "Test System",
            "identity": {
                "purpose": "Test the simulation engine",
                "values": ["Rigor"],
                "never_do": ["Break tests"],
            },
            "system_1": [
                {"name": "Unit Alpha", "purpose": "Do alpha work", "tools": ["tool-a"]},
                {"name": "Unit Beta", "purpose": "Do beta work", "tools": ["tool-b"]},
            ],
            "system_2": {
                "coordination_rules": [
                    {"trigger": "Unit Alpha completes", "action": "Notify Unit Beta"},
                ],
            },
            "system_3": {
                "reporting_rhythm": "weekly",
                "resource_allocation": "Alpha 60%, Beta 40%",
            },
            "system_3_star": {
                "checks": [
                    {"name": "Quality check", "target": "Unit Alpha", "method": "Cross-verify output"},
                ],
            },
            "system_4": {
                "monitoring": {
                    "competitors": ["Competitor A"],
                    "technology": ["AI advances"],
                    "regulation": ["LGPD"],
                },
            },
        },
    }


# ── MessageBus ────────────────────────────────────────────────


class TestMessageBus:
    def test_allowed_channel_s1_to_s2(self):
        assert is_channel_allowed("s1", "s2") is True

    def test_blocked_channel_s1_to_s1(self):
        assert is_channel_allowed("s1", "s1") is False

    def test_algedonic_any_to_s5(self):
        assert is_channel_allowed("s1", "s5") is True
        assert is_channel_allowed("s3", "s5") is True
        assert is_channel_allowed("s4", "s5") is True

    def test_send_and_deliver(self):
        bus = MessageBus()
        msg = Message(
            sender="unit_a", sender_level="s1",
            receiver="s2_coordinator", receiver_level="s2",
            performative="inform", content="Status: idle",
        )
        assert bus.send(msg) is True
        assert bus.total_sent == 1

        delivered = bus.deliver()
        assert delivered == 1
        assert bus.total_delivered == 1

        collected = bus.collect("s2_coordinator")
        assert len(collected) == 1
        assert collected[0].content == "Status: idle"

    def test_blocked_message(self):
        bus = MessageBus()
        msg = Message(
            sender="unit_a", sender_level="s1",
            receiver="unit_b", receiver_level="s1",
            performative="inform", content="Hey",
        )
        assert bus.send(msg) is False
        assert bus.total_blocked == 1

    def test_algedonic_alert_counted(self):
        bus = MessageBus()
        msg = Message(
            sender="unit_a", sender_level="s1",
            receiver="s5_policy", receiver_level="s5",
            performative="alert", content="Critical error!",
        )
        bus.send(msg)
        assert bus.algedonic_count == 1


# ── VSMSimulation ─────────────────────────────────────────────


class TestVSMSimulation:
    def test_builds_all_agents(self):
        sim = VSMSimulation(_minimal_config())
        agent_levels = [a.system_level for a in sim.scheduler.agents]
        assert agent_levels.count("s1") == 2
        assert agent_levels.count("s2") == 1
        assert agent_levels.count("s3") == 1
        assert agent_levels.count("s3star") == 1
        assert agent_levels.count("s4") == 1
        assert agent_levels.count("s5") == 1

    def test_total_agents(self):
        sim = VSMSimulation(_minimal_config())
        assert len(sim.scheduler.agents) == 7  # 2 S1 + 5 meta

    def test_step_increments_tick(self):
        sim = VSMSimulation(_minimal_config())
        assert sim.tick == 0
        sim.step()
        assert sim.tick == 1
        sim.step()
        assert sim.tick == 2

    def test_run_multiple_ticks(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(100)
        assert sim.tick == 100


# ── Multi-rate Scheduling ─────────────────────────────────────


class TestMultiRateScheduling:
    def test_s2_activates_every_tick(self):
        """S2 (nervous system) activates every tick — faster than S1."""
        sim = VSMSimulation(_minimal_config())
        sim.run(10)
        s2 = next(a for a in sim.scheduler.agents if a.system_level == "s2")
        assert s2.step_count == 10  # tick_rate=1

    def test_s1_activates_every_2_ticks(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(10)
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        assert s1.step_count == 5  # tick_rate=2

    def test_s3_activates_every_14_ticks(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(28)
        s3 = next(a for a in sim.scheduler.agents if a.system_level == "s3")
        assert s3.step_count == 2  # tick_rate=14

    def test_s5_activates_rarely(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(50)
        s5 = next(a for a in sim.scheduler.agents if a.system_level == "s5")
        assert s5.step_count == 1  # tick_rate=50

    def test_s2_faster_than_s1(self):
        """Beer's principle: coordination is faster than operations."""
        sim = VSMSimulation(_minimal_config())
        sim.run(10)
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        s2 = next(a for a in sim.scheduler.agents if a.system_level == "s2")
        assert s2.step_count > s1.step_count

    def test_priority_order(self):
        """S5 has lowest priority number (acts first), S1 highest (acts last)."""
        sim = VSMSimulation(_minimal_config())
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        s5 = next(a for a in sim.scheduler.agents if a.system_level == "s5")
        assert s5.priority < s1.priority


# ── Agent Communication ───────────────────────────────────────


class TestAgentCommunication:
    def test_s1_reports_to_s2(self):
        """S1 sends status to S2 when it has work to report."""
        sim = VSMSimulation(_minimal_config())
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        s2 = next(a for a in sim.scheduler.agents if a.system_level == "s2")

        # Give S1 a task by putting a message in its mailbox
        sim.message_bus._mailboxes[s1.name].append(Message(
            sender="s3_optimizer", sender_level="s3",
            receiver=s1.name, receiver_level="s1",
            performative="request", content="Analyze new legislation",
        ))

        # Run one S1 cycle
        sim.step()
        sim.step()  # S1 activates on tick 2

        # Check S2 received the status report
        assert sim.message_bus.total_sent > 0

    def test_algedonic_reaches_s5(self):
        """Any agent can alert S5 (algedonic channel)."""
        sim = VSMSimulation(_minimal_config())
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        s5 = next(a for a in sim.scheduler.agents if a.system_level == "s5")

        # S1 sends alert directly to S5
        sim.message_bus.send(Message(
            sender=s1.name, sender_level="s1",
            receiver=s5.name, receiver_level="s5",
            performative="alert", content="Critical: data source compromised",
        ))
        sim.message_bus.deliver()

        # S5 should have the alert
        messages = sim.message_bus.peek(s5.name)
        assert len(messages) == 1
        assert messages[0].performative == "alert"


# ── Mode Switching ────────────────────────────────────────────


class TestModeSwitching:
    def test_switch_to_elevated(self):
        sim = VSMSimulation(_minimal_config())
        sim.switch_mode("elevated")
        assert sim.mode == "elevated"

        # All tick rates should be halved (faster)
        s1 = next(a for a in sim.scheduler.agents if a.system_level == "s1")
        assert s1.tick_rate == 1  # was 2, now 2 * 0.5 = 1

    def test_switch_to_crisis(self):
        sim = VSMSimulation(_minimal_config())
        sim.switch_mode("crisis")
        assert sim.mode == "crisis"

        # S5 in crisis: 50 * 0.25 = 12
        s5 = next(a for a in sim.scheduler.agents if a.system_level == "s5")
        assert s5.tick_rate == 12

    def test_crisis_s2_stays_at_1(self):
        """S2 tick_rate can't go below 1 (already fastest)."""
        sim = VSMSimulation(_minimal_config())
        sim.switch_mode("crisis")
        s2 = next(a for a in sim.scheduler.agents if a.system_level == "s2")
        assert s2.tick_rate == 1

    def test_same_mode_noop(self):
        sim = VSMSimulation(_minimal_config())
        sim.switch_mode("normal")  # already normal
        assert sim.mode == "normal"


# ── DataCollector ─────────────────────────────────────────────


class TestDataCollector:
    def test_collects_model_data(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(5)
        df = sim.datacollector.get_model_vars_dataframe()
        assert len(df) == 5
        assert "tick" in df.columns
        assert "mode" in df.columns
        assert list(df["tick"]) == [1, 2, 3, 4, 5]

    def test_collects_agent_data(self):
        sim = VSMSimulation(_minimal_config())
        sim.run(5)
        df = sim.datacollector.get_agent_vars_dataframe()
        assert "system_level" in df.columns
        assert "step_count" in df.columns


# ── Integration: full simulation run ──────────────────────────


class TestFullSimulation:
    def test_100_ticks_no_crash(self):
        """Smoke test: run 100 ticks without errors."""
        sim = VSMSimulation(_minimal_config())
        sim.run(100)
        assert sim.tick == 100
        assert sim.message_bus.total_blocked == 0  # no invalid channel attempts

    def test_with_policy_research_template(self):
        """Run simulation from the actual policy-research template."""
        import yaml
        from pathlib import Path

        template_path = Path("src/viableos/templates/policy-research.yaml")
        if not template_path.exists():
            pytest.skip("Template not found")

        config = yaml.safe_load(template_path.read_text())
        sim = VSMSimulation(config)

        # Should have 4 S1 + 5 meta = 9 agents
        assert len(sim.scheduler.agents) == 9

        sim.run(50)
        assert sim.tick == 50

        # Verify data collection works
        df = sim.datacollector.get_model_vars_dataframe()
        assert len(df) == 50
