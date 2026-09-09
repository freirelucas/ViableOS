"""TR Generator API routes — document generation for IPEA/PIPA."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from viableos.tr.data import (
    MODALIDADES, DIRETORIAS, DIRETORIA_TEMA, NORMA,
    FUNCOES, TEMAS, FUNCAO_PERFIL, TEMA_LINHA,
    OBJETO_EXEMPLOS, CRITERIOS_PERFIS,
)
from viableos.tr.conformidade import conformidade, resumo_conf, diff_dias
from viableos.tr.minuta import build_tr, build_edital, minuta_to_text, vagas_de
from viableos.tr.perfil import compor_perfil, compor_atividades, sugerir_criterios, compor_objeto
from viableos.tr.format import fmt_valor, fmt_data, extenso, brl

tr_router = APIRouter(prefix="/api/tr")


@tr_router.get("/data/modalidades")
def list_modalidades() -> list[dict[str, Any]]:
    return MODALIDADES


@tr_router.get("/data/diretorias")
def list_diretorias() -> list[dict[str, Any]]:
    return DIRETORIAS


@tr_router.get("/data/perfis")
def list_perfis() -> dict[str, Any]:
    return {
        "funcoes": FUNCOES,
        "temas": TEMAS,
        "funcao_perfil": FUNCAO_PERFIL,
        "tema_linha": TEMA_LINHA,
    }


@tr_router.get("/data/norma")
def get_norma() -> dict[str, Any]:
    return NORMA


@tr_router.get("/data/objetos")
def list_objetos() -> list[dict[str, Any]]:
    return OBJETO_EXEMPLOS


@tr_router.get("/data/criterios")
def list_criterios() -> list[dict[str, Any]]:
    return CRITERIOS_PERFIS


@tr_router.post("/generate")
def generate_document(payload: dict[str, Any]) -> dict[str, Any]:
    doc_type = payload.get("type", "tr")
    form = payload.get("form", {})

    if doc_type == "edital":
        sections = build_edital(form)
    else:
        sections = build_tr(form)

    return {
        "sections": sections,
        "text": minuta_to_text(sections),
    }


@tr_router.post("/validate")
def validate_form(payload: dict[str, Any]) -> dict[str, Any]:
    form = payload.get("form", {})
    checks = conformidade(form)
    return {
        "checks": checks,
        "summary": resumo_conf(checks),
    }


@tr_router.post("/compose/perfil")
def api_compor_perfil(payload: dict[str, Any]) -> dict[str, str]:
    text = compor_perfil(
        modalidade=payload.get("modalidade", ""),
        funcoes=payload.get("funcoes", []),
        temas=payload.get("temas", []),
        experiencia=payload.get("experiencia", ""),
        enfases=payload.get("enfases", []),
        recortes=payload.get("recortes", []),
    )
    return {"text": text}


@tr_router.post("/compose/atividades")
def api_compor_atividades(payload: dict[str, Any]) -> dict[str, str]:
    text = compor_atividades(
        funcoes=payload.get("funcoes", []),
        temas=payload.get("temas", []),
    )
    return {"text": text}


@tr_router.post("/compose/criterios")
def api_sugerir_criterios(payload: dict[str, Any]) -> dict[str, str]:
    text = sugerir_criterios(
        modalidade=payload.get("modalidade", ""),
        funcoes=payload.get("funcoes", []),
        prova_pratica=payload.get("prova_pratica", False),
    )
    return {"text": text}


@tr_router.post("/compose/objeto")
def api_compor_objeto(payload: dict[str, Any]) -> dict[str, str]:
    text = compor_objeto(projeto_nome=payload.get("projetoNome", ""))
    return {"text": text}


@tr_router.post("/diff-dias")
def api_diff_dias(payload: dict[str, str]) -> dict[str, int | None]:
    return {"dias": diff_dias(payload.get("a"), payload.get("b"))}
