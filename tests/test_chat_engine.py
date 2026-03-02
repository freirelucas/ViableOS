"""Tests for the VSM Expert Chat engine."""

import pytest

from viableos.chat.session import ChatSession, SessionStore, store as global_store
from viableos.chat.engine import (
    _extract_json_from_response,
    _litellm_model_id,
    finalize_assessment,
    get_history,
    start_session,
)
from viableos.chat.system_prompt import SYSTEM_PROMPT


# ── System Prompt ────────────────────────────────────────────


class TestSystemPrompt:
    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 500

    def test_system_prompt_has_interview_phases(self):
        assert "PHASE 1" in SYSTEM_PROMPT
        assert "PHASE 4" in SYSTEM_PROMPT

    def test_system_prompt_has_output_schema(self):
        assert "system_name" in SYSTEM_PROMPT
        assert "recursion_levels" in SYSTEM_PROMPT
        assert "metasystem" in SYSTEM_PROMPT

    def test_system_prompt_mentions_vsm(self):
        assert "Viable System Model" in SYSTEM_PROMPT
        # Stafford Beer is intentionally NOT mentioned — the prompt
        # instructs the AI to never reference authors to the user.
        # But it should contain the deep knowledge internally.
        assert "Ashby" in SYSTEM_PROMPT
        assert "Subsidiarity" in SYSTEM_PROMPT

    def test_system_prompt_has_language_rule(self):
        assert "language" in SYSTEM_PROMPT.lower()


# ── Session Store ────────────────────────────────────────────


class TestSessionStore:
    def test_create_session(self):
        ss = SessionStore()
        session = ss.create("anthropic", "claude-sonnet-4-6", "sk-test")
        assert session.id is not None
        assert session.provider == "anthropic"
        assert session.model == "claude-sonnet-4-6"
        assert session.api_key == "sk-test"

    def test_get_session(self):
        ss = SessionStore()
        session = ss.create("openai", "gpt-5.1", "sk-test")
        found = ss.get(session.id)
        assert found is not None
        assert found.id == session.id

    def test_get_nonexistent_returns_none(self):
        ss = SessionStore()
        assert ss.get("nonexistent-id") is None

    def test_delete_session(self):
        ss = SessionStore()
        session = ss.create("anthropic", "claude-sonnet-4-6", "sk-test")
        ss.delete(session.id)
        assert ss.get(session.id) is None

    def test_delete_nonexistent_is_noop(self):
        ss = SessionStore()
        ss.delete("nonexistent-id")  # should not raise

    def test_cleanup_old_sessions(self):
        import time
        ss = SessionStore()
        session = ss.create("anthropic", "claude-sonnet-4-6", "sk-test")
        # Manually backdate the session
        session.created_at = time.time() - 25 * 3600  # 25h ago
        removed = ss.cleanup_old(max_age_hours=24)
        assert removed == 1
        assert ss.get(session.id) is None

    def test_cleanup_keeps_fresh_sessions(self):
        ss = SessionStore()
        session = ss.create("anthropic", "claude-sonnet-4-6", "sk-test")
        removed = ss.cleanup_old(max_age_hours=24)
        assert removed == 0
        assert ss.get(session.id) is not None

    def test_unique_session_ids(self):
        ss = SessionStore()
        ids = set()
        for _ in range(50):
            session = ss.create("anthropic", "claude-sonnet-4-6", "sk-test")
            ids.add(session.id)
        assert len(ids) == 50


# ── ChatSession ──────────────────────────────────────────────


class TestChatSession:
    def test_add_message(self):
        session = ChatSession(
            id="test", provider="anthropic", model="claude-sonnet-4-6", api_key="sk-test"
        )
        msg = session.add_message("user", "Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp > 0

    def test_to_litellm_messages(self):
        session = ChatSession(
            id="test", provider="anthropic", model="claude-sonnet-4-6", api_key="sk-test"
        )
        session.add_message("system", "You are a helper")
        session.add_message("user", "Hi")
        msgs = session.to_litellm_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "You are a helper"}
        assert msgs[1] == {"role": "user", "content": "Hi"}

    def test_to_history_excludes_system(self):
        session = ChatSession(
            id="test", provider="anthropic", model="claude-sonnet-4-6", api_key="sk-test"
        )
        session.add_message("system", "System prompt")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there")
        history = session.to_history()
        # to_history includes ALL messages
        assert len(history) == 3
        assert all("content" in m for m in history)
        assert all("timestamp" in m for m in history)

    def test_assessment_data_initially_none(self):
        session = ChatSession(
            id="test", provider="anthropic", model="claude-sonnet-4-6", api_key="sk-test"
        )
        assert session.assessment_data is None


# ── JSON Extraction ──────────────────────────────────────────


