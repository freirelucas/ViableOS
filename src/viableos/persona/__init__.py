"""IPEA researcher persona module for ViableOS.

Fetches researcher profiles from DSpace / IpeaPub, caches them locally,
and renders markdown sections for injection into agent SOUL.md files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from viableos.persona.cache import get_cached_profile, save_profile_to_cache
from viableos.persona.dspace import fetch_researcher_from_dspace
from viableos.persona.ipeapub import enrich_from_ipeapub
from viableos.persona.profile import PersonaProfile, render_persona_section

__all__ = ["PersonaProfile", "render_persona_section", "resolve_personas"]

logger = logging.getLogger(__name__)

_DEFAULT_DSPACE_URL = "https://repositorio.ipea.gov.br/server/api"


def resolve_personas(
    s1_units: list[dict[str, Any]],
    persona_source: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    """Resolve persona sections for all S1 units that have a ``persona`` field.

    Returns a dict mapping unit name → rendered markdown section string.
    Units without a persona field (or on fetch failure) get no entry.
    """
    # Check if any unit actually needs a persona
    units_with_persona = [
        (u.get("name", f"Unit {i}"), u["persona"])
        for i, u in enumerate(s1_units)
        if u.get("persona")
    ]
    if not units_with_persona:
        return {}

    dspace_url = persona_source.get("dspace_url", _DEFAULT_DSPACE_URL)
    ipeapub_url = persona_source.get("ipeapub_url")  # None = skip enrichment
    cache_dir = Path(persona_source.get("cache_dir", output_dir / ".persona_cache"))
    max_age = int(persona_source.get("cache_max_age_hours", 168))
    max_tokens = int(persona_source.get("max_tokens", 800))

    # Resolve each researcher (may share profiles if two units reference same name)
    profile_cache: dict[str, PersonaProfile | None] = {}
    result: dict[str, str] = {}

    for unit_name, researcher_name in units_with_persona:
        # Dedup: reuse profile if same researcher already fetched
        if researcher_name not in profile_cache:
            profile = _resolve_single(
                researcher_name, dspace_url, ipeapub_url, cache_dir, max_age,
            )
            profile_cache[researcher_name] = profile

        profile = profile_cache[researcher_name]
        if profile is not None:
            profile.max_tokens = max_tokens
            section = render_persona_section(profile)
            if section:
                result[unit_name] = section

    if result:
        logger.info(
            "Resolved personas for %d unit(s): %s",
            len(result), ", ".join(result.keys()),
        )

    return result


def _resolve_single(
    researcher_name: str,
    dspace_url: str,
    ipeapub_url: str | None,
    cache_dir: Path,
    max_age_hours: int,
) -> PersonaProfile | None:
    """Resolve a single researcher: cache → DSpace → optionally IpeaPub."""
    # 1. Try cache first
    profile = get_cached_profile(researcher_name, cache_dir, max_age_hours)
    if profile is not None:
        logger.info("Persona cache hit for %r", researcher_name)
        return profile

    # 2. Fetch from DSpace
    logger.info("Fetching persona for %r from DSpace...", researcher_name)
    profile = fetch_researcher_from_dspace(researcher_name, dspace_url)
    if profile is None:
        logger.warning("Could not fetch persona for %r — skipping", researcher_name)
        return None

    # 3. Optional IpeaPub enrichment
    if ipeapub_url:
        logger.info("Enriching persona for %r from IpeaPub...", researcher_name)
        enrichment = enrich_from_ipeapub(profile, ipeapub_url)
        if enrichment:
            profile.ipeapub_enrichment = enrichment

    # 4. Cache the result
    save_profile_to_cache(profile, cache_dir)

    return profile
