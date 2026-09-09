"""API da Sala de Operação da CDA — arquitetura recursiva."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from viableos.cda.fabrica import fabrica
from viableos.cda.algedonic import GravidadeSinal, TipoGatilho
from viableos.cda.agente import StatusAgente
from viableos.cda.bratman import EstrategiaCompromisso, agenda_bratman
from viableos.cda.recursao.orquestrador import orquestrador
from viableos.cda.recursao.clock import sistema_clocks
from viableos.cda.recursao.bargain import protocolo_bargain
from viableos.api.auth import TokenPayload, require_s5

cda_router = APIRouter(prefix="/api/cda", tags=["cda"])


@cda_router.get("/tree")
def arvore_cda() -> dict[str, Any]:
    """Árvore completa da CDA com todos os níveis recursivos."""
    return fabrica.arvore() or {}


@cda_router.get("/niveis")
def listar_niveis() -> list[dict[str, Any]]:
    """Lista todos os níveis VSM da CDA."""
    niveis = []

    def _coletar(n: Any) -> None:
        niveis.append(n.to_dict())
        for sub in n.listar_subniveis():
            _coletar(sub)

    if fabrica.raiz:
        _coletar(fabrica.raiz)
    return niveis


@cda_router.get("/agentes")
def listar_agentes() -> list[dict[str, Any]]:
    return fabrica.listar_agentes()


@cda_router.get("/agentes/{nome}")
def obter_agente(nome: str) -> dict[str, Any] | None:
    a = fabrica.obter_agente_obj(nome)
    if a is None:
        return None
    if fabrica.raiz is None:
        return a.to_dict()
    nivel = _nivel_do_agente(nome)
    pendentes_do_agente = nivel.motor.pendentes() if nivel else []
    data = a.to_dict()
    data["decisoes_pendentes"] = [
        {
            "id": d.id,
            "assunto": d.assunto,
            "contexto": d.contexto,
            "urgencia": d.urgencia,
            "opcoes": d.opcoes,
            "criado_em": d.criado_em,
            "autonomia": d.autonomia.value,
            "status": d.status.value,
        }
        for d in pendentes_do_agente
        if d.solicitante == a.nome
    ]
    return data


@cda_router.post("/agentes/{nome}/atividade")
def definir_atividade(nome: str, payload: dict[str, str]) -> dict[str, str]:
    a = fabrica.obter_agente_obj(nome)
    if a is None:
        return {"status": "erro", "motivo": "agente nao encontrado"}
    a.definir_atividade(payload.get("atividade", ""))
    return {"status": "ok"}


@cda_router.post("/agentes/{nome}/decisao")
def solicitar_decisao(nome: str, payload: dict[str, Any]) -> dict[str, Any]:
    a = fabrica.obter_agente_obj(nome)
    if a is None:
        return {"status": "erro", "motivo": "agente nao encontrado"}

    # Encontrar o nível do agente para usar seu motor
    nivel = _nivel_do_agente(nome)
    if nivel is None:
        return {"status": "erro", "motivo": "nivel do agente nao encontrado"}

    try:
        d = nivel.motor.solicitar(
            solicitante=nome,
            tipo_solicitante=a.tipo.value,
            assunto=payload.get("assunto", ""),
            contexto=payload.get("contexto", ""),
            opcoes=payload.get("opcoes", []),
            urgencia=payload.get("urgencia", "media"),
            justificativa=payload.get("justificativa", ""),
            intencao_id=payload.get("intencao_id", ""),
        )
    except ValueError as e:
        return {"status": "erro", "motivo": str(e)}
    a.registrar_acao(f"Decisão solicitada: {d.assunto}", d.status.value)
    return {"status": "ok", "decisao_id": d.id, "autonomia": d.autonomia.value, "resultado": d.status.value}


@cda_router.get("/clocks")
def status_clocks() -> list[dict[str, Any]]:
    return sistema_clocks.status_todos()


@cda_router.get("/clocks/espiral")
def espiral_clocks() -> dict[str, Any]:
    return sistema_clocks.espiral_info()


@cda_router.get("/clocks/{nivel}")
def status_clock(nivel: str) -> dict[str, Any] | None:
    c = sistema_clocks.obter(nivel)
    if c is None:
        return None
    info = c.status()
    info["ultimos_heartbeats"] = c.ultimos_heartbeats(10)
    return info


@cda_router.post("/bargain/solicitar")
def solicitar_bargain(payload: dict[str, Any]) -> dict[str, str]:
    n = protocolo_bargain.solicitar(
        subnivel=payload["subnivel"],
        nivel_pai=payload["nivel_pai"],
        recursos=payload.get("recursos", []),
        justificativa=payload.get("justificativa", ""),
    )
    return {"status": "ok", "negociacao_id": n.id}


@cda_router.post("/bargain/avaliar/{negociacao_id}")
def avaliar_bargain(negociacao_id: str, payload: dict[str, Any]) -> dict[str, str]:
    if protocolo_bargain.avaliar(
        negociacao_id,
        alocacao=payload.get("alocacao", {}),
        contraproposta=payload.get("contraproposta", ""),
    ):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "negociacao nao encontrada ou ja respondida"}


@cda_router.get("/bargain/pendentes")
def bargain_pendentes(subnivel: str | None = None) -> list[dict[str, Any]]:
    return protocolo_bargain.to_dict(apenas_pendentes=True)


@cda_router.get("/bratman/agenda")
def agenda_intencoes() -> dict[str, Any]:
    return agenda_bratman.status_geral()


@cda_router.get("/bratman/intencoes/{agente_nome}")
def intencoes_agente(agente_nome: str, apenas_ativas: bool = False) -> list[dict[str, Any]]:
    motor = agenda_bratman.obter_motor(agente_nome)
    return motor.listar(apenas_ativas=apenas_ativas)


@cda_router.post("/bratman/adotar")
def adotar_intencao(payload: dict[str, Any]) -> dict[str, Any]:
    agente_nome = payload.get("agente", "")
    a = fabrica.obter_agente_obj(agente_nome)
    if a is None:
        return {"status": "erro", "motivo": "agente nao encontrado"}

    intencao = a.adotar_intencao(
        desejo=payload.get("desejo", ""),
        plano=payload.get("plano", ""),
        passos=payload.get("passos"),
        prioridade=payload.get("prioridade", 3),
    )
    if intencao is None:
        return {"status": "erro", "motivo": "intencao rejeitada pelo filtro de admissibilidade"}
    a.registrar_acao(f"Intenção adotada: {intencao.desejo}", "ativa")
    return {"status": "ok", "intencao_id": intencao.id, "desejo": intencao.desejo}


@cda_router.post("/bratman/executar/{intencao_id}")
def executar_passo_intencao(intencao_id: str) -> dict[str, Any]:
    for motor_nome in agenda_bratman._motores:
        motor = agenda_bratman._motores[motor_nome]
        for i in motor._intencoes:
            if i.id == intencao_id:
                resultado = motor.executar_passo(intencao_id)
                return resultado
    return {"status": "erro", "motivo": "intencao_nao_encontrada"}


@cda_router.get("/bratman/coerencia")
def coerencia_intencoes() -> list[dict[str, Any]]:
    return agenda_bratman.verificar_coerencia()


def _nivel_do_agente(nome: str) -> Any:
    """Encontra o NivelVSM que contém o agente."""
    def _buscar(nivel: Any) -> Any:
        if nome in nivel._agentes:
            return nivel
        for sub in nivel.listar_subniveis():
            encontrado = _buscar(sub)
            if encontrado:
                return encontrado
        return None
    if fabrica.raiz:
        return _buscar(fabrica.raiz)
    return None


@cda_router.get("/decisoes")
def listar_decisoes() -> list[dict[str, Any]]:
    """Decisões pendentes de todos os níveis."""
    decisoes = []

    def _coletar(n: Any) -> None:
        decisoes.extend(n.motor.to_dict())
        for sub in n.listar_subniveis():
            _coletar(sub)

    if fabrica.raiz:
        _coletar(fabrica.raiz)
    return sorted(decisoes, key=lambda d: d.get("criado_em", ""), reverse=True)


@cda_router.post("/decisoes/{decisao_id}/resolver")
def resolver_decisao(
    decisao_id: str,
    payload: dict[str, str],
    token: TokenPayload = Depends(require_s5),
) -> dict[str, str]:
    """Aprova decisão — ato exclusivo do S5 humano (R5).

    `resolvido_por` deriva do JWT; o campo do payload é ignorado.
    """
    resolucao = payload.get("resolucao", "")
    resolvido_por = token.sub  # identidade do token, nunca do payload

    def _resolver(n: Any) -> bool:
        if n.motor.resolver(decisao_id, resolucao, resolvido_por, resolvido_por_sub=token.sub):
            return True
        for sub in n.listar_subniveis():
            if _resolver(sub):
                return True
        return False

    if fabrica.raiz and _resolver(fabrica.raiz):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "decisao nao encontrada"}


@cda_router.post("/decisoes/{decisao_id}/rejeitar")
def rejeitar_decisao(
    decisao_id: str,
    payload: dict[str, str],
    token: TokenPayload = Depends(require_s5),
) -> dict[str, str]:
    def _rejeitar(n: Any) -> bool:
        if n.motor.rejeitar(decisao_id, payload.get("feedback", "")):
            return True
        for sub in n.listar_subniveis():
            if _rejeitar(sub):
                return True
        return False

    if fabrica.raiz and _rejeitar(fabrica.raiz):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "decisao nao encontrada"}


@cda_router.post("/decisoes/{decisao_id}/delegar")
def delegar_decisao(
    decisao_id: str,
    token: TokenPayload = Depends(require_s5),
) -> dict[str, str]:
    def _delegar(n: Any) -> bool:
        if n.motor.delegar(decisao_id):
            return True
        for sub in n.listar_subniveis():
            if _delegar(sub):
                return True
        return False

    if fabrica.raiz and _delegar(fabrica.raiz):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "decisao nao encontrada"}


@cda_router.get("/sinais")
def listar_sinais(gravidade: str | None = None) -> list[dict[str, Any]]:
    """Sinais pendentes de todos os níveis."""
    sinais = []

    def _coletar(n: Any) -> None:
        filtrados = n.canal.todos()
        if gravidade:
            try:
                g = GravidadeSinal(gravidade)
                filtrados = [s for s in filtrados if s.gravidade == g]
            except ValueError:
                pass
        sinais.extend([
            {
                "id": s.id,
                "fonte": s.fonte,
                "gravidade": s.gravidade.value,
                "gatilho": s.gatilho.value,
                "assunto": s.assunto,
                "mensagem": s.mensagem,
                "timestamp": s.timestamp,
                "nivel": n.nome,
                "respondido": s.resolucao is not None,
            }
            for s in filtrados
        ])
        for sub in n.listar_subniveis():
            _coletar(sub)

    if fabrica.raiz:
        _coletar(fabrica.raiz)
    return sorted(sinais, key=lambda s: s.get("timestamp", ""), reverse=True)


@cda_router.post("/sinais")
def disparar_sinal(payload: dict[str, Any]) -> dict[str, Any]:
    fonte = payload.get("fonte", "desconhecido")
    nivel = _nivel_do_agente(fonte)
    if nivel is None and fabrica.raiz:
        nivel = fabrica.raiz

    # R4 na entrada: gatilho deve pertencer à tabela constante
    gatilho_raw = payload.get("gatilho", TipoGatilho.TIMEOUT_DECISAO.value)
    try:
        gatilho = TipoGatilho(gatilho_raw)
    except ValueError:
        return {"status": "erro", "motivo": f"R4: gatilho fora da tabela ({gatilho_raw})"}

    sinal = nivel.canal.disparar(
        fonte=fonte,
        gravidade=GravidadeSinal(payload.get("gravidade", "amarelo")),
        assunto=payload.get("assunto", ""),
        mensagem=payload.get("mensagem", ""),
        gatilho=gatilho,
        contexto=payload.get("contexto"),
    )
    return {"status": "ok", "sinal_id": sinal.id}


@cda_router.post("/sinais/{sinal_id}/responder")
def responder_sinal(
    sinal_id: str,
    payload: dict[str, str],
    token: TokenPayload = Depends(require_s5),
) -> dict[str, str]:
    """Responde sinal algédonico — o canal termina no S5 humano (R5)."""
    def _responder(n: Any) -> bool:
        if n.canal.responder(sinal_id, payload.get("resolucao", "")):
            return True
        for sub in n.listar_subniveis():
            if _responder(sub):
                return True
        return False

    if fabrica.raiz and _responder(fabrica.raiz):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "sinal nao encontrado"}


@cda_router.get("/status")
def status_cda() -> dict[str, Any]:
    if not fabrica.raiz:
        return {"erro": "CDA nao inicializada"}
    agentes = fabrica.raiz.listar_agentes()
    decisoes_total = 0
    sinais_pend = 0
    sinais_verm = 0

    def _contar(n: Any) -> None:
        nonlocal decisoes_total, sinais_pend, sinais_verm
        decisoes_total += len(n.motor.pendentes())
        sinais_pend += len(n.canal.pendentes())
        sinais_verm += len(n.canal.pendentes(GravidadeSinal.VERMELHO))
        for sub in n.listar_subniveis():
            _contar(sub)

    _contar(fabrica.raiz)
    return {
        "total_agentes": len(agentes),
        "online": sum(1 for a in agentes if a.status in (StatusAgente.ONLINE, StatusAgente.TRABALHANDO)),
        "standby": sum(1 for a in agentes if a.status == StatusAgente.STANDBY),
        "decisoes_pendentes": decisoes_total,
        "sinais_pendentes": sinais_pend,
        "sinais_vermelhos": sinais_verm,
        "niveis": fabrica.raiz.total_subniveis() + 1,
        "auto_aprovadas": sum(
            1 for d in _historico_completo() if d.get("resolvido_por") != "Diretora"
        ),
    }


def _historico_completo():
    hist = []

    def _coletar(n: Any) -> None:
        for d in n.motor.historico(1000):
            hist.append({
                "id": d.id,
                "assunto": d.assunto,
                "solicitante": d.solicitante,
                "tipo_solicitante": d.tipo_solicitante,
                "contexto": d.contexto,
                "opcoes": d.opcoes,
                "justificativa": d.justificativa,
                "status": d.status.value,
                "resolucao": d.resolucao,
                "resolvido_por": d.resolvido_por,
                "papel_origem": d.papel_origem,
                "papel_aprovacao": d.papel_aprovacao,
                "intencao_id": d.intencao_id,
                "criado_em": d.criado_em,
                "resolvido_em": d.resolvido_em,
            })
        for sub in n.listar_subniveis():
            _coletar(sub)

    if fabrica.raiz:
        _coletar(fabrica.raiz)
    return hist


@cda_router.get("/decisoes/historico")
def historico_decisoes() -> list[dict[str, Any]]:
    return _historico_completo()


@cda_router.get("/auditoria")
def auditoria_cda() -> list[dict[str, Any]]:
    """Relatório de auditoria de todos os níveis."""
    from viableos.cda.recursao.orquestrador import orquestrador
    if orquestrador:
        return orquestrador.auditar()
    return []


@cda_router.get("/auditoria/regras")
def auditoria_seis_regras() -> list[dict[str, Any]]:
    """Audita as 6 regras inegociáveis da Constituição S5."""
    from viableos.cda.recursao.orquestrador import orquestrador
    if orquestrador:
        return orquestrador.auditar_regras()
    return []


@cda_router.get("/auditoria/discordancia")
def taxa_discordancia() -> dict[str, Any]:
    """Taxa de discordância S5×proposta — dado de pesquisa, não veredito.

    PaperBench (arXiv 2504.01848): replicação se mede por rubrica. Aqui o
    proxy estrutural é a fração de decisões aprovadas cuja resolução ficou
    fora das opções propostas pelo agente.
    """
    from viableos.cda.auditoria_regras import auditoria_seis_regras as _auditoria
    if not fabrica.raiz:
        return {"erro": "CDA nao inicializada"}

    historico = []
    for d in _historico_completo():
        historico.append({
            "status": d.get("status"),
            "opcoes": d.get("opcoes", []),
            "resolucao": d.get("resolucao"),
        })
    return _auditoria.taxa_discordancia({"decisoes_historico": historico})


@cda_router.get("/arquitetura")
def arquitetura_cda() -> dict[str, Any]:
    """Documentação da arquitetura: dois eixos de coerência."""
    return {
        "nome": "CDA — Corporação Digital Autônoma",
        "versao": "2.0-bratman",
        "dois_eixos_coerencia": {
            "eixo_temporal": "Bratman (1987): intenção estável com filtro de admissibilidade. Agentes agem por compromisso, não por prompt reativo.",
            "eixo_normativo": "VSM (Beer 1972, 1979, 1985): recursão S1-S5 com canais determinísticos entre níveis. Assimetria temporal de clocks.",
        },
        "seis_regras": [
            "R1: LLM só no S1",
            "R2: Envelope de escrita reversível",
            "R3: S3* anti-correlacionado (modelo diferente)",
            "R4: Quatro gatilhos algedônicos",
            "R5: S5 é humano",
            "R6: Cascata rastreável",
        ],
        "motor_bratman": {
            "tres_papeis": ["Deliberação (filtro)", "Meios-fins (passos)", "Estabilidade (estratégia)"],
            "estrategias": ["BLIND", "SINGLE_MINDED", "OPEN"],
        },
        "constituicao": "/api/cda/constituicao",
    }


@cda_router.get("/constituicao")
def texto_constituicao() -> dict[str, str]:
    """Retorna o texto da Constituição S5."""
    import os
    # src/viableos/api/ → 3 níveis acima = raiz do repo
    caminho = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "CONSTITUICAO_S5.md"))
    try:
        with open(caminho, encoding="utf-8") as f:
            return {"conteudo": f.read()}
    except FileNotFoundError:
        return {"conteudo": "Constituição não encontrada"}


# ═══════════════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════════════


@cda_router.get("/health/boot")
def health_check_boot() -> dict[str, Any]:
    """Health check estático no boot da CDA."""
    from viableos.cda.health_check import health_check_boot as _boot
    if not fabrica.raiz:
        return {"erro": "CDA não inicializada"}
    # Os checks esperam config["agents"] com dicionários de agente —
    # passar a árvore inteira (chave "agentes") fazia todos passarem vazio
    # (auditoria 2026-09-03 §2.2).
    config = {"agents": [a.to_dict() for a in fabrica.raiz.listar_agentes()]}
    relatorio = _boot(config)
    return relatorio.to_dict()


@cda_router.get("/health/periodico")
def health_check_periodico() -> dict[str, Any]:
    """Health check periódico do estado runtime."""
    from viableos.cda.health_check import health_check_periodico as _periodico
    if not fabrica.raiz:
        return {"erro": "CDA não inicializada"}
    sinais_pendentes = []
    budget_usage = []
    try:
        from viableos.cda.budget_monitor import budget_monitor
        uso = budget_monitor.obter_uso()
        budget_usage = uso if isinstance(uso, list) else [uso]
    except Exception:
        pass

    def _coletar_sinais(n: Any) -> None:
        sinais_pendentes.extend(n.canal.pendentes())
        for sub in n.listar_subniveis():
            _coletar_sinais(sub)

    _coletar_sinais(fabrica.raiz)
    estado_cda = {
        "agentes": [a.to_dict() for a in fabrica.raiz.listar_agentes()],
        "sinais_pendentes": sinais_pendentes,
        "budget_usage": budget_usage,
    }
    relatorio = _periodico(estado_cda)
    return relatorio.to_dict()


# ═══════════════════════════════════════════════════════════════════
# Cenários
# ═══════════════════════════════════════════════════════════════════


@cda_router.get("/cenarios")
def listar_cenarios() -> list[dict[str, Any]]:
    """Lista cenários disponíveis para simulação."""
    from viableos.cda.scenarios import simulador
    return simulador.listar_cenarios()


@cda_router.post("/cenarios/{nome}/simular")
def simular_cenario(nome: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Simula um cenário por N ticks."""
    from viableos.cda.scenarios import simulador
    ticks = (payload or {}).get("ticks", 100)
    try:
        resultado = simulador.simular(nome, ticks=ticks)
        return resultado.to_dict()
    except ValueError as e:
        return {"erro": str(e)}


