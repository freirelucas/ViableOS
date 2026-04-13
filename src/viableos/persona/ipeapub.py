"""IpeaPub RAG client for optional persona enrichment."""

from __future__ import annotations

import logging

import httpx

from viableos.persona.profile import PersonaProfile

logger = logging.getLogger(__name__)


def enrich_from_ipeapub(
    profile: PersonaProfile,
    ipeapub_url: str = "http://localhost:8000",
    timeout: float = 10.0,
) -> str | None:
    """Query IpeaPub's RAG for additional context about a researcher.

    Returns a short enrichment paragraph, or None on any failure.
    """
    try:
        return _enrich_impl(profile, ipeapub_url, timeout)
    except Exception:
        logger.warning(
            "IpeaPub enrichment failed for %r", profile.researcher_name, exc_info=True,
        )
        return None


def _enrich_impl(
    profile: PersonaProfile,
    ipeapub_url: str,
    timeout: float,
) -> str | None:
    base = ipeapub_url.rstrip("/")
    query = (
        f"Quais são as principais contribuições e temas de pesquisa de "
        f"{profile.researcher_name}?"
    )

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.post(
            f"{base}/search",
            json={"query": query, "top_k": 5},
        )
        resp.raise_for_status()
        data = resp.json()

    # IpeaPub returns a list of chunks with text + metadata
    results = data if isinstance(data, list) else data.get("results", [])

    if not results:
        return None

    # Concatenate chunk texts into an enrichment paragraph
    texts: list[str] = []
    for chunk in results[:5]:
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        if text:
            texts.append(text.strip())

    if not texts:
        return None

    combined = " ".join(texts)
    # Truncate to ~500 chars to keep the enrichment concise
    if len(combined) > 500:
        combined = combined[:497] + "..."

    return combined
