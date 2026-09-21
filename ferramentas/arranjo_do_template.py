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


def vaos_da_dobra(lugares):
    """
    ((x...), (y...), medida, queixas) - ONDE A DOBRA COLA e onde se corta.

    Devolve MULTIPLICADORES, um por juncao: 0 onde as pecas se encostam
    e 1 onde ha vao. O tamanho do vao sai a parte, em 'medida'.

    POR QUE NAO UM VAO SO PARA A GRADE INTEIRA. Ate aqui o motor
    espalhava o vao por igual entre as celulas, que e o certo em folha
    solta - ali toda junta e corte. NUM CADERNO NAO: onde a folha DOBRA
    as duas paginas sao a mesma folha e tem de se encostar; so onde a
    guilhotina passa e que sobra vao. Medido nos modelos da casa em
    21/09/2026:

        SAPIENTIA   16 pag  4x2   x: 0 5 0    y: 5
        RCC         32 pag  4x4   x: 0 5 0    y: 5 5 5
        LIVRO AMERICA 18 pag 3x3  x: 5 0      y: 5 5
        CAD 03      12 pag  2x3   x: 0        y: 5 5

    Repare o LIVRO AMERICA: o vao esta entre a primeira e a segunda
    coluna, e nao no meio. Mesma peca, mesma grade que outros, e o vao
    em outro lugar - entao ele NAO se deduz da grade, le-se do modelo.

    E A PECA PODE ESTAR DEITADA. Nos tutoriais A4 a peca e 210 x 297 e o
    passo em x da 297: quem descontasse a largura acharia um vao de 87 mm
    que nao existe. O que se desconta e o lado que a peca OCUPA depois
    de girada.
    """
    def ocupa(p):
        return ((p["alt"], p["larg"]) if abs(int(p["giro"])) % 180 == 90
                else (p["larg"], p["alt"]))

    queixas = []

    def num(eixo, tomar):
        # por coluna (ou linha): a posicao e o lado que a peca ocupa ali
        tamanhos = {}
        for p in lugares:
            chave = round(p[eixo], 2)
            tamanhos.setdefault(chave, set()).add(round(tomar(p), 2))
        for onde, quais in sorted(tamanhos.items()):
            if len(quais) > 1:
                queixas.append(
                    "em %s=%g a peca ocupa %s - duas medidas na mesma "
                    "faixa, nao sei qual descontar"
                    % (eixo, onde, sorted(quais)))
        return [(onde, max(quais)) for onde, quais in sorted(tamanhos.items())]

    def folgas(faixas):
        return [round(b - (a + tam_a), 2)
                for (a, tam_a), (b, _) in zip(faixas, faixas[1:])]

    vx = folgas(num("x", lambda p: ocupa(p)[0]))
    # DE CIMA PARA BAIXO, como as LINHAS do catalogo - e nao como o
    # Preps guarda. La o y cresce para cima, entao a primeira folga que
    # sai daqui e a de baixo; o catalogo conta a linha 1 como a de cima,
    # e as duas listas tem de falar da mesma juncao.
    #
    # Nos quatro arranjos de hoje isso nao muda um numero: as grades tem
    # 2 ou 3 linhas e os vaos saem simetricos. E exatamente por isso que
    # esta troca precisa estar escrita - ela so apareceria no dia de uma
    # grade que nao fosse simetrica, ja montada errada.
    vy = list(reversed(folgas(num("y", lambda p: ocupa(p)[1]))))

    medidos = sorted({v for v in vx + vy if abs(v) > 0.05})
    for v in medidos:
        if v < 0:
            queixas.append("achei vao NEGATIVO (%g mm): as pecas se "
                           "invadem, e li a coisa errada" % v)
    if len(medidos) > 1:
        queixas.append(
            "achei vaos DIFERENTES no mesmo caderno (%s mm). O catalogo "
            "guarda multiplicador, e isso so serve com um vao so - este "
            "modelo pede outra conversa"
            % ", ".join("%g" % v for v in medidos))

    medida = medidos[0] if medidos else 0.0
    def mult(v):
        return 0 if abs(v) <= 0.05 else 1
    return (tuple(mult(v) for v in vx), tuple(mult(v) for v in vy),
            medida, queixas)


def escrever(caminho, qual=0):
    cadernos = leitor.ler(caminho)
    if not cadernos:
        raise SystemExit("nao achei caderno nenhum em %s"
                         % os.path.basename(caminho))
    if qual >= len(cadernos):
        # LISTA, nao so conta. O modelo do SAPIENTIA tem QUATRO
        # assinaturas - o caderno cheio de 16 e as tres sobras (8, 4 e 4
        # repetido duas vezes na mesma chapa) - e quem so lesse a
        # primeira acharia que o modelo nao sabe fechar o fim do livro.
        raise SystemExit(
            "este modelo tem %d caderno(s), e pedi o %d:\n%s"
            % (len(cadernos), qual,
               "\n".join("   %d  |%s|  %d paginas"
                          % (i, c["nome"], c["paginas"])
                          for i, c in enumerate(cadernos))))
    cad = cadernos[qual]
    lugares = cad["lugares"]
    colunas, linhas, celulas = grade_e_celulas(lugares)
    com_verso = any(c[4] for c in celulas)
    vaos_x, vaos_y, vao_medido, queixas = vaos_da_dobra(lugares)
    if com_verso:
        vira = "FRENTE_E_VERSO"
    else:
        vira = "BATE_VIRA"
        celulas, eixo, mais = completar_o_verso(colunas, linhas, celulas)
        queixas = queixas + mais

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
    print("# vao de %g mm onde a guilhotina passa; 0 onde a folha dobra"
          % vao_medido)
    print("(%d, %s): {" % (cad["paginas"], vira))
    print('    "grade": (%d, %d),' % (colunas, linhas))
    print('    "vaos": {"x": (%s), "y": (%s)},'
          % (", ".join(str(v) for v in vaos_x) + ("," if len(vaos_x) == 1 else ""),
             ", ".join(str(v) for v in vaos_y) + ("," if len(vaos_y) == 1 else "")))
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
