"""Chat engine — LiteLLM streaming with VSM system prompt.

No tool calling, no sandbox, no agent loop — just LLM streaming + system prompt.
Keeps the dependency footprint minimal.
"""

from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator

from viableos.chat.files import IMAGE_TYPES, Attachment, file_store
from viableos.chat.session import AttachmentMeta, ChatSession, store
from viableos.chat.system_prompt import SYSTEM_PROMPT

# Provider-to-LiteLLM model prefix mapping
PROVIDER_PREFIXES: dict[str, str] = {
    "anthropic": "anthropic/",
    "openai": "openai/",
    "google": "gemini/",
    "deepseek": "deepseek/",
    "xai": "xai/",
    "ollama": "ollama/",
}


def _litellm_model_id(provider: str, model: str) -> str:
    """Convert provider + model into a LiteLLM model string."""
    prefix = PROVIDER_PREFIXES.get(provider, "")
    if model.startswith(prefix):
        return model
    return f"{prefix}{model}"


def _extract_api_key_env(provider: str) -> str:
    """Return the environment variable name LiteLLM expects for a provider."""
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "xai": "XAI_API_KEY",
    }
    return mapping.get(provider, "OPENAI_API_KEY")


def start_session(provider: str, model: str, api_key: str) -> ChatSession:
    """Create a new chat session with system prompt pre-loaded."""
    session = store.create(provider=provider, model=model, api_key=api_key)
    session.add_message("system", SYSTEM_PROMPT)
    return session


def _build_multimodal_content(
    user_message: str, attachments: list[Attachment],
) -> str | list[dict[str, Any]]:
    """Build LiteLLM content: plain string or multimodal content blocks."""
    if not attachments:
        return user_message

    content_parts: list[dict[str, Any]] = []

    # Text attachments (PDFs, TXT, etc.) as context before user message
    for att in attachments:
        if att.content_type not in IMAGE_TYPES and isinstance(att.llm_content, str):
            content_parts.append({
                "type": "text",
                "text": f"[Attached file: {att.filename}]\n{att.llm_content}",
            })

    # User message
    content_parts.append({"type": "text", "text": user_message})

    # Image attachments as image_url blocks
    for att in attachments:
        if att.content_type in IMAGE_TYPES and isinstance(att.llm_content, dict):
            content_parts.append(att.llm_content)

    return content_parts


async def send_message(
    session_id: str,
    user_message: str,
    attachment_ids: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Send a user message and stream the assistant response.

    Yields chunks of the assistant response as they arrive.
    The complete response is stored in the session when done.
    """
    import litellm

    session = store.get(session_id)
    if session is None:
        yield "[ERROR] Session not found"
        return

    # Resolve attachments
    attachments: list[Attachment] = []
    att_meta: list[AttachmentMeta] = []
    for att_id in (attachment_ids or []):
        att = file_store.get(att_id)
        if att:
            attachments.append(att)
            att_meta.append(AttachmentMeta(
                id=att.id, filename=att.filename, content_type=att.content_type,
            ))

    # Store the user message (text only — attachments referenced by meta)
    session.add_message("user", user_message, attachments=att_meta)

    # Build LiteLLM messages — swap the last user message content for multimodal
    messages = session.to_litellm_messages()
    messages[-1]["content"] = _build_multimodal_content(user_message, attachments)

    model_id = _litellm_model_id(session.provider, session.model)

    try:
        response = await litellm.acompletion(
            model=model_id,
            messages=messages,
            stream=True,
            api_key=session.api_key,
            max_tokens=4096,
        )

        full_response = ""
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                full_response += delta.content
                yield delta.content

        session.add_message("assistant", full_response)

    except Exception as e:
        error_msg = f"[ERROR] {type(e).__name__}: {e}"
        yield error_msg


def _extract_json_from_response(text: str) -> dict[str, Any] | None:
    """Extract JSON block from markdown-formatted assistant response."""
    pattern = r"```json\s*\n(.*?)\n\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def finalize_assessment(session_id: str) -> dict[str, Any] | None:
    """Extract assessment data from the last assistant message containing JSON.

    Returns the assessment_config dict or None if not found.
    """
    session = store.get(session_id)
    if session is None:
        return None

    for msg in reversed(session.messages):
        if msg.role == "assistant":
            data = _extract_json_from_response(msg.content)
            if data:
                session.assessment_data = data
                return data

    return None


def get_history(session_id: str) -> list[dict[str, Any]] | None:
    """Get message history for a session (excluding system messages)."""
    session = store.get(session_id)
    if session is None:
        return None
    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp,
            "attachments": [
                {"id": a.id, "filename": a.filename, "type": a.content_type}
                for a in m.attachments
            ],
        }
        for m in session.messages
        if m.role != "system"
    ]
