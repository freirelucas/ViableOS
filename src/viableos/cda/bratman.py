"""Motor Bratmaniano — intenção estável para AgentesGLM.

Três papéis funcionais (Bratman 1987):
1. Deliberação: quais desejos virarão intenções (filtro de admissibilidade)
2. Raciocínio meios-fins: como executar intenções (planos parciais)
3. Estabilidade de intenção: quando reconsiderar (commitment strategy)

Integra com AgenteGLM existente — adiciona camada de intencionalidade
sem substituir a estrutura VSM.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class EstrategiaCompromisso(str, enum.Enum):
    """Três estratégias de commitment (Bratman 1987, cap. 4)."""
    BLIND = "blind"
    SINGLE_MINDED = "single_minded"
    OPEN = "open"


class StatusIntencao(str, enum.Enum):
    ATIVA = "ativa"
    EM_EXECUCAO = "em_execucao"
    SUSPENSA = "suspensa"
    CONCLUIDA = "concluida"
    ABANDONADA = "abandonada"


class StatusPasso(str, enum.Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    BLOQUEADO = "bloqueado"


@dataclass
class Passo:
    descricao: str = ""
    status: StatusPasso = StatusPasso.PENDENTE
    responsavel: str = ""
    recursos: list[str] = field(default_factory=list)
    dependencias: list[str] = field(default_factory=list)
    resultado: str = ""


@dataclass
class Intencao:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    agente: str = ""
    desejo: str = ""
    plano: str = ""
    passos: list[Passo] = field(default_factory=list)
    status: StatusIntencao = StatusIntencao.ATIVA
    estrategia: EstrategiaCompromisso = EstrategiaCompromisso.SINGLE_MINDED
    adotada_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    revisada_em: str = ""
    evidencia_contraria: list[str] = field(default_factory=list)
    prioridade: int = 3

    def passo_atual(self) -> Passo | None:
        for p in self.passos:
            if p.status in (StatusPasso.PENDENTE, StatusPasso.EM_ANDAMENTO):
                return p
        return None

    def proporcao_concluida(self) -> float:
        if not self.passos:
            return 0.0
        concluidos = sum(1 for p in self.passos if p.status == StatusPasso.CONCLUIDO)
        return concluidos / len(self.passos)

    def reseta_evidencia(self) -> None:
        self.evidencia_contraria = []


def _deve_reconsiderar(
    intencao: Intencao,
    estrategia: EstrategiaCompromisso,
    mudancas_contexto: list[str],
    intensidade_evidencia: float = 0.0,
) -> bool:
    """Determina se a intenção deve ser reconsiderada."""
    if estrategia == EstrategiaCompromisso.BLIND:
        return False
    if estrategia == EstrategiaCompromisso.OPEN:
        return intensidade_evidencia > 0.3 or len(mudancas_contexto) >= 2
    evidencia_relevante = [e for e in mudancas_contexto if e in intencao.evidencia_contraria]
    return len(evidencia_relevante) >= 2 or intensidade_evidencia > 0.7


def _filtrar_admissiveis(
    opcoes: list[dict[str, Any]],
    intencoes_ativas: list[Intencao],
    estrategia: EstrategiaCompromisso,
) -> list[dict[str, Any]]:
    """Filtro de admissibilidade: opções compatíveis com intenções existentes."""
    if not intencoes_ativas:
        return opcoes
    if estrategia == EstrategiaCompromisso.OPEN:
        return opcoes
    desejos_ativos = {i.desejo for i in intencoes_ativas}
    filtradas = []
    for op in opcoes:
        desejo_op = op.get("desejo", "")
        if not desejo_op:
            filtradas.append(op)
            continue
        if desejo_op in desejos_ativos:
            continue
        conflitos = [
            i for i in intencoes_ativas
            if _opcoes_conflitam(op, i)
        ]
        if not conflitos:
            filtradas.append(op)
    return filtradas


def _recursos_flat(passos: list[Any]) -> set[str]:
    recursos: set[str] = set()
    for p in passos:
        if isinstance(p, dict):
            for r in p.get("recursos", []):
                if isinstance(r, str):
                    recursos.add(r)
        elif hasattr(p, "recursos"):
            for r in p.recursos:
                if isinstance(r, str):
                    recursos.add(r)
    return recursos


def _opcoes_conflitam(opcao: dict[str, Any], intencao: Intencao) -> bool:
    recursos_op_lista = opcao.get("recursos_necessarios", [])
    recursos_op: set[str] = set()
    for item in recursos_op_lista:
        if isinstance(item, str):
            recursos_op.add(item)
        elif isinstance(item, list):
            for r in item:
                if isinstance(r, str):
                    recursos_op.add(r)
    recursos_int = _recursos_flat(intencao.passos)
    return len(recursos_op & recursos_int) > 0


class MotorIntencoes:
    """Motor Bratmaniano para agentes CDA.

    Cada agente pode ter múltiplas intenções ativas.
    O motor gerencia:
    - Adoção de novas intenções (deliberação)
    - Execução de passos (meios-fins)
    - Reconsideração (estabilidade)
    """

    def __init__(self, agente_nome: str):
        self.agente_nome = agente_nome
        self._intencoes: list[Intencao] = []
        self._estrategia_padrao = EstrategiaCompromisso.SINGLE_MINDED
        self._historico_intencoes: list[Intencao] = []

    @property
    def intencoes_ativas(self) -> list[Intencao]:
        return [i for i in self._intencoes if i.status in (
            StatusIntencao.ATIVA, StatusIntencao.EM_EXECUCAO, StatusIntencao.SUSPENSA
        )]

    @property
    def intencoes_executando(self) -> list[Intencao]:
        return [i for i in self._intencoes if i.status == StatusIntencao.EM_EXECUCAO]

    def adotar(
        self,
        desejo: str,
        plano: str,
        passos: list[dict[str, Any]] | None = None,
        estrategia: EstrategiaCompromisso | None = None,
        prioridade: int = 3,
    ) -> Intencao | None:
        """Deliberação: adota nova intenção se compatível com as ativas."""
        opcao = {
            "desejo": desejo,
            "plano": plano,
            "recursos_necessarios": [
                p.get("recursos", []) for p in (passos or [])
            ],
            "prioridade": prioridade,
        }
        admissiveis = _filtrar_admissiveis(
            [opcao],
            self.intencoes_ativas,
            estrategia or self._estrategia_padrao,
        )
        if not admissiveis:
            return None

        passos_obj = []
        for p in (passos or []):
            passos_obj.append(Passo(
                descricao=p.get("descricao", ""),
                responsavel=p.get("responsavel", self.agente_nome),
                recursos=p.get("recursos", []),
                dependencias=p.get("dependencias", []),
            ))

        intencao = Intencao(
            agente=self.agente_nome,
            desejo=desejo,
            plano=plano,
            passos=passos_obj,
            estrategia=estrategia or self._estrategia_padrao,
            prioridade=prioridade,
        )
        self._intencoes.append(intencao)
        self._persistir_estado(intencao)
        return intencao

    def executar_passo(self, intencao_id: str) -> dict[str, Any]:
        """Avança um passo na intenção (meios-fins)."""
        for i in self._intencoes:
            if i.id != intencao_id:
                continue

            passo = i.passo_atual()
            if passo is None:
                i.status = StatusIntencao.CONCLUIDA
                self._persistir_estado(i)
                return {"status": "concluida", "proporcao": 1.0}

            passo.status = StatusPasso.EM_ANDAMENTO
            i.status = StatusIntencao.EM_EXECUCAO

            if _deve_reconsiderar(i, i.estrategia, i.evidencia_contraria):
                i.status = StatusIntencao.SUSPENSA
                self._persistir_estado(i)
                return {"status": "suspensa", "motivo": "evidencia_contraria"}

            passo.status = StatusPasso.CONCLUIDO
            i.revisada_em = datetime.now(timezone.utc).isoformat()
            self._persistir_estado(i)

            return {
                "status": "passo_executado",
                "passo": passo.descricao,
                "proporcao": i.proporcao_concluida(),
            }

        return {"status": "erro", "motivo": "intencao_nao_encontrada"}

    def reconsiderar(
        self,
        intencao_id: str,
        mudancas: list[str],
        intensidade: float = 0.0,
    ) -> dict[str, Any]:
        """Reconsidera intenção dado novo contexto."""
        for i in self._intencoes:
            if i.id != intencao_id:
                continue
            i.evidencia_contraria.extend(mudancas)
            i.revisada_em = datetime.now(timezone.utc).isoformat()

            if _deve_reconsiderar(i, i.estrategia, mudancas, intensidade):
                i.status = StatusIntencao.ABANDONADA
                self._persistir_estado(i)
                return {"status": "abandonada", "motivo": "evidencia_contraria_suficiente"}

            self._persistir_estado(i)
            return {"status": "mantida", "estrategia": i.estrategia.value}

        return {"status": "erro", "motivo": "intencao_nao_encontrada"}

    def abandonar(self, intencao_id: str) -> bool:
        for i in self._intencoes:
            if i.id == intencao_id:
                i.status = StatusIntencao.ABANDONADA
                i.revisada_em = datetime.now(timezone.utc).isoformat()
                self._persistir_estado(i)
                return True
        return False

    def _persistir_estado(self, intencao: Intencao) -> None:
        """Anexa o estado da intenção ao ledger (se habilitado via CDA_STATE_DIR).

        Regra 2 do handout: intenção persiste fora do runner.
        """
        try:
            from viableos.cda.provenancia import ledger
            ledger.registrar("intencao_estado", {
                "agente": self.agente_nome,
                "intencao": {
                    "id": intencao.id,
                    "agente": intencao.agente,
                    "desejo": intencao.desejo,
                    "plano": intencao.plano,
                    "status": intencao.status.value,
                    "estrategia": intencao.estrategia.value,
                    "prioridade": intencao.prioridade,
                    "adotada_em": intencao.adotada_em,
                    "revisada_em": intencao.revisada_em,
                    "evidencia_contraria": list(intencao.evidencia_contraria),
                    "passos": [
                        {
                            "descricao": p.descricao,
                            "status": p.status.value,
                            "responsavel": p.responsavel,
                            "recursos": list(p.recursos),
                            "dependencias": list(p.dependencias),
                            "resultado": p.resultado,
                        }
                        for p in intencao.passos
                    ],
                },
            }, papel="s1_executou")
        except Exception:
            pass  # o núcleo nunca quebra por falha de ledger

    def _aplicar_estado(self, dados: dict[str, Any]) -> None:
        """Replay do ledger — reconstrói intenção a partir do estado persistido."""
        from viableos.cda.provenancia import _intencao_de_dict

        intencao = _intencao_de_dict(dados)
        for i, existente in enumerate(self._intencoes):
            if existente.id == intencao.id:
                self._intencoes[i] = intencao
                return
        self._intencoes.append(intencao)

    def filtrar_opcoes(self, opcoes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filtro de admissibilidade público."""
        return _filtrar_admissiveis(opcoes, self.intencoes_ativas, self._estrategia_padrao)

    def listar(self, apenas_ativas: bool = False) -> list[dict[str, Any]]:
        fonte = self.intencoes_ativas if apenas_ativas else self._intencoes
        return [
            {
                "id": i.id,
                "agente": i.agente,
                "desejo": i.desejo,
                "plano": i.plano,
                "status": i.status.value,
                "estrategia": i.estrategia.value,
                "passos": len(i.passos),
                "passo_atual": i.passo_atual().descricao if i.passo_atual() else None,
                "proporcao_concluida": round(i.proporcao_concluida(), 2),
                "prioridade": i.prioridade,
                "adotada_em": i.adotada_em,
                "evidencia_contraria": i.evidencia_contraria,
            }
            for i in fonte
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agente": self.agente_nome,
            "estrategia_padrao": self._estrategia_padrao.value,
            "intencoes_ativas": len(self.intencoes_ativas),
            "intencoes": self.listar(),
            "total_historico": len(self._historico_intencoes),
        }


