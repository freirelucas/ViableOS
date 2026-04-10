# Schema Extension: VSM Behavioral Specifications

## Problem

The current schema (`ViableSystem`) describes **topology** (which units, which checks, which sources) — but not **behavior** (when does who escalate, how does a control loop close, what changes in a crisis).

The generators (`generator.py`, `soul_templates.py`) compensate for this with hardcoded text in SOUL.md and SKILL.md. Result: All organizations get the same behavior, regardless of their context.

## Design Principle

**Config describes WHAT, generators decide HOW.**

But: The WHAT needs to become richer. The assessment dialog knows the organization well enough to derive domain-specific behavior. Example: A home care service needs different escalation thresholds than a software startup.

## Strategy: Three Layers

```
Layer 1: Config Schema (TypeScript + Python)
    ↓ What the organization needs
Layer 2: Assessment Transformer
    ↓ Derives behavior from context
Layer 3: Generators (SOUL.md, SKILL.md, HEARTBEAT.md)
    ↓ Translates into agent-readable Markdown instructions
```

All new fields are **optional** with sensible defaults. Existing configs remain 100% compatible.

---

## New Schema Fields

### 1. System-wide: `operational_modes`

Three modes that affect ALL agents. Each organization defines its own thresholds.

```typescript
// In ViableSystem (top-level)
operational_modes?: {
  normal: {
    description: string;           // "Day-to-day operations, full unit autonomy"
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "weekly"
    escalation_threshold: string;  // "2 hours without response"
  };
  elevated: {
    description: string;           // "Heightened vigilance under external pressure"
    triggers: string[];            // ["Customer complaint rate > 5%", "Staff absence > 20%"]
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "daily"
    escalation_threshold: string;  // "30 minutes without response"
  };
  crisis: {
    description: string;           // "Acute crisis, centralized control"
    triggers: string[];            // ["Data loss", "Regulatory order", "Revenue drop > 30%"]
    s1_autonomy: 'full' | 'standard' | 'restricted';
    reporting_frequency: string;   // "hourly"
    escalation_threshold: string;  // "immediately"
    human_required: boolean;       // true — a human must activate crisis mode
  };
};
```

**Why:** Currently all agents always react the same way. A home care service with staff shortages needs immediate switch to crisis mode — a software team only needs that upon data loss.

**Generator Impact:** SKILL.md gets an "Operational Modes" section. HEARTBEAT.md adjusts frequencies to the active mode.

### 2. System-wide: `escalation_chains`

Who escalates to whom, when, and with what urgency.

```typescript
// In ViableSystem (top-level)
escalation_chains?: {
  operational: {
    // S1 → S2 → S3 → Human
    path: string[];               // ["s2-coordination", "s3-optimization", "human"]
    timeout_per_step: string;     // "2h" — if no response, next level
  };
  quality: {
    // S3* → S3 → Human
    path: string[];
    timeout_per_step: string;
  };
  strategic: {
    // S4 → S5 → Human
    path: string[];
    timeout_per_step: string;
  };
  algedonic: {
    // Anyone → S5 → Human (bypasses all levels)
    description: string;          // "Algedonic Signal for fundamental problems"
    triggers: string[];           // ["Values violation", "Illegal instruction", "Endangerment of persons"]
    path: string[];               // ["s5-policy", "human"]
  };
};
```

**Why:** Currently "escalate to Coordinator" is in SKILL.md, but what's missing is: timeout, urgency, what happens if S2 doesn't respond, and the algedonic bypass.

**Generator Impact:** Every agent gets an "Escalation Protocol" section in SKILL.md with its specific chain.

### 3. System-wide: `vollzug_protocol`

The four-step control loop according to Pfiffner.

```typescript
// In ViableSystem (top-level)
vollzug_protocol?: {
  enabled: boolean;               // true
  steps: ['order', 'acknowledgment', 'execution', 'confirmation'];
  timeout_quittung: string;       // "30min" — how long to wait for order acknowledgment
  timeout_vollzug: string;        // "24h" — how long to wait for completion report
  on_timeout: 'escalate' | 'remind' | 'alert_human';
};
```

**Why:** Pfiffner: "Only when we have heard the response do we know what we said." Currently there is no obligation to acknowledge orders or report results. Tasks disappear into the void.

