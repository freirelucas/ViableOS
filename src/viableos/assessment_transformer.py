"""Transform an assessment_config.json into a viable_system config for the generator.

The assessment dialog produces a rich JSON with recursion levels, dependencies,
metasystem tasks, shared resources, external forces, etc. This module maps that
into the viable_system schema the generator expects, preserving domain context
that generic wizard-based configs would lack.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _priority_to_weight(priority: int | str) -> int:
    """Map assessment priority (1=highest) to generator weight (1-10, higher = more budget)."""
    mapping = {1: 8, 2: 5, 3: 3}
    if isinstance(priority, int):
        return mapping.get(priority, 5)
    return 5


def _classify_external_force(force: dict[str, Any]) -> str:
    """Classify an external force into competitors/technology/regulation."""
    name_lower = force.get("name", "").lower()
    regulation_keywords = [
        # German keywords
        "sgb", "dsgvo", "datenschutz", "compliance", "gesetz", "recht",
        "verordnung", "vergütung", "§",
        # English keywords
        "regulation", "gdpr", "privacy", "law", "legal", "ordinance",
        "compensation", "regulatory",
    ]
    tech_keywords = [
        "technolog", "llm", "ki", "ai", "algorithm", "software", "api",
    ]
    competition_keywords = [
        "wettbew", "konkur", "compet", "markt", "market",
    ]
    for kw in regulation_keywords:
        if kw in name_lower:
            return "regulation"
    for kw in tech_keywords:
        if kw in name_lower:
            return "technology"
    for kw in competition_keywords:
        if kw in name_lower:
            return "competitors"
    return "regulation"


def _build_s1_units(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert recursion levels into a flat S1 unit list with sub_unit metadata."""
    recursion = assessment.get("recursion_levels", {})
    level_0 = recursion.get("level_0", {})
    units_raw = level_0.get("operational_units", [])

    sub_levels = {
        key: val for key, val in recursion.items()
        if key.startswith("level_1")
    }
    parent_to_sublevel: dict[str, dict[str, Any]] = {}
    for sl in sub_levels.values():
        parent_id = sl.get("parent", "")
        if parent_id:
            parent_to_sublevel[parent_id] = sl

    s1_units: list[dict[str, Any]] = []
    for unit in units_raw:
        uid = unit.get("id", "")
        entry: dict[str, Any] = {
            "name": unit.get("name", uid),
            "purpose": unit.get("description", ""),
            "weight": _priority_to_weight(unit.get("priority", 2)),
        }

        if uid in parent_to_sublevel:
            sl = parent_to_sublevel[uid]
            sub_units = []
            for su in sl.get("operational_units", []):
                sub_units.append({
                    "name": su.get("name", su.get("id", "")),
                    "purpose": su.get("description", ""),
                    "priority": su.get("priority", 2),
                })
            entry["sub_units"] = sub_units

            central = sl.get("central_object")
            if central:
                entry["domain_context"] = (
                    f"Central object: {central['name']} "
                    f"({central.get('flow', '')})"
                )

        s1_units.append(entry)

    return s1_units


