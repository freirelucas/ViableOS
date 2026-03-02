"""Tests for the assessment transformer — behavioral spec builders."""

from viableos.assessment_transformer import transform_assessment
from viableos.schema import validate


def _make_assessment(
    *,
    team_size: int = 3,
    external_forces: list | None = None,
    success_criteria: list | None = None,
    shared_resources: list | None = None,
    never_do: list | None = None,
) -> dict:
    """Build a realistic assessment dict for testing."""
    if external_forces is None:
        external_forces = [
            {"name": "DSGVO-Anforderungen", "type": "regulation", "frequency": "quarterly"},
            {"name": "KI-Entwicklung (LLMs)", "type": "technology", "frequency": "monthly"},
            {"name": "Wettbewerber X", "type": "competitors", "frequency": "monthly"},
        ]
    if success_criteria is None:
        success_criteria = [
            {"criterion": "Kundenzufriedenheit > 90%", "priority": "1"},
            {"criterion": "Umsatzwachstum 15%", "priority": "2"},
            {"criterion": "Mitarbeiterzufriedenheit hoch", "priority": "3"},
        ]
    if shared_resources is None:
        shared_resources = ["CRM-System", "Wissensdatenbank"]

    policies = ["Qualität vor Geschwindigkeit", "Transparenz"]
    if never_do:
        policies.extend([f"Ethik: {n}" for n in never_do])
    else:
        policies.append("Ethik: Keine Kundendaten verkaufen")

    return {
        "system_name": "Test-Organisation",
        "purpose": "Ganzheitliche Betreuung von Kunden",
        "team": {"size": team_size, "roles": ["Manager", "Spezialist"]},
        "recursion_levels": {
            "level_0": {
                "operational_units": [
                    {
                        "id": "vertrieb",
                        "name": "Vertrieb",
                        "description": "Kundenakquise und -betreuung",
                        "priority": 1,
                    },
                    {
                        "id": "produktion",
                        "name": "Produktion",
                        "description": "Leistungserstellung",
                        "priority": 2,
                    },
                ],
            },
        },
        "dependencies": {
            "business_level": [
                {"from": "Vertrieb", "to": "Produktion", "what": "Aufträge"},
                {"from": "Produktion", "to": "Vertrieb", "what": "Lieferstatus"},
            ],
        },
        "external_forces": external_forces,
        "success_criteria": success_criteria,
        "shared_resources": shared_resources,
        "metasystem": {
            "s2_coordination": {
                "tasks": ["Auftragskoordination"],
                "label": "Koordinator",
            },
            "s3_optimization": {
                "tasks": ["KPI-Tracking", "Ressourcenoptimierung"],
                "label": "Optimizer",
            },
            "s3_star_audit": {
                "tasks": ["Qualitätsprüfung", "Compliance-Check"],
                "design_principle": "Eskalation an S3",
                "label": "Auditor",
            },
            "s4_intelligence": {
                "tasks": ["Marktbeobachtung"],
                "label": "Scout",
            },
            "s5_policy": {
                "policies": policies,
            },
        },
    }


