"""Testes do ledger de proveniência — hash-chain, carimbo e replay.

Regra 2 do handout: intenção persiste fora do runner. O ledger é a
proveniência organizacional (PACT-inspired) e o substrato de rebuild.
"""

from __future__ import annotations

import json
import os

import pytest

from viableos.cda.algedonic import GravidadeSinal, TipoGatilho
from viableos.cda.bratman import AgendaBratman
from viableos.cda.decisoes import StatusDecisao
from viableos.cda.provenancia import (
    LedgerProveniencia,
    PapelProveniencia,
    _decisao_de_dict,
    _intencao_de_dict,
    _sinal_de_dict,
    carimbo_constituicao,
    papel_por_tipo,
)
from viableos.cda.recursao.nivel import NivelVSM


# ─── Papel organizacional ──────────────────────────────────────────


def test_papel_por_tipo_mapeia_todos():
    assert papel_por_tipo("s1_desenvolvedor") == PapelProveniencia.S1_EXECUTOU
    assert papel_por_tipo("s1_executor") == PapelProveniencia.S1_EXECUTOU
    assert papel_por_tipo("s3_auditoria") == PapelProveniencia.S3STAR_REPLICOU
    assert papel_por_tipo("s5_diretor") == PapelProveniencia.S5_HUMANO_APROVOU
    assert papel_por_tipo("s4_inteligencia") == PapelProveniencia.CONTROLE_DETERMINISTICO
    assert papel_por_tipo("s3_gestao") == PapelProveniencia.CONTROLE_DETERMINISTICO
    assert papel_por_tipo("s2_coordenacao") == PapelProveniencia.CONTROLE_DETERMINISTICO


def test_carimbo_constituicao_estavel():
    c1 = carimbo_constituicao()
    c2 = carimbo_constituicao()
    assert c1["hash_sha256"] == c2["hash_sha256"]
    # hash presente quando a constituição existe no repo; sempre 64 hex se não vazio
    assert len(c1["hash_sha256"]) in (0, 64)


# ─── Ledger: caderno append-only ───────────────────────────────────


def test_ledger_desabilitado_nao_escreve(tmp_path):
    led = LedgerProveniencia()
    assert led.habilitado is False
    assert led.registrar("x", {}) is None
    assert led.eventos() == []
    assert not os.path.exists(tmp_path / "ninguem.jsonl")


def test_ledger_encadeia_registros(tmp_path):
    led = LedgerProveniencia(diretorio=str(tmp_path))
    r1 = led.registrar("decisao_estado", {"nivel": "CDA"}, papel="controle_deterministico")
    r2 = led.registrar("sinal_estado", {"nivel": "Projeto 1"})

    assert r1["sequencia"] == 1 and r2["sequencia"] == 2
    assert r2["hash_anterior"] == r1["hash"]
    assert r1["hash_anterior"] == LedgerProveniencia.GENESIS
    # todo registro carimba a constituição vigente
    assert "hash_sha256" in r1["constituicao"]
    assert led.verificar_cadeia()["integro"] is True
    assert len(led.eventos()) == 2


def test_ledger_detecta_adulteracao(tmp_path):
    led = LedgerProveniencia(diretorio=str(tmp_path))
    led.registrar("a", {"dado": 1})
    led.registrar("b", {"dado": 2})

    caminho = led.caminho
    with open(caminho, encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]
    reg = json.loads(linhas[0])
    reg["dados"]["dado"] = 999  # adulteração de conteúdo registrado
    linhas[0] = json.dumps(reg, ensure_ascii=False)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    resultado = led.verificar_cadeia()
    assert resultado["integro"] is False
    assert resultado["quebras"]


# ─── Replay: intenção persiste fora do runner ──────────────────────


@pytest.fixture
def ledger_ativo(tmp_path):
    """Habilita o singleton global — o mesmo caminho que o domínio usa
    em produção (CDA_STATE_DIR). Os hooks de decisoes/algedonic/bratman
    escrevem no singleton, não em instâncias locais."""
    from viableos.cda import provenancia

    diretorio = str(tmp_path / "estado")
    provenancia.ledger.habilitar(diretorio)
    yield diretorio
    provenancia.ledger.desabilitar()


