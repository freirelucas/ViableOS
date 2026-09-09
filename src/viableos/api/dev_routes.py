"""API do pipeline de autodesenvolvimento da CDA."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from viableos.cda.autodesenvolvimento import pipeline, TipoArtefato

dev_router = APIRouter(prefix="/api/cda/dev", tags=["cda-dev"])


@dev_router.get("/tarefas")
def listar_tarefas(projeto: str | None = None) -> list[dict[str, Any]]:
    return pipeline.tarefas_para_dict()


@dev_router.post("/tarefas")
def criar_tarefa(payload: dict[str, str]) -> dict[str, Any]:
    t = pipeline.criar_tarefa(
        titulo=payload["titulo"],
        descricao=payload.get("descricao", ""),
        projeto=payload.get("projeto", "Projeto 1"),
        solicitante=payload.get("solicitante", "S3 - Gestão de Projetos"),
    )
    return {"status": "ok", "tarefa_id": t.id}


@dev_router.post("/tarefas/{tarefa_id}/iniciar")
def iniciar_tarefa(tarefa_id: str) -> dict[str, str]:
    if pipeline.iniciar(tarefa_id):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "tarefa nao encontrada ou ja iniciada"}


@dev_router.post("/tarefas/{tarefa_id}/concluir")
def concluir_tarefa(tarefa_id: str, payload: dict[str, str]) -> dict[str, str]:
    if pipeline.concluir(tarefa_id, payload.get("notas", "")):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "tarefa nao encontrada ou nao em_execucao"}


@dev_router.get("/artefatos")
def listar_artefatos(projeto: str | None = None) -> list[dict[str, Any]]:
    return pipeline.artefatos_para_dict(projeto)


@dev_router.post("/artefatos")
def registrar_artefato(payload: dict[str, Any]) -> dict[str, Any]:
    a = pipeline.registrar_artefato(
        nome=payload["nome"],
        tipo=TipoArtefato(payload.get("tipo", "codigo")),
        descricao=payload.get("descricao", ""),
        caminho=payload.get("caminho", ""),
        projeto=payload.get("projeto", "Projeto 1"),
        linguagem=payload.get("linguagem", ""),
        linhas=payload.get("linhas", 0),
        conteudo=payload.get("conteudo"),
    )
    # Vincular à tarefa se informada
    tarefa_id = payload.get("tarefa_id")
    if tarefa_id:
        pipeline.vincular_artefato(tarefa_id, a.id)
    return {
        "status": "ok",
        "artefato_id": a.id,
        "hash_conteudo": a.hash_conteudo,
        "verificado": a.verificado,
    }


@dev_router.get("/artefatos/{artefato_id}")
def obter_artefato(artefato_id: str) -> dict[str, Any] | None:
    for a in pipeline._artefatos:
        if a.id == artefato_id:
            return a.to_dict()
    return None
