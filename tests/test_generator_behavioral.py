"""Tests for generator output with behavioral spec fields.

Verifies that SOUL.md, SKILL.md, and HEARTBEAT.md contain the new
behavioral spec sections when a config includes them.
"""

import tempfile
from pathlib import Path

from viableos.assessment_transformer import transform_assessment
from viableos.generator import generate_openclaw_package


def _make_assessment(team_size: int = 3) -> dict:
    """Build a realistic assessment for testing generator output."""
    return {
        "system_name": "Molaris Pflegedienst",
        "purpose": "Ambulante Pflege für ältere Menschen",
        "team": {"size": team_size, "roles": ["Geschäftsführer", "PDL"]},
        "recursion_levels": {
            "level_0": {
                "operational_units": [
                    {
                        "id": "planung",
                        "name": "Tourenplanung",
                        "description": "Einsatzplanung und Routenoptimierung",
                        "priority": 1,
                    },
                    {
                        "id": "abrechnung",
                        "name": "Abrechnung",
                        "description": "Leistungsabrechnung mit Kassen",
                        "priority": 2,
                    },
                ],
            },
        },
        "dependencies": {
            "business_level": [
                {"from": "Tourenplanung", "to": "Abrechnung", "what": "Leistungsnachweise"},
            ],
        },
        "external_forces": [
            {"name": "SGB XI Änderungen", "type": "regulation", "frequency": "quarterly"},
            {"name": "KI-gestützte Tourenplanung", "type": "technology", "frequency": "monthly"},
        ],
        "success_criteria": [
            {"criterion": "Versorgungsqualität > 95%", "priority": "1"},
            {"criterion": "Abrechnungsquote > 98%", "priority": "2"},
        ],
        "shared_resources": ["Pflegesoftware"],
        "metasystem": {
            "s2_coordination": {
                "tasks": ["Dienstplanabstimmung"],
                "label": "Koordinator",
            },
            "s3_optimization": {
                "tasks": ["KPI-Tracking Pflegequalität", "Ressourcenplanung"],
                "label": "Optimierer",
            },
            "s3_star_audit": {
                "tasks": ["Dokumentationsprüfung", "Qualitätsstichproben"],
                "design_principle": "Eskalation an Geschäftsführer",
                "label": "Prüfer",
            },
            "s4_intelligence": {
                "tasks": ["Regulatorische Veränderungen beobachten"],
                "label": "Aufklärer",
            },
            "s5_policy": {
                "policies": [
                    "Patientenwohl vor Effizienz",
                    "Ethik: Keine Patientendaten verkaufen",
                ],
            },
        },
    }


def _generate_with_behavioral_specs(team_size: int = 3) -> Path:
    """Transform assessment → generate package → return output path."""
    assessment = _make_assessment(team_size)
    config = transform_assessment(assessment)
    with tempfile.TemporaryDirectory() as tmpdir:
        output = generate_openclaw_package(config, tmpdir)
        # Read all files into a dict before tmpdir is cleaned up
        return output


