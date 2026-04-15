"""Simulation API endpoints — run VSM simulations and retrieve results."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from viableos.schema import validate
from viableos.simulation.engine import VSMSimulation
from viableos.simulation.environment import (
    minimal_scenario,
    policy_research_scenario,
)

logger = logging.getLogger(__name__)

sim_router = APIRouter(prefix="/api/simulate", tags=["simulation"])


class SimulationRequest(BaseModel):
    config: dict[str, Any]
    ticks: int = Field(default=100, ge=1, le=1000)
    scenario: str = Field(default="auto", description="Scenario: 'auto', 'policy_research', 'minimal', or 'none'")
    trigger_syntegration_at: int | None = Field(default=None, description="Tick at which to manually trigger a Syntegration")


class AgentSnapshot(BaseModel):
    name: str
    system_level: str
    step_count: int
    tasks_completed: int
    beliefs_count: int
    inbox_size: int


class SyntegrationSnapshot(BaseModel):
    id: str
    trigger: str
    proposed_by: str
    phase: str
    topics: list[str]
    outcomes_count: int
    started_at_tick: int
    completed_at_tick: int | None


class SimulationResponse(BaseModel):
    ticks_run: int
    mode: str
    agents: list[AgentSnapshot]
    messages_sent: int
    messages_delivered: int
    messages_blocked: int
    algedonic_signals: int
    environment_events_total: int
    syntegrations_completed: int
    syntegration_history: list[SyntegrationSnapshot]
    metrics: list[dict[str, Any]]  # per-tick model metrics


@sim_router.post("", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest) -> SimulationResponse:
    """Run a VSM simulation and return results."""
    # Validate config
    errors = validate(req.config)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    # Select scenario
    scenario_map = {
        "policy_research": lambda: policy_research_scenario(req.ticks),
        "minimal": lambda: minimal_scenario(req.ticks),
        "none": lambda: [],
    }
    if req.scenario == "auto":
        scenario_events = policy_research_scenario(req.ticks)
    elif req.scenario in scenario_map:
        scenario_events = scenario_map[req.scenario]()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario}")

    # Create and run simulation (no LLM for API — fast, deterministic)
    sim = VSMSimulation(
        req.config,
        scenario=scenario_events,
        ticks=req.ticks,
    )

    # Optionally trigger syntegration at specified tick
    for tick_num in range(1, req.ticks + 1):
        if req.trigger_syntegration_at and tick_num == req.trigger_syntegration_at:
            sim.trigger_syntegration("manual_api_trigger", proposed_by="human")
        sim.step()

    # Collect results
    agents = [
        AgentSnapshot(
            name=a.name,
            system_level=a.system_level,
            step_count=a.step_count,
            tasks_completed=a.tasks_completed,
            beliefs_count=len(a.beliefs),
            inbox_size=len(a.inbox),
        )
        for a in sim.scheduler.agents
    ]

    synteg_history = [
        SyntegrationSnapshot(
            id=s.id,
            trigger=s.trigger,
            proposed_by=s.proposed_by,
            phase=s.phase.value,
            topics=s.topics,
            outcomes_count=len(s.outcomes),
            started_at_tick=s.started_at_tick,
            completed_at_tick=s.completed_at_tick,
        )
        for s in sim.syntegration_history
    ]

    # Per-tick metrics as list of dicts
    try:
        df = sim.datacollector.get_model_vars_dataframe()
        metrics = df.reset_index().to_dict(orient="records")
    except Exception:
        metrics = []

    return SimulationResponse(
        ticks_run=sim.tick,
        mode=sim.mode,
        agents=agents,
        messages_sent=sim.message_bus.total_sent,
        messages_delivered=sim.message_bus.total_delivered,
        messages_blocked=sim.message_bus.total_blocked,
        algedonic_signals=sim.message_bus.algedonic_count,
        environment_events_total=len(sim.environment._history),
        syntegrations_completed=len(sim.syntegration_history),
        syntegration_history=synteg_history,
        metrics=metrics,
    )
