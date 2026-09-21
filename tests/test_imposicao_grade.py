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


# --------------------------------------------------------------------------
# a cor da arte: CMYK se le como esta escrito, RGB se converte
# --------------------------------------------------------------------------
#
# O caso, 16/09/2026: o 'IPO-563263 FOLDER -FLYER 148x210mm (1).pdf' da
# AMERICA, um PDF todo em ICCBased /N 3. A montagem saiu com K em ZERO e
# o operador viu na hora - "as cores mudaram completamente".
#
# A causa era uma suposicao escrita no topo do programa: "o arquivo ja
# chega em CMYK". Nele o -dUseFastColor e o certo, porque le a tinta
# como esta escrita. Em arte RGB a mesma flag desliga o gerenciamento e
# cai na conta ingenua C=1-R, M=1-G, Y=1-B - sem gerar preto nenhum.
#
#     com a flag    C 0,9942  M 0,9945  Y 0,9949  K 0,0000
#     gerenciado    C 0,9925  M 0,9945  Y 0,9948  K 0,8978
#
# A chapa que o operador montou no CorelDRAW no mesmo dia tem 68,9% de
# preto dentro da arte; o caminho gerenciado da 69,2%.

def _pdf_rgb(caminho, larg_mm=60.0, alt_mm=40.0):
    """Uma pagina cinza medio escrita em RGB - onde a flag zerava o K."""
    return _pdf(caminho,
                lambda L, A: ("0.5 0.5 0.5 rg 0 0 %.2f %.2f re f\n"
                              % (L, A)).encode(), larg_mm, alt_mm)


def _pdf_cmyk(caminho, larg_mm=60.0, alt_mm=40.0):
    """A mesma mancha, mas escrita em CMYK com o preto no K."""
    return _pdf(caminho,
                lambda L, A: ("0 0 0 0.5 k 0 0 %.2f %.2f re f\n"
                              % (L, A)).encode(), larg_mm, alt_mm)


def test_quem_decide_a_conversao_e_o_espaco_de_cor_do_ARQUIVO(tmp_path):
    assert mbv.arte_em_cmyk(_pdf_cmyk(str(tmp_path / "cmyk.pdf"))) is True
    assert mbv.arte_em_cmyk(_pdf_rgb(str(tmp_path / "rgb.pdf"))) is False


def test_arte_RGB_NAO_sai_com_o_preto_zerado(tmp_path):
    """
    O defeito em uma linha: cinza 50% RGB tem de virar tinta COM preto.

    Sem a correcao este K vinha 0,0000 e todo o escuro saia das tres
    tintas coloridas - tres chapas onde tem de haver a do preto, e
    qualquer desvio de registro borrando o que devia ser neutro.
    """
    origem = _pdf_rgb(str(tmp_path / "rgb.pdf"))
    saida = str(tmp_path / "peca.pdf")
    mbv.peca_em_pdf(origem, 1, 150, saida)
    from finart_ctp.ghostscript import cobertura_por_pagina
    tinta = cobertura_por_pagina(saida, sem_icc=True)[0]
    assert tinta["K"] > 0.10, "arte RGB saiu sem preto: %s" % tinta


def test_arte_CMYK_continua_lida_como_esta_escrita(tmp_path):
    """
    A outra metade, e ela nao pode regredir: 0 0 0 0.5 k e UMA tinta.

    E a armadilha 1 da skill de cor - passar isto pelo perfil embutido
    remistura o preto de K sozinho nas quatro tintas, e a OS passaria a
    falar de quatro chapas onde a gravadora encontra uma.
    """
    origem = _pdf_cmyk(str(tmp_path / "cmyk.pdf"))
    saida = str(tmp_path / "peca.pdf")
    mbv.peca_em_pdf(origem, 1, 150, saida)
    from finart_ctp.ghostscript import cobertura_por_pagina
    tinta = cobertura_por_pagina(saida, sem_icc=True)[0]
    assert tinta["K"] > 0.40, "o preto saiu do K: %s" % tinta
    for t in ("C", "M", "Y"):
        assert tinta[t] < 0.05, "%s foi inventado pelo perfil: %s" % (t, tinta)


# --------------------------------------------------------------------------
# O GIRO DA PECA: em pe ou deitada, e quem decide
# --------------------------------------------------------------------------
#
# O caso, 18/09/2026, do operador: "a pagina e em pe, e vc esta colocando
# ela como se fosse deitada, e na visualizacao quando eu giro ela, vc fala
# que nao cabe na montagem".
#
# A celula era SEMPRE a peca deitada - `dl, da = corte_a, corte_l` fixo -
# e o giro so podia ser -90 ou +90. Arte em pe nao tinha como ficar em pe:
# invertendo os campos o painel deitava de novo, e a montagem que sobrava
# estourava o limite e vinha de vermelho.
#
# Duas coisas estavam com o mesmo nome. A MONTAGEM sai deitada - a borda
# longa entra na pinca, e isso continua valendo. A PECA dentro da celula
# pode entrar de qualquer um dos quatro jeitos.

