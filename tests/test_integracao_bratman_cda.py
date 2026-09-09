"""Testes de integração entre Bratman e CDA.

Verifica que o motor de intenções funciona corretamente
dentro da arquitetura VSM da CDA.
"""

import pytest
from viableos.cda.agente import AgenteGLM, StatusAgente, TipoAgente
from viableos.cda.bratman import EstrategiaCompromisso, agenda_bratman
from viableos.cda.glm import system_prompt_agente
from viableos.cda.recursao.nivel import NivelVSM


@pytest.fixture
def nivel_teste():
    nivel = NivelVSM(nome="Teste", nivel=1, proposito="Testar integração")
    agente = AgenteGLM(
        nome="Agente Teste",
        tipo=TipoAgente.S1_DESENVOLVEDOR,
        proposito="Testar intenções",
        ferramentas=["python", "git"],
        estrategia_compromisso=EstrategiaCompromisso.SINGLE_MINDED,
        system_prompt=system_prompt_agente("Agente Teste", "Teste", ["python"]),
    )
    nivel.adicionar_agente(agente)
    return nivel


def test_agente_adota_intencao_via_cda(nivel_teste):
    agente = nivel_teste.obter_agente("Agente Teste")
    assert agente is not None

    intencao = agente.adotar_intencao(
        desejo="Automatizar testes",
        plano="Criar suíte de testes",
        passos=[
            {"descricao": "Configurar pytest", "recursos": ["python"]},
            {"descricao": "Escrever testes", "recursos": ["python"]},
        ],
        prioridade=1,
    )
    assert intencao is not None
    assert intencao.desejo == "Automatizar testes"
    assert len(agente.intencoes_ativas()) == 1


def test_agente_executa_passo_e_registra_historico(nivel_teste):
    agente = nivel_teste.obter_agente("Agente Teste")
    intencao = agente.adotar_intencao("Tarefa", "Plano", [
        {"descricao": "Passo 1"},
        {"descricao": "Passo 2"},
    ])
    assert intencao is not None

    r1 = agente.executar_passo(intencao.id)
    assert r1["status"] == "passo_executado"

    r2 = agente.executar_passo(intencao.id)
    assert r2["status"] == "passo_executado"

    r3 = agente.executar_passo(intencao.id)
    assert r3["status"] == "concluida"

    agente.registrar_acao("Intenção concluída", "concluida")
    assert len(agente.historico) > 0


def test_agente_filtra_opcoes_com_intencoes_ativas(nivel_teste):
    agente = nivel_teste.obter_agente("Agente Teste")
    agente.adotar_intencao("Projeto A", "Plano A", [
        {"descricao": "Passo 1", "recursos": ["gpu"]},
    ])

    opcoes = [
        {"desejo": "Projeto B", "recursos_necessarios": ["gpu"], "plano": "Plano B"},
        {"desejo": "Projeto C", "recursos_necessarios": ["cpu"], "plano": "Plano C"},
    ]
    filtradas = agente.filtrar_opcoes(opcoes)
    assert len(filtradas) == 1
    assert filtradas[0]["desejo"] == "Projeto C"


def test_agenda_global_gerencia_multiplos_agentes(nivel_teste):
    agente1 = nivel_teste.obter_agente("Agente Teste")

    # Criar segundo agente no mesmo nível
    agente2 = AgenteGLM(
        nome="Agente 2",
        tipo=TipoAgente.S1_EXECUTOR,
        proposito="Teste 2",
        ferramentas=[],
        system_prompt=system_prompt_agente("Agente 2", "Teste", []),
    )
    nivel_teste.adicionar_agente(agente2)

    agente1.adotar_intencao("Tarefa A", "Plano A", [
        {"descricao": "p1", "recursos": ["recurso_x"]},
    ])
    agente2.adotar_intencao("Tarefa B", "Plano B", [
        {"descricao": "p1", "recursos": ["recurso_x"]},
    ])

    conflitos = agenda_bratman.verificar_coerencia()
    assert len(conflitos) > 0
    assert any("recurso_x" in c["recursos_conflitantes"] for c in conflitos)


def test_agente_to_dict_inclui_intencoes(nivel_teste):
    agente = nivel_teste.obter_agente("Agente Teste")
    agente.adotar_intencao("Missão", "Plano Missão", [
        {"descricao": "p1"},
    ])

    dados = agente.to_dict()
    assert "intencoes_ativas" in dados
    assert dados["intencoes_ativas"] >= 1
    assert dados["estrategia"] == "single_minded"


def test_agente_com_estrategia_blind_mantem_intencao(nivel_teste):
    agente = AgenteGLM(
        nome="Agente Blind",
        tipo=TipoAgente.S3_AUDITORIA,
        proposito="Auditoria",
        ferramentas=[],
        estrategia_compromisso=EstrategiaCompromisso.BLIND,
        system_prompt=system_prompt_agente("Blind", "Auditar", []),
    )
    nivel_teste.adicionar_agente(agente)

    intencao = agente.adotar_intencao("Auditar tudo", "Plano", [
        {"descricao": "p1"},
    ])
    assert intencao is not None

    # BLIND não abandona
    motor = agenda_bratman.obter_motor("Agente Blind")
    resultado = motor.reconsiderar(intencao.id, mudancas=["qualquer"], intensidade=0.9)
    assert resultado["status"] == "mantida"


def test_nivel_vsm_lista_intencoes_dos_agentes(nivel_teste):
    agente = nivel_teste.obter_agente("Agente Teste")
    agente.adotar_intencao("Intenção 1", "Plano 1")
    agente.adotar_intencao("Intenção 2", "Plano 2")

    intencoes_total = 0
    for a in nivel_teste.listar_agentes():
        motor = agenda_bratman.obter_motor(a.nome)
        intencoes_total += len(motor.listar())

    assert intencoes_total >= 2
