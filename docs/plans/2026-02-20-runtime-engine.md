# ViableOS Runtime Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a production-capable runtime that loads a generated ViableOS package and runs the multi-agent organization — with agent loop, tool calling, multi-agent routing via S2, state persistence, heartbeats, budget tracking, and live UI.

**Architecture:** The runtime reads the already-generated package (SOUL.md, SKILL.md, HEARTBEAT.md per agent + openclaw.json). Each agent is an async loop: receive task → build system prompt from files → call LLM → handle tool calls → return result. The S2 Coordinator routes messages between agents using the VSM communication matrix. SQLite stores state. WebSocket streams live output to the React dashboard.

**Tech Stack:** Python 3.10+, LiteLLM (multi-provider LLM client), aiosqlite (async SQLite), asyncio, WebSocket (FastAPI), existing React frontend

---

## Dependency: LiteLLM

LiteLLM provides a unified API for 100+ LLM providers with one interface. Instead of writing separate code for OpenAI, Anthropic, Google, etc., we call `litellm.acompletion()` and pass the model string from our MODEL_CATALOG (e.g. `anthropic/claude-sonnet-4-6`).

```python
import litellm
response = await litellm.acompletion(
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "system", "content": soul_md}, {"role": "user", "content": task}],
    tools=tool_schemas,
)
```

This is the only new core dependency. Everything else uses stdlib or existing deps.

---

## Task 1: LLM Client Wrapper

**Files:**
- Create: `src/viableos/runtime/__init__.py`
- Create: `src/viableos/runtime/llm.py`
- Test: `tests/test_runtime_llm.py`
- Modify: `pyproject.toml` — add `litellm` dependency

**Step 1: Write the failing test**

```python
# tests/test_runtime_llm.py
import pytest
from unittest.mock import AsyncMock, patch
from viableos.runtime.llm import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_llm_client_basic_call():
    """LLMClient wraps litellm and returns structured response."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Hello from the agent"
    mock_response.choices[0].message.tool_calls = None
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 20

    with patch("viableos.runtime.llm.litellm.acompletion", return_value=mock_response):
        client = LLMClient()
        result = await client.complete(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Hi"}],
        )

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from the agent"
    assert result.tool_calls is None
    assert result.prompt_tokens == 50
    assert result.completion_tokens == 20


@pytest.mark.asyncio
async def test_llm_client_with_tool_calls():
    """LLMClient correctly parses tool call responses."""
    mock_tool_call = AsyncMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "read_file"
    mock_tool_call.function.arguments = '{"path": "README.md"}'

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 30

    with patch("viableos.runtime.llm.litellm.acompletion", return_value=mock_response):
        client = LLMClient()
        result = await client.complete(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Read the readme"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
        )

    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "read_file"


@pytest.mark.asyncio
async def test_llm_client_fallback():
    """LLMClient falls back to next model on failure."""
    call_count = 0

    async def mock_completion(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Rate limited")
        mock_resp = AsyncMock()
        mock_resp.choices = [AsyncMock()]
        mock_resp.choices[0].message.content = "Fallback worked"
        mock_resp.choices[0].message.tool_calls = None
        mock_resp.usage.prompt_tokens = 30
        mock_resp.usage.completion_tokens = 10
        return mock_resp

    with patch("viableos.runtime.llm.litellm.acompletion", side_effect=mock_completion):
        client = LLMClient()
        result = await client.complete(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Hi"}],
            fallbacks=["openai/gpt-5.1"],
        )

    assert result.content == "Fallback worked"
    assert call_count == 2


def test_token_cost_estimation():
    """Estimate USD cost from token counts."""
    client = LLMClient()
    cost = client.estimate_cost("anthropic/claude-sonnet-4-6", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0
    assert isinstance(cost, float)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runtime_llm.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Add litellm dependency**

In `pyproject.toml`, add to dependencies:

```toml
dependencies = [
    "PyYAML>=6.0",
    "jsonschema>=4.0",
    "click>=8.0",
    "rich>=13.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "litellm>=1.55",
    "aiosqlite>=0.20",
]
```

Run: `pip install -e ".[dev]"`

**Step 4: Implement LLM client**

```python
# src/viableos/runtime/__init__.py
"""ViableOS Runtime — executes multi-agent organizations."""

# src/viableos/runtime/llm.py
"""LLM client wrapper using LiteLLM for multi-provider support.

Handles: API calls, fallbacks, token counting, cost estimation.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import litellm

litellm.suppress_debug_info = True
log = logging.getLogger("viableos.runtime")

COST_PER_1K = {
    "anthropic/claude-opus-4-6": {"input": 0.015, "output": 0.075},
    "anthropic/claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "anthropic/claude-haiku-4-5": {"input": 0.0008, "output": 0.004},
    "openai/gpt-5.2": {"input": 0.010, "output": 0.030},
    "openai/gpt-5.1": {"input": 0.005, "output": 0.015},
    "openai/gpt-5.3-codex": {"input": 0.012, "output": 0.036},
    "openai/gpt-5-mini": {"input": 0.0004, "output": 0.0016},
    "google/gemini-3-pro": {"input": 0.007, "output": 0.021},
    "google/gemini-3-flash": {"input": 0.001, "output": 0.004},
}
DEFAULT_COST = {"input": 0.003, "output": 0.015}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[dict[str, Any]] | None
    prompt_tokens: int
    completion_tokens: int
    model: str = ""
    cost_usd: float = 0.0


class LLMClient:
    def __init__(self) -> None:
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        fallbacks: list[str] | None = None,
    ) -> LLMResponse:
        models_to_try = [model] + (fallbacks or [])

        last_error: Exception | None = None
        for m in models_to_try:
            try:
                kwargs: dict[str, Any] = {
                    "model": m,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools

                response = await litellm.acompletion(**kwargs)
                choice = response.choices[0]

                parsed_tool_calls = None
                if choice.message.tool_calls:
                    parsed_tool_calls = []
                    for tc in choice.message.tool_calls:
                        args = tc.function.arguments
                        if isinstance(args, str):
                            args = json.loads(args)
                        parsed_tool_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": args,
                        })

                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                cost = self.estimate_cost(m, prompt_tokens, completion_tokens)

                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                self.total_cost_usd += cost
                self.call_count += 1

                return LLMResponse(
                    content=choice.message.content,
                    tool_calls=parsed_tool_calls,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=m,
                    cost_usd=cost,
                )
            except Exception as e:
                last_error = e
                log.warning("Model %s failed: %s. Trying fallback...", m, e)
                continue

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = COST_PER_1K.get(model, DEFAULT_COST)
        return (prompt_tokens / 1000 * rates["input"]) + (completion_tokens / 1000 * rates["output"])

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "call_count": self.call_count,
        }
```

**Step 5: Run tests**

Run: `pytest tests/test_runtime_llm.py -v`
Expected: PASS (install `pytest-asyncio` if needed: `pip install pytest-asyncio`)

**Step 6: Commit**

```bash
git add src/viableos/runtime/ tests/test_runtime_llm.py pyproject.toml
git commit -m "feat(runtime): add LLM client with multi-provider fallback via LiteLLM"
```

---

## Task 2: Tool Framework

**Files:**
- Create: `src/viableos/runtime/tools.py`
- Test: `tests/test_runtime_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_runtime_tools.py
import os
import tempfile
from pathlib import Path

import pytest
from viableos.runtime.tools import ToolRegistry, SandboxedFileTools


def test_tool_registry_register_and_list():
    """Registry tracks tools and produces OpenAI-compatible schemas."""
    registry = ToolRegistry()

    @registry.register("Read a file", {"path": {"type": "string", "description": "File path"}})
    def read_file(path: str) -> str:
        return f"contents of {path}"

    schemas = registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "read_file"
    assert "path" in schemas[0]["function"]["parameters"]["properties"]


def test_tool_registry_execute():
    """Registry can execute a registered tool by name."""
    registry = ToolRegistry()

    @registry.register("Add numbers", {
        "a": {"type": "number", "description": "First number"},
        "b": {"type": "number", "description": "Second number"},
    })
    def add(a: float, b: float) -> str:
        return str(a + b)

    result = registry.execute("add", {"a": 3, "b": 4})
    assert result == "7.0"


def test_tool_registry_unknown_tool():
    """Executing unknown tool returns error string."""
    registry = ToolRegistry()
    result = registry.execute("nonexistent", {})
    assert "error" in result.lower()


def test_sandboxed_file_tools_read():
    """Sandboxed tools can read files within workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "test.txt").write_text("hello world")

        tools = SandboxedFileTools(workspace)
        result = tools.read_file("test.txt")
        assert result == "hello world"


