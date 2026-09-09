"""Testes para topology.py — validação de comunicação VSM."""

import pytest
from viableos.cda.topology import TopologyValidator, topology_validator


class TestTopologyValidator:
    def setup_method(self):
        self.v = TopologyValidator()

    def test_s1_to_s2_valido(self):
        r = self.v.validar("S1_Dev", "S2_Coord", "s1", "s2")
        assert r.permitido is True

    def test_s2_to_s3_valido(self):
        r = self.v.validar("S2_Coord", "S3_Gestao", "s2", "s3")
        assert r.permitido is True

    def test_s1_to_s3_direto_invalido(self):
        r = self.v.validar("S1_Dev", "S3_Gestao", "s1", "s3")
        assert r.permitido is False

    def test_s1_to_s1_self_invalido(self):
        r = self.v.validar("S1_Dev", "S1_Dev", "s1", "s1")
        assert r.permitido is False

    def test_s3star_para_s1_auditoria(self):
        r = self.v.validar("S3_Audit", "S1_Dev", "s3*", "s1")
        assert r.permitido is True

    def test_s4_para_s2(self):
        r = self.v.validar("S4_Intel", "S2_Coord", "s4", "s2")
        assert r.permitido is True

    def test_s4_para_s5(self):
        r = self.v.validar("S4_Intel", "S5_Diretora", "s4", "s5")
        assert r.permitido is True

    def test_nivel_nao_mapeado_permitido(self):
        r = self.v.validar("X", "Y", "unknown", "also_unknown")
        assert r.permitido is True

    def test_validar_por_tipo(self):
        r = self.v.validar_por_tipo("Dev", "Coord", "s1_desenvolvedor", "s2_coordenacao")
        assert r.permitido is True

    def test_validar_por_tipo_s3star(self):
        r = self.v.validar_por_tipo("Audit", "Dev", "s3_auditoria", "s1_desenvolvedor")
        assert r.permitido is True

    def test_blocos_registrados(self):
        self.v.validar("S1_Dev", "S3_Gestao", "s1", "s3")
        assert self.v.total_blocos == 1

    def test_singleton(self):
        assert topology_validator is not None
        assert isinstance(topology_validator, TopologyValidator)
