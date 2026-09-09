"""CDA — Corporação Digital Autônoma para digitalização do IPEA.

Este módulo implementa o núcleo da CDA: a classe base AgenteGLM, os subsistemas
VSM (S1-S5), o motor de decisões, os canais algêdonicos, e a integração com
o GLM 5.2 do IPEA.

A CDA NÃO é um sistema de gestão de bolsistas. A CDA é uma corporação de
agentes autônomos contratada para digitalizar processos do IPEA.
A gestão de bolsistas é apenas o Projeto 1.
"""

from viableos.cda.agente import AgenteGLM, StatusAgente, TipoAgente
from viableos.cda.algedonic import SinalAlgedonico, GravidadeSinal

__all__ = ["AgenteGLM", "StatusAgente", "TipoAgente", "SinalAlgedonico", "GravidadeSinal"]
