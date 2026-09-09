"""Testes para prompts.py — prompts ricos em PT-BR."""

import pytest
from viableos.cda.prompts import (
    prompt_s1, prompt_s2, prompt_s3, prompt_s3star, prompt_s4, prompt_s5,
)


class TestPromptS1:
    def test_gera_prompt_basico(self):
        r = prompt_s1(
            unidade={"name": "Dev", "purpose": "Escrever código", "tools": ["git"]},
            identidade={"values": ["qualidade"], "never_do": ["não hackear"]},
            regras=[],
            hitl={"approval_required": ["deploy"]},
            outras_unidades=["Gestor"],
        )
        assert "Dev" in r
        assert "Escrever código" in r
        assert "git" in r
        assert "qualidade" in r
        assert "não hackear" in r

    def test_com_modos(self):
        r = prompt_s1(
            unidade={"name": "Dev", "purpose": "X", "tools": []},
            identidade={"values": [], "never_do": []},
            regras=[],
            hitl={"approval_required": []},
            outras_unidades=[],
            modos={"normal": {"description": "Normal"}, "elevated": {"triggers": ["risco"]}, "crisis": {"triggers": ["emergência"]}},
        )
        assert "Modos Operacionais" in r


class TestPromptS2:
    def test_gera_prompt(self):
        r = prompt_s2(
            regras=[{"trigger": "conflito", "action": "mediar"}],
            unidades_s1=["Dev", "Gestor"],
            identidade={"purpose": "Coordenar", "never_do": []},
        )
        assert "Coordenador" in r
        assert "Dev" in r


class TestPromptS3:
    def test_gera_prompt(self):
        r = prompt_s3(
            identidade={"purpose": "Gerenciar"},
            unidades_s1=["Dev"],
            orcamento_mensal=1000,
            alocacao_recursos="prioridade alta",
            ritmo_relatorios="semanal",
        )
        assert "Gestor de Projetos" in r
        assert "R$1000" in r


class TestPromptS3Star:
    def test_gera_prompt(self):
        r = prompt_s3star(
            identidade={"purpose": "Auditar"},
            checks=[{"name": "R1", "target": "S1", "method": "verificação"}],
            unidades_s1=["Dev"],
            ao_falhar="Escalar",
        )
        assert "Auditor" in r
        assert "R1" in r


class TestPromptS4:
    def test_gera_prompt(self):
        r = prompt_s4(
            identidade={"purpose": "Analisar"},
            monitoramento={"competitors": ["Gov.br"], "technology": ["IA"], "regulation": ["LGPD"]},
        )
        assert "Inteligente" in r
        assert "Gov.br" in r


class TestPromptS5:
    def test_gera_prompt(self):
        r = prompt_s5(
            identidade={"purpose": "Governar", "values": ["transparência"], "never_do": []},
            hitl={"approval_required": ["estratégia"], "emergency_alerts": ["crise"]},
        )
        assert "Guardião" in r
        assert "transparência" in r
