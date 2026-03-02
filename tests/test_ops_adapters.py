"""Tests for the Operations Room adapters and API routes."""

import pytest

from viableos.ops.adapter import RuntimeAdapter
from viableos.ops.openclaw_adapter import OpenClawAdapter, _map_openclaw_status
from viableos.ops.langgraph_adapter import LangGraphAdapter


# ── Abstract Adapter ─────────────────────────────────────────


class TestRuntimeAdapterABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            RuntimeAdapter()

    def test_openclaw_is_runtime_adapter(self):
        adapter = OpenClawAdapter()
        assert isinstance(adapter, RuntimeAdapter)

    def test_langgraph_is_runtime_adapter(self):
        adapter = LangGraphAdapter()
        assert isinstance(adapter, RuntimeAdapter)


# ── OpenClaw Adapter ─────────────────────────────────────────


class TestOpenClawAdapter:
    def test_initial_state(self):
        adapter = OpenClawAdapter()
        assert adapter._client is None
        assert adapter._base_url == ""

    @pytest.mark.asyncio
    async def test_connect_fails_on_bad_url(self):
        adapter = OpenClawAdapter()
        result = await adapter.connect("http://localhost:99999", "fake-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agents_without_connection(self):
        adapter = OpenClawAdapter()
        agents = await adapter.get_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_get_activity_without_connection(self):
        adapter = OpenClawAdapter()
        activity = await adapter.get_activity()
        assert activity == []

    @pytest.mark.asyncio
    async def test_get_signals_without_connection(self):
        adapter = OpenClawAdapter()
        signals = await adapter.get_signals()
        assert signals == []

    @pytest.mark.asyncio
    async def test_get_work_packages_without_connection(self):
        adapter = OpenClawAdapter()
        wp = await adapter.get_work_packages()
        assert wp == []

    @pytest.mark.asyncio
    async def test_get_decisions_without_connection(self):
        adapter = OpenClawAdapter()
        decisions = await adapter.get_decisions()
        assert decisions == []

    @pytest.mark.asyncio
    async def test_resolve_decision_without_connection(self):
        adapter = OpenClawAdapter()
        result = await adapter.resolve_decision("test-id", "approve")
        assert "error" in result


class TestOpenClawStatusMapping:
    def test_active_maps_to_online(self):
        assert _map_openclaw_status("active") == "online"

    def test_running_maps_to_working(self):
        assert _map_openclaw_status("running") == "working"

    def test_error_maps_to_error(self):
        assert _map_openclaw_status("error") == "error"

    def test_idle_maps_to_online(self):
        assert _map_openclaw_status("idle") == "online"

    def test_stopped_maps_to_offline(self):
        assert _map_openclaw_status("stopped") == "offline"

    def test_unknown_maps_to_offline(self):
        assert _map_openclaw_status("something_else") == "offline"

    def test_case_insensitive(self):
        assert _map_openclaw_status("ACTIVE") == "online"
        assert _map_openclaw_status("Running") == "working"


# ── LangGraph Adapter ────────────────────────────────────────


class TestLangGraphAdapter:
    def test_initial_state(self):
        adapter = LangGraphAdapter()
        assert adapter._client is None
        assert adapter._base_url == ""

    @pytest.mark.asyncio
    async def test_connect_fails_on_bad_url(self):
        adapter = LangGraphAdapter()
        result = await adapter.connect("http://localhost:99999", "fake-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agents_without_connection(self):
        adapter = LangGraphAdapter()
        agents = await adapter.get_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_get_activity_without_connection(self):
        adapter = LangGraphAdapter()
        activity = await adapter.get_activity()
        assert activity == []

    @pytest.mark.asyncio
    async def test_get_signals_without_connection(self):
        """LangGraph has no native signals — always returns empty."""
        adapter = LangGraphAdapter()
        signals = await adapter.get_signals()
        assert signals == []

    @pytest.mark.asyncio
    async def test_get_work_packages_without_connection(self):
        adapter = LangGraphAdapter()
        wp = await adapter.get_work_packages()
        assert wp == []

    @pytest.mark.asyncio
    async def test_get_decisions_without_connection(self):
        adapter = LangGraphAdapter()
        decisions = await adapter.get_decisions()
        assert decisions == []

    @pytest.mark.asyncio
    async def test_resolve_decision_without_connection(self):
        adapter = LangGraphAdapter()
        result = await adapter.resolve_decision("test-id", "approve")
        assert "error" in result


# ── API Routes (FastAPI TestClient) ──────────────────────────


class TestOpsRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from viableos.api.main import app
        return TestClient(app)

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_agents_without_connection_returns_400(self, client):
        resp = client.get("/api/ops/agents")
        assert resp.status_code == 400
        assert "Not connected" in resp.json()["detail"]

    def test_activity_without_connection_returns_400(self, client):
        resp = client.get("/api/ops/activity")
        assert resp.status_code == 400

    def test_signals_without_connection_returns_400(self, client):
        resp = client.get("/api/ops/signals")
        assert resp.status_code == 400

    def test_workpackages_without_connection_returns_400(self, client):
        resp = client.get("/api/ops/workpackages")
        assert resp.status_code == 400

    def test_decisions_without_connection_returns_400(self, client):
        resp = client.get("/api/ops/decisions")
        assert resp.status_code == 400

    def test_connect_invalid_runtime(self, client):
        resp = client.post("/api/ops/connect", json={
            "runtime": "invalid",
            "url": "http://localhost:1234",
            "api_key": "test",
        })
        assert resp.status_code == 400

    def test_connect_openclaw_bad_url(self, client):
        resp = client.post("/api/ops/connect", json={
            "runtime": "openclaw",
            "url": "http://localhost:99999",
            "api_key": "test",
        })
        data = resp.json()
        assert data["connected"] is False

    def test_disconnect_without_connection(self, client):
        resp = client.post("/api/ops/disconnect")
        assert resp.status_code == 200
        assert resp.json()["disconnected"] is True


# ── Chat Routes ──────────────────────────────────────────────


class TestChatRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from viableos.api.main import app
        return TestClient(app)

    def test_chat_start(self, client):
        resp = client.post("/api/chat/start", json={
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key": "sk-test-not-real",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 10

    def test_chat_history_not_found(self, client):
        resp = client.get("/api/chat/history/nonexistent-id")
        assert resp.status_code == 404

    def test_chat_history_for_valid_session(self, client):
        # Create session
        start_resp = client.post("/api/chat/start", json={
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key": "sk-test",
        })
        session_id = start_resp.json()["session_id"]

        # Get history (should be empty — system message excluded)
        resp = client.get(f"/api/chat/history/{session_id}")
        assert resp.status_code == 200
        # History should have 0 messages since system is excluded by get_history
        history = resp.json()
        assert isinstance(history, list)

    def test_chat_finalize_missing_session(self, client):
        resp = client.post("/api/chat/finalize", json={"session_id": "bad-id"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["assessment"] is None

    def test_chat_finalize_empty_session_id(self, client):
        resp = client.post("/api/chat/finalize", json={})
        assert resp.status_code == 400


# ── Assessment Transform Route ───────────────────────────────


class TestAssessmentTransformRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from viableos.api.main import app
        return TestClient(app)

    def test_transform_minimal_assessment(self, client):
        assessment = {
            "system_name": "Test System",
            "purpose": "Test purpose",
            "team": {"size": 1},
            "recursion_levels": {
                "level_0": {
                    "operational_units": [
                        {"id": "dev", "name": "Development", "description": "Build stuff", "priority": 1}
                    ]
                }
            },
            "metasystem": {
                "s2_coordination": {"tasks": []},
                "s3_optimization": {"tasks": []},
                "s3_star_audit": {"tasks": []},
                "s4_intelligence": {"tasks": []},
                "s5_policy": {"policies": []},
            },
        }
        resp = client.post("/api/assessment/transform", json=assessment)
        assert resp.status_code == 200
        data = resp.json()
        assert "viable_system" in data
        assert data["viable_system"]["name"] == "Test System"
        assert len(data["viable_system"]["system_1"]) == 1


# ── LangGraph Generate Route ────────────────────────────────


class TestLanggraphGenerateRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from viableos.api.main import app
        return TestClient(app)

    def test_generate_langgraph_returns_zip(self, client):
        config = {
            "viable_system": {
                "name": "Test LG",
                "identity": {"purpose": "Test"},
                "system_1": [{"name": "Unit1", "purpose": "Do work"}],
                "budget": {"monthly_usd": 100, "strategy": "balanced"},
            }
        }
        resp = client.post("/api/generate/langgraph", json=config)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert len(resp.content) > 100  # ZIP file has content

    def test_generate_langgraph_invalid_config(self, client):
        resp = client.post("/api/generate/langgraph", json={"invalid": True})
        assert resp.status_code == 422
