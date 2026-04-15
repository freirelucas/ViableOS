# ViableOS

**The operating system for viable AI agent organizations.**

ViableOS applies the [Viable System Model](https://en.wikipedia.org/wiki/Viable_system_model) (VSM) to multi-agent AI systems. Design a self-governing organization with operations, coordination, optimization, audit, intelligence, and policy — then simulate it or generate a deployable package.

Built from real community pain points: token cost management, agent looping, workspace conflicts, model reliability, and the gap between demo and production.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/freirelucas/ViableOS?ref=main)

![Dashboard](docs/screenshots/dashboard.png)

## Quick Start

### One-click (GitHub Codespaces)

Click the badge above. Everything installs automatically. Browser opens to ViableOS.

### Local

```bash
pip install -e .
uvicorn viableos.api.main:app --port 8000 &
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

### Local with Ollama ($0, no API keys)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b && ollama pull mistral:7b
pip install -e .
uvicorn viableos.api.main:app --port 8000 &
cd frontend && npm install && npm run dev
```

## What it does

### Design
- **AI-Guided Assessment** — Chat with a VSM expert that interviews you about your organization and auto-generates a complete config
- **Guided Setup Wizard** — 6-step web wizard: template, identity, teams, budget & models, human-in-the-loop, review
- **13 Organization Templates** — SaaS, E-Commerce, Agency, Content Creator, Consulting, Law Firm, Accounting, Education, Policy Research, and more
- **Smart Budget Calculator** — Maps monthly USD budget to per-agent model allocations with 23 models across 7 providers
- **IPEA Researcher Personas** — Fetches researcher profiles from DSpace/IpeaPub RAG and injects expertise, themes, and writing style into agent prompts

### Simulate
- **Multi-Agent Simulation Engine** — Mesa-based tick simulation with Beer's tempo hierarchy (S2 faster than S1)
- **9 BDI Agents** — Beliefs-Desires-Intentions structure with LLM deliberation (or mock for fast testing)
- **Syntegration Protocol** — Beer's non-hierarchical deliberation: OSI → Jostle → Auction → 3× Reverberation → Resolution
- **Environment Model** — Scenario-driven timeline (legislation, publications, data, crises) with signal buffering
- **Mode Switching** — Normal / Elevated / Crisis scales all tick rates
- **VSM Communication Channels** — Typed message bus with channel constraints (S1 never talks to S1 directly)
- **Viability Metrics** — Per-tick DataFrames: messages, escalations, algedonic signals, agent activity
- **Simulation Dashboard** — Run simulations from the browser with agent activity bars, Syntegration timeline, and metrics

### Behavioral Specifications
- **Operational Modes** — Normal / Elevated / Crisis with mode-dependent autonomy, reporting frequency, and escalation thresholds
- **Escalation Chains** — Operational, quality, strategic, and algedonic paths with per-step timeouts
- **Execution Protocol** — Directive tracking: acknowledge → execute → report, with timeout escalation
- **Autonomy Matrix** — Per-unit definition of what agents can do alone, what needs coordination, what needs approval
- **Conflict Detection & Transduction** — S2 detects resource overlaps, deadline conflicts, output contradictions
- **Triple Index** — S3 tracks actuality, capability, and potentiality with deviation logic
- **Algedonic Channel** — Emergency bypass that lets any agent signal existential issues directly to S5/human

### Generate
- **OpenClaw Package Generator** — Creates SOUL.md, SKILL.md, HEARTBEAT.md, USER.md, MEMORY.md, AGENTS.md per agent
- **LangGraph Export** — Export configs as LangGraph-compatible Python packages with `setup.sh` one-command installer
- **Viability Checker** — 6 VSM completeness checks + community-driven warnings + behavioral spec validation
- **Ollama Support** — Local-only deployment with `ChatOllama`, zero API cost

## Architecture

```
React Frontend (TypeScript + Tailwind CSS 4)
        |
        | HTTP/JSON + SSE streaming
        v
FastAPI Backend (Python + LiteLLM)
        |
        v
Core Library
├── schema.py              # JSON Schema validation
├── assessment_transformer  # Assessment → ViableSystem config
├── budget.py              # Token budget calculator
├── checker.py             # VSM completeness + behavioral spec checks
├── generator.py           # OpenClaw package generator
├── langgraph_generator.py # LangGraph package generator
├── soul_templates.py      # Per-agent SOUL/SKILL/HEARTBEAT content
├── coordination.py        # Auto-generated coordination rules
├── persona/               # IPEA researcher profiles (DSpace + IpeaPub RAG)
├── chat/                  # LLM assessment interview engine
└── simulation/            # Mesa-based multi-agent simulation
    ├── engine.py          # VSMSimulation(mesa.Model)
    ├── scheduler.py       # Multi-rate: S2=1, S1=2, S4=4, S3*=8, S3=14, S5=50
    ├── channels.py        # Typed VSM message bus
    ├── environment.py     # Scenario-driven world model
    ├── metrics.py         # DataCollector → pandas DataFrames
    ├── agents/            # BDI agents: S1, S2 (rule-based), S3, S3*, S4, S5
    └── protocols/         # Syntegration (Beer's Team Syntegrity)
```

## Simulation: Beer's Tempo Hierarchy

