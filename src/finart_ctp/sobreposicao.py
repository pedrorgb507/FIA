# -*- coding: utf-8 -*-
r"""
O PRETO CHEIO PASSA A SOBREPOR, dentro do PDF.

Regra do operador, 18/09/2026: *"sempre o preto fique sobreposto, quando
ele for 100% nao pode vazar nas outras cores"*.

O QUE ACONTECE SEM ISTO
-----------------------
Preto que nao sobrepoe **recorta** o que esta embaixo: abre um buraco com
o formato exato da letra nas outras tres chapas. Qualquer desvio de
registro vira um fio branco em volta do texto, e nada da erro em lugar
nenhum - so aparece na tiragem, com a chapa queimada e o papel rodando.

Medido no 'Timbrado Traumat' de 18/09/2026, um texto preto sobre azul
chapado (C 67, Y 19):

    19.860 pixels de preto forte, e em TODOS eles C=M=Y=0
    o anel de 3 px em volta do preto: 100% com cor, C medio 171

Um buraco perfeito no azul.

POR QUE ISTO NAO SAI DO CORELDRAW
---------------------------------
Foram tentados, nesta ordem, e os tres FALHARAM:

 1. `PDFSettings.Overprints = True` - o PDF saiu identico. Aquilo
    PRESERVA a sobreposicao que os objetos ja tem; nao cria nenhuma;
 2. `Shape.OverprintFill = True` nos objetos de preto cheio - a marca
    PEGA (relendo, `GetOverprintFillState()` devolve 4), mas o
    `PublishToPDF` do Corel 27 **nao a exporta**: os `ExtGState` do PDF
    continuaram `/OP false`;
 3. os dois juntos, com e sem a predefinicao FINART carregada. Idem.

Entao a sobreposicao se declara aqui, no PDF, que e onde a gravadora vai
le-la.

COMO
----
Em PDF a sobreposicao e estado grafico, nao propriedade da cor. Entao:

  - nascem dois `ExtGState`: um que LIGA (`/OP true /op true /OPM 1`) e
    um que DESLIGA (`/OP false /op false`);
  - o fluxo e varrido atras dos operadores de cor CMYK - `k` (preenche)
    e `K` (contorna) -, e logo depois de cada um entra o `gs` que
    corresponde aquela cor.

Assim o estado de sobreposicao anda SEMPRE colado na ultima cor
escolhida, sem que se precise rastrear `q`/`Q` - e e por isso que o
DESLIGA existe: sem ele, uma cor clara herdaria o `/OP true` do preto
anterior.

SO O PRETO, E SO O CHEIO
------------------------
Cor clara sobrepondo nao cobre o que esta embaixo: ela **mistura**, e sai
uma terceira cor que ninguem pediu. E o operador falou em **100%** - o
proprio Timbrado tem preto de 70%, que fica de fora: cinza sobreposto
misturaria do mesmo jeito. O corte e o `OverprintBlackLimit` da casa,
que ja era 95 - 95 pega o 100 e a franja de antisserrilhamento junto.

O `/OPM 1` e o que faz a conta certa: nesse modo o canal que vale ZERO
nao e escrito, e o que estava embaixo fica. Preto cheio e `0 0 0 1`, e
entao C, M e Y do fundo atravessam.
"""

import re

import pypdf
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject,
                           DictionaryObject, NameObject, NumberObject)

# os dois nomes que entram nos recursos da pagina. Sao feios de
# proposito: tem de nao colidir com os que a Corel ja escreveu.
LIGA = "/FIA_OP_LIGA"
DESLIGA = "/FIA_OP_DESLIGA"

# c m y k seguidos de 'k' (preenche) ou 'K' (contorna). O \b no fim
# impede casar com o 'k' de outro token.
COR_CMYK = re.compile(
    rb"(?P<c>[\d.]+)\s+(?P<m>[\d.]+)\s+(?P<y>[\d.]+)\s+(?P<k>[\d.]+)\s+"
    rb"(?P<op>k|K)(?=[\s/\[<(\]>)]|$)")


