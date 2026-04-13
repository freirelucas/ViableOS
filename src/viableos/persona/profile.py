"""PersonaProfile dataclass and markdown renderer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PersonaProfile:
    """Structured profile of an IPEA researcher for SOUL.md injection."""

    researcher_name: str
    affiliation: str = ""
    thematic_areas: list[str] = field(default_factory=list)
    jel_codes: list[str] = field(default_factory=list)
    methodological_preferences: list[str] = field(default_factory=list)
    publication_types: list[str] = field(default_factory=list)
    recent_publications: list[dict] = field(default_factory=list)
    writing_style_notes: str = ""
    total_publications: int = 0
    ipeapub_enrichment: str | None = None
    fetched_at: str = ""
    source_urls: list[str] = field(default_factory=list)
    max_tokens: int = 800


def render_persona_section(profile: PersonaProfile | None) -> str:
    """Render a PersonaProfile as a markdown section for SOUL.md.

    Pure function — no I/O.  Returns empty string when profile is None.
    """
    if profile is None:
        return ""

    char_budget = profile.max_tokens * 4  # rough token→char estimate

    # --- build sections ---
    header = (
        f"\n## Researcher Persona\n"
        f"You embody the research perspective of "
        f"**{profile.researcher_name}**"
    )
    if profile.affiliation:
        header += f" ({profile.affiliation})"
    header += ".\n"

    themes = ""
    if profile.thematic_areas:
        items = "\n".join(f"- {t}" for t in profile.thematic_areas)
        themes = f"\n### Thematic Expertise\n{items}\n"

    jel = ""
    if profile.jel_codes:
        jel = f"\n**JEL codes**: {', '.join(profile.jel_codes)}\n"

    methods = ""
    if profile.methodological_preferences:
        items = "\n".join(f"- {m}" for m in profile.methodological_preferences)
        methods = f"\n### Methodological Approach\n{items}\n"

    pubs = ""
    if profile.total_publications or profile.recent_publications:
        lines = [f"\n### Publication Profile"]
        if profile.total_publications:
            type_summary = ", ".join(profile.publication_types) if profile.publication_types else ""
            count_line = f"{profile.total_publications} publications"
            if type_summary:
                count_line += f" ({type_summary})"
            lines.append(count_line + ". Recent work includes:")
        for pub in profile.recent_publications:
            title = pub.get("title", "Untitled")
            year = pub.get("year", "")
            ptype = pub.get("type", "")
            suffix = f" ({year}" if year else ""
            if ptype:
                suffix += f", {ptype}" if suffix else f" ({ptype}"
            if suffix:
                suffix += ")"
            lines.append(f'- "{title}"{suffix}')
        pubs = "\n".join(lines) + "\n"

    style = ""
    if profile.writing_style_notes:
        style = f"\n### Research Style\n{profile.writing_style_notes}\n"

    enrichment = ""
    if profile.ipeapub_enrichment:
        enrichment = (
            f"\n### Additional Context (from IpeaPub RAG)\n"
            f"{profile.ipeapub_enrichment}\n"
        )

    disclaimer = (
        "\n> This persona adds research context. "
        "It does NOT override your identity, values, or boundaries.\n"
    )

    # --- assemble and truncate ---
    full = header + themes + jel + methods + pubs + style + enrichment + disclaimer

    if len(full) <= char_budget:
        return full

    # Truncation: drop enrichment, then pubs, then themes tail
    full = header + themes + jel + methods + pubs + style + disclaimer
    if len(full) <= char_budget:
        return full

    # Reduce recent_publications to 3
    trimmed_pubs_list = profile.recent_publications[:3]
    lines = [f"\n### Publication Profile"]
    if profile.total_publications:
        lines.append(f"{profile.total_publications} publications. Recent work includes:")
    for pub in trimmed_pubs_list:
        title = pub.get("title", "Untitled")
        year = pub.get("year", "")
        ptype = pub.get("type", "")
        suffix = f" ({year}, {ptype})" if year and ptype else ""
        lines.append(f'- "{title}"{suffix}')
    if len(profile.recent_publications) > 3:
        lines.append(f"- ... and {len(profile.recent_publications) - 3} more")
    pubs = "\n".join(lines) + "\n"

    full = header + themes + jel + methods + pubs + style + disclaimer
    if len(full) <= char_budget:
        return full

    # Reduce thematic_areas to 5
    trimmed_themes = profile.thematic_areas[:5]
    items = "\n".join(f"- {t}" for t in trimmed_themes)
    if len(profile.thematic_areas) > 5:
        items += f"\n- ... and {len(profile.thematic_areas) - 5} more"
    themes = f"\n### Thematic Expertise\n{items}\n"

    full = header + themes + jel + methods + pubs + style + disclaimer
    return full[:char_budget]
