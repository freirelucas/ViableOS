"""Testes do canal algédonico — tabela R4, gatilhos ligados e dedups.

Cobre o módulo inteiro (zero testes antes da revisão de coerência de
2026-09-03 — docs/audits/2026-09-03-coerencia-cda.md §2.6).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from viableos.cda.algedonic import (
    GATILHOS_R4,
    CanalAlgedonico,
    GravidadeSinal,
    PRAZO_RESPOSTA_HORAS,
    SinalAlgedonico,
    TipoGatilho,
)
from viableos.cda.budget_monitor import BudgetMonitor
from viableos.cda.recursao.nivel import NivelVSM
from viableos.cda.recursao.orquestrador import OrquestradorRecursivo


# ─── Tabela R4 (fonte única da constituição local) ─────────────────


def test_tabela_r4_cobre_todo_enum():
    assert set(GATILHOS_R4) == set(TipoGatilho)
    for cfg in GATILHOS_R4.values():
        assert cfg["semantica"] in ("notifica", "bloqueia")
        assert isinstance(cfg["bloqueia"], bool)


def test_sob_constituicao_local_gatilhos_sao_notificacao():
    """Na vigente, todos notificam (a fonte-mãe exige 2 bloqueantes —
    emenda proposta em docs/propostas/emenda-r4-gatilhos.md)."""
    assert all(not cfg["bloqueia"] for cfg in GATILHOS_R4.values())


# ─── Registro e gravidade ───────────────────────────────────────────


def test_disparar_registra_gatilho_nivel_e_contexto():
    canal = CanalAlgedonico()
    canal.nivel_nome = "CDA"
    s = canal.disparar(
        fonte="Agente Desenvolvedor",
        gravidade=GravidadeSinal.AMARELO,
        assunto="Dependência externa",
        mensagem="API X sem previsão",
        gatilho=TipoGatilho.CONFLITO_AGENTES,
    )
    assert s.gatilho == TipoGatilho.CONFLITO_AGENTES
    assert s.nivel == "CDA"  # nível real, não "R3-S1" hardcoded
    assert canal.pendentes(GravidadeSinal.AMARELO)[0].id == s.id


def test_disparar_conflito_mantem_contexto_extra():
    canal = CanalAlgedonico()
    s = canal.disparar_conflito(
        fonte="AgendaBratman",
        agentes=["Dev", "Gestor"],
        recurso="gpu",
        contexto_extra={"intencao_a": "i1", "intencao_b": "i2"},
    )
    assert s.contexto["intencao_a"] == "i1"
    assert s.contexto["recurso"] == "gpu"


def test_prazos_resposta():
    assert PRAZO_RESPOSTA_HORAS[GravidadeSinal.VERMELHO] == 24
    assert PRAZO_RESPOSTA_HORAS[GravidadeSinal.AMARELO] == 48


def test_responder_resolve_sinal():
    canal = CanalAlgedonico()
    s = canal.disparar("X", GravidadeSinal.VERMELHO, "A", "M")
    assert canal.responder(s.id, "tratado")
    assert canal.pendentes() == []
    assert canal.responder("inexistente", "x") is False


# ─── Gatilho R4-1: timeout com dedup ────────────────────────────────


def _decisao_velha(velocidade_horas: float = 25) -> SimpleNamespace:
    antigo = datetime.now(timezone.utc) - timedelta(hours=velocidade_horas)
    return SimpleNamespace(
        id="d1", solicitante="S4", assunto="Atrasada", criado_em=antigo.isoformat(),
    )


def test_verificar_timeouts_dispara_para_decisao_expirada():
    canal = CanalAlgedonico()
    disparados = canal.verificar_timeouts([_decisao_velha()])
    assert len(disparados) == 1
    assert disparados[0].gatilho == TipoGatilho.TIMEOUT_DECISAO
    assert disparados[0].gravidade == GravidadeSinal.VERMELHO


def test_verificar_timeouts_nao_duplica():
    """O bug da revisão: cada chamada redisparava pelo mesmo motivo."""
    canal = CanalAlgedonico()
    pendentes = [_decisao_velha()]
    canal.verificar_timeouts(pendentes)
    segundo = canal.verificar_timeouts(pendentes)
    assert segundo == []
    assert len(canal.todos()) == 1


def test_verificar_timeouts_ignora_decisao_recente():
    canal = CanalAlgedonico()
    recente = SimpleNamespace(
        id="d2", solicitante="S4", assunto="Nova",
        criado_em=datetime.now(timezone.utc).isoformat(),
    )
    assert canal.verificar_timeouts([recente]) == []


# ─── Propagação entre níveis com dedup (orquestrador) ──────────────


def _arvore_dois_niveis():
    raiz = NivelVSM("CDA", 1, "raiz")
    sub = NivelVSM("Projeto 1", 2, "sub")
    raiz.adicionar_subnivel(sub)
    return raiz, sub


def test_propagacao_sobe_sem_duplicar():
    raiz, sub = _arvore_dois_niveis()
    orq = OrquestradorRecursivo(raiz)
    sub.canal.disparar("Dev", GravidadeSinal.AMARELO, "Bloqueio", "sem API")

    primeira = orq.propagar_sinais()
    segunda = orq.propagar_sinais()

    assert primeira == 1
    assert segunda == 0, "tick seguinte não pode copiar o mesmo sinal de novo"
    assert len(raiz.canal.todos()) == 1
    assert raiz.canal.todos()[0].assunto.startswith("[Projeto 1]")


def test_propagacao_ignora_sinal_respondido():
    raiz, sub = _arvore_dois_niveis()
    orq = OrquestradorRecursivo(raiz)
    s = sub.canal.disparar("Dev", GravidadeSinal.AMARELO, "Bloqueio", "sem API")
    sub.canal.responder(s.id, "resolvido")
    assert orq.propagar_sinais() == 0


# ─── Gatilho R4-2: orçamento conectado ao canal ─────────────────────


def test_monitor_desvio_dispara_sinal_algedonico():
    canal = CanalAlgedonico()
    monitor = BudgetMonitor(canal=canal)
    monitor.definir_orcamento("CDA", 10.0)

    monitor.registrar_uso("CDA", tokens=1000, custo_usd=8.5)
    alertas = monitor.verificar_desvio(tick=1)
    assert len(alertas) == 1
    sinais = canal.pendentes()
    assert len(sinais) == 1
    assert sinais[0].gatilho == TipoGatilho.DESVIO_ORCAMENTO
    assert sinais[0].gravidade == GravidadeSinal.AMARELO


def test_monitor_desvio_nao_duplica_alerta():
    canal = CanalAlgedonico()
    monitor = BudgetMonitor(canal=canal)
    monitor.definir_orcamento("CDA", 10.0)
    monitor.registrar_uso("CDA", tokens=1000, custo_usd=8.5)
    monitor.verificar_desvio(tick=1)
    alertas = monitor.verificar_desvio(tick=2)
    assert alertas == []


def test_monitor_sem_canal_nao_dispara():
    monitor = BudgetMonitor(canal=None)
    monitor.definir_orcamento("CDA", 10.0)
    monitor.registrar_uso("CDA", tokens=1000, custo_usd=9.9)
    # não explode — e o estado continua consultável
    assert monitor.verificar_desvio(tick=1)


# ─── Serialização do sinal ─────────────────────────────────────────


def test_to_dict_expoe_gatilho_e_nivel():
    canal = CanalAlgedonico()
    canal.nivel_nome = "CDA"
    canal.disparar("X", GravidadeSinal.VERDE, "A", "M", gatilho=TipoGatilho.OPORTUNIDADE_ESTRATEGICA)
    d = canal.to_dict()[0]
    assert d["gatilho"] == "oportunidade_estrategica"
    assert d["nivel"] == "CDA"
    assert isinstance(canal.todos()[0], SinalAlgedonico)