def test_replay_restaura_decisao_sinal_e_intencao(ledger_ativo):
    from viableos.cda import provenancia

    diretorio = ledger_ativo

    # ── "Processo A": estado vivo + singleton habilitado ──
    nivel_a = NivelVSM("CDA", 1, "raiz")
    dec = nivel_a.motor.solicitar(
        solicitante="Inteligência Estratégica (S4)",
        tipo_solicitante="s4_inteligencia",
        assunto="Priorizar sprint",
        contexto="Recursos sobrecarregados",
        opcoes=["Concluir sprint 3", "Iniciar Projeto 2"],
        justificativa="Janela crítica.",
    )
    nivel_a.motor.resolver(
        dec.id, "Concluir sprint 3", "diretora@ipea", resolvido_por_sub="diretora@ipea",
    )
    nivel_a.canal.disparar(
        "Dev", GravidadeSinal.AMARELO, "Bloqueio API", "sem previsão",
        gatilho=TipoGatilho.CONFLITO_AGENTES,
    )
    agenda_a = AgendaBratman()
    motor_int = agenda_a.obter_motor("Dev")
    intencao = motor_int.adotar(
        desejo="Entregar prestação de contas",
        plano="Construir API REST",
        passos=[{"descricao": "modelar schema"}, {"descricao": "escrever rotas"}],
    )
    assert intencao is not None
    motor_int.executar_passo(intencao.id)
    total_eventos = len(provenancia.ledger.eventos())
    assert total_eventos >= 5  # decisões + sinal + intenção(ões)

    # ── "Processo B": instância NOVA lendo o mesmo arquivo (restart) ──
    led_b = LedgerProveniencia(diretorio=diretorio)
    nivel_b = NivelVSM("CDA", 1, "raiz")
    agenda_b = AgendaBratman()
    stats = led_b.reconstruir(raiz=nivel_b, agenda=agenda_b)

    assert stats["decisoes"] >= 2
    assert stats["sinais"] == 1
    assert stats["intencoes"] >= 1

    # decisão voltou resolvida com identidade e papel originais
    hist = nivel_b.motor.historico(10)
    assert len(hist) == 1
    assert hist[0].status == StatusDecisao.APROVADA
    assert hist[0].resolvido_por_sub == "diretora@ipea"
    assert hist[0].papel_aprovacao == "s5_humano_aprovou"
    assert nivel_b.motor.pendentes() == []

    # sinal voltou com gatilho e estado pendente
    sinais = nivel_b.canal.todos()
    assert len(sinais) == 1
    assert sinais[0].gatilho == TipoGatilho.CONFLITO_AGENTES

    # intenção voltou com o passo executado
    intencao_b = agenda_b.obter_motor("Dev")._intencoes[0]
    assert intencao_b.id == intencao.id
    assert intencao_b.passos[0].status.value == "concluido"


def test_replay_nao_reescreve_o_ledger(ledger_ativo):
    from viableos.cda import provenancia

    nivel = NivelVSM("CDA", 1, "raiz")
    nivel.motor.solicitar(
        solicitante="S4", tipo_solicitante="s4_inteligencia",
        assunto="A", contexto="C", opcoes=["A1"], justificativa="J",
    )
    antes = len(provenancia.ledger.eventos())

    led_b = LedgerProveniencia(diretorio=ledger_ativo)
    raiz_b = NivelVSM("CDA", 1, "raiz")
    led_b.reconstruir(raiz=raiz_b, agenda=AgendaBratman())
    assert len(led_b.eventos()) == antes
    assert len(provenancia.ledger.eventos()) == antes


# ─── Conversores de replay ─────────────────────────────────────────


def test_decisao_de_dict_converte_enums():
    dec = _decisao_de_dict({
        "id": "x1", "contexto": "c", "opcoes": ["a"],
        "autonomia": "recomendacao", "status": "aprovada",
        "resolucao": "a", "papel_aprovacao": "s5_humano_aprovou",
    })
    assert dec.status.value == "aprovada"
    assert dec.papel_aprovacao == "s5_humano_aprovou"


def test_sinal_de_dict_converte_enums_e_propagacao():
    s = _sinal_de_dict({
        "id": "s1", "gravidade": "vermelho", "gatilho": "desvio_orcamento",
        "propagado_para": ["CDA"],
    })
    assert s.gravidade.value == "vermelho"
    assert s.gatilho.value == "desvio_orcamento"
    assert s.propagado_para == ["CDA"]


def test_intencao_de_dict_restaura_passos():
    i = _intencao_de_dict({
        "id": "i1", "desejo": "D", "plano": "P", "status": "em_execucao",
        "estrategia": "single_minded",
        "passos": [{"descricao": "p1", "status": "concluido"}],
    })
    assert i.passos[0].status.value == "concluido"
    assert i.status.value == "em_execucao"