**Generator Impact:** Every S1 agent gets the obligation in SKILL.md: "You respond to every order with an acknowledgment. After completion you send a completion report." S3 agent gets: "Escalate open orders without acknowledgment after {timeout}."

### 4. S1 Unit Extension: `autonomy_levels`

Structured instead of free text.

```typescript
// In S1Unit
autonomy_levels?: {
  can_do_alone: string[];         // ["Answer customer inquiries", "Create routine reports"]
  needs_coordination: string[];   // ["Price changes", "Schedule changes with other units"]
  needs_approval: string[];       // ["Contract changes", "Budget > €500", "New employee access"]
};
```

**Why:** `autonomy: string` is too unstructured. The generator cannot build clear decision trees from it. Structured → the agent knows exactly: "This I can decide alone, this I need to coordinate, this needs the boss."

**Generator Impact:** SOUL.md § "What you can do alone" becomes three clear lists. SKILL.md gets a decision matrix.

### 5. S2 Extension: `conflict_detection` + `transduction`

```typescript
// In system_2
system_2?: {
  coordination_rules?: CoordinationRule[];
  conflict_detection?: {
    resource_overlaps: boolean;      // true — automatically detect resource collisions
    deadline_conflicts: boolean;     // true — detect scheduling conflicts
    output_contradictions: boolean;  // true — detect contradictory outputs
    custom_triggers?: string[];      // ["When both teams want to contact the same customer"]
  };
  transduction_mappings?: Array<{
    from_unit: string;              // "Billing"
    to_unit: string;                // "Planning"
    translation: string;            // "What Billing calls 'service record' is what Planning calls 'weekly plan output'"
  }>;
  escalation_to_s3_after?: string;  // "2 failed mediation attempts"
};
```

**Why:** S2 is currently a passive router. With Conflict Detection it becomes an active early warning system. Transduction solves the problem that S1 units speak different domain languages.

**Generator Impact:** SOUL.md § "Behavior" becomes concrete: "On every action from Unit A, check whether it conflicts with Unit B." SKILL.md gets a glossary of domain language translations.

### 6. S3 Extension: `triple_index` + `deviation_logic` + `intervention_authority`

```typescript
// In system_3
system_3?: {
  reporting_rhythm?: string;
  resource_allocation?: string;
  kpi_list?: string[];
  triple_index?: {
    actuality: string;              // "What is the unit actually delivering right now?"
    capability: string;             // "What could it deliver at optimal utilization?"
    potentiality: string;           // "What could it deliver if we invest?"
    measurement: string;            // "Hours, revenue, output quantity" — domain-specific
  };
  deviation_logic?: {
    report_only_deviations: boolean; // true — do not report "everything is normal"
    threshold_percent?: number;      // 15 — deviation > 15% = report
    trend_detection: boolean;        // true — 3x consecutive slight decline = report
  };
  intervention_authority?: {
    can_restrict_s1_autonomy: boolean;   // true
    requires_documentation: boolean;     // true — every intervention must be justified
    requires_human_approval: boolean;    // false — in crisis S3 may act immediately
    max_duration: string;                // "48h" — after that a human must confirm
    allowed_actions: string[];           // ["Freeze budget", "Reroute task", "Downgrade model"]
  };
};
```

**Why:**
- **Triple Index** (Beer): Actuality/Capability/Potentiality is THE management instrument. Currently it is completely missing.
- **Deviation Logic**: "Everything is normal" is not a report. Reporting only deviations saves token budget and attention.
- **Intervention Authority**: Channel 3 (Corporate Intervention) is the only channel on which S3 may restrict S1's autonomy. Must be explicitly defined and documented.

**Generator Impact:** SOUL.md gets Triple Index as management framework. SKILL.md gets Deviation Logic and Intervention Protocol.

### 7. S3* Extension: `provider_constraint` + `audit_methodology`

```typescript
// In system_3_star
system_3_star?: {
  checks?: Array<{
    name: string;
    target: string;
    method: string;
    // NEW:
    data_source?: 'raw_data' | 'agent_output' | 'both';  // What is being checked
    comparison?: string;            // "Compare reported hours with actual timestamps"
  }>;
  on_failure?: string;
  provider_constraint?: {
    must_differ_from: 's1' | 'all';  // Provider must differ from S1 (or all)
    reason: string;                   // "Prevents correlated hallucinations"
  };
  reporting_target?: 's3' | 's3_and_human';  // To whom — NEVER directly to S1
  independence_rules?: string[];     // ["No write access to S1 workspaces", "No access to S1 prompts"]
};
```

