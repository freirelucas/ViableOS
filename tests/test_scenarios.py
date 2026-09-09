"""Testes para scenarios.py — cenários IPEA e simulador."""

import pytest
from viableos.cda.scenarios import SimuladorCenarios, CenarioIPEA, simulador


class TestCenarioIPEA:
    def test_cenario_criacao(self):
        c = CenarioIPEA("teste", [
            {"tick": 1, "categoria": "crise", "titulo": "Teste", "descricao": "desc", "relevancia": 5}
        ])
        assert c.nome == "teste"
        assert c.total_eventos == 1

    def test_eventos_em_tick(self):
        c = CenarioIPEA("teste", [
            {"tick": 1, "categoria": "crise", "titulo": "A", "descricao": "d", "relevancia": 5},
            {"tick": 5, "categoria": "dados", "titulo": "B", "descricao": "d", "relevancia": 3},
        ])
        assert len(c.eventos_em(1)) == 1
        assert len(c.eventos_em(5)) == 1
        assert len(c.eventos_em(3)) == 0

    def test_injetar_evento(self):
        c = CenarioIPEA("teste")
        c.injetar_evento({"tick": 10, "categoria": "crise", "titulo": "X", "descricao": "d", "relevancia": 4})
        assert c.total_eventos == 1


class TestSimuladorCenarios:
    def test_listar_cenarios_padrao(self):
        s = SimuladorCenarios()
        cenarios = s.listar_cenarios()
        assert len(cenarios) >= 3
        nomes = [c["nome"] for c in cenarios]
        assert "ipea_digital" in nomes

    def test_simular_cenario(self):
        s = SimuladorCenarios()
        r = s.simular("ipea_digital", ticks=50)
        assert r.ticks_simulados == 50
        assert r.eventos_processados > 0
        assert "densidade_eventos" in r.metricas

    def test_simular_inexistente_erro(self):
        s = SimuladorCenarios()
        with pytest.raises(ValueError):
            s.simular("nao_existe")

    def test_historico(self):
        s = SimuladorCenarios()
        s.simular("ipea_digital", ticks=10)
        h = s.obter_historico()
        assert len(h) == 1

    def test_singleton(self):
        assert simulador is not None
        assert isinstance(simulador, SimuladorCenarios)
