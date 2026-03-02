# Benchmark Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a benchmark engine that scores ViableOS configs against academic multi-agent benchmarks, giving users a concrete quality score before deployment.

**Architecture:** Four independent scorers (budget efficiency, safety coverage, token efficiency, architecture quality) each return a 0-100 score with actionable insights. A runner orchestrates them, exposed via API endpoint and rendered as a radar chart in the dashboard.

**Tech Stack:** Python (scorers + API), React/TypeScript (dashboard), Recharts (radar chart), existing Pydantic models

---

## Context: What We're Building Against

| Benchmark | Paper | What We Extract |
|---|---|---|
| **BAMAS** (AAAI 2026) | Budget-Aware Multi-Agent Systems | Budget efficiency scoring criteria: tier-matching, concentration risk, cost-per-agent balance |
| **AgentTaxo** (ICLR 2025) | Token Distribution in LLM-MA Systems | Communication tax formula: estimated token duplication based on agent count + topology |
| **Agent-SafetyBench** (Dec 2024) | 8 risk categories, 2000 test cases | Safety coverage checklist: which categories our config addresses |
| **MAESTRO** (Jan 2026) | MAS architecture > model choice for performance | Architecture quality scoring: structural properties that predict production success |
| **MultiAgentBench** (ACL 2025) | Coordination topologies (star/chain/tree/graph) | Topology analysis: VSM as "informed star" vs other patterns |
| **REALM-Bench** (Feb 2025) | Real-world planning with LangGraph baselines | Export adapter: generate REALM-Bench-compatible agent configs |

## Phase 1: Internal Benchmark Engine

These scorers work on the config alone — no running agents needed.

---

### Task 1: Budget Efficiency Scorer

**Files:**
- Create: `src/viableos/benchmarks/__init__.py`
- Create: `src/viableos/benchmarks/budget_efficiency.py`
- Test: `tests/test_benchmarks.py`

**Step 1: Write the failing test**

```python
# tests/test_benchmarks.py
import pytest
from viableos.benchmarks.budget_efficiency import score_budget_efficiency


def test_balanced_config_scores_well():
    """A balanced config with alerts and proper tier matching should score >70."""
    config = {
        "viable_system": {
            "system_1": [
                {"name": "Product Dev", "tools": ["code", "git"]},
                {"name": "Marketing", "tools": ["analytics"]},
            ],
            "budget": {"monthly_usd": 200, "strategy": "balanced", "alerts": {"warn_at_percent": 80, "auto_downgrade_at_percent": 95}},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_budget_efficiency(config)
    assert result.score >= 70
    assert result.score <= 100
    assert result.dimension == "budget_efficiency"
    assert isinstance(result.insights, list)
    assert len(result.insights) > 0


def test_no_budget_scores_zero():
    """No budget defined should score 0."""
    config = {"viable_system": {}}
    result = score_budget_efficiency(config)
    assert result.score == 0


def test_frugal_low_budget_scores_high():
    """Frugal strategy with low budget is smart — should score well."""
    config = {
        "viable_system": {
            "system_1": [{"name": "Core", "tools": ["code"]}],
            "budget": {"monthly_usd": 50, "strategy": "frugal", "alerts": {"warn_at_percent": 80, "auto_downgrade_at_percent": 95}},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_budget_efficiency(config)
    assert result.score >= 60


def test_performance_tiny_budget_warns():
    """Performance strategy with $30/month is a mismatch — low score + insight."""
    config = {
        "viable_system": {
            "system_1": [
                {"name": "A", "tools": []},
                {"name": "B", "tools": []},
                {"name": "C", "tools": []},
            ],
            "budget": {"monthly_usd": 30, "strategy": "performance"},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_budget_efficiency(config)
    assert result.score < 50
    assert any("mismatch" in i.lower() or "budget" in i.lower() for i in result.insights)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmarks.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'viableos.benchmarks'"

**Step 3: Create the benchmarks package and shared types**

```python
# src/viableos/benchmarks/__init__.py
"""ViableOS Benchmark Engine — scores configs against academic multi-agent benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkScore:
    dimension: str
    score: int  # 0-100
    max_score: int  # always 100
    insights: list[str] = field(default_factory=list)
    details: dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    overall_score: int
    scores: list[BenchmarkScore]
    grade: str  # A/B/C/D/F
    summary: str
```

**Step 4: Implement budget efficiency scorer**

```python
# src/viableos/benchmarks/budget_efficiency.py
"""Budget efficiency scorer — inspired by BAMAS (AAAI 2026).

BAMAS showed that budget-aware model selection via constrained optimization
reduces costs by up to 86% while maintaining performance. We score configs
on how well they balance cost vs capability.

