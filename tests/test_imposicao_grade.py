# -*- coding: utf-8 -*-
"""A grade de imposicao: quantas pecas, e onde cada uma cai.

Ate 11/09/2026 a montagem era 2 x 2 e nada mais, e exigia frente E
verso. O caso que derrubou isso foi um convite 100 x 210 que precisava
de SEIS pecas, so frente, na 525 x 459 - e nao havia por onde pedir.

O que estes testes prendem:

  1. a grade vem de fora (cols x rows) e a SANGRIA vem dela - metade do
     vao. Vao 3 da sangria 1,5, e nao os 2,5 do vao 5;
  2. 'so frente' e UMA arte repetida: uma pagina basta, e o programa nao
     escolhe pagina nem arquivo no lugar de ninguem;
  3. o bate-vira continua precisando de colunas PARES - ele parte a
     chapa ao meio por uma linha vertical;
  4. as seis pecas saem no lugar certo E VIRADAS, o que so se ve
     olhando o pixel: um quadrado no canto da arte tem de reaparecer no
     canto girado de cada celula.

A arte de cliente nao vai para o git, entao o PDF aqui e sintetico - a
mesma escolha de test_sangrar.py.
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ferramentas"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

pytest.importorskip("PIL")
from PIL import Image                                  # noqa: E402

import montar_bate_vira as mbv                         # noqa: E402
import sangrar                                         # noqa: E402

MM, PT = 25.4, 72.0


def _pdf(caminho, desenho, larg_mm, alt_mm, paginas=1):
    """PDF pelado (TrimBox = MediaBox) - a arte 'chegou sem sangria'."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject

    L, A = larg_mm / MM * PT, alt_mm / MM * PT
    w = PdfWriter()
    for _ in range(paginas):
        p = w.add_blank_page(width=L, height=A)
        fluxo = DecodedStreamObject()
        fluxo.set_data(desenho(L, A))
        p.replace_contents(fluxo)
        cx = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
        p.trimbox, p.bleedbox, p.cropbox = cx, cx, cx
    with open(caminho, "wb") as f:
        w.write(f)
    return caminho


def _canto(L, A):
    """
    Quase branco, com um quadrado PRETO no canto de baixo a esquerda.

    E ele que faz o giro aparecer: girando -90, o canto de baixo a
    esquerda da arte vai para o canto de CIMA a esquerda da celula. Uma
    arte chapada passaria neste teste mesmo montada ao contrario.
    """
    q = 20.0 / MM * PT
    return (("0 0 0 0.04 k 0 0 %.2f %.2f re f\n" % (L, A))
            + ("0 0 0 1 k 0 0 %.2f %.2f re f\n" % (q, q))).encode()


# --------------------------------------------------------------------------
# quem vai nas celulas
# --------------------------------------------------------------------------

def test_so_frente_aceita_um_arquivo_de_uma_pagina(tmp_path):
    """O convite chegou assim: uma pagina so, e seis vezes na chapa."""
    arte = _pdf(str(tmp_path / "convite.pdf"), _canto, 100.0, 210.0)
    assert mbv._pecas(arte, "so-frente") == [(arte, 1)]


def test_so_frente_nao_escolhe_pagina_nem_arquivo(tmp_path):
    """Escolher errado aqui nao daria erro em lugar nenhum."""
    duas = _pdf(str(tmp_path / "duas.pdf"), _canto, 100.0, 210.0, paginas=2)
    with pytest.raises(SystemExit) as erro:
        mbv._pecas(duas, "so-frente")
    assert "qual das 2" in str(erro.value)

    a = _pdf(str(tmp_path / "a.pdf"), _canto, 100.0, 210.0)
    b = _pdf(str(tmp_path / "b.pdf"), _canto, 100.0, 210.0)
    with pytest.raises(SystemExit) as erro:
        mbv._pecas([a, b], "so-frente")
    assert "UM arquivo" in str(erro.value)


def test_o_bate_vira_continua_exigindo_colunas_pares(tmp_path):
    """Ele parte a chapa ao meio por uma linha VERTICAL."""
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 100.0, 210.0, paginas=2)
    with pytest.raises(SystemExit) as erro:
        mbv.montar(arte, str(tmp_path / "m.pdf"), cols=3, rows=2)
    assert "PARES" in str(erro.value)


def test_frente_e_verso_ainda_nao_e_invencao_minha(tmp_path):
    """Sao DUAS chapas, e o nome de cada saida e convencao da casa."""
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 100.0, 210.0, paginas=2)
    with pytest.raises(SystemExit) as erro:
        mbv.montar(arte, str(tmp_path / "m.pdf"), tipo="frente-verso")
    assert "frente-verso" in str(erro.value)


