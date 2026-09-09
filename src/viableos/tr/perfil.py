from .data.modalidades import MODALIDADES
from .data.perfis import FUNCAO_PERFIL, TEMA_LINHA


def _lista(arr):
    if len(arr) <= 1:
        return "".join(arr)
    return ", ".join(arr[:-1]) + " e " + arr[-1]


def _cap(s):
    if not s:
        return s
    return s[0].upper() + s[1:]


def compor_objeto(projeto_nome=""):
    from .data.objetos import objeto_formula, PROPOSITO_SKELETON
    return f"{objeto_formula(projeto_nome)}\n\n{PROPOSITO_SKELETON}"


def compor_perfil(modalidade="", funcoes=None, temas=None, experiencia="", enfases=None, recortes=None):
    if funcoes is None:
        funcoes = []
    if temas is None:
        temas = []
    if enfases is None:
        enfases = []
    if recortes is None:
        recortes = []
    mod = None
    for m in MODALIDADES:
        if m["nome"] == modalidade:
            mod = m
            break
    base = (mod and mod.get("perfilBase")) or "Profissional com a formação exigida pela modalidade"
    compet = [FUNCAO_PERFIL[fn]["competencia"] for fn in funcoes if fn in FUNCAO_PERFIL]
    linhas = [TEMA_LINHA[t] for t in temas if t in TEMA_LINHA]
    parts = [base]
    if compet:
        parts.append(f", com {_lista(compet)}")
    if linhas:
        parts.append(f", com atuação em {_lista(linhas)}")
    if recortes:
        parts.append(f" (com recorte em {_lista(recortes)})")
    parts.append(".")
    s = "".join(parts)
    if enfases:
        s += f" Ênfase em {_lista(enfases)}."
    if experiencia and experiencia.strip():
        s += f" Experiência desejável: {experiencia.strip()}."
    return s


def compor_atividades(funcoes=None, temas=None):
    if funcoes is None:
        funcoes = []
    if temas is None:
        temas = []
    ats = []
    for fn in funcoes:
        if fn in FUNCAO_PERFIL:
            for a in FUNCAO_PERFIL[fn].get("atividades", []):
                if a not in ats:
                    ats.append(a)
    if not ats:
        return ""
    linhas = [TEMA_LINHA[t] for t in temas if t in TEMA_LINHA]
    s = _cap("; ".join(ats))
    if linhas:
        s += f", no âmbito de {_lista(linhas)}"
    return s + "."


def sugerir_criterios(modalidade="", funcoes=None, prova_pratica=False):
    if funcoes is None:
        funcoes = []
    from .data.criterios import escolher_perfil_criterios
    perf = escolher_perfil_criterios(modalidade, funcoes)
    itens = list(perf["itens"])
    if prova_pratica and perf.get("opcional"):
        itens.insert(len(itens) - 1, perf["opcional"])
    corpo = "; ".join(f'{chr(65 + i)}) {it["c"]} (peso {it["p"]})' for i, it in enumerate(itens))
    return (
        f"A seleção observará os critérios de julgamento a seguir, com os pesos indicados: {corpo}. "
        f"A entrevista será aplicada às pessoas candidatas mais bem pontuadas nos demais critérios. "
        f"Será desclassificada a candidatura com nota inferior a 50% da pontuação total; o desempate "
        f"observará a maior idade na inscrição (SISBOLSAS)."
    )
