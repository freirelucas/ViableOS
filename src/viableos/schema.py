"""JSON Schema definition for ViableOS YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

_STRING_ARRAY = {"type": "array", "items": {"type": "string"}}

# ── Reusable sub-schemas for behavioral specs ──

_OPERATIONAL_MODE_CONFIG = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "description": {"type": "string"},
        "triggers": _STRING_ARRAY,
        "s1_autonomy": {
            "type": "string",
            "enum": ["full", "standard", "restricted"],
        },
        "reporting_frequency": {"type": "string"},
        "escalation_threshold": {"type": "string"},
        "human_required": {"type": "boolean"},
    },
}

_ESCALATION_PATH = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "path": _STRING_ARRAY,
        "timeout_per_step": {"type": "string"},
        "description": {"type": "string"},
        "triggers": _STRING_ARRAY,
    },
}

_AUTONOMY_LEVELS = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "can_do_alone": _STRING_ARRAY,
        "needs_coordination": _STRING_ARRAY,
        "needs_approval": _STRING_ARRAY,
    },
}

_CONFLICT_DETECTION = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resource_overlaps": {"type": "boolean"},
        "deadline_conflicts": {"type": "boolean"},
        "output_contradictions": {"type": "boolean"},
        "custom_triggers": _STRING_ARRAY,
    },
}

_TRANSDUCTION_MAPPING = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "from_unit": {"type": "string"},
        "to_unit": {"type": "string"},
        "translation": {"type": "string"},
    },
}

_TRIPLE_INDEX = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "actuality": {"type": "string"},
        "capability": {"type": "string"},
        "potentiality": {"type": "string"},
        "measurement": {"type": "string"},
    },
}

_DEVIATION_LOGIC = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "report_only_deviations": {"type": "boolean"},
        "threshold_percent": {"type": "number"},
        "trend_detection": {"type": "boolean"},
    },
}

_INTERVENTION_AUTHORITY = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "can_restrict_s1": {"type": "boolean"},
        "requires_documentation": {"type": "boolean"},
        "requires_human_approval": {"type": "boolean"},
        "max_duration": {"type": "string"},
        "allowed_actions": _STRING_ARRAY,
    },
}

_PROVIDER_CONSTRAINT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "must_differ_from": {
            "type": "string",
            "enum": ["s1", "all"],
        },
        "reason": {"type": "string"},
    },
}

_STRATEGIC_PREMISE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "premise": {"type": "string"},
        "check_frequency": {"type": "string"},
        "invalidation_signal": {"type": "string"},
        "consequence_if_invalid": {"type": "string"},
    },
}

_STRATEGY_BRIDGE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "injection_point": {"type": "string"},
        "format": {"type": "string"},
        "recipient": {"type": "string"},
    },
}

_WEAK_SIGNALS = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "enabled": {"type": "boolean"},
        "sources": _STRING_ARRAY,
        "detection_method": {"type": "string"},
    },
}

_BALANCE_MONITORING = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "s3_vs_s4_target": {"type": "string"},
        "measurement": {"type": "string"},
        "alert_if_exceeds": {"type": "string"},
    },
}

_ALGEDONIC_CHANNEL = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "enabled": {"type": "boolean"},
        "who_can_send": {
            "type": "string",
            "enum": ["all_agents", "s1_only"],
        },
        "triggers": _STRING_ARRAY,
        "bypasses_hierarchy": {"type": "boolean"},
    },
}

_BASTA_CONSTRAINT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "description": {"type": "string"},
        "examples": _STRING_ARRAY,
        "agent_role": {
            "type": "string",
            "enum": ["prepare_only"],
        },
    },
}

# ── Main schema ──

VIABLEOS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["viable_system"],
    "additionalProperties": False,
    "properties": {
        "viable_system": {
            "type": "object",
            "required": ["name", "identity", "system_1"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "runtime": {
                    "type": "string",
                    "enum": [
                        "openclaw",
                        "langgraph",
                        "crewai",
                        "openai-agents",
                        "cursor",
                    ],
                },
                "budget": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "monthly_usd": {"type": "number", "minimum": 0},
                        "strategy": {
                            "type": "string",
                            "enum": ["frugal", "balanced", "performance"],
                        },
                        "alerts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["at_percent", "action"],
                                "additionalProperties": False,
                                "properties": {
                                    "at_percent": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 100,
                                    },
                                    "action": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "model_routing": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "default": {"type": "string"},
                        "provider_preference": {
                            "type": "string",
                            "enum": [
                                "anthropic",
                                "openai",
                                "google",
                                "deepseek",
                                "xai",
                                "meta",
                                "mixed",
                                "ollama",
                            ],
                        },
                        "s1_routine": {"type": "string"},
                        "s1_complex": {"type": "string"},
                        "s2_coordination": {"type": "string"},
                        "s3_optimization": {"type": "string"},
                        "s3_star_audit": {"type": "string"},
                        "s4_intelligence": {"type": "string"},
                        "s5_preparation": {"type": "string"},
                        "fallback": {"type": "string"},
                    },
                },
                "human_in_the_loop": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "notification_channel": {
                            "type": "string",
                            "enum": [
                                "whatsapp",
                                "telegram",
                                "email",
                                "slack",
                                "discord",
                            ],
                        },
                        "approval_required": _STRING_ARRAY,
                        "review_required": _STRING_ARRAY,
                        "emergency_alerts": _STRING_ARRAY,
                    },
                },
                "persistence": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "strategy": {
                            "type": "string",
                            "enum": ["sqlite", "file", "notion", "custom", "none"],
                        },
                        "path": {"type": "string"},
                    },
                },
                "identity": {
                    "type": "object",
                    "required": ["purpose"],
                    "additionalProperties": False,
                    "properties": {
                        "purpose": {"type": "string"},
                        "values": _STRING_ARRAY,
                        "never_do": _STRING_ARRAY,
                        "decisions_requiring_human": _STRING_ARRAY,
                        "balance_monitoring": _BALANCE_MONITORING,
                        "algedonic_channel": _ALGEDONIC_CHANNEL,
                        "basta_constraint": _BASTA_CONSTRAINT,
                    },
                },
                "system_1": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "purpose"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "purpose": {"type": "string", "minLength": 1},
                            "autonomy": {"type": "string"},
                            "tools": _STRING_ARRAY,
                            "model": {"type": "string"},
                            "weight": {"type": "number", "minimum": 1, "maximum": 10},
                            "domain_context": {"type": "string"},
                            "sub_units": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "purpose"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {"type": "string", "minLength": 1},
                                        "purpose": {"type": "string"},
                                        "priority": {"type": "number"},
                                    },
                                },
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["target", "description"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "target": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                },
                            },
                            "autonomy_levels": _AUTONOMY_LEVELS,
                        },
                    },
                },
                "system_2": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "coordination_rules": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["trigger", "action"],
                                "additionalProperties": False,
                                "properties": {
                                    "trigger": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "action": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                },
                            },
                        },
                        "conflict_detection": _CONFLICT_DETECTION,
                        "transduction_mappings": {
                            "type": "array",
                            "items": _TRANSDUCTION_MAPPING,
                        },
                        "escalation_to_s3_after": {"type": "string"},
                        "label": {"type": "string"},
                    },
                },
                "system_3": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "reporting_rhythm": {"type": "string"},
                        "resource_allocation": {"type": "string"},
                        "kpi_list": _STRING_ARRAY,
                        "label": {"type": "string"},
                        "triple_index": _TRIPLE_INDEX,
                        "deviation_logic": _DEVIATION_LOGIC,
                        "intervention_authority": _INTERVENTION_AUTHORITY,
                    },
                },
                "system_3_star": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "schedule": {"type": "string"},
                        "checks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "target", "method"],
                                "additionalProperties": False,
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "target": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "method": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "data_source": {"type": "string"},
                                    "comparison": {"type": "string"},
                                },
                            },
                        },
                        "on_failure": {"type": "string"},
                        "label": {"type": "string"},
                        "provider_constraint": _PROVIDER_CONSTRAINT,
                        "reporting_target": {
                            "type": "string",
                            "enum": ["s3", "s3_and_human"],
                        },
                        "independence_rules": _STRING_ARRAY,
                    },
                },
                "system_4": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "monitoring": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "competitors": _STRING_ARRAY,
                                "technology": _STRING_ARRAY,
                                "regulation": _STRING_ARRAY,
                            },
                        },
                        "label": {"type": "string"},
                        "premises_register": {
                            "type": "array",
                            "items": _STRATEGIC_PREMISE,
                        },
                        "strategy_bridge": _STRATEGY_BRIDGE,
                        "weak_signals": _WEAK_SIGNALS,
                    },
                },
                "success_criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["criterion", "priority"],
                        "additionalProperties": False,
                        "properties": {
                            "criterion": {"type": "string"},
                            "priority": {"type": "string"},
                        },
                    },
                },
                "shared_resources": _STRING_ARRAY,
                "domain_flow": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "central_object": {"type": "string"},
                        "flow_description": {"type": "string"},
                        "feedback_loop": {"type": "string"},
                    },
                },
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["from", "to", "description"],
                        "additionalProperties": False,
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
                # ── Behavioral Specs (top-level) ──
                "operational_modes": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "normal": _OPERATIONAL_MODE_CONFIG,
                        "elevated": _OPERATIONAL_MODE_CONFIG,
                        "crisis": _OPERATIONAL_MODE_CONFIG,
                    },
                },
                "escalation_chains": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "operational": _ESCALATION_PATH,
                        "quality": _ESCALATION_PATH,
                        "strategic": _ESCALATION_PATH,
                        "algedonic": _ESCALATION_PATH,
                    },
                },
                "vollzug_protocol": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "timeout_quittung": {"type": "string"},
                        "timeout_vollzug": {"type": "string"},
                        "on_timeout": {
                            "type": "string",
                            "enum": ["escalate", "remind", "alert_human"],
                        },
                    },
                },
            },
        },
    },
}


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def validate(config: dict[str, Any]) -> list[str]:
    """Validate a config dict against the ViableOS schema.

    Returns a list of validation error messages (empty if valid).
    """
    validator = jsonschema.Draft202012Validator(VIABLEOS_SCHEMA)
    return [e.message for e in sorted(validator.iter_errors(config), key=str)]
