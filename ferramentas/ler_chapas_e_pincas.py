# -*- coding: utf-8 -*-
r"""
Le a lista de chapas e pincas das graficas. NAO ESCREVE NADA.

O arquivo de origem e o 'CHAPAS E PINCAS.TXT' que o operador mantem a
mao ha anos: cada grafica atendida, o formato da chapa dela e quantos
centimetros de pinca aquela maquina pede.

ATENCAO - E POR ISSO QUE ESTE PROGRAMA SO LE E SO OLHA CHAPA:

O arquivo tambem guarda SENHA de Teams, e-mail, FTP, webmail, Skype e
wi-fi, no meio do texto. Nada disso e lido, nada e copiado, e a pasta
onde ele mora esta no .gitignore. Se um dia este script for mudado para
extrair 'tudo', ele passa a vazar credencial - entao ele extrai
exatamente dois padroes, e mais nada:

    <numero> x <numero>        a chapa, em milimetros
    pinca <numero> cm|mm       a pinca

Linha que nao case com isso e ignorada sem ser olhada.

O que sai: uma tabela grafica -> [(chapa, pinca_mm)], para conferir
contra o que a FIA ja tem no config.py e para servir de consulta na
montagem.
"""

import collections
import io
import os
import re
import sys

ORIGEM = os.path.join("ARQUIVOS TEMP PARA TESTES", "CHAPAS E PINCAS.TXT")

# uma medida de chapa: '510x400', '745 X 605', '660 x 605'
CHAPA = re.compile(r"\b(\d{2,4})\s*[xX]\s*(\d{2,4})\b")

# a pinca: 'PINCA 3 CM', 'pinça: 4,5cm', 'Pinca 6 cm', '3,3 CM DE PINCA'
PINCA = re.compile(
    r"(?:pin[cç]a\D{0,12}?(\d{1,3}(?:[.,]\d+)?)\s*(cm|mm)?"
    r"|(\d{1,3}(?:[.,]\d+)?)\s*(cm|mm)\s*(?:de\s+)?pin[cç]a)",
    re.IGNORECASE)

# medidas que NAO sao chapa: dinheiro, telefone, ano, resolucao
NAO_E_CHAPA = re.compile(r"R\$|\d{4}-\d{4}|linhas", re.IGNORECASE)


def para_mm(valor, unidade):
    """'3,5' + 'cm' -> 35.0. Sem unidade, decide pelo tamanho."""
    n = float(valor.replace(",", "."))
    if unidade and unidade.lower() == "mm":
        return n
    if unidade and unidade.lower() == "cm":
        return n * 10.0
    # sem unidade: 3 e 3 cm; 29 e 29 mm. A viravolta fica em 15,
    # porque pinca de 15 cm nao existe e de 15 mm existe.
    return n * 10.0 if n <= 15 else n


def ler(caminho):
    """{grafica: [(chapa, pinca_mm)]}, na ordem em que aparecem."""
    achados = collections.OrderedDict()
    atual = None
    chapas_pendentes = []

    with io.open(caminho, encoding="latin-1", errors="replace") as f:
        linhas = [l.rstrip("\r\n") for l in f]

    for linha in linhas:
        limpa = linha.strip()
        if not limpa or set(limpa) <= set("_- "):
            continue

        tem_chapa = CHAPA.search(limpa) and not NAO_E_CHAPA.search(limpa)
        tem_pinca = PINCA.search(limpa)

        if not tem_chapa and not tem_pinca:
            # linha de nome: curta, sem numero solto demais
            if len(limpa) <= 60 and not re.search(r"senha|login|@|http|ftp",
                                                  limpa, re.IGNORECASE):
                atual = limpa
                chapas_pendentes = []
            continue

        if tem_chapa:
            for a, b in CHAPA.findall(limpa):
                a, b = int(a), int(b)
                if 100 <= max(a, b) <= 1200 and 100 <= min(a, b):
                    chapas_pendentes.append((max(a, b), min(a, b)))

        if tem_pinca and atual:
            m = PINCA.search(limpa)
            valor = m.group(1) or m.group(3)
            unidade = m.group(2) or m.group(4)
            pinca = para_mm(valor, unidade)
            alvo = chapas_pendentes or [None]
            for chapa in alvo:
                achados.setdefault(atual, []).append((chapa, pinca))
            chapas_pendentes = []

    return achados


def principal():
    caminho = sys.argv[1] if len(sys.argv) > 1 else ORIGEM
    if not os.path.exists(caminho):
        raise SystemExit("nao achei: %s" % caminho)

    tabela = ler(caminho)

    pares = [(c, p) for lista in tabela.values() for c, p in lista if c]
    print("graficas com chapa e pinca: %d" % len(tabela))
    print("pares chapa+pinca: %d" % len(pares))
    print()

    formatos = collections.Counter(c for c, _ in pares)
    print("== chapas mais usadas ==")
    for chapa, n in formatos.most_common(15):
        pincas = sorted(set(p for c, p in pares if c == chapa))
        texto = ", ".join("%g" % p for p in pincas[:8])
        print("   %-12s %3d graficas   pincas: %s mm"
              % ("%dx%d" % chapa, n, texto))
    print()

    print("== a pinca varia por MAQUINA, nao por formato ==")
    for chapa, n in formatos.most_common(5):
        pincas = collections.Counter(p for c, p in pares if c == chapa)
        comum = pincas.most_common(1)[0]
        print("   %-12s %d valores de pinca; o mais comum e %g mm (%d de %d)"
              % ("%dx%d" % chapa, len(pincas), comum[0], comum[1], n))


if __name__ == "__main__":
    principal()