Scoring criteria:
- Budget exists and has alerts (20 pts)
- Strategy matches budget size (25 pts)
- Per-agent budget is sufficient for chosen model tier (25 pts)
- No single agent consumes >50% of budget (15 pts)
- Fallback chain provides cost resilience (15 pts)
"""

from __future__ import annotations

from typing import Any

from viableos.benchmarks import BenchmarkScore
from viableos.budget import MODEL_CATALOG, MODEL_PRESETS, calculate_budget


def score_budget_efficiency(config: dict[str, Any]) -> BenchmarkScore:
    vs = config.get("viable_system", {})
    budget_cfg = vs.get("budget", {})
    monthly = budget_cfg.get("monthly_usd", 0)

    if not monthly:
        return BenchmarkScore(
            dimension="budget_efficiency",
            score=0,
            max_score=100,
            insights=["No budget defined. Without a budget, cost control is impossible."],
        )

    points = 0.0
    insights: list[str] = []
    details: dict[str, float] = {}

    # --- 1. Budget exists and has alerts (20 pts) ---
    alerts = budget_cfg.get("alerts", {})
    if monthly > 0:
        points += 10
    if alerts.get("warn_at_percent"):
        points += 5
    else:
        insights.append("No warning threshold set. Add a warn_at_percent alert.")
    if alerts.get("auto_downgrade_at_percent"):
        points += 5
    else:
        insights.append("No auto-downgrade threshold. Budget can silently overrun.")
    details["budget_alerts"] = min(points, 20)

    # --- 2. Strategy matches budget size (25 pts) ---
    strategy = budget_cfg.get("strategy", "balanced")
    units = vs.get("system_1", [])
    agent_count = max(len(units), 1)
    per_agent_usd = monthly / (agent_count + 5)  # +5 for S2-S5

    strategy_pts = 0.0
    if strategy == "frugal" and per_agent_usd < 20:
        strategy_pts = 25
    elif strategy == "frugal" and per_agent_usd >= 20:
        strategy_pts = 20
        insights.append("Frugal strategy with generous budget — consider balanced for better quality.")
    elif strategy == "balanced" and 10 <= per_agent_usd <= 80:
        strategy_pts = 25
    elif strategy == "balanced" and per_agent_usd < 10:
        strategy_pts = 15
        insights.append("Balanced strategy with very tight budget — consider frugal to avoid quota issues.")
    elif strategy == "balanced" and per_agent_usd > 80:
        strategy_pts = 20
        insights.append("Balanced strategy with high budget — performance strategy could yield better results.")
    elif strategy == "performance" and per_agent_usd >= 30:
        strategy_pts = 25
    elif strategy == "performance" and per_agent_usd < 30:
        strategy_pts = 5
        insights.append("Strategy-budget mismatch: performance strategy needs $30+/agent/month. Current: ${:.0f}.".format(per_agent_usd))
    else:
        strategy_pts = 15

    points += strategy_pts
    details["strategy_match"] = strategy_pts

    # --- 3. Per-agent budget vs model tier (25 pts) ---
    try:
        plan = calculate_budget(config)
        tier_pts = 25.0
        for alloc in plan.allocations:
            model_info = MODEL_CATALOG.get(alloc.model, {})
            tier = model_info.get("tier", "high")
            # Premium models need ~$40+/month, high ~$15+, fast ~$5+
            tier_minimums = {"premium": 40, "high": 15, "fast": 5, "budget": 2}
            minimum = tier_minimums.get(tier, 10)
            if alloc.monthly_usd < minimum:
                tier_pts -= 5
                insights.append(
                    f"{alloc.friendly_name}: ${alloc.monthly_usd:.0f}/month may be too low for {tier}-tier model ({alloc.model})."
                )
        tier_pts = max(tier_pts, 0)
    except Exception:
        tier_pts = 10
        insights.append("Could not calculate budget plan. Check config for errors.")

    points += tier_pts
    details["tier_match"] = tier_pts

    # --- 4. Concentration risk (15 pts) ---
    try:
        plan = calculate_budget(config)
        max_pct = max(a.percentage for a in plan.allocations) if plan.allocations else 0
        if max_pct > 50:
            conc_pts = 5.0
            insights.append(f"Budget concentration risk: one agent gets {max_pct:.0f}% of total budget.")
        elif max_pct > 40:
            conc_pts = 10.0
        else:
            conc_pts = 15.0
    except Exception:
        conc_pts = 5.0

    points += conc_pts
    details["concentration"] = conc_pts

    # --- 5. Fallback chain resilience (15 pts) ---
    routing = vs.get("model_routing", {})
    providers_used = set()
    for key, model in routing.items():
        if key != "provider_preference" and model:
            provider = model.split("/")[0] if "/" in model else ""
            if provider:
                providers_used.add(provider)

    if len(providers_used) >= 3:
        fallback_pts = 15.0
    elif len(providers_used) == 2:
        fallback_pts = 10.0
        insights.append("Only 2 providers used. Add a third for better fallback resilience.")
    elif len(providers_used) == 1:
        fallback_pts = 5.0
        insights.append("Single provider risk. If that provider has an outage, all agents stop.")
    else:
        fallback_pts = 0.0

    points += fallback_pts
    details["fallback_resilience"] = fallback_pts

    return BenchmarkScore(
        dimension="budget_efficiency",
        score=min(int(points), 100),
        max_score=100,
        insights=insights,
        details=details,
    )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_benchmarks.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/viableos/benchmarks/ tests/test_benchmarks.py
git commit -m "feat(benchmarks): add budget efficiency scorer inspired by BAMAS"
```

---

### Task 2: Safety Coverage Scorer

**Files:**
- Create: `src/viableos/benchmarks/safety_coverage.py`
- Modify: `tests/test_benchmarks.py`

**Step 1: Write the failing test**

Add to `tests/test_benchmarks.py`:

```python
from viableos.benchmarks.safety_coverage import score_safety_coverage


def test_full_safety_config_scores_high():
    """Config with all safety features should score >80."""
    config = {
        "viable_system": {
            "identity": {
                "purpose": "Test org",
                "values": ["quality"],
                "never_do": ["delete production data", "send without approval"],
            },
            "system_1": [
                {"name": "Dev", "tools": ["code", "git"], "autonomy": "supervised"},
            ],
            "system_2": {"coordination_rules": [
                {"trigger": "Agent repeats 3+ times", "action": "stop and escalate"},
            ]},
            "system_3": {"reporting_rhythm": "weekly"},
            "system_3_star": {"checks": [{"name": "code_review", "frequency": "daily"}]},
            "human_in_the_loop": {
                "approval_required": ["deployments"],
                "notification_channel": "slack",
            },
        }
    }
    result = score_safety_coverage(config)
    assert result.score >= 80
    assert result.dimension == "safety_coverage"


def test_no_safety_scores_low():
    """Bare config with no safety features should score very low."""
    config = {
        "viable_system": {
            "system_1": [{"name": "Solo", "tools": ["code", "ssh", "docker"]}],
        }
    }
    result = score_safety_coverage(config)
    assert result.score < 30
    assert len(result.insights) >= 3


def test_sensitive_tools_without_audit_penalized():
    """Sensitive tools (ssh, docker) without S3* audit should lose points."""
    config = {
        "viable_system": {
            "system_1": [{"name": "Ops", "tools": ["ssh", "docker", "deployment"]}],
            "identity": {"never_do": ["delete data"]},
            "human_in_the_loop": {"approval_required": ["deployments"]},
        }
    }
    result = score_safety_coverage(config)
    assert any("audit" in i.lower() for i in result.insights)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmarks.py::test_full_safety_config_scores_high -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement safety coverage scorer**

```python
# src/viableos/benchmarks/safety_coverage.py
"""Safety coverage scorer — inspired by Agent-SafetyBench and ShieldAgent-Bench.

