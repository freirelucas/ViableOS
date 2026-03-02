"""Tests for the VSM Completeness Checker."""

from pathlib import Path

from viableos.checker import check_viability
from viableos.schema import load_yaml

FIXTURES = Path(__file__).parent / "fixtures"


class TestCheckViability:
    def test_complete_config_scores_6(self):
        config = load_yaml(FIXTURES / "complete.yaml")
        report = check_viability(config)
        assert report.score == 6
        assert report.total == 6
        assert all(c.present for c in report.checks)

    def test_minimal_config_scores_2(self):
        """Minimal has only S1 and S5 (identity with purpose)."""
        config = load_yaml(FIXTURES / "minimal.yaml")
        report = check_viability(config)
        assert report.score == 2
        assert report.total == 6

        present = {c.system for c in report.checks if c.present}
        assert present == {"S1", "S5"}

    def test_missing_systems_have_suggestions(self):
        config = load_yaml(FIXTURES / "minimal.yaml")
        report = check_viability(config)
        for c in report.checks:
            if not c.present:
                assert len(c.suggestions) > 0

    def test_empty_purpose_is_not_present(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": ""},
                "system_1": [{"name": "u", "purpose": "p"}],
            }
        }
        report = check_viability(config)
        s5 = next(c for c in report.checks if c.system == "S5")
        assert not s5.present

    def test_whitespace_only_purpose_is_not_present(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "   "},
                "system_1": [{"name": "u", "purpose": "p"}],
            }
        }
        report = check_viability(config)
        s5 = next(c for c in report.checks if c.system == "S5")
        assert not s5.present

    def test_s1_details_lists_unit_names(self):
        config = load_yaml(FIXTURES / "complete.yaml")
        report = check_viability(config)
        s1 = next(c for c in report.checks if c.system == "S1")
        assert "Unit A" in s1.details
        assert "Unit B" in s1.details

    def test_s2_counts_rules(self):
        config = load_yaml(FIXTURES / "complete.yaml")
        report = check_viability(config)
        s2 = next(c for c in report.checks if c.system == "S2")
        assert "1 rule" in s2.details

    def test_s3_star_lists_check_names(self):
        config = load_yaml(FIXTURES / "complete.yaml")
        report = check_viability(config)
        s3star = next(c for c in report.checks if c.system == "S3*")
        assert "Quality Check" in s3star.details

    def test_healthcare_example_scores_6(self):
        config = load_yaml(FIXTURES / ".." / ".." / "examples" / "healthcare-saas.yaml")
        report = check_viability(config)
        assert report.score == 6

    def test_empty_config(self):
        config = {"viable_system": {}}
        report = check_viability(config)
        assert report.score == 0
        assert report.total == 6


class TestCommunityWarnings:
    """Tests for community-driven warnings (painpoints 1-7)."""

    def test_no_budget_gives_critical_warning(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p"}],
            }
        }
        report = check_viability(config)
        budget_warnings = [w for w in report.warnings if w.category == "Token Budget"]
        assert any(w.severity == "critical" for w in budget_warnings)

    def test_budget_without_alerts_gives_warning(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p"}],
                "budget": {"monthly_usd": 100},
            }
        }
        report = check_viability(config)
        budget_warnings = [w for w in report.warnings if w.category == "Token Budget"]
        assert any(w.severity == "warning" for w in budget_warnings)

    def test_model_warning_for_known_bad_model(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p", "model": "deepseek/deepseek-v3.2"}],
            }
        }
        report = check_viability(config)
        model_warnings = [w for w in report.warnings if w.category == "Model Warning"]
        assert len(model_warnings) >= 1
        assert "deepseek" in model_warnings[0].message.lower()

    def test_no_persistence_gives_warning(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p"}],
            }
        }
        report = check_viability(config)
        persistence_warnings = [w for w in report.warnings if w.category == "Persistence"]
        assert len(persistence_warnings) >= 1

    def test_persistence_sqlite_no_warning(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p"}],
                "persistence": {"strategy": "sqlite", "path": "./state"},
            }
        }
        report = check_viability(config)
        persistence_warnings = [w for w in report.warnings if w.category == "Persistence"]
        assert len(persistence_warnings) == 0

    def test_sensitive_tools_without_audit_critical(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p", "tools": ["ssh", "deployment"]}],
            }
        }
        report = check_viability(config)
        security_warnings = [w for w in report.warnings if w.category == "Security"]
        assert any(w.severity == "critical" for w in security_warnings)

    def test_no_never_do_gives_info(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "u", "purpose": "p"}],
            }
        }
        report = check_viability(config)
        security_warnings = [w for w in report.warnings if w.category == "Security"]
        assert any(w.severity == "info" and "never do" in w.message.lower() for w in security_warnings)

    def test_multiple_units_without_manual_rules_info(self):
        """2+ units without manual rules gets an info (auto-rules cover the base)."""
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [
                    {"name": "A", "purpose": "a"},
                    {"name": "B", "purpose": "b"},
                ],
            }
        }
        report = check_viability(config)
        coord_warnings = [w for w in report.warnings if w.category == "Coordination"]
        assert any(w.severity == "info" and "auto-generated" in w.message.lower() for w in coord_warnings)
        assert not any(w.message == "No anti-looping rule found." for w in coord_warnings)

    def test_many_units_without_hitl_warns_rollout(self):
        config = {
            "viable_system": {
                "name": "Test",
                "identity": {"purpose": "Test"},
                "system_1": [
                    {"name": "A", "purpose": "a"},
                    {"name": "B", "purpose": "b"},
                    {"name": "C", "purpose": "c"},
                    {"name": "D", "purpose": "d"},
                ],
            }
        }
        report = check_viability(config)
        rollout_warnings = [w for w in report.warnings if w.category == "Rollout"]
        assert any("start with 1-2" in w.message.lower() for w in rollout_warnings)


