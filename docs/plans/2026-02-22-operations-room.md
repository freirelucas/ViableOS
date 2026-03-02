# ViableOS Operations Room

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a live Operations Room to ViableOS — an integrated steering cockpit where strategy becomes work packages and flows into operational units. Inspired by Stafford Beer's Operations Room (Chile, 1971), translated into a digital product feature.

**Depends on:** Runtime Engine (Tasks 1-8 from `2026-02-20-runtime-engine.md`)

**Tech Stack:** Existing — Python/FastAPI backend, React/TypeScript/Tailwind frontend, SQLite (aiosqlite), WebSocket

---

## What the Operations Room Is

The Operations Room is the single place where a ViableOS user sees everything and steers everything:

1. **What's coming in** — signals from the environment, customers, audit, and own ideas
2. **What's been decided** — the prioritized backlog of work packages
3. **What's happening now** — live status of every agent
4. **What needs me** — pending decisions that require human judgment
5. **How loaded is the system** — capacity per operational unit

It is a VIEW on top of the existing runtime components (state.py, router.py, orchestrator.py), plus a new Signal/Backlog persistence layer.

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATIONS ROOM                           │
│                                                             │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │ SIGNAL INBOX │  │          S3 BACKLOG                 │  │
│  │              │  │                                     │  │
│  │ [S4] SGB VIII│  │  TRIAGE    QUEUED      ACTIVE       │  │
│  │ [CU] Feature │  │  ┌────┐   ┌────┐   ┌──────────┐   │  │
│  │ [AU] Bug     │  │  │ #5 │   │ #2 │   │ #1 → Dev │   │  │
│  │ [GR] Idea    │  │  │ #6 │   │ #3 │   │ #4 → Ops │   │  │
│  │ [S1] Refactor│  │  └────┘   └────┘   └──────────┘   │  │
│  └──────────────┘  └────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────┐  ┌────────────────────────────┐  │
│  │ SYSTEM STATUS        │  │ PENDING DECISIONS          │  │
│  │                      │  │                            │  │
│  │ Dev    ● working #1  │  │ ⚠ Deploy v2.3? [Y] [N]   │  │
│  │ Ops    ● idle        │  │ ⚠ DiGA starten? [Y] [N]  │  │
│  │ GTM    ● working #7  │  │ ℹ PR #48 review          │  │
│  │ S2     ● idle        │  │                            │  │
│  │ S3*    ● auditing    │  │                            │  │
│  │                      │  │                            │  │
│  │ Budget: $87/$150     │  │                            │  │
│  └──────────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Signal

A signal is anything that enters the system and might require action.

```python
@dataclass
class Signal:
    id: str                     # UUID
    source: str                 # "s4" | "customer" | "audit" | "founder" | "s1"
    source_agent: str | None    # agent_id if from an agent, None if from human
    title: str                  # short description
    description: str            # full context
    affected_areas: list[str]   # list of agent_ids or area names
    urgency: str                # "low" | "medium" | "high" | "critical"
    status: str                 # "new" | "triaged" | "converted" | "dismissed"
    created_at: str             # ISO timestamp
    triaged_at: str | None      # when S3 or human triaged it
    work_package_id: str | None # if converted to a work package
    metadata: dict[str, Any]    # source-specific extra data
```

### WorkPackage

A work package is a triaged signal turned into actionable work.

```python
@dataclass
class WorkPackage:
    id: str                     # UUID
    title: str
    description: str
    priority: int               # 1 (highest) to 5 (lowest)
    status: str                 # "queued" | "active" | "blocked" | "done" | "cancelled"
    assigned_to: str | None     # agent_id of the S1 unit
    source_signal_id: str       # reference to originating signal
    estimated_effort: str | None # "small" | "medium" | "large"
    created_at: str             # ISO timestamp
    started_at: str | None
    completed_at: str | None
    result_summary: str | None  # what was done, filled on completion
    verified_by: str | None     # agent_id of S3* if audited
```

### Decision

A pending decision that requires human input.

```python
@dataclass
class Decision:
    id: str                     # UUID
    decision_type: str          # "approval" | "review" | "strategic" | "escalation"
    title: str
    context: str                # why this needs a decision
    options: list[str]          # e.g. ["approve", "reject", "defer"]
    urgency: str                # "low" | "medium" | "high" | "critical"
    source_agent: str           # who raised it
    related_work_package: str | None
    status: str                 # "pending" | "decided" | "expired"
    created_at: str
    decided_at: str | None
    decision: str | None        # chosen option
    rationale: str | None       # human's reason
```