def test_sandboxed_file_tools_blocks_escape():
    """Sandboxed tools block path traversal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        tools = SandboxedFileTools(workspace)
        result = tools.read_file("../../etc/passwd")
        assert "denied" in result.lower() or "error" in result.lower()


def test_sandboxed_file_tools_write():
    """Sandboxed tools can write files within workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        tools = SandboxedFileTools(workspace)

        result = tools.write_file("output.txt", "test content")
        assert "ok" in result.lower() or "written" in result.lower()
        assert (workspace / "output.txt").read_text() == "test content"


def test_sandboxed_file_tools_list():
    """Sandboxed tools can list files in workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "a.txt").write_text("a")
        (workspace / "b.txt").write_text("b")

        tools = SandboxedFileTools(workspace)
        result = tools.list_files(".")
        assert "a.txt" in result
        assert "b.txt" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runtime_tools.py -v`
Expected: FAIL

**Step 3: Implement tool framework**

```python
# src/viableos/runtime/tools.py
"""Tool framework with sandbox enforcement.

Each agent gets a SandboxedFileTools instance scoped to its workspace directory.
Path traversal is blocked. The ToolRegistry produces OpenAI-compatible tool schemas.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("viableos.runtime")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., str]] = {}
        self._schemas: list[dict[str, Any]] = []

    def register(
        self, description: str, parameters: dict[str, Any]
    ) -> Callable[[Callable[..., str]], Callable[..., str]]:
        def decorator(func: Callable[..., str]) -> Callable[..., str]:
            self._tools[func.__name__] = func
            self._schemas.append({
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": parameters,
                        "required": list(parameters.keys()),
                    },
                },
            })
            return func
        return decorator

    def add(self, name: str, func: Callable[..., str], description: str, parameters: dict[str, Any]) -> None:
        self._tools[name] = func
        self._schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": list(parameters.keys()),
                },
            },
        })

    def get_schemas(self) -> list[dict[str, Any]]:
        return list(self._schemas)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        func = self._tools.get(name)
        if not func:
            return f"Error: unknown tool '{name}'"
        try:
            return func(**arguments)
        except Exception as e:
            return f"Error executing {name}: {e}"

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())