def _build_dependencies(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract business-level dependencies as structured list."""
    deps_raw = assessment.get("dependencies", {})
    result: list[dict[str, Any]] = []

    for dep in deps_raw.get("business_level", []):
        result.append({
            "from": dep.get("from", ""),
            "to": dep.get("to", ""),
            "description": dep.get("what", ""),
        })

    return result


def _build_domain_flow(assessment: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the central object flow if present."""
    deps = assessment.get("dependencies", {})
    pf = deps.get("product_flow")
    if not pf:
        return None
    return {
        "central_object": pf.get("central_object", ""),
        "flow_description": pf.get("direction", ""),
        "feedback_loop": pf.get("feedback_loop", ""),
    }


def _build_coordination_rules(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert S2 tasks + dependencies into coordination rules."""
    rules: list[dict[str, Any]] = []

    meta_s2 = assessment.get("metasystem", {}).get("s2_coordination", {})
    for task in meta_s2.get("tasks", []):
        rules.append({
            "trigger": f"Coordination needed for: {task}",
            "action": f"Coordinator handles {task} according to defined process",
        })

    for dep in assessment.get("dependencies", {}).get("business_level", []):
        rules.append({
            "trigger": f"{dep['from']} produces output affecting {dep['to']}",
            "action": f"Coordinator routes: {dep.get('what', 'information')}",
        })

    return rules


def _build_s3_config(assessment: dict[str, Any]) -> dict[str, Any]:
    """Map S3 optimization tasks to reporting and resource config."""
    meta_s3 = assessment.get("metasystem", {}).get("s3_optimization", {})
    tasks = meta_s3.get("tasks", [])

    kpi_list = [t for t in tasks if "kpi" in t.lower() or "tracking" in t.lower()]
    resource_tasks = [t for t in tasks if t not in kpi_list]

    return {
        "reporting_rhythm": "weekly",
        "resource_allocation": "; ".join(resource_tasks) if resource_tasks else "",
        "kpi_list": tasks,
        "label": meta_s3.get("label", "Optimizer"),
    }


def _build_s3star_config(assessment: dict[str, Any]) -> dict[str, Any]:
    """Map S3* audit tasks to checks."""
    meta = assessment.get("metasystem", {}).get("s3_star_audit", {})
    checks = []
    for task in meta.get("tasks", []):
        checks.append({
            "name": task,
            "target": "all_units",
            "method": "independent_verification",
        })
    result: dict[str, Any] = {"checks": checks}
    if meta.get("design_principle"):
        result["on_failure"] = meta["design_principle"]
    result["label"] = meta.get("label", "Auditor")
    return result


def _build_s4_config(assessment: dict[str, Any]) -> dict[str, Any]:
    """Map S4 tasks + external forces to monitoring config."""
    meta = assessment.get("metasystem", {}).get("s4_intelligence", {})
    forces = assessment.get("external_forces", [])

    competitors: list[str] = []
    technology: list[str] = []
    regulation: list[str] = []

    for task in meta.get("tasks", []):
        cat = _classify_external_force({"name": task})
        {"competitors": competitors, "technology": technology, "regulation": regulation}[cat].append(task)

    for force in forces:
        cat = _classify_external_force(force)
        entry = force["name"]
        if force.get("frequency"):
            entry += f" ({force['frequency']})"
        target = {"competitors": competitors, "technology": technology, "regulation": regulation}[cat]
        if entry not in target:
            target.append(entry)

    return {
        "monitoring": {
            "competitors": competitors,
            "technology": technology,
            "regulation": regulation,
        },
        "label": meta.get("label", "Scout"),
    }


def _build_identity(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build identity from purpose + S5 policies."""
    meta_s5 = assessment.get("metasystem", {}).get("s5_policy", {})
    policies = meta_s5.get("policies", [])

    values = [p for p in policies if not p.lower().startswith("ethik")]
    never_do_raw = [p for p in policies if p.lower().startswith("ethik")]

    identity: dict[str, Any] = {
        "purpose": assessment.get("purpose", ""),
        "values": values,
    }
    if never_do_raw:
        identity["never_do"] = never_do_raw

    return identity


def _build_hitl(assessment: dict[str, Any]) -> dict[str, Any]:
    """Set human-in-the-loop defaults based on team size."""
    team = assessment.get("team", {})
    size = team.get("size", 1)

    hitl: dict[str, Any] = {
        "notification_channel": "whatsapp",
        "approval_required": ["deployment", "budget_changes", "new_agent_creation"],
    }

    if size <= 2:
        hitl["approval_required"].extend([
            "customer_communication",
            "data_deletion",
        ])

    return hitl


# ── Behavioral Spec Builders ──


def _get_team_size(assessment: dict[str, Any]) -> int:
    """Extract team size from assessment, default 1."""
    return assessment.get("team", {}).get("size", 1)


def _build_operational_modes(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build operational modes from external_forces + success_criteria + team size."""
    team_size = _get_team_size(assessment)
    forces = assessment.get("external_forces", [])
    criteria = assessment.get("success_criteria", [])

    # Elevated triggers from external forces (risks)
    elevated_triggers = [f["name"] for f in forces[:3]] if forces else ["External pressure detected"]

    # Crisis triggers from inverted priority-1 success criteria
    crisis_triggers = []
    for c in criteria:
        prio = c.get("priority", 2)
        if str(prio) == "1":
            crisis_triggers.append(f"Failure: {c['criterion']}")
    if not crisis_triggers:
        crisis_triggers = ["Critical system failure"]

    # Reporting frequency proportional to team size
    if team_size <= 2:
        normal_freq = "daily"
        elevated_freq = "twice_daily"
    elif team_size <= 5:
        normal_freq = "weekly"
        elevated_freq = "daily"
    else:
        normal_freq = "weekly"
        elevated_freq = "daily"

    return {
        "normal": {
            "description": "Day-to-day operations, full unit autonomy",
            "s1_autonomy": "full",
            "reporting_frequency": normal_freq,
            "escalation_threshold": "2h" if team_size <= 2 else "4h",
        },
        "elevated": {
            "description": "Heightened vigilance under external pressure",
            "triggers": elevated_triggers,
            "s1_autonomy": "standard",
            "reporting_frequency": elevated_freq,
            "escalation_threshold": "30min" if team_size <= 2 else "1h",
        },
        "crisis": {
            "description": "Acute crisis, centralized control",
            "triggers": crisis_triggers,
            "s1_autonomy": "restricted",
            "reporting_frequency": "hourly",
            "escalation_threshold": "immediate",
            "human_required": True,
        },
    }


def _build_escalation_chains(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build escalation chains with timeouts based on team size."""
    team_size = _get_team_size(assessment)
    identity = _build_identity(assessment)
    never_do = identity.get("never_do", [])

    if team_size <= 2:
        timeout = "1h"
    elif team_size <= 5:
        timeout = "2h"
    else:
        timeout = "4h"

    algedonic_triggers = list(never_do) if never_do else []
    algedonic_triggers.append("Systemic malfunction")

    return {
        "operational": {
            "path": ["s2-coordination", "s3-optimization", "human"],
            "timeout_per_step": timeout,
        },
        "quality": {
            "path": ["s3-optimization", "human"],
            "timeout_per_step": timeout,
        },
        "strategic": {
            "path": ["s5-policy", "human"],
            "timeout_per_step": timeout,
        },
        "algedonic": {
            "path": ["s5-policy", "human"],
            "timeout_per_step": "15min",
            "description": "Pain signal for fundamental problem",
            "triggers": algedonic_triggers,
        },
    }


def _build_execution_protocol(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build execution protocol with timeouts based on team size and reporting rhythm."""
    team_size = _get_team_size(assessment)
    s3_config = _build_s3_config(assessment)
    rhythm = s3_config.get("reporting_rhythm", "weekly")

    timeout_acknowledgment = "15min" if team_size <= 2 else "30min"

    rhythm_to_completion = {
        "hourly": "4h",
        "daily": "12h",
        "weekly": "48h",
        "monthly": "1w",
    }
    timeout_completion = rhythm_to_completion.get(rhythm, "48h")

    on_timeout = "alert_human" if team_size <= 2 else "escalate"

    return {
        "enabled": True,
        "timeout_acknowledgment": timeout_acknowledgment,
        "timeout_completion": timeout_completion,
        "on_timeout": on_timeout,
    }


def _build_s1_autonomy_levels(
    unit: dict[str, Any],
    hitl: dict[str, Any],
    dependencies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build structured autonomy levels for an S1 unit."""
    approval_required = hitl.get("approval_required", [])

    unit_name = unit.get("name", "")
    tools = unit.get("tools", [])
    purpose = unit.get("purpose", "")

    can_do_alone = []
    if purpose:
        can_do_alone.append(purpose)
    for tool in tools:
        can_do_alone.append(f"Use of {tool}")

    needs_coordination = []
    for dep in dependencies:
        if dep.get("from") == unit_name or dep.get("to") == unit_name:
            needs_coordination.append(dep.get("description", "Coordination with other unit"))

    return {
        "can_do_alone": can_do_alone,
        "needs_coordination": needs_coordination if needs_coordination else ["Resource sharing with other units"],
        "needs_approval": list(approval_required),
    }


def _build_conflict_detection(
    dependencies: list[dict[str, Any]],
    shared_resources: list[str],
    s1_count: int,
) -> dict[str, Any]:
    """Build S2 conflict detection from dependencies and shared resources."""
    custom_triggers = []
    for dep in dependencies:
        desc = dep.get("description", "")
        if desc:
            custom_triggers.append(f"Conflict potential: {desc}")

    return {
        "resource_overlaps": len(shared_resources) > 0,
        "deadline_conflicts": True,
        "output_contradictions": s1_count > 1,
        "custom_triggers": custom_triggers if custom_triggers else None,
    }


def _build_transduction_mappings(
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build S2 transduction mappings from dependencies."""
    mappings = []
    for dep in dependencies:
        from_unit = dep.get("from", "")
        to_unit = dep.get("to", "")
        desc = dep.get("description", "")
        if from_unit and to_unit:
            mappings.append({
                "from_unit": from_unit,
                "to_unit": to_unit,
                "translation": f"What {from_unit} delivers as '{desc}' is an input for {to_unit}",
            })
    return mappings


def _build_triple_index(
    s3_config: dict[str, Any],
    success_criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build S3 triple index from KPIs and success criteria."""
    kpis = s3_config.get("kpi_list", [])
    measurement = "; ".join(kpis[:3]) if kpis else "Output volume, quality, throughput time"

    criteria_texts = [c.get("criterion", "") for c in success_criteria[:2]]
    criteria_hint = "; ".join(criteria_texts) if criteria_texts else "Core performance"

    return {
        "actuality": f"Current performance measured against: {criteria_hint}",
        "capability": "Maximum performance at optimal utilization of all units",
        "potentiality": "Achievable performance with targeted investment in bottlenecks",
        "measurement": measurement,
    }


def _build_deviation_logic(budget_strategy: str) -> dict[str, Any]:
    """Build S3 deviation logic based on budget strategy."""
    threshold_map = {
        "frugal": 10,
        "balanced": 15,
        "performance": 20,
    }
    return {
        "report_only_deviations": True,
        "threshold_percent": threshold_map.get(budget_strategy, 15),
        "trend_detection": True,
    }


def _build_intervention_authority(assessment: dict[str, Any]) -> dict[str, Any]:
    """Build S3 intervention authority based on team size."""
    team_size = _get_team_size(assessment)
    return {
        "can_restrict_s1": True,
        "requires_documentation": True,
        "requires_human_approval": team_size <= 2,
        "max_duration": "48h",
        "allowed_actions": [
            "Freeze budget",
            "Reroute task",
            "Downgrade model",
        ],
    }


def _build_s3star_extensions() -> dict[str, Any]:
    """Build S3* behavioral extensions (always the same — VSM principle)."""
    return {
        "provider_constraint": {
            "must_differ_from": "s1",
            "reason": "Prevents correlated hallucinations",
        },
        "reporting_target": "s3",
        "independence_rules": [
            "No write access to S1 workspaces",
            "No access to S1 prompts",
            "Own data sources for verification",
        ],
    }


def _build_premises_register(
    external_forces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build S4 premises register from external forces."""
    type_to_frequency = {
        "regulation": "monthly",
        "technology": "weekly",
        "competitors": "monthly",
    }
    premises = []
    for force in external_forces:
        force_type = _classify_external_force(force)
        freq = type_to_frequency.get(force_type, "monthly")
        name = force.get("name", "Unknown force")
        premises.append({
            "premise": f"Assumption regarding: {name}",
            "check_frequency": freq,
            "invalidation_signal": f"Significant change in: {name}",
            "consequence_if_invalid": f"Strategy regarding {name} must be reviewed",
        })
    return premises


def _build_strategy_bridge(s3_config: dict[str, Any]) -> dict[str, Any]:
    """Build S4 strategy bridge tied to S3 reporting rhythm."""
    rhythm = s3_config.get("reporting_rhythm", "weekly")
    return {
        "injection_point": f"Before the {rhythm} reporting",
        "format": "Strategic briefing with max. 3 action recommendations",
        "recipient": "s3-optimization",
    }


def _build_identity_extensions(
    identity: dict[str, Any],
    budget_strategy: str,
) -> dict[str, Any]:
    """Build S5/identity behavioral extensions."""
    balance_map = {
        "frugal": ("70/30", "85/15"),
        "balanced": ("60/40", "80/20"),
        "performance": ("50/50", "75/25"),
    }
    target, alert = balance_map.get(budget_strategy, ("60/40", "80/20"))

    never_do = identity.get("never_do", [])
    algedonic_triggers = list(never_do) if never_do else []
    algedonic_triggers.append("Systemic malfunction")

    return {
        "balance_monitoring": {
            "s3_vs_s4_target": target,
            "measurement": "Share of agent tokens flowing into S3 vs S4",
            "alert_if_exceeds": alert,
        },
        "algedonic_channel": {
            "enabled": True,
            "who_can_send": "all_agents",
            "triggers": algedonic_triggers,
            "bypasses_hierarchy": True,
        },
        "basta_constraint": {
            "description": "Normative decisions in cases of undecidability",
            "examples": [
                "Strategy change",
                "Merger/Acquisition",
                "Ethics dilemma",
            ],
            "agent_role": "prepare_only",
        },
    }


def transform_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    """Convert an assessment_config.json dict into a viable_system config.

    Returns a dict compatible with the ViableOS schema, enriched with
    domain-specific fields from the assessment.
    """
    s1_units = _build_s1_units(assessment)
    dependencies = _build_dependencies(assessment)
    domain_flow = _build_domain_flow(assessment)
    coord_rules = _build_coordination_rules(assessment)
    s3_config = _build_s3_config(assessment)
    s3star_config = _build_s3star_config(assessment)
    s4_config = _build_s4_config(assessment)
    identity = _build_identity(assessment)
    hitl = _build_hitl(assessment)

    success_criteria = assessment.get("success_criteria", [])
    shared_resources = assessment.get("shared_resources", [])
    external_forces = assessment.get("external_forces", [])
    budget_strategy = "balanced"

    # ── Behavioral Specs ──

    # Top-level
    operational_modes = _build_operational_modes(assessment)
    escalation_chains = _build_escalation_chains(assessment)
    execution_protocol = _build_execution_protocol(assessment)

    # S1: autonomy levels per unit
    for unit in s1_units:
        unit["autonomy_levels"] = _build_s1_autonomy_levels(
            unit, hitl, dependencies,
        )

    # S2: conflict detection + transduction
    s1_count = len(s1_units)
    conflict_detection = _build_conflict_detection(dependencies, shared_resources, s1_count)
    transduction_mappings = _build_transduction_mappings(dependencies)

    # S3: triple index, deviation logic, intervention authority
    triple_index = _build_triple_index(s3_config, success_criteria)
    deviation_logic = _build_deviation_logic(budget_strategy)
    intervention_authority = _build_intervention_authority(assessment)

    # S3*: extensions
    s3star_ext = _build_s3star_extensions()

    # S4: premises register + strategy bridge
    premises_register = _build_premises_register(external_forces)
    strategy_bridge = _build_strategy_bridge(s3_config)

    # S5/Identity: extensions
    identity_ext = _build_identity_extensions(identity, budget_strategy)

    # ── Merge behavioral specs into existing configs ──

    # S2
    s2_config: dict[str, Any] = {"coordination_rules": coord_rules}
    s2_config["conflict_detection"] = conflict_detection
    if conflict_detection.get("custom_triggers") is None:
        del s2_config["conflict_detection"]["custom_triggers"]
    if transduction_mappings:
        s2_config["transduction_mappings"] = transduction_mappings

    # S3
    s3_config["triple_index"] = triple_index
    s3_config["deviation_logic"] = deviation_logic
    s3_config["intervention_authority"] = intervention_authority

    # S3*
    s3star_config.update(s3star_ext)

    # S4
    s4_config["premises_register"] = premises_register
    s4_config["strategy_bridge"] = strategy_bridge
    s4_config["weak_signals"] = {"enabled": True}

    # Identity
    identity.update(identity_ext)

    config: dict[str, Any] = {
        "viable_system": {
            "name": assessment.get("system_name", "Unnamed System"),
            "identity": identity,
            "system_1": s1_units,
            "system_2": s2_config,
            "system_3": s3_config,
            "system_3_star": s3star_config,
            "system_4": s4_config,
            "human_in_the_loop": hitl,
            "budget": {
                "monthly_usd": 150.0,
                "strategy": "balanced",
            },
            "success_criteria": success_criteria,
            "shared_resources": shared_resources,
            "operational_modes": operational_modes,
            "escalation_chains": escalation_chains,
            "execution_protocol": execution_protocol,
        },
    }

    if domain_flow:
        config["viable_system"]["domain_flow"] = domain_flow

    if dependencies:
        config["viable_system"]["dependencies"] = dependencies

    return config


def load_assessment(path: str | Path) -> dict[str, Any]:
    """Load an assessment_config.json file."""
    with open(path) as f:
        return json.load(f)
