"""JSON file cache for researcher persona profiles."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from viableos.persona.profile import PersonaProfile

logger = logging.getLogger(__name__)


def _slugify_name(name: str) -> str:
    """Slugify a researcher name for use as a cache filename."""
    # Normalize unicode but preserve accented chars in the slug
    normalized = unicodedata.normalize("NFC", name)
    slug = normalized.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "_", slug)
    return slug


def get_cached_profile(
    name: str,
    cache_dir: Path,
    max_age_hours: int = 168,
) -> PersonaProfile | None:
    """Load a cached persona profile if it exists and is fresh enough."""
    slug = _slugify_name(name)
    path = cache_dir / f"persona_{slug}.json"

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read persona cache %s: %s", path, exc)
        return None

    fetched_at = data.get("fetched_at", "")
    if not fetched_at:
        return None

    try:
        fetched_dt = datetime.fromisoformat(fetched_at)
    except ValueError:
        return None

    age_hours = (datetime.now(timezone.utc) - fetched_dt).total_seconds() / 3600
    if age_hours > max_age_hours:
        logger.info("Persona cache for %r expired (%.1fh old)", name, age_hours)
        return None

    return PersonaProfile(**{
        k: v for k, v in data.items()
        if k in PersonaProfile.__dataclass_fields__
    })


def save_profile_to_cache(profile: PersonaProfile, cache_dir: Path) -> None:
    """Save a persona profile to the JSON file cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify_name(profile.researcher_name)
    path = cache_dir / f"persona_{slug}.json"

    try:
        path.write_text(
            json.dumps(asdict(profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to write persona cache %s: %s", path, exc)
