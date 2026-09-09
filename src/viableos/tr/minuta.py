from .data.modalidades import MODALIDADES
from .data.norma import NORMA
from .format import fmt_valor, extenso, fmt_data


def _ou(v, fallback):
    return str(v).strip() if v and str(v).strip() else fallback


def _pad(n):
    return str(int(n)).zfill(2)


def _mod_of(nome):
    for m in MODALIDADES:
        if m["nome"] == nome:
            return m
    return {"nome": nome or "[MODALIDADE]", "valor": 0, "moeda": "BRL", "requisito": ""}


def _cotas_de(v):
    return {"er": int(v.get("cotaER", 0) or 0), "m": int(v.get("cotaM", 0) or 0), "pcd": int(v.get("cotaPCD", 0) or 0)}


def _tem_cota(v):
    c = _cotas_de(v)
    return c["er"] + c["m"] + c["pcd"] > 0


def vagas_de(f):
    if isinstance(f.get("vagas"), list) and len(f["vagas"]) > 0:
        return f["vagas"]
    return [{
        "modalidade": f.get("modalidade", ""),
        "qtd": f.get("qtd", "1"),
        "tipo": "Imediata + cadastro reserva" if f.get("cadastroReserva") else "Imediata",
        "cotaER": f.get("cotaER", 0) if f.get("cotasOn") else 0,
        "cotaM": f.get("cotaM", 0) if f.get("cotasOn") else 0,
        "cotaPCD": f.get("cotaPCD", 0) if f.get("cotasOn") else 0,
        "duracaoBolsa": f.get("duracaoBolsa", "12"),
        "duracaoPesquisa": f.get("duracaoPesquisa", "12"),
        "perfil": f.get("perfil", ""),
        "atividades": f.get("atividades", ""),
        "criterios": f.get("criterios", ""),
    }]


def _dur_b(v, f):
    return int(v.get("duracaoBolsa", 0) or 0) or int(f.get("duracaoBolsa", 0) or 0) or 12


def _dur_p(v, f):
    return (int(v.get("duracaoPesquisa", 0) or 0) or int(v.get("duracaoBolsa", 0) or 0)
            or int(f.get("duracaoPesquisa", 0) or 0) or int(f.get("duracaoBolsa", 0) or 0) or 12)


def _duracao_sec(vs, f):
    ub = list(set(_dur_b(v, f) for v in vs))
    up = list(set(_dur_p(v, f) for v in vs))
    if len(ub) == 1 and len(up) == 1:
        b = ub[0]
        pp = up[0]
        return [
            f"Duração da bolsa: {_pad(b)} ({extenso(b)}) {'mês' if b == 1 else 'meses'}.",
            f"Tempo de duração da pesquisa: {_pad(pp)} ({extenso(pp)}) {'mês' if pp == 1 else 'meses'}.",
        ]
    return [f"Seleção {i + 1}: bolsa de {_pad(_dur_b(v, f))} {'mês' if _dur_b(v, f) == 1 else 'meses'}; pesquisa de {_pad(_dur_p(v, f))} {'mês' if _dur_p(v, f) == 1 else 'meses'}."
            for i, v in enumerate(vs)]


def _caracteristicas_bolsa(v, f):
    mod = _mod_of(v.get("modalidade", ""))
    q = int(v.get("qtd", 1) or 1)
    db = _dur_b(v, f)
    cadastro = "cadastro reserva" in (v.get("tipo", "") or "").lower() or f.get("cadastroReserva", False)
    b = [
        f"Modalidade: {mod['nome']} — {fmt_valor(mod['valor'], mod['moeda'])} mensais (Anexo I da {NORMA['portaria']}).",
        f"Requisito da modalidade: {_ou(mod.get('requisito', ''), 'conforme Art. 4º da norma vigente.')}",
        f"Quantitativo: {_pad(q)} ({extenso(q)}) bolsa(s), com duração prevista de {_pad(db)} ({extenso(db)}) {'mês' if db == 1 else 'meses'}, renovável a critério do IPEA.",
        "Haverá cadastro reserva, observada a ordem de classificação, admitido provimento adicional na vigência da chamada (Art. 9º, §2º)." if cadastro else "Não haverá cadastro reserva.",
    ]
    if _ou(f.get("reservaVagas", ""), ""):
        b.append(f'Público-alvo / reserva de vagas (Art. 25): {f["reservaVagas"].strip()}')
    if _tem_cota(v):
        c = _cotas_de(v)
        ac = max(q - c["er"] - c["m"] - c["pcd"], 0)
        b.append(f'Reserva de vagas (cotas): das {_pad(q)} vaga(s), {_pad(ac)} de ampla concorrência e {_pad(c["er"] + c["m"] + c["pcd"])} reservada(s), conforme o quadro abaixo e {_ou(f.get("fundamentoCotas", ""), "a legislação aplicável e o disposto na chamada")}.')
        if f.get("heteroident"):
            b.append("A autodeclaração étnico-racial será confirmada por procedimento de heteroidentificação, na forma da chamada.")
    return b


