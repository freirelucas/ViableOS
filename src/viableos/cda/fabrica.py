"""Fábrica da CDA — constrói a árvore recursiva de níveis VSM.

Arquitetura:
  Level 1: CDA (corporação)
    S5: Diretora (humana, não-agente)
    S4: Inteligência Estratégica
    S3: Gestão de Projetos
    S3*: Auditoria
    S2: Coordenação
    S1 (operacionais) = Projetos (Level 2)

  Level 2: Projeto N
    S5: Sponsor do Projeto (ex: DIDES, DIEST)
    S4: Inteligência do Projeto
    S3: Coordenação do Projeto
    S1 (operacionais) = Usuários finais (Level 3)

  Level 3: Usuário Final
    S5: O próprio usuário (representação externa)
    S1-S4: Seu sistema
"""

from __future__ import annotations

from viableos.cda.agente import AgenteGLM, StatusAgente, TipoAgente
from viableos.cda.algedonic import GravidadeSinal, TipoGatilho
from viableos.cda.bratman import EstrategiaCompromisso
from viableos.cda.glm import system_prompt_agente
from viableos.cda.recursao.nivel import NivelVSM
from viableos.cda.recursao.orquestrador import inicializar_orquestrador
from viableos.cda.recursao.clock import sistema_clocks, FrequenciaClock


