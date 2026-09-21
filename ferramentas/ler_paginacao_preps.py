# -*- coding: utf-8 -*-
r"""
Le a PAGINACAO dos modelos do Preps 5.0. NAO ESCREVE NADA.

O varredura_preps.py ja pergunta aos modelos qual e a sangria, o tamanho
da marca e o vao entre pecas. Ele ignora justamente o que um arquivo de
MUITAS PAGINAS precisa saber: QUAL PAGINA VAI EM QUAL LUGAR, de que lado
da folha, e virada para onde.

Isso esta escrito em cada linha de peca, e sempre esteve:

    %SSiPrshPage: x y larg alt GIRO FRENTE VERSO sangE sangB sangD sangT ...

Os dois numeros depois do giro sao um PAR: a pagina que cai naquele
lugar na frente da folha, e a que cai no MESMO lugar no verso. E assim
que uma folha de oito paginas se descreve em quatro lugares.

    %SSiSignature: |nome| quantas_paginas ...

O caderno diz quantas paginas ele segura. A conferencia que este
programa faz e essa: as paginas do caderno tem de dar 1..N, cada uma uma
vez. Batendo, a leitura dos campos esta certa; nao batendo, eu li a
coisa errada - e e melhor saber disso aqui do que numa chapa.

O GIRO, medido nos modelos (ver 'girar' abaixo): o campo vale 4, 5, 6 ou
7, e nao e um angulo - e um par de bits. O de baixo diz se a peca esta
DEITADA na celula; o outro diz se ela esta de cabeca para baixo. A prova
e geometrica, e esta no proprio modelo: no '8 page SW' as pecas so se
encaixam na folha se as de giro 4 e 6 ocuparem 297 mm de largura, que e
a ALTURA da pagina A4 - ou seja, giradas.

    python ferramentas/ler_paginacao_preps.py                  <- todos
    python ferramentas/ler_paginacao_preps.py "<arquivo.tpl>"  <- um so
"""

import io
import os
import re
import sys

PASTA = r"C:\Program Files (x86)\Creo\Preps 5.0\Templates"
PT_MM = 25.4 / 72.0


def mm(pt):
    return round(float(pt) * PT_MM, 2)


def numeros(resto):
    """Os campos numericos, fora os |nomes| e as ''."""
    resto = re.sub(r"\|[^|]*\|", " ", resto)
    resto = re.sub(r"'[^']*'", " ", resto)
    return [float(n) for n in re.findall(r"-?\d+\.?\d*", resto)]


# O giro, em texto. Os dois bits de baixo do campo, medidos nos modelos:
#   bit 0 ligado  -> a peca fica em PE (do jeito que o arquivo e)
#   bit 0 apagado -> a peca fica DEITADA (girada um quarto de volta)
#   bit 1 ligado  -> mais meia volta
GIROS = {7: "0", 5: "180", 6: "90", 4: "-90"}


def girar(campo):
    return GIROS.get(int(campo), "?%d" % int(campo))


# O ESTILO DE VIRA, no 5o campo do %SSiPressSheet. Medido nos 100
# cadernos dos modelos de exemplo, e a separacao e limpa - nenhum caso
# cai do lado errado:
#
#   campo 5 = 0   67 cadernos, 30 dizem 'SW'/'duplex' no nome, nenhum
#                 diz WT nem simplex
#   campo 5 = 1   11 cadernos, 8 dizem 'WT' no nome, nenhum diz outra
#   campo 5 = 3   22 cadernos, 13 dizem 'simplex'/'1-up', nenhum outro
#
# Sao os MESMOS tres tipos de vira do painel da FIA.
VIRAS = {0: "frente e verso", 1: "bate-vira", 3: "so frente"}


def vira(campo):
    return VIRAS.get(int(campo), "?%d" % int(campo))