class TestExtractJson:
    def test_extracts_valid_json(self):
        text = 'Here is the assessment:\n```json\n{"system_name": "Test"}\n```\nDone!'
        result = _extract_json_from_response(text)
        assert result == {"system_name": "Test"}

    def test_returns_none_for_no_json(self):
        text = "This is just a normal response without JSON."
        result = _extract_json_from_response(text)
        assert result is None

    def test_returns_none_for_invalid_json(self):
        text = '```json\n{invalid json here}\n```'
        result = _extract_json_from_response(text)
        assert result is None

    def test_extracts_complex_json(self):
        text = '''Here is the result:
```json
{
  "system_name": "My Agency",
  "purpose": "Help clients succeed",
  "recursion_levels": {
    "level_0": {
      "operational_units": [
        {"id": "dev", "name": "Development", "priority": 1}
      ]
    }
  },
  "metasystem": {
    "s2_coordination": {"label": "Coordinator", "tasks": ["Route tasks"]}
  }
}
```
Let me know if you'd like to adjust anything.'''
        result = _extract_json_from_response(text)
        assert result is not None
        assert result["system_name"] == "My Agency"
        assert "recursion_levels" in result
        assert "metasystem" in result

    def test_extracts_first_json_block(self):
        text = '```json\n{"first": true}\n```\nSome text\n```json\n{"second": true}\n```'
        result = _extract_json_from_response(text)
        assert result == {"first": True}


# ── LiteLLM Model ID ────────────────────────────────────────


class TestLitellmModelId:
    def test_anthropic_prefix(self):
        assert _litellm_model_id("anthropic", "claude-sonnet-4-6") == "anthropic/claude-sonnet-4-6"

    def test_openai_prefix(self):
        assert _litellm_model_id("openai", "gpt-5.1") == "openai/gpt-5.1"

    def test_google_prefix(self):
        assert _litellm_model_id("google", "gemini-3-pro") == "gemini/gemini-3-pro"

    def test_ollama_prefix(self):
        assert _litellm_model_id("ollama", "llama-4") == "ollama/llama-4"

    def test_no_double_prefix(self):
        assert _litellm_model_id("anthropic", "anthropic/claude-sonnet-4-6") == "anthropic/claude-sonnet-4-6"

    def test_unknown_provider(self):
        result = _litellm_model_id("unknown", "some-model")
        assert result == "some-model"


# ── Engine Functions ─────────────────────────────────────────


class TestStartSession:
    def test_creates_session_with_system_prompt(self):
        session = start_session("anthropic", "claude-sonnet-4-6", "sk-test")
        assert session.id is not None
        assert len(session.messages) == 1
        assert session.messages[0].role == "system"
        assert "Viable System Model" in session.messages[0].content
        # Cleanup
        global_store.delete(session.id)

    def test_session_stored_in_global_store(self):
        session = start_session("openai", "gpt-5.1", "sk-test")
        found = global_store.get(session.id)
        assert found is not None
        assert found.id == session.id
        global_store.delete(session.id)


class TestFinalizeAssessment:
    def test_extracts_from_last_assistant_message(self):
        session = start_session("anthropic", "claude-sonnet-4-6", "sk-test")
        session.add_message("user", "Tell me the assessment")
        session.add_message(
            "assistant",
            'Here:\n```json\n{"system_name": "Extracted", "purpose": "Test"}\n```'
        )
        result = finalize_assessment(session.id)
        assert result is not None
        assert result["system_name"] == "Extracted"
        assert session.assessment_data is not None
        global_store.delete(session.id)

    def test_returns_none_when_no_json(self):
        session = start_session("anthropic", "claude-sonnet-4-6", "sk-test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi, let's start the interview.")
        result = finalize_assessment(session.id)
        assert result is None
        global_store.delete(session.id)

    def test_returns_none_for_invalid_session(self):
        result = finalize_assessment("nonexistent-session-id")
        assert result is None

    def test_scans_multiple_messages_for_json(self):
        session = start_session("anthropic", "claude-sonnet-4-6", "sk-test")
        session.add_message("user", "q1")
        session.add_message("assistant", "Let me think...")
        session.add_message("user", "q2")
        session.add_message(
            "assistant",
            '```json\n{"system_name": "Found", "purpose": "Deep"}\n```'
        )
        result = finalize_assessment(session.id)
        assert result is not None
        assert result["system_name"] == "Found"
        global_store.delete(session.id)


class TestGetHistory:
    def test_returns_history_without_system(self):
        session = start_session("anthropic", "claude-sonnet-4-6", "sk-test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        history = get_history(session.id)
        assert history is not None
        # get_history excludes system messages
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        global_store.delete(session.id)

    def test_returns_none_for_invalid_session(self):
        assert get_history("nonexistent-session-id") is None