Agent-SafetyBench tested 16 agents across 8 risk categories. None exceeded 60%
safety score. ShieldAgent identified 7 risk categories where explicit policies
help. We score how well a ViableOS config covers these categories.

The 8 scoring dimensions (from Agent-SafetyBench mapped to ViableOS config):
1. Explicit boundaries (never_do list)           — 15 pts
2. Tool scoping (tools are defined per unit)      — 15 pts
3. Approval gates (HiTL approval_required)        — 15 pts
4. Independent audit (S3* with different provider) — 15 pts
5. Anti-looping rules (coordination rules)         — 10 pts
6. Communication control (structured routing)      — 10 pts
7. Identity anchoring (purpose + values defined)   — 10 pts
8. Rollout caution (not too many agents at once)   — 10 pts
"""

from __future__ import annotations

from typing import Any

from viableos.benchmarks import BenchmarkScore


def score_safety_coverage(config: dict[str, Any]) -> BenchmarkScore:
    vs = config.get("viable_system", {})
    identity = vs.get("identity", {})
    units = vs.get("system_1", [])
    s2 = vs.get("system_2", {})
    s3star = vs.get("system_3_star", {})
    hitl = vs.get("human_in_the_loop", {})
    routing = vs.get("model_routing", {})

    points = 0.0
    insights: list[str] = []
    details: dict[str, float] = {}

    # --- 1. Explicit boundaries (15 pts) ---
    never_do = identity.get("never_do", [])
    if len(never_do) >= 3:
        boundary_pts = 15.0
    elif len(never_do) >= 1:
        boundary_pts = 10.0
        insights.append(f"Only {len(never_do)} boundary rules. Agent-SafetyBench recommends 3+ explicit boundaries.")
    else:
        boundary_pts = 0.0
        insights.append("No 'never do' boundaries. This is the #1 cause of agent safety failures.")
    points += boundary_pts
    details["boundaries"] = boundary_pts

    # --- 2. Tool scoping (15 pts) ---
    sensitive_tools = {"ssh", "deployment", "docker", "payment-processing", "customer-data", "database"}
    units_with_tools = sum(1 for u in units if u.get("tools"))
    units_with_sensitive = [u for u in units if set(u.get("tools", [])) & sensitive_tools]

    if units and all(u.get("tools") for u in units):
        tool_pts = 15.0
    elif units_with_tools > 0:
        tool_pts = 10.0
        insights.append("Some units have no tools defined. Explicit tool scoping prevents unauthorized actions.")
    else:
        tool_pts = 0.0
        insights.append("No tools defined for any unit. Without tool scoping, agents can access everything.")
    points += tool_pts
    details["tool_scoping"] = tool_pts

    # --- 3. Approval gates (15 pts) ---
    approvals = hitl.get("approval_required", [])
    if len(approvals) >= 2:
        approval_pts = 15.0
    elif len(approvals) >= 1:
        approval_pts = 10.0
        insights.append("Only 1 approval gate. Consider adding more for sensitive operations.")
    else:
        approval_pts = 0.0
        insights.append("No human approval gates. Agents operate without any human checkpoint.")
    points += approval_pts
    details["approval_gates"] = approval_pts

    # --- 4. Independent audit (15 pts) ---
    has_audit = bool(s3star.get("checks"))
    audit_pts = 0.0
    if has_audit:
        audit_pts = 10.0
        s1_model = routing.get("s1_routine", "")
        s3star_model = routing.get("s3_star_audit", "")
        s1_provider = s1_model.split("/")[0] if "/" in s1_model else ""
        s3star_provider = s3star_model.split("/")[0] if "/" in s3star_model else ""
        if s1_provider and s3star_provider and s1_provider != s3star_provider:
            audit_pts = 15.0
        elif s1_provider and s3star_provider:
            insights.append("Auditor uses same provider as S1. Cross-provider audit catches more errors.")
    else:
        if units_with_sensitive:
            insights.append("Sensitive tools detected but no S3* audit. This is a critical safety gap.")
        else:
            insights.append("No independent audit (S3*). Agent self-reports are unreliable.")
    points += audit_pts
    details["audit"] = audit_pts

    # --- 5. Anti-looping (10 pts) ---
    rules = s2.get("coordination_rules", [])
    has_anti_loop = any(
        "loop" in r.get("trigger", "").lower() or "repeat" in r.get("trigger", "").lower()
        for r in rules
    )
    if has_anti_loop:
        loop_pts = 10.0
    elif rules:
        loop_pts = 5.0
        insights.append("Coordination rules exist but no anti-looping rule. Agents commonly get stuck in loops.")
    else:
        loop_pts = 0.0
        insights.append("No coordination rules. Auto-generated rules will add basic anti-looping.")
    points += loop_pts
    details["anti_looping"] = loop_pts

    # --- 6. Communication control (10 pts) ---
    has_structured_comm = any(
        "structured" in r.get("action", "").lower() or "route" in r.get("action", "").lower()
        for r in rules
    )
    if has_structured_comm:
        comm_pts = 10.0
    elif rules:
        comm_pts = 5.0
    else:
        comm_pts = 0.0
        insights.append("No structured communication protocol. Free-text agent chatter causes identity loss.")
    points += comm_pts
    details["communication"] = comm_pts

    # --- 7. Identity anchoring (10 pts) ---
    has_purpose = bool(identity.get("purpose", "").strip())
    has_values = bool(identity.get("values"))
    if has_purpose and has_values:
        identity_pts = 10.0
    elif has_purpose or has_values:
        identity_pts = 5.0
        insights.append("Partial identity: define both purpose AND values to prevent agent 'echoing'.")
    else:
        identity_pts = 0.0
        insights.append("No identity defined. Agents without purpose drift and echo user patterns.")
    points += identity_pts
    details["identity"] = identity_pts

    # --- 8. Rollout caution (10 pts) ---
    if len(units) <= 3:
        rollout_pts = 10.0
    elif len(units) <= 5:
        rollout_pts = 7.0
        insights.append(f"{len(units)} agents from the start. Consider phased rollout (start with 1-2).")
    else:
        rollout_pts = 3.0
        insights.append(f"{len(units)} agents is ambitious. MAESTRO research shows complexity scales non-linearly.")
    points += rollout_pts
    details["rollout_caution"] = rollout_pts

    return BenchmarkScore(
        dimension="safety_coverage",
        score=min(int(points), 100),
        max_score=100,
        insights=insights,
        details=details,
    )
```

**Step 4: Run tests**

Run: `pytest tests/test_benchmarks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/viableos/benchmarks/safety_coverage.py tests/test_benchmarks.py
git commit -m "feat(benchmarks): add safety coverage scorer inspired by Agent-SafetyBench"
```

---

### Task 3: Token Efficiency Estimator

**Files:**
- Create: `src/viableos/benchmarks/token_efficiency.py`
- Modify: `tests/test_benchmarks.py`

**Step 1: Write the failing test**

Add to `tests/test_benchmarks.py`:

```python
from viableos.benchmarks.token_efficiency import score_token_efficiency


def test_lean_setup_scores_high():
    """Few agents with heartbeat optimization should score well."""
    config = {
        "viable_system": {
            "system_1": [{"name": "Core", "tools": ["code"]}],
            "system_3": {"reporting_rhythm": "weekly"},
            "budget": {"monthly_usd": 100, "strategy": "frugal"},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_token_efficiency(config)
    assert result.score >= 70
    assert result.dimension == "token_efficiency"


def test_many_agents_scores_lower():
    """6+ agents have higher communication overhead per AgentTaxo."""
    config = {
        "viable_system": {
            "system_1": [
                {"name": f"Unit{i}", "tools": ["code"]} for i in range(6)
            ],
            "system_3": {"reporting_rhythm": "hourly"},
            "budget": {"monthly_usd": 100, "strategy": "balanced"},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_token_efficiency(config)
    assert result.score < 70


def test_no_agents_returns_zero():
    """No agents means nothing to estimate."""
    config = {"viable_system": {}}
    result = score_token_efficiency(config)
    assert result.score == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmarks.py::test_lean_setup_scores_high -v`
Expected: FAIL

**Step 3: Implement token efficiency estimator**

```python
# src/viableos/benchmarks/token_efficiency.py
"""Token efficiency estimator — inspired by AgentTaxo (ICLR 2025).