class SandboxedFileTools:
    """Filesystem tools scoped to a single workspace directory."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def _safe_path(self, relative: str) -> Path | None:
        target = (self.workspace / relative).resolve()
        if not str(target).startswith(str(self.workspace)):
            return None
        return target

    def read_file(self, path: str) -> str:
        safe = self._safe_path(path)
        if safe is None:
            return "Error: access denied — path is outside workspace"
        if not safe.exists():
            return f"Error: file not found: {path}"
        try:
            return safe.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading {path}: {e}"

    def write_file(self, path: str, content: str) -> str:
        safe = self._safe_path(path)
        if safe is None:
            return "Error: access denied — path is outside workspace"
        try:
            safe.parent.mkdir(parents=True, exist_ok=True)
            safe.write_text(content, encoding="utf-8")
            return f"OK: written {len(content)} chars to {path}"
        except Exception as e:
            return f"Error writing {path}: {e}"

    def list_files(self, path: str = ".") -> str:
        safe = self._safe_path(path)
        if safe is None:
            return "Error: access denied — path is outside workspace"
        if not safe.is_dir():
            return f"Error: not a directory: {path}"
        try:
            entries = sorted(safe.iterdir())
            lines = []
            for entry in entries:
                rel = entry.relative_to(self.workspace)
                prefix = "d" if entry.is_dir() else "f"
                lines.append(f"[{prefix}] {rel}")
            return "\n".join(lines) if lines else "(empty directory)"
        except Exception as e:
            return f"Error listing {path}: {e}"

    def to_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.add("read_file", self.read_file, "Read a file from the workspace",
                      {"path": {"type": "string", "description": "Relative file path"}})
        registry.add("write_file", self.write_file, "Write content to a file in the workspace",
                      {"path": {"type": "string", "description": "Relative file path"},
                       "content": {"type": "string", "description": "File content to write"}})
        registry.add("list_files", self.list_files, "List files in a workspace directory",
                      {"path": {"type": "string", "description": "Relative directory path (default: .)"}})
        return registry
```

**Step 4: Run tests**

Run: `pytest tests/test_runtime_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/viableos/runtime/tools.py tests/test_runtime_tools.py
git commit -m "feat(runtime): add sandboxed tool framework with filesystem isolation"
```

---

## Task 3: Single Agent (Agent Loop)

**Files:**
- Create: `src/viableos/runtime/agent.py`
- Test: `tests/test_runtime_agent.py`

This is the core component. An Agent:
1. Loads SOUL.md + SKILL.md as system prompt
2. Receives a task (user message)
3. Runs the agent loop: call LLM → handle tool calls → repeat until done
4. Enforces anti-looping (max iterations, repetition detection)
5. Tracks token usage

**Step 1: Write the failing test**

```python
# tests/test_runtime_agent.py
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from viableos.runtime.agent import Agent, AgentConfig


@pytest.fixture
def agent_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        (ws / "SOUL.md").write_text("# Test Agent\nYou are a helpful test agent.")
        (ws / "SKILL.md").write_text("# Skills\n- Only use approved tools")
        (ws / "HEARTBEAT.md").write_text("# Heartbeat\n- Check status every 30 minutes")
        yield ws


@pytest.mark.asyncio
async def test_agent_loads_identity(agent_workspace):
    """Agent reads SOUL.md and SKILL.md on init."""
    config = AgentConfig(
        agent_id="s1-test",
        name="Test Agent",
        model="anthropic/claude-sonnet-4-6",
        workspace=agent_workspace,
    )
    agent = Agent(config)
    assert "helpful test agent" in agent.system_prompt
    assert "approved tools" in agent.system_prompt


@pytest.mark.asyncio
async def test_agent_basic_response(agent_workspace):
    """Agent returns LLM response for a simple task."""
    from viableos.runtime.llm import LLMResponse

    mock_response = LLMResponse(
        content="Task completed successfully.",
        tool_calls=None,
        prompt_tokens=100,
        completion_tokens=50,
        model="anthropic/claude-sonnet-4-6",
        cost_usd=0.001,
    )

    config = AgentConfig(
        agent_id="s1-test",
        name="Test Agent",
        model="anthropic/claude-sonnet-4-6",
        workspace=agent_workspace,
    )
    agent = Agent(config)

    with patch.object(agent.llm, "complete", return_value=mock_response):
        result = await agent.run("Do something useful")

    assert result.content == "Task completed successfully."
    assert result.iterations == 1


@pytest.mark.asyncio
async def test_agent_handles_tool_calls(agent_workspace):
    """Agent executes tool calls and feeds results back to LLM."""
    from viableos.runtime.llm import LLMResponse

    # First call: LLM wants to read a file
    tool_response = LLMResponse(
        content=None,
        tool_calls=[{"id": "call_1", "name": "read_file", "arguments": {"path": "SOUL.md"}}],
        prompt_tokens=100, completion_tokens=30,
        model="anthropic/claude-sonnet-4-6", cost_usd=0.001,
    )
    # Second call: LLM returns final answer
    final_response = LLMResponse(
        content="I read the file. It says you are a test agent.",
        tool_calls=None,
        prompt_tokens=200, completion_tokens=50,
        model="anthropic/claude-sonnet-4-6", cost_usd=0.002,
    )

    config = AgentConfig(
        agent_id="s1-test",
        name="Test Agent",
        model="anthropic/claude-sonnet-4-6",
        workspace=agent_workspace,
    )
    agent = Agent(config)

    with patch.object(agent.llm, "complete", side_effect=[tool_response, final_response]):
        result = await agent.run("What does your SOUL.md say?")

    assert result.iterations == 2
    assert "test agent" in result.content.lower()


@pytest.mark.asyncio
async def test_agent_anti_loop_protection(agent_workspace):
    """Agent stops after max_iterations to prevent infinite loops."""
    from viableos.runtime.llm import LLMResponse

    # LLM keeps calling tools forever
    loop_response = LLMResponse(
        content=None,
        tool_calls=[{"id": "call_n", "name": "list_files", "arguments": {"path": "."}}],
        prompt_tokens=50, completion_tokens=20,
        model="anthropic/claude-sonnet-4-6", cost_usd=0.001,
    )

    config = AgentConfig(
        agent_id="s1-test",
        name="Test Agent",
        model="anthropic/claude-sonnet-4-6",
        workspace=agent_workspace,
        max_iterations=5,
    )
    agent = Agent(config)

    with patch.object(agent.llm, "complete", return_value=loop_response):
        result = await agent.run("Loop forever")

    assert result.iterations == 5
    assert result.stopped_reason == "max_iterations"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runtime_agent.py -v`
Expected: FAIL

**Step 3: Implement the Agent**

```python
# src/viableos/runtime/agent.py
"""Single agent — the core execution unit.

Loads SOUL.md + SKILL.md as system prompt, runs the agent loop
(LLM call → tool execution → repeat), enforces anti-looping.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from viableos.runtime.llm import LLMClient, LLMResponse
from viableos.runtime.tools import SandboxedFileTools, ToolRegistry

log = logging.getLogger("viableos.runtime")


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    model: str
    workspace: Path
    fallbacks: list[str] = field(default_factory=list)
    max_iterations: int = 15
    max_tokens_per_response: int = 4096
    extra_tools: ToolRegistry | None = None


