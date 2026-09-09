"""Orquestrador recursivo — conecta níveis VSM entre si.

Três mecanismos de conexão entre níveis N e N+1:

1. Bargain: S3(N) negocia recursos com S3(N+1) de cada subnível
2. Algêdonico: canal(N+1) → S5(N) direto, sem filtro hierárquico
3. Auditoria: S3*(N) audita conformidade dos subníveis S1
"""

from __future__ import annotations

import logging
from typing import Any

from viableos.cda.algedonic import GravidadeSinal, TipoGatilho
from viableos.cda.recursao.nivel import NivelVSM

logger = logging.getLogger(__name__)


class OrquestradorRecursivo:
    """Mantém a consistência entre níveis VSM recursivos."""

    def __init__(self, raiz: NivelVSM):
        self.raiz = raiz

    def propagar_sinais(self) -> int:
        """Sobe sinais não respondidos de subníveis ao S5 do nível pai.
        
        Valida comunicação via topology antes de propagar.
        Regra: todo sinal pendente em subnível N+1 é copiado como
        sinal de mesma gravidade no canal do nível N.
        """
        total = [0]
        self._propagar_para_cima(self.raiz, total)
        return total[0]

    def _propagar_para_cima(self, nivel: NivelVSM, total: list[int]) -> None:
        from viableos.cda.topology import topology_validator
        for sub in nivel.listar_subniveis():
            sinais_pendentes = [
                s for s in sub.canal.todos() if s.resolucao is None
            ]
            for s in sinais_pendentes:
                # Dedup: sinal só sobe uma vez por nível-destino — sem isso,
                # cada tick copia de novo e a Sala de Op inunda (bug registrado
                # na docs/audits/2026-09-03-coerencia-cda.md §2.2).
                if nivel.nome in s.propagado_para:
                    continue

                # Validar via topology (NivelVSM não tem tipo VSM — usa nível numérico)
                nivel_r = f"s{sub.nivel}" if sub.nivel <= 5 else f"sub{sub.nivel}"
                nivel_d = f"s{nivel.nivel}" if nivel.nivel <= 5 else f"sub{nivel.nivel}"
                resultado = topology_validator.validar(
                    remetente=sub.nome,
                    destinatario=nivel.nome,
                    nivel_remetente=nivel_r,
                    nivel_destinatario=nivel_d,
                )
                if not resultado.permitido:
                    logger.warning(
                        "Sinal %s bloqueado pela topologia: %s",
                        s.id, resultado.motivo,
                    )
                    continue

                nivel.canal.disparar(
                    fonte=f"{sub.nome}:{s.fonte}",
                    gravidade=s.gravidade,
                    gatilho=s.gatilho,
                    assunto=f"[{sub.nome}] {s.assunto}",
                    mensagem=s.mensagem,
                    contexto=s.contexto,
                )
                s.propagado_para.append(nivel.nome)
                total[0] += 1
            self._propagar_para_cima(sub, total)

    def auditar(self) -> list[dict[str, Any]]:
        """S3* de cada nível audita seus subníveis.
        
        Retorna relatórios de auditoria para toda a árvore.
        """
        relatorios: list[dict[str, Any]] = []
        self._auditar_nivel(self.raiz, relatorios)
        return relatorios

    def _auditar_nivel(self, nivel: NivelVSM, relatorios: list[dict[str, Any]]) -> None:
        from viableos.cda.bratman import agenda_bratman

        for sub in nivel.listar_subniveis():
            decisoes_pendentes = len(sub.motor.pendentes())
            sinais_vermelhos = len(sub.canal.pendentes(GravidadeSinal.VERMELHO))
            agentes_offline = sum(
                1 for a in sub.listar_agentes()
                if a.status.value == "erro"
            )
            intencoes_ativas = sum(
                len(agenda_bratman.obter_motor(a.nome).intencoes_ativas)
                for a in sub.listar_agentes()
            )
            conflitos = len(agenda_bratman.verificar_coerencia())

            status = "conforme"
            if sinais_vermelhos > 0 or agentes_offline > 0:
                status = "critico"
            elif decisoes_pendentes > 3 or conflitos > 0:
                status = "atencao"

            relatorios.append({
                "nivel": sub.nome,
                "nivel_num": sub.nivel,
                "status": status,
                "agentes": sub.total_agentes(),
                "decisoes_pendentes": decisoes_pendentes,
                "sinais_vermelhos": sinais_vermelhos,
                "agentes_offline": agentes_offline,
                "intencoes_ativas": intencoes_ativas,
                "conflitos_intencoes": conflitos,
                "proposito": sub.proposito,
                "parent": nivel.nome,
            })
            self._auditar_nivel(sub, relatorios)

    def auditar_regras(self) -> list[dict[str, Any]]:
        """Audita as 6 regras inegociáveis em toda a CDA (raiz incluída)."""
        from viableos.cda.auditoria_regras import auditoria_seis_regras

        agentes = [a.to_dict() for a in self.raiz.listar_agentes()]
        sinais = []
        decisoes_historico = []
        for nivel in [self.raiz, *self._todos_subniveis()]:
            sinais.extend(nivel.canal.to_dict())
            for d in nivel.motor.historico(1000):
                decisoes_historico.append({
                    "id": d.id,
                    "solicitante": d.solicitante,
                    "contexto": d.contexto,
                    "opcoes": d.opcoes,
                    "justificativa": d.justificativa,
                    "resolucao": d.resolucao,
                    "status": d.status.value,
                    "papel_origem": d.papel_origem,
                    "papel_aprovacao": d.papel_aprovacao,
                })

        estado = {
            "agentes": agentes,
            "sinais": sinais,
            "decisoes_historico": decisoes_historico,
        }
        resultados = auditoria_seis_regras.auditar(estado)
        return [
            {
                "regra": r.regra,
                "descricao": r.descricao,
                "status": r.status.value,
                "detalhes": r.detalhes,
            }
            for r in resultados
        ]

    def _todos_subniveis(self) -> list[NivelVSM]:
        niveis = []

        def _coletar(n: NivelVSM) -> None:
            for sub in n.listar_subniveis():
                niveis.append(sub)
                _coletar(sub)

        _coletar(self.raiz)
        return niveis

    def arvore_para_dict(self) -> dict[str, Any]:
        """Serializa a árvore completa para visualização.
        
        Inclui intenções Bratman por agente.
        """
        return self._nivel_para_dict(self.raiz)

    def _nivel_para_dict(self, nivel: NivelVSM) -> dict[str, Any]:
        from viableos.cda.bratman import agenda_bratman

        agentes_data = []
        for a in nivel._agentes.values():
            data = a.to_dict()
            motor = agenda_bratman.obter_motor(a.nome)
            data["intencoes"] = motor.listar(apenas_ativas=True)
            agentes_data.append(data)

        return {
            "id": nivel.id,
            "nome": nivel.nome,
            "nivel": nivel.nivel,
            "proposito": nivel.proposito,
            "proposito_completo": nivel.proposito_completo(),
            "agentes": agentes_data,
            "decisoes": nivel.motor.to_dict(),
            "sinais_pendentes": [
                {
                    "id": s.id,
                    "fonte": s.fonte,
                    "gravidade": s.gravidade.value,
                    "gatilho": s.gatilho.value,
                    "assunto": s.assunto,
                    "mensagem": s.mensagem,
                    "timestamp": s.timestamp,
                }
                for s in nivel.canal.pendentes()
            ],
            "subniveis": [
                self._nivel_para_dict(sub) for sub in nivel.listar_subniveis()
            ],
        }


orquestrador: OrquestradorRecursivo | None = None


def inicializar_orquestrador(raiz: NivelVSM) -> OrquestradorRecursivo:
    global orquestrador
    orquestrador = OrquestradorRecursivo(raiz)
    return orquestrador