**Why:** Provider constraint is listed in the Checker as a warning, but it needs to be in the schema as a hard architectural decision. Audit methodology requires a definition per check of what is compared against what.

**Generator Impact:** SOUL.md § "Independence" is filled with concrete rules. SKILL.md § "Verification Methodology" gets the comparison logic per check.

### 8. S4 Extension: `premises_register` + `strategy_bridge`

```typescript
// In system_4
system_4?: {
  monitoring?: { ... };  // as before
  premises_register?: Array<{
    premise: string;                // "Skilled workers are available on the market"
    check_frequency: string;        // "monthly"
    invalidation_signal: string;    // "Job applications declining for 3 consecutive months"
    consequence_if_invalid: string; // "Strategy 'growth through hiring' no longer works"
  }>;
  strategy_bridge?: {
    injection_point: string;        // "Before the operational quarterly planning"
    format: string;                 // "Strategic briefing with max. 3 action recommendations"
    recipient: string;              // "s3-optimization"
  };
  weak_signals?: {
    enabled: boolean;
    unconventional_sources?: string[];  // ["Cross-industry innovations", "Customer complaint patterns"]
    detection_method: string;           // "Pattern recognition over 3-month window"
  };
};
```

**Why:**
- **Premises Register**: Pfiffner example: A corporation plans its budget (September) before strategy (November). Result: Strategy never becomes operational. A register forces the check: "Are our assumptions still valid?"
- **Strategy Bridge**: S4 insights must flow into operational planning in a timely manner — not "sometime via email".

**Generator Impact:** SOUL.md gets a "Premises to watch" list. HEARTBEAT.md gets a premises check at the appropriate rhythm. SKILL.md gets the format for the Strategy Bridge.

### 9. S5 Extension: `balance_monitoring` + `algedonic_channel` + `basta_constraint`

```typescript
// In Identity (extended)
identity?: {
  purpose: string;
  values?: string[];
  never_do?: string[];
  decisions_requiring_human?: string[];
  // NEW:
  balance_monitoring?: {
    s3_vs_s4_target: string;        // "60/40" — 60% operational optimization, 40% future
    measurement: string;            // "Share of agent tokens flowing into S3 vs S4"
    alert_if_exceeds: string;       // "80/20" — alert when optimization crowds out S4
  };
  algedonic_channel?: {
    enabled: boolean;
    who_can_send: 'all_agents' | 's1_only' | 'all_agents_and_human';
    triggers: string[];             // ["Values violation detected", "Illegal instruction received", "Systemic malfunction"]
    bypasses_hierarchy: boolean;    // true — goes directly to S5, bypasses S2/S3
  };
  basta_constraint?: {
    description: string;            // "Normative Reserve — decisions under undecidability"
    examples: string[];             // ["Strategy change", "Merger/acquisition", "Ethics dilemma"]
    agent_role: 'prepare_only';     // Agent prepares, does NOT decide
  };
};
```

**Why:**
- **Balance Monitoring**: The most common VSM pathology is that S3 (day-to-day operations) completely crowds out S4 (future). Must be measured.
- **Algedonic Channel**: The only channel that pierces through all levels. Currently completely missing.
- **Normative Reserve**: Make explicit what the agent CANNOT do. Prevents the agent from presuming to make normative decisions.

**Generator Impact:** SOUL.md § "S3/S4 Balance" and "Algedonic Signal" as new sections. HEARTBEAT.md: Balance measurement on a weekly rhythm.

---

## Assessment Transformer: What Is Automatically Derived

The assessment dialog knows the organization. From this, the transformer can derive much of the behavioral specification without requiring the user to fill in each field individually:

