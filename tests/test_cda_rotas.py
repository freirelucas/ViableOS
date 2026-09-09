"""Testes de rota da CDA — os endpoints HTTP reais, via TestClient.

Gap registrado na docs/audits/2026-09-03-coerencia-cda.md §2.6: o endpoint
quebrado GET /agentes/{nome} existia sem nenhum teste de rota pegá-lo.
Aqui cada imposição constitucional é exercida pela fronteira HTTP:
R5 (auth no resolver), R6 (cascata na entrada), R4 (gatilho validado).

Sem context manager: startup não roda (padrão do repo — testa-se a API,
não o evento de seed).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from viableos.api.auth import create_token
from viableos.api.main import app
from viableos.cda.fabrica import fabrica

client = TestClient(app)

Nome_S4 = "Inteligência Estratégica (S4)"


def _token(scopes: list[str]) -> str:
    return create_token("diretora@ipea", scopes=scopes)


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def _criar_decisao(assunto: str) -> str:
    resp = client.post(
        f"/api/cda/agentes/{Nome_S4}/decisao",
        json={
            "assunto": assunto,
            "contexto": "Contexto de teste via API",
            "opcoes": ["Opção A", "Opção B"],
            "urgencia": "media",
            "justificativa": "Teste de rota exige cascata completa (R6).",
        },
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["status"] == "ok", corpo
    return corpo["decisao_id"]


# ─── Leitura da árvore ──────────────────────────────────────────────


def test_agentes_da_arvore_presentes():
    resp = client.get("/api/cda/agentes")
    assert resp.status_code == 200
    nomes = [a["nome"] for a in resp.json()]
    assert Nome_S4 in nomes
    assert len(nomes) >= 7


def test_agente_detalhe_endpoint_antes_quebrado():
    """Regressão do bug: iterava agentes como se fossem decisões e
    explodia em AttributeError. Agora expõe decisões pendentes do nível."""
    resp = client.get(f"/api/cda/agentes/{Nome_S4}")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["nome"] == Nome_S4
    assert "decisoes_pendentes" in corpo
    for d in corpo["decisoes_pendentes"]:
        assert set(d) >= {"id", "assunto", "contexto", "opcoes"}


def test_arvore_e_status():
    resp = client.get("/api/cda/tree")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "CDA"
    resp = client.get("/api/cda/status")
    assert resp.status_code == 200
    assert resp.json()["total_agentes"] >= 7


# ─── R6 imposta na entrada (via API) ────────────────────────────────


def test_solicitar_sem_justificativa_rejeitado():
    resp = client.post(
        f"/api/cda/agentes/{Nome_S4}/decisao",
        json={"assunto": "Sem cascata", "contexto": "ctx", "opcoes": ["a"]},
    )
    corpo = resp.json()
    assert corpo["status"] == "erro"
    assert "R6" in corpo["motivo"]


def test_solicitar_com_cascata_e_pendentes_visiveis():
    decisao_id = _criar_decisao("Solicitar com cascata completa")
    pendentes = client.get("/api/cda/decisoes").json()
    alvo = [d for d in pendentes if d["id"] == decisao_id][0]
    assert alvo["solicitante"] == Nome_S4
    assert alvo["justificativa"]
    assert alvo["papel_origem"] == "controle_deterministico"


# ─── R5 imposta nos vereditos ───────────────────────────────────────


def test_resolver_sem_token_e_401():
    decisao_id = _criar_decisao("Resolver sem token")
    resp = client.post(
        f"/api/cda/decisoes/{decisao_id}/resolver", json={"resolucao": "Opção A"},
    )
    assert resp.status_code == 401
    assert "R5" in resp.json()["detail"]


def test_resolver_com_escopo_insuficiente_e_403():
    decisao_id = _criar_decisao("Resolver com escopo errado")
    resp = client.post(
        f"/api/cda/decisoes/{decisao_id}/resolver",
        json={"resolucao": "Opção A"},
        headers=_auth(_token(["tr:write"])),
    )
    assert resp.status_code == 403


def test_resolver_com_token_admin_ok_e_identidade_do_jwt():
    decisao_id = _criar_decisao("Resolver com token válido")
    resp = client.post(
        f"/api/cda/decisoes/{decisao_id}/resolver",
        json={"resolucao": "Opção A", "resolvido_por": "Impostor Malicioso"},
        headers=_auth(_token(["admin"])),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # identidade REGISTRADA vem do JWT — o payload "resolvido_por" é ignorado
    historico = client.get("/api/cda/decisoes/historico").json()
    alvo = [d for d in historico if d["id"] == decisao_id][0]
    assert alvo["resolvido_por"] == "diretora@ipea"
    assert alvo["resolvido_por"] != "Impostor Malicioso"
    assert alvo["papel_aprovacao"] == "s5_humano_aprovou"


def test_rejeitar_e_delegar_exigem_token():
    decisao_id = _criar_decisao("Rejeitar e delegar exigem token")
    resp = client.post(
        f"/api/cda/decisoes/{decisao_id}/rejeitar", json={"feedback": "não"},
    )
    assert resp.status_code == 401
    resp = client.post(f"/api/cda/decisoes/{decisao_id}/delegar")
    assert resp.status_code == 401


def test_responder_sinal_exige_token():
    resp = client.post("/api/cda/sinais/zzz/responder", json={"resolucao": "x"})
    assert resp.status_code == 401


# ─── R4 imposta na entrada de sinais ────────────────────────────────


def test_sinal_com_gatilho_fora_da_tabela_rejeitado():
    resp = client.post(
        "/api/cda/sinais",
        json={
            "fonte": Nome_S4,
            "gravidade": "amarelo",
            "assunto": "Teste",
            "mensagem": "mensagem",
            "gatilho": "inventado_do_nada",
        },
    )
    corpo = resp.json()
    assert corpo["status"] == "erro"
    assert "R4" in corpo["motivo"]


def test_sinal_com_gatilho_valido_fica_visivel_com_gatilho():
    resp = client.post(
        "/api/cda/sinais",
        json={
            "fonte": Nome_S4,
            "gravidade": "amarelo",
            "assunto": "Sinal válido de teste",
            "mensagem": "mensagem",
            "gatilho": "conflito_agentes",
        },
    )
    assert resp.json()["status"] == "ok"
    sinais = client.get("/api/cda/sinais").json()
    alvo = [s for s in sinais if s["assunto"] == "Sinal válido de teste"][0]
    assert alvo["gatilho"] == "conflito_agentes"


# ─── Health e auditoria com dados reais ─────────────────────────────


def test_health_boot_checks_reais():
    resp = client.get("/api/cda/health/boot")
    assert resp.status_code == 200
    corpo = resp.json()
    itens = corpo["itens"]
    assert len(itens) >= 6, "boot deve rodar os checks — vazio = bug do config"

    por_nome = " ".join(str(i.get("nome", "")) for i in itens)
    # R1-R5 são checks de config estática; R6 é regra de runtime (decisões)
    for regra in ("R1", "R2", "R3", "R4", "R5"):
        assert regra in por_nome, f"check {regra} ausente do boot"
    # R2 conforme com os dados reais da fábrica: todos os S1 têm git
    r2 = [i for i in itens if "R2" in str(i.get("nome", ""))][0]
    assert r2["passou"] is True
    assert "Todos os agentes S1 possuem git" in r2["detalhes"]


def test_auditoria_regras_retorna_seis():
    resp = client.get("/api/cda/auditoria/regras")
    assert resp.status_code == 200
    regras = resp.json()
    assert [r["regra"] for r in regras] == ["R1", "R2", "R3", "R4", "R5", "R6"]


def test_discordancia_como_dado():
    resp = client.get("/api/cda/auditoria/discordancia")
    assert resp.status_code == 200
    corpo = resp.json()
    assert {"total_analisadas", "discordantes", "taxa", "nota"} <= set(corpo)
    assert corpo["total_analisadas"] >= 1  # há decisão aprovada nos testes acima


def test_constituicao_visivel():
    resp = client.get("/api/cda/constituicao")
    assert resp.status_code == 200
    assert "R4" in resp.json()["conteudo"]


# ─── Login (aquisição de token para testar no ar) ───────────────────


def test_login_com_users_file(tmp_path, monkeypatch):
    import bcrypt

    from viableos.api import auth as auth_mod

    hash_senha = bcrypt.hashpw(b"senha-do-teste", bcrypt.gensalt()).decode()
    users_file = tmp_path / "users_teste.json"
    users_file.write_text(
        f'{{"diretora": {{"password_hash": "{hash_senha}", "scopes": ["admin"]}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(auth_mod, "USERS_PATH", str(users_file))

    resp = client.post("/api/auth/login", json={"username": "diretora", "password": "senha-do-teste"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.json() == {"authenticated": True, "username": "diretora", "scopes": ["admin"]}

    resp = client.post("/api/auth/login", json={"username": "diretora", "password": "errada"})
    assert resp.status_code == 401
