"""File upload handling — in-memory storage with PDF/image processing."""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_FILES_PER_MESSAGE = 5

IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
TEXT_TYPES = {"text/plain", "text/markdown", "text/csv"}
PDF_TYPE = "application/pdf"


@dataclass
class Attachment:
    id: str
    session_id: str
    filename: str
    content_type: str
    llm_content: str | dict  # text string or {"type": "image_url", ...} block
    size_bytes: int


class FileStore:
    """In-memory attachment store, keyed by attachment ID."""

    def __init__(self) -> None:
        self._files: dict[str, Attachment] = {}

    def process_upload(
        self,
        session_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Attachment:
        """Process an uploaded file and return an Attachment."""
        if len(data) > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({len(data)} bytes). Max {MAX_FILE_SIZE} bytes.")

        att_id = str(uuid.uuid4())

        if content_type in IMAGE_TYPES:
            llm_content = _encode_image_base64(data, content_type)
        elif content_type == PDF_TYPE:
            llm_content = _extract_pdf_text(data)
        elif content_type in TEXT_TYPES or filename.endswith((".txt", ".md", ".csv")):
            llm_content = data.decode("utf-8", errors="replace")
        else:
            llm_content = f"[Unsupported file type: {filename} ({content_type})]"

        att = Attachment(
            id=att_id,
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            llm_content=llm_content,
            size_bytes=len(data),
        )
        self._files[att_id] = att
        return att

    def get(self, attachment_id: str) -> Attachment | None:
        return self._files.get(attachment_id)

    def get_for_session(self, session_id: str) -> list[Attachment]:
        return [a for a in self._files.values() if a.session_id == session_id]


def _extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF using PyMuPDF."""
    import pymupdf

    text_parts: list[str] = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip() or "[PDF contained no extractable text]"


def _encode_image_base64(data: bytes, content_type: str) -> dict:
    """Return a Vision API image_url content block."""
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{content_type};base64,{b64}"},
    }


# Global file store
file_store = FileStore()
