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


def _segmentos_horizontais(pagina, leitor):
    """[(y, x_inicio, comprimento)] de cada traco reto horizontal, em mm."""
    from pypdf.generic import ContentStream

    conteudo = ContentStream(pagina.get_contents(), leitor)
    achados = []
    atual = None
    for operandos, operador in conteudo.operations:
        try:
            if operador == b"m":
                atual = (float(operandos[0]), float(operandos[1]))
            elif operador == b"l" and atual:
                fim = (float(operandos[0]), float(operandos[1]))
                if abs(fim[1] - atual[1]) <= 0.5:        # horizontal
                    achados.append((_mm(atual[1]),
                                    _mm(min(atual[0], fim[0])),
                                    _mm(abs(fim[0] - atual[0]))))
                atual = fim
            elif operador in (b"S", b"s", b"f", b"F", b"n", b"B", b"b"):
                atual = None
        except (TypeError, ValueError, IndexError):
            atual = None
    return achados


def marcas_de_corte(pdf, pagina=1):
    """
    (corte_do_pe_mm, corte_do_topo_mm) da pagina, ou (None, None).

    Medidos da borda do arquivo ate a marca de corte. Devolve None quando
    nao ha marca reconhecivel - e ai o servico para, em vez de sair com a
    pinca chutada.
    """
    from pypdf import PdfReader

    try:
        leitor = PdfReader(pdf)
        pag = leitor.pages[pagina - 1]
    except Exception:
        return None, None

    if ((pag.get("/Rotate") or 0) % 360) != 0:
        # pagina girada: as coordenadas dos tracos nao batem com o que se
        # ve na tela. Preferimos parar a arriscar a conta.
        return None, None

    caixa = pag.mediabox
    larg, alt = _mm(float(caixa.width)), _mm(float(caixa.height))

    try:
        tracos = _segmentos_horizontais(pag, leitor)
    except Exception:
        return None, None

    # so os que estao na margem lateral e tem tamanho de marca
    candidatos = []
    for y, x, comp in tracos:
        if not (CURTO_MM <= comp <= COMPRIDO_MM):
            continue
        if x < LADO_MM:
            lado = "esq"
        elif x + comp > larg - LADO_MM:
            lado = "dir"
        else:
            continue
        candidatos.append((y, lado))

    def corte(distancia_da_borda):
        """A marca mais de DENTRO, entre as que aparecem nos dois lados."""
        alturas = {}
        for y, lado in candidatos:
            d = distancia_da_borda(y)
            if 0 <= d <= BORDA_MM:
                alturas.setdefault(round(d / JUNTAS_MM), set()).add(lado)
        dobradas = [k * JUNTAS_MM for k, lados in alturas.items()
                    if len(lados) == 2]
        return max(dobradas) if dobradas else None

    return corte(lambda y: y), corte(lambda y: alt - y)
