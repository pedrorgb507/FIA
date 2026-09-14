# -*- coding: utf-8 -*-
"""
Onde esta a MARCA DE CORTE da arte - a cruz que manda na pinca.

Por que isto existe: a pinca nao se mede da borda do arquivo, e sim da
marca de corte. Sao coisas diferentes - no santinho da Creative a marca
fica 11,9 mm para dentro da borda -, e medir do lugar errado poe a arte
12 mm fora do lugar na chapa.

Por que ler VETOR e nao imagem: tentamos achar a marca na imagem
rasterizada e nao deu. Em arte cheia, mancha de desenho passa por risco e
risco passa por mancha; duas versoes do detector deram numeros diferentes
para o mesmo arquivo. A marca, porem, NAO e imagem: e um traco desenhado,
e no PDF ele esta escrito com coordenada exata. Ali nao ha o que
interpretar.

COMO A MARCA SE RECONHECE, olhando os arquivos de verdade:

    y=  7.1 mm do pe   lados=diresq  comp=6.9    <- sangria
    y= 11.9 mm do pe   lados=diresq  comp=6.9    <- CORTE
    y= 26.9 mm do pe   lados=esq     comp=3.9    <- desenho, nao marca

  - e um traco HORIZONTAL curto, de 2,5 a 20 mm;
  - fica na margem LATERAL, fora do desenho;
  - aparece nos DOIS lados, na mesma altura - e o que separa marca de
    linha de desenho, que cai de um lado so;
  - vem sempre em duas: a de fora e a sangria, a de DENTRO e o corte.

Nao achando marca nenhuma, esta funcao devolve None e quem chamou para o
servico. Chutar a pinca e mandar chapa errada para a gravadora.
"""

import re


LADO_MM = 30.0          # ate onde vai a margem lateral onde a marca mora
BORDA_MM = 40.0         # e a faixa, junto da borda, onde ela pode estar
CURTO_MM = 2.5          # comprimento minimo de um traco de marca
COMPRIDO_MM = 20.0      # e o maximo
# Duas marcas a esta distancia UMA DA OUTRA sao a mesma altura.
#
# PERTO UMA DA OUTRA, e nao 'no mesmo balde de uma grade' - foi assim
# que o 'O.S 1035 - MPGO CARTAZES' da PRIME virou pendencia em
# 14/09/2026 com a marca desenhada e visivel na tela. As duas estavam
# la, a 0,10 mm uma da outra:
#
#     esquerda  10,06 mm do pe
#     direita    9,96 mm do pe
#
# Arredondando cada uma para a grade de 0,3 mm, a primeira caia em 10,2
# e a segunda em 9,9: baldes vizinhos, e o programa concluia que a marca
# so aparecia de um lado. 0,10 mm e folga de desenho, nao e outra marca.
JUNTAS_MM = 0.3


def _mm(pontos):
    return pontos / 72.0 * 25.4


def _segmentos(pagina, leitor):
    """
    Os tracos retos da pagina, em mm, separados por sentido.

    Devolve (horizontais, verticais), cada um como
    [(onde_esta, inicio, comprimento)]:

      horizontal -> (y, x do inicio, comprimento)   diz um corte de ALTURA
      vertical   -> (x, y do inicio, comprimento)   diz um corte de LARGURA
    """
    from pypdf.generic import ContentStream

    conteudo = ContentStream(pagina.get_contents(), leitor)
    horizontais, verticais = [], []
    atual = None
    for operandos, operador in conteudo.operations:
        try:
            if operador == b"m":
                atual = (float(operandos[0]), float(operandos[1]))
            elif operador == b"l" and atual:
                fim = (float(operandos[0]), float(operandos[1]))
                if abs(fim[1] - atual[1]) <= 0.5:        # horizontal
                    horizontais.append((_mm(atual[1]),
                                        _mm(min(atual[0], fim[0])),
                                        _mm(abs(fim[0] - atual[0]))))
                elif abs(fim[0] - atual[0]) <= 0.5:      # vertical
                    verticais.append((_mm(atual[0]),
                                      _mm(min(atual[1], fim[1])),
                                      _mm(abs(fim[1] - atual[1]))))
                atual = fim
            elif operador in (b"S", b"s", b"f", b"F", b"n", b"B", b"b"):
                atual = None
        except (TypeError, ValueError, IndexError):
            atual = None
    return horizontais, verticais


def _candidatos(tracos, medida_transversal, distancia_da_borda):
    """
    (de um extremo, do outro) - as alturas que podem ser marca.

    Um traco so conta se estiver encostado num dos dois extremos da
    folha no outro sentido, e dentro da faixa junto da borda.
    """
    a, b = [], []
    for onde, inicio, comp in tracos:
        if not (CURTO_MM <= comp <= COMPRIDO_MM):
            continue
        if inicio < LADO_MM:
            lado = a
        elif inicio + comp > medida_transversal - LADO_MM:
            lado = b
        else:
            continue
        d = distancia_da_borda(onde)
        if 0 <= d <= BORDA_MM:
            lado.append(d)
    return sorted(a), sorted(b)