def test_a_meia_volta_e_180_e_nao_troca_de_sinal():
    """
    Com ±90 trocar o sinal dava o mesmo e por isso a conta antiga
    passava. Com 0 ela quebraria calada: -0 e 0, e as duas metades do
    bate-vira sairiam NO MESMO sentido.
    """
    assert mbv._meia(-90) == 90
    assert mbv._meia(90) == -90
    assert mbv._meia(0) == 180
    assert mbv._meia(180) == 0
    for g in (-90, 90, 0, 180):
        assert mbv._meia(mbv._meia(g)) == g, "duas meias voltas tem de voltar"


def _cel(tmp_path, giro, nome):
    """Monta so-frente 1x1 e devolve (largura, altura) da celula."""
    arte = _pdf(str(tmp_path / nome), _canto, 100.0, 200.0)
    saida = str(tmp_path / (nome + ".out.pdf"))
    d = mbv.montar(arte, saida, cols=1, rows=1, tipo="so-frente",
                   vao=0, giro=giro)
    return d["deitada"]


def test_a_90_a_peca_DEITA_e_a_0_ela_fica_EM_PE(tmp_path):
    larg, alt = _cel(tmp_path, -90, "a.pdf")
    assert larg > alt, "a -90 a peca tem de deitar: %s" % ((larg, alt),)
    larg, alt = _cel(tmp_path, 0, "b.pdf")
    assert alt > larg, "a 0 a peca tem de ficar em pe: %s" % ((larg, alt),)


def test_180_fica_em_pe_como_o_0_e_mais_90_deita_como_menos_90(tmp_path):
    assert _cel(tmp_path, 180, "c.pdf") == _cel(tmp_path, 0, "d.pdf")
    assert _cel(tmp_path, 90, "e.pdf") == _cel(tmp_path, -90, "f.pdf")


def test_o_padrao_continua_sendo_a_peca_DEITADA(tmp_path):
    """Quem nao pedir giro nenhum tem de ver o que a casa ja fazia."""
    arte = _pdf(str(tmp_path / "g.pdf"), _canto, 100.0, 200.0)
    d = mbv.montar(arte, str(tmp_path / "g.out.pdf"),
                   cols=1, rows=1, tipo="so-frente", vao=0)
    assert d["deitada"] == _cel(tmp_path, -90, "h.pdf")


def test_a_peca_em_pe_MUDA_o_tamanho_da_montagem(tmp_path):
    """
    E o defeito que o operador viu: a montagem deitada estourava, e a
    em pe cabia - mas nao havia como pedir a em pe.
    """
    # 100 x 150 de proposito: numa grade 2x2 as DUAS orientacoes cabem
    # na PM 52 (util 525 x 399), entao o que se mede aqui e a forma, e
    # nao um estouro. Com 100 x 200 a em pe daria 400 de altura e o
    # motor pararia - o que e ele acertando, mas mediria outra coisa.
    arte = _pdf(str(tmp_path / "i.pdf"), _canto, 100.0, 150.0)
    deitada = mbv.montar(arte, str(tmp_path / "i1.pdf"), cols=2, rows=2,
                         tipo="so-frente", vao=0, giro=-90)
    empe = mbv.montar(arte, str(tmp_path / "i2.pdf"), cols=2, rows=2,
                      tipo="so-frente", vao=0, giro=0)
    assert deitada["montagem"] != empe["montagem"]
    # deitada da 300 x 200; em pe, 200 x 300
    assert deitada["montagem"][0] > empe["montagem"][0]
    assert empe["montagem"][1] > deitada["montagem"][1]


# --------------------------------------------------------------------------
# O VERSO DO BATE-VIRA E O ESPELHO, e nao a meia volta
# --------------------------------------------------------------------------
#
# Corrigido pelo operador em 18/09/2026, no CHECK-LIST RESSONANCIA
# MAGNETICA (A4 em pe): "o verso nao pode ser 180 graus, tem que ficar
# com 0 graus como a frente".
#
# Sao duas maquinas diferentes, e cada uma pede uma conta:
#
#   BATE-VIRA      a folha VIRA sobre o eixo VERTICAL, a pinca fica na
#                  mesma borda. E um ESPELHO: o que aponta para a direita
#                  passa a apontar para a esquerda, e o que aponta para
#                  CIMA continua para cima. Verso = -frente.
#   FRENTE E VERSO a folha TOMBA sobre o eixo horizontal. Verso = +180.
#
# Com ±90 as duas dao o MESMO numero (-(-90) = +90 = -90+180), e foi por
# isso que o erro passou meses: enquanto a peca so deitava, as duas
# contas eram indistinguiveis. So com a peca EM PE elas se separam - e
# ai o 180 poe metade da chapa de cabeca para baixo.

def _giros_das_celulas(tmp_path, giro, nome):
    """Monta um bate-vira 2x1 e devolve o giro de cada celula."""
    arte = _pdf(str(tmp_path / nome), _canto, 100.0, 150.0, paginas=2)
    vistos = []
    real = mbv.por

    def espiao(base, fonte, g, x, y):
        vistos.append(g)
        return real(base, fonte, g, x, y)

    mbv.por = espiao
    try:
        mbv.montar(arte, str(tmp_path / (nome + ".out.pdf")),
                   cols=2, rows=1, tipo="bate-vira", vao=0, giro=giro)
    finally:
        mbv.por = real
    # 'por' tambem poe as MARCAS (registro em pe, escala de cor girada),
    # e elas viriam de carona. As celulas sao as PRIMEIRAS colocacoes -
    # o laco da grade roda antes do bloco das marcas.
    return vistos[:2]


