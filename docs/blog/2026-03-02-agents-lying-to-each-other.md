# Your Multi-Agent Framework Handles Operations. What About the Other Five?

In [Part 1](https://dev.to/philippenderle/your-ai-agents-need-an-org-chart-but-not-the-kind-you-think-2fg7), I introduced the Viable System Model (VSM) and how it maps to multi-agent AI systems. The response was great — but the most common question was: *"OK, the theory makes sense. But how is this actually different from what CrewAI/LangGraph/AutoGen already do?"*

Fair question. Let me answer it properly.

## The One Thing Every Framework Gets Right

Every multi-agent framework gives you System 1 — Operations. The agents that do actual work. Define a role, give it tools, let it run. CrewAI calls them "agents." LangGraph calls them "nodes." AutoGen calls them "agents" too. This part works.

The problem is that operations is 1 of 6 necessary control functions. The other five — coordination, optimization, audit, intelligence, and identity — are either missing entirely or left as an exercise for the developer.

Here's what that looks like:

```
              S1    S2    S3    S3*   S4    S5
             Ops  Coord Optim Audit Intel Ident
CrewAI        ✅    ❌    ⚠️    ❌    ❌    ❌
LangGraph     ✅    ❌    ⚠️    ❌    ❌    ❌
OpenAI Agents ✅    ❌    ❌    ❌    ❌    ❌
AutoGen       ⚠️    ⚠️    ❌    ❌    ❌    ❌
ViableOS      ✅    ✅    ✅    ✅    ✅    ✅
```

This isn't a knock on those frameworks. They're excellent infrastructure — they give you the building blocks to run agents. But infrastructure isn't organization. It's like having Kubernetes without knowing what services to deploy, how they should communicate, and who watches them.

## Why VSM Is Different: It's About the Channels, Not the Agents

Stafford Beer's Viable System Model isn't a framework you bolt onto agents. It's a structural theory about what ANY viable system needs to survive — whether it's a cell, a company, or a swarm of AI agents. He published it in 1972. It's been validated on governments, corporations, and cooperatives. And it maps 1:1 to multi-agent AI.

The key insight: **viability requires specific communication channels, not just capable components.**

In a flat multi-agent system with 5 agents, you potentially need 20 direct communication channels. Every agent might talk to every other agent. That's n×(n-1) complexity. It doesn't scale. More importantly, it doesn't differentiate — a resource conflict looks the same as a strategic concern looks the same as an emergency.

The VSM replaces this with **structured channels**, each with a specific purpose:

```
S5 (Identity/Policy)
    ↕ balance channel
S4 (Intelligence)     S3 (Optimization)
    ↕ strategy bridge      ↕ command channel
                      S2 (Coordination)
                           ↕ coordination rules
              S1a ←→ S1b ←→ S1c (Operations)
                    ↕
              S3* (Audit — independent, different provider)
```

**S2 coordination rules** prevent conflicts between S1 units. Not by managing them, but by establishing traffic rules. "If you deploy, notify ops. If you claim a feature, verify with dev first."

**S3 command channel** gives optimization authority over operations. "Shift 20% of your token budget to the high-priority task." This is top-down resource allocation with teeth.

**S3* audit bypass** goes directly from the auditor into S1 operations — read-only, independent, different LLM provider. "I checked the last 5 commits. Tests didn't actually pass." (More on why "different provider" matters below.)

**S4→S3 strategy bridge** injects external intelligence into operational planning. "Competitor just launched feature X. Here's a briefing."

**S5 balance channel** ensures the system doesn't drift too far toward internal optimization (S3) or external scanning (S4). Too much S3 = navel-gazing. Too much S4 = strategy tourism.

**Algedonic channel** — the emergency bypass. Any agent can signal existential issues directly to S5 and the human, skipping the entire hierarchy. Named after the Greek words for pain (*algos*) and pleasure (*hedone*). This is your system's fire alarm.

These channels aren't nice-to-haves. Each one prevents a specific failure mode:

| Without this channel... | You get... |
|---|---|
| S2 coordination | Agents contradicting each other |
| S3 command | No resource control, token budgets explode |
| S3* audit | Hallucinations go undetected |
| S4→S3 bridge | System optimizes for yesterday's world |
| S5 balance | Either navel-gazing or strategy tourism |
| Algedonic | Critical issues buried in status reports |

That's the difference between "a list of agents with a router" and "a viable system." The agents are the same. The organization makes them work.

## Deep Dive: Why Your Agents Forget Their Orders

Let me zoom in on one problem that every multi-agent system has but almost nobody talks about: **context window amnesia**.

LLMs don't have persistent memory. Everything lives in the context window — a buffer of recent messages that eventually overflows. When S3 (Optimization) sends a directive to an S1 worker — say, "switch to a cheaper model for routine tasks to stay within budget" — that directive enters the context window. For maybe 20-40 turns, the agent remembers. Then newer messages push it out.

The agent doesn't refuse the directive. It doesn't disagree. It simply *forgets it existed*.

In a human organization, this is the memo that nobody read. The policy that got announced but never enforced. The quarterly goal that was abandoned by February. Stafford Beer saw this problem 50 years ago and his solution had a name: the **Execution Protocol** (German: *Vollzug*).

*Vollzug* is German for the confirmed execution of a directive. Not "I heard you" — but "I heard you, I did it, and here's proof." Beer was a British cyberneticist who borrowed the German term because English doesn't have a single word for this concept. We call it the Execution Protocol. Three steps, each with a hard timeout:

```yaml
execution_protocol:
  enabled: true
  timeout_acknowledgment: 30min    # Must acknowledge within 30 min
  timeout_completion: 48h          # Must execute within 48 hours
  on_timeout: escalate             # Auto-escalate if missed
```

**Step 1 — Acknowledgment.** The receiving agent has 30 minutes to confirm receipt. No confirmation → auto-escalate. This catches the case where a directive is sent but never enters the agent's active context.

**Step 2 — Execution.** The agent has 48 hours to carry out the directive. The timeout scales with team size — a 2-person org gets 12 hours, a 10-person org gets a full week.

**Step 3 — Report.** Confirm completion with evidence. Not "done" — but "done, and here's what changed."

If any step times out, the system escalates automatically. But not everything goes through the same path:

```yaml
escalation_chains:
  operational:
    path: [s2-coordination, s3-optimization, human]
    timeout_per_step: 2h
  quality:
    path: [s3-optimization, human]
    timeout_per_step: 2h
  strategic:
    path: [s4-intelligence, s5-policy, human]
    timeout_per_step: 4h
  algedonic:
    path: [s5-policy, human]
    timeout_per_step: 15min
```

An operational timeout goes through coordination first. A quality issue goes straight to optimization. A strategic concern routes through intelligence and policy. And an existential threat — the algedonic channel — reaches the human in 15 minutes, no matter what.

This is what "from topology to behavior" means. It's not enough to define which agents exist. You need to define how they behave when things go wrong. When context is lost. When directives are ignored. When the whole system is on fire. That's the gap between a diagram and an operating system.

And here's why this matters specifically for LLM-based agents: LLMs are *optimized to produce coherent, confident outputs*. An agent reporting "task completed" sounds exactly like an agent that actually completed the task — and one that hallucinated the completion. Without execution tracking, without S3* audit, without escalation chains — you have no way to tell the difference.

## What We've Built

[ViableOS](https://github.com/philipp-lm/ViableOS) takes all of this and turns it into working software. You describe your organization — or let an AI-powered assessment interview figure it out — and it generates the full VSM package: every agent, every channel, every behavioral spec.

**What works today:**

- **AI-guided assessment interview** — Chat with a VSM expert that asks the right questions and auto-generates a complete config
- **6-step web wizard** with 12 organization templates (SaaS, E-Commerce, Agency, Consulting, Law Firm, Education, and more)
- **Budget calculator** mapping monthly USD to per-agent model allocations across 23 models and 7 providers
- **Assessment transformer** that auto-derives all 9 behavioral spec areas from your assessment data — team size, external forces, success criteria, dependencies → operational modes, escalation chains, execution protocol, autonomy matrix, provider constraints, everything
- **Package generator** producing SOUL.md, SKILL.md, HEARTBEAT.md per agent, plus coordination rules, permission matrices, and fallback chains
- **LangGraph export** for direct integration
- **Viability checker** with VSM completeness checks and behavioral spec validation
- **245 passing tests** across schema, transformer, generator, and checker

**What's auto-derived, not hand-configured:**

Small team (1-2 people) → shorter timeouts, more human approval, daily reporting. Large team (10+) → more agent autonomy, longer execution windows, weekly reporting. Regulatory external forces → monthly premise checks, elevated mode triggers. You can override everything, but the defaults are designed to be sensible based on 50 years of organizational theory.

**What we haven't built yet:**

The runtime engine. ViableOS currently generates the *configuration* for a viable agent organization. It doesn't yet *execute* it. There's no live enforcement of execution protocol timeouts, no real-time escalation routing, no Operations Room. That's v0.3 — and it's where I need help.

## First Test: My Own Healthcare Software Company

Theory is worth nothing without practice. So the first real test of ViableOS will be my own company — a small medical care software firm in Germany.

It's a good test case for three reasons:

**The domain is regulated.** GDPR, healthcare data laws, documentation requirements. This forces the system to take identity and values seriously — "patient privacy above everything" isn't a nice-to-have, it's legally required. S5 (Identity) earns its keep here. And S3* audit with a different LLM provider isn't theoretical elegance — it's practical necessity when agents touch patient-adjacent workflows.

**The stakes are real.** When agents handle scheduling, documentation, or billing, hallucinations aren't just annoying — they're potentially harmful. The Execution Protocol isn't academic neatness. It's "did you actually update that patient record, or did you just tell me you did?"

**It's small enough to be honest about.** Solo founder, small team. If ViableOS generates reasonable defaults for an organization this size, and if those defaults actually change agent behavior in practice, that's validation. If they don't — that's equally valuable information. I'll document the entire process publicly.

## Try It Yourself

But one test case doesn't validate a theory. If you're running multi-agent systems — on CrewAI, LangGraph, AutoGen, or your own framework — I'd genuinely love you to try ViableOS on your setup and tell us:

1. **Does the assessment capture your organization correctly?** Chat with the VSM expert or use the wizard. Does the output match your reality?
2. **Are the behavioral specs sensible?** Look at the generated SOUL.md files. Do the escalation chains, autonomy levels, and operational modes match your intuition about how your agents should work?
3. **What's missing?** Which failure patterns have you seen in production that our nine behavioral specs don't cover?

```bash
pip install -e ".[dev]"
viableos api
# Open http://localhost:5173
```

**GitHub:** [github.com/philipp-lm/ViableOS](https://github.com/philipp-lm/ViableOS)

Open an issue, start a discussion, or drop a comment here. Every behavioral spec in ViableOS started from theory — now we need practice to validate it. The more diverse the test cases, the better the system gets.

---

*This is part 2 of a series on applying organizational design to AI agent systems. [Part 1: Your AI Agents Need an Org Chart](https://dev.to/philippenderle/your-ai-agents-need-an-org-chart-but-not-the-kind-you-think-2fg7). Next: building the runtime that actually enforces these specs — the Operations Room.*

---

**Philipp Enderle** — Engineer (KIT, TU Munich, UC Berkeley). 9 years strategy consulting at Deloitte and Berylls by AlixPartners, designing org transformations for DAX automotive companies. Now applying the same organizational theory to AI agent teams.

[LinkedIn](https://linkedin.com/in/philippenderle) · [GitHub](https://github.com/philipp-lm) · [ViableOS](https://github.com/philipp-lm/ViableOS)