# --------------------------------------------------------------------------
# a sangria sai da grade
# --------------------------------------------------------------------------

def test_a_sangria_sai_do_vao_da_grade():
    """
    Vao 3 da 1,5 - nao os 2,5 que o vao 5 dava. Amarrar a sangria a um
    numero fixo era justamente o que a regra do operador desfez, e a
    grade generica traria o erro de volta se ela nao viesse do vao.
    """
    assert sangrar.regra_da_sangria(3.0, 6) == 1.5
    assert sangrar.regra_da_sangria(5.0, 4) == 2.5
    assert sangrar.regra_da_sangria(3.0, 1) == 2.5      # sozinha: o padrao


# --------------------------------------------------------------------------
# a chapa que sai
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seis(tmp_path_factory):
    """O servico de verdade, em PDF sintetico: 6 x 100x210, vao 3, PM 52."""
    pasta = tmp_path_factory.mktemp("seis")
    arte = _pdf(str(pasta / "convite.pdf"), _canto, 100.0, 210.0)
    destino = str(pasta / "convite_MONTAGEM.pdf")
    d = mbv.montar(arte, destino, chapa=mbv.PM52, dpi=300,
                   cols=2, rows=3, vao=3.0, tipo="so-frente")
    return destino, d


def test_a_grade_de_seis_da_os_numeros_medidos(seis):
    """
    423,0 x 306,1 de corte a corte, margem 51 e o 1o corte em 60 - os
    mesmos numeros da chapa que rodou com o convite da UP. O centesimo
    de diferenca e o arredondamento do pixel a 300 dpi.
    """
    _, d = seis
    assert d["pecas"] == 6 and (d["cols"], d["rows"]) == (2, 3)
    assert d["sangria"] == 1.5 and d["vao"] == 3.0

    assert d["montagem"][0] == pytest.approx(423.0, abs=0.2)
    assert d["montagem"][1] == pytest.approx(306.0, abs=0.2)
    assert d["canto"][0] == pytest.approx(51.0, abs=0.2)

    # A PINCA NAO SE MEDE DA BORDA DO ARQUIVO: o primeiro corte cai
    # EXATAMENTE na pinca da maquina. Foi este numero que ja custou uma
    # chapa 12 mm fora do lugar, na CREATIVE.
    assert d["canto"][1] == mbv.PM52.pinca == 60.0
    assert len(d["colunas"]) == 2 and len(d["linhas"]) == 3
    assert not d["marcas_recusadas"]


def test_a_montagem_e_deitada(seis):
    """A borda LONGA da montagem e a que entra na pinca."""
    _, d = seis
    assert d["montagem"][0] > d["montagem"][1]


def test_as_seis_celulas_tem_arte_E_ESTAO_GIRADAS(seis):
    """
    Prova no pixel. O quadrado preto esta no canto de BAIXO A ESQUERDA
    da arte; girada -90, ele tem de reaparecer no canto de CIMA a
    esquerda de cada celula - e o canto de baixo a direita fica claro.

    Uma montagem sem giro, ou com uma celula vazia, passa em toda conta
    de milimetro e morre aqui.
    """
    from finart_ctp.ghostscript import GS

    destino, d = seis
    png = destino + ".png"
    R = 50.8                                   # 2 px por milimetro
    subprocess.check_call([GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
                           "-sDEVICE=pnggray", "-r%g" % R,
                           "-sOutputFile=" + png, destino])
    px = Image.open(png).load()
    alt = mbv.PM52.alt

    def tom(x_mm, y_do_pe):
        return px[int(round(x_mm * R / MM)),
                  int(round((alt - y_do_pe) * R / MM))]

    dl, da = d["deitada"]
    for lin, y in enumerate(d["linhas"]):
        for col, x in enumerate(d["colunas"]):
            cima_esq = tom(x + 8, y + da - 10)
            baixo_dir = tom(x + dl - 8, y + 8)
            assert cima_esq < 90, (
                "celula %d,%d sem o quadrado no canto girado (tom %d)"
                % (col, lin, cima_esq))
            assert baixo_dir > 200, (
                "celula %d,%d escura onde devia ser clara (tom %d) - "
                "giro errado?" % (col, lin, baixo_dir))


def test_o_padrao_continua_sendo_o_bate_vira_de_quatro():
    """Mexer na grade nao podia mudar o que a casa ja fazia."""
    assert (mbv.COLS, mbv.ROWS) == (2, 2)
    assert mbv.PECAS == 4
    assert mbv.VAO == 5.0
    assert not hasattr(mbv, "SANGRIA"), "a sangria voltou a ser numero fixo"