def test_a_peca_EM_PE_no_bate_vira_sai_no_MESMO_sentido(tmp_path):
    """Era o defeito que o operador viu: o verso de cabeca para baixo."""
    g = _giros_das_celulas(tmp_path, 0, "a.pdf")
    assert g == [0, 0], "frente a 0, as duas metades tem de sair a 0: %s" % g


def test_a_peca_DEITADA_continua_encontrando_cabeca_com_cabeca(tmp_path):
    """E o que a casa sempre fez, e nao pode ter mudado."""
    g = _giros_das_celulas(tmp_path, -90, "b.pdf")
    assert g == [-90, 90], "esperava -90 e +90, veio %s" % g


def test_a_meia_volta_continua_existindo_para_quem_TOMBA():
    """_meia nao morreu: e a conta do frente-e-verso, que tomba a folha."""
    assert mbv._meia(0) == 180
    assert mbv._meia(-90) == 90


# --------------------------------------------------------------------------
# O LIVRO SAI NUM PDF DE VARIAS PAGINAS - uma chapa por pagina
# --------------------------------------------------------------------------
#
# Regra do operador, 21/09/2026, depois de a montagem recusar um caderno
# de canoa: "preciso que na montagem consiga montar multiplas paginas,
# para ir caderno frente e verso, ai quando colocar PARA CTP, la sim,
# voce separa as paginas por chapa, cada pagina em uma chapa, e manda
# para o ctp".
#
# ISSO DESTRAVOU UM IMPASSE DE DEZ DIAS. A montagem recusava 'frente e
# verso' desde 11/09 dizendo que "o nome de cada arquivo de saida e
# convencao da casa que eu ainda nao tenho". A saida nao era descobrir o
# nome - era nao precisar dele: um arquivo so, com uma chapa por pagina.
# E a casa JA sabe separar (entrega.entregar_no_ctp, desde 17/09).

def _livro(caminho, paginas, larg=150.0, alt=220.0):
    """Um miolo com o numero da pagina escrito grande no meio."""
    def desenho(n):
        def d(L, A):
            return (("0 0 0 1 k 0 %.2f %.2f 12 re f\n" % (A - 12, L))
                    + ("BT /F1 90 Tf 1 0 0 1 %.2f %.2f Tm (%d) Tj ET\n"
                       % (L/2 - 30, A/2 - 30, n))).encode()
        return d
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject)
    L, A = larg / MM * PT, alt / MM * PT
    w = PdfWriter()
    for n in range(1, paginas + 1):
        p = w.add_blank_page(width=L, height=A)
        f = DecodedStreamObject()
        f.set_data(desenho(n)(L, A))
        p.replace_contents(f)
        p[NameObject("/Resources")] = DictionaryObject()
        cx = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
        p.trimbox, p.bleedbox, p.cropbox = cx, cx, cx
    with open(caminho, "wb") as fh:
        w.write(fh)
    return caminho


@pytest.fixture(scope="module")
def livro_montado(tmp_path_factory):
    """32 paginas, dois cadernos de 16 em frente e verso, canoa.

    ERA UM CADERNO DE 8 ate 21/09/2026, e mudou porque o motor passou a
    exigir a DOBRA do modelo - onde a folha cola e onde a guilhotina
    passa. Dos arranjos do catalogo, o de 8 em frente e verso e o unico
    sem essa informacao: os quatro tutoriais do Preps dao a mesma
    paginacao e DISCORDAM da dobra, e a casa nao tem modelo proprio
    dele. Ver test_paginacao.py.

    Estes testes sao sobre a ORDEM das paginas e sobre o PDF de uma
    chapa por pagina - nao sobre a dobra -, entao passaram a rodar no
    caderno de 16, que a AMERICA usa em 51 modelos. A peca encolheu para
    100 x 150 porque 16 celulas de 150 x 220 nao cabem na PM 52.
    """
    from finart_ctp import paginacao
    pasta = tmp_path_factory.mktemp("livro")
    arte = _livro(str(pasta / "miolo.pdf"), 32, larg=100.0, alt=150.0)
    d = mbv.montar_livro(arte, str(pasta / "miolo_MONTAGEM.pdf"),
                         paginas=32, por_caderno=16,
                         processo=paginacao.CANOA,
                         vira=paginacao.FRENTE_E_VERSO,
                         chapa=mbv.PM52, dpi=100, vao=5,
                         extra="MIOLO DE TESTE")
    return d


def test_o_livro_sai_num_PDF_de_UMA_CHAPA_POR_PAGINA(livro_montado):
    """Dois cadernos em frente e verso = quatro chapas = quatro paginas."""
    import pypdf
    d = livro_montado
    assert d["cadernos"] == 2
    assert d["paginas_no_pdf"] == 4
    assert len(pypdf.PdfReader(d["destino"]).pages) == 4