@dataclass
class AgentResult:
    content: str | None
    iterations: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    stopped_reason: str = "completed"
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    def __init__(self, config: AgentConfig, llm: LLMClient | None = None) -> None:
        self.config = config
        self.llm = llm or LLMClient()

        # Load identity files
        soul_path = config.workspace / "SOUL.md"
        skill_path = config.workspace / "SKILL.md"

        soul_content = soul_path.read_text() if soul_path.exists() else ""
        skill_content = skill_path.read_text() if skill_path.exists() else ""

        self.system_prompt = f"{soul_content}\n\n---\n\n{skill_content}".strip()

        # Setup sandboxed tools
        file_tools = SandboxedFileTools(config.workspace)
        self.tools = file_tools.to_registry()

        if config.extra_tools:
            for schema in config.extra_tools.get_schemas():
                func_name = schema["function"]["name"]
                func = config.extra_tools._tools.get(func_name)
                if func:
                    self.tools.add(
                        func_name, func,
                        schema["function"]["description"],
                        schema["function"]["parameters"].get("properties", {}),
                    )

        self._on_event: Callable[[dict[str, Any]], None] | None = None

    def on_event(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._on_event = callback

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._on_event:
            self._on_event({"agent_id": self.config.agent_id, "type": event_type, **data})

    async def run(self, task: str) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]

        total_prompt = 0
        total_completion = 0
        total_cost = 0.0
        tool_calls_log: list[dict[str, Any]] = []

        for iteration in range(1, self.config.max_iterations + 1):
            self._emit("llm_call", {"iteration": iteration, "model": self.config.model})

            response = await self.llm.complete(
                model=self.config.model,
                messages=messages,
                tools=self.tools.get_schemas() if self.tools.names else None,
                fallbacks=self.config.fallbacks,
            )

            total_prompt += response.prompt_tokens
            total_completion += response.completion_tokens
            total_cost += response.cost_usd

            if response.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": str(tc["arguments"])},
                        }
                        for tc in response.tool_calls
                    ],
                })

                for tc in response.tool_calls:
                    self._emit("tool_call", {"tool": tc["name"], "args": tc["arguments"]})
                    result = self.tools.execute(tc["name"], tc["arguments"])
                    self._emit("tool_result", {"tool": tc["name"], "result": result[:200]})

                    tool_calls_log.append({
                        "iteration": iteration,
                        "tool": tc["name"],
                        "arguments": tc["arguments"],
                        "result_preview": result[:200],
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
            else:
                self._emit("response", {"content": response.content})
                return AgentResult(
                    content=response.content,
                    iterations=iteration,
                    prompt_tokens=total_prompt,
                    completion_tokens=total_completion,
                    cost_usd=total_cost,
                    tool_calls_made=tool_calls_log,
                )

        # Hit max iterations — anti-loop protection
        self._emit("max_iterations", {"iterations": self.config.max_iterations})
        return AgentResult(
            content=f"[Agent stopped: exceeded {self.config.max_iterations} iterations]",
            iterations=self.config.max_iterations,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            cost_usd=total_cost,
            stopped_reason="max_iterations",
            tool_calls_made=tool_calls_log,
        )
```

**Step 4: Run tests**

Run: `pytest tests/test_runtime_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/viableos/runtime/agent.py tests/test_runtime_agent.py
git commit -m "feat(runtime): add Agent with loop, tool calling, and anti-loop protection"
```

---

## Task 4: Multi-Agent Router (S2 Coordinator Pattern)

**Files:**
- Create: `src/viableos/runtime/router.py`
- Test: `tests/test_runtime_router.py`

The Router implements the VSM communication matrix: S1 agents can only talk to S2. S2 routes to everyone. S3* has read-only access. This uses the `agentToAgent` config from `openclaw.json`.

**Step 1: Write the failing test**

```python
# tests/test_runtime_router.py
import pytest
from viableos.runtime.router import MessageRouter, Message


def test_s1_can_message_s2():
    permissions = {"s1-dev": ["s2-coordination"], "s2-coordination": ["s1-dev", "s3-optimization"]}
    router = MessageRouter(permissions)
    msg = Message(from_agent="s1-dev", to_agent="s2-coordination", content="Need help")
    assert router.is_allowed(msg) is True


def test_s1_cannot_message_s1():
    permissions = {"s1-dev": ["s2-coordination"], "s1-ops": ["s2-coordination"]}
    router = MessageRouter(permissions)
    msg = Message(from_agent="s1-dev", to_agent="s1-ops", content="Direct contact")
    assert router.is_allowed(msg) is False


def test_s2_can_message_everyone():
    permissions = {"s2-coordination": ["s1-dev", "s1-ops", "s3-optimization"]}
    router = MessageRouter(permissions)
    for target in ["s1-dev", "s1-ops", "s3-optimization"]:
        msg = Message(from_agent="s2-coordination", to_agent=target, content="Update")
        assert router.is_allowed(msg) is True


def test_router_queues_messages():
    permissions = {"s1-dev": ["s2-coordination"]}
    router = MessageRouter(permissions)
    msg = Message(from_agent="s1-dev", to_agent="s2-coordination", content="Request data")
    router.send(msg)

    inbox = router.get_inbox("s2-coordination")
    assert len(inbox) == 1
    assert inbox[0].content == "Request data"


def test_router_blocks_unauthorized():
    permissions = {"s1-dev": ["s2-coordination"]}
    router = MessageRouter(permissions)
    msg = Message(from_agent="s1-dev", to_agent="s3-optimization", content="Bypass")
    router.send(msg)  # Should be blocked

    inbox = router.get_inbox("s3-optimization")
    assert len(inbox) == 0


def test_router_wildcard_permissions():
    """s1-* pattern matches any S1 agent."""
    permissions = {"s2-coordination": ["s1-*", "s3-optimization"]}
    router = MessageRouter(permissions)
    msg = Message(from_agent="s2-coordination", to_agent="s1-product-dev", content="Task")
    assert router.is_allowed(msg) is True
```

**Step 2: Implement router**

```python
# src/viableos/runtime/router.py
"""Multi-agent message router using VSM communication matrix.

Enforces: S1 talks only to S2. S2 routes to all. S3* has read-only.
Permissions come from openclaw.json's agentToAgent.allow section.
"""
from __future__ import annotations

import fnmatch
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

log = logging.getLogger("viableos.runtime")


@dataclass
class Message:
    from_agent: str
    to_agent: str
    content: str
    msg_type: str = "request"  # request | response | alert | status
    priority: str = "normal"  # low | normal | high | critical
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    def __init__(self, permissions: dict[str, list[str]]) -> None:
        self._permissions = permissions
        self._inboxes: dict[str, list[Message]] = defaultdict(list)
        self._history: list[Message] = []
        self._blocked: list[Message] = []

    def is_allowed(self, msg: Message) -> bool:
        allowed_targets = self._permissions.get(msg.from_agent, [])
        for pattern in allowed_targets:
            if fnmatch.fnmatch(msg.to_agent, pattern):
                return True
        return False

    def send(self, msg: Message) -> bool:
        if not self.is_allowed(msg):
            log.warning("Blocked: %s -> %s (not in permission matrix)", msg.from_agent, msg.to_agent)
            self._blocked.append(msg)
            return False

        self._inboxes[msg.to_agent].append(msg)
        self._history.append(msg)
        log.info("Routed: %s -> %s (%s)", msg.from_agent, msg.to_agent, msg.msg_type)
        return True

    def get_inbox(self, agent_id: str) -> list[Message]:
        messages = list(self._inboxes.get(agent_id, []))
        self._inboxes[agent_id] = []
        return messages

    def peek_inbox(self, agent_id: str) -> list[Message]:
        return list(self._inboxes.get(agent_id, []))

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    @property
    def blocked_count(self) -> int:
        return len(self._blocked)

    @classmethod
    def from_openclaw_json(cls, openclaw_config: dict[str, Any]) -> MessageRouter:
        agent_to_agent = openclaw_config.get("agentToAgent", {})
        permissions = agent_to_agent.get("allow", {})
        return cls(permissions)
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_runtime_router.py -v`

```bash
git add src/viableos/runtime/router.py tests/test_runtime_router.py
git commit -m "feat(runtime): add VSM message router with permission matrix"
```

---

## Task 5: State Persistence (SQLite)

**Files:**
- Create: `src/viableos/runtime/state.py`
- Test: `tests/test_runtime_state.py`

Stores: agent sessions, message history, token usage per agent, budget consumed, **Operations Room state (signals, work packages, decisions)**.

> **Operations Room extension (see `2026-02-22-operations-room.md`):** In addition to the three base tables (sessions, token_usage, budgets), `StateStore.init()` must also create three Operations Room tables: `signals`, `work_packages`, and `decisions`. The schemas are defined in the Operations Room design document. The StateStore class gains additional methods for CRUD on these tables (`create_signal`, `get_signals`, `update_signal`, `create_work_package`, `get_backlog`, `update_work_package`, `get_active_by_agent`, `get_capacity`, `create_decision`, `get_pending_decisions`, `resolve_decision`).

**Step 1: Write the failing test**

```python
# tests/test_runtime_state.py
import tempfile
from pathlib import Path

import pytest
from viableos.runtime.state import StateStore


@pytest.mark.asyncio
async def test_store_and_retrieve_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = StateStore(Path(tmpdir) / "state.db")
        await store.init()

        await store.save_session("s1-dev", "session-1", [
            {"role": "user", "content": "Build the feature"},
            {"role": "assistant", "content": "On it."},
        ])

        messages = await store.load_session("s1-dev", "session-1")
        assert len(messages) == 2
        assert messages[0]["content"] == "Build the feature"

        await store.close()


@pytest.mark.asyncio
async def test_track_token_usage():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = StateStore(Path(tmpdir) / "state.db")
        await store.init()

        await store.record_usage("s1-dev", prompt_tokens=100, completion_tokens=50, cost_usd=0.002)
        await store.record_usage("s1-dev", prompt_tokens=200, completion_tokens=100, cost_usd=0.005)

        usage = await store.get_usage("s1-dev")
        assert usage["total_prompt_tokens"] == 300
        assert usage["total_completion_tokens"] == 150
        assert abs(usage["total_cost_usd"] - 0.007) < 0.0001

        await store.close()


@pytest.mark.asyncio
async def test_budget_tracking():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = StateStore(Path(tmpdir) / "state.db")
        await store.init()

        await store.set_budget("s1-dev", monthly_usd=50.0)
        await store.record_usage("s1-dev", prompt_tokens=1000, completion_tokens=500, cost_usd=10.0)

        status = await store.get_budget_status("s1-dev")
        assert status["monthly_usd"] == 50.0
        assert status["spent_usd"] == 10.0
        assert status["remaining_usd"] == 40.0
        assert status["percent_used"] == 20.0

        await store.close()
```

**Step 2: Implement state store**

```python
# src/viableos/runtime/state.py
"""SQLite-based state persistence for agent sessions and budget tracking."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                agent_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                messages TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS budgets (
                agent_id TEXT PRIMARY KEY,
                monthly_usd REAL NOT NULL
            );
        """)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def save_session(self, agent_id: str, session_id: str, messages: list[dict[str, Any]]) -> None:
        assert self._db
        await self._db.execute(
            "INSERT OR REPLACE INTO sessions (agent_id, session_id, messages) VALUES (?, ?, ?)",
            (agent_id, session_id, json.dumps(messages)),
        )
        await self._db.commit()

    async def load_session(self, agent_id: str, session_id: str) -> list[dict[str, Any]]:
        assert self._db
        async with self._db.execute(
            "SELECT messages FROM sessions WHERE agent_id = ? AND session_id = ?",
            (agent_id, session_id),
        ) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else []

    async def record_usage(self, agent_id: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
        assert self._db
        await self._db.execute(
            "INSERT INTO token_usage (agent_id, prompt_tokens, completion_tokens, cost_usd) VALUES (?, ?, ?, ?)",
            (agent_id, prompt_tokens, completion_tokens, cost_usd),
        )
        await self._db.commit()

    async def get_usage(self, agent_id: str) -> dict[str, Any]:
        assert self._db
        async with self._db.execute(
            "SELECT COALESCE(SUM(prompt_tokens), 0), COALESCE(SUM(completion_tokens), 0), COALESCE(SUM(cost_usd), 0) FROM token_usage WHERE agent_id = ?",
            (agent_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return {
                "total_prompt_tokens": row[0],
                "total_completion_tokens": row[1],
                "total_cost_usd": row[2],
            }

    async def set_budget(self, agent_id: str, monthly_usd: float) -> None:
        assert self._db
        await self._db.execute(
            "INSERT OR REPLACE INTO budgets (agent_id, monthly_usd) VALUES (?, ?)",
            (agent_id, monthly_usd),
        )
        await self._db.commit()

    async def get_budget_status(self, agent_id: str) -> dict[str, Any]:
        assert self._db
        usage = await self.get_usage(agent_id)
        async with self._db.execute(
            "SELECT monthly_usd FROM budgets WHERE agent_id = ?", (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            monthly = row[0] if row else 0.0

        spent = usage["total_cost_usd"]
        return {
            "monthly_usd": monthly,
            "spent_usd": spent,
            "remaining_usd": monthly - spent,
            "percent_used": round((spent / monthly * 100) if monthly > 0 else 0, 1),
        }

    async def get_all_usage(self) -> dict[str, dict[str, Any]]:
        assert self._db
        result: dict[str, dict[str, Any]] = {}
        async with self._db.execute(
            "SELECT agent_id, SUM(prompt_tokens), SUM(completion_tokens), SUM(cost_usd) FROM token_usage GROUP BY agent_id"
        ) as cursor:
            async for row in cursor:
                result[row[0]] = {
                    "total_prompt_tokens": row[1],
                    "total_completion_tokens": row[2],
                    "total_cost_usd": row[3],
                }
        return result
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_runtime_state.py -v`

```bash
git add src/viableos/runtime/state.py tests/test_runtime_state.py
git commit -m "feat(runtime): add SQLite state persistence for sessions and budget tracking"
```

---

## Task 6: Orchestrator (Loads Package, Starts All Agents)

**Files:**
- Create: `src/viableos/runtime/orchestrator.py`
- Test: `tests/test_runtime_orchestrator.py`

The Orchestrator:
1. Reads a generated ViableOS package directory
2. Parses `openclaw.json` for agent configs, models, permissions
3. Creates Agent instances per workspace
4. Sets up the MessageRouter with the communication matrix
5. Initializes the StateStore
6. Provides `run_agent(agent_id, task)` and `send_message(from, to, content)`

**Step 1: Write the failing test**

```python
# tests/test_runtime_orchestrator.py
import json
import tempfile
from pathlib import Path

import pytest
from viableos.runtime.orchestrator import Orchestrator


@pytest.fixture
def sample_package():
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = Path(tmpdir)

        # Create agent workspaces
        for agent_dir in ["s1-product-dev", "s2-coordinator"]:
            ws = pkg / "workspaces" / agent_dir
            ws.mkdir(parents=True)
            (ws / "SOUL.md").write_text(f"# {agent_dir}\nYou are {agent_dir}.")
            (ws / "SKILL.md").write_text("# Skills\n- Follow rules")

        # Create openclaw.json
        config = {
            "agents": [
                {"id": "s1-product-dev", "name": "Product Dev", "workspace": "workspaces/s1-product-dev", "model": "anthropic/claude-sonnet-4-6"},
                {"id": "s2-coordinator", "name": "Coordinator", "workspace": "workspaces/s2-coordinator", "model": "anthropic/claude-haiku-4-5"},
            ],
            "agentToAgent": {
                "enabled": True,
                "allow": {
                    "s1-product-dev": ["s2-coordinator"],
                    "s2-coordinator": ["s1-product-dev"],
                },
            },
        }
        (pkg / "openclaw.json").write_text(json.dumps(config))

        yield pkg


@pytest.mark.asyncio
async def test_orchestrator_loads_package(sample_package):
    orch = await Orchestrator.from_package(sample_package)
    assert "s1-product-dev" in orch.agent_ids
    assert "s2-coordinator" in orch.agent_ids
    assert len(orch.agent_ids) == 2


@pytest.mark.asyncio
async def test_orchestrator_respects_permissions(sample_package):
    orch = await Orchestrator.from_package(sample_package)
    assert orch.router.is_allowed(
        type("M", (), {"from_agent": "s1-product-dev", "to_agent": "s2-coordinator"})()
    )
    assert not orch.router.is_allowed(
        type("M", (), {"from_agent": "s1-product-dev", "to_agent": "s1-product-dev"})()
    )


@pytest.mark.asyncio
async def test_orchestrator_status(sample_package):
    orch = await Orchestrator.from_package(sample_package)
    status = await orch.get_status()
    assert "agents" in status
    assert len(status["agents"]) == 2
    await orch.shutdown()
```

**Step 2: Implement orchestrator**

```python
# src/viableos/runtime/orchestrator.py
"""Top-level orchestrator — loads a ViableOS package and manages all agents."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from viableos.runtime.agent import Agent, AgentConfig, AgentResult
from viableos.runtime.llm import LLMClient
from viableos.runtime.router import Message, MessageRouter
from viableos.runtime.state import StateStore

log = logging.getLogger("viableos.runtime")


class Orchestrator:
    def __init__(
        self,
        agents: dict[str, Agent],
        router: MessageRouter,
        state: StateStore,
        llm: LLMClient,
        package_path: Path,
    ) -> None:
        self.agents = agents
        self.router = router
        self.state = state
        self.llm = llm
        self.package_path = package_path
        self._event_handlers: list[Any] = []

    @classmethod
    async def from_package(
        cls, package_path: Path, llm: LLMClient | None = None
    ) -> Orchestrator:
        package_path = Path(package_path)
        config_path = package_path / "openclaw.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No openclaw.json found in {package_path}")

        config = json.loads(config_path.read_text())
        shared_llm = llm or LLMClient()

        # State store
        state = StateStore(package_path / ".viableos-state.db")
        await state.init()

        # Message router
        agent_to_agent = config.get("agentToAgent", {})
        permissions = agent_to_agent.get("allow", {})
        router = MessageRouter(permissions)

        # Create agents
        agents: dict[str, Agent] = {}
        for agent_cfg in config.get("agents", []):
            agent_id = agent_cfg["id"]
            workspace = package_path / agent_cfg["workspace"]
            if not workspace.exists():
                log.warning("Workspace not found for %s: %s", agent_id, workspace)
                continue

            ac = AgentConfig(
                agent_id=agent_id,
                name=agent_cfg.get("name", agent_id),
                model=agent_cfg["model"],
                workspace=workspace,
                fallbacks=agent_cfg.get("fallbacks", []),
            )
            agents[agent_id] = Agent(ac, llm=shared_llm)

            # Set budget if available
            # Budget per agent is approximated from the allocation percentages
            # In a real deployment, this comes from the budget calculator

        return cls(
            agents=agents,
            router=router,
            state=state,
            llm=shared_llm,
            package_path=package_path,
        )

    @property
    def agent_ids(self) -> list[str]:
        return list(self.agents.keys())

    async def run_agent(self, agent_id: str, task: str) -> AgentResult:
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_id}")

        result = await agent.run(task)

        # Persist usage
        await self.state.record_usage(
            agent_id,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
        )

        return result

    def send_message(self, from_agent: str, to_agent: str, content: str, msg_type: str = "request") -> bool:
        msg = Message(from_agent=from_agent, to_agent=to_agent, content=content, msg_type=msg_type)
        return self.router.send(msg)

    async def get_status(self) -> dict[str, Any]:
        usage = await self.state.get_all_usage()
        return {
            "package": str(self.package_path),
            "agents": [
                {
                    "id": aid,
                    "name": agent.config.name,
                    "model": agent.config.model,
                    "usage": usage.get(aid, {"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_cost_usd": 0}),
                }
                for aid, agent in self.agents.items()
            ],
            "llm_stats": self.llm.get_stats(),
            "messages_routed": len(self.router.history),
            "messages_blocked": self.router.blocked_count,
        }

    async def shutdown(self) -> None:
        await self.state.close()
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_runtime_orchestrator.py -v`

```bash
git add src/viableos/runtime/orchestrator.py tests/test_runtime_orchestrator.py
git commit -m "feat(runtime): add Orchestrator that loads packages and manages agents"
```

---

## Task 7: CLI Command `viableos run`

**Files:**
- Modify: `src/viableos/cli.py` — add `run` command

**Step 1: Add the CLI command**

```python
# Add to src/viableos/cli.py

@main.command()
@click.argument("package_path", type=click.Path(exists=True))
@click.option("--agent", "-a", help="Run a specific agent (default: interactive selection)")
@click.option("--task", "-t", help="Task to send to the agent")
def run(package_path: str, agent: str | None, task: str | None) -> None:
    """Run a ViableOS agent organization from a generated package."""
    import asyncio
    from viableos.runtime.orchestrator import Orchestrator

    async def _run() -> None:
        console.print(f"\n[bold]Loading ViableOS package...[/bold] {package_path}")
        orch = await Orchestrator.from_package(Path(package_path))

        console.print(f"  [green]✓[/green] {len(orch.agent_ids)} agents loaded")
        for aid in orch.agent_ids:
            a = orch.agents[aid]
            console.print(f"    {aid}: {a.config.name} ({a.config.model})")

        target = agent
        if not target:
            console.print("\n[bold]Available agents:[/bold]")
            for i, aid in enumerate(orch.agent_ids, 1):
                console.print(f"  {i}. {aid}")
            choice = click.prompt("Select agent number", type=int, default=1)
            target = orch.agent_ids[choice - 1]

        user_task = task
        if not user_task:
            user_task = click.prompt(f"\n[{target}] Enter task")

        console.print(f"\n[bold]Running {target}...[/bold]")
        result = await orch.run_agent(target, user_task)

        console.print(Panel(
            result.content or "(no output)",
            title=f"[bold]{target} Response[/bold]",
        ))

        table = Table(title="Stats")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Iterations", str(result.iterations))
        table.add_row("Prompt tokens", f"{result.prompt_tokens:,}")
        table.add_row("Completion tokens", f"{result.completion_tokens:,}")
        table.add_row("Cost", f"${result.cost_usd:.4f}")
        table.add_row("Tool calls", str(len(result.tool_calls_made)))
        if result.stopped_reason != "completed":
            table.add_row("Stopped", result.stopped_reason)
        console.print(table)

        # Interactive loop
        while True:
            next_task = click.prompt(f"\n[{target}] Next task (or 'quit')", default="quit")
            if next_task.lower() in ("quit", "exit", "q"):
                break
            result = await orch.run_agent(target, next_task)
            console.print(Panel(result.content or "(no output)", title=f"[bold]{target}[/bold]"))
            console.print(f"  [dim]{result.iterations} iterations, ${result.cost_usd:.4f}[/dim]")

        status = await orch.get_status()
        console.print(f"\n[bold]Session summary:[/bold]")
        console.print(f"  Total LLM calls: {status['llm_stats']['call_count']}")
        console.print(f"  Total cost: [green]${status['llm_stats']['total_cost_usd']:.4f}[/green]")
        console.print(f"  Messages routed: {status['messages_routed']}")
        console.print(f"  Messages blocked: {status['messages_blocked']}")

        await orch.shutdown()

    asyncio.run(_run())
```

**Step 2: Test manually**

Run: `viableos run ./viableos-openclaw/`
Expected: Interactive agent selection and task execution

**Step 3: Commit**

```bash
git add src/viableos/cli.py
git commit -m "feat(cli): add 'viableos run' command for interactive agent execution"
```

---

## Task 8: API Endpoint + WebSocket for Live Streaming

**Files:**
- Modify: `src/viableos/api/routes.py` — add runtime endpoints
- Modify: `src/viableos/api/models.py` — add response models
- Modify: `src/viableos/api/main.py` — add WebSocket route

**Step 1: Add REST endpoints**

Add to `routes.py`:
- `POST /api/runtime/start` — load a package (from generated output or uploaded config)
- `POST /api/runtime/run` — send a task to an agent
- `GET /api/runtime/status` — get all agent stats and budget usage
- `GET /api/runtime/agents` — list loaded agents

**Step 2: Add Operations Room REST endpoints**

> **Operations Room extension (see `2026-02-22-operations-room.md`):** All under `/api/ops/` prefix.

Add to `routes.py`:

**Signals:**
- `POST /api/ops/signals` — create a new signal (from agent or human)
- `GET /api/ops/signals` — list signals (query params: `?status=new&limit=50`)
- `PATCH /api/ops/signals/{id}` — update signal (triage, dismiss)
- `POST /api/ops/signals/{id}/convert` — convert signal to work package (creates WP, links signal)

**Work Packages:**
- `POST /api/ops/workpackages` — create work package directly (without signal)
- `GET /api/ops/backlog` — list backlog (query params: `?status=queued&assigned_to=s1-dev`)
- `PATCH /api/ops/workpackages/{id}` — update work package (priority, status, assignment)
- `GET /api/ops/workpackages/{id}` — get single work package with full detail
- `GET /api/ops/capacity` — per-agent capacity summary

**Decisions:**
- `GET /api/ops/decisions` — list pending decisions
- `POST /api/ops/decisions/{id}/resolve` — submit decision (body: `{choice, rationale}`)

**Step 3: Add WebSocket for streaming**

Add to `main.py`:
- `WS /ws/runtime` — streams agent events (llm_call, tool_call, tool_result, response) in real time

```python
# Sketch for WebSocket handler
from fastapi import WebSocket

@app.websocket("/ws/runtime")
async def runtime_ws(websocket: WebSocket):
    await websocket.accept()
    # Register event handler that forwards to WebSocket
    # Events: {"agent_id": "s1-dev", "type": "tool_call", "tool": "read_file", ...}
    while True:
        data = await websocket.receive_text()
        # Parse command: {"action": "run", "agent_id": "s1-dev", "task": "..."}
        # Execute and stream events back
```

**Step 4: Add Operations Room WebSocket events**

> Extend the existing `/ws/runtime` WebSocket to push additional event types for Operations Room updates:

```json
{"type": "signal_created", "signal": {"id": "...", "source": "s4", "title": "..."}}
{"type": "work_package_updated", "work_package": {"id": "...", "status": "active", "assigned_to": "s1-dev"}}
{"type": "decision_created", "decision": {"id": "...", "title": "...", "urgency": "high"}}
{"type": "decision_resolved", "decision": {"id": "...", "decision": "approve"}}
{"type": "agent_status_changed", "agent_id": "s1-dev", "status": "working", "task": "Implement feature #12"}
```

**Step 5: Commit**

```bash
git add src/viableos/api/
git commit -m "feat(api): add runtime REST endpoints, Operations Room API, and WebSocket streaming"
```

---

## Task 9: Frontend — Operations Room

> **Replaces the originally planned "Live Agent Panel" (see `2026-02-22-operations-room.md`).** The Operations Room is the primary UI when a runtime is active. AgentTerminal becomes a sub-panel opened from the SystemStatus component.

**Files:**
- Create: `frontend/src/pages/OperationsRoomPage.tsx` — main page layout (2x2 grid)
- Create: `frontend/src/components/runtime/SignalInbox.tsx` — signal list with triage actions
- Create: `frontend/src/components/runtime/BacklogBoard.tsx` — 3-column kanban (Triage / Queued / Active)
- Create: `frontend/src/components/runtime/SystemStatus.tsx` — per-agent health cards + capacity bars
- Create: `frontend/src/components/runtime/PendingDecisions.tsx` — decision cards with inline actions
- Create: `frontend/src/components/runtime/AgentTerminal.tsx` — live agent output (slide-over panel)
- Modify: `frontend/src/store/useConfigStore.ts` — add Operations Room state (signals, workPackages, decisions, agentStatuses)

**Components:**

- `OperationsRoomPage`: 2x2 grid on desktop, stacked on mobile. Contains SignalInbox (top-left), BacklogBoard (top-right), SystemStatus (bottom-left), PendingDecisions (bottom-right).
- `SignalInbox`: Scrollable list of signals. Each shows source icon, title, urgency badge, timestamp, affected areas. Actions: "Triage" (opens priority/assignment popover), "Dismiss". "New Signal" button for manual founder input. Filter tabs: All | New | Triaged | Dismissed.
- `BacklogBoard`: Three columns — Triage (unconverted signals), Queued (prioritized work packages with drag-and-drop reorder), Active (in-progress work packages grouped by agent). Cards show title, priority number, assigned agent chip, estimated effort.
- `SystemStatus`: One card per agent with health dot (green=idle, blue=working, yellow=warning, red=error, gray=stopped), current task, token budget mini-bar. Click card to open AgentTerminal as slide-over. Summary bar: total budget spent / total budget.
- `PendingDecisions`: Cards sorted by urgency then age. Each shows decision type badge, title, context (expandable), source agent, and action buttons (approve/reject/defer) with optional rationale text field.
- `AgentTerminal`: Shows live agent output, tool calls, cost per interaction. Opened from SystemStatus as a slide-over panel.

**Step 1: Build components, verify `npx tsc --noEmit`**

**Step 2: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add Operations Room page with signal inbox, backlog, system status, and pending decisions"
```

---

## Task 10: Operations Room — Agent Integration (Closed Loop)

> **Depends on:** Tasks 3 (agent.py), 5 (state.py), 6 (orchestrator.py), 8 (API). **Design:** `2026-02-22-operations-room.md`

**Goal:** Wire metasystem agents (S4, S3*, S3) to automatically generate signals, triage work, and process work packages — making the Operations Room a live, autonomous steering system rather than a manual task board.

**Files:**
- Modify: `src/viableos/runtime/tools.py` — add Operations Room tools to the ToolRegistry
- Modify: agent SKILL.md templates — add Operations Room instructions

**Step 1: Register Operations Room tools**

Add to `ToolRegistry`:

```python
ops_tools = [
    {
        "type": "function",
        "function": {
            "name": "create_signal",
            "description": "Create a new signal in the Operations Room inbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "affected_areas": {"type": "array", "items": {"type": "string"}},
                    "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                },
                "required": ["title", "description", "affected_areas", "urgency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_decision",
            "description": "Escalate a decision to the human via the Operations Room",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "context": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                },
                "required": ["title", "context", "options", "urgency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_work_package",
            "description": "Update the status of a work package (for S1 agents reporting progress)",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_package_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "blocked", "done"]},
                    "result_summary": {"type": "string"}
                },
                "required": ["work_package_id", "status"]
            }
        }
    }
]
```

**Tool availability by agent role:**
- **S4 (Scout):** `create_signal` — creates signals when detecting environment changes
- **S3* (Audit):** `create_signal`, `create_decision` — creates signals for findings, escalates critical issues
- **S3 (Controller):** all ops tools — triages signals, creates work packages, manages backlog
- **S1 (Operational):** `update_work_package` — reports task progress and completion
- **S2 (Coordinator):** no ops tools (S2 routes messages, doesn't create work)

**Step 2: Update SKILL.md templates**

Add Operations Room instructions to the generated SKILL.md files so agents know when and how to use these tools. The instructions vary by role (see Operations Room design document, "Agent Integration" section).

**Step 3: Wire tool execution in agent.py**

When an agent calls an ops tool, the tool handler must:
1. Call the corresponding StateStore method (e.g., `state.create_signal(...)`)
2. Push a WebSocket event (e.g., `signal_created`) so the frontend updates in real time
3. Return a confirmation to the agent

**Step 4: Commit**

```bash
git add src/viableos/runtime/tools.py
git commit -m "feat(runtime): add Operations Room tools for closed-loop agent integration"
```

---

## Summary

| Task | Module | What It Does | Estimated Effort |
|---|---|---|---|
| 1 | `runtime/llm.py` | LiteLLM wrapper with fallbacks + cost tracking | 2-3 hours |
| 2 | `runtime/tools.py` | Sandboxed filesystem tools + registry | 2-3 hours |
| 3 | `runtime/agent.py` | Agent loop: system prompt → LLM → tool calls → repeat | 3-4 hours |
| 4 | `runtime/router.py` | VSM message routing (S1→S2 only, permission matrix) | 2-3 hours |
| 5 | `runtime/state.py` | SQLite persistence for sessions, budget tracking, **+ Operations Room tables** | 3-4 hours |
| 6 | `runtime/orchestrator.py` | Load package, create agents, wire everything | 3-4 hours |
| 7 | `cli.py` | `viableos run` interactive CLI | 1-2 hours |
| 8 | `api/` | REST + WebSocket for live agent streaming **+ Operations Room endpoints** | 4-5 hours |
| 9 | `frontend/` | **Operations Room** — signal inbox, backlog, system status, pending decisions | 6-8 hours |
| 10 | `runtime/tools.py` | **Operations Room agent integration** — closed-loop signal/WP tools | 2-3 hours |

**Total: ~30-40 hours of focused work = 5-6 days with AI assistance**

After this, `viableos run ./viableos-openclaw/` starts your entire organization. The Operations Room shows everything in one place: incoming signals, prioritized backlog, live agent status, and pending decisions. Agents autonomously detect changes, create work packages, and execute them — with the human steering from the cockpit.
