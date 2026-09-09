"""Classe base para todos os agentes da CDA."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from viableos.cda.bratman import (
    EstrategiaCompromisso,
    MotorIntencoes,
    StatusIntencao,
    agenda_bratman,
)


class StatusAgente(str, enum.Enum):
    ONLINE = "online"
    TRABALHANDO = "trabalhando"
    STANDBY = "standby"
    ERRO = "erro"


class TipoAgente(str, enum.Enum):
    S5_DIRETOR = "s5_diretor"
    S4_INTELIGENCIA = "s4_inteligencia"
    S3_GESTAO = "s3_gestao"
    S3_AUDITORIA = "s3_auditoria"
    S2_COORDENACAO = "s2_coordenacao"
    S1_DESENVOLVEDOR = "s1_desenvolvedor"
    S1_EXECUTOR = "s1_executor"
    S1_ANALISTA = "s1_analista"


@dataclass
class Decisao:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    assunto: str = ""
    solicitante: str = ""
    contexto: str = ""
    urgencia: str = "media"
    opcoes: list[str] = field(default_factory=list)
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolvido_em: str | None = None
    resolucao: str | None = None
    resolvido_por: str | None = None


@dataclass
class Projeto:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    nome: str = ""
    descricao: str = ""
    status: str = "planejado"
    progresso: int = 0
    artefatos: list[str] = field(default_factory=list)
    agente_responsavel: str = ""


class AgenteGLM:
    """Um membro da CDA — um agente autônomo movido a GLM 5.2.

    Integra Bratman intention engine para estabilidade de intenção.
    Cada agente tem um MotorIntencoes que gerencia:
    - Deliberação: quais desejos viram intenções
    - Compromisso: estratégia BLIND/SINGLE_MINDED/OPEN
    - Filtro de admissibilidade: opções compatíveis com intenções ativas
    """

    def __init__(
        self,
        nome: str,
        tipo: TipoAgente,
        proposito: str,
        system_prompt: str,
        ferramentas: list[str] | None = None,
        estrategia_compromisso: EstrategiaCompromisso | None = None,
        modelo: str | None = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.nome = nome
        self.tipo = tipo
        self.proposito = proposito
        self.system_prompt = system_prompt
        self.status = StatusAgente.STANDBY
        self.ferramentas = ferramentas or []
        self.modelo = modelo or ""
        self.atividade = "Aguardando tarefa"
        self.ultima_acao = datetime.now(timezone.utc).isoformat()
        self.decisoes_pendentes: list[Decisao] = []
        self.historico: list[dict[str, str]] = []
        self._motor_intencoes = agenda_bratman.obter_motor(nome)
        self._estrategia_padrao = estrategia_compromisso or EstrategiaCompromisso.SINGLE_MINDED

    def definir_atividade(self, atividade: str) -> None:
        self.atividade = atividade
        self.ultima_acao = datetime.now(timezone.utc).isoformat()

    def alterar_status(self, status: StatusAgente) -> None:
        self.status = status

    def solicitar_decisao(
        self,
        assunto: str,
        contexto: str,
        opcoes: list[str],
        urgencia: str = "media",
    ) -> Decisao:
        d = Decisao(
            assunto=assunto,
            solicitante=self.nome,
            contexto=contexto,
            urgencia=urgencia,
            opcoes=opcoes,
        )
        self.decisoes_pendentes.append(d)
        return d

    def registrar_acao(self, acao: str, resultado: str = "") -> None:
        self.historico.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "acao": acao,
            "resultado": resultado,
        })

    def adotar_intencao(
        self,
        desejo: str,
        plano: str,
        passos: list[dict] | None = None,
        prioridade: int = 3,
    ):
        return self._motor_intencoes.adotar(
            desejo=desejo,
            plano=plano,
            passos=passos,
            estrategia=self._estrategia_padrao,
            prioridade=prioridade,
        )

    def executar_passo(self, intencao_id: str):
        return self._motor_intencoes.executar_passo(intencao_id)

    def intencoes_ativas(self):
        return self._motor_intencoes.listar(apenas_ativas=True)

    def filtrar_opcoes(self, opcoes: list[dict]) -> list[dict]:
        return self._motor_intencoes.filtrar_opcoes(opcoes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo.value,
            "status": self.status.value,
            "proposito": self.proposito,
            "atividade": self.atividade,
            "ultima_acao": self.ultima_acao,
            "ferramentas": self.ferramentas,
            "modelo": self.modelo,
            "decisoes_pendentes": len(self.decisoes_pendentes),
            "intencoes_ativas": len(self._motor_intencoes.intencoes_ativas),
            "estrategia": self._estrategia_padrao.value,
        }