def _quadro_vagas(v):
    q = int(v.get("qtd", 1) or 1)
    c = _cotas_de(v)
    ac = max(q - c["er"] - c["m"] - c["pcd"], 0)
    rows = [["Categoria", "Vagas"], ["Ampla concorrência (AC)", _pad(ac)]]
    if c["er"]:
        rows.append(["Étnico-racial (ER)", _pad(c["er"])])
    if c["m"]:
        rows.append(["Mulheres (M)", _pad(c["m"])])
    if c["pcd"]:
        rows.append(["Pessoa com deficiência (PCD)", _pad(c["pcd"])])
    rows.append(["Total", _pad(q)])
    return rows


def _quadro_multivagas(vs):
    rows = [["Seleção", "Modalidade", "Valor mensal", "Vagas", "Reserva"]]
    tot = 0
    for i, v in enumerate(vs):
        m = _mod_of(v.get("modalidade", ""))
        q = int(v.get("qtd", 1) or 1)
        tot += q
        c = _cotas_de(v)
        partes_res = []
        if c["er"]:
            partes_res.append(f"ER {_pad(c['er'])}")
        if c["m"]:
            partes_res.append(f"M {_pad(c['m'])}")
        if c["pcd"]:
            partes_res.append(f"PCD {_pad(c['pcd'])}")
        res_str = ", ".join(partes_res) if partes_res else "—"
        tipo = v.get("tipo", "")
        sel_label = f"Seleção {i + 1}" + (f" — {tipo}" if tipo else "")
        rows.append([sel_label, m["nome"], fmt_valor(m["valor"], m["moeda"]), _pad(q), res_str])
    rows.append(["Total", "", "", _pad(tot), ""])
    return rows


def _caracteristicas_multivagas(vs, f):
    tot = sum(int(v.get("qtd", 1) or 1) for v in vs)
    b = [
        f"Esta chamada compreende {_pad(len(vs))} ({extenso(len(vs))}) seleção(ões), totalizando {_pad(tot)} ({extenso(tot)}) bolsa(s), conforme o quadro a seguir. Cada seleção possui modalidade, valor e requisitos próprios (Art. 4º e Anexo I da {NORMA['portaria']}).",
    ]
    if _ou(f.get("reservaVagas", ""), ""):
        b.append(f'Público-alvo / reserva de vagas (Art. 25): {f["reservaVagas"].strip()}')
    if any(_tem_cota(v) for v in vs):
        b.append(f'As vagas reservadas (cotas) observam, em cada seleção, a ordem de classificação e {_ou(f.get("fundamentoCotas", ""), "a legislação aplicável")}, conforme detalhado na chamada.')
    return b


def _perfil_multivagas(vs):
    return [f"Seleção {i + 1} — {_mod_of(v.get('modalidade', ''))['nome']}: {_ou(_mod_of(v.get('modalidade', ''))['requisito'], 'requisitos conforme Art. 4º da norma vigente.')}{' ' + v['perfil'].strip() if v.get('perfil', '').strip() else ''}"
            for i, v in enumerate(vs)]


def _atividades_multivagas(vs):
    return [f'Seleção {i + 1} — {_mod_of(v.get("modalidade", ""))["nome"]}: {_ou(v.get("atividades", ""), "[descrever as atividades de pesquisa desta seleção].")}'
            for i, v in enumerate(vs)]


def _criterios_default(f):
    if f.get("cartaIntencoes"):
        return ("A seleção considerará a carta de intenções (trajetória profissional, competências aplicáveis ao objeto e motivações) "
                "e a análise curricular, conforme modelo divulgado na chamada (Art. 8º, §1º).")
    return ("A seleção será baseada em análise curricular e critérios complementares — ensaios, propostas de projeto ou de atividades, "
            "entrevistas, entre outros — definidos na chamada (Art. 8º, §2º).")


def _criterios_multivagas(vs, f):
    return [f'Seleção {i + 1} — {_mod_of(v.get("modalidade", ""))["nome"]}: {_ou(v.get("criterios", ""), _criterios_default(f))}'
            for i, v in enumerate(vs)]


