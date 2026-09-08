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
JUNTAS_MM = 0.3         # duas marcas nesta distancia sao a mesma altura


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


def _dos_dois_lados(tracos, medida_transversal, distancia_da_borda):
    """
    A marca mais de DENTRO, entre as que aparecem nos DOIS extremos.

    'tracos' sao (onde_esta, inicio, comprimento). Um traco so conta se
    estiver encostado num dos dois extremos da folha no outro sentido -
    e a marca de verdade aparece nos dois, na mesma altura. Linha de
    desenho cai de um lado so.
    """
    posicoes = {}
    for onde, inicio, comp in tracos:
        if not (CURTO_MM <= comp <= COMPRIDO_MM):
            continue
        if inicio < LADO_MM:
            extremo = "a"
        elif inicio + comp > medida_transversal - LADO_MM:
            extremo = "b"
        else:
            continue
        d = distancia_da_borda(onde)
        if 0 <= d <= BORDA_MM:
            posicoes.setdefault(round(d / JUNTAS_MM), set()).add(extremo)

    dobradas = [k * JUNTAS_MM for k, extremos in posicoes.items()
                if len(extremos) == 2]
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


def _como_aparece(medido, rotacao):
    """As marcas na orientacao em que a pagina e VISTA, nao gravada."""
    de_onde = DE_ONDE_VEM_CADA_LADO.get(rotacao)
    if de_onde is None:
        return medido                  # giro torto: melhor nao inventar
    return {lado: medido[origem] for lado, origem in de_onde.items()}