# --------------------------------------------------------------------------
# os DOIS limites: a area util da chapa, e a folha do formato
# --------------------------------------------------------------------------

def test_a_tabela_de_formatos_e_a_do_operador():
    """
    Tabela passada por ele em 11/09/2026, em centimetro; guardada em
    MILIMETRO. UM NUMERO PODE TER MAIS DE UMA FOLHA, e nao e erro de
    digitacao - o F-04 e 33x48 OU 24x66, e o F-06 tem tres.
    """
    from finart_ctp.config import FORMATOS_DA_CASA as F

    assert F[1][0] == ((660, 960), (640, 900))
    assert F[2][0] == ((480, 660), (460, 640))
    assert len(F[4]) == 2 and len(F[6]) == 3 and len(F[8]) == 2
    assert F[4][0] == ((330, 480), (315, 460))
    assert F[4][1] == ((240, 660), (230, 640))
    # a util e sempre MENOR que a folha, em todos eles
    for numero, folhas in F.items():
        for total, uteis in folhas:
            assert uteis[0] < total[0] and uteis[1] <= total[1], numero


def test_a_folha_entra_nos_DOIS_sentidos():
    """
    A tabela escreve largura x altura, mas 33x48 e a mesma folha que
    48x33 - e a montagem sai sempre DEITADA. Conferir num sentido so
    acusaria 'nao cabe' no que cabe: o convite da 423 x 306 e o util do
    F-04 e 315 x 460, que so serve virado.
    """
    from finart_ctp.config import cabe_no_formato

    cabe, sentido = cabe_no_formato(423.04, 306.12, 4)
    assert cabe and sentido == (460, 315)

    # a SEGUNDA folha do F-04 (24x66) nao serve para esta montagem
    assert cabe_no_formato(423.04, 306.12, 4, folha=1)[0] is False


def test_nao_saber_e_diferente_de_nao_caber():
    """
    Formato fora da tabela devolve None - e quem chama tem de poder ver
    a diferenca. Um 'nao cabe' manda parar; um 'nao sei' nao.
    """
    from finart_ctp.config import cabe_no_formato

    assert cabe_no_formato(100, 100, 13) == (None, None)
    assert cabe_no_formato(425, 100, 32)[0] is False
    assert cabe_no_formato(100, 90, 32)[0] is True


def test_a_montagem_que_nao_cabe_PARA_e_conta_o_que_houve(tmp_path):
    """
    "me avise somente se nao couber dentro do formato, area util" - o
    operador, 11/09/2026. Nao cabendo, eu paro e digo QUAL dos dois
    limites estourou; nao escolho por ele.
    """
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 150.0, 210.0)

    with pytest.raises(SystemExit) as erro:
        mbv.montar(arte, str(tmp_path / "m.pdf"), dpi=300,
                   cols=4, rows=3, tipo="so-frente")
    assert "UTIL DA CHAPA" in str(erro.value)
    assert "--assim-mesmo" in str(erro.value)

    # cabe na chapa, NAO cabe na folha do formato 32
    with pytest.raises(SystemExit) as erro:
        mbv.montar(arte, str(tmp_path / "m.pdf"), dpi=300,
                   cols=2, rows=1, tipo="so-frente", formato=32)
    assert "FORMATO 32" in str(erro.value)
    assert "UTIL DA CHAPA" not in str(erro.value), "acusou o limite errado"


def test_assim_mesmo_toca_e_deixa_dito_que_estourou(tmp_path):
    """
    A montagem e livre: quem manda tocar e o operador. Mas o relato tem
    de guardar que estourou - quem ler depois precisa saber que foi
    decisao de alguem, e nao descuido de ninguem.
    """
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 150.0, 210.0)
    destino = str(tmp_path / "m.pdf")

    d = mbv.montar(arte, destino, dpi=300, cols=2, rows=1,
                   tipo="so-frente", formato=32, assim_mesmo=True)
    assert os.path.exists(destino)
    assert d["estourou"] is True
    assert d["cabe_util"] is True and d["cabe_formato"] is False


def test_sem_formato_so_a_area_util_e_conferida(tmp_path):
    """O formato e opcional: sem ele, nada da folha e afirmado."""
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 100.0, 210.0)
    d = mbv.montar(arte, str(tmp_path / "m.pdf"), dpi=300,
                   cols=2, rows=3, vao=3.0, tipo="so-frente")
    assert d["cabe_util"] is True
    assert d["cabe_formato"] is None and d["estourou"] is False