def _comissao_texto(f):
    return _ou(
        f.get("comissao", ""),
        f'Comissão julgadora composta por, no mínimo, {NORMA["comissaoMinIntegrantes"]} (três) integrantes e um suplente, '
        'indicados pelo coordenador do projeto (Art. 9º). Vedada a participação de cônjuge/parente até 3º grau, '
        'orientador dos últimos cinco anos ou amigo íntimo/inimigo do avaliado.'
    )


def _cronograma(f):
    return [
        ["Etapa", "Data"],
        ["Publicação da chamada", fmt_data(f.get("dataPub", ""))],
        [f'Inscrições (mín. {NORMA["prazoMinEspecializadaDias"]} dias)', f'{fmt_data(f.get("inscIni", ""))} a {fmt_data(f.get("inscFim", ""))}'],
        ["Divulgação do resultado", f'a partir de {fmt_data(f.get("resultado", ""))}'],
        ["Início das atividades", f'a partir de {fmt_data(f.get("inicio", ""))}'],
    ]


def _sec_modalidade(vs, f, t1, tn):
    if len(vs) > 1:
        return {"t": tn, "b": _caracteristicas_multivagas(vs, f), "table": _quadro_multivagas(vs)}
    result = {"t": t1, "b": _caracteristicas_bolsa(vs[0], f)}
    if _tem_cota(vs[0]):
        result["table"] = _quadro_vagas(vs[0])
    return result


def build_tr(f):
    vs = vagas_de(f)
    multi = len(vs) > 1
    S = []
    S.append({"t": f'TERMO DE REFERÊNCIA — CHAMADA PÚBLICA ESPECIALIZADA IPEA/PIPA Nº {_ou(f.get("numero", ""), "XXX/AAAA")}', "head": True})
    S.append({"p": f'Termo de referência para seleção de bolsista no âmbito do {NORMA["programa"]}, nos termos do Art. 7º da {NORMA["portaria"]}.'})
    S.append({"n": 1, "t": "UNIDADE RESPONSÁVEL E COORDENAÇÃO", "b": [
        f'Unidade responsável: {_ou(f.get("unidade", ""), "[DIRETORIA/UNIDADE RESPONSÁVEL]")}.',
        f'Coordenação do projeto: {_ou(f.get("coordenador", ""), "[NOME DO(S) COORDENADOR(ES)]")}.',
    ]})
    S.append({"n": 2, "t": "DEFINIÇÃO DO PROJETO DE PESQUISA", "b": [
        _ou(f.get("projeto", ""), "[Descrever o projeto de pesquisa: objeto, justificativa, objetivos e resultados esperados.]"),
    ]})
    S.append({"n": 3, "t": "PERFIL DO BOLSISTA DESEJADO", "b": (
        _perfil_multivagas(vs) if multi
        else [_ou(vs[0].get("perfil", ""), "[Descrever titulação, conhecimentos, competências e experiência desejados.]")]
    )})
    S.append({"n": 4, **_sec_modalidade(vs, f, "MODALIDADE, VALOR E QUANTITATIVO DA BOLSA", "MODALIDADES, VALORES E QUADRO DE VAGAS")})
    S.append({"n": 5, "t": "DURAÇÃO DA BOLSA E DA PESQUISA", "b": _duracao_sec(vs, f)})
    S.append({"n": 6, "t": "ATIVIDADES A SEREM DESENVOLVIDAS", "b": (
        _atividades_multivagas(vs) if multi
        else [_ou(vs[0].get("atividades", ""), "[Descrever as atividades de pesquisa que o bolsista irá desenvolver.]")]
    )})
    S.append({"n": 7, "t": "CRITÉRIOS DE SELEÇÃO", "b": _criterios_multivagas(vs, f) if multi else [_ou(vs[0].get("criterios", ""), _criterios_default(f))]})
    S.append({"n": 8, "t": "COMISSÃO JULGADORA", "b": [_comissao_texto(f)]})
    S.append({"n": 9, "t": "INSCRIÇÕES, RESULTADO E RECURSOS", "b": [
        f'As inscrições serão realizadas pelo SISBOLSAS ({NORMA["sisbolsas"]}), pelo prazo mínimo de {NORMA["prazoMinEspecializadaDias"]} (dez) dias (Art. 8º, §4º).',
        "O resultado será divulgado no sítio do IPEA e seu extrato publicado no Diário Oficial da União (Art. 10).",
        "Caberá recurso fundamentado, na forma da chamada, com juízo de retratação pela comissão julgadora e deliberação final da DIDES (Art. 9º, §§3º e 4º).",
    ], "table": _cronograma(f)})
    S.append({"n": 10, "t": "DISPOSIÇÕES FINAIS", "b": [
        NORMA["vinculo"],
        f'Aplicam-se subsidiariamente as disposições da {NORMA["portaria"]} e demais normas pertinentes; os casos omissos serão resolvidos pela {NORMA["diretoria"]}.',
    ]})
    S.append({"sign": True, "b": [
        f'Brasília, {fmt_data(f.get("dataPub", ""))}.',
        f'{_ou(f.get("coordenador", ""), "[COORDENADOR(A) DO PROJETO]")} — Coordenação do projeto',
        f'De acordo. {_ou(f.get("diretoria", ""), "[DIRETOR(A) DA ÁREA]")} (Art. 7º, parágrafo único).',
    ]})
    return S