---

## SQLite Schema Extension

Added to `StateStore.init()` alongside existing tables:

```sql
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_agent TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    affected_areas TEXT NOT NULL,    -- JSON array
    urgency TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triaged_at TIMESTAMP,
    work_package_id TEXT,
    metadata TEXT DEFAULT '{}'       -- JSON object
);

CREATE TABLE IF NOT EXISTS work_packages (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'queued',
    assigned_to TEXT,
    source_signal_id TEXT REFERENCES signals(id),
    estimated_effort TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_summary TEXT,
    verified_by TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    title TEXT NOT NULL,
    context TEXT NOT NULL,
    options TEXT NOT NULL,            -- JSON array
    urgency TEXT NOT NULL DEFAULT 'medium',
    source_agent TEXT NOT NULL,
    related_work_package TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMP,
    decision TEXT,
    rationale TEXT
);
```

---

## StateStore Methods (additions to state.py)

```python
# --- Signals ---

async def create_signal(self, signal: dict[str, Any]) -> str:
    """Insert a new signal. Returns the signal ID."""

async def get_signals(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List signals, optionally filtered by status."""

async def update_signal(self, signal_id: str, updates: dict[str, Any]) -> None:
    """Update signal fields (status, triaged_at, work_package_id)."""

# --- Work Packages ---

async def create_work_package(self, wp: dict[str, Any]) -> str:
    """Insert a new work package. Returns the WP ID."""

async def get_backlog(self, status: str | None = None) -> list[dict[str, Any]]:
    """List work packages ordered by priority, optionally filtered by status."""

async def update_work_package(self, wp_id: str, updates: dict[str, Any]) -> None:
    """Update work package fields (status, assigned_to, started_at, etc.)."""

async def get_active_by_agent(self) -> dict[str, list[dict[str, Any]]]:
    """Return active work packages grouped by assigned agent."""

async def get_capacity(self) -> dict[str, dict[str, int]]:
    """Return per-agent counts: {agent_id: {queued: N, active: N, done: N}}."""

# --- Decisions ---

async def create_decision(self, decision: dict[str, Any]) -> str:
    """Insert a pending decision. Returns the decision ID."""

async def get_pending_decisions(self) -> list[dict[str, Any]]:
    """List all pending decisions, sorted by urgency then created_at."""

async def resolve_decision(self, decision_id: str, choice: str, rationale: str | None = None) -> None:
    """Record the human's decision."""
```

---

## API Endpoints

All under `/api/ops/` prefix. Added to `routes.py`.

### Signals

```
POST   /api/ops/signals              Create a new signal
GET    /api/ops/signals              List signals (query: ?status=new&limit=50)
PATCH  /api/ops/signals/{id}         Update signal (triage, dismiss, convert)
POST   /api/ops/signals/{id}/convert Convert signal to work package (creates WP, links signal)
```

### Work Packages

```
POST   /api/ops/workpackages             Create work package directly (without signal)
GET    /api/ops/backlog                   List backlog (query: ?status=queued&assigned_to=s1-dev)
PATCH  /api/ops/workpackages/{id}         Update work package (priority, status, assignment)
GET    /api/ops/workpackages/{id}         Get single work package with full detail
GET    /api/ops/capacity                  Per-agent capacity summary
```

### Decisions

```
GET    /api/ops/decisions                 List pending decisions
POST   /api/ops/decisions/{id}/resolve    Submit decision (body: {choice, rationale})
```

### WebSocket Extensions

Extend the existing `/ws/runtime` WebSocket to push additional event types:

```json
{"type": "signal_created", "signal": {...}}
{"type": "work_package_updated", "work_package": {...}}
{"type": "decision_created", "decision": {...}}
{"type": "decision_resolved", "decision": {...}}
{"type": "agent_status_changed", "agent_id": "s1-dev", "status": "working", "task": "..."}
```

---

## Frontend Components

### Page: OperationsRoomPage.tsx

New page that replaces the previous "Live Agent Panel" concept. This is the main view when a runtime is active.

Layout: 2x2 grid on desktop, stacked on mobile.