class TestBehavioralSpecWarnings:
    """Tests for behavioral spec completeness warnings."""

    def _behavioral_warnings(self, config: dict) -> list:
        report = check_viability(config)
        return [w for w in report.warnings if w.category == "Behavioral Specs"]

    def test_no_warnings_for_manual_config(self):
        """Manual configs (no behavioral spec fields) get no behavioral warnings."""
        config = {
            "viable_system": {
                "name": "Manual",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "Worker", "purpose": "Do stuff"}],
            }
        }
        assert self._behavioral_warnings(config) == []

    def test_complete_behavioral_specs_minimal_warnings(self):
        """A fully-specified behavioral config should have no warnings."""
        config = {
            "viable_system": {
                "name": "Full",
                "identity": {
                    "purpose": "Test",
                    "algedonic_channel": {
                        "enabled": True,
                        "who_can_send": "all_agents",
                        "triggers": ["Systemische Fehlfunktion"],
                        "bypasses_hierarchy": True,
                    },
                },
                "system_1": [
                    {
                        "name": "Worker",
                        "purpose": "Do stuff",
                        "autonomy_levels": {
                            "can_do_alone": ["Routine"],
                            "needs_coordination": ["Shared"],
                            "needs_approval": ["Budget"],
                        },
                    },
                ],
                "system_3_star": {
                    "checks": [{"name": "Audit", "target": "Worker", "method": "sample"}],
                    "provider_constraint": {"must_differ_from": "s1", "reason": "Independence"},
                },
                "system_4": {
                    "monitoring": {"competitors": "monthly"},
                    "premises_register": [
                        {"premise": "Market stable", "check_frequency": "monthly",
                         "invalidation_signal": "Crash", "consequence_if_invalid": "Pivot"},
                    ],
                },
                "operational_modes": {
                    "normal": {
                        "description": "Normal",
                        "s1_autonomy": "full",
                        "reporting_frequency": "weekly",
                        "escalation_threshold": "4h",
                    },
                    "elevated": {
                        "description": "Elevated",
                        "s1_autonomy": "standard",
                        "triggers": ["Risk event"],
                        "reporting_frequency": "daily",
                        "escalation_threshold": "2h",
                    },
                    "crisis": {
                        "description": "Crisis",
                        "s1_autonomy": "restricted",
                        "triggers": ["Critical failure"],
                        "reporting_frequency": "hourly",
                        "escalation_threshold": "30min",
                        "human_required": True,
                    },
                },
                "escalation_chains": {
                    "operational": {"path": ["s2", "s3", "human"], "timeout_per_step": "2h"},
                    "quality": {"path": ["s3", "human"], "timeout_per_step": "2h"},
                    "strategic": {"path": ["s4", "s5", "human"], "timeout_per_step": "4h"},
                    "algedonic": {"path": ["s5", "human"], "timeout_per_step": "15min"},
                },
                "vollzug_protocol": {
                    "enabled": True,
                    "timeout_quittung": "30min",
                    "timeout_vollzug": "48h",
                    "on_timeout": "escalate",
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert warnings == [], f"Unexpected warnings: {[w.message for w in warnings]}"

    def test_missing_operational_modes_warns(self):
        """Config with some behavioral fields but no modes → warning."""
        config = {
            "viable_system": {
                "name": "Partial",
                "identity": {"purpose": "Test"},
                "system_1": [
                    {"name": "A", "purpose": "a", "autonomy_levels": {
                        "can_do_alone": ["x"], "needs_coordination": [], "needs_approval": ["y"],
                    }},
                ],
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("operational modes" in w.message.lower() for w in warnings)

    def test_crisis_without_triggers_info(self):
        """Crisis mode defined but empty triggers → info."""
        config = {
            "viable_system": {
                "name": "NoTrigger",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": [], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("crisis" in w.message.lower() and "triggers" in w.message.lower()
                    for w in warnings)

    def test_missing_escalation_chains_warns(self):
        """Behavioral config without escalation chains → warning."""
        config = {
            "viable_system": {
                "name": "NoChains",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("escalation" in w.message.lower() for w in warnings)

    def test_missing_algedonic_chain_warns(self):
        """Escalation chains present but no algedonic → warning."""
        config = {
            "viable_system": {
                "name": "NoAlgedonic",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
                "escalation_chains": {
                    "operational": {"path": ["s2", "s3"], "timeout_per_step": "2h"},
                    "quality": {"path": ["s3"], "timeout_per_step": "2h"},
                    "strategic": {"path": ["s4", "s5"], "timeout_per_step": "4h"},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("algedonic" in w.message.lower() and "escalation" in w.message.lower()
                    for w in warnings)

    def test_vollzug_disabled_info(self):
        """Vollzug protocol not enabled → info."""
        config = {
            "viable_system": {
                "name": "NoVollzug",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
                "vollzug_protocol": {"enabled": False, "timeout_quittung": "30min",
                                     "timeout_vollzug": "48h", "on_timeout": "escalate"},
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("vollzug" in w.message.lower() for w in warnings)

    def test_s1_without_autonomy_levels_info(self):
        """S1 units missing autonomy levels in behavioral config → info."""
        config = {
            "viable_system": {
                "name": "NoAutonomy",
                "identity": {"purpose": "Test"},
                "system_1": [
                    {"name": "Alpha", "purpose": "a"},
                    {"name": "Beta", "purpose": "b"},
                ],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        autonomy_warns = [w for w in warnings if "autonomy" in w.message.lower()]
        assert len(autonomy_warns) == 1
        assert "Alpha" in autonomy_warns[0].message
        assert "Beta" in autonomy_warns[0].message

    def test_s3star_checks_without_provider_constraint_warns(self):
        """S3* with checks but no provider constraint → warning."""
        config = {
            "viable_system": {
                "name": "NoProv",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "system_3_star": {
                    "checks": [{"name": "Audit", "target": "A", "method": "sample"}],
                },
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("provider constraint" in w.message.lower() for w in warnings)

    def test_algedonic_channel_not_enabled_info(self):
        """Algedonic channel not enabled → info."""
        config = {
            "viable_system": {
                "name": "NoAlgedonic",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("algedonic channel" in w.message.lower() for w in warnings)

    def test_s4_monitoring_without_premises_info(self):
        """S4 monitoring but no premises register → info."""
        config = {
            "viable_system": {
                "name": "NoPremises",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "A", "purpose": "a"}],
                "system_4": {"monitoring": {"competitors": "monthly"}},
                "operational_modes": {
                    "normal": {"description": "N", "s1_autonomy": "full",
                               "reporting_frequency": "w", "escalation_threshold": "4h"},
                    "elevated": {"description": "E", "s1_autonomy": "standard",
                                 "triggers": ["x"], "reporting_frequency": "d",
                                 "escalation_threshold": "2h"},
                    "crisis": {"description": "C", "s1_autonomy": "restricted",
                               "triggers": ["y"], "reporting_frequency": "h",
                               "escalation_threshold": "30m", "human_required": True},
                },
            }
        }
        warnings = self._behavioral_warnings(config)
        assert any("premises" in w.message.lower() for w in warnings)

    def test_transformer_output_has_few_warnings(self):
        """Config from the transformer should have minimal behavioral warnings."""
        from viableos.assessment_transformer import transform_assessment

        assessment = {
            "system_name": "Test-Org",
            "purpose": "Testing",
            "team": {"size": 3, "roles": ["Dev"]},
            "recursion_levels": {
                "level_0": {
                    "operational_units": [
                        {"id": "dev", "name": "Dev", "description": "Develop", "priority": 1},
                    ],
                },
            },
            "dependencies": {"business_level": []},
            "external_forces": [
                {"name": "AI", "type": "technology", "frequency": "monthly"},
            ],
            "success_criteria": [
                {"criterion": "Quality > 90%", "priority": "1"},
            ],
            "shared_resources": [],
            "metasystem": {
                "s2_coordination": {"tasks": ["Sync"], "label": "Coord"},
                "s3_optimization": {"tasks": ["KPI"], "label": "Opt"},
                "s3_star_audit": {"tasks": ["Check"], "design_principle": "Escalate", "label": "Aud"},
                "s4_intelligence": {"tasks": ["Watch"], "label": "Intel"},
                "s5_policy": {"policies": ["Quality first"]},
            },
        }
        config = transform_assessment(assessment)
        report = check_viability(config)
        bw = [w for w in report.warnings if w.category == "Behavioral Specs"]
        # Transformer output should be well-formed → no warnings
        assert bw == [], f"Unexpected behavioral warnings: {[w.message for w in bw]}"
