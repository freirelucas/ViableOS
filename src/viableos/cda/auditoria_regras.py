"""Auditoria das seis regras inegociáveis da Constituição S5.

Executada pelo S3* a cada ciclo de auditoria.
Cada regra tem um check determinístico (não usa LLM).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StatusRegra(str, Enum):
    CONFORME = "conforme"
    VIOLADO = "violado"
    NAO_APLICAVEL = "nao_aplicavel"


@dataclass
class ResultadoAuditoria:
    regra: str = ""
    descricao: str = ""
    status: StatusRegra = StatusRegra.CONFORME
    detalhes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditoriaSeisRegras:
    """Verifica as 6 regras inegociáveis em runtime."""

    def __init__(self):
        self._historico: list[ResultadoAuditoria] = []

    def auditar(self, estado_cda: dict[str, Any]) -> list[ResultadoAuditoria]:
        resultados: list[ResultadoAuditoria] = []

        resultados.append(self._r1_llm_apenas_s1(estado_cda))
        resultados.append(self._r2_envelope_reversivel(estado_cda))
        resultados.append(self._r3_anticorrelacao(estado_cda))
        resultados.append(self._r4_gatilhos_algedonicos(estado_cda))
        resultados.append(self._r5_s5_humano(estado_cda))
        resultados.append(self._r6_cascata_rastreavel(estado_cda))

        self._historico.extend(resultados)
        return resultados

    def _r1_llm_apenas_s1(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R1: LLM só no S1. S2-S5 usam canais determinísticos."""
        violacoes = []
        for agente in estado.get("agentes", []):
            tipo = agente.get("tipo", "")
            ferramentas = agente.get("ferramentas", [])
            # S1 é o ÚNICO nível que pode ter LLM/tools de LLM
            if not tipo.startswith("s1"):
                for f in ferramentas:
                    f_lower = f.lower()
                    if any(kw in f_lower for kw in ("glm", "llm", "chat", "linguagem")):
                        violacoes.append(f"{agente.get('nome')} ({tipo}) usa {f}")

        if violacoes:
            return ResultadoAuditoria(
                regra="R1",
                descricao="LLM só no S1",
                status=StatusRegra.VIOLADO,
                detalhes="; ".join(violacoes),
            )
        return ResultadoAuditoria(
            regra="R1",
            descricao="LLM só no S1",
            status=StatusRegra.CONFORME,
            detalhes="Apenas agentes S1 possuem ferramentas LLM",
        )

    def _r2_envelope_reversivel(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R2: Toda escrita é reversível. S1 deve ter git. S2-S5 NÃO precisam."""
        agentes_s1 = [
            a for a in estado.get("agentes", [])
            if a.get("tipo", "").startswith("s1")
        ]
        sem_git = [
            a.get("nome", "") for a in agentes_s1
            if "git" not in [f.lower() for f in a.get("ferramentas", [])]
        ]
        if sem_git:
            return ResultadoAuditoria(
                regra="R2",
                descricao="Envelope de escrita reversível",
                status=StatusRegra.VIOLADO,
                detalhes=f"Agentes S1 sem git: {', '.join(sem_git)}",
            )
        return ResultadoAuditoria(
            regra="R2",
            descricao="Envelope de escrita reversível",
            status=StatusRegra.CONFORME,
            detalhes=f"Todos os {len(agentes_s1)} agentes S1 possuem git",
        )

    def _r3_anticorrelacao(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R3: S3* usa modelo/provider diferente de S1 (anti-correlação)."""
        agentes = estado.get("agentes", [])
        modelos_s1 = set()
        modelos_s3star = set()
        providers_s1 = set()
        providers_s3star = set()

        for a in agentes:
            tipo = a.get("tipo", "")
            modelo = a.get("modelo", "")
            provider = modelo.split("/")[0] if "/" in modelo else modelo

            if tipo.startswith("s1"):
                modelos_s1.add(modelo)
                providers_s1.add(provider)
            elif "s3" in tipo and "audit" in tipo:
                modelos_s3star.add(modelo)
                providers_s3star.add(provider)

        if not modelos_s1 or not modelos_s3star:
            return ResultadoAuditoria(
                regra="R3",
                descricao="S3* anti-correlacionado",
                status=StatusRegra.NAO_APLICAVEL,
                detalhes="S1 ou S3* não configurados — impossível verificar",
            )

        overlap_modelos = modelos_s1 & modelos_s3star
        if overlap_modelos:
            return ResultadoAuditoria(
                regra="R3",
                descricao="S3* anti-correlacionado",
                status=StatusRegra.VIOLADO,
                detalhes=f"S3* e S1 compartilham modelos: {overlap_modelos}",
            )

        overlap_providers = providers_s1 & providers_s3star
        if overlap_providers:
            return ResultadoAuditoria(
                regra="R3",
                descricao="S3* anti-correlacionado",
                status=StatusRegra.VIOLADO,
                detalhes=f"S3* e S1 usam mesmo provider: {overlap_providers}",
            )

        return ResultadoAuditoria(
            regra="R3",
            descricao="S3* anti-correlacionado",
            status=StatusRegra.CONFORME,
            detalhes=f"S3* usa modelos diferentes de S1: {modelos_s3star} vs {modelos_s1}",
        )

    def _r4_gatilhos_algedonicos(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R4: Apenas 4 gatilhos algedônicos."""
        gatilhos_esperados = {
            "timeout_decisao", "desvio_orcamento",
            "conflito_agentes", "oportunidade_estrategica",
        }
        gatilhos_usados = set()
        for sinal in estado.get("sinais", []):
            g = sinal.get("gatilho", "")
            if g:
                gatilhos_usados.add(g)

        extras = gatilhos_usados - gatilhos_esperados
        if extras:
            return ResultadoAuditoria(
                regra="R4",
                descricao="Quatro gatilhos algedônicos",
                status=StatusRegra.VIOLADO,
                detalhes=f"Gatilhos não-previstos: {', '.join(extras)}",
            )
        return ResultadoAuditoria(
            regra="R4",
            descricao="Quatro gatilhos algedônicos",
            status=StatusRegra.CONFORME,
            detalhes=f"Apenas gatilhos previstos: {', '.join(gatilhos_esperados)}",
        )

    def _r5_s5_humano(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R5: S5 é sempre humano (Diretora)."""
        # Verifica se existe agente com tipo S5 que não seja a Diretora
        for a in estado.get("agentes", []):
            if a.get("tipo") == "s5_diretor":
                return ResultadoAuditoria(
                    regra="R5",
                    descricao="S5 é humano",
                    status=StatusRegra.VIOLADO,
                    detalhes=f"S5 ocupado por agente: {a.get('nome')}",
                )
        return ResultadoAuditoria(
            regra="R5",
            descricao="S5 é humano",
            status=StatusRegra.CONFORME,
            detalhes="Nenhum agente no papel S5. Diretora humana no comando.",
        )

    def _r6_cascata_rastreavel(self, estado: dict[str, Any]) -> ResultadoAuditoria:
        """R6: toda decisão tem cascata completa — solicitante, contexto,
        opções, justificativa, resolução (Constituição S5)."""
        decisoes = estado.get("decisoes_historico", [])
        sem_cascata = []
        sem_solicitante = []
        sem_justificativa = []
        aprovada_sem_resolucao = []
        for d in decisoes:
            cid = d.get("id", "?")
            if not d.get("contexto") or not d.get("opcoes"):
                sem_cascata.append(cid)
            if not d.get("solicitante"):
                sem_solicitante.append(cid)
            if not d.get("justificativa"):
                sem_justificativa.append(cid)
            # O enum real é aprovada/rejeitada/delegada — "resolvida" nunca
            # ocorria, o que cegava este check (auditoria 2026-09-03 §2.2).
            if d.get("status") == "aprovada" and not d.get("resolucao"):
                aprovada_sem_resolucao.append(cid)

        problemas = []
        if sem_cascata:
            problemas.append(f"sem contexto/opcoes: {', '.join(sem_cascata[:5])}")
        if sem_solicitante:
            problemas.append(f"sem solicitante: {', '.join(sem_solicitante[:5])}")
        if sem_justificativa:
            problemas.append(f"sem justificativa: {', '.join(sem_justificativa[:5])}")
        if aprovada_sem_resolucao:
            problemas.append(f"aprovada sem resolucao: {', '.join(aprovada_sem_resolucao[:5])}")

        if problemas:
            return ResultadoAuditoria(
                regra="R6",
                descricao="Cascata rastreável",
                status=StatusRegra.VIOLADO,
                detalhes="; ".join(problemas),
            )
        return ResultadoAuditoria(
            regra="R6",
            descricao="Cascata rastreável",
            status=StatusRegra.CONFORME,
            detalhes=f"Todas as {len(decisoes)} decisões têm cascata completa",
        )

    def taxa_discordancia(self, estado: dict[str, Any]) -> dict[str, Any]:
        """Taxa de discordância S5×proposta — registrada como dado, não veredito.

        Proxy estrutural (PaperBench, arXiv 2504.01848: replicação se mede por
        rubrica, não por impressão): dentre decisões aprovadas com opções, conta
        quantas tiveram resolução fora do conjunto proposto — o S5 humano
        discordou das alternativas colocadas pelo agente.
        """
        aprovadas = [
            d for d in estado.get("decisoes_historico", [])
            if d.get("status") == "aprovada" and d.get("opcoes")
        ]
        discordantes = [
            d for d in aprovadas
            if (d.get("resolucao") or "").strip()
            not in [o.strip() for o in d["opcoes"]]
        ]
        total = len(aprovadas)
        taxa = round(len(discordantes) / total, 3) if total else 0.0
        return {
            "total_analisadas": total,
            "discordantes": len(discordantes),
            "taxa": taxa,
            "nota": (
                "Dado bruto de replicação/divergência — não é veredito de "
                "conformidade (S3* real com LLM anticorrelacionado é roadmap)."
            ),
        }

    def historico(self) -> list[dict[str, Any]]:
        return [
            {
                "regra": r.regra,
                "descricao": r.descricao,
                "status": r.status.value,
                "detalhes": r.detalhes,
                "timestamp": r.timestamp,
            }
            for r in self._historico
        ]


auditoria_seis_regras = AuditoriaSeisRegras()
