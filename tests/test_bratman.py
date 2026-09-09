"""Testes do motor Bratmaniano — intenção estável."""

import pytest

from viableos.cda.bratman import (
    EstrategiaCompromisso,
    MotorIntencoes,
    StatusIntencao,
    StatusPasso,
    _deve_reconsiderar,
    _filtrar_admissiveis,
    Intencao,
    Passo,
)


def test_adotar_intencao_com_sucesso():
    motor = MotorIntencoes("test-agent")
    intencao = motor.adotar(
        desejo="Automatizar gestão de bolsistas",
        plano="Implementar TR Generator",
        passos=[
            {"descricao": "Analisar requisitos", "responsavel": "test-agent"},
            {"descricao": "Implementar módulo", "responsavel": "test-agent"},
        ],
        prioridade=1,
    )
    assert intencao is not None
    assert intencao.desejo == "Automatizar gestão de bolsistas"
    assert intencao.status == StatusIntencao.ATIVA
    assert len(intencao.passos) == 2


def test_filtro_admissibilidade_bloqueia_conflito():
    motor = MotorIntencoes("test-agent")

    intencao = motor.adotar(
        desejo="Projeto A",
        plano="Plano A",
        passos=[{"descricao": "Passo 1", "recursos": ["gpu"]}],
        estrategia=EstrategiaCompromisso.SINGLE_MINDED,
    )
    assert intencao is not None

    conflitante = motor.adotar(
        desejo="Projeto B",
        plano="Plano B",
        passos=[{"descricao": "Passo 1", "recursos": ["gpu"]}],
        estrategia=EstrategiaCompromisso.SINGLE_MINDED,
    )
    assert conflitante is None, "Desejo conflitante deve ser rejeitado"


def test_filtro_admissibilidade_permite_sem_conflito():
    motor = MotorIntencoes("test-agent")

    motor.adotar(
        desejo="Projeto A",
        plano="Plano A",
        passos=[{"descricao": "Passo 1", "recursos": ["gpu"]}],
    )

    permitido = motor.adotar(
        desejo="Projeto B",
        plano="Plano B",
        passos=[{"descricao": "Passo 1", "recursos": ["cpu"]}],
    )
    assert permitido is not None, "Desejo sem conflito deve ser permitido"


def test_executar_passo_avanca_intencao():
    motor = MotorIntencoes("test-agent")
    intencao = motor.adotar(
        desejo="Teste",
        plano="Plano",
        passos=[
            {"descricao": "Passo 1"},
            {"descricao": "Passo 2"},
        ],
    )
    assert intencao is not None

    r1 = motor.executar_passo(intencao.id)
    assert r1["status"] == "passo_executado"
    assert r1["passo"] == "Passo 1"

    r2 = motor.executar_passo(intencao.id)
    assert r2["status"] == "passo_executado"
    assert r2["passo"] == "Passo 2"

    r3 = motor.executar_passo(intencao.id)
    assert r3["status"] == "concluida"
    assert r3["proporcao"] == 1.0


def test_reconsiderar_abandona_intencao():
    motor = MotorIntencoes("test-agent")
    intencao = motor.adotar(
        desejo="Projeto Arriscado",
        plano="Plano",
        passos=[{"descricao": "Passo 1"}],
    )
    assert intencao is not None

    intencao.evidencia_contraria.append("mudanca_escopo")
    resultado = motor.reconsiderar(
        intencao.id,
        mudancas=["mudanca_escopo", "perda_recursos"],
        intensidade=0.8,
    )
    assert resultado["status"] == "abandonada"


def test_blind_nao_reconsidera():
    motor = MotorIntencoes("test-agent")
    intencao = motor.adotar(
        desejo="Missao Critica",
        plano="Plano Blindado",
        passos=[{"descricao": "Passo 1"}],
        estrategia=EstrategiaCompromisso.BLIND,
    )
    assert intencao is not None

    resultado = motor.reconsiderar(
        intencao.id,
        mudancas=["qualquer_coisa"],
        intensidade=1.0,
    )
    assert resultado["status"] == "mantida"


def test_open_sempre_reconsidera():
    motor = MotorIntencoes("test-agent")
    intencao = motor.adotar(
        desejo="Exploracao",
        plano="Plano Aberto",
        passos=[{"descricao": "Passo 1"}],
        estrategia=EstrategiaCompromisso.OPEN,
    )
    assert intencao is not None

    intencao.evidencia_contraria.append("nova_info")
    resultado = motor.reconsiderar(
        intencao.id,
        mudancas=["nova_info"],
        intensidade=0.0,
    )
    assert resultado["status"] == "mantida"

    resultado2 = motor.reconsiderar(
        intencao.id,
        mudancas=["nova_info", "outra_mudanca", "mais_uma"],
        intensidade=0.0,
    )
    assert resultado2["status"] == "abandonada"


def test_filtrar_admissiveis_function():
    intencoes = [
        Intencao(
            desejo="Existente",
            passos=[Passo(descricao="p1", recursos=["gpu"])],
        )
    ]
    opcoes = [
        {"desejo": "Novo", "recursos_necessarios": ["cpu"], "plano": ""},
        {"desejo": "Existente", "recursos_necessarios": ["gpu"], "plano": ""},
    ]
    resultado = _filtrar_admissiveis(opcoes, intencoes, EstrategiaCompromisso.SINGLE_MINDED)
    assert len(resultado) == 1
    assert resultado[0]["desejo"] == "Novo"


def test_listar_intencoes():
    motor = MotorIntencoes("test-agent")
    motor.adotar(desejo="A", plano="P1", passos=[{"descricao": "p1"}])
    motor.adotar(desejo="B", plano="P2", passos=[{"descricao": "p1"}])

    todas = motor.listar(apenas_ativas=False)
    assert len(todas) == 2

    ativas = motor.listar(apenas_ativas=True)
    assert len(ativas) == 2

    for i in motor._intencoes:
        motor.executar_passo(i.id)
        motor.executar_passo(i.id)

    ativas2 = motor.listar(apenas_ativas=True)
    assert len(ativas2) == 0


def test_agenda_bratman_verifica_coerencia():
    from viableos.cda.bratman import agenda_bratman

    m1 = agenda_bratman.obter_motor("agente_a")
    m2 = agenda_bratman.obter_motor("agente_b")

    m1.adotar("Tarefa X", "Plano", passos=[{"descricao": "p1", "recursos": ["gpu"]}])
    m2.adotar("Tarefa Y", "Plano", passos=[{"descricao": "p1", "recursos": ["gpu"]}])

    conflitos = agenda_bratman.verificar_coerencia()
    assert len(conflitos) > 0