def build_edital(f):
    vs = vagas_de(f)
    multi = len(vs) > 1
    S = []
    S.append({"t": f'CHAMADA PÚBLICA ESPECIALIZADA IPEA/PIPA Nº {_ou(f.get("numero", ""), "XXX/AAAA")}', "head": True})
    S.append({"p": f'O {NORMA["instituto"]}, CONVIDA interessados(as) a se candidatarem à concessão de bolsa de pesquisa no âmbito do {NORMA["programa"]}, nos termos da {NORMA["portaria"]} e do Termo de Referência (Anexo I).'})
    S.append({"n": 1, "t": "DO OBJETO", "b": [
        f'Seleção de bolsista para o projeto de pesquisa: {_ou(f.get("projeto", ""), "[TÍTULO/OBJETO DO PROJETO]")}, conforme o Termo de Referência constante do Anexo I.',
    ]})
    S.append({"n": 2, **_sec_modalidade(vs, f, "DA MODALIDADE, DO VALOR E DO QUANTITATIVO", "DAS MODALIDADES, DOS VALORES E DO QUADRO DE VAGAS")})
    S.append({"n": 3, "t": "DOS REQUISITOS E DO PERFIL", "b": (
        _perfil_multivagas(vs) if multi else [
            f'Requisito da modalidade: {_ou(_mod_of(vs[0].get("modalidade", "")).get("requisito", ""), "conforme Art. 4º da norma vigente.")}',
            f'Perfil desejado: {_ou(vs[0].get("perfil", ""), "[Descrever o perfil exigido.]")}',
        ]
    )})
    S.append({"n": 4, "t": "DAS INSCRIÇÕES", "b": [
        f'As candidaturas serão realizadas exclusivamente pelo SISBOLSAS ({NORMA["sisbolsas"]}), no período do cronograma, observado o prazo mínimo de {NORMA["prazoMinEspecializadaDias"]} (dez) dias.',
    ], "table": _cronograma(f)})
    S.append({"n": 5, "t": "DOS CRITÉRIOS DE SELEÇÃO", "b": _criterios_multivagas(vs, f) if multi else [_ou(vs[0].get("criterios", ""), _criterios_default(f))]})
    S.append({"n": 6, "t": "DA COMISSÃO JULGADORA", "b": [_comissao_texto(f)]})
    S.append({"n": 7, "t": "DO RESULTADO E DOS RECURSOS", "b": [
        "O resultado será divulgado no sítio do IPEA e seu extrato publicado no Diário Oficial da União (Art. 10).",
        "Caberá recurso fundamentado, com juízo de retratação pela comissão julgadora e deliberação final da DIDES (Art. 9º).",
    ]})
    S.append({"n": 8, "t": "DAS DISPOSIÇÕES FINAIS", "b": [
        NORMA["vinculo"],
        f'Os casos omissos serão resolvidos pela {NORMA["diretoria"]}, observada a {NORMA["portaria"]}.',
    ]})
    S.append({"sign": True, "b": [
        f'Brasília, {fmt_data(f.get("dataPub", ""))}.',
        f'{_ou(f.get("diretoria", ""), "[DIRETORIA RESPONSÁVEL]")}',
        "Instituto de Pesquisa Econômica Aplicada — IPEA",
    ]})
    return S


def minuta_to_text(S):
    out = []
    for s in S:
        if s.get("head"):
            out.append(s["t"].upper())
            out.append("")
            continue
        if s.get("p"):
            out.append(s["p"])
            out.append("")
            continue
        if s.get("sign"):
            out.append("")
            for l in s["b"]:
                out.append(l)
            continue
        if s.get("n"):
            out.append(f'{s["n"]}. {s["t"]}')
            for l in s.get("b", []):
                out.append(l)
        if s.get("table"):
            for r in s["table"]:
                out.append("  |  ".join(r))
        if s.get("n") or s.get("table"):
            out.append("")
    return "\n".join(out)
