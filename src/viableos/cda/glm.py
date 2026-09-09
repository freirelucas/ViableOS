"""Integração com GLM 5.2 — o sistema nervoso da CDA.

TODO: Substituir httpx mock por chamada real ao ipeagpt quando API key disponível.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

IPEAGPT_URL = os.environ.get(
    "IPEAGPT_URL",
    "https://ipeagpt.ipea.gov.br/api/v1/chat/completions",
)
IPEAGPT_API_KEY = os.environ.get("IPEAGPT_API_KEY", "")
PROXY_URL = os.environ.get("HTTPS_PROXY", "")

# Contabilidade de uso — alimenta o monitor de orçamento (gatilho R4
# DESVIO_ORCAMENTO). O custo é estimado; sem preço configurado, só tokens.
CUSTO_POR_1K_TOKENS = float(os.environ.get("CDA_CUSTO_POR_1K_TOKENS", "0") or "0")
uso_glm: dict[str, float] = {"tokens": 0, "chamadas": 0, "custo_usd": 0.0}
_ultimo_reporte_tokens = 0.0


def _contabilizar_uso(
    system_prompt: str, user_message: str, resposta: str, usage: dict[str, Any] | None,
) -> None:
    """Registra tokens/custo da chamada no acumulador e no BudgetMonitor."""
    if usage and isinstance(usage.get("total_tokens"), int) and usage["total_tokens"] > 0:
        tokens = usage["total_tokens"]
    else:
        # Estimativa honesta quando a API não reporta usage: ~4 chars/token.
        tokens = (len(system_prompt) + len(user_message) + len(resposta)) // 4
    custo = tokens / 1000.0 * CUSTO_POR_1K_TOKENS
    uso_glm["tokens"] += tokens
    uso_glm["chamadas"] += 1
    uso_glm["custo_usd"] += custo
    try:
        from viableos.cda.budget_monitor import budget_monitor
        budget_monitor.registrar_uso("CDA", tokens=tokens, chamadas=1, custo_usd=custo)
    except Exception:
        pass  # contabilidade nunca derruba a chamada


def tokens_desde_ultimo_tick() -> int:
    """Delta de tokens desde a última chamada — para o heartbeat do clock."""
    global _ultimo_reporte_tokens
    delta = int(uso_glm["tokens"] - _ultimo_reporte_tokens)
    _ultimo_reporte_tokens = uso_glm["tokens"]
    return delta


async def glm_chat(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Envia mensagem ao GLM 5.2 e retorna a resposta."""
    if IPEAGPT_API_KEY:
        proxy = {"https://": PROXY_URL} if PROXY_URL else None
        async with httpx.AsyncClient(proxies=proxy) as client:
            resp = await client.post(
                IPEAGPT_URL,
                headers={
                    "Authorization": f"Bearer {IPEAGPT_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "glm-5-52b-0106",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            resp.raise_for_status()
            corpo = resp.json()
            resposta = corpo["choices"][0]["message"]["content"]
            _contabilizar_uso(system_prompt, user_message, resposta, corpo.get("usage"))
            return resposta
    else:
        resposta = _mock_glm(system_prompt, user_message)
        _contabilizar_uso(system_prompt, user_message, resposta, None)
        return resposta


def _mock_glm(system_prompt: str, user_message: str) -> str:
    """Resposta simulada para desenvolvimento sem API key."""
    return json.dumps({
        "agente": "modo_desenvolvimento",
        "resposta": (
            f"[MOCK GLM] Prompt: {system_prompt[:60]}... "
            f"Mensagem: {user_message[:60]}..."
        ),
        "nota": "Configure IPEAGPT_API_KEY para respostas reais do GLM 5.2",
    })


def system_prompt_agente(
    nome: str,
    proposito: str,
    ferramentas: list[str],
    *,
    tipo: str = "s1",
    identidade: dict[str, Any] | None = None,
    modos: dict[str, Any] | None = None,
    cadeias: dict[str, Any] | None = None,
) -> str:
    """Gera o system prompt para um agente CDA.

    Usa prompts ricos em PT-BR quando identidade é fornecida,
    senão fallback para prompt básico.
    """
    if identidade and tipo.startswith("s1"):
        from viableos.cda.prompts import prompt_s1
        return prompt_s1(
            unidade={"name": nome, "purpose": proposito, "tools": ferramentas},
            identidade=identidade,
            regras=[],
            hitl={"approval_required": []},
            outras_unidades=[],
            modos=modos,
            cadeias=cadeias,
        )
    return (
        f"Você é {nome}, membro da CDA — Corporação Digital Autônoma "
        f"contratada para digitalizar processos do IPEA.\n\n"
        f"Propósito: {proposito}\n\n"
        f"Ferramentas disponíveis: {', '.join(ferramentas)}\n\n"
        f"Instruções:\n"
        f"1. Você é um membro autônomo da corporação, não uma interface\n"
        f"2. Tome decisões dentro da sua autonomia\n"
        f"3. Solicite decisão ao S5 se algo exceder sua alçada\n"
        f"4. Dispare sinal algédonico se emergência\n"
        f"5. Registre todas as ações no histórico\n"
        f"6. Seja direto e objetivo"
    )