class AgendaBratman:
    """Gerencia intenções de múltiplos agentes — a agenda coletiva.

    No VSM, a agenda conecta intenções de S5-S1 em uma direção coerente.
    O S5 define o propósito; S3-S1 executam intenções consistentes.
    """

    def __init__(self):
        self._motores: dict[str, MotorIntencoes] = {}

    def obter_motor(self, agente_nome: str) -> MotorIntencoes:
        if agente_nome not in self._motores:
            self._motores[agente_nome] = MotorIntencoes(agente_nome)
        return self._motores[agente_nome]

    def adotar_intencao(
        self,
        agente: str,
        desejo: str,
        plano: str,
        passos: list[dict[str, Any]] | None = None,
        estrategia: EstrategiaCompromisso | None = None,
    ) -> Intencao | None:
        return self.obter_motor(agente).adotar(desejo, plano, passos, estrategia)

    def verificar_coerencia(self) -> list[dict[str, Any]]:
        """Verifica se intenções de diferentes agentes são coerentes entre si."""
        conflitos = []
        todas_intencoes = []
        for motor in self._motores.values():
            todas_intencoes.extend(motor.intencoes_ativas)

        for i, a in enumerate(todas_intencoes):
            recursos_a = _recursos_flat(a.passos)
            for b in todas_intencoes[i + 1:]:
                recursos_b = _recursos_flat(b.passos)
                conflitantes = recursos_a & recursos_b
                if conflitantes:
                    conflitos.append({
                        "intencao_a": a.id,
                        "agente_a": a.agente,
                        "intencao_b": b.id,
                        "agente_b": b.agente,
                        "recursos_conflitantes": list(conflitantes),
                    })
        return conflitos

    def status_geral(self) -> dict[str, Any]:
        return {
            "agentes_com_intencoes": len(self._motores),
            "total_intencoes_ativas": sum(
                len(m.intencoes_ativas) for m in self._motores.values()
            ),
            "conflitos": len(self.verificar_coerencia()),
            "motores": {
                nome: m.to_dict() for nome, m in self._motores.items()
            },
        }


agenda_bratman = AgendaBratman()
