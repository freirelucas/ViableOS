"""Testes para syntegration.py — protocolo Team Syntegrity."""

import pytest
from viableos.cda.syntegration import (
    ProtocoloSyntegration,
    FaseSyntegration,
    GerenciadorSyntegration,
    gerenciador_syntegration,
    verificar_gatilho_sinais_convergentes_s4,
    verificar_gatilho_falhas_coordenacao,
    verificar_gatilho_erros_correlacionados,
    verificar_gatilho_alerta_s5,
)


AGENTES_TESTE = [
    {"nome": "S1_Dev", "tipo": "s1_dev", "proposito": "Escrever código"},
    {"nome": "S2_Coord", "tipo": "s2_coord", "proposito": "Coordenar"},
    {"nome": "S3_Gestao", "tipo": "s3_gestao", "proposito": "Gerenciar"},
    {"nome": "S4_Intel", "tipo": "s4_inteligencia", "proposito": "Analisar"},
]


class TestProtocoloSyntegration:
    def test_criacao(self):
        p = ProtocoloSyntegration(gatilho="teste")
        assert p.fase == FaseSyntegration.PROPOSTA
        assert p.esta_ativo is False

    def test_avancar_osi(self):
        p = ProtocoloSyntegration(gatilho="teste")
        p.avancar(AGENTES_TESTE, tick=1)  # PROPOSTA → OSI (inicia)
        assert p.fase == FaseSyntegration.OSI
        # Participants set in PROPOSTA, OSI not yet run
        assert len(p.participantes) == 4

    def test_avancar_jostle(self):
        p = ProtocoloSyntegration(gatilho="teste")
        p.avancar(AGENTES_TESTE, tick=1)  # PROPOSTA → OSI
        p.avancar(AGENTES_TESTE, tick=2)  # OSI → JOSTLE (osi runs, sets declarations)
        p.avancar(AGENTES_TESTE, tick=3)  # JOSTLE → LEILAO (jostle runs, sets topics)
        assert p.fase == FaseSyntegration.LEILAO
        assert len(p.declaracoes_importancia) == 4
        assert len(p.topicos) >= 2

    def test_avancar_completo(self):
        p = ProtocoloSyntegration(gatilho="teste", max_topicos=2)
        for i in range(8):
            p.avancar(AGENTES_TESTE, tick=i)
        assert p.fase == FaseSyntegration.CONCLUIDO
        assert len(p.resultados) > 0

    def test_cancelar(self):
        p = ProtocoloSyntegration(gatilho="teste")
        p.avancar(AGENTES_TESTE, tick=1)
        p.fase = FaseSyntegration.CANCELADO
        assert p.esta_concluido is True

    def test_to_dict(self):
        p = ProtocoloSyntegration(gatilho="teste")
        d = p.to_dict()
        assert "id" in d
        assert "fase" in d


class TestGatilhos:
    def test_s4_sinais(self):
        agentes = [{"tipo": "s4_inteligencia", "sinais_detectados": 5}]
        assert verificar_gatilho_sinais_convergentes_s4(agentes, 3) is not None

    def test_s4_sem_sinais(self):
        agentes = [{"tipo": "s4_inteligencia", "sinais_detectados": 1}]
        assert verificar_gatilho_sinais_convergentes_s4(agentes, 3) is None

    def test_s2_conflitos(self):
        agentes = [{"tipo": "s2_coord", "conflitos_detectados": 4}]
        assert verificar_gatilho_falhas_coordenacao(agentes, 3) is not None

    def test_s3star_erros(self):
        agentes = [{"tipo": "s3_audit", "achados_auditoria": [{"status": "fail"}, {"status": "fail"}]}]
        assert verificar_gatilho_erros_correlacionados(agentes, 3) is None

    def test_s5_alerta(self):
        assert verificar_gatilho_alerta_s5(5, 3) is not None
        assert verificar_gatilho_alerta_s5(1, 3) is None


class TestGerenciadorSyntegration:
    def test_iniciar_manual(self):
        g = GerenciadorSyntegration()
        p = g.iniciar_manual("manual", "Diretora", AGENTES_TESTE)
        assert p.fase == FaseSyntegration.OSI
        assert len(g.obter_ativos()) == 1

    def test_verificar_automatico(self):
        g = GerenciadorSyntegration()
        agentes = [{"tipo": "s4_inteligencia", "sinais_detectados": 5}]
        p = g.verificar_automatico(agentes, limiar=3)
        assert p is not None

    def test_avancar(self):
        g = GerenciadorSyntegration()
        p = g.iniciar_manual("teste", "auto", AGENTES_TESTE)
        r = g.avancar(p.id, AGENTES_TESTE)
        assert r == FaseSyntegration.JOSTLE

    def test_cancelar(self):
        g = GerenciadorSyntegration()
        p = g.iniciar_manual("teste", "auto", AGENTES_TESTE)
        assert g.cancelar(p.id) is True
        assert len(g.obter_historico()) == 1

    def test_singleton(self):
        assert gerenciador_syntegration is not None