class TestTransformAssessment:
    def test_basic_transform_still_works(self):
        """Bestehende Felder bleiben korrekt."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        vs = config["viable_system"]

        assert vs["name"] == "Test-Organisation"
        assert vs["identity"]["purpose"] == "Ganzheitliche Betreuung von Kunden"
        assert len(vs["system_1"]) == 2
        assert vs["system_1"][0]["name"] == "Vertrieb"
        assert vs["system_1"][1]["name"] == "Produktion"
        assert vs["budget"]["strategy"] == "balanced"

    def test_operational_modes_generated(self):
        """Operational modes werden aus external_forces + success_criteria abgeleitet."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        modes = config["viable_system"]["operational_modes"]

        assert "normal" in modes
        assert "elevated" in modes
        assert "crisis" in modes

        assert modes["normal"]["s1_autonomy"] == "full"
        assert modes["elevated"]["s1_autonomy"] == "standard"
        assert modes["crisis"]["s1_autonomy"] == "restricted"
        assert modes["crisis"]["human_required"] is True

        # Elevated triggers from external forces
        assert len(modes["elevated"]["triggers"]) > 0
        assert "DSGVO-Anforderungen" in modes["elevated"]["triggers"]

        # Crisis triggers from inverted priority-1 criteria
        assert any("Kundenzufriedenheit" in t for t in modes["crisis"]["triggers"])

    def test_escalation_chains_generated(self):
        """Escalation chains werden mit korrekten Pfaden und Timeouts generiert."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        chains = config["viable_system"]["escalation_chains"]

        assert "operational" in chains
        assert "quality" in chains
        assert "strategic" in chains
        assert "algedonic" in chains

        # VSM standard paths
        assert chains["operational"]["path"] == ["s2-coordination", "s3-optimization", "human"]
        assert chains["quality"]["path"] == ["s3-optimization", "human"]
        assert chains["algedonic"]["path"] == ["s5-policy", "human"]

        # Algedonic timeout is always short
        assert chains["algedonic"]["timeout_per_step"] == "15min"

    def test_vollzug_protocol_generated(self):
        """Vollzug protocol ist enabled mit sinnvollen Timeouts."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        vollzug = config["viable_system"]["vollzug_protocol"]

        assert vollzug["enabled"] is True
        assert vollzug["timeout_quittung"] in ("15min", "30min")
        assert vollzug["timeout_vollzug"] in ("4h", "12h", "48h", "1w")
        assert vollzug["on_timeout"] in ("escalate", "remind", "alert_human")

    def test_s1_autonomy_levels_generated(self):
        """Jede S1-Unit bekommt strukturierte Autonomy-Levels."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)

        for unit in config["viable_system"]["system_1"]:
            al = unit["autonomy_levels"]
            assert "can_do_alone" in al
            assert "needs_coordination" in al
            assert "needs_approval" in al
            assert len(al["can_do_alone"]) > 0
            assert len(al["needs_approval"]) > 0

    def test_conflict_detection_generated(self):
        """S2 bekommt Conflict Detection aus Dependencies."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        cd = config["viable_system"]["system_2"]["conflict_detection"]

        assert cd["resource_overlaps"] is True  # shared_resources not empty
        assert cd["deadline_conflicts"] is True
        assert cd["output_contradictions"] is True  # >1 S1 unit

    def test_transduction_mappings_generated(self):
        """S2 bekommt Transduction Mappings aus Dependencies."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        tm = config["viable_system"]["system_2"]["transduction_mappings"]

        assert len(tm) == 2  # 2 dependencies
        assert tm[0]["from_unit"] == "Vertrieb"
        assert tm[0]["to_unit"] == "Produktion"

    def test_triple_index_generated(self):
        """S3 bekommt Triple Index."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        ti = config["viable_system"]["system_3"]["triple_index"]

        assert "actuality" in ti
        assert "capability" in ti
        assert "potentiality" in ti
        assert "measurement" in ti
        assert len(ti["measurement"]) > 0

    def test_s3star_provider_constraint(self):
        """S3* bekommt immer Provider-Constraint."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        s3star = config["viable_system"]["system_3_star"]

        assert s3star["provider_constraint"]["must_differ_from"] == "s1"
        assert s3star["reporting_target"] == "s3"
        assert len(s3star["independence_rules"]) >= 3

    def test_premises_register_from_forces(self):
        """S4 bekommt Prämissen aus external_forces."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        pr = config["viable_system"]["system_4"]["premises_register"]

        assert len(pr) == 3  # 3 external forces
        assert all("premise" in p for p in pr)
        assert all("check_frequency" in p for p in pr)

        # Regulation force should be monthly
        dsgvo_premise = [p for p in pr if "DSGVO" in p["premise"]][0]
        assert dsgvo_premise["check_frequency"] == "monthly"

        # Technology force should be weekly
        ki_premise = [p for p in pr if "KI" in p["premise"]][0]
        assert ki_premise["check_frequency"] == "weekly"

    def test_algedonic_channel_from_never_do(self):
        """Algedonic Channel triggers kommen aus identity.never_do."""
        assessment = _make_assessment(never_do=["Kundendaten verkaufen", "Mitarbeiter ausspionieren"])
        config = transform_assessment(assessment)
        ac = config["viable_system"]["identity"]["algedonic_channel"]

        assert ac["enabled"] is True
        assert ac["bypasses_hierarchy"] is True
        assert "Systemische Fehlfunktion" in ac["triggers"]
        # never_do items should be in triggers (they get "Ethik:" prefix from _make_assessment)
        assert len(ac["triggers"]) >= 2

    def test_schema_validates(self):
        """Transformiertes Assessment validiert gegen JSON Schema."""
        assessment = _make_assessment()
        config = transform_assessment(assessment)
        errors = validate(config)
        assert errors == [], f"Schema validation errors: {errors}"

    def test_small_team_defaults(self):
        """Team <= 2: kürzere Timeouts, mehr human_required."""
        assessment = _make_assessment(team_size=1)
        config = transform_assessment(assessment)
        vs = config["viable_system"]

        # Shorter timeouts
        assert vs["escalation_chains"]["operational"]["timeout_per_step"] == "1h"
        assert vs["vollzug_protocol"]["timeout_quittung"] == "15min"
        assert vs["vollzug_protocol"]["on_timeout"] == "alert_human"

        # More human approval
        assert vs["system_3"]["intervention_authority"]["requires_human_approval"] is True

        # Shorter escalation threshold
        assert vs["operational_modes"]["normal"]["escalation_threshold"] == "2h"
        assert vs["operational_modes"]["normal"]["reporting_frequency"] == "daily"

    def test_large_team_defaults(self):
        """Team > 5: längere Timeouts, mehr Autonomie."""
        assessment = _make_assessment(team_size=10)
        config = transform_assessment(assessment)
        vs = config["viable_system"]

        # Longer timeouts
        assert vs["escalation_chains"]["operational"]["timeout_per_step"] == "4h"
        assert vs["vollzug_protocol"]["timeout_quittung"] == "30min"
        assert vs["vollzug_protocol"]["on_timeout"] == "escalate"

        # Less human approval
        assert vs["system_3"]["intervention_authority"]["requires_human_approval"] is False

        # Longer escalation threshold
        assert vs["operational_modes"]["normal"]["escalation_threshold"] == "4h"
        assert vs["operational_modes"]["normal"]["reporting_frequency"] == "weekly"

    def test_no_external_forces(self):
        """Ohne external_forces: sinnvolle Defaults statt Crash."""
        assessment = _make_assessment(external_forces=[])
        config = transform_assessment(assessment)
        vs = config["viable_system"]

        # Elevated should still have triggers
        assert len(vs["operational_modes"]["elevated"]["triggers"]) > 0

        # Premises register is empty but present
        assert vs["system_4"]["premises_register"] == []

        # Schema still validates
        assert validate(config) == []

    def test_no_success_criteria(self):
        """Ohne success_criteria: sinnvolle Crisis-Defaults."""
        assessment = _make_assessment(success_criteria=[])
        config = transform_assessment(assessment)
        vs = config["viable_system"]

        # Crisis triggers should have a default
        assert len(vs["operational_modes"]["crisis"]["triggers"]) > 0
        assert validate(config) == []