def test_cada_chapa_leva_a_ETIQUETA_que_vai_escrita_nela(livro_montado):
    """
    'CAD 01 FRENTE' - oito cadernos sao ate dezesseis chapas quase
    iguais na mao de quem roda, e trocar duas e um livro fora de ordem.
    """
    etiquetas = [c["etiqueta"] for c in livro_montado["chapas"]]
    assert etiquetas == ["CAD 01 FRENTE - MIOLO DE TESTE",
                         "CAD 01 VERSO - MIOLO DE TESTE",
                         "CAD 02 FRENTE - MIOLO DE TESTE",
                         "CAD 02 VERSO - MIOLO DE TESTE"]


def test_a_CANOA_poe_o_comeco_E_O_FIM_no_caderno_de_FORA(livro_montado):
    """
    E a diferenca fisica entre canoa e lombada: o grampo atravessa
    todos, entao os cadernos se ENCAIXAM e o de fora carrega as duas
    pontas do livro. Numa lombada seriam 1..8 e 9..16.
    """
    chapas = livro_montado["chapas"]
    cad1 = set(chapas[0]["paginas_do_livro"]) | set(chapas[1]["paginas_do_livro"])
    cad2 = set(chapas[2]["paginas_do_livro"]) | set(chapas[3]["paginas_do_livro"])
    assert cad1 - {0} == {1, 2, 3, 4, 5, 6, 7, 8,
                          25, 26, 27, 28, 29, 30, 31, 32}
    assert cad2 - {0} == set(range(9, 25))


def test_as_duas_paginas_de_um_LUGAR_sao_a_MESMA_FOLHA(livro_montado):
    """
    A invariante que prende o encaixe inteiro: um lugar e um pedaco de
    papel, e papel tem dois lados - a 2i-1 e a 2i. Errando um caderno,
    algum lugar passa a juntar folhas diferentes.

    O LUGAR SE ACHA PELA COLUNA ESPELHADA, desde 21/09/2026. Este teste
    casava posicao a posicao nas duas listas, e passava - porque as duas
    saiam na mesma ordem logica. Com o verso passando a ser DESENHADO
    espelhado, casar por posicao juntou 5 com 7, que nao sao a mesma
    folha, e o teste reprovou.

    Ele estava certo na invariante e errado no jeito de achar o lugar.
    A folha VIRA: a coluna 1 da frente e a coluna n do verso sao os dois
    lados do mesmo papel. Corrigido o pareamento, a invariante volta a
    valer - e agora ela cobre tambem o espelho, que antes ela nao via.
    """
    chapas = livro_montado["chapas"]
    for frente, verso in ((chapas[0], chapas[1]), (chapas[2], chapas[3])):
        cols = frente["cols"]
        do_verso = {(x["linha"], x["coluna"]): x["pagina"]
                    for x in verso["desenhadas"]}
        for x in frente["desenhadas"]:
            f = x["pagina"]
            v = do_verso.get((x["linha"], cols + 1 - x["coluna"]))
            if not f or not v:
                continue
            assert {f, v} == {2 * ((max(f, v) + 1) // 2) - 1,
                              2 * ((max(f, v) + 1) // 2)}, \
                "o lugar juntou %d com %d, que nao sao a mesma folha" % (f, v)


def test_todas_as_paginas_do_livro_saem_UMA_VEZ(livro_montado):
    todas = []
    for c in livro_montado["chapas"]:
        todas += [n for n in c["paginas_do_livro"] if n]
    assert sorted(todas) == list(range(1, 33)), \
        "pagina repetida ou faltando: %s" % sorted(todas)


def test_o_CADERNO_em_bate_vira_sai_em_UMA_CHAPA_SO(tmp_path):
    """
    Quatro paginas numa chapa: a folha passa duas vezes na MESMA.

    ISTO ERA UMA RECUSA ate 21/09/2026, e a recusa estava certa enquanto
    durou - eu tinha o par de cada lugar, mas nao qual pagina cai em
    qual POSICAO da chapa, e chutar poria metade do miolo fora de ordem
    sem dar erro nenhum.

    O que destravou foi o operador mandar o modelo E o resultado:
    '150 x 220 - Perfect Bound_SAPIENTIA.tpl' com o PDF que ele montou
    no Preps ao lado. A ultima chapa daquele arquivo - 330 x 480, quatro
    paginas - traz 227 / 226 em cima e 228 / 225 embaixo, que em
    numeracao local e 3 / 2 e 4 / 1. E o que o catalogo ja dizia.

    Gasta UMA chapa, nao duas, e e por isso que a sobra do livro sai
    assim: pedir as duas gravaria a segunda a toa e ainda daria baixa de
    chapa que ninguem usou.
    """
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "m.pdf"), 4, larg=100.0, alt=150.0)
    d = mbv.montar_livro(arte, str(tmp_path / "m_MONTAGEM.pdf"),
                         paginas=4, por_caderno=4,
                         processo=paginacao.CANOA,
                         vira=paginacao.BATE_VIRA, chapa=mbv.PM52,
                         dpi=72, vao=5, extra="SOBRA")
    assert d["paginas_no_pdf"] == 1, "bate-vira e UMA chapa"
    import pypdf
    assert len(pypdf.PdfReader(d["destino"]).pages) == 1
    chapa = d["chapas"][0]
    # na chapa nao se escreve FRENTE: ela e as duas coisas
    assert chapa["etiqueta"] == "CAD 01 BATE-VIRA - SOBRA"
    assert chapa["paginas_do_livro"] == [3, 2, 4, 1]


def test_a_montagem_de_UMA_chapa_nao_mudou(tmp_path):
    """O caminho de sempre nao pode ter regredido com o do livro."""
    arte = _pdf(str(tmp_path / "a.pdf"), _canto, 100.0, 150.0)
    d = mbv.montar(arte, str(tmp_path / "a.out.pdf"),
                   cols=2, rows=2, tipo="so-frente", vao=0)
    import pypdf
    assert len(pypdf.PdfReader(d["montagem_pdf"] if "montagem_pdf" in d
                               else str(tmp_path / "a.out.pdf")).pages) == 1


# --------------------------------------------------------------------------
# OS CADERNOS VEM DA TELA, e cada um pode ter a SUA vira
# --------------------------------------------------------------------------
#
# Ligado em 21/09/2026. O painel deixa o montador somar caderno por
# caderno, e a casa MISTURA mesmo: o MIOLO CANTICOS saiu com um caderno
# de 16 em frente e verso e um de 8 em bate-vira, que e como o miolo
# fecha com menos chapa.
#
# Recalcular aqui um por_caderno unico jogaria essa escolha fora e
# montaria um livro que ninguem pediu.

def _cadernos_da_tela():
    """A lista como o painel a manda - as chaves sao as dele."""
    from finart_ctp import paginacao
    fatias = paginacao.cadernos_do_livro(32, 16, paginacao.CANOA)
    return [
        {"numero": 1, "tipo": paginacao.FRENTE_E_VERSO, "paginas": 16,
         "repeticao": 1, "do_livro": fatias[0]},
        {"numero": 2, "tipo": paginacao.FRENTE_E_VERSO, "paginas": 16,
         "repeticao": 1, "do_livro": fatias[1]},
    ]


def test_os_cadernos_DA_TELA_mandam_na_montagem(tmp_path):
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "miolo.pdf"), 32, larg=100.0, alt=150.0)
    d = mbv.montar_livro(arte, str(tmp_path / "m_MONTAGEM.pdf"),
                         cadernos=_cadernos_da_tela(),
                         paginas=32, por_caderno=16,
                         processo=paginacao.CANOA,
                         vira=paginacao.FRENTE_E_VERSO,
                         chapa=mbv.PM52, dpi=72, vao=5)
    assert d["cadernos"] == 2 and d["paginas_no_pdf"] == 4
    # a FRENTE do caderno de FORA, na ordem das celulas do arranjo: a
    # canoa poe as duas pontas do livro no mesmo caderno, e por isso a
    # 1 e a 32 saem lado a lado nesta chapa
    primeiro = d["chapas"][0]["paginas_do_livro"]
    assert primeiro == [5, 28, 25, 8, 4, 29, 32, 1]