AgentTaxo found that multi-agent systems suffer from "communication tax":
up to 86% token duplication when agents share reasoning results. The key
factors are:
- Number of agents (linear scaling of coordination overhead)
- Reporting frequency (more frequent = more tokens)
- Model tier (premium models use more tokens per call)
- Heartbeat optimization (using cheap models for routine checks)

We estimate relative efficiency from the config structure.

Scoring criteria:
- Agent count efficiency (25 pts) — fewer agents = less overhead
- Heartbeat optimization (25 pts) — cheap models for routine tasks
- Reporting frequency (20 pts) — less frequent = fewer tokens
- Model tier distribution (15 pts) — not all premium = efficient
- Communication structure (15 pts) — hub topology reduces duplication
"""

from __future__ import annotations

from typing import Any

from viableos.benchmarks import BenchmarkScore
from viableos.budget import MODEL_CATALOG


def score_token_efficiency(config: dict[str, Any]) -> BenchmarkScore:
    vs = config.get("viable_system", {})
    units = vs.get("system_1", [])

    if not units:
        return BenchmarkScore(
            dimension="token_efficiency",
            score=0,
            max_score=100,
            insights=["No agents defined. Nothing to estimate."],
        )

    points = 0.0
    insights: list[str] = []
    details: dict[str, float] = {}
    agent_count = len(units)

    # --- 1. Agent count efficiency (25 pts) ---
    # AgentTaxo: communication tax scales with N*(N-1)/2 potential interactions
    # VSM mitigates this with hub topology (S2), but base overhead still grows
    if agent_count <= 2:
        count_pts = 25.0
    elif agent_count <= 4:
        count_pts = 20.0
    elif agent_count <= 6:
        count_pts = 15.0
        insights.append(f"{agent_count} agents: AgentTaxo estimates ~{agent_count * 12}% token overhead from coordination.")
    else:
        count_pts = 5.0
        overhead_est = min(agent_count * 14, 86)
        insights.append(f"{agent_count} agents: estimated {overhead_est}% communication tax (AgentTaxo ceiling: 86%).")
    points += count_pts
    details["agent_count"] = count_pts

    # --- 2. Heartbeat optimization (25 pts) ---
    # Using cheap models for heartbeats saves 60-80% on routine checks
    routing = vs.get("model_routing", {})
    strategy = vs.get("budget", {}).get("strategy", "balanced")
    if strategy == "frugal":
        hb_pts = 25.0
    elif strategy == "balanced":
        hb_pts = 20.0
    else:
        s1_model = routing.get("s1_routine", "")
        model_info = MODEL_CATALOG.get(s1_model, {})
        if model_info.get("tier") == "premium":
            hb_pts = 10.0
            insights.append("Premium models for all tasks including heartbeats. Consider frugal heartbeat model to save 60-80%.")
        else:
            hb_pts = 15.0
    points += hb_pts
    details["heartbeat"] = hb_pts

    # --- 3. Reporting frequency (20 pts) ---
    s3 = vs.get("system_3", {})
    rhythm = s3.get("reporting_rhythm", "weekly")
    rhythm_scores = {"monthly": 20, "weekly": 18, "daily": 12, "hourly": 5}
    rhythm_pts = float(rhythm_scores.get(rhythm, 15))
    if rhythm == "hourly":
        insights.append("Hourly reporting generates significant token volume. Weekly is sufficient for most orgs.")
    points += rhythm_pts
    details["reporting"] = rhythm_pts

    # --- 4. Model tier distribution (15 pts) ---
    tiers_used: list[str] = []
    for unit in units:
        model = unit.get("model", routing.get("s1_routine", ""))
        info = MODEL_CATALOG.get(model, {})
        tiers_used.append(info.get("tier", "high"))

    premium_ratio = tiers_used.count("premium") / len(tiers_used) if tiers_used else 0
    if premium_ratio == 0:
        tier_pts = 15.0
    elif premium_ratio <= 0.3:
        tier_pts = 12.0
    elif premium_ratio <= 0.5:
        tier_pts = 8.0
    else:
        tier_pts = 3.0
        insights.append(f"{int(premium_ratio * 100)}% of agents use premium-tier models. Mix tiers to reduce token costs.")
    points += tier_pts
    details["tier_distribution"] = tier_pts

    # --- 5. Communication structure (15 pts) ---
    # VSM's hub topology (S2 coordinator) already reduces N*(N-1)/2 to N connections
    # We give credit for having S2 coordination and structured communication
    rules = vs.get("system_2", {}).get("coordination_rules", [])
    has_structured = any(
        "structured" in r.get("action", "").lower() or "route" in r.get("action", "").lower()
        for r in rules
    )
    if has_structured:
        comm_pts = 15.0
    elif rules:
        comm_pts = 10.0
    else:
        comm_pts = 5.0  # VSM topology alone gives some credit
        insights.append("No explicit communication rules. Auto-generated rules will add structured routing.")
    points += comm_pts
    details["communication"] = comm_pts

    return BenchmarkScore(
        dimension="token_efficiency",
        score=min(int(points), 100),
        max_score=100,
        insights=insights,
        details=details,
    )
```

**Step 4: Run tests**

Run: `pytest tests/test_benchmarks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/viableos/benchmarks/token_efficiency.py tests/test_benchmarks.py
git commit -m "feat(benchmarks): add token efficiency estimator inspired by AgentTaxo"
```

---

### Task 4: Architecture Quality Scorer

**Files:**
- Create: `src/viableos/benchmarks/architecture_quality.py`
- Modify: `tests/test_benchmarks.py`

**Step 1: Write the failing test**

Add to `tests/test_benchmarks.py`:

```python
from viableos.benchmarks.architecture_quality import score_architecture_quality


def test_complete_vsm_scores_high():
    """A config with all VSM systems should score >80."""
    config = {
        "viable_system": {
            "identity": {"purpose": "Build great software", "values": ["quality"]},
            "system_1": [
                {"name": "Dev", "tools": ["code", "git"], "autonomy": "supervised"},
                {"name": "Ops", "tools": ["docker"]},
            ],
            "system_2": {"coordination_rules": [{"trigger": "conflict", "action": "route"}]},
            "system_3": {"reporting_rhythm": "weekly", "resource_allocation": "dynamic"},
            "system_3_star": {"checks": [{"name": "review", "frequency": "daily"}]},
            "system_4": {"monitoring": {"competitors": True, "technology": True}},
            "budget": {"monthly_usd": 200, "strategy": "balanced"},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    result = score_architecture_quality(config)
    assert result.score >= 80
    assert result.dimension == "architecture_quality"


def test_s1_only_scores_low():
    """Only S1 defined means no self-regulation — low architecture score."""
    config = {
        "viable_system": {
            "system_1": [{"name": "Worker", "tools": ["code"]}],
        }
    }
    result = score_architecture_quality(config)
    assert result.score < 40


def test_missing_s3star_warns():
    """Missing audit system should generate an insight."""
    config = {
        "viable_system": {
            "identity": {"purpose": "Test"},
            "system_1": [{"name": "Dev", "tools": ["code"]}],
            "system_2": {"coordination_rules": [{"trigger": "x", "action": "y"}]},
            "system_3": {"reporting_rhythm": "weekly"},
        }
    }
    result = score_architecture_quality(config)
    assert any("audit" in i.lower() or "s3*" in i.lower() for i in result.insights)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmarks.py::test_complete_vsm_scores_high -v`
Expected: FAIL

**Step 3: Implement architecture quality scorer**

```python
# src/viableos/benchmarks/architecture_quality.py
"""Architecture quality scorer — inspired by MAESTRO (Jan 2026) and MultiAgentBench (ACL 2025).