```
┌─────────────────────┬──────────────────────────────┐
│   Signal Inbox      │        S3 Backlog            │
│   (scrollable list) │   (3-column kanban)          │
│                     │                              │
├─────────────────────┼──────────────────────────────┤
│   System Status     │     Pending Decisions        │
│   (agent cards)     │     (decision cards)         │
│   + Capacity bars   │     + inline actions         │
└─────────────────────┴──────────────────────────────┘
```

### Component: SignalInbox.tsx

- List of signals, newest first
- Each signal shows: source icon, title, urgency badge, timestamp, affected areas as chips
- Source icons: telescope (S4), user (customer), magnifier (audit), crown (founder), gear (S1)
- Actions per signal: "Triage" button opens a popover to set priority and assign area, "Dismiss" button
- "New Signal" button at top for manual founder input
- Filter tabs: All | New | Triaged | Dismissed

### Component: BacklogBoard.tsx

- Three columns: Triage (unconverted signals), Queued (prioritized WPs), Active (in-progress WPs)
- Each card shows: title, priority number, assigned agent chip, estimated effort
- Drag-and-drop reordering within Queued column
- Click card to expand detail view with description, source signal link, result summary
- Active column is grouped by agent

### Component: SystemStatus.tsx

- One card per loaded agent
- Each card shows:
  - Agent name and role (S1/S2/S3/S3*/S4)
  - Health dot: green (idle), blue (working), yellow (warning), red (error), gray (stopped)
  - Current task label (from active work package or "idle")
  - Token budget mini-bar: spent vs remaining, percentage
  - Last activity timestamp
- Click card to open AgentTerminal (existing component from runtime plan Task 9) as a slide-over panel
- Summary bar at bottom: total budget spent / total budget, total messages routed, messages blocked

### Component: PendingDecisions.tsx

- Sorted by urgency (critical first), then by age (oldest first)
- Each decision card shows:
  - Decision type badge (approval / review / strategic / escalation)
  - Title and context summary (expandable)
  - Source agent
  - Action buttons matching the options (e.g., "Approve" / "Reject" / "Defer")
  - Optional rationale text field (shown on click of action button)
- Empty state: "No decisions pending — your system is running autonomously"

### Component: CapacityView.tsx

- Integrated into SystemStatus as capacity bars per agent
- Per agent: stacked bar showing queued (gray) + active (blue) + done today (green)
- Token budget bar below: spent (colored by percentage — green < 50%, yellow < 80%, red >= 80%)

---

## Signal-to-Work-Package Flow

This is the core process that the Operations Room enables:

```
1. SIGNAL ARRIVES
   Source → POST /api/ops/signals
   Examples:
   - S4 agent detects SGB VIII change → auto-creates signal
   - Human clicks "New Signal" → manual entry
   - S3* audit finds discrepancy → auto-creates signal
   - Customer support logs feature request → auto-creates signal

2. SIGNAL APPEARS IN INBOX
   WebSocket pushes signal_created event → UI updates
   Signal status: "new"

3. TRIAGE (S3 or Human)
   S3 agent periodically reads new signals and proposes priority + assignment
   OR human manually triages in the UI
   → PATCH /api/ops/signals/{id} with urgency assessment
   Signal status: "triaged"

4. CONVERT TO WORK PACKAGE
   POST /api/ops/signals/{id}/convert
   Creates a WorkPackage with:
   - priority from triage
   - assigned_to from triage or left unassigned
   - source_signal_id linked
   Signal status: "converted"
   WP status: "queued"

5. PRIORITIZE
   Human or S3 reorders the backlog
   PATCH /api/ops/workpackages/{id} with new priority

6. ACTIVATE
   S3 decides a WP is ready → assigns to S1 unit
   PATCH /api/ops/workpackages/{id} {status: "active", assigned_to: "s1-dev"}
   S2 routes the task to the S1 agent via MessageRouter

7. EXECUTE
   S1 agent works autonomously (runtime agent loop)
   Agent status in SystemStatus: "working"

8. COMPLETE
   S1 agent finishes → reports result
   PATCH /api/ops/workpackages/{id} {status: "done", result_summary: "..."}

9. VERIFY (optional)
   S3* audits the result
   PATCH /api/ops/workpackages/{id} {verified_by: "s3star-audit"}

10. CLOSED LOOP
    S3 updates org_memory.md with completed work
    Capacity view reflects the freed capacity
```