| Schema Field | Derived From |
|-------------|---------------|
| `operational_modes.elevated.triggers` | `external_forces` (risks) + `team.size` (small teams = faster into crisis) |
| `operational_modes.crisis.triggers` | `success_criteria` with priority 1 (inversion: if this fails = crisis) |
| `escalation_chains.operational.timeout` | `team.size` (1-2 people = short timeouts, 10+ = longer) |
| `escalation_chains.algedonic.triggers` | `identity.never_do` (violation = Algedonic Signal) |
| `vollzug_protocol.timeout_quittung` | `operational_modes.normal.reporting_frequency` (proportional) |
| `s1.autonomy_levels.needs_approval` | `human_in_the_loop.approval_required` (break down per unit) |
| `s2.conflict_detection.custom_triggers` | `dependencies` (every dependency = potential conflict) |
| `s2.transduction_mappings` | `dependencies` + `s1.domain_context` (domain language differences) |
| `s3.triple_index.measurement` | `success_criteria` + `s3.kpi_list` (what is measured) |
| `s3.deviation_logic.threshold` | `budget.strategy` ("frugal" = 10%, "balanced" = 15%, "generous" = 20%) |
| `s3.intervention_authority.allowed_actions` | `human_in_the_loop.approval_required` (inverse: what CANNOT be done alone) |
| `s3_star.provider_constraint` | Always `must_differ_from: 's1'` (no assessment needed) |
| `s4.premises_register` | `external_forces` → each force becomes a premise |
| `s4.strategy_bridge.injection_point` | `s3.reporting_rhythm` (always BEFORE the reporting cycle) |
| `identity.balance_monitoring.s3_vs_s4_target` | `budget.strategy` ("frugal" = 70/30, "balanced" = 60/40, "generous" = 50/50) |
| `identity.algedonic_channel.triggers` | `identity.never_do` + "Systemic malfunction" |

**Principle:** The user only needs to complete the assessment interview. The transformer derives the Behavioral Specs automatically. In the wizard, the user can override the defaults.

---

## Impact on the Generators

### SOUL.md — New Sections

For **every agent** the following are added:

```markdown
## Operational Modes
- **Normal**: {description}. You work autonomously.
- **Elevated**: Triggered by {triggers}. Reporting frequency increases to {freq}.
- **Crisis**: Triggered by {triggers}. You wait for instructions from S3.
  Autonomy: {level}. Every action requires a completion report.

## Escalation Protocol
Your escalation chain: {path}
Timeout per step: {timeout}
On Algedonic Signal (values violation, endangerment): Directly to S5 → Human.
```

For **S1** the following is added:

```markdown
## Autonomy Matrix
### Decide Alone
{can_do_alone}
### Coordination Required (via S2)
{needs_coordination}
### Approval Required (Human)
{needs_approval}

## Execution Obligation
You respond to every order with an acknowledgment within {timeout_quittung}.
After completion you send a completion report.
Without a completion report the order is considered NOT completed.
```

For **S3** the following is added:

```markdown
## Triple Index
For each unit you measure:
- **Actuality**: {actuality} — what is it delivering now?
- **Capability**: {capability} — what could it deliver at full utilization?
- **Potentiality**: {potentiality} — what would be possible with investment?
Unit of measurement: {measurement}

## Deviation Logic
Report ONLY deviations > {threshold}%. "Everything is normal" is NOT a report.
On 3x consecutive slight decline: report the trend, even if individual values are below threshold.

## Intervention Authority (Channel 3)
You MAY in justified cases:
{allowed_actions}
BUT: Every intervention must be documented and justified.
Maximum duration without human confirmation: {max_duration}.
```

For **S4** the following is added:

```markdown
## Premises Register
You must continuously monitor the following assumptions:
{for each premise:}
- **{premise}** — Check: {check_frequency}
  Invalidation signal: {invalidation_signal}
  If invalid: {consequence_if_invalid}

## Strategy Bridge
Your insights feed in at: {injection_point}
Format: {format}
Recipient: {recipient}
```

For **S5** the following is added:

```markdown
## S3/S4 Balance
Target ratio: {s3_vs_s4_target}
Measurement: {measurement}
Alert when: {alert_if_exceeds}

## Algedonic Channel
Any agent can send a signal directly to you upon {triggers}.
This signal bypasses the hierarchy. You forward it IMMEDIATELY to the human.

## Normative Reserve
You NEVER make the following decisions yourself: {examples}
Your role: Prepare the decision brief (context, options, recommendation, urgency).
The human decides. You execute.
```

### HEARTBEAT.md — Mode-Dependent Frequencies

