"""DSpace 7 REST API client for fetching IPEA researcher profiles."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timezone

import httpx

from viableos.persona.profile import PersonaProfile

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://repositorio.ipea.gov.br/server/api"

# Keywords that hint at methodological approach when found in abstracts.
_METHOD_KEYWORDS: list[tuple[str, str]] = [
    (r"\banálise institucional\b", "Institutional analysis"),
    (r"\bneo-?institucionalismo\b", "Neo-institutionalist framework"),
    (r"\bmétodos mistos\b", "Mixed methods (quali-quanti)"),
    (r"\bpainel\b.*\bdados\b", "Panel data analysis"),
    (r"\bregressão\b", "Regression analysis"),
    (r"\bestudo de caso\b", "Case study methodology"),
    (r"\bsurvey\b|\bpesquisa domiciliar\b", "Survey-based research"),
    (r"\bcomparati[vf]\b", "Comparative analysis"),
    (r"\bqualitativ[ao]\b", "Qualitative analysis"),
    (r"\bquantitativ[ao]\b", "Quantitative analysis"),
    (r"\brevisão sistemática\b", "Systematic literature review"),
    (r"\beconometri[ac]\b", "Econometric methods"),
    (r"\banálise de rede\b|\bnetwork analysis\b", "Network analysis"),
    (r"\btext mining\b|\bmineração de texto\b", "Text mining / NLP"),
    (r"\bOCDE\b|\bOECD\b", "International benchmarking (OECD)"),
]

# Mapping from DSpace dc.description.serie patterns to short type labels.
_SERIES_PATTERNS: list[tuple[str, str]] = [
    (r"^TD\b|Texto para Discuss", "TD"),
    (r"^NT\b|Nota Técnica", "NT"),
    (r"BAPI", "BAPI"),
    (r"Livro|Book", "Book"),
    (r"Capítulo|Chapter", "Chapter"),
    (r"Artigo|Article", "Article"),
    (r"Relatório|Report", "Report"),
]


def _classify_series(raw: str) -> str:
    """Map a raw dc.description.serie value to a short label."""
    for pattern, label in _SERIES_PATTERNS:
        if re.search(pattern, raw, re.IGNORECASE):
            return label
    return raw[:30] if raw else "Other"


def _extract_dc(metadata: list[dict], key: str) -> list[str]:
    """Extract all values for a Dublin Core key from the DSpace metadata list."""
    return [
        m.get("value", "")
        for m in metadata
        if m.get("key") == key and m.get("value")
    ]


def _infer_methods(abstracts: list[str]) -> list[str]:
    """Infer methodological preferences from a list of abstracts."""
    hits: Counter[str] = Counter()
    combined = " ".join(abstracts).lower()
    for pattern, label in _METHOD_KEYWORDS:
        if re.search(pattern, combined, re.IGNORECASE):
            hits[label] += 1
    return [label for label, _ in hits.most_common(5)]


def _extract_affiliation(metadata_items: list[list[dict]]) -> str:
    """Try to extract organizational affiliation from item metadata."""
    for metadata in metadata_items:
        others = _extract_dc(metadata, "dc.contributor.other")
        for val in others:
            if "DIEST" in val.upper():
                return "IPEA/DIEST"
            if "DIMAC" in val.upper():
                return "IPEA/DIMAC"
            if "DISOC" in val.upper():
                return "IPEA/DISOC"
            if "DISET" in val.upper():
                return "IPEA/DISET"
            if "DIRUR" in val.upper():
                return "IPEA/DIRUR"
            if "DINTE" in val.upper():
                return "IPEA/DINTE"
            if "IPEA" in val.upper():
                return "IPEA"
    return "IPEA"


def fetch_researcher_from_dspace(
    name: str,
    base_url: str = _DEFAULT_BASE_URL,
    timeout: float = 15.0,
) -> PersonaProfile | None:
    """Fetch an IPEA researcher profile from the DSpace 7 REST API.

    Returns None on any error (network, parse, no match).  Never raises.
    """
    try:
        return _fetch_impl(name, base_url, timeout)
    except Exception:
        logger.warning("Failed to fetch persona for %r from DSpace", name, exc_info=True)
        return None


def _fetch_impl(name: str, base_url: str, timeout: float) -> PersonaProfile | None:
    base_url = base_url.rstrip("/")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        # Step 1: Search for publications by this author
        search_url = f"{base_url}/discover/search/objects"
        resp = client.get(search_url, params={
            "query": f'author:"{name}"',
            "dsoType": "ITEM",
            "size": 50,
            "sort": "dc.date.issued,DESC",
        })
        resp.raise_for_status()
        search_data = resp.json()

        embedded = search_data.get("_embedded", {})
        search_objects = embedded.get("searchResult", {}).get("_embedded", {}).get("objects", [])

        if not search_objects:
            # Fallback: try a simpler text query
            resp = client.get(search_url, params={
                "query": name,
                "dsoType": "ITEM",
                "size": 50,
                "sort": "dc.date.issued,DESC",
            })
            resp.raise_for_status()
            search_data = resp.json()
            embedded = search_data.get("_embedded", {})
            search_objects = embedded.get("searchResult", {}).get("_embedded", {}).get("objects", [])

        if not search_objects:
            logger.info("No publications found for researcher %r", name)
            return None

        total_elements = (
            search_data.get("_embedded", {})
            .get("searchResult", {})
            .get("page", {})
            .get("totalElements", len(search_objects))
        )

        # Step 2: Extract metadata from each item
        all_keywords: list[str] = []
        all_jel: list[str] = []
        all_abstracts: list[str] = []
        all_types: list[str] = []
        recent_pubs: list[dict] = []
        all_metadata: list[list[dict]] = []

        for obj in search_objects[:30]:
            item = obj.get("_embedded", {}).get("indexableObject", {})
            metadata = item.get("metadata", [])

            # DSpace 7 can return metadata as a dict of lists or list of dicts
            if isinstance(metadata, dict):
                # Convert dict format to list format
                flat: list[dict] = []
                for key, values in metadata.items():
                    if isinstance(values, list):
                        for v in values:
                            if isinstance(v, dict):
                                flat.append({"key": key, "value": v.get("value", "")})
                            else:
                                flat.append({"key": key, "value": str(v)})
                    else:
                        flat.append({"key": key, "value": str(values)})
                metadata = flat

            all_metadata.append(metadata)

            keywords = _extract_dc(metadata, "dc.subject.keyword")
            all_keywords.extend(keywords)

            jel = _extract_dc(metadata, "dc.subject.jel")
            all_jel.extend(jel)

            abstracts = _extract_dc(metadata, "dc.description.abstract")
            all_abstracts.extend(abstracts)

            series = _extract_dc(metadata, "dc.description.serie")
            for s in series:
                all_types.append(_classify_series(s))

            titles = _extract_dc(metadata, "dc.title")
            dates = _extract_dc(metadata, "dc.date.issued")
            title = titles[0] if titles else "Untitled"
            year = dates[0][:4] if dates else ""
            ptype = _classify_series(series[0]) if series else ""

            if len(recent_pubs) < 10:
                recent_pubs.append({
                    "title": title,
                    "year": year,
                    "type": ptype,
                })

        # Step 3: Aggregate into profile
        keyword_counts = Counter(all_keywords)
        top_themes = [kw for kw, _ in keyword_counts.most_common(10)]

        jel_deduped = list(dict.fromkeys(all_jel))  # preserve order

        type_counts = Counter(all_types)
        pub_types = [f"{count} {ptype}" for ptype, count in type_counts.most_common()]

        methods = _infer_methods(all_abstracts)

        affiliation = _extract_affiliation(all_metadata)

        # Writing style notes from abstract patterns
        style_notes = _infer_writing_style(all_abstracts)

        return PersonaProfile(
            researcher_name=name,
            affiliation=affiliation,
            thematic_areas=top_themes,
            jel_codes=jel_deduped[:10],
            methodological_preferences=methods,
            publication_types=pub_types,
            recent_publications=recent_pubs,
            writing_style_notes=style_notes,
            total_publications=total_elements,
            ipeapub_enrichment=None,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source_urls=[f"{base_url}/discover/search/objects?query=author:{name}"],
        )


def _infer_writing_style(abstracts: list[str]) -> str:
    """Produce a short description of the researcher's writing style."""
    if not abstracts:
        return ""

    traits: list[str] = []
    combined = " ".join(abstracts).lower()
    total = len(abstracts)

    # Language detection
    pt_markers = combined.count("este") + combined.count("esta") + combined.count("são")
    en_markers = combined.count("this") + combined.count("these") + combined.count("are")
    if pt_markers > en_markers * 2:
        traits.append("Predominantly writes in Portuguese")
    elif en_markers > pt_markers * 2:
        traits.append("Predominantly writes in English")
    else:
        traits.append("Publishes in both Portuguese and English")

    # Formality and structure
    if "o presente" in combined or "este trabalho" in combined or "este estudo" in combined:
        traits.append("Uses formal impersonal academic style ('o presente estudo')")

    if "recomendações" in combined or "recomendação" in combined or "policy" in combined:
        traits.append("Frequently includes policy recommendations")

    if "dados" in combined and ("evidência" in combined or "empíric" in combined):
        traits.append("Evidence-oriented, grounds arguments in empirical data")

    if "limitações" in combined or "limitations" in combined:
        traits.append("Includes explicit methodological limitations sections")

    if total >= 10:
        avg_len = len(combined) / total
        if avg_len > 1500:
            traits.append("Writes detailed, comprehensive abstracts")
        elif avg_len < 600:
            traits.append("Favors concise, focused abstracts")

    return ". ".join(traits) + "." if traits else ""
