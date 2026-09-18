# -*- coding: utf-8 -*-
"""O preto cheio sobrepoe, e so ele.

O caso, 18/09/2026: o 'Timbrado Traumat' saiu da montagem com o rodape
- texto preto sobre uma barra verde chapada (C 67, Y 19) - RECORTANDO o
verde. Na chapa do ciano, o texto aparecia vazado em branco; qualquer
desvio de registro na maquina viraria um fio branco em volta de cada
letra. O operador viu e disse: "sempre o preto fique sobreposto, quando
ele for 100% nao pode vazar nas outras cores".

Medido no arquivo: 19.860 pixels de preto forte, TODOS com C=M=Y=0, e o
anel de 3 px em volta deles com 100% de cor.

O que estes testes prendem:

  1. so o preto CHEIO ganha sobreposicao - o de 70% do proprio Timbrado
     fica de fora, e cor nenhuma entra;
  2. o desliga existe e e obrigatorio: sem ele a cor seguinte herdaria o
     '/OP true' do preto anterior, porque o estado anda colado na cor;
  3. quem le o PDF acha a sobreposicao (e por isso a montagem sabe
     trocar de modo de rasterizacao);
  4. o desenho nao muda - so o estado grafico entra no fluxo.

A arte de cliente nao vai para o git, entao os PDFs aqui sao sinteticos.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ferramentas"))

from finart_ctp.sobreposicao import (DESLIGA, LIGA,  # noqa: E402
                                     sobrepor_preto)
import montar_bate_vira as mbv                       # noqa: E402

MM, PT = 25.4, 72.0


def _pdf(caminho, desenho, larg_mm=100.0, alt_mm=60.0):
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject
    L, A = larg_mm / MM * PT, alt_mm / MM * PT
    w = PdfWriter()
    p = w.add_blank_page(width=L, height=A)
    f = DecodedStreamObject()
    f.set_data(desenho(L, A))
    p.replace_contents(f)
    cx = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
    p.trimbox, p.bleedbox, p.cropbox = cx, cx, cx
    with open(caminho, "wb") as fh:
        w.write(fh)
    return caminho


def _rodape(L, A):
    """O caso de verdade: barra verde chapada com texto preto por cima."""
    return (("0.67 0 0.19 0 k 0 0 %.2f %.2f re f\n" % (L, A))      # o verde
            + ("0 0 0 1 k 10 10 %.2f 20 re f\n" % (L - 20))        # o preto
            ).encode()


def _so_cor(L, A):
    return ("0.67 0 0.19 0 k 0 0 %.2f %.2f re f\n" % (L, A)).encode()


def _preto_fraco(L, A):
    """Preto de 70% - o proprio Timbrado tem, e ele NAO sobrepoe."""
    return (("0.67 0 0.19 0 k 0 0 %.2f %.2f re f\n" % (L, A))
            + ("0 0 0 0.7 k 10 10 %.2f 20 re f\n" % (L - 20))).encode()


def _fluxo(pdf):
    import pypdf
    return pypdf.PdfReader(pdf).pages[0].get_contents().get_data()


def test_o_preto_cheio_ganha_sobreposicao(tmp_path):
    arte = _pdf(str(tmp_path / "a.pdf"), _rodape)
    saida = str(tmp_path / "a.op.pdf")
    assert sobrepor_preto(arte, saida) == 1
    d = _fluxo(saida)
    assert d.count(LIGA.encode()) == 1, "o preto cheio nao ligou"
    assert d.count(DESLIGA.encode()) == 1, "o verde nao desligou"


def test_cor_nenhuma_sobrepoe(tmp_path):
    """Cor clara sobreposta nao cobre: ela MISTURA, e sai outra cor."""
    arte = _pdf(str(tmp_path / "b.pdf"), _so_cor)
    saida = str(tmp_path / "b.op.pdf")
    assert sobrepor_preto(arte, saida) == 0
    d = _fluxo(saida)
    assert LIGA.encode() not in d
    assert d.count(DESLIGA.encode()) == 1


def test_o_preto_de_70_por_cento_NAO_sobrepoe(tmp_path):
    """O operador falou em 100%. Cinza sobreposto misturaria igual."""
    arte = _pdf(str(tmp_path / "c.pdf"), _preto_fraco)
    saida = str(tmp_path / "c.op.pdf")
    assert sobrepor_preto(arte, saida) == 0


def test_o_limite_e_quem_manda(tmp_path):
    """Baixando o corte, o mesmo 70% passa a contar."""
    arte = _pdf(str(tmp_path / "d.pdf"), _preto_fraco)
    assert sobrepor_preto(arte, str(tmp_path / "d1.pdf"), limite=95) == 0
    assert sobrepor_preto(arte, str(tmp_path / "d2.pdf"), limite=60) == 1


def test_o_DESLIGA_existe_para_a_cor_nao_herdar(tmp_path):
    """
    O estado anda colado na ULTIMA cor escolhida - e de proposito, para
    nao ter de rastrear q/Q. Sem o desliga, o verde pintado depois do
    preto herdaria o '/OP true' dele.
    """
    def dois(L, A):
        return (("0 0 0 1 k 0 0 10 10 re f\n")
                + ("0.67 0 0.19 0 k 20 20 30 30 re f\n")).encode()
    arte = _pdf(str(tmp_path / "e.pdf"), dois)
    saida = str(tmp_path / "e.op.pdf")
    sobrepor_preto(arte, saida)
    d = _fluxo(saida)
    i_liga, i_desliga = d.index(LIGA.encode()), d.index(DESLIGA.encode())
    assert i_liga < i_desliga, "o desliga tem de vir DEPOIS, na cor seguinte"


def test_o_desenho_nao_muda(tmp_path):
    """So entra estado grafico: nenhum 're' ou 'f' a mais ou a menos."""
    arte = _pdf(str(tmp_path / "f.pdf"), _rodape)
    saida = str(tmp_path / "f.op.pdf")
    antes, _ = _fluxo(arte), sobrepor_preto(arte, saida)
    depois = _fluxo(saida)
    for op in (b" re", b" f", b" k"):
        assert antes.count(op) == depois.count(op), \
            "mudou a contagem de %r" % op


def test_a_montagem_RECONHECE_o_pdf_com_sobreposicao(tmp_path):
    """
    E o que faz a rasterizacao trocar de modo: com sobreposicao
    declarada, o -dUseFastColor SAI (ele desliga o pipeline de cor e o
    Ghostscript ignora o overprint) e entra o -sOverprint=simulate.
    """
    arte = _pdf(str(tmp_path / "g.pdf"), _rodape)
    saida = str(tmp_path / "g.op.pdf")
    assert mbv.tem_sobreposicao(arte) is False
    sobrepor_preto(arte, saida)
    assert mbv.tem_sobreposicao(saida) is True


@pytest.mark.parametrize("desenho,espera", [(_rodape, 1), (_so_cor, 0)])
def test_o_pdf_continua_legivel(tmp_path, desenho, espera):
    import pypdf
    arte = _pdf(str(tmp_path / "h.pdf"), desenho)
    saida = str(tmp_path / "h.op.pdf")
    assert sobrepor_preto(arte, saida) == espera
    r = pypdf.PdfReader(saida)
    assert len(r.pages) == 1
    gs = r.pages[0]["/Resources"].get_object()["/ExtGState"].get_object()
    assert LIGA in gs and DESLIGA in gs


# --------------------------------------------------------------------------
# A COR SE PERGUNTA AO QUE ESTA DENTRO DO CORTE
# --------------------------------------------------------------------------
#
# Regra do operador, 18/09/2026: "voce analisa somente o arquivo, as
# marcas de corte geralmente ficam nas 4 cores mesmo, mas se o arquivo
# for somente no preto, gera a OS com 1 chapa so, e o nome do arquivo em
# GRAY".
#
# Quase todo PDF fechado por designer traz as marcas DELE em cor de
# registro - CMYK a 100% -, fora do corte, onde nada imprime. Contando a
# pagina inteira, arte de preto puro responde 'quatro tintas': quatro
# chapas gravadas e cobradas onde devia sair UMA.

def _pdf_com_marcas(caminho):
    """
    Arte de PRETO PURO, com marcas de registro CMYK fora do corte.

    MediaBox 120x80, TrimBox 100x60 - a moldura de 10 mm em volta e onde
    as marcas do designer vivem.
    """
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject
    L, A = 120 / MM * PT, 80 / MM * PT
    m = 10 / MM * PT
    w = PdfWriter()
    p = w.add_blank_page(width=L, height=A)
    d = (
        # a ARTE: preto puro, dentro do corte
        ("0 0 0 1 k %.2f %.2f %.2f %.2f re f\n" % (m + 5, m + 5, 60, 30))
        # as MARCAS: cor de registro, fora do corte
        + ("1 1 1 1 k 2 2 %.2f 3 re f\n" % (L - 4))
        + ("1 1 1 1 k 2 %.2f %.2f 3 re f\n" % (A - 5, L - 4))
    ).encode()
    f = DecodedStreamObject(); f.set_data(d)
    p.replace_contents(f)
    # A CROPBOX FICA NA MEDIABOX, e nao no corte - senao o Ghostscript ja
    # recortaria as marcas por conta propria e o gabarito nao teria o
    # defeito que ele existe para mostrar.
    caixa = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
    corte = ArrayObject([FloatObject(v) for v in (m, m, L - m, A - m)])
    p.mediabox, p.cropbox = caixa, caixa
    p.trimbox, p.bleedbox = corte, corte
    with open(caminho, "wb") as fh:
        w.write(fh)
    return caminho


def test_a_pagina_inteira_ACUSA_quatro_tintas_por_causa_das_marcas(tmp_path):
    """O defeito, medido: e a leitura que fazia sair quatro chapas."""
    from finart_ctp.ghostscript import cobertura_por_pagina, tintas_da_cobertura
    arte = _pdf_com_marcas(str(tmp_path / "a.pdf"))
    cob = cobertura_por_pagina(arte, sem_icc=True)[0]
    assert tintas_da_cobertura(cob) == {"C", "M", "Y", "K"}


def test_DENTRO_DO_CORTE_a_mesma_arte_e_so_PRETO(tmp_path):
    from finart_ctp.ghostscript import cobertura_por_pagina, tintas_da_cobertura
    arte = _pdf_com_marcas(str(tmp_path / "b.pdf"))
    cob = cobertura_por_pagina(arte, sem_icc=True, so_o_corte=True)[0]
    assert tintas_da_cobertura(cob) == {"K"}, cob


def test_e_e_isso_que_a_AMERICA_passa_a_medir(tmp_path):
    """medir() decide a sugestao de cor da tela, e por ela a OS."""
    from finart_ctp import america
    arte = _pdf_com_marcas(str(tmp_path / "c.pdf"))
    _, _, tintas = america.medir(arte)
    assert tintas == {"K"}
    assert america.e_preto_e_branco(tintas) is True, "sairia com 4 chapas"