def test_a_DOBRA_QUE_A_CASA_NAO_TEM_para_e_diz_o_que_falta(tmp_path):
    """
    Um caderno de 16 em bate-vira nao existe em modelo nenhum da casa.

    A recusa do bate-vira em caderno caiu, mas a regra que a sustentava
    nao: dobra que ninguem leu num modelo NAO se deduz. Trocar um
    caderno de 16 para bate-vira na tela ainda para - e a mensagem diz
    quantas paginas, que vira, e o que se conhece -, porque a ordem das
    paginas de um 16 em bate-vira nunca foi lida em lugar nenhum.

    Chutar aqui poe metade do miolo fora de ordem sem dar erro nenhum:
    a chapa grava limpa e o defeito aparece depois de dobrado.
    """
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "miolo.pdf"), 32, larg=100.0, alt=150.0)
    cadernos = _cadernos_da_tela()
    cadernos[1]["tipo"] = paginacao.BATE_VIRA
    with pytest.raises(paginacao.NaoSeiPaginar) as erro:
        mbv.montar_livro(arte, str(tmp_path / "m.pdf"), cadernos=cadernos,
                         paginas=32, por_caderno=16,
                         processo=paginacao.CANOA,
                         vira=paginacao.FRENTE_E_VERSO, chapa=mbv.PM52, dpi=72)
    recado = str(erro.value)
    assert "16 paginas em bate-vira" in recado
    assert "modelo do Preps" in recado


def test_a_PAGINA_REPETIDA_na_chapa_ainda_para(tmp_path):
    """
    O caderno duplicado poe a mesma pagina mais de uma vez na chapa.
    Ignorar a repeticao sairia com celulas vazias, e inventa-la sairia
    com pagina a mais - as duas erradas sem dar erro.
    """
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "miolo.pdf"), 16)
    cadernos = _cadernos_da_tela()
    cadernos[0]["repeticao"] = 2
    with pytest.raises(SystemExit) as erro:
        mbv.montar_livro(arte, str(tmp_path / "m.pdf"), cadernos=cadernos,
                         paginas=16, por_caderno=8,
                         processo=paginacao.CANOA,
                         vira=paginacao.FRENTE_E_VERSO, chapa=mbv.PM52, dpi=72)
    assert "repetida" in str(erro.value)


# ----------------------------------------------------------------------
# A GRADE DE UM CADERNO: o vao nao e igual entre todas as celulas
# ----------------------------------------------------------------------

