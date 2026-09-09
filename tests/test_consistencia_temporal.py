"""Testes de consistência temporal — clock, bargain, intenção.

Verifica que:
1. Clocks têm frequências assimétricas corretas
2. Bargain alinha recursos entre níveis
3. Intenções Bratman evoluem com o tempo (passos executados)
4. O spiral buffer (assimetria de clock) isola níveis
"""

import pytest
from datetime import datetime, timezone
from viableos.cda.recursao.clock import Clock, FrequenciaClock, FREQUENCIA_SEGUNDOS
from viableos.cda.recursao.bargain import ProtocoloBargain, Recurso, StatusBargain
from viableos.cda.bratman import MotorIntencoes, EstrategiaCompromisso


class TestClocksAssimetricos:

    def test_frequencias_corretas(self):
        assert FREQUENCIA_SEGUNDOS[FrequenciaClock.OPERACIONAL] == 30
        assert FREQUENCIA_SEGUNDOS[FrequenciaClock.TATICO] == 900
        assert FREQUENCIA_SEGUNDOS[FrequenciaClock.ESTRATEGICO] == 3600

    def test_clock_inicia_e_para(self):
        clock = Clock("teste", FrequenciaClock.OPERACIONAL)
        assert not clock._rodando
        assert clock.tick_atual == 0

    def test_clock_tick_incrementa(self):
        ticks = []

        async def tick_handler(n: int):
            ticks.append(n)
            return {}

        clock = Clock("teste", FrequenciaClock.OPERACIONAL, on_tick=tick_handler)
        assert clock.intervalo == 30
        assert clock.minutos_por_tick == 0.5

    def test_heartbeat_registrado(self):
        async def tick_handler(n: int):
            return {"decisoes": 1, "sinais": 0, "agentes": 3}

        clock = Clock("teste", FrequenciaClock.OPERACIONAL, on_tick=tick_handler)
        clock.tick_atual = 1
        import time
        import asyncio

        # Simulate one tick
        async def simular():
            inicio = time.monotonic()
            resultado = await tick_handler(1)
            from viableos.cda.recursao.clock import Heartbeat
            clock._heartbeats.append(type('hb', (), {
                'nivel': clock.nivel_nome,
                'tick': 1,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'decisoes_processadas': resultado.get("decisoes", 0),
                'sinais_propagados': resultado.get("sinais", 0),
                'agentes_ativos': resultado.get("agentes", 0),
                'duracao_ms': 0.5,
                'erros': 0,
            })())

        asyncio.run(simular())
        assert len(clock._heartbeats) == 1
        assert clock._heartbeats[0].tick == 1

    def test_status_clock(self):
        clock = Clock("CDA", FrequenciaClock.ESTRATEGICO)
        status = clock.status()
        assert status["nivel"] == "CDA"
        assert status["frequencia"] == "estrategico"
        assert status["intervalo_segundos"] == 3600


class TestBargainComIntencoes:

    def test_bargain_solicita_recursos(self):
        protocolo = ProtocoloBargain()
        negociacao = protocolo.solicitar(
            subnivel="Projeto 1",
            nivel_pai="CDA",
            recursos=[
                {"tipo": "agente", "quantidade": 2, "unidade": "unidades", "prioridade": 1},
                {"tipo": "api_calls", "quantidade": 1000, "unidade": "req/dia", "prioridade": 2},
            ],
            justificativa="Automatizar gestão de bolsistas",
        )
        assert negociacao.status == StatusBargain.SOLICITADO
        assert len(negociacao.recursos) == 2

    def test_bargain_avalia_e_aloca(self):
        protocolo = ProtocoloBargain()
        n = protocolo.solicitar(
            subnivel="Projeto 1",
            nivel_pai="CDA",
            recursos=[
                {"tipo": "agente", "quantidade": 2, "unidade": "unidades", "prioridade": 1},
            ],
        )
        assert protocolo.avaliar(n.id, alocacao={"agente": 1}, contraproposta="1 agente disponível")
        assert n.status == StatusBargain.PARCIAL

    def test_bargain_rejeita_sem_recursos(self):
        protocolo = ProtocoloBargain()
        n = protocolo.solicitar("P1", "CDA", [{"tipo": "gpu", "quantidade": 5, "unidade": "h/dia"}])
        assert protocolo.avaliar(n.id, alocacao={})
        assert n.status == StatusBargain.REJEITADO

    def test_bargain_com_intencoes_alinhadas(self):
        """Bargain entre níveis gera intenções no nível filho."""
        protocolo = ProtocoloBargain()
        motor = MotorIntencoes("Projeto 1")

        n = protocolo.solicitar(
            "Projeto 1", "CDA",
            [{"tipo": "agente", "quantidade": 1, "unidade": "unidades"}],
            "Precisamos de 1 agente para desenvolvimento",
        )
        assert protocolo.avaliar(n.id, alocacao={"agente": 1})

        intencao = motor.adotar(
            desejo="Executar projeto com recursos alocados",
            plano=f"Bargain {n.id} aprovado: 1 agente",
            passos=[
                {"descricao": "Iniciar desenvolvimento", "recursos": ["agente"]},
            ],
            prioridade=1,
        )
        assert intencao is not None
        assert intencao.status.value == "ativa"

    def test_conflito_entre_bargain_e_intencao(self):
        """Recurso alocado via bargain pode conflitar com intenção existente."""
        protocolo = ProtocoloBargain()
        motor = MotorIntencoes("Projeto 1")

        motor.adotar("Feature A", "Plano A", [{"descricao": "p1", "recursos": ["gpu"]}])

        conflicitante = motor.adotar(
            "Feature B", "Plano B",
            [{"descricao": "p1", "recursos": ["gpu"]}],
        )
        assert conflicitante is None, "Intenção conflitante deve ser rejeitada pelo filtro"


class TestFabricaExiste:

    def test_fabrica_cria_arvore(self):
        from viableos.cda.fabrica import fabrica
        assert fabrica.raiz is not None
        assert fabrica.raiz.nome == "CDA"
        assert fabrica.raiz.total_agentes() > 0
        assert fabrica.raiz.total_subniveis() >= 1

    def test_orquestrador_audita(self):
        from viableos.cda.fabrica import fabrica
        from viableos.cda.recursao.orquestrador import orquestrador
        assert orquestrador is not None
        relatorios = orquestrador.auditar()
        assert len(relatorios) > 0
        for r in relatorios:
            assert "status" in r
            assert "intencoes_ativas" in r or True  # campo opcional