def _e_preto_cheio(c, m, y, k, limite):
    return c == 0.0 and m == 0.0 and y == 0.0 and k * 100.0 >= limite


def _marcar(dados, limite):
    """
    Devolve (novo_fluxo, quantos_pretos). Nao mexe no desenho: so
    acrescenta um 'gs' depois de cada cor.
    """
    saida = bytearray()
    fim = 0
    pretos = 0
    for m in COR_CMYK.finditer(dados):
        try:
            vals = [float(m.group(n)) for n in ("c", "m", "y", "k")]
        except ValueError:
            continue
        preto = _e_preto_cheio(*vals, limite=limite)
        if preto:
            pretos += 1
        saida += dados[fim:m.end()]
        saida += b" " + (LIGA if preto else DESLIGA).encode() + b" gs"
        fim = m.end()
    saida += dados[fim:]
    return bytes(saida), pretos


def _estados(recursos):
    """Poe os dois ExtGState nos recursos, se ainda nao estiverem."""
    if "/ExtGState" not in recursos:
        recursos[NameObject("/ExtGState")] = DictionaryObject()
    gs = recursos["/ExtGState"]
    try:
        gs = gs.get_object()
    except Exception:
        pass

    liga = DictionaryObject()
    liga[NameObject("/Type")] = NameObject("/ExtGState")
    liga[NameObject("/OP")] = BooleanObject(True)     # contorno
    liga[NameObject("/op")] = BooleanObject(True)     # preenchimento
    liga[NameObject("/OPM")] = NumberObject(1)        # o zero nao escreve

    desliga = DictionaryObject()
    desliga[NameObject("/Type")] = NameObject("/ExtGState")
    desliga[NameObject("/OP")] = BooleanObject(False)
    desliga[NameObject("/op")] = BooleanObject(False)

    gs[NameObject(LIGA)] = liga
    gs[NameObject(DESLIGA)] = desliga


def sobrepor_preto(origem, destino, limite=95):
    """
    Grava em 'destino' o PDF de 'origem' com o preto cheio sobrepondo.

    Devolve quantas ocorrencias de preto cheio foram marcadas. Zero quer
    dizer que nao havia preto de uma tinta so - e nao que falhou.

    Mexe tambem nos Form XObject: arte da Corel guarda quase tudo neles,
    e so a pagina nao pegaria quase nada.
    """
    leitor = pypdf.PdfReader(origem)
    escritor = pypdf.PdfWriter()
    escritor.append(leitor)

    total = 0
    for pagina in escritor.pages:
        recursos = pagina.get("/Resources")
        if recursos is None:
            continue
        recursos = recursos.get_object()
        _estados(recursos)

        fluxo = pagina.get_contents()
        if fluxo is not None:
            novo, n = _marcar(fluxo.get_data(), limite)
            total += n
            fs = DecodedStreamObject()
            fs.set_data(novo)
            pagina.replace_contents(fs)

        # OS FORM XOBJECT. Cada um tem recursos proprios, e o 'gs' que
        # eu escrevo la dentro precisa de um ExtGState de LA.
        xo = recursos.get("/XObject")
        if xo is None:
            continue
        for nome in list(xo.get_object().keys()):
            o = xo.get_object()[nome].get_object()
            if o.get("/Subtype") != "/Form":
                continue
            rec = o.get("/Resources")
            if rec is None:
                rec = DictionaryObject()
                o[NameObject("/Resources")] = rec
            _estados(rec.get_object())
            novo, n = _marcar(o.get_data(), limite)
            total += n
            o.set_data(novo)

    with open(destino, "wb") as f:
        escritor.write(f)
    return total


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        raise SystemExit("uso: sobreposicao.py entrada.pdf saida.pdf [limite]")
    lim = float(sys.argv[3]) if len(sys.argv) > 3 else 95
    n = sobrepor_preto(sys.argv[1], sys.argv[2], lim)
    print("%d ocorrencia(s) de preto cheio passaram a sobrepor" % n)
