"""Chat com agentes da CDA — Diretora conversa com cada membro."""

from __future__ import annotations

from fastapi import APIRouter

from viableos.cda.fabrica import fabrica
from viableos.cda.glm import glm_chat

agente_chat_router = APIRouter(prefix="/api/cda/chat", tags=["cda-chat"])


@agente_chat_router.post("/{nome}")
async def falar_com_agente(nome: str, payload: dict[str, str]) -> dict[str, str]:
    """Diretora conversa com agente da CDA e recebe resposta via GLM.

    R1 imposta: LLM opera apenas no S1 — a conversa direta com o GLM é
    exclusiva dos agentes operacionais (tipos s1_*). S2-S4 respondem por
    seus canais determinísticos (dados, agenda, auditoria), não por LLM.
    """
    a = fabrica.obter_agente_obj(nome)
    if a is None:
        return {"status": "erro", "motivo": "agente nao encontrado"}

    if not a.tipo.value.startswith("s1"):
        return {
            "status": "erro",
            "motivo": "R1: LLM opera apenas no S1 — use os canais determinísticos do agente",
        }

    pergunta = payload.get("mensagem", "")
    if not pergunta:
        return {"status": "erro", "motivo": "mensagem vazia"}

    resposta = await glm_chat(
        system_prompt=a.system_prompt,
        user_message=pergunta,
    )

    a.registrar_acao(f"Diretora perguntou: {pergunta[:100]}", resposta[:200])
    return {"status": "ok", "resposta": resposta}