class TestSoulBehavioralSections:
    """SOUL.md files should contain behavioral spec sections."""

    def _read_soul(self, output: Path, agent_slug: str) -> str:
        return (output / "workspaces" / agent_slug / "SOUL.md").read_text()

    def test_s1_soul_has_operational_modes(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s1-tourenplanung")
        assert "Operational Modes" in soul
        assert "Normal" in soul
        assert "Crisis" in soul

    def test_s1_soul_has_escalation_protocol(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s1-tourenplanung")
        assert "Escalation Protocol" in soul
        assert "s2-coordination" in soul

    def test_s1_soul_has_vollzug_protocol(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s1-tourenplanung")
        assert "Execution Obligation" in soul
        assert "acknowledgment" in soul

    def test_s1_soul_has_autonomy_matrix(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s1-tourenplanung")
        assert "Autonomy Matrix" in soul
        assert "Decide alone" in soul
        assert "Coordination needed" in soul
        assert "Approval needed" in soul

    def test_s2_soul_has_conflict_detection(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s2-coordination")
        assert "Conflict Detection" in soul

    def test_s2_soul_has_transduction(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s2-coordination")
        assert "Transduction" in soul
        assert "Tourenplanung" in soul

    def test_s3_soul_has_triple_index(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s3-optimization")
        assert "Triple Index" in soul
        assert "Actuality" in soul
        assert "Capability" in soul
        assert "Potentiality" in soul

    def test_s3_soul_has_deviation_logic(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s3-optimization")
        assert "Deviation Logic" in soul

    def test_s3_soul_has_intervention_authority(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s3-optimization")
        assert "Intervention Authority" in soul
        assert "Freeze budget" in soul

    def test_s3star_soul_has_provider_constraint(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s3star-audit")
        assert "Provider" in soul
        assert "s1" in soul
        assert "correlated" in soul

    def test_s3star_soul_has_independence_rules(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s3star-audit")
        assert "Independence Rules" in soul
        assert "No write access" in soul

    def test_s4_soul_has_premises_register(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s4-intelligence")
        assert "Premises Register" in soul
        assert "SGB XI" in soul

    def test_s4_soul_has_strategy_bridge(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s4-intelligence")
        assert "Strategy Bridge" in soul
        assert "s3-optimization" in soul

    def test_s5_soul_has_balance_monitoring(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s5-policy")
        assert "S3/S4 Balance" in soul
        assert "60/40" in soul

    def test_s5_soul_has_algedonic_channel(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s5-policy")
        assert "Algedonic Channel" in soul

    def test_s5_soul_has_basta_constraint(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        soul = self._read_soul(output, "s5-policy")
        assert "Normative Reserve" in soul
        assert "Strategy change" in soul


class TestSkillBehavioralSections:
    """SKILL.md files should contain behavioral spec sections."""

    def _read_skill(self, output: Path, agent_slug: str) -> str:
        return (output / "workspaces" / agent_slug / "SKILL.md").read_text()

    def test_s2_skill_has_conflict_detection(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        skill = self._read_skill(output, "s2-coordination")
        assert "Conflict Detection" in skill

    def test_s2_skill_has_transduction(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        skill = self._read_skill(output, "s2-coordination")
        assert "Transduction" in skill

    def test_s3_skill_has_intervention(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        skill = self._read_skill(output, "s3-optimization")
        assert "Intervention Authority" in skill

    def test_s4_skill_has_premises(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        skill = self._read_skill(output, "s4-intelligence")
        assert "Premises Register" in skill

    def test_s4_skill_has_strategy_bridge(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        skill = self._read_skill(output, "s4-intelligence")
        assert "Strategy Bridge" in skill


class TestHeartbeatModeTable:
    """HEARTBEAT.md files should contain mode-dependent frequency tables."""

    def _read_heartbeat(self, output: Path, agent_slug: str) -> str:
        return (output / "workspaces" / agent_slug / "HEARTBEAT.md").read_text()

    def test_all_heartbeats_have_mode_table(self, tmp_path):
        config = transform_assessment(_make_assessment())
        output = generate_openclaw_package(config, tmp_path / "pkg")
        for slug in [
            "s1-tourenplanung",
            "s1-abrechnung",
            "s2-coordination",
            "s3-optimization",
            "s3star-audit",
            "s4-intelligence",
            "s5-policy",
        ]:
            hb = self._read_heartbeat(output, slug)
            assert "Frequencies by Operating Mode" in hb, f"Missing mode table in {slug}"
            assert "Normal" in hb
            assert "Crisis" in hb


class TestBackwardCompatibility:
    """Generator still works with configs that have NO behavioral specs."""

    def test_minimal_config_generates(self, tmp_path):
        config = {
            "viable_system": {
                "name": "Minimal",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "Worker", "purpose": "Do stuff"}],
                "budget": {"monthly_usd": 50, "strategy": "frugal"},
            }
        }
        output = generate_openclaw_package(config, tmp_path / "pkg")
        # Should not crash and should produce output
        assert (output / "workspaces" / "s1-worker" / "SOUL.md").exists()
        assert (output / "openclaw.json").exists()

        # SOUL should NOT have behavioral sections (no modes configured)
        soul = (output / "workspaces" / "s1-worker" / "SOUL.md").read_text()
        assert "Operational Modes" not in soul
        assert "Execution Obligation" not in soul
