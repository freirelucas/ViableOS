"""Tests for the LangGraph deployment package generator."""

import json
from pathlib import Path

from viableos.langgraph_generator import generate_langgraph_package, _model_to_langchain
from viableos.schema import validate


def _full_config() -> dict:
    return {
        "viable_system": {
            "name": "Test SaaS",
            "runtime": "langgraph",
            "identity": {
                "purpose": "Build great software",
                "values": ["Ship fast", "User first"],
                "never_do": ["Delete production data", "Send emails without approval"],
                "decisions_requiring_human": ["deployments"],
            },
            "budget": {"monthly_usd": 200, "strategy": "balanced"},
            "model_routing": {"provider_preference": "anthropic"},
            "human_in_the_loop": {
                "notification_channel": "whatsapp",
                "approval_required": ["deployments"],
                "review_required": ["features"],
                "emergency_alerts": ["data_leak"],
            },
            "system_1": [
                {"name": "Dev", "purpose": "Build software", "autonomy": "Fix bugs alone", "tools": ["github"], "model": "openai/gpt-5.1-codex", "weight": 8},
                {"name": "Sales", "purpose": "Close deals", "tools": ["crm"], "weight": 3},
            ],
            "system_2": {
                "coordination_rules": [
                    {"trigger": "Dev deploys", "action": "Notify Sales"},
                ]
            },
            "system_3": {
                "reporting_rhythm": "weekly",
                "resource_allocation": "Dev 70%, Sales 30%",
            },
            "system_3_star": {
                "checks": [
                    {"name": "Quality", "target": "Dev", "method": "Review commits"},
                ],
                "on_failure": "Alert human",
            },
            "system_4": {
                "monitoring": {
                    "competitors": ["Rival"],
                    "technology": ["AI models"],
                    "regulation": ["GDPR"],
                }
            },
        }
    }


def test_config_validates():
    errors = validate(_full_config())
    assert errors == []


def test_generates_output_directory(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    assert out.exists()
    assert out.is_dir()


def test_generates_graph_py(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    graph_file = out / "graph.py"
    assert graph_file.exists()
    content = graph_file.read_text()
    assert "StateGraph" in content
    assert "AgentState" in content
    assert "build_graph" in content


def test_generates_state_py(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    state_file = out / "state.py"
    assert state_file.exists()
    content = state_file.read_text()
    assert "AgentState" in content
    assert "TypedDict" in content
    assert "messages" in content
    assert "dev_status" in content
    assert "sales_status" in content


def test_generates_requirements_txt(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    req_file = out / "requirements.txt"
    assert req_file.exists()
    content = req_file.read_text()
    assert "langgraph" in content
    assert "langchain-anthropic" in content
    assert "langchain-openai" in content


def test_generates_langgraph_json(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    lg_file = out / "langgraph.json"
    assert lg_file.exists()
    data = json.loads(lg_file.read_text())
    assert "graphs" in data
    assert "agent" in data["graphs"]
    assert "graph.py" in data["graphs"]["agent"]


def test_generates_env_example(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    env_file = out / ".env.example"
    assert env_file.exists()
    content = env_file.read_text()
    assert "ANTHROPIC_API_KEY" in content
    assert "OPENAI_API_KEY" in content


def test_generates_agent_directories(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    agents_dir = out / "agents"
    assert agents_dir.exists()
    expected_dirs = {"s1_dev", "s1_sales", "s2_coordinator", "s3_optimizer", "s3star_auditor", "s4_scout", "s5_policy"}
    actual_dirs = {d.name for d in agents_dir.iterdir() if d.is_dir()}
    assert expected_dirs == actual_dirs


def test_agent_dirs_have_system_prompt(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    for agent_dir in (out / "agents").iterdir():
        if agent_dir.is_dir():
            assert (agent_dir / "system_prompt.md").exists(), f"Missing system_prompt.md in {agent_dir.name}"


def test_s1_system_prompt_has_identity(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    prompt = (out / "agents" / "s1_dev" / "system_prompt.md").read_text()
    assert "Dev" in prompt
    assert "Build software" in prompt
    assert "github" in prompt


def test_s2_system_prompt_has_units(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    prompt = (out / "agents" / "s2_coordinator" / "system_prompt.md").read_text()
    assert "Dev" in prompt
    assert "Sales" in prompt


def test_shared_directory_exists(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    shared = out / "shared"
    assert shared.exists()
    assert (shared / "org_memory.md").exists()
    assert (shared / "coordination_rules.md").exists()


def test_org_memory_has_system_name(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    mem = (out / "shared" / "org_memory.md").read_text()
    assert "Test SaaS" in mem


def test_coordination_rules_file(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    rules = (out / "shared" / "coordination_rules.md").read_text()
    assert "Coordination Rules" in rules


def test_graph_py_has_all_nodes(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    content = (out / "graph.py").read_text()
    assert "s1_dev" in content
    assert "s1_sales" in content
    assert "s2_coordinator" in content
    assert "s3_optimizer" in content
    assert "s3star_auditor" in content
    assert "s4_scout" in content
    assert "s5_policy" in content
    assert "supervisor" in content


def test_graph_py_has_model_assignments(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    content = (out / "graph.py").read_text()
    assert "MODELS" in content
    assert "gpt-5.1-codex" in content  # Dev's explicit model


def test_graph_py_has_entry_point(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    content = (out / "graph.py").read_text()
    assert "set_entry_point" in content


def test_graph_py_has_conditional_edges(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    content = (out / "graph.py").read_text()
    assert "add_conditional_edges" in content


def test_graph_py_has_memory_saver(tmp_path: Path):
    out = generate_langgraph_package(_full_config(), tmp_path / "pkg")
    content = (out / "graph.py").read_text()
    assert "MemorySaver" in content
    assert "checkpointer" in content


def test_overwrites_existing_output(tmp_path: Path):
    out_dir = tmp_path / "pkg"
    generate_langgraph_package(_full_config(), out_dir)
    out = generate_langgraph_package(_full_config(), out_dir)
    assert out.exists()
    assert (out / "graph.py").exists()


# ── Model Mapping ────────────────────────────────────────────


class TestModelToLangchain:
    def test_anthropic_model(self):
        cls, model = _model_to_langchain("claude-sonnet-4-6")
        assert cls == "ChatAnthropic"
        assert model == "claude-sonnet-4-6"

    def test_openai_model(self):
        cls, model = _model_to_langchain("gpt-5.1")
        assert cls == "ChatOpenAI"
        assert model == "gpt-5.1"

    def test_gemini_model(self):
        cls, model = _model_to_langchain("gemini-3-pro")
        assert cls == "ChatGoogleGenerativeAI"
        assert model == "gemini-3-pro"

    def test_deepseek_uses_openai_compat(self):
        cls, model = _model_to_langchain("deepseek-v3.2")
        assert cls == "ChatOpenAI"

    def test_grok_uses_openai_compat(self):
        cls, model = _model_to_langchain("grok-4")
        assert cls == "ChatOpenAI"

    def test_o3_model(self):
        cls, model = _model_to_langchain("o3")
        assert cls == "ChatOpenAI"