The simulation engine implements Beer's insight that different VSM systems operate at different speeds:

```
S2 Coordinator  ████████████████████  rate=1  (nervous system — fastest)
S1 Operations   █·█·█·█·█·█·█·█·█·  rate=2  (organs)
S4 Intelligence ···█···█···█···█···  rate=4  (environmental scanning)
S3* Audit       ·······█·······█···  rate=8  (periodic sampling)
S3 Control      ·············█·····  rate=14 (management cycle)
S5 Policy       ···················  rate=50 (normative — slowest)
```

Syntegration events interrupt normal heartbeats for democratic deliberation when triggered by converging signals, coordination failures, or human request.

## Screenshots

| Chat Assessment | Wizard Templates | Budget & Models |
|:---:|:---:|:---:|
| ![Chat](docs/screenshots/chat.png) | ![Templates](docs/screenshots/wizard-templates.png) | ![Budget](docs/screenshots/wizard-budget.png) |

| Review & Warnings | Identity & Values | Units |
|:---:|:---:|:---:|
| ![Review](docs/screenshots/wizard-review.png) | ![Identity](docs/screenshots/wizard-identity.png) | ![Units](docs/screenshots/wizard-units.png) |

## Organization Templates

| Template | Units | Best for |
|---|---|---|
| SaaS Startup | Product Dev, Operations, Go-to-Market | Technical founders |
| E-Commerce | Sourcing, Store, Fulfillment, Customer Service | Online retailers |
| Freelance / Agency | Client Acquisition, Delivery, Knowledge | Solo consultants |
| Content Creator | Production, Community, Monetization | YouTubers, writers |
| Marketing Agency | Strategy, Creative, Performance, Client Relations | Digital agencies |
| Consulting Firm | Business Dev, Engagement Delivery, Knowledge & IP | Professional services |
| Law Firm | Case Management, Legal Research, Client Relations | Legal practices |
| Accounting Firm | Bookkeeping, Tax & Compliance, Advisory | Financial services |
| Online Education | Course Dev, Student Success, Growth | Course creators |
| Restaurant / Hospitality | Kitchen, Front-of-House, Marketing | F&B businesses |
| **Policy Research** | **Monitoring, Bibliographic, Text Production, Data & Evidence** | **IPEA/DIEST researchers** |
| Personal Productivity | Deep Work, Admin, Learning | Anyone |
| Start from Scratch | — | Custom organizations |

## VSM Systems

| System | Role | In Simulation |
|---|---|---|
| S1 | Operations — the units that do the actual work | BDI agents with LLM deliberation, tick_rate=2 |
| S2 | Coordination — prevents conflicts between units | Rule-based (no LLM, faster than S1), tick_rate=1 |
| S3 | Optimization — allocates resources, tracks KPIs | Issues directives to S1 via S2, tick_rate=14 |
| S3* | Audit — independent quality checks (different provider) | Cross-model verification, event-driven, tick_rate=8 |
| S4 | Intelligence — monitors environment, strategic briefs | Scans environment model, detects signals, tick_rate=4 |
| S5 | Identity — enforces values, prepares human decisions | Algedonic channel, lowest tick_rate=50 |

## Model Routing

```yaml
# Local-only ($0) — all Ollama
model_routing:
  s1_routine: "ollama/llama3.1:8b"
  s3_optimization: "ollama/qwen2.5:32b"
  s3_star_audit: "ollama/mistral-small:22b"  # different family for audit

# Hybrid — S1 local, S3/S4 cloud (~$17/month)
model_routing:
  s1_routine: "ollama/llama3.1:8b"
  s3_optimization: "claude-haiku-4-5"
  s3_star_audit: "ollama/mistral:7b"
  s4_intelligence: "claude-haiku-4-5"
```

## Development

```bash
pip install -e ".[dev]"

# Backend tests (281 tests)
pytest tests/ -v

# Frontend
cd frontend && npm install
npx tsc --noEmit          # Type check
npx vitest run             # Unit tests
npx playwright test        # E2E tests
```

## Tech Stack

**Backend:** Python, FastAPI, LiteLLM, Mesa 3, PyYAML, jsonschema, httpx
**Frontend:** React 19, TypeScript, Tailwind CSS 4, Zustand, Vite
**Simulation:** Mesa 3 (multi-agent), pandas (metrics)
**Testing:** pytest (281 tests), Vitest, Playwright
**Deployment:** Docker Compose, GitHub Codespaces, Ollama

## Roadmap

- [x] v0.1 — YAML schema, VSM completeness checker, CLI
- [x] v0.2 — Web wizard, dashboard, budget calculator, OpenClaw generator, 12 templates
- [x] v0.2.1 — Chat-based assessment, file upload, SSE streaming, LangGraph export
- [x] v0.2.2 — Behavioral specifications: operational modes, escalation chains, execution protocol, autonomy matrix, conflict detection, triple index, algedonic channel
- [x] v0.2.3 — **Simulation engine**: Mesa-based multi-agent simulation, Syntegration protocol, IPEA personas, Ollama support, environment model, simulation dashboard, one-click Codespaces
- [ ] v0.3 — LLM-powered deliberation, live Syntegration with real reasoning, Operations Room
- [ ] v0.4 — Multi-runtime support (LangGraph, CrewAI, custom), benchmark integration

## License

MIT
