from datetime import datetime
from .data.norma import NORMA
from .data.modalidades import MODALIDADES


def diff_dias(a, b):
    if not a or not b:
        return None
    try:
        da = datetime.fromisoformat(a)
        db = datetime.fromisoformat(b)
        return (db - da).days
    except ValueError:
        return None


def _vagas_de(f):
    if isinstance(f.get("vagas"), list) and len(f["vagas"]) > 0:
        return f["vagas"]
    return [{"modalidade": f.get("modalidade", ""), "qtd": f.get("qtd", "1"),
             "perfil": f.get("perfil", ""), "atividades": f.get("atividades", ""),
             "criterios": f.get("criterios", ""),
             "cotaER": f.get("cotaER", 0) if f.get("cotasOn") else 0,
             "cotaM": f.get("cotaM", 0) if f.get("cotasOn") else 0,
             "cotaPCD": f.get("cotaPCD", 0) if f.get("cotasOn") else 0}]


def _tem(v):
    return bool(v and str(v).strip())


def conformidade(f):
    out = []
    add = lambda sev, label, detail: out.append({"sev": sev, "label": label, "detail": detail})
    vs = _vagas_de(f)
    multi = len(vs) > 1

    add("ok" if _tem(f.get("numero")) else "warn", "Número da chamada",
        f.get("numero", "defina o nº (ex.: 020/2026)") if _tem(f.get("numero")) else "defina o nº (ex.: 020/2026)")

    assina = _tem(f.get("unidade")) and _tem(f.get("coordenador")) and _tem(f.get("diretoria"))
    add("ok" if assina else "warn", "Unidade, coordenação e diretoria",
        "completos para assinatura" if assina else "necessários (Art. 7º, parágrafo único)")

    add("ok" if _tem(f.get("projeto")) else "err", "Definição do projeto",
        "preenchida" if _tem(f.get("projeto")) else "obrigatória (Art. 7º, II)")

    com_perfil = sum(1 for v in vs if _tem(v.get("perfil")))
    add("ok" if com_perfil == len(vs) else "warn", "Perfil do bolsista",
        "preenchido" if com_perfil == len(vs) else f"{com_perfil}/{len(vs)} vaga(s) — recomendado (Art. 7º, III)")

    nomes_mod = {m["nome"] for m in MODALIDADES}
    sem_mod = sum(1 for v in vs if v.get("modalidade") not in nomes_mod)
    add("ok" if sem_mod == 0 else "warn", "Modalidade e valor",
        f"{len(vs)} vaga(s) — Anexo I" if sem_mod == 0 else f"{sem_mod} vaga(s) sem modalidade do Anexo I")

    din = diff_dias(f.get("inscIni"), f.get("inscFim"))
    if din is None:
        add("warn", "Prazo de inscrição ≥ 10 dias", "defina início e fim das inscrições")
    else:
        min_dias = NORMA["prazoMinEspecializadaDias"]
        add("ok" if din >= min_dias else "err", "Prazo de inscrição ≥ 10 dias",
            f"{din} dia(s) — mínimo {min_dias} (Art. 8º, §4º)")

    for nome, a, b in [["publicação → inscrição", f.get("dataPub"), f.get("inscIni")],
                        ["inscrição → resultado", f.get("inscFim"), f.get("resultado")],
                        ["resultado → início", f.get("resultado"), f.get("inicio")]]:
        dd = diff_dias(a, b)
        if dd is not None:
            add("ok" if dd >= 0 else "err", f"Ordem: {nome}",
                "datas coerentes" if dd >= 0 else "data fora de ordem")

    tot = sum(int(v.get("qtd", 1) or 1) for v in vs)
    if multi:
        add("ok", "Seleções (multivagas)", f"{len(vs)} seleção(ões), {tot} bolsa(s) no total")
    for i, v in enumerate(vs):
        q = int(v.get("qtd", 1) or 1)
        res = int(v.get("cotaER", 0) or 0) + int(v.get("cotaM", 0) or 0) + int(v.get("cotaPCD", 0) or 0)
        rotulo = f"Seleção {i + 1}: " if multi else ""
        if res > q:
            add("err", f"{rotulo}Reserva ≤ vagas", f"{res} reservada(s) de {q}")

    add("ok", "Comissão julgadora",
        f"mín. {NORMA['comissaoMinIntegrantes']} integrantes + 1 suplente (Art. 9º)")

    for i, v in enumerate(vs):
        cd_mod = "Ciência de Dados" in v.get("modalidade", "")
        funcoes = v.get("funcoes", f.get("funcoes", []))
        cd_func = any("Ciência de Dados" in fn for fn in funcoes)
        if cd_mod and not cd_func:
            rotulo = f"Seleção {i + 1}: " if multi else ""
            add("info", f"{rotulo}Coerência modalidade × função (corpus)",
                "modalidade de Ciência de Dados sem função de Ciência de Dados — nas chamadas PIPA, 9/9 casam")

    if tot > 3:
        add("info", "Quantitativo usual (corpus)",
            f"{tot} vagas — no corpus PIPA o usual é 1 bolsa (máximo observado: 3)")

    if din is not None and din >= NORMA["prazoMinEspecializadaDias"] and din > 21:
        add("info", "Janela de inscrição usual (corpus)",
            f"{din} dias — mediana PIPA 13 (faixa típica 11–14 dias)")

    return out


def resumo_conf(lista):
    return {
        "err": sum(1 for x in lista if x["sev"] == "err"),
        "warn": sum(1 for x in lista if x["sev"] == "warn"),
        "ok": sum(1 for x in lista if x["sev"] == "ok"),
    }