def ler(caminho):
    """[{nome, paginas, folha, lugares:[...]}] - um por caderno."""
    cadernos = []
    atual = None
    folha = None
    with io.open(caminho, encoding="latin-1", errors="replace") as f:
        for linha in f:
            if not linha.startswith("%SSi"):
                continue
            chave, _, resto = linha[4:].rstrip("\r\n").partition(":")
            n = numeros(resto)
            if chave == "Signature":
                achado = re.search(r"\|([^|]*)\|", resto)
                atual = {"nome": achado.group(1) if achado else "?",
                         "paginas": int(n[0]) if n else 0,
                         "folha": None, "vira": None, "pinca": None,
                         "lugares": []}
                cadernos.append(atual)
                folha = None
            elif chave == "PressSheet" and len(n) >= 2:
                folha = (mm(n[0]), mm(n[1]))
                if atual is not None and atual["folha"] is None:
                    atual["folha"] = folha
                    # A FOLHA DIZ COMO ELA VIRA E QUANTO SOBRA NO PE.
                    # O 6o campo fica na faixa da pinca em todos os 100
                    # cadernos - 101,6 mm (4 polegadas) nos modelos em
                    # polegada, 60 mm nos em milimetro, que e justamente
                    # a pinca da PM 52 da AMERICA.
                    if len(n) >= 6:
                        atual["vira"] = vira(n[4])
                        atual["pinca"] = mm(n[5])
            elif chave == "PrshPage" and len(n) >= 7 and atual is not None:
                atual["lugares"].append({
                    "x": mm(n[0]), "y": mm(n[1]),
                    "larg": mm(n[2]), "alt": mm(n[3]),
                    "giro": girar(n[4]),
                    "frente": int(n[5]), "verso": int(n[6]),
                })
    return cadernos


def conferir(caderno):
    """
    As paginas do caderno dao 1..N, cada uma uma vez?

    Esta e a prova de que os dois campos sao mesmo frente e verso. Devolve
    (bate, recado).

    O ZERO NAO E PAGINA: e 'deste lado nao vai nada'. O Calendar.tpl e
    feito disso - cada folha do calendario tem mes de um lado so, e o
    outro lado do lugar vem 0. Contar o zero como pagina fazia o modelo
    do calendario 'repetir a pagina 0' oito vezes, e era leitura minha
    errada, nao defeito do modelo.
    """
    n = caderno["paginas"]
    if not n or not caderno["lugares"]:
        return None, "caderno sem pecas"
    saiu = [p["frente"] for p in caderno["lugares"]]
    saiu += [p["verso"] for p in caderno["lugares"]]
    vazios = saiu.count(0)
    saiu = sorted(p for p in saiu if p)
    esperado = list(range(1, n + 1))
    sobra = (" (%d lado%s em branco)" % (vazios, "s" if vazios > 1 else "")
             if vazios else "")
    if saiu == esperado:
        return True, "1..%d, cada uma uma vez%s" % (n, sobra)
    repetidas = sorted(set(x for x in saiu if saiu.count(x) > 1))
    faltando = sorted(set(esperado) - set(saiu))
    partes = []
    if repetidas:
        partes.append("repetidas %s" % repetidas)
    if faltando:
        partes.append("faltando %s" % faltando)
    if not partes:
        partes.append("saiu %s" % saiu)
    return False, "; ".join(partes)


def mostrar(caminho, so_resumo=False):
    cadernos = ler(caminho)
    if not cadernos:
        return 0, 0
    print("=" * 70)
    print(os.path.basename(caminho))
    batem = falham = 0
    for c in cadernos:
        bate, recado = conferir(c)
        if bate:
            batem += 1
        elif bate is False:
            falham += 1
        folha = ("%g x %g mm" % c["folha"]) if c["folha"] else "?"
        print()
        print("  |%s|  %d paginas em %d lugares   folha %s"
              % (c["nome"], c["paginas"], len(c["lugares"]), folha))
        print("  vira: %s   pinca: %s"
              % (c["vira"] or "?",
                 "%g mm" % c["pinca"] if c["pinca"] is not None else "?"))
        print("  paginas: %s" % recado)
        if so_resumo:
            continue
        print("      %-9s %-9s %-13s %-6s %-7s %s"
              % ("x", "y", "peca", "giro", "frente", "verso"))
        for p in sorted(c["lugares"], key=lambda p: (-p["y"], p["x"])):
            print("      %-9g %-9g %-13s %-6s %-7d %d"
                  % (p["x"], p["y"], "%g x %g" % (p["larg"], p["alt"]),
                     p["giro"], p["frente"], p["verso"]))
    print()
    return batem, falham


def principal():
    alvos = [a for a in sys.argv[1:] if not a.startswith("--")]
    so_resumo = "--resumo" in sys.argv
    if not alvos:
        if not os.path.isdir(PASTA):
            raise SystemExit("nao achei a pasta de modelos: %s" % PASTA)
        alvos = []
        for raiz, _, nomes in os.walk(PASTA):
            for nome in sorted(nomes):
                if nome.lower().endswith(".tpl"):
                    alvos.append(os.path.join(raiz, nome))
        so_resumo = True

    batem = falham = 0
    for caminho in alvos:
        b, f = mostrar(caminho, so_resumo=so_resumo)
        batem += b
        falham += f
    print("cadernos cuja paginacao FECHA em 1..N: %d" % batem)
    print("cadernos que NAO fecham (ou repetem de proposito): %d" % falham)


if __name__ == "__main__":
    principal()
