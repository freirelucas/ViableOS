"""Health check da CDA — validação estática (boot) + periódica (runtime).

Complementa auditoria_regras.py (que verifica R1-R6 em runtime) com checks
de completude, segurança, comportamento e integridade da configuração.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckItem:
    """Resultado de um check individual."""
    nome: str
    categoria: str
    passou: bool
    severidade: str  # "ok", "info", "warning", "critical"
    detalhes: str = ""
    sugestao: str = ""


@dataclass
class RelatorioHealthCheck:
    """Relatório consolidado de health check."""
    momento: str  # "boot" ou "periodico"
    total_checks: int = 0
    passes: int = 0
    warnings: int = 0
    criticals: int = 0
    itens: list[CheckItem] = field(default_factory=list)

    @property
    def saudavel(self) -> bool:
        return self.criticals == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "momento": self.momento,
            "total": self.total_checks,
            "passes": self.passes,
            "warnings": self.warnings,
            "criticals": self.criticals,
            "saudavel": self.saudavel,
            "itens": [
                {
                    "nome": i.nome,
                    "categoria": i.categoria,
                    "passou": i.passou,
                    "severidade": i.severidade,
                    "detalhes": i.detalhes,
                    "sugestao": i.sugestao,
                }
                for i in self.itens
            ],
        }


# ── Checks de boot (validação estática da config) ──────────────


def _check_r1_llm_somente_s1(config: dict[str, Any]) -> CheckItem:
    """R1: LLM deve operar apenas no S1. Verifica modelos e tools."""
    vs = config.get("viable_system", config)
    agentes = vs.get("agents", [])

    s1_tools_glm = set()
    s2_plus_tools_glm = set()

    for agente in agentes:
        tipo = agente.get("tipo", "").lower()
        ferramentas = set(agente.get("ferramentas", []))
        tem_llm = any("glm" in t.lower() for t in ferramentas)

        if tipo.startswith("s1"):
            s1_tools_glm.update(t for t in ferramentas if "glm" in t.lower())
        elif tem_llm:
            s2_plus_tools_glm.update(t for t in ferramentas if "glm" in t.lower())

    if s2_plus_tools_glm:
        return CheckItem(
            nome="R1: LLM apenas no S1",
            categoria="Constituicao",
            passou=False,
            severidade="critical",
            detalhes=f"Agentes S2-S5 com tools LLM: {s2_plus_tools_glm}",
            sugestao="Remover tools LLM de agentes S2-S5. R1: LLM opera exclusivamente no S1.",
        )
    return CheckItem(
        nome="R1: LLM apenas no S1",
        categoria="Constituicao",
        passou=True,
        severidade="ok",
        detalhes="Apenas agentes S1 possuem tools LLM",
    )


def _check_r2_envelope_reversivel(config: dict[str, Any]) -> CheckItem:
    """R2: Todos os S1 devem ter git (envelope reversível)."""
    vs = config.get("viable_system", config)
    agentes = vs.get("agents", [])

    s1_sem_git = []
    for agente in agentes:
        tipo = agente.get("tipo", "").lower()
        if tipo.startswith("s1"):
            ferramentas = [f.lower() for f in agente.get("ferramentas", [])]
            if "git" not in ferramentas:
                s1_sem_git.append(agente.get("nome", "?"))

    if s1_sem_git:
        return CheckItem(
            nome="R2: Envelope reversível (git)",
            categoria="Constituicao",
            passou=False,
            severidade="warning",
            detalhes=f"Agentes S1 sem git: {', '.join(s1_sem_git)}",
            sugestao="Adicionar 'git' às ferramentas de todos os agentes S1.",
        )
    return CheckItem(
        nome="R2: Envelope reversível (git)",
        categoria="Constituicao",
        passou=True,
        severidade="ok",
        detalhes="Todos os agentes S1 possuem git",
    )


def _check_r3_anticorrelacao(config: dict[str, Any]) -> CheckItem:
    """R3: S3* deve usar modelo/provider diferente de S1."""
    vs = config.get("viable_system", config)
    agentes = vs.get("agents", [])

    s1_modelos = set()
    s3star_modelos = set()

    for agente in agentes:
        tipo = agente.get("tipo", "").lower()
        modelo = agente.get("modelo", "")
        if tipo.startswith("s1"):
            s1_modelos.add(modelo)
        elif "s3" in tipo and "audit" in tipo:
            s3star_modelos.add(modelo)

    if s3star_modelos and s1_modelos:
        overlap = s1_modelos & s3star_modelos
        if overlap:
            return CheckItem(
                nome="R3: Anti-correlação S3* ≠ S1",
                categoria="Constituicao",
                passou=False,
                severidade="critical",
                detalhes=f"S3* e S1 compartilham modelos: {overlap}",
                sugestao="S3* deve usar modelo/provider diferente de S1 (anti-correlação).",
            )
        s1_providers = {m.split("/")[0] if "/" in m else "local" for m in s1_modelos}
        s3star_providers = {m.split("/")[0] if "/" in m else "local" for m in s3star_modelos}
        if s1_providers & s3star_providers:
            return CheckItem(
                nome="R3: Anti-correlação S3* ≠ S1",
                categoria="Constituicao",
                passou=False,
                severidade="warning",
                detalhes=f"S3* e S1 usam mesmo provider: {s1_providers & s3star_providers}",
                sugestao="Considere usar provider diferente para S3* (ex: Claude vs GLM).",
            )

    return CheckItem(
        nome="R3: Anti-correlação S3* ≠ S1",
        categoria="Constituicao",
        passou=True,
        severidade="ok",
        detalhes="S3* usa modelo/provider diferente de S1",
    )


def _check_r5_s5_humano(config: dict[str, Any]) -> CheckItem:
    """R5: S5 deve ser sempre humano."""
    vs = config.get("viable_system", config)
    agentes = vs.get("agents", [])

    for agente in agentes:
        tipo = agente.get("tipo", "").lower()
        if "s5" in tipo:
            return CheckItem(
                nome="R5: S5 é humano",
                categoria="Constituicao",
                passou=False,
                severidade="critical",
                detalhes=f"Agente S5 encontrado: {agente.get('nome', '?')}. S5 deve ser sempre humano.",
                sugestao="Remover agente S5. S5 é a Diretora (humana), não um agente LLM.",
            )
    return CheckItem(
        nome="R5: S5 é humano",
        categoria="Constituicao",
        passou=True,
        severidade="ok",
        detalhes="Nenhum agente S5 encontrado (correto: S5 é humano)",
    )


def _check_4_gatilhos(config: dict[str, Any]) -> CheckItem:
    """R4: Apenas 4 gatilhos algêdonicos específicos."""
    vs = config.get("viable_system", config)
    gatilhos = vs.get("algedonic_triggers", [])

    gatilhos_esperados = {
        "timeout_decisao", "desvio_orcamento",
        "conflito_agentes", "oportunidade_estrategica",
    }

    if gatilhos:
        gatilhos_encontrados = {g.get("tipo", "").lower() for g in gatilhos if isinstance(g, dict)}
        extras = gatilhos_encontrados - gatilhos_esperados
        if extras:
            return CheckItem(
                nome="R4: 4 gatilhos algêdonicos",
                categoria="Constituicao",
                passou=False,
                severidade="warning",
                detalhes=f"Gatilhos extras encontrados: {extras}",
                sugestao="Apenas 4 gatilhos são permitidos: timeout_decisao, desvio_orcamento, conflito_agentes, oportunidade_estrategica.",
            )

    return CheckItem(
        nome="R4: 4 gatilhos algêdonicos",
        categoria="Constituicao",
        passou=True,
        severidade="ok",
        detalhes="Configuração de gatilhos algêdonicos dentro do permitido",
    )


def _check_completude_sistemas(config: dict[str, Any]) -> list[CheckItem]:
    """Verifica se todos os sistemas VSM estão presentes."""
    vs = config.get("viable_system", config)
    checks = []

    sistemas = {
        "S1": ("Operações", vs.get("agents", [])),
        "S2": ("Coordenação", vs.get("coordination", [])),
        "S3": ("Gestão", vs.get("management", [])),
        "S3*": ("Auditoria", vs.get("audit", [])),
        "S4": ("Inteligência", vs.get("intelligence", [])),
    }

    for sys, (nome, dados) in sistemas.items():
        presente = bool(dados)
        checks.append(CheckItem(
            nome=f"Completude {sys} ({nome})",
            categoria="Estrutura",
            passou=presente,
            severidade="ok" if presente else "warning",
            detalhes=f"{sys} {'configurado' if presente else 'não configurado'}",
            sugestao="" if presente else f"Configurar {sys} ({nome}) na árvore VSM",
        ))

    return checks


def _check_seguranca(config: dict[str, Any]) -> list[CheckItem]:
    """Verifica segurança: tools sensíveis, provider correlation, never_do."""
    vs = config.get("viable_system", config)
    checks = []

    # Provider correlation (S1 vs S3*)
    routing = vs.get("model_routing", {})
    s1_routine = routing.get("s1_routine", "")
    s3star_audit = routing.get("s3_star_audit", "")
    if s1_routine and s3star_audit:
        s1_provider = s1_routine.split("/")[0]
        s3star_provider = s3star_audit.split("/")[0]
        if s1_provider == s3star_provider:
            checks.append(CheckItem(
                nome="Provider correlation S1-S3*",
                categoria="Seguranca",
                passou=False,
                severidade="warning",
                detalhes=f"S1 e S3* usam mesmo provider: {s1_provider}",
                sugestao="Use provider diferente para S3* para evitar erros correlacionados.",
            ))
        else:
            checks.append(CheckItem(
                nome="Provider correlation S1-S3*",
                categoria="Seguranca",
                passou=True,
                severidade="ok",
                detalhes=f"Providers distintos: S1={s1_provider}, S3*={s3star_provider}",
            ))

    return checks


def _check_comportamento(config: dict[str, Any]) -> list[CheckItem]:
    """Verifica specs comportamentais: modos, escalação, anti-loop."""
    vs = config.get("viable_system", config)
    checks = []

    # Operational modes
    modos = vs.get("operational_modes", {})
    if modos:
        checks.append(CheckItem(
            nome="Modos operacionais",
            categoria="Comportamento",
            passou=True,
            severidade="ok",
            detalhes="Modos operacionais definidos",
        ))
    else:
        checks.append(CheckItem(
            nome="Modos operacionais",
            categoria="Comportamento",
            passou=False,
            severidade="info",
            detalhes="Modos operacionais não definidos",
            sugestao="Definir modos Normal/Elevated/Crisis com triggers.",
        ))

    # Escalation chains
    cadeias = vs.get("escalation_chains", {})
    if cadeias:
        checks.append(CheckItem(
            nome="Cadeias de escalação",
            categoria="Comportamento",
            passou=True,
            severidade="ok",
            detalhes="Cadeias de escalação definidas",
        ))
    else:
        checks.append(CheckItem(
            nome="Cadeias de escalação",
            categoria="Comportamento",
            passou=False,
            severidade="warning",
            detalhes="Cadeias de escalação não definidas",
            sugestao="Definir caminhos operacional/quality/strategic + algédonico.",
        ))

    # Anti-loop rules
    regras = vs.get("coordination_rules", [])
    tem_anti_loop = any(
        "loop" in r.get("trigger", "").lower() or "repeat" in r.get("trigger", "").lower()
        for r in regras if isinstance(r, dict)
    )
    if tem_anti_loop:
        checks.append(CheckItem(
            nome="Anti-loop rules",
            categoria="Comportamento",
            passou=True,
            severidade="ok",
            detalhes="Regra anti-loop encontrada",
        ))
    else:
        checks.append(CheckItem(
            nome="Anti-loop rules",
            categoria="Comportamento",
            passou=False,
            severidade="warning",
            detalhes="Nenhuma regra anti-loop encontrada",
            sugestao="Adicionar: 'Agente repete output 3+ vezes → parar e escalar'.",
        ))

    return checks


# ── Health check principal ──────────────────────────────────────


def health_check_boot(config: dict[str, Any]) -> RelatorioHealthCheck:
    """Health check no boot da CDA — valida config antes de criar agentes."""
    relatorio = RelatorioHealthCheck(momento="boot")

    # Checks constitucionais
    relatorio.itens.append(_check_r1_llm_somente_s1(config))
    relatorio.itens.append(_check_r2_envelope_reversivel(config))
    relatorio.itens.append(_check_r3_anticorrelacao(config))
    relatorio.itens.append(_check_r5_s5_humano(config))
    relatorio.itens.append(_check_4_gatilhos(config))

    # Completude
    relatorio.itens.extend(_check_completude_sistemas(config))

    # Segurança
    relatorio.itens.extend(_check_seguranca(config))

    # Comportamento
    relatorio.itens.extend(_check_comportamento(config))

    # Consolidar
    relatorio.total_checks = len(relatorio.itens)
    relatorio.passes = sum(1 for i in relatorio.itens if i.passou)
    relatorio.warnings = sum(1 for i in relatorio.itens if i.severidade == "warning")
    relatorio.criticals = sum(1 for i in relatorio.itens if i.severidade == "critical")

    return relatorio


def health_check_periodico(estado_cda: dict[str, Any]) -> RelatorioHealthCheck:
    """Health check periódico — verifica estado runtime da CDA.

    Args:
        estado_cda: dict com estado atual (agentes, decisões, sinais, etc.)
    """
    relatorio = RelatorioHealthCheck(momento="periodico")

    # Verificar sinais algêdonicos pendentes
    sinais = estado_cda.get("sinais_pendentes", [])
    sinais_vermelhos = [s for s in sinais if s.get("gravidade") == "vermelho"]
    if sinais_vermelhos:
        relatorio.itens.append(CheckItem(
            nome="Sinais algêdonicos vermelhos",
            categoria="Emergencia",
            passou=False,
            severidade="critical",
            detalhes=f"{len(sinais_vermelhos)} sinais vermelhos pendentes",
            sugestao="Responder aos sinais vermelhos imediatamente (prazo 24h).",
        ))
    else:
        relatorio.itens.append(CheckItem(
            nome="Sinais algêdonicos vermelhos",
            categoria="Emergencia",
            passou=True,
            severidade="ok",
            detalhes=f"{len([s for s in sinais if s.get('gravidade') == 'vermelho'])} sinais vermelhos",
        ))

    # Verificar decisões pendentes há muito tempo
    decisoes = estado_cda.get("decisoes_pendentes", [])
    if len(decisoes) > 5:
        relatorio.itens.append(CheckItem(
            nome="Decisões pendentes acumuladas",
            categoria="Operacional",
            passou=False,
            severidade="warning",
            detalhes=f"{len(decisoes)} decisões pendentes",
            sugestao="Resolver ou delegar decisões pendentes.",
        ))
    else:
        relatorio.itens.append(CheckItem(
            nome="Decisões pendentes",
            categoria="Operacional",
            passou=True,
            severidade="ok",
            detalhes=f"{len(decisoes)} decisões pendentes",
        ))

    # Verificar agentes offline
    agentes = estado_cda.get("agentes", [])
    offline = [a for a in agentes if a.get("status") != "online"]
    if offline:
        relatorio.itens.append(CheckItem(
            nome="Agentes offline",
            categoria="Disponibilidade",
            passou=False,
            severidade="warning",
            detalhes=f"{len(offline)} agentes offline: {', '.join(a.get('nome', '?') for a in offline)}",
            sugestao="Verificar conectividade dos agentes.",
        ))
    else:
        relatorio.itens.append(CheckItem(
            nome="Agentes online",
            categoria="Disponibilidade",
            passou=True,
            severidade="ok",
            detalhes=f"Todos os {len(agentes)} agentes online",
        ))

    # Verificar orçamento
    uso_budget = estado_cda.get("budget_usage", [])
    for sistema in uso_budget:
        percentual = sistema.get("percentual", 0)
        if percentual >= 95:
            relatorio.itens.append(CheckItem(
                nome=f"Orçamento {sistema.get('sistema', '?')}",
                categoria="Orcamento",
                passou=False,
                severidade="critical",
                detalhes=f"{sistema.get('sistema', '?')}: {percentual}% do orçamento utilizado",
                sugestao="Considerar downgrade de modelo ou aumento de orçamento.",
            ))
        elif percentual >= 80:
            relatorio.itens.append(CheckItem(
                nome=f"Orçamento {sistema.get('sistema', '?')}",
                categoria="Orcamento",
                passou=False,
                severidade="warning",
                detalhes=f"{sistema.get('sistema', '?')}: {percentual}% do orçamento utilizado",
                sugestao="Monitorar uso de tokens.",
            ))

    # Consolidar
    relatorio.total_checks = len(relatorio.itens)
    relatorio.passes = sum(1 for i in relatorio.itens if i.passou)
    relatorio.warnings = sum(1 for i in relatorio.itens if i.severidade == "warning")
    relatorio.criticals = sum(1 for i in relatorio.itens if i.severidade == "critical")

    return relatorio