def test_as_colunas_do_SAPIENTIA_caem_onde_o_preps_as_poe():
    """
    22,5 / 172,5 / 327,5 / 477,5 - os numeros do modelo e do PDF montado.

    E a prova da conta inteira: peca de 150 mm, quatro colunas, folgas
    0 / 5 / 0, comecando em 22,5. Foram medidos em dois lugares
    independentes - nas coordenadas do
    '150 x 220 - Perfect Bound_SAPIENTIA.tpl' e no pixel do 'SAPIENCIA
    MONTADO.pdf' que o operador montou a mao - e batem no decimo.
    """
    import montar_bate_vira as motor
    xs = motor.passos_da_grade(22.5, 150.0, [0.0, 5.0, 0.0], 4)
    assert xs == [22.5, 172.5, 327.5, 477.5]


def test_espalhar_o_vao_por_igual_ERRA_A_DOBRA_em_1_7_mm():
    """
    O mesmo caderno com vao espalhado: 1,7 mm de erro por coluna.

    Este teste guarda o defeito que a mudanca desfez. O erro cai bem no
    lugar onde a folha dobra, grava limpo, imprime limpo, e so aparece
    depois de dobrado e cortado - que e a forma mais cara de descobrir.
    """
    import montar_bate_vira as motor
    vao_igual = 5.0 / 3.0                      # 5 mm repartidos nas 3 juncoes
    espalhado = motor.passos_da_grade(22.5, 150.0, [vao_igual] * 3, 4)
    certo = motor.passos_da_grade(22.5, 150.0, [0.0, 5.0, 0.0], 4)
    erros = [round(b - a, 2) for a, b in zip(certo, espalhado)]
    assert erros == [0.0, 1.67, -1.67, 0.0]


def test_grade_sem_folga_nenhuma_sai_encostada():
    """Folgas zeradas - ou lista vazia - poem as pecas coladas."""
    import montar_bate_vira as motor
    assert motor.passos_da_grade(0.0, 100.0, [0.0], 2) == [0.0, 100.0]
    assert motor.passos_da_grade(0.0, 100.0, [], 1) == [0.0]


def test_a_folga_a_MENOS_nao_passa_calada():
    """
    Grade de 4 colunas com 2 folgas: a quarta coluna sairia no lugar da
    terceira mais um vao, e ninguem veria.

    A conta em si aceita a lista curta (ela para de somar), e por isso
    quem chama tem de conferir o tamanho - o que montar() e
    paginacao.vaos_do_arranjo() fazem. Este teste fixa o comportamento
    da conta para que a conferencia continue sendo responsabilidade
    declarada de alguem.
    """
    import montar_bate_vira as motor
    xs = motor.passos_da_grade(0.0, 100.0, [0.0, 5.0], 4)
    assert xs == [0.0, 100.0, 205.0, 305.0]     # a ultima juncao virou 0


# ----------------------------------------------------------------------
# LIVRO NAO SE CONVERTE EM IMAGEM
# ----------------------------------------------------------------------
# Regra do operador, 21/09/2026: "no caso dos livros o procedimento sera
# outro, nao vamos converter nada em 800 dpi na hora de montar (...) as
# paginas nao serao convertidas em imagem, pq geralmente sao mais textos
# e fotos que nao dao problema".

def _tem_texto_desenhado(caminho):
    """
    O PDF ainda MANDA DESENHAR texto?

    Nao se pergunta pela FONTE declarada nos recursos: o miolo sintetico
    daqui desenha com /F1 sem declarar fonte nenhuma, e a primeira
    versao deste teste reprovou o proprio miolo por isso. O que sobrevive
    a rasterizacao e nada - depois dela ha uma imagem e mais nada -,
    entao a pergunta certa e se o operador de texto continua no fluxo.
    """
    import pypdf
    for p in pypdf.PdfReader(caminho).pages:
        if b"Tj" in p.get_contents().get_data():
            return True
    return False


def test_o_LIVRO_chega_na_chapa_COM_O_TEXTO_VIVO(tmp_path):
    """
    O miolo vai como esta: o texto continua texto na chapa.

    Rasterizar nao cria resolucao - cria peso. Num miolo, que e texto
    corrido e foto, o que se ganharia e justamente o que se perde: texto
    vetorial em corpo pequeno vira pixel e piora.
    """
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "miolo.pdf"), 4, larg=100.0, alt=150.0)
    assert _tem_texto_desenhado(arte), "o miolo de teste precisa ter texto"
    d = mbv.montar_livro(arte, str(tmp_path / "m_MONTAGEM.pdf"),
                         paginas=4, por_caderno=4,
                         processo=paginacao.CANOA,
                         vira=paginacao.BATE_VIRA, chapa=mbv.PM52,
                         dpi=72, vao=5)
    assert _tem_texto_desenhado(d["destino"]), \
        "a chapa do livro saiu sem fonte nenhuma - foi convertida em imagem"