@cda_router.get("/cenarios/historico")
def historico_simulacoes() -> list[dict[str, Any]]:
    """Histórico de simulações realizadas."""
    from viableos.cda.scenarios import simulador
    return simulador.obter_historico()


# ═══════════════════════════════════════════════════════════════════
# Syntegration (Team Syntegrity)
# ═══════════════════════════════════════════════════════════════════


@cda_router.get("/syntegration")
def listar_syntegration() -> dict[str, Any]:
    """Lista protocolos Syntegration ativos e histórico."""
    from viableos.cda.syntegration import gerenciador_syntegration
    return {
        "ativos": gerenciador_syntegration.obter_ativos(),
        "historico": gerenciador_syntegration.obter_historico(),
    }


@cda_router.post("/syntegration/iniciar")
def iniciar_syntegration(payload: dict[str, Any]) -> dict[str, Any]:
    """Diretora inicia Syntegration manualmente."""
    from viableos.cda.syntegration import gerenciador_syntegration
    agentes = fabrica.listar_agentes()
    protocolo = gerenciador_syntegration.iniciar_manual(
        gatilho=payload.get("gatilho", "manual_diretora"),
        proposto_por="Diretora",
        agentes=agentes,
    )
    return {"status": "ok", "protocolo_id": protocolo.id, "fase": protocolo.fase.value}


