"""Pipeline de autodesenvolvimento da CDA.

O Agente Desenvolvedor recebe tarefas, gera artefatos (código, skills, docs),
e registra a produção no projeto correspondente. Artefatos carregam hash
SHA-256 do conteúdo quando disponível (R2 honesta — ver
docs/audits/2026-09-03-coerencia-cda.md §2.5): a reversibilidade de escrita é
delegada aos runtimes externos (git do envelope), mas a identidade do que foi
produzido fica registrada no ato.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TipoArtefato(str, Enum):
    CODIGO = "codigo"
    SKILL = "skill"
    DOCUMENTO = "documento"
    CONFIG = "configuracao"
    FERRAMENTA = "ferramenta"
    TESTE = "teste"


class StatusTarefa(str, Enum):
    PENDENTE = "pendente"
    EM_EXECUCAO = "em_execucao"
    CONCLUIDA = "concluida"
    BLOQUEADA = "bloqueada"
    REJEITADA = "rejeitada"


@dataclass
class Artefato:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    nome: str = ""
    tipo: TipoArtefato = TipoArtefato.CODIGO
    descricao: str = ""
    caminho: str = ""
    projeto: str = ""
    linguagem: str = ""
    linhas: int = 0
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    autor: str = "Agente Desenvolvedor"
    # R2 honesta: hash do conteúdo quando disponível; verificado=True indica
    # que o hash corresponde a conteúdo lido de fato (não a metadados).
    hash_conteudo: str = ""
    verificado: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo.value,
            "descricao": self.descricao,
            "caminho": self.caminho,
            "projeto": self.projeto,
            "linguagem": self.linguagem,
            "linhas": self.linhas,
            "criado_em": self.criado_em,
            "autor": self.autor,
            "hash_conteudo": self.hash_conteudo,
            "verificado": self.verificado,
        }


@dataclass
class TarefaDesenvolvimento:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    titulo: str = ""
    descricao: str = ""
    projeto: str = "Projeto 1"
    status: StatusTarefa = StatusTarefa.PENDENTE
    artefatos: list[str] = field(default_factory=list)
    solicitante: str = "S3 - Gestão de Projetos"
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    concluido_em: str | None = None
    notas: str = ""


class PipelineAutodesenvolvimento:
    """Gerencia o ciclo de desenvolvimento autônomo da CDA."""

    def __init__(self):
        self._tarefas: list[TarefaDesenvolvimento] = []
        self._artefatos: list[Artefato] = []

    def criar_tarefa(
        self,
        titulo: str,
        descricao: str,
        projeto: str = "Projeto 1",
        solicitante: str = "S3 - Gestão de Projetos",
    ) -> TarefaDesenvolvimento:
        t = TarefaDesenvolvimento(
            titulo=titulo,
            descricao=descricao,
            projeto=projeto,
            solicitante=solicitante,
        )
        self._tarefas.append(t)
        return t

    def iniciar(self, tarefa_id: str) -> bool:
        for t in self._tarefas:
            if t.id == tarefa_id and t.status == StatusTarefa.PENDENTE:
                t.status = StatusTarefa.EM_EXECUCAO
                return True
        return False

    def concluir(self, tarefa_id: str, notas: str = "") -> bool:
        for t in self._tarefas:
            if t.id == tarefa_id and t.status == StatusTarefa.EM_EXECUCAO:
                t.status = StatusTarefa.CONCLUIDA
                t.concluido_em = datetime.now(timezone.utc).isoformat()
                t.notas = notas
                return True
        return False

    def registrar_artefato(
        self,
        nome: str,
        tipo: TipoArtefato,
        descricao: str,
        caminho: str = "",
        projeto: str = "Projeto 1",
        linguagem: str = "",
        linhas: int = 0,
        conteudo: str | None = None,
    ) -> Artefato:
        hash_conteudo = ""
        verificado = False

        if conteudo is None and caminho:
            # Tenta ler o conteúdo real do arquivo dentro do repo
            candidato = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", caminho)
            )
            try:
                with open(candidato, encoding="utf-8", errors="replace") as f:
                    conteudo = f.read()
            except OSError:
                conteudo = None

        if conteudo is not None:
            hash_conteudo = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
            verificado = True

        a = Artefato(
            nome=nome,
            tipo=tipo,
            descricao=descricao,
            caminho=caminho,
            projeto=projeto,
            linguagem=linguagem,
            linhas=linhas,
            hash_conteudo=hash_conteudo,
            verificado=verificado,
        )
        self._artefatos.append(a)
        return a

    def vincular_artefato(self, tarefa_id: str, artefato_id: str) -> bool:
        for t in self._tarefas:
            if t.id == tarefa_id:
                t.artefatos.append(artefato_id)
                return True
        return False

    def tarefas(self, projeto: str | None = None) -> list[TarefaDesenvolvimento]:
        if projeto:
            return [t for t in self._tarefas if t.projeto == projeto]
        return list(self._tarefas)

    def artefatos(self, projeto: str | None = None) -> list[Artefato]:
        if projeto:
            return [a for a in self._artefatos if a.projeto == projeto]
        return list(self._artefatos)

    def tarefas_para_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "id": t.id,
                "titulo": t.titulo,
                "descricao": t.descricao,
                "projeto": t.projeto,
                "status": t.status.value,
                "artefatos": t.artefatos,
                "solicitante": t.solicitante,
                "criado_em": t.criado_em,
                "concluido_em": t.concluido_em,
            }
            for t in self._tarefas
        ]

    def artefatos_para_dict(self, projeto: str | None = None) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.artefatos(projeto)]


pipeline = PipelineAutodesenvolvimento()
