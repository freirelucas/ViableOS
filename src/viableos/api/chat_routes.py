"""Chat API routes — SSE streaming for the VSM Expert Chat."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from viableos.chat.engine import (
    finalize_assessment,
    get_history,
    send_message,
    start_session,
)
from viableos.chat.files import MAX_FILE_SIZE, file_store

chat_router = APIRouter(prefix="/api/chat")


class StartRequest(BaseModel):
    provider: str
    model: str
    api_key: str


class StartResponse(BaseModel):
    session_id: str


class MessageRequest(BaseModel):
    session_id: str
    message: str
    attachment_ids: list[str] = []


@chat_router.post("/start", response_model=StartResponse)
async def chat_start(req: StartRequest) -> StartResponse:
    """Start a new chat session. Returns session ID."""
    session = start_session(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
    )
    return StartResponse(session_id=session.id)


@chat_router.post("/message")
async def chat_message(req: MessageRequest) -> StreamingResponse:
    """Send a message and receive SSE-streamed response."""

    async def event_stream():
        async for chunk in send_message(
            req.session_id, req.message, attachment_ids=req.attachment_ids,
        ):
            # JSON-encode to safely handle newlines in LLM output
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post("/upload")
async def chat_upload(
    session_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload a file for inclusion in a chat message."""
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    att = file_store.process_upload(
        session_id=session_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    return {
        "id": att.id,
        "filename": att.filename,
        "type": att.content_type,
        "size": att.size_bytes,
    }


class FinalizeResponse(BaseModel):
    assessment: dict[str, Any] | None
    success: bool


@chat_router.post("/finalize", response_model=FinalizeResponse)
async def chat_finalize(req: dict[str, str]) -> FinalizeResponse:
    """Extract assessment data from the conversation."""
    session_id = req.get("session_id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    data = finalize_assessment(session_id)
    return FinalizeResponse(assessment=data, success=data is not None)


@chat_router.get("/history/{session_id}")
async def chat_history(session_id: str) -> list[dict[str, Any]]:
    """Get message history for a session."""
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return history