def test_o_LIVRO_converte_QUANDO_LHE_PEDEM(tmp_path):
    """
    O padrao e nao converter, mas a escolha continua sendo de quem monta.

    'depende do miolo, eu digo na hora' - entao a tela pergunta, e o
    programa nao decide por ela.
    """
    from finart_ctp import paginacao
    arte = _livro(str(tmp_path / "miolo.pdf"), 4, larg=100.0, alt=150.0)
    d = mbv.montar_livro(arte, str(tmp_path / "m_MONTAGEM.pdf"),
                         paginas=4, por_caderno=4,
                         processo=paginacao.CANOA,
                         vira=paginacao.BATE_VIRA, chapa=mbv.PM52,
                         dpi=72, vao=5, em_imagem=True)
    assert not _tem_texto_desenhado(d["destino"]), \
        "pediram em imagem e o texto continuou vivo"


def test_a_FOLHA_SOLTA_continua_convertendo(tmp_path):
    """
    A regra do livro nao vale para a folha solta, e este teste guarda
    isso: ali a arte vem de designer e converter e o que impede fonte
    que falta, transparencia que achata errado e vetor que engasga o RIP.
    """
    arte = _livro(str(tmp_path / "a.pdf"), 1, larg=100.0, alt=150.0)
    saida = str(tmp_path / "a.out.pdf")
    mbv.montar(arte, saida, cols=2, rows=2, tipo="so-frente", vao=5, dpi=72)
    assert not _tem_texto_desenhado(saida), \
        "a folha solta deixou de converter em imagem"


def _miolo_com_tarja_fora_do_corte(caminho, paginas=4):
    """
    Um miolo cuja folha e MAIOR que o corte, com tinta la fora.

    E o que chega de verdade quando o designer deixa marca de corte ou
    recado de servico na margem: a folha tem 140 x 190 e o corte, 100 x
    150. A tarja ocupa a margem esquerda inteira.
    """
    import pypdf
    from pypdf.generic import (ArrayObject, DecodedStreamObject,
                               DictionaryObject, FloatObject, NameObject)
    L, A = 100.0 / MM * PT, 150.0 / MM * PT
    MARGEM = 20.0 / MM * PT
    w = pypdf.PdfWriter()
    for _ in range(paginas):
        p = w.add_blank_page(width=L + 2 * MARGEM, height=A + 2 * MARGEM)
        f = DecodedStreamObject()
        f.set_data((("0 0 0 1 k %.2f %.2f 40 40 re f"
                     % (MARGEM + 10, MARGEM + 10))
                    + chr(10)
                    + ("0 0 0 1 k 0 0 %.2f %.2f re f"
                       % (MARGEM, A + 2 * MARGEM))).encode())
        p.replace_contents(f)
        p[NameObject("/Resources")] = DictionaryObject()
        corte = ArrayObject([FloatObject(v) for v in
                             (MARGEM, MARGEM, MARGEM + L, MARGEM + A)])
        p.trimbox, p.bleedbox, p.cropbox = corte, corte, corte
    with open(caminho, "wb") as fh:
        w.write(fh)
    return caminho


def _tinta_da_pagina(pdf, caminho_png, dpi=24):
    """A tinta do PDF, em pixel - (matriz, px_por_mm)."""
    import numpy as np
    mbv._rodar(mbv.GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
               "-sDEVICE=pnggray", "-r%d" % dpi, "-dFirstPage=1",
               "-dLastPage=1", "-sOutputFile=" + caminho_png, pdf)
    a = 255 - np.asarray(Image.open(caminho_png).convert("L"), dtype=float)
    return a > 40, dpi / 25.4


def test_a_PECA_DO_LIVRO_sai_recortada_no_corte(tmp_path):
    """
    A peca sai com a medida do CORTE, e sem a tinta que mora fora dele.

    Rasterizando, quem recortava era o Ghostscript com -dUseBleedBox.
    Sem ele eu supus que bastava trocar a mediabox - e nao basta: o
    pypdf NAO embrulha a pagina num Form ao mescla-la, ele CONCATENA o
    fluxo dela na chapa, e fluxo concatenado nao tem caixa. O que
    estivesse fora do corte entraria de carona e cairia na pagina
    vizinha, que numa dobra esta ENCOSTADA.

    A casa ja sabia disto noutro lugar: sangrar._recortar faz o mesmo
    clip, pelo mesmo motivo. So que ele so roda quando a sangria precisa
    ser mexida - e num livro ela e 0, entao nao roda.
    """
    import pypdf
    arte = _miolo_com_tarja_fora_do_corte(str(tmp_path / "miolo.pdf"))
    peca = mbv.peca_como_esta(arte, 1, str(tmp_path / "peca.pdf"))

    p = pypdf.PdfReader(peca).pages[0]
    assert (round(float(p.mediabox.width) / PT * MM, 1),
            round(float(p.mediabox.height) / PT * MM, 1)) == (100.0, 150.0)

    tinta, px = _tinta_da_pagina(peca, str(tmp_path / "peca.png"))
    # a tarja atravessava a folha de cima a baixo; sobrando dela alguma
    # coisa, havera coluna de pixel cheia
    cheias = [x for x in range(tinta.shape[1])
              if tinta[:, x].mean() > 0.9]
    assert not cheias, (
        "sobrou coluna cheia de tinta em x=%s mm - a tarja de fora do "
        "corte entrou na peca" % [round(x / px, 1) for x in cheias])
    assert tinta.any(), "a peca saiu em branco; o teste nao prova nada"


