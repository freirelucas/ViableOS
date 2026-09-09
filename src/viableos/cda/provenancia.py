"""Proveniência da CDA — ledger append-only com hash-chain.

Implementa o esquema de proveniência organizacional com três mecanismos
(docs/audits/2026-09-03-coerencia-cda.md §2.5):
1. Papel estruturado por registro — "authority binding" (PACT, arXiv 2605.11039):
   o papel organizacional sob o qual o ato ocorreu (S1 executou / S3* replicou /
   S5 humano aprovou / controle determinístico), derivado do tipo organizacional
   — nunca de string spoofável.
2. Carimbo de constituição: todo registro carrega o hash SHA-256 da
   CONSTITUICAO_S5.md vigente no momento do ato.
3. Hash-chain append-only: cada registro referencia o hash do anterior. É o
   mínimo verificável sem infraestrutura externa; timestamp assinado
   (RFC 3161/Sigstore/SLSA) é roadmap.

Distinção mantida deliberadamente: PACT é proveniência *de segurança* (argumento
→ fonte); a CDA reivindica proveniência *organizacional de pesquisa* (ato →
papel → constituição vigente). As citações no código referenciam o primeiro
como inspiração, não como equivalência.

O ledger também é o substrato de persistência (Regra 2 do handout: "intenção
persiste fora do runner"): com CDA_STATE_DIR definido, decisões, sinais e
intenções são restaurados por replay no startup.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PapelProveniencia(str, Enum):
    """Papéis organizacionais fechados — enum deliberadamente curto."""

    S1_EXECUTOU = "s1_executou"
    S3STAR_REPLICOU = "s3star_replicou"
    S5_HUMANO_APROVOU = "s5_humano_aprovou"
    # S2-S4 operam por canais determinísticos sem LLM (auditado 2026-09-03):
    # afirmações do plano de controle são verificáveis pelo código, não por LLM.
    CONTROLE_DETERMINISTICO = "controle_deterministico"


def papel_por_tipo(tipo: str) -> PapelProveniencia:
    """Deriva o papel de proveniência do tipo organizacional do agente."""
    if tipo.startswith("s1"):
        return PapelProveniencia.S1_EXECUTOU
    if tipo == "s3_auditoria":
        return PapelProveniencia.S3STAR_REPLICOU
    if tipo == "s5_diretor":
        return PapelProveniencia.S5_HUMANO_APROVOU
    return PapelProveniencia.CONTROLE_DETERMINISTICO


_cache_constituicao: list[Any] = [None, None]


def _caminho_constituicao() -> str:
    # src/viableos/cda/provenancia.py → raiz do repo (3 níveis acima)
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "CONSTITUICAO_S5.md")
    )


def carimbo_constituicao() -> dict[str, Any]:
    """Hash SHA-256 da CONSTITUICAO_S5.md vigente (cacheado por mtime/tamanho)."""
    try:
        st = os.stat(_caminho_constituicao())
        chave = (st.st_mtime_ns, st.st_size)
        if _cache_constituicao[0] == chave:
            return _cache_constituicao[1]
        with open(_caminho_constituicao(), "rb") as f:
            conteudo = f.read()
        carimbo = {
            "hash_sha256": hashlib.sha256(conteudo).hexdigest(),
            "tamanho_bytes": len(conteudo),
            "carimbado_em": datetime.now(timezone.utc).isoformat(),
        }
        _cache_constituicao[0] = chave
        _cache_constituicao[1] = carimbo
        return carimbo
    except OSError:
        return {
            "hash_sha256": "",
            "tamanho_bytes": 0,
            "carimbado_em": datetime.now(timezone.utc).isoformat(),
        }


def _hash_registro(registro: dict[str, Any]) -> str:
    base = {k: v for k, v in registro.items() if k != "hash"}
    texto = json.dumps(base, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class LedgerProveniencia:
    """Registro append-only com hash-chain — o caderno de laboratório da CDA.

    Desabilitado por padrão (estado em memória, modo demo). Habilitado quando
    CDA_STATE_DIR aponta para um diretório persistido — todo ato de decisão,
    sinal e intenção é anexado e pode ser restaurado por replay.
    """

    GENESIS = "0" * 64

    def __init__(self, diretorio: str | None = None):
        self._dir: str | None = diretorio
        self._sequencia = 0
        self._ultimo_hash = self.GENESIS
        self.reconstruindo = False
        if diretorio:
            self.habilitar(diretorio)

    def habilitar(self, diretorio: str) -> None:
        os.makedirs(diretorio, exist_ok=True)
        self._dir = diretorio
        self._carregar_cadeia()

    def desabilitar(self) -> None:
        """Volta ao estado em-memória (demo) — usado por testes e teardown."""
        self._dir = None
        self._sequencia = 0
        self._ultimo_hash = self.GENESIS
        self.reconstruindo = False

    @property
    def habilitado(self) -> bool:
        return self._dir is not None

    @property
    def caminho(self) -> str:
        return os.path.join(self._dir or ".", "ledger_cda.jsonl")

    def _carregar_cadeia(self) -> None:
        self._sequencia = 0
        self._ultimo_hash = self.GENESIS
        if not os.path.isfile(self.caminho):
            return
        with open(self.caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                reg = json.loads(linha)
                self._sequencia = reg["sequencia"]
                self._ultimo_hash = reg["hash"]

    def registrar(
        self,
        tipo_evento: str,
        dados: dict[str, Any] | None = None,
        papel: str = "",
    ) -> dict[str, Any] | None:
        """Anexa um ato ao ledger. No-op se desabilitado ou reconstruindo."""
        if not self.habilitado or self.reconstruindo:
            return None
        registro: dict[str, Any] = {
            "sequencia": self._sequencia + 1,
            "tipo_evento": tipo_evento,
            "papel": papel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "constituicao": carimbo_constituicao(),
            "dados": dados or {},
            "hash_anterior": self._ultimo_hash,
        }
        registro["hash"] = _hash_registro(registro)
        try:
            with open(self.caminho, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            logger.warning("Ledger: falha ao anexar registro %s: %s", tipo_evento, e)
            return None
        self._sequencia += 1
        self._ultimo_hash = registro["hash"]
        return registro

    def eventos(self) -> list[dict[str, Any]]:
        if not self.habilitado or not os.path.isfile(self.caminho):
            return []
        registros = []
        with open(self.caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    registros.append(json.loads(linha))
        return registros

    def verificar_cadeia(self) -> dict[str, Any]:
        """Verifica a integridade da hash-chain (deteca alteração/remoção)."""
        registros = self.eventos()
        anterior = self.GENESIS
        quebras: list[int] = []
        for r in registros:
            if r.get("hash_anterior") != anterior or _hash_registro(r) != r.get("hash"):
                quebras.append(r.get("sequencia", -1))
            anterior = r.get("hash", anterior)
        return {"total": len(registros), "quebras": quebras, "integro": not quebras}

    # ─── Replay (Regra 2 do handout: intenção persiste fora do runner) ───

    def reconstruir(self, raiz: Any = None, agenda: Any = None) -> dict[str, int]:
        """Replay do ledger no estado em memória (startup persistido).

        raiz: NivelVSM raiz da árvore; agenda: AgendaBratman. Se omitidos,
        usa os singletons da aplicação.
        """
        if not self.habilitado:
            return {}
        if raiz is None:
            from viableos.cda.fabrica import fabrica as _fabrica
            raiz = _fabrica.raiz
        if agenda is None:
            from viableos.cda.bratman import agenda_bratman as _agenda
            agenda = _agenda
        if raiz is None:
            return {}

        niveis: dict[str, Any] = {raiz.nome: raiz}

        def _coletar(n: Any) -> None:
            for sub in n.listar_subniveis():
                niveis[sub.nome] = sub
                _coletar(sub)

        _coletar(raiz)

        contador: dict[str, int] = defaultdict(int)
        eventos = self.eventos()
        self.reconstruindo = True
        try:
            for ev in eventos:
                tipo = ev.get("tipo_evento", "")
                dados = ev.get("dados", {})
                nivel = niveis.get(dados.get("nivel", ""))
                if tipo == "decisao_estado" and nivel is not None:
                    nivel.motor._aplicar_estado(dados.get("decisao", {}))
                    contador["decisoes"] += 1
                elif tipo == "sinal_estado" and nivel is not None:
                    nivel.canal._aplicar_estado(dados.get("sinal", {}))
                    contador["sinais"] += 1
                elif tipo == "intencao_estado":
                    motor = agenda.obter_motor(dados.get("agente", ""))
                    motor._aplicar_estado(dados.get("intencao", {}))
                    contador["intencoes"] += 1
        finally:
            self.reconstruindo = False
        logger.info(
            "Ledger replay: %d eventos → %d decisões, %d sinais, %d intenções",
            len(eventos), contador["decisoes"], contador["sinais"], contador["intencoes"],
        )
        return dict(contador)


def _decisao_de_dict(d: dict[str, Any]):
    from viableos.cda.decisoes import DecisaoWorkflow, NivelAutonomia, StatusDecisao

    return DecisaoWorkflow(
        id=d["id"],
        assunto=d.get("assunto", ""),
        solicitante=d.get("solicitante", ""),
        tipo_solicitante=d.get("tipo_solicitante", ""),
        contexto=d.get("contexto", ""),
        urgencia=d.get("urgencia", "media"),
        opcoes=list(d.get("opcoes", [])),
        autonomia=NivelAutonomia(d.get("autonomia", "recomendacao")),
        status=StatusDecisao(d.get("status", "pendente")),
        justificativa=d.get("justificativa", ""),
        criado_em=d.get("criado_em", ""),
        resolvido_em=d.get("resolvido_em"),
        resolvido_por=d.get("resolvido_por"),
        resolucao=d.get("resolucao"),
        feedback=d.get("feedback"),
        papel_origem=d.get("papel_origem", ""),
        papel_aprovacao=d.get("papel_aprovacao", ""),
        resolvido_por_sub=d.get("resolvido_por_sub", ""),
        constituicao_hash=d.get("constituicao_hash", ""),
        intencao_id=d.get("intencao_id", ""),
    )


def _sinal_de_dict(d: dict[str, Any]):
    from viableos.cda.algedonic import (
        CanalAlgedonico,  # noqa: F401 — apenas para tipagem do retorno
        GravidadeSinal,
        SinalAlgedonico,
        TipoGatilho,
    )

    return SinalAlgedonico(
        id=d["id"],
        fonte=d.get("fonte", ""),
        nivel=d.get("nivel", ""),
        gravidade=GravidadeSinal(d.get("gravidade", "amarelo")),
        gatilho=TipoGatilho(d.get("gatilho", "timeout_decisao")),
        assunto=d.get("assunto", ""),
        mensagem=d.get("mensagem", ""),
        contexto=dict(d.get("contexto", {})),
        timestamp=d.get("timestamp", ""),
        respondido_em=d.get("respondido_em"),
        resolucao=d.get("resolucao"),
        propagado_para=list(d.get("propagado_para", [])),
    )


def _intencao_de_dict(d: dict[str, Any]):
    from viableos.cda.bratman import (
        EstrategiaCompromisso,
        Intencao,
        Passo,
        StatusIntencao,
        StatusPasso,
    )

    passos = [
        Passo(
            descricao=p.get("descricao", ""),
            status=StatusPasso(p.get("status", "pendente")),
            responsavel=p.get("responsavel", ""),
            recursos=list(p.get("recursos", [])),
            dependencias=list(p.get("dependencias", [])),
            resultado=p.get("resultado", ""),
        )
        for p in d.get("passos", [])
    ]
    return Intencao(
        id=d["id"],
        agente=d.get("agente", ""),
        desejo=d.get("desejo", ""),
        plano=d.get("plano", ""),
        passos=passos,
        status=StatusIntencao(d.get("status", "ativa")),
        estrategia=EstrategiaCompromisso(d.get("estrategia", "single_minded")),
        adotada_em=d.get("adotada_em", ""),
        revisada_em=d.get("revisada_em", ""),
        evidencia_contraria=list(d.get("evidencia_contraria", [])),
        prioridade=d.get("prioridade", 3),
    )


# Singleton — habilitado via CDA_STATE_DIR (persistência fora do runner).
ledger = LedgerProveniencia(os.environ.get("CDA_STATE_DIR") or None)