@cda_router.post("/syntegration/{protocolo_id}/avancar")
def avancar_syntegration(protocolo_id: str) -> dict[str, Any]:
    """Avança protocolo Syntegration para próxima fase."""
    from viableos.cda.syntegration import gerenciador_syntegration
    agentes = fabrica.listar_agentes()
    fase = gerenciador_syntegration.avancar(protocolo_id, agentes)
    if fase:
        return {"status": "ok", "fase": fase.value}
    return {"status": "erro", "motivo": "protocolo não encontrado ou concluído"}


@cda_router.post("/syntegration/{protocolo_id}/cancelar")
def cancelar_syntegration(protocolo_id: str) -> dict[str, str]:
    """Cancela protocolo Syntegration."""
    from viableos.cda.syntegration import gerenciador_syntegration
    if gerenciador_syntegration.cancelar(protocolo_id):
        return {"status": "ok"}
    return {"status": "erro", "motivo": "protocolo não encontrado ou já concluído"}


# ═══════════════════════════════════════════════════════════════════
# Topology
# ═══════════════════════════════════════════════════════════════════


@cda_router.get("/topology")
def topology_info() -> dict[str, Any]:
    """Informações sobre a topologia de comunicação VSM."""
    from viableos.cda.topology import topology_validator, CANAIS_VSM, NIVEIS_VSM
    return {
        "canais": [
            {"remetente": k[0], "destinatario": k[1], "permitido": v}
            for k, v in CANAIS_VSM.items()
        ],
        "niveis_conhecidos": sorted(NIVEIS_VSM),
        "total_blocos": topology_validator.total_blocos,
    }


@cda_router.post("/topology/validar")
def validar_comunicacao(payload: dict[str, str]) -> dict[str, Any]:
    """Valida se uma comunicação é permitida pela topologia."""
    from viableos.cda.topology import topology_validator
    resultado = topology_validator.validar(
        remetente=payload.get("remetente", payload.get("origem", "")),
        destinatario=payload.get("destinatario", payload.get("destino", "")),
        nivel_remetente=payload.get("nivel_remetente", "s1"),
        nivel_destinatario=payload.get("nivel_destinatario", "s2"),
    )
    return {
        "permitido": resultado.permitido,
        "motivo": resultado.motivo,
        "remetente": resultado.remetente,
        "destinatario": resultado.destinatario,
    }