---

## Agent Integration (Closed Loop)

For the Operations Room to be truly live (not just a manual task board), agents must be wired to automatically generate signals and process work packages.

### S4 (Scout) Signal Generation

Add to S4's SKILL.md:
```
When you detect a relevant environment change during your scan:
1. Create a signal via POST /api/ops/signals with source="s4"
2. Include your relevance assessment in the description
3. Set urgency based on your scoring (>=4 → "high", >=3 → "medium", else "low")
```

S4 gets a new tool: `create_signal(title, description, affected_areas, urgency)`

### S3* (Audit) Signal Generation

Add to S3*'s SKILL.md:
```
When you find a discrepancy during audit:
- Tier 1 (auto-retry): No signal, handle internally
- Tier 2 (correct + notify): Create signal with urgency="medium"
- Tier 3 (block + escalate): Create signal with urgency="critical" AND create decision
```

S3* gets tools: `create_signal(...)`, `create_decision(title, context, options, urgency)`

### S3 (Controller) Backlog Processing

Add to S3's SKILL.md:
```
Periodically (every heartbeat cycle):
1. Read new signals: GET /api/ops/signals?status=new
2. For each signal, assess priority and affected area
3. Convert promising signals to work packages
4. Dismiss noise signals
5. Check active work packages for completion
6. Update org_memory.md with current priorities
```

S3 gets tools: `triage_signal(id, urgency)`, `convert_signal(id, priority, assigned_to)`, `dismiss_signal(id, reason)`

### S1 (Operational) Work Package Awareness

Add to each S1's SKILL.md:
```
When you receive a task from S2:
1. Check if it references a work_package_id
2. When you complete the task, update the work package status
3. Include a result_summary of what you did
```

S1 gets tools: `update_work_package(id, status, result_summary)`

---

## Relation to Existing Plans

### Replaces in Runtime Engine Plan

- **Task 9 (Frontend)**: The "AgentTerminal" and "RuntimePanel" components are absorbed into the Operations Room. AgentTerminal becomes a sub-panel opened from SystemStatus. RuntimePanel's cost summary becomes part of the CapacityView.

### Extends in Runtime Engine Plan

- **Task 5 (State Persistence)**: Three new SQLite tables (signals, work_packages, decisions)
- **Task 8 (API + WebSocket)**: New `/api/ops/*` endpoints and WebSocket event types

### New Task in Runtime Engine Plan

- **Task 10: Operations Room**: Build the frontend page and wire the closed-loop agent integration

### Relation to Agent Architecture

- The Operations Room is the **live interface** to the memory architecture. Signals map to what enters Schicht 2/3. Work packages are the operational translation. Decisions are the S5 touchpoints.
- The S3 Weekly Digest and S4 Monthly Brief still exist as structured summaries, but they are now generated FROM the Operations Room data rather than being the primary interaction surface.
- WhatsApp/Telegram push notifications remain for algedonic signals only (critical alerts that bypass the dashboard).

---

## Implementation Sequence

| Step | What | Effort |
|------|------|--------|
| 1 | SQLite schema extension (3 tables) + StateStore methods | 2-3 hours |
| 2 | REST API endpoints for signals, work packages, decisions | 3-4 hours |
| 3 | WebSocket event extensions | 1-2 hours |
| 4 | Frontend: OperationsRoomPage layout + SignalInbox | 3-4 hours |
| 5 | Frontend: BacklogBoard with drag-and-drop | 3-4 hours |
| 6 | Frontend: SystemStatus + CapacityView | 2-3 hours |
| 7 | Frontend: PendingDecisions with inline actions | 2-3 hours |
| 8 | Agent tools: create_signal, create_decision, update_work_package | 2-3 hours |
| 9 | S4/S3*/S3 SKILL.md updates for closed-loop integration | 1-2 hours |
| **Total** | | **~20-28 hours (3-4 days with AI)** |

---

## What's NOT in Scope (v1)

- Drag-and-drop between columns (only within Queued)
- Historical analytics (done WPs over time, signal trends)
- Multiple Operations Rooms for different recursion levels
- Role-based access (everyone sees everything)
- Mobile-optimized layout
- Notification preferences per signal type
