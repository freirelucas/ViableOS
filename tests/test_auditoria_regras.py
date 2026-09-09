"""Testes da auditoria das 6 regras inegociáveis."""

from viableos.cda.auditoria_regras import AuditoriaSeisRegras, StatusRegra


def test_r1_llm_apenas_s1_conforme():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "S4", "tipo": "s4_inteligencia", "ferramentas": ["analise-deterministica"]},
            {"nome": "S3", "tipo": "s3_gestao", "ferramentas": ["dashboard"]},
            {"nome": "S2", "tipo": "s2_coordenacao", "ferramentas": ["cronograma"]},
            {"nome": "S3*", "tipo": "s3_auditoria", "ferramentas": ["conformidade"]},
            {"nome": "Dev", "tipo": "s1_desenvolvedor", "ferramentas": ["glm", "git"]},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r1 = [r for r in resultados if r.regra == "R1"][0]
    assert r1.status == StatusRegra.CONFORME


def test_r1_viola_s4_com_llm():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "S4", "tipo": "s4_inteligencia", "ferramentas": ["glm-analise"]},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r1 = [r for r in resultados if r.regra == "R1"][0]
    assert r1.status == StatusRegra.VIOLADO


def test_r1_viola_s3_com_glm():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "S3", "tipo": "s3_gestao", "ferramentas": ["glm-analise"]},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r1 = [r for r in resultados if r.regra == "R1"][0]
    assert r1.status == StatusRegra.VIOLADO


def test_r2_envelope_reversivel():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "Dev", "tipo": "s1_desenvolvedor", "ferramentas": ["python", "git"]},
            {"nome": "Gestor", "tipo": "s1_executor", "ferramentas": ["tr-generator"]},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r2 = [r for r in resultados if r.regra == "R2"][0]
    assert r2.status == StatusRegra.VIOLADO
    assert "Gestor" in r2.detalhes


def test_r5_s5_humano_conforme():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "S4", "tipo": "s4_inteligencia", "ferramentas": []},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r5 = [r for r in resultados if r.regra == "R5"][0]
    assert r5.status == StatusRegra.CONFORME


def test_r5_s5_agente_viola():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [
            {"nome": "Agente S5", "tipo": "s5_diretor", "ferramentas": []},
        ],
        "sinais": [],
        "decisoes_historico": [],
    }
    resultados = auditoria.auditar(estado)
    r5 = [r for r in resultados if r.regra == "R5"][0]
    assert r5.status == StatusRegra.VIOLADO


def test_r6_cascata_rastreavel():
    auditoria = AuditoriaSeisRegras()
    estado = {
        "agentes": [],
        "sinais": [],
        "decisoes_historico": [
            {"id": "1", "contexto": "ctx", "opcoes": ["a", "b"]},
            {"id": "2", "contexto": "", "opcoes": []},
        ],
    }
    resultados = auditoria.auditar(estado)
    r6 = [r for r in resultados if r.regra == "R6"][0]
    assert r6.status == StatusRegra.VIOLADO


def test_historico_auditoria():
    auditoria = AuditoriaSeisRegras()
    estado = {"agentes": [], "sinais": [], "decisoes_historico": []}
    auditoria.auditar(estado)
    hist = auditoria.historico()
    assert len(hist) == 6
    assert all("regra" in h for h in hist)