def test_o_LIVRO_MONTADO_nao_leva_a_tinta_de_fora_do_corte(tmp_path):
    """
    O mesmo, ja na chapa: a peca encostada nao recebe tinta da vizinha.

    Numa grade 2x2 de 100 x 150 na PM 52 as colunas ficam em 162,5 e
    262,5, encostadas - ali e dobra. A tarja da coluna 2 cairia de 242,5
    a 262,5, bem dentro da coluna 1.
    """
    from finart_ctp import paginacao
    arte = _miolo_com_tarja_fora_do_corte(str(tmp_path / "miolo.pdf"))
    saida = str(tmp_path / "m_MONTAGEM.pdf")
    mbv.montar_livro(arte, saida, paginas=4, por_caderno=4,
                     processo=paginacao.CANOA, vira=paginacao.BATE_VIRA,
                     chapa=mbv.PM52, dpi=72, vao=5)

    tinta, px = _tinta_da_pagina(saida, str(tmp_path / "chapa.png"))
    alt = tinta.shape[0]
    invadida = tinta[int(alt - 205 * px):int(alt - 65 * px),
                     int(243 * px):int(261 * px)]
    assert invadida.mean() < 0.05, (
        "%.0f%% da faixa tem tinta - a tarja da coluna 2 caiu na coluna 1"
        % (invadida.mean() * 100))


def test_o_VERSO_do_caderno_sai_ESPELHADO(tmp_path):
    """
    A folha VIRA entre a chapa da frente e a do verso: o que estava na
    coluna 1 passa a estar na ULTIMA quando ela volta. Entao a pagina do
    verso tem de ser desenhada na coluna espelhada, ou toda pagina cai
    atras da pagina errada.

    Pedido do operador em 21/09/2026, olhando a primeira montagem de
    teste do Sapientia: "a montagem tem de ser espelhada para bater
    frente e verso automatico".

    Sem o espelho a chapa saia assim, e nada acusava:

        frente   5  12   9   8
        verso    6  11  10   7

    A 6 e o verso da 5 e ia cair atras da 8. A chapa grava limpa, a
    folha imprime limpa, e o erro so aparece na dobra - com a tiragem
    pronta e o papel gasto.

    CONFERE PELO PAR, que e o que importa: a coluna c da frente e a
    coluna (n+1-c) do verso sao os dois lados da MESMA folhinha, entao
    as paginas delas tem de ser consecutivas.
    """
    from finart_ctp import paginacao

    origem = str(tmp_path / "miolo.pdf")
    _pdf(origem, _canto, 150.0, 220.0, paginas=16)

    d = mbv.montar_livro(
        origem, str(tmp_path / "cad_MONTAGEM.pdf"),
        paginas=16, por_caderno=16,
        processo=paginacao.LOMBADA, vira="frente e verso",
        chapa=mbv.MOZP,
        cadernos=[{"numero": 1, "do_livro": list(range(1, 17)),
                   "tipo": "frente e verso"}])

    chapas = {c["lado"]: c for c in d["chapas"]}
    assert set(chapas) == {"frente", "verso"}

    def por_lugar(chapa):
        return {(x["linha"], x["coluna"]): x["pagina"]
                for x in chapa["desenhadas"]}

    frente, verso = por_lugar(chapas["frente"]), por_lugar(chapas["verso"])
    cols = chapas["frente"]["cols"]
    assert frente and len(frente) == len(verso)

    for (linha, coluna), pag_f in frente.items():
        pag_v = verso[(linha, cols + 1 - coluna)]
        assert abs(pag_f - pag_v) == 1, (
            "a pagina %d (linha %d, coluna %d) tem o verso %d - nao sao "
            "consecutivas, entao a folha nao bate"
            % (pag_f, linha, coluna, pag_v))

    # a etiqueta e a que o operador pediu, sem enfeite
    assert chapas["frente"]["etiqueta"] == "CAD 01 FRENTE"
    assert chapas["verso"]["etiqueta"] == "CAD 01 VERSO"


def test_o_relato_do_caderno_le_a_CHAPA_e_nao_a_lista(tmp_path):
    """
    'paginas_do_livro' sai na ordem em que as paginas estao NA CHAPA.

    Ate 21/09/2026 ele saia na ordem logica dos lugares, e no teste do
    espelho isso mentiu: o relato do verso mostrava 6 11 10 7 enquanto a
    chapa, ja espelhada, tinha 7 10 11 6. Relatorio que refaz a conta
    por fora acaba discordando do que foi desenhado - e quem confere
    olha o relatorio.
    """
    from finart_ctp import paginacao

    origem = str(tmp_path / "miolo.pdf")
    _pdf(origem, _canto, 150.0, 220.0, paginas=16)

    d = mbv.montar_livro(
        origem, str(tmp_path / "cad_MONTAGEM.pdf"),
        paginas=16, por_caderno=16,
        processo=paginacao.LOMBADA, vira="frente e verso",
        chapa=mbv.MOZP,
        cadernos=[{"numero": 1, "do_livro": list(range(1, 17)),
                   "tipo": "frente e verso"}])

    for c in d["chapas"]:
        da_chapa = [x["pagina"] for x in sorted(
            c["desenhadas"], key=lambda x: (-x["linha"], x["coluna"]))]
        assert c["paginas_do_livro"] == da_chapa