class FabricaCDA:
    """Constrói e mantém a árvore recursiva da CDA."""

    def __init__(self):
        self.raiz: NivelVSM | None = None
        self._construir()

    def _construir(self) -> None:
        # ═══════════════════════════════════════════════════
        # Level 1: CDA
        # ═══════════════════════════════════════════════════
        cda = NivelVSM(
            nome="CDA",
            nivel=1,
            proposito="Digitalizar processos do IPEA como corporação autônoma de agentes GLM",
        )

        # S4: Inteligência Estratégica (OPEN — sempre reconsidera)
        # R1: S4 NÃO usa LLM — usa ferramentas determinísticas
        cda.adicionar_agente(AgenteGLM(
            nome="Inteligência Estratégica (S4)",
            tipo=TipoAgente.S4_INTELIGENCIA,
            proposito="Detectar oportunidades de digitalização, analisar portarias, planejar projetos futuros",
            ferramentas=["analise-deterministica", "corpus-historico", "dados-orcamentarios"],
            estrategia_compromisso=EstrategiaCompromisso.OPEN,
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Inteligência Estratégica (S4)",
                "Detectar oportunidades de digitalização no IPEA",
                ["analise-deterministica", "corpus-historico"],
            ),
        ))
        # S3: Gestão de Projetos
        cda.adicionar_agente(AgenteGLM(
            nome="Gestão de Projetos (S3)",
            tipo=TipoAgente.S3_GESTAO,
            proposito="Alocar recursos, definir prioridades, gerenciar cronograma dos projetos da CDA",
            ferramentas=["dashboard-alocacao", "workflow-aprovacao"],
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Gestão de Projetos (S3)",
                "Alocar recursos e priorizar projetos",
                ["dashboard-alocacao", "workflow-aprovacao"],
            ),
        ))
        # S3*: Auditoria (BLIND — nunca reconsidera) com modelo DIFERENTE de S1
        # Anti-correlação R3: S3* usa claude enquanto S1 usa glm
        # R1: S3* NÃO usa LLM — usa ferramentas determinísticas de auditoria
        cda.adicionar_agente(AgenteGLM(
            nome="Auditoria (S3*)",
            tipo=TipoAgente.S3_AUDITORIA,
            proposito="Auditar conformidade normativa e qualidade dos artefatos produzidos pela CDA e seus projetos",
            ferramentas=["conformidade-automatica", "verificacao-deterministica"],
            estrategia_compromisso=EstrategiaCompromisso.BLIND,
            modelo="claude-3-5-sonnet-20241022",
            system_prompt=system_prompt_agente(
                "Auditoria (S3*)",
                "Auditar conformidade e qualidade",
                ["conformidade-automatica", "verificacao-deterministica"],
            ),
        ))
        # S2: Coordenação
        cda.adicionar_agente(AgenteGLM(
            nome="Coordenação (S2)",
            tipo=TipoAgente.S2_COORDENACAO,
            proposito="Resolver conflitos entre agentes e projetos, coordenar fluxos entre níveis",
            ferramentas=["comite-gestor", "cronograma"],
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Coordenação (S2)",
                "Resolver conflitos e coordenar fluxos",
                ["comite-gestor", "cronograma"],
            ),
        ))

        # ═══════════════════════════════════════════════════
        # Level 2: Projeto 1 — Gestão de Bolsistas
        # ═══════════════════════════════════════════════════
        proj1 = NivelVSM(
            nome="Projeto 1",
            nivel=2,
            proposito="Automatizar o ciclo de gestão de bolsistas do IPEA",
        )

        proj1.adicionar_agente(AgenteGLM(
            nome="Agente Desenvolvedor",
            tipo=TipoAgente.S1_DESENVOLVEDOR,
            proposito="Escrever código, criar skills, expandir as ferramentas do Projeto 1",
            ferramentas=["python", "typescript", "git", "skills-editor"],
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Agente Desenvolvedor",
                "Escrever código e expandir as ferramentas do projeto",
                ["python", "typescript", "git", "skills-editor"],
            ),
        ))
        proj1.adicionar_agente(AgenteGLM(
            nome="Gestor de Bolsas",
            tipo=TipoAgente.S1_EXECUTOR,
            proposito="Operar o TR Generator e gerenciar o ciclo de bolsistas",
            ferramentas=["tr-generator", "glm-mentor", "acompanhamento-bolsistas", "git"],
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Gestor de Bolsas",
                "Operar TR Generator e gerenciar bolsistas",
                ["tr-generator", "glm-mentor"],
            ),
        ))
        proj1.adicionar_agente(AgenteGLM(
            nome="Analista de Processos",
            tipo=TipoAgente.S1_ANALISTA,
            proposito="Mapear fluxos de trabalho do IPEA no contexto do Projeto 1",
            ferramentas=["mapeamento-fluxos", "documentacao", "git"],
            modelo="glm-5-52b-0106",
            system_prompt=system_prompt_agente(
                "Analista de Processos",
                "Mapear fluxos e identificar automação",
                ["mapeamento-fluxos", "documentacao"],
            ),
        ))

        # ═══════════════════════════════════════════════════
        # Level 3: Usuário Final (Bolsinha/IPEA)
        # ═══════════════════════════════════════════════════
        user_padrao = NivelVSM(
            nome="Usuário Padrão",
            nivel=3,
            proposito="Interagir com o sistema de gestão de bolsistas como pesquisador/bolsista do IPEA",
        )

        proj1.adicionar_subnivel(user_padrao)

        # ═══════════════════════════════════════════════════
        # Montar árvore
        # ═══════════════════════════════════════════════════
        cda.adicionar_subnivel(proj1)
        self.raiz = cda

        # Inicializar orquestrador global
        inicializar_orquestrador(cda)

        async def tick_cda(tick: int) -> dict[str, Any]:
            from viableos.cda.recursao.orquestrador import orquestrador
            from viableos.cda.bratman import agenda_bratman
            from viableos.cda.glm import tokens_desde_ultimo_tick
            if not orquestrador:
                return {}

            # Gatilho R4-1+R4-2 e escalação: propagação algedônica entre níveis
            sinais_propagados = orquestrador.propagar_sinais()

            # Gatilho R4-1 (timeout): decisões pendentes além do prazo, por nível
            timeouts = 0
            decisoes_pendentes = 0
            niveis = [cda]
            while niveis:
                n = niveis.pop()
                niveis.extend(n.listar_subniveis())
                decisoes_pendentes += len(n.motor.pendentes())
                timeouts += len(n.canal.verificar_timeouts(n.motor.pendentes()))

            # Gatilho R4-3 (conflito): intenções incoerentes → sinal algédonico
            conflitos_disparados = 0
            for conflito in agenda_bratman.verificar_coerencia():
                ja_sinalizado = any(
                    s.gatilho == TipoGatilho.CONFLITO_AGENTES
                    and s.contexto.get("intencao_a") == conflito["intencao_a"]
                    and s.contexto.get("intencao_b") == conflito["intencao_b"]
                    for s in cda.canal.todos()
                )
                if ja_sinalizado:
                    continue
                cda.canal.disparar_conflito(
                    fonte="AgendaBratman",
                    agentes=[conflito["agente_a"], conflito["agente_b"]],
                    recurso=", ".join(conflito["recursos_conflitantes"]),
                    contexto_extra={
                        "intencao_a": conflito["intencao_a"],
                        "intencao_b": conflito["intencao_b"],
                    },
                )
                conflitos_disparados += 1

            # R4-4 (orçamento): desvio verificado no próprio tick
            # (BudgetMonitor é alimentado por glm.py; o sinal sobe no canal da raiz)
            try:
                from viableos.cda.budget_monitor import budget_monitor
                budget_monitor.verificar_desvio(tick=tick)
            except Exception:
                pass

            return {
                "decisoes": decisoes_pendentes,
                "sinais": sinais_propagados + timeouts + conflitos_disparados,
                "tokens_usados": tokens_desde_ultimo_tick(),
                "agentes": self.raiz.total_agentes() if self.raiz else 0,
            }

        # Registrar clocks por nível (não inicia — startup da app inicia)
        sistema_clocks.registrar("CDA", FrequenciaClock.ESTRATEGICO, on_tick=tick_cda)
        sistema_clocks.registrar("Projeto 1", FrequenciaClock.TATICO, on_tick=tick_cda)
        sistema_clocks.registrar("Usuário Padrão", FrequenciaClock.OPERACIONAL)

        # Ativar todos os agentes
        for a in self.raiz.listar_agentes():
            a.status = StatusAgente.ONLINE

    # ─── API de consulta ────────────────────────────────

    def listar_agentes(self) -> list[dict]:
        if not self.raiz:
            return []
        return [a.to_dict() for a in self.raiz.listar_agentes()]

    def obter_agente(self, nome: str) -> dict | None:
        if not self.raiz:
            return None
        a = self.raiz.obter_agente(nome)
        return a.to_dict() if a else None

    def obter_agente_obj(self, nome: str) -> AgenteGLM | None:
        if not self.raiz:
            return None
        return self.raiz.obter_agente(nome)

    def arvore(self) -> dict | None:
        if not self.raiz:
            return None
        from viableos.cda.recursao.orquestrador import orquestrador
        if orquestrador:
            return orquestrador.arvore_para_dict()
        return self.raiz.to_dict_profundo()


fabrica = FabricaCDA()
