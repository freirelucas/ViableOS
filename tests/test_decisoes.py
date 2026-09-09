"""Testes do motor de decisões — R6 na entrada, autonomia e proveniência.

Cobre o módulo inteiro (zero testes antes da revisão de coerência de
2026-09-03 — docs/audits/2026-09-03-coerencia-cda.md §2.6).
"""

from __future__ import annotations

import pytest

from viableos.cda.decisoes import (
    AUTONOMIA_POR_TIPO,
    MotorDecisoes,
    NivelAutonomia,
    StatusDecisao,
)


def _motor() -> MotorDecisoes:
    return MotorDecisoes()


def _solicitar(motor, **kwargs):
    padrao = dict(
        solicitante="Inteligência Estratégica (S4)",
        tipo_solicitante="s4_inteligencia",
        assunto="Priorizar sprint",
        contexto="Recursos sobrecarregados",
        opcoes=["Concluir sprint 3", "Iniciar Projeto 2"],
        justificativa="S4: análise de capacidade indica janela crítica.",
    )
    padrao.update(kwargs)
    return motor.solicitar(**padrao)


# ─── R6 imposta na entrada ─────────────────────────────────────────


def test_r6_decisao_sem_contexto_e_nula():
    with pytest.raises(ValueError, match="R6"):
        _solicitar(_motor(), contexto="")


def test_r6_decisao_sem_opcoes_e_nula():
    with pytest.raises(ValueError, match="R6"):
        _solicitar(_motor(), opcoes=[])


def test_r6_decisao_sem_justificativa_e_nula():
    with pytest.raises(ValueError, match="R6"):
        _solicitar(_motor(), justificativa="")


# ─── Autonomia ──────────────────────────────────────────────────────


def test_recomendacao_sobe_ao_s5():
    motor = _motor()
    dec = _solicitar(motor)
    assert dec.status == StatusDecisao.PENDENTE
    assert dec in motor.pendentes()


def test_s1_desenvolvedor_nao_tem_autonomia_total():
    """Decisão técnica da auditoria 2026-09-03 §2.4: TOTAL é dos papéis de
    auditoria — desenvolvedor recomenda, não decide sozinho."""
    assert AUTONOMIA_POR_TIPO["s1_desenvolvedor"] is not NivelAutonomia.TOTAL
    motor = _motor()
    dec = _solicitar(motor, tipo_solicitante="s1_desenvolvedor")
    assert dec.status == StatusDecisao.PENDENTE


def test_s3_auditoria_autonomia_total():
    motor = _motor()
    dec = _solicitar(motor, tipo_solicitante="s3_auditoria")
    assert dec.status == StatusDecisao.APROVADA
    assert dec in motor.historico(10)


def test_limitada_auto_aprova_dentro_da_alcada():
    motor = _motor()
    dec = _solicitar(motor, tipo_solicitante="s3_gestao")
    assert dec.status == StatusDecisao.APROVADA
    assert "alçada" in (dec.feedback or "")


def test_nenhuma_sobe_ao_s5_com_feedback(monkeypatch):
    monkeypatch.setitem(
        AUTONOMIA_POR_TIPO, "x_zero", NivelAutonomia.NENHUMA,
    )
    motor = _motor()
    dec = _solicitar(motor, tipo_solicitante="x_zero")
    assert dec.status == StatusDecisao.PENDENTE
    assert "ordens" in (dec.feedback or "")


# ─── Proveniência organizacional ────────────────────────────────────


def test_papel_origem_por_tipo():
    motor = _motor()
    dec = _solicitar(motor, tipo_solicitante="s4_inteligencia")
    assert dec.papel_origem == "controle_deterministico"

    dec_s1 = _solicitar(motor, tipo_solicitante="s1_analista")
    assert dec_s1.papel_origem == "s1_executou"


def test_constituicao_carimbada_na_criacao():
    dec = _solicitar(_motor())
    # Se o arquivo existe, hash de 64 hex; nunca string arbitrária
    assert dec.constituicao_hash == "" or len(dec.constituicao_hash) == 64


def test_resolver_carimba_papel_s5_e_identidade():
    motor = _motor()
    dec = _solicitar(motor)
    ok = motor.resolver(
        dec.id, "Concluir sprint 3", "diretora@ipea", resolvido_por_sub="diretora@ipea",
    )
    assert ok
    resolvida = motor.historico(10)[0]
    assert resolvida.status == StatusDecisao.APROVADA
    assert resolvida.papel_aprovacao == "s5_humano_aprovou"
    assert resolvida.resolvido_por_sub == "diretora@ipea"
    assert resolvida.resolvido_por == "diretora@ipea"
    assert motor.pendentes() == []


def test_resolver_decisao_inexistente():
    assert _motor().resolver("zzzz", "x") is False


# ─── Rejeitar / Delegar ─────────────────────────────────────────────


def test_rejeitar_registra_status_e_feedback():
    motor = _motor()
    dec = _solicitar(motor)
    assert motor.rejeitar(dec.id, "Escopo grande demais")
    rejeitada = motor.historico(10)[0]
    assert rejeitada.status == StatusDecisao.REJEITADA
    assert rejeitada.feedback == "Escopo grande demais"
    assert rejeitada.papel_aprovacao == "s5_humano_aprovou"


def test_delegar_devolve_ao_agente():
    motor = _motor()
    dec = _solicitar(motor)
    assert motor.delegar(dec.id)
    delegada = motor.historico(10)[0]
    assert delegada.status == StatusDecisao.DELEGADA


# ─── Serialização ──────────────────────────────────────────────────


def test_to_dict_expondo_cascata():
    motor = _motor()
    _solicitar(motor, intencao_id="abc123")
    d = motor.to_dict()[0]
    assert d["justificativa"]
    assert d["papel_origem"]
    assert d["intencao_id"] == "abc123"