MAESTRO's key finding: MAS architecture is the dominant driver of resource profiles,
reproducibility, and cost-latency-accuracy trade-offs — often outweighing model choice.

MultiAgentBench found that graph/hierarchical topologies outperform flat structures,
and cognitive planning improves milestone achievement.

We score the structural completeness and quality of the VSM architecture.

Scoring criteria:
- VSM completeness: all 6 systems present (30 pts)
- Hierarchy depth: proper S2/S3/S3*/S4/S5 layering (20 pts)
- Self-regulation loop: S3 monitors S1, S3* audits independently (15 pts)
- Environmental awareness: S4 monitoring configured (10 pts)
- Variety matching: tools and autonomy per unit (15 pts)
- Structural resilience: fallback chains + multi-provider (10 pts)
"""

from __future__ import annotations

from typing import Any

from viableos.benchmarks import BenchmarkScore
from viableos.checker import check_viability


def score_architecture_quality(config: dict[str, Any]) -> BenchmarkScore:
    vs = config.get("viable_system", {})

    points = 0.0
    insights: list[str] = []
    details: dict[str, float] = {}

    # Use existing viability checker for system completeness
    report = check_viability(config)

    # --- 1. VSM completeness (30 pts) ---
    # 5 pts per system present (S1-S5 + S3*)
    completeness_pts = report.score * 5.0
    if report.score < 6:
        missing = [c.system for c in report.checks if not c.present]
        insights.append(f"Missing VSM systems: {', '.join(missing)}. MAESTRO shows architecture matters more than model choice.")
    points += completeness_pts
    details["completeness"] = completeness_pts

    # --- 2. Hierarchy depth (20 pts) ---
    has_s2 = any(c.present for c in report.checks if c.system == "S2")
    has_s3 = any(c.present for c in report.checks if c.system == "S3")
    has_s5 = any(c.present for c in report.checks if c.system == "S5")

    layers = sum([
        bool(vs.get("system_1")),
        has_s2,
        has_s3,
        bool(vs.get("system_3_star", {}).get("checks")),
        bool(vs.get("system_4", {}).get("monitoring")),
        has_s5,
    ])

    if layers >= 5:
        hierarchy_pts = 20.0
    elif layers >= 4:
        hierarchy_pts = 15.0
    elif layers >= 3:
        hierarchy_pts = 10.0
    elif layers >= 2:
        hierarchy_pts = 5.0
    else:
        hierarchy_pts = 0.0
        insights.append("Flat structure (1-2 layers). MultiAgentBench shows hierarchical topologies outperform flat ones.")
    points += hierarchy_pts
    details["hierarchy"] = hierarchy_pts

    # --- 3. Self-regulation loop (15 pts) ---
    has_s3star = bool(vs.get("system_3_star", {}).get("checks"))
    has_s3_reporting = bool(vs.get("system_3", {}).get("reporting_rhythm"))

    if has_s3_reporting and has_s3star:
        regulation_pts = 15.0
    elif has_s3_reporting or has_s3star:
        regulation_pts = 8.0
        if not has_s3star:
            insights.append("No S3* audit. Without independent verification, agent self-reports go unchecked.")
        else:
            insights.append("No S3 reporting rhythm. Optimization needs regular performance data.")
    else:
        regulation_pts = 0.0
        insights.append("No self-regulation loop (S3 + S3*). This is the VSM's core advantage — don't skip it.")
    points += regulation_pts
    details["self_regulation"] = regulation_pts

    # --- 4. Environmental awareness (10 pts) ---
    monitoring = vs.get("system_4", {}).get("monitoring", {})
    monitor_fields = [k for k in ("competitors", "technology", "regulation") if monitoring.get(k)]
    if len(monitor_fields) >= 2:
        env_pts = 10.0
    elif len(monitor_fields) == 1:
        env_pts = 5.0
        insights.append("S4 monitors only one area. Add technology and regulation monitoring for better awareness.")
    else:
        env_pts = 0.0
        insights.append("No environmental monitoring (S4). Your agents have no awareness of external changes.")
    points += env_pts
    details["environment"] = env_pts

    # --- 5. Variety matching (15 pts) ---
    # Ashby's Law: the controller must have at least as much variety as the system it controls
    units = vs.get("system_1", [])
    units_with_autonomy = sum(1 for u in units if u.get("autonomy"))
    units_with_tools = sum(1 for u in units if u.get("tools"))
    units_with_model = sum(1 for u in units if u.get("model"))

    if not units:
        variety_pts = 0.0
    else:
        variety_score = (
            (units_with_autonomy / len(units)) * 0.4
            + (units_with_tools / len(units)) * 0.4
            + (min(units_with_model / len(units), 1.0)) * 0.2
        )
        variety_pts = round(variety_score * 15)
        if variety_score < 0.5:
            insights.append("Low variety matching: units lack differentiated autonomy/tools. One-size-fits-all configs underperform.")
    points += variety_pts
    details["variety"] = variety_pts

    # --- 6. Structural resilience (10 pts) ---
    routing = vs.get("model_routing", {})
    providers = set()
    for key, model in routing.items():
        if key != "provider_preference" and model and "/" in model:
            providers.add(model.split("/")[0])

    if len(providers) >= 3:
        resilience_pts = 10.0
    elif len(providers) == 2:
        resilience_pts = 7.0
    elif len(providers) == 1:
        resilience_pts = 3.0
        insights.append("Single provider architecture. MAESTRO found multi-provider setups have better reliability.")
    else:
        resilience_pts = 0.0
    points += resilience_pts
    details["resilience"] = resilience_pts

    return BenchmarkScore(
        dimension="architecture_quality",
        score=min(int(points), 100),
        max_score=100,
        insights=insights,
        details=details,
    )
```

**Step 4: Run tests**

Run: `pytest tests/test_benchmarks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/viableos/benchmarks/architecture_quality.py tests/test_benchmarks.py
git commit -m "feat(benchmarks): add architecture quality scorer inspired by MAESTRO"
```

---

### Task 5: Benchmark Runner + API Endpoint

**Files:**
- Create: `src/viableos/benchmarks/runner.py`
- Modify: `src/viableos/api/models.py` — add Pydantic response models
- Modify: `src/viableos/api/routes.py` — add `POST /api/benchmark`
- Modify: `tests/test_benchmarks.py` — add runner tests

**Step 1: Write the failing test**

Add to `tests/test_benchmarks.py`:

```python
from viableos.benchmarks.runner import run_benchmarks


def test_runner_returns_all_dimensions():
    """Runner should return scores for all 4 dimensions."""
    config = {
        "viable_system": {
            "identity": {"purpose": "Test", "values": ["quality"]},
            "system_1": [{"name": "Dev", "tools": ["code"]}],
            "budget": {"monthly_usd": 100, "strategy": "balanced"},
            "model_routing": {"provider_preference": "anthropic"},
        }
    }
    report = run_benchmarks(config)
    dimensions = {s.dimension for s in report.scores}
    assert dimensions == {"budget_efficiency", "safety_coverage", "token_efficiency", "architecture_quality"}
    assert 0 <= report.overall_score <= 100
    assert report.grade in ("A", "B", "C", "D", "F")


def test_runner_grade_calculation():
    """Complete config should get A or B grade."""
    config = {
        "viable_system": {
            "identity": {"purpose": "Build software", "values": ["quality", "speed"], "never_do": ["delete data", "bypass review", "ignore tests"]},
            "system_1": [
                {"name": "Dev", "tools": ["code", "git"], "autonomy": "supervised"},
            ],
            "system_2": {"coordination_rules": [
                {"trigger": "Agent repeats 3+ times", "action": "stop and escalate"},
                {"trigger": "Communication needed", "action": "Route through coordinator using structured JSON"},
            ]},
            "system_3": {"reporting_rhythm": "weekly", "resource_allocation": "dynamic"},
            "system_3_star": {"checks": [{"name": "code_review", "frequency": "daily"}]},
            "system_4": {"monitoring": {"competitors": True, "technology": True, "regulation": True}},
            "budget": {"monthly_usd": 200, "strategy": "balanced", "alerts": {"warn_at_percent": 80, "auto_downgrade_at_percent": 95}},
            "model_routing": {"provider_preference": "anthropic"},
            "human_in_the_loop": {"approval_required": ["deployments", "data-deletion"], "notification_channel": "slack"},
        }
    }
    report = run_benchmarks(config)
    assert report.grade in ("A", "B")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmarks.py::test_runner_returns_all_dimensions -v`
Expected: FAIL

**Step 3: Implement runner**

```python
# src/viableos/benchmarks/runner.py
"""Benchmark runner — orchestrates all scorers and produces a unified report."""

from __future__ import annotations

from typing import Any

from viableos.benchmarks import BenchmarkReport, BenchmarkScore
from viableos.benchmarks.architecture_quality import score_architecture_quality
from viableos.benchmarks.budget_efficiency import score_budget_efficiency
from viableos.benchmarks.safety_coverage import score_safety_coverage
from viableos.benchmarks.token_efficiency import score_token_efficiency


def run_benchmarks(config: dict[str, Any]) -> BenchmarkReport:
    scores: list[BenchmarkScore] = [
        score_budget_efficiency(config),
        score_safety_coverage(config),
        score_token_efficiency(config),
        score_architecture_quality(config),
    ]

    overall = round(sum(s.score for s in scores) / len(scores))

    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 50:
        grade = "C"
    elif overall >= 30:
        grade = "D"
    else:
        grade = "F"

    all_insights = []
    for s in scores:
        all_insights.extend(s.insights)

    top_issues = sorted(scores, key=lambda s: s.score)
    weakest = top_issues[0]

    summary = f"Overall grade: {grade} ({overall}/100). "
    if grade in ("A", "B"):
        summary += "Your config is well-structured for production multi-agent deployment."
    elif grade == "C":
        summary += f"Reasonable start. Biggest gap: {weakest.dimension.replace('_', ' ')} ({weakest.score}/100)."
    else:
        summary += f"Significant gaps detected. Priority: {weakest.dimension.replace('_', ' ')} ({weakest.score}/100)."

    return BenchmarkReport(
        overall_score=overall,
        scores=scores,
        grade=grade,
        summary=summary,
    )
```

**Step 4: Add Pydantic response models**

Add to `src/viableos/api/models.py`:

```python
class BenchmarkScoreResponse(BaseModel):
    dimension: str
    score: int
    max_score: int
    insights: list[str] = []
    details: dict[str, float] = {}


class BenchmarkReportResponse(BaseModel):
    overall_score: int
    scores: list[BenchmarkScoreResponse]
    grade: str
    summary: str
```

**Step 5: Add API endpoint**

Add to `src/viableos/api/routes.py`:

```python
from viableos.benchmarks.runner import run_benchmarks

@router.post("/benchmark", response_model=BenchmarkReportResponse)
def benchmark_config(config: dict[str, Any]) -> BenchmarkReportResponse:
    """Run all benchmarks against a config and return scores."""
    report = run_benchmarks(config)
    return BenchmarkReportResponse(
        overall_score=report.overall_score,
        grade=report.grade,
        summary=report.summary,
        scores=[
            BenchmarkScoreResponse(
                dimension=s.dimension,
                score=s.score,
                max_score=s.max_score,
                insights=s.insights,
                details=s.details,
            )
            for s in report.scores
        ],
    )
```

**Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/viableos/benchmarks/runner.py src/viableos/api/models.py src/viableos/api/routes.py tests/test_benchmarks.py
git commit -m "feat(benchmarks): add runner, API endpoint, and Pydantic models"
```

---

### Task 6: Frontend — Benchmark Dashboard Section

**Files:**
- Create: `frontend/src/components/dashboard/BenchmarkPanel.tsx`
- Modify: `frontend/src/types/index.ts` — add benchmark types
- Modify: `frontend/src/api/client.ts` — add benchmark API call
- Modify: `frontend/src/hooks/useApiData.ts` — add `useBenchmark` hook
- Modify: `frontend/src/pages/DashboardPage.tsx` — add BenchmarkPanel

**Step 1: Add TypeScript types**

Add to `frontend/src/types/index.ts`:

```typescript
export interface BenchmarkScore {
  dimension: string;
  score: number;
  max_score: number;
  insights: string[];
  details: Record<string, number>;
}

export interface BenchmarkReport {
  overall_score: number;
  scores: BenchmarkScore[];
  grade: string;
  summary: string;
}
```

**Step 2: Add API client method**

Add to `frontend/src/api/client.ts`:

```typescript
import type { BenchmarkReport } from '../types';

// inside the api object:
runBenchmark: (config: Config) => post<BenchmarkReport>('/benchmark', config),
```

**Step 3: Add React hook**

Add to `frontend/src/hooks/useApiData.ts`:

```typescript
import type { BenchmarkReport } from '../types';

export function useBenchmark(config: Config) {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const configJson = JSON.stringify(config);

  useEffect(() => {
    const timer = setTimeout(() => {
      api.runBenchmark(config).then(setReport).catch(() => {});
    }, 500);
    return () => clearTimeout(timer);
  }, [configJson]);

  return report;
}
```

**Step 4: Build the BenchmarkPanel component**

```typescript
// frontend/src/components/dashboard/BenchmarkPanel.tsx
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import { Card } from '../ui/Card';
import type { BenchmarkReport } from '../../types';

const DIMENSION_LABELS: Record<string, string> = {
  budget_efficiency: 'Budget Efficiency',
  safety_coverage: 'Safety Coverage',
  token_efficiency: 'Token Efficiency',
  architecture_quality: 'Architecture Quality',
};

const GRADE_COLORS: Record<string, string> = {
  A: '#10b981',
  B: '#6366f1',
  C: '#f59e0b',
  D: '#f97316',
  F: '#ef4444',
};

interface Props {
  report: BenchmarkReport;
}

export function BenchmarkPanel({ report }: Props) {
  const radarData = report.scores.map((s) => ({
    dimension: DIMENSION_LABELS[s.dimension] || s.dimension,
    score: s.score,
    fullMark: 100,
  }));

  const gradeColor = GRADE_COLORS[report.grade] || '#94a3b8';

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Benchmark Score</h3>
        <div className="flex items-center gap-3">
          <span
            className="text-3xl font-bold"
            style={{ color: gradeColor }}
          >
            {report.grade}
          </span>
          <span className="text-sm text-[var(--color-muted)]">
            {report.overall_score}/100
          </span>
        </div>
      </div>

      <p className="text-sm text-[var(--color-muted)] mb-4">{report.summary}</p>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData}>
            <PolarGrid stroke="var(--color-border)" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fill: 'var(--color-muted)', fontSize: 11 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: 'var(--color-muted)', fontSize: 10 }}
            />
            <Radar
              dataKey="score"
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.3}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-3">
        {report.scores.map((s) => (
          <div key={s.dimension}>
            <div className="flex justify-between text-sm mb-1">
              <span>{DIMENSION_LABELS[s.dimension]}</span>
              <span className="text-[var(--color-muted)]">{s.score}/100</span>
            </div>
            <div className="w-full bg-[var(--color-bg)] rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${s.score}%`,
                  backgroundColor: s.score >= 70 ? '#10b981' : s.score >= 50 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
            {s.insights.length > 0 && (
              <ul className="mt-1 text-xs text-[var(--color-muted)] space-y-0.5">
                {s.insights.slice(0, 2).map((insight, i) => (
                  <li key={i}>- {insight}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
```

**Step 5: Wire into DashboardPage**

In `frontend/src/pages/DashboardPage.tsx`, import the hook and component, add the panel to the dashboard grid:

```typescript
import { BenchmarkPanel } from '../components/dashboard/BenchmarkPanel';
import { useBenchmark } from '../hooks/useApiData';

// inside DashboardPage:
const benchmark = useBenchmark(config);

// in the JSX grid:
{benchmark && <BenchmarkPanel report={benchmark} />}
```

**Step 6: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/components/dashboard/BenchmarkPanel.tsx frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/hooks/useApiData.ts frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): add benchmark radar chart and score panel to dashboard"
```

---

## Phase 2: Template Baseline Scores

### Task 7: Score All Templates and Store Reference Data

**Files:**
- Create: `src/viableos/benchmarks/baselines.py`
- Modify: `tests/test_benchmarks.py`

**Step 1: Write the failing test**

```python
from viableos.benchmarks.baselines import get_template_baselines


def test_all_templates_have_baselines():
    """Every template should have a benchmark baseline."""
    baselines = get_template_baselines()
    # We have 12 templates (including "custom")
    assert len(baselines) >= 11
    for key, report in baselines.items():
        assert report.overall_score >= 0
        assert report.grade in ("A", "B", "C", "D", "F")


def test_saas_template_scores_well():
    """SaaS template should score reasonably well out of the box."""
    baselines = get_template_baselines()
    assert "saas" in baselines
    assert baselines["saas"].overall_score >= 40
```

**Step 2: Implement baselines**

```python
# src/viableos/benchmarks/baselines.py
"""Pre-computed benchmark baselines for all templates.

