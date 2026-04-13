"""Tests for the persona module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from viableos.persona.cache import (
    _slugify_name,
    get_cached_profile,
    save_profile_to_cache,
)
from viableos.persona.profile import PersonaProfile, render_persona_section


# ── Fixtures ──────────────────────────────────────────────────


def _make_profile(**overrides) -> PersonaProfile:
    defaults = {
        "researcher_name": "Maria Silva",
        "affiliation": "IPEA/DIEST",
        "thematic_areas": ["digital government", "institutional capacity", "state reform"],
        "jel_codes": ["H11", "H83", "O38"],
        "methodological_preferences": ["Institutional analysis", "Mixed methods (quali-quanti)"],
        "publication_types": ["12 TD", "5 NT", "3 Article"],
        "recent_publications": [
            {"title": "Governo Digital no Brasil", "year": "2025", "type": "TD"},
            {"title": "Capacidade Estatal e Transformação", "year": "2024", "type": "TD"},
            {"title": "Interoperabilidade no Setor Público", "year": "2024", "type": "NT"},
        ],
        "writing_style_notes": "Formal academic Portuguese. Evidence-oriented.",
        "total_publications": 20,
        "ipeapub_enrichment": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_urls": ["https://repositorio.ipea.gov.br/server/api/test"],
        "max_tokens": 800,
    }
    defaults.update(overrides)
    return PersonaProfile(**defaults)


# ── render_persona_section ────────────────────────────────────


class TestRenderPersonaSection:
    def test_none_returns_empty(self):
        assert render_persona_section(None) == ""

    def test_full_profile_has_all_sections(self):
        profile = _make_profile()
        result = render_persona_section(profile)
        assert "## Researcher Persona" in result
        assert "Maria Silva" in result
        assert "IPEA/DIEST" in result
        assert "### Thematic Expertise" in result
        assert "digital government" in result
        assert "### Methodological Approach" in result
        assert "Institutional analysis" in result
        assert "### Publication Profile" in result
        assert "20 publications" in result
        assert "Governo Digital no Brasil" in result
        assert "### Research Style" in result
        assert "does NOT override" in result

    def test_jel_codes_rendered(self):
        profile = _make_profile()
        result = render_persona_section(profile)
        assert "H11" in result
        assert "JEL codes" in result

    def test_no_ipeapub_enrichment(self):
        profile = _make_profile(ipeapub_enrichment=None)
        result = render_persona_section(profile)
        assert "IpeaPub RAG" not in result

    def test_with_ipeapub_enrichment(self):
        profile = _make_profile(ipeapub_enrichment="Researcher focuses on digital transformation.")
        result = render_persona_section(profile)
        assert "IpeaPub RAG" in result
        assert "digital transformation" in result

    def test_truncation_drops_enrichment_first(self):
        profile = _make_profile(
            ipeapub_enrichment="x" * 2000,
            max_tokens=200,
        )
        result = render_persona_section(profile)
        # Should fit within budget (200 * 4 = 800 chars)
        assert len(result) <= 800 + 100  # some slack for final truncation

    def test_truncation_reduces_publications(self):
        pubs = [
            {"title": f"Publication {i}", "year": "2025", "type": "TD"}
            for i in range(10)
        ]
        profile = _make_profile(
            recent_publications=pubs,
            max_tokens=300,
        )
        result = render_persona_section(profile)
        # Should contain "... and N more" if truncated
        assert "Publication 0" in result  # first few should survive

    def test_empty_profile_minimal(self):
        profile = PersonaProfile(
            researcher_name="Test",
            max_tokens=800,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        result = render_persona_section(profile)
        assert "## Researcher Persona" in result
        assert "**Test**" in result


# ── Cache ─────────────────────────────────────────────────────


class TestCache:
    def test_slugify_name(self):
        assert _slugify_name("Luseni Aquino") == "luseni_aquino"
        assert _slugify_name("Flávia de Holanda Schmidt") == "flávia_de_holanda_schmidt"

    def test_cache_roundtrip(self, tmp_path: Path):
        profile = _make_profile()
        save_profile_to_cache(profile, tmp_path)
        loaded = get_cached_profile("Maria Silva", tmp_path)
        assert loaded is not None
        assert loaded.researcher_name == "Maria Silva"
        assert loaded.affiliation == "IPEA/DIEST"
        assert loaded.thematic_areas == profile.thematic_areas
        assert loaded.total_publications == 20

    def test_cache_miss(self, tmp_path: Path):
        result = get_cached_profile("Unknown Person", tmp_path)
        assert result is None

    def test_cache_expired(self, tmp_path: Path):
        profile = _make_profile(
            fetched_at=(datetime.now(timezone.utc) - timedelta(hours=200)).isoformat(),
        )
        save_profile_to_cache(profile, tmp_path)
        result = get_cached_profile("Maria Silva", tmp_path, max_age_hours=168)
        assert result is None

    def test_cache_fresh(self, tmp_path: Path):
        profile = _make_profile(
            fetched_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        save_profile_to_cache(profile, tmp_path)
        result = get_cached_profile("Maria Silva", tmp_path, max_age_hours=168)
        assert result is not None

    def test_cache_corrupt_json(self, tmp_path: Path):
        slug = _slugify_name("Maria Silva")
        (tmp_path / f"persona_{slug}.json").write_text("not json", encoding="utf-8")
        result = get_cached_profile("Maria Silva", tmp_path)
        assert result is None


# ── DSpace client ─────────────────────────────────────────────


class TestDSpaceFetch:
    def _mock_search_response(self, items: list[dict]) -> dict:
        """Build a mock DSpace search API response."""
        objects = []
        for item in items:
            metadata = item.get("metadata", {})
            objects.append({
                "_embedded": {
                    "indexableObject": {
                        "metadata": metadata,
                    },
                },
            })
        return {
            "_embedded": {
                "searchResult": {
                    "_embedded": {"objects": objects},
                    "page": {"totalElements": len(items)},
                },
            },
        }

    @patch("viableos.persona.dspace.httpx.Client")
    def test_fetch_success(self, mock_client_cls):
        from viableos.persona.dspace import fetch_researcher_from_dspace

        items = [
            {
                "metadata": {
                    "dc.title": [{"value": "Governo Digital"}],
                    "dc.date.issued": [{"value": "2025-01-01"}],
                    "dc.subject.keyword": [{"value": "digital government"}, {"value": "state capacity"}],
                    "dc.subject.jel": [{"value": "H11"}],
                    "dc.description.abstract": [{"value": "Este estudo analisa a transformação digital do estado."}],
                    "dc.description.serie": [{"value": "TD 3001"}],
                    "dc.contributor.other": [{"value": "DIEST"}],
                },
            },
            {
                "metadata": {
                    "dc.title": [{"value": "Interoperabilidade"}],
                    "dc.date.issued": [{"value": "2024-06-01"}],
                    "dc.subject.keyword": [{"value": "interoperability"}, {"value": "digital government"}],
                    "dc.subject.jel": [{"value": "O38"}],
                    "dc.description.abstract": [{"value": "O presente trabalho discute interoperabilidade."}],
                    "dc.description.serie": [{"value": "NT 112"}],
                    "dc.contributor.other": [{"value": "DIEST/IPEA"}],
                },
            },
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_search_response(items)
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        profile = fetch_researcher_from_dspace("Luseni Aquino")
        assert profile is not None
        assert profile.researcher_name == "Luseni Aquino"
        assert profile.affiliation == "IPEA/DIEST"
        assert "digital government" in profile.thematic_areas
        assert "H11" in profile.jel_codes
        assert profile.total_publications == 2
        assert len(profile.recent_publications) == 2
        assert profile.recent_publications[0]["title"] == "Governo Digital"

    @patch("viableos.persona.dspace.httpx.Client")
    def test_fetch_no_results(self, mock_client_cls):
        from viableos.persona.dspace import fetch_researcher_from_dspace

        empty_response = self._mock_search_response([])
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = empty_response
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        profile = fetch_researcher_from_dspace("Nonexistent Author")
        assert profile is None

    @patch("viableos.persona.dspace.httpx.Client")
    def test_fetch_network_error(self, mock_client_cls):
        from viableos.persona.dspace import fetch_researcher_from_dspace

        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        profile = fetch_researcher_from_dspace("Luseni Aquino")
        assert profile is None  # Graceful degradation


# ── IpeaPub client ────────────────────────────────────────────


class TestIpeaPubEnrich:
    @patch("viableos.persona.ipeapub.httpx.Client")
    def test_enrich_success(self, mock_client_cls):
        from viableos.persona.ipeapub import enrich_from_ipeapub

        profile = _make_profile()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {"text": "Luseni Aquino tem contribuído significativamente para a pesquisa em governo digital."},
                {"text": "Suas publicações focam na capacidade institucional do estado."},
            ],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = enrich_from_ipeapub(profile, "http://localhost:8000")
        assert result is not None
        assert "governo digital" in result

    @patch("viableos.persona.ipeapub.httpx.Client")
    def test_enrich_unreachable(self, mock_client_cls):
        from viableos.persona.ipeapub import enrich_from_ipeapub

        import httpx

        profile = _make_profile()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        result = enrich_from_ipeapub(profile, "http://localhost:8000")
        assert result is None


# ── resolve_personas orchestration ────────────────────────────


class TestResolvePersonas:
    @patch("viableos.persona.fetch_researcher_from_dspace")
    def test_with_persona_units(self, mock_fetch, tmp_path: Path):
        from viableos.persona import resolve_personas

        mock_fetch.return_value = _make_profile()
        units = [
            {"name": "Unit A", "persona": "Maria Silva"},
            {"name": "Unit B"},  # no persona
        ]
        result = resolve_personas(units, {}, tmp_path)
        assert "Unit A" in result
        assert "Unit B" not in result
        assert "## Researcher Persona" in result["Unit A"]

    def test_no_persona_units(self, tmp_path: Path):
        from viableos.persona import resolve_personas

        units = [{"name": "Unit A"}, {"name": "Unit B"}]
        result = resolve_personas(units, {}, tmp_path)
        assert result == {}

    @patch("viableos.persona.fetch_researcher_from_dspace")
    def test_fetch_failure_graceful(self, mock_fetch, tmp_path: Path):
        from viableos.persona import resolve_personas

        mock_fetch.return_value = None
        units = [{"name": "Unit A", "persona": "Unknown"}]
        result = resolve_personas(units, {}, tmp_path)
        assert result == {}

    @patch("viableos.persona.fetch_researcher_from_dspace")
    def test_dedup_same_researcher(self, mock_fetch, tmp_path: Path):
        from viableos.persona import resolve_personas

        mock_fetch.return_value = _make_profile()
        units = [
            {"name": "Unit A", "persona": "Maria Silva"},
            {"name": "Unit B", "persona": "Maria Silva"},
        ]
        result = resolve_personas(units, {}, tmp_path)
        assert "Unit A" in result
        assert "Unit B" in result
        # Should only call fetch once (dedup)
        mock_fetch.assert_called_once()


# ── Integration: soul_templates persona injection ─────────────


class TestSoulTemplatePersonaInjection:
    def test_persona_section_injected(self):
        from viableos.soul_templates import generate_s1_soul

        unit = {"name": "Test Unit", "purpose": "Testing", "tools": ["web-search"]}
        identity = {"purpose": "Test system", "values": ["Rigor"], "never_do": []}
        hitl = {"approval_required": []}

        persona_md = "\n## Researcher Persona\nYou are **Test Researcher**.\n"
        soul = generate_s1_soul(
            unit, identity, [], hitl, [],
            persona_section=persona_md,
        )
        assert "## Researcher Persona" in soul
        assert "Test Researcher" in soul
        # Persona should appear between Identity refresh and System purpose
        id_pos = soul.index("Identity refresh")
        persona_pos = soul.index("Researcher Persona")
        sys_pos = soul.index("System purpose")
        assert id_pos < persona_pos < sys_pos

    def test_no_persona_backward_compatible(self):
        from viableos.soul_templates import generate_s1_soul

        unit = {"name": "Test Unit", "purpose": "Testing", "tools": ["web-search"]}
        identity = {"purpose": "Test system", "values": ["Rigor"], "never_do": []}
        hitl = {"approval_required": []}

        soul = generate_s1_soul(unit, identity, [], hitl, [])
        assert "Researcher Persona" not in soul
        # System purpose should still follow identity refresh
        assert "## Identity refresh" in soul
        assert "## System purpose" in soul


# ── Integration: schema validation ────────────────────────────


class TestSchemaValidation:
    def test_persona_field_accepted(self):
        from viableos.schema import validate

        config = {
            "viable_system": {
                "name": "Test",
                "identity": {
                    "purpose": "Test",
                    "values": ["v1"],
                    "never_do": ["n1"],
                },
                "system_1": [
                    {
                        "name": "Unit A",
                        "purpose": "Test",
                        "persona": "Maria Silva",
                    },
                ],
            },
        }
        errors = validate(config)
        assert errors == [], f"Validation errors: {errors}"

    def test_persona_source_accepted(self):
        from viableos.schema import validate

        config = {
            "viable_system": {
                "name": "Test",
                "identity": {
                    "purpose": "Test",
                    "values": ["v1"],
                    "never_do": ["n1"],
                },
                "system_1": [
                    {"name": "Unit A", "purpose": "Test"},
                ],
                "persona_source": {
                    "dspace_url": "https://repositorio.ipea.gov.br/server/api",
                    "ipeapub_url": "http://localhost:8000",
                    "max_tokens": 800,
                },
            },
        }
        errors = validate(config)
        assert errors == [], f"Validation errors: {errors}"
