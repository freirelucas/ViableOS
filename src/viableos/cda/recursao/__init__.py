"""Recursão VSM da CDA.

Cada nível é um sistema viável completo (S1-S5) que pode conter
subsistemas viáveis como suas unidades S1.

  Level 1: CDA (corporação)
    S5 = Diretora (humana)
    S4 = Inteligência Estratégica
    S3 = Gestão de Projetos
    S3* = Auditoria
    S2 = Coordenação
    S1 = [Projeto 1, Projeto 2, ...]  ← cada um é NivelVSM

Conexões entre níveis:
  - S3 bargain:    S3(N) negocia recursos com S3(N+1) de cada S1
  - Algêdonico:    canal(N+1) → S5(N) pulando hierarquia
  - Auditoria:     S3*(N) audita S3(N+1) de cada S1
  - Identidade:    propósito(N+1) = propósito(N) + específico
"""

from viableos.cda.recursao.nivel import NivelVSM
from viableos.cda.recursao.clock import Clock, FrequenciaClock, sistema_clocks
from viableos.cda.recursao.bargain import ProtocoloBargain, protocolo_bargain
from viableos.cda.recursao.orquestrador import OrquestradorRecursivo, orquestrador

__all__ = [
    "NivelVSM",
    "Clock", "FrequenciaClock", "sistema_clocks",
    "ProtocoloBargain", "protocolo_bargain",
    "OrquestradorRecursivo", "orquestrador",
]