def _dos_dois_lados(tracos, medida_transversal, distancia_da_borda):
    """
    A marca mais de DENTRO, entre as que aparecem nos DOIS extremos.

    'tracos' sao (onde_esta, inicio, comprimento). A marca de verdade
    aparece nos DOIS lados, na mesma altura; linha de desenho cai de um
    lado so.

    'na mesma altura' se mede UMA CONTRA A OUTRA - ver JUNTAS_MM. Cada
    par devolve a MEDIA das duas alturas: a diferenca entre elas e folga
    de desenho, e nao ha razao para preferir um lado.
    """
    a, b = _candidatos(tracos, medida_transversal, distancia_da_borda)
    dobradas = []
    for d in a:
        perto = [o for o in b if abs(o - d) <= JUNTAS_MM]
        if perto:
            dobradas.append((d + min(perto, key=lambda o: abs(o - d))) / 2.0)
    return max(dobradas) if dobradas else None


def marcas_de_corte(pdf, pagina=1):
    """
    {'pe':, 'topo':, 'esquerda':, 'direita':} - a distancia em mm de cada
    borda do arquivo ate a marca de corte daquele lado. None onde nao
    houver marca reconhecivel.

    Os quatro lados importam porque a arte da Creative as vezes chega EM
    PE e e girada antes de entrar na chapa. Girando, o pe passa a ser
    outra borda do arquivo, e a pinca tem de sair da marca daquela borda.
    """
    from pypdf import PdfReader

    vazio = {"pe": None, "topo": None, "esquerda": None, "direita": None}
    try:
        leitor = PdfReader(pdf)
        pag = leitor.pages[pagina - 1]
    except Exception:
        return vazio

    caixa = pag.mediabox
    larg, alt = _mm(float(caixa.width)), _mm(float(caixa.height))

    try:
        horizontais, verticais = _segmentos(pag, leitor)
    except Exception:
        return vazio

    medido = {
        # traco horizontal na margem lateral -> corte de baixo e de cima
        "pe": _dos_dois_lados(horizontais, larg, lambda y: y),
        "topo": _dos_dois_lados(horizontais, larg, lambda y: alt - y),
        # traco vertical na margem de cima/baixo -> corte da esquerda e
        # da direita
        "esquerda": _dos_dois_lados(verticais, alt, lambda x: x),
        "direita": _dos_dois_lados(verticais, alt, lambda x: larg - x),
    }
    return _como_aparece(medido, (pag.get("/Rotate") or 0) % 360)


# O /Rotate do PDF gira a pagina na hora de mostrar, sem mexer no
# desenho: os tracos continuam escritos na posicao antiga. Gire uma folha
# 90 graus para a direita e veja - a borda da direita desce e vira o pe.
#
# Sem esta conversao, arte que chegasse com /Rotate marcado sairia com a
# pinca tirada da borda errada, e ninguem veria antes da maquina.
DE_ONDE_VEM_CADA_LADO = {
    0: {"pe": "pe", "topo": "topo",
        "esquerda": "esquerda", "direita": "direita"},
    90: {"pe": "direita", "topo": "esquerda",
         "esquerda": "pe", "direita": "topo"},
    180: {"pe": "topo", "topo": "pe",
          "esquerda": "direita", "direita": "esquerda"},
    270: {"pe": "esquerda", "topo": "direita",
          "esquerda": "topo", "direita": "pe"},
}


def pistas_da_marca(pdf, pagina, lado):
    """
    O que SE VIU naquele lado, em palavras. Para o recado da pendencia.

    Quando a marca nao e achada, dizer so 'nao achei' manda o operador
    procurar no escuro - e o mais provavel e que ela esteja la, so que
    fora de alguma das regras daqui. Entao a FIA conta o que viu: as
    alturas candidatas de cada extremo. Foi olhando exatamente esses
    numeros que se descobriu, em 14/09/2026, que o 'MPGO CARTAZES' tinha
    a marca nos dois lados com 0,10 mm de diferenca.
    """
    from pypdf import PdfReader

    try:
        leitor = PdfReader(pdf)
        pag = leitor.pages[pagina - 1]
        larg, alt = _mm(float(pag.mediabox.width)), _mm(float(pag.mediabox.height))
        horizontais, verticais = _segmentos(pag, leitor)
    except Exception:
        return "nao consegui reler o arquivo para dizer o que vi"

    onde = {
        "pe": (horizontais, larg, lambda y: y),
        "topo": (horizontais, larg, lambda y: alt - y),
        "esquerda": (verticais, alt, lambda x: x),
        "direita": (verticais, alt, lambda x: larg - x),
    }.get(lado)
    if not onde:
        return ""

    a, b = _candidatos(*onde)
    # o mesmo traco aparece varias vezes (contorno, sombra, repeticao);
    # listar 10,06 tres vezes nao ajuda ninguem
    a = sorted({round(d, 2) for d in a})
    b = sorted({round(d, 2) for d in b})
    if not a and not b:
        return ("nao vi traco curto nenhum na faixa dos %.0f mm da borda "
                "- se a marca estiver mais para dentro, ela esta fora do "
                "alcance" % BORDA_MM)
    if not a or not b:
        return ("vi traco de UM lado so, a %s mm da borda. A marca de "
                "verdade aparece nos dois"
                % ", ".join("%.2f" % d for d in sorted(a or b)[:6]))
    return ("vi traco dos dois lados, mas nao na mesma altura: de um "
            "lado a %s mm e do outro a %s mm"
            % (", ".join("%.2f" % d for d in a[:6]),
               ", ".join("%.2f" % d for d in b[:6])))


def _como_aparece(medido, rotacao):
    """As marcas na orientacao em que a pagina e VISTA, nao gravada."""
    de_onde = DE_ONDE_VEM_CADA_LADO.get(rotacao)
    if de_onde is None:
        return medido                  # giro torto: melhor nao inventar
    return {lado: medido[origem] for lado, origem in de_onde.items()}
