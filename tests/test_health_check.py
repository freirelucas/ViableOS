"""Testes para health_check.py — checks de boot e periódico."""

import pytest
from viableos.cda.health_check import (
    health_check_boot,
    health_check_periodico,
    RelatorioHealthCheck,
)


class TestHealthCheckBoot:
    def test_boot_retorna_relatorio(self):
        config = {"viable_system": {"agents": []}}
        r = health_check_boot(config)
        assert isinstance(r, RelatorioHealthCheck)
        assert r.momento == "boot"

    def test_boot_conta_checks(self):
        config = {"viable_system": {"agents": []}}
        r = health_check_boot(config)
        assert r.total_checks > 0
        # info severidade não conta como warning — passes + warnings + criticals pode ser <= total
        assert r.passes + r.warnings + r.criticals <= r.total_checks

    def test_r1_conforme_quando_apenas_s1_tem_llm(self):
        config = {
            "viable_system": {
                "agents": [
                    {"tipo": "s1_dev", "ferramentas": ["git", "glm-chat"]},
                    {"tipo": "s2_coord", "ferramentas": ["cronograma"]},
                ]
            }
        }
        r = health_check_boot(config)
        r1 = [i for i in r.itens if "R1" in i.nome]
        assert len(r1) == 1
        assert r1[0].passou is True

    def test_r1_violado_quando_s2_tem_llm(self):
        config = {
            "viable_system": {
                "agents": [
                    {"tipo": "s1_dev", "ferramentas": ["git"]},
                    {"tipo": "s2_coord", "ferramentas": ["glm-chat"]},
                ]
            }
        }
        r = health_check_boot(config)
        r1 = [i for i in r.itens if "R1" in i.nome]
        assert r1[0].passou is False
        assert r1[0].severidade == "critical"

    def test_r5_conforme_quando_nenhum_s5(self):
        config = {"viable_system": {"agents": [{"tipo": "s1_dev", "ferramentas": []}]}}
        r = health_check_boot(config)
        r5 = [i for i in r.itens if "R5" in i.nome]
        assert r5[0].passou is True

    def test_r5_violado_quando_s5_agente(self):
        config = {"viable_system": {"agents": [{"tipo": "s5_diretor", "ferramentas": []}]}}
        r = health_check_boot(config)
        r5 = [i for i in r.itens if "R5" in i.nome]
        assert r5[0].passou is False


class TestHealthCheckPeriodico:
    def test_periodico_retorna_relatorio(self):
        estado = {"agentes": [], "sinais_pendentes": [], "budget_usage": []}
        r = health_check_periodico(estado)
        assert isinstance(r, RelatorioHealthCheck)
        assert r.momento == "periodico"

    def test_sinais_vermelhos_critical(self):
        estado = {
            "agentes": [],
            "sinais_pendentes": [{"gravidade": "vermelho"}],
            "budget_usage": [],
        }
        r = health_check_periodico(estado)
        crits = [i for i in r.itens if i.severidade == "critical"]
        assert len(crits) > 0
