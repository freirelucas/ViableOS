"""Testes para budget_monitor.py — monitoramento de orçamento."""

import pytest
from viableos.cda.budget_monitor import BudgetMonitor, budget_monitor


class TestBudgetMonitor:
    def setup_method(self):
        self.m = BudgetMonitor()

    def test_registrar_uso(self):
        self.m.registrar_uso("S1", tokens=1000, chamadas=5, custo_usd=0.05)
        uso = self.m.obter_uso("S1")
        assert uso["tokens"] == 1000
        assert uso["chamadas"] == 5

    def test_registrar_multiplos(self):
        self.m.registrar_uso("S1", tokens=1000, custo_usd=0.05)
        self.m.registrar_uso("S1", tokens=500, custo_usd=0.03)
        uso = self.m.obter_uso("S1")
        assert uso["tokens"] == 1500
        assert uso["custo_usd"] == 0.08

    def test_verificar_desvio_ok(self):
        self.m.definir_orcamento("S1", 1.0)
        self.m.registrar_uso("S1", custo_usd=0.5)
        alertas = self.m.verificar_desvio()
        assert len(alertas) == 0

    def test_verificar_desvio_warning(self):
        self.m.definir_orcamento("S1", 1.0)
        self.m.registrar_uso("S1", custo_usd=0.85)
        alertas = self.m.verificar_desvio()
        assert len(alertas) == 1
        assert alertas[0].gravidade == "amarelo"

    def test_verificar_desvio_critical(self):
        self.m.definir_orcamento("S1", 1.0)
        self.m.registrar_uso("S1", custo_usd=0.96)
        alertas = self.m.verificar_desvio()
        assert len(alertas) == 1
        assert alertas[0].gravidade == "vermelho"

    def test_obter_uso_lista(self):
        self.m.registrar_uso("S1", tokens=100, custo_usd=0.01)
        self.m.registrar_uso("S2", tokens=200, custo_usd=0.02)
        lista = self.m.obter_uso()
        assert len(lista) == 2

    def test_obter_alertas(self):
        self.m.definir_orcamento("S1", 1.0)
        self.m.registrar_uso("S1", custo_usd=0.85)
        self.m.verificar_desvio()
        alertas = self.m.obter_alertas()
        assert len(alertas) == 1

    def test_singleton(self):
        assert budget_monitor is not None
        assert isinstance(budget_monitor, BudgetMonitor)