```markdown
## Frequencies by Operational Mode

| Check | Normal | Elevated | Crisis |
|-------|--------|----------|--------|
| Status Report | weekly | daily | hourly |
| Execution Check | daily | every 4h | hourly |
| Premises Check (S4) | monthly | weekly | daily |
| Balance Check (S5) | weekly | daily | daily |
| Audit Sample (S3*) | every 4h | every 2h | every 1h |
```

### SKILL.md — New Sections

For **S2** the following is added:

```markdown
## Conflict Detection
Automatically check:
{if resource_overlaps} - Resource overlap between units
{if deadline_conflicts} - Detect scheduling conflicts
{if output_contradictions} - Detect contradictory outputs
{custom_triggers}

## Domain Language Translation (Transduction)
{for each mapping:}
- {from_unit} says "{x}" → {to_unit} understands this as "{y}"
```

---

## Wizard Extension

The new fields do NOT require new wizard steps. They are:

1. **Automatically derived** by the Assessment Transformer (80%)
2. **Displayed on the ReviewStep (Step 6)** as a "Behavioral Specs" section with expandable details
3. **Editable** via an optional "Advanced" area in the wizard

The ReviewStep gets a new section:

```
📋 Behavioral Specifications (auto-generated)
├── Operational Modes: Normal / Elevated (2 triggers) / Crisis (3 triggers)
├── Escalation: S1→S2→S3→Human (2h timeout)
├── Execution Protocol: active (30min acknowledgment, 24h completion)
├── S3 Intervention: permitted (Freeze budget, Reroute task)
├── S3* Provider: must differ from S1
├── S4 Premises: 4 monitored assumptions
├── S3/S4 Balance: Target 60/40, Alert at 80/20
└── Algedonic Channel: active (3 triggers)
```

---

## Change Overview

### Files to be modified

| File | Change | Effort |
|-------|----------|---------|
| `frontend/src/types/index.ts` | New interfaces + extended existing ones | medium |
| `src/viableos/assessment_transformer.py` | New builder functions for each field | large |
| `src/viableos/soul_templates.py` | New sections in each `generate_*_soul()` | large |
| `src/viableos/generator.py` | Pass new fields through to Soul/Skill/Heartbeat generators | medium |
| `src/viableos/checker.py` | New checks (modes defined? execution protocol active? etc.) | small |
| `src/viableos/coordination.py` | Integrate Conflict Detection + Transduction | small |
| `frontend/src/components/wizard/ReviewStep.tsx` | "Behavioral Specs" section | small |

### Files that will NOT be modified

- `chat/` — Chat flow stays the same
- `system_prompt.py` — Assessment interview stays the same (the new fields are derived, not asked)
- `budget.py` — Budget logic stays the same
- `langgraph_generator.py` — Separate, can follow later

---

## Implementation Order

### Phase 1: Schema + Transformer (Backend-only, no UI needed)
1. Extend TypeScript types
2. Extend Python dataclasses / dicts
3. `assessment_transformer.py` — Derivation logic for each new field
4. Tests: Transform existing assessments → new fields are populated

### Phase 2: Generators (Output improves)
5. `soul_templates.py` — New sections per system
6. `generator.py` — Pass new fields through
7. Tests: Verify generated SOUL.md / SKILL.md / HEARTBEAT.md

### Phase 3: Checker + UI (Validation + Visibility)
8. `checker.py` — New viability checks
9. `ReviewStep.tsx` — Display Behavioral Specs
10. Optional: Advanced editing in the wizard

---

## Example: Complete Schema After Extension

```typescript
export interface ViableSystem {
  name: string;
  runtime?: string;
  identity: Identity;                    // extended with balance_monitoring, algedonic, basta
  system_1: S1Unit[];                    // extended with autonomy_levels
  system_2?: System2;                    // extended with conflict_detection, transduction
  system_3?: System3;                    // extended with triple_index, deviation_logic, intervention
  system_3_star?: System3Star;           // extended with provider_constraint, audit_methodology
  system_4?: System4;                    // extended with premises_register, strategy_bridge
  budget?: Budget;
  model_routing?: ModelRouting;
  human_in_the_loop?: HumanInTheLoop;
  persistence?: Persistence;
  // NEW:
  operational_modes?: OperationalModes;
  escalation_chains?: EscalationChains;
  vollzug_protocol?: VollzugProtocol;
}
```
