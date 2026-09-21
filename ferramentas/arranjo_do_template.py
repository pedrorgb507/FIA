# -*- coding: utf-8 -*-
r"""
Escreve a entrada do CATALOGO DE DOBRAS a partir de um modelo do Preps.

    python ferramentas/arranjo_do_template.py "<caminho do .tpl>" [caderno]

NAO ESCREVE NO CODIGO: imprime o bloco Python pronto, para alguem ler,
conferir e colar no `paginacao._ARRANJOS`. A colagem e a mao de
proposito - o catalogo e o que decide em que ordem o livro sai, e um
arranjo errado so aparece depois de dobrado e cortado.

POR QUE ELE EXISTE. O catalogo dizia, com razao, que a dobra vem de
MODELO LIDO e nunca de formula. So que ele foi enchido a mao, lugar por
lugar, a partir de DOIS tutoriais - e a casa tem 1725 modelos. Varridos
os 194 da AMERICA em 21/09/2026, o que ela usa e outra coisa:

    4 paginas   2x2  bate-vira        56 cadernos
    16          4x2  frente e verso   51
    8           4x2  bate-vira        45
    8           2x2  frente e verso   32
    12          2x3  frente e verso   12

O catalogo tinha 4 em 1x2 e 8 em 2x2 - os tutoriais. Nenhum dos dois e
o que a casa dobra.

O BATE-VIRA DO PREPS NAO TEM VERSO ESCRITO, e entender isso foi o que
destravou o caderno em bate-vira. Nesses modelos as N paginas do caderno
ficam TODAS na mesma chapa, em N lugares, com o campo de verso em zero:
a folha vira e passa de novo na MESMA chapa. Entao o verso de um lugar e
a pagina do lugar ESPELHADO - e a pergunta e por qual EIXO.

E O EIXO NAO E SEMPRE O MESMO. Eu li um modelo, vi o espelho horizontal
fechar, e escrevi aqui que era a regra. No modelo seguinte ela nao
fechava:

    AMERICA LIVRETO FT4_BV   8 paginas, 4x2   -> espelho HORIZONTAL
    LIVRO AMERICA RCC        4 paginas, 2x2   -> espelho VERTICAL

No RCC o horizontal juntaria a pagina 3 com a 2, que nao sao a mesma
folha. Eu ia colar aquilo no catalogo, e o miolo sairia fora de ordem -
o tipo de defeito que grava limpo e so aparece depois de dobrado.

Quem me barrou foi a CONFERENCIA, e e por isso que ela vem antes da
conveniencia: as duas paginas de um lugar tem de ser a MESMA FOLHA, a
2i-1 e a 2i. Entao aqui nao se escolhe o eixo - tentam-se os dois e fica
o que fecha. Nao fechando nenhum, nao ha arranjo a colar.

E a terceira vez nesta casa que generalizar de UM exemplo deu errado; as
outras duas estao na skill de imposicao, na dobra dos tutoriais e na
peca que "nunca deita".
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "..", "src"))

import ler_paginacao_preps as leitor              # noqa: E402


def grade_e_celulas(lugares):
    """
    (colunas, linhas, [(col, lin, giro, frente, verso)]) de um caderno.

    A COLUNA vem do x, da esquerda para a direita. A LINHA vem do y, mas
    ao contrario: no Preps o y cresce para CIMA, e a linha 1 do catalogo
    e a de CIMA - como a folha se le e como a skill desenha a dobra.
    """
    xs = sorted({round(p["x"], 1) for p in lugares})
    ys = sorted({round(p["y"], 1) for p in lugares}, reverse=True)
    celulas = []
    for p in lugares:
        col = xs.index(round(p["x"], 1)) + 1
        lin = ys.index(round(p["y"], 1)) + 1
        celulas.append((col, lin, str(p["giro"]), p["frente"], p["verso"]))
    celulas.sort(key=lambda c: (c[1], c[0]))
    return len(xs), len(ys), celulas


def completar_o_verso(colunas, linhas, celulas):
    """
    O verso de cada lugar, no bate-vira - e por QUAL EIXO a folha volta.

    Devolve (celulas, eixo, queixas).

    O EIXO NAO E SEMPRE O MESMO, e descobri isso porque a conferencia me
    barrou. No 'AMERICA LIVRETO FT4_BV' (8 paginas, 4x2) o verso vem do
    lugar espelhado na HORIZONTAL - a folha vira sobre o eixo vertical.
    No 'LIVRO AMERICA RCC' (4 paginas, 2x2) esse mesmo espelho juntaria
    a pagina 3 com a 2, que nao sao a mesma folha; ali quem fecha e o
    espelho VERTICAL - a folha TOMBA.

    Eu tinha generalizado o horizontal a partir de um modelo so, e ia
    colar um arranjo que poria o miolo fora de ordem. Entao aqui nao se
    escolhe o eixo: tentam-se os dois e fica o que FECHA. Nao fechando
    nenhum, nao ha arranjo a colar - e e melhor saber aqui.
    """
    por_lugar = {(c, l): f for c, l, _, f, _ in celulas}

    def tentar(par):
        saida, queixas = [], []
        for col, lin, giro, frente, _ in celulas:
            verso = por_lugar.get(par(col, lin), 0)
            if frente and verso and (frente + 1) // 2 != (verso + 1) // 2:
                queixas.append(
                    "o lugar (%d,%d) juntaria %d com %d, que nao sao a "
                    "mesma folha" % (col, lin, frente, verso))
            saida.append((col, lin, giro, frente, verso))
        return saida, queixas

    eixos = (
        ("VIRA no eixo vertical (espelho horizontal)",
         lambda c, l: (colunas + 1 - c, l)),
        ("TOMBA no eixo horizontal (espelho vertical)",
         lambda c, l: (c, linhas + 1 - l)),
    )
    primeira = None
    for nome, par in eixos:
        saida, queixas = tentar(par)
        if not queixas:
            return saida, nome, []
        if primeira is None:
            primeira = (saida, nome, queixas)
    saida, nome, queixas = primeira
    return saida, nome, queixas


def escrever(caminho, qual=0):
    cadernos = leitor.ler(caminho)
    if not cadernos:
        raise SystemExit("nao achei caderno nenhum em %s"
                         % os.path.basename(caminho))
    if qual >= len(cadernos):
        raise SystemExit("este modelo tem %d caderno(s); pedi o %d"
                         % (len(cadernos), qual))
    cad = cadernos[qual]
    lugares = cad["lugares"]
    colunas, linhas, celulas = grade_e_celulas(lugares)
    com_verso = any(c[4] for c in celulas)

    queixas = []
    if com_verso:
        vira = "FRENTE_E_VERSO"
    else:
        vira = "BATE_VIRA"
        celulas, eixo, queixas = completar_o_verso(
            colunas, linhas, celulas)

    # A CONFERENCIA QUE VALE: as paginas do caderno tem de dar 1..N,
    # cada uma uma vez. Batendo, a leitura esta certa; nao batendo, eu
    # li a coisa errada - e e melhor saber aqui do que numa chapa.
    numeros = sorted(n for c in celulas for n in (c[3], c[4]) if n)
    esperado = list(range(1, cad["paginas"] + 1))
    if vira == "BATE_VIRA":
        # no bate-vira cada pagina aparece DUAS vezes: uma como frente
        # de um lugar e outra como verso do espelhado
        esperado = sorted(esperado * 2)
    fecha = numeros == esperado

    print("# %s" % os.path.basename(caminho))
    print("# caderno |%s| - %d paginas, %dx%d, lido em %s"
          % (cad["nome"], cad["paginas"], colunas, linhas,
             __import__("datetime").date.today().strftime("%d/%m/%Y")))
    if not com_verso:
        print("# a folha %s" % eixo)
    print("(%d, %s): {" % (cad["paginas"], vira))
    print('    "grade": (%d, %d),' % (colunas, linhas))
    print('    "celulas": [')
    for col, lin, giro, f, v in celulas:
        print('        (%d, %d, "%s", %d, %d),' % (col, lin, giro, f, v))
    print("    ],")
    print("},")
    print()
    if queixas:
        print("NAO COLE ISTO:")
        for q in queixas:
            print("   " + q)
    print("conferencia das paginas: %s"
          % ("FECHA em 1..%d" % cad["paginas"] if fecha
             else "NAO FECHA - li %s" % numeros[:12]))
    return fecha and not queixas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[2])
    qual = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    sys.exit(0 if escrever(sys.argv[1], qual) else 1)