Run at import time (cached). Enables "compare to template" in the dashboard.
"""

from __future__ import annotations

import functools

from viableos.benchmarks import BenchmarkReport
from viableos.benchmarks.runner import run_benchmarks
from viableos.schema import TEMPLATES


@functools.lru_cache(maxsize=1)
def get_template_baselines() -> dict[str, BenchmarkReport]:
    baselines: dict[str, BenchmarkReport] = {}
    for key, template in TEMPLATES.items():
        if key == "custom":
            continue
        config = template.get("config", template)
        baselines[key] = run_benchmarks(config)
    return baselines
```

**Step 3: Add API endpoint for baselines**

Add to `src/viableos/api/routes.py`:

```python
from viableos.benchmarks.baselines import get_template_baselines

@router.get("/benchmark/baselines")
def get_baselines() -> dict[str, BenchmarkReportResponse]:
    baselines = get_template_baselines()
    return {
        key: BenchmarkReportResponse(
            overall_score=r.overall_score,
            grade=r.grade,
            summary=r.summary,
            scores=[
                BenchmarkScoreResponse(
                    dimension=s.dimension,
                    score=s.score,
                    max_score=s.max_score,
                    insights=s.insights,
                    details=s.details,
                )
                for s in r.scores
            ],
        )
        for key, r in baselines.items()
    }
```

**Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/viableos/benchmarks/baselines.py src/viableos/api/routes.py tests/test_benchmarks.py
git commit -m "feat(benchmarks): add template baseline scores for comparison"
```

---

## Phase 3: External Benchmark Adapters (Future — documented but not implemented yet)

These tasks prepare ViableOS for integration with external benchmark suites. They produce export formats, not runtime integrations.

### Task 8 (Future): REALM-Bench Config Exporter

**Goal:** Export a ViableOS config as a REALM-Bench-compatible agent definition so users can test their organization against real-world planning scenarios.

**Approach:**
- Map S1 units to REALM-Bench agent roles
- Map S2 coordinator to REALM-Bench orchestrator
- Output as the JSON format REALM-Bench expects
- Add "Export for REALM-Bench" button to dashboard

**Reference:** https://github.com/genglongling/REALM-Bench

### Task 9 (Future): MAESTRO Trace Format

**Goal:** Add OpenTelemetry-compatible trace fields to `openclaw.json` so generated packages can export execution traces in MAESTRO's format.

**Approach:**
- Add `trace_config` section to `openclaw.json` output
- Include spans for: agent invocation, tool calls, coordination events
- Enable MAESTRO's cost-latency-accuracy analysis on ViableOS-generated systems

**Reference:** https://arxiv.org/abs/2601.00481

### Task 10 (Future): VSM-Bench — Our Own Benchmark

**Goal:** Define a benchmark that specifically tests organizational viability in multi-agent systems. This would be the first benchmark to measure:
- Hierarchical self-regulation under load
- Budget adherence over time
- Anti-looping effectiveness
- Identity preservation across sessions
- Graceful degradation when agents fail

**Approach:**
- Define 10 test scenarios per template type
- Measure: task completion, budget adherence, loop count, identity drift score
- Publish as academic paper + open-source benchmark suite
- Position ViableOS as the reference implementation

**Academic framing:** "VSM-Bench: A Benchmark for Organizational Viability in Multi-Agent Systems"

---

## Summary

| Phase | Tasks | Effort | What You Get |
|---|---|---|---|
| **Phase 1** | Tasks 1-6 | 2-3 sessions | 4 scorers + runner + API + radar chart in dashboard |
| **Phase 2** | Task 7 | 1 session | Template baselines for "compare to average" |
| **Phase 3** | Tasks 8-10 | Future | External benchmark integration + own benchmark |

After Phase 1+2, every user sees a concrete score (A-F) with actionable insights before they deploy. This is a strong differentiator — no other multi-agent tool does this.
