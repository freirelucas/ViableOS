import locale


def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_valor(valor, moeda):
    if moeda == "NONE":
        return "sem bolsa (serviço voluntário)"
    if moeda == "USD":
        v = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"US$ {v}"
    return brl(valor)


_UN_EXT = ["zero", "uma", "duas", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze"]


def extenso(n):
    if isinstance(n, str):
        n = int(n)
    return _UN_EXT[n] if 0 <= n < len(_UN_EXT) else str(n)


_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def fmt_data(iso):
    if not iso:
        return "____ de __________ de ____"
    parts = iso.split("-")
    if len(parts) != 3:
        return iso
    y, m, d = parts
    return f"{int(d)} de {_MESES[int(m) - 1]} de {y}"
