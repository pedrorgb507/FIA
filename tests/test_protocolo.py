# -*- coding: utf-8 -*-
r"""
O protocolo de entrega - o papel que o cliente assina.

O desenho nao foi inventado: saiu do U:\ZAP PROT ENTREGA.rpf, um
protocolo renderizado de verdade pelo proprio GEREMPRE (OS 16577, ZAP
CARTOES, 30/04/2026), de onde vieram os 104 campos com posicao exata.

Estes testes cuidam do que o papel PRECISA dizer, e nao de pixel: valor
certo, as quatro vagas, as duas vias, e nenhum campo escrevendo por cima
do outro.
"""

import datetime

from finart_ctp import protocolo


def dados(itens=None, **extra):
    d = {
        "numero": 19605,
        "entrada": datetime.date(2026, 9, 10),
        "entrega": datetime.date(2026, 9, 10),
        "cliente": "SOLIDA GRAFICA (SOLIDA GRAFICA EDITORA LTDA)",
        "contato": "GUSTAVO / EDUARDO",
        "telefone": "(62) 3280-3808",
        "endereco": "",
        "responsavel": "FIA",
        "total_geral": 192.0,
        "itens": itens if itens is not None else [vaga(1)],
    }
    d.update(extra)
    return d


def vaga(n, **extra):
    v = {"vaga": n, "material": "SOLIDA FT4", "codigo": 98,
         "alt": 510.0, "lar": 400.0, "montagem": "F4",
         "frente": 1, "verso": 0, "quantas": 4,
         "titulo": "49758 - BRUNO PEIXOTO - BOTTONS", "obs": "",
         "unitario": 9.0, "total": 36.0}
    v.update(extra)
    return v


# ----------------------------------------------------------------------
# O que o papel diz
# ----------------------------------------------------------------------

def test_dinheiro_sai_com_virgula():
    """O papel e brasileiro."""
    assert protocolo._dinheiro(35) == "35,00"
    assert protocolo._dinheiro(192.0) == "192,00"
    assert protocolo._dinheiro(None) == "0,00"
    assert protocolo._dinheiro(8.5) == "8,50"


def test_o_produto_sai_no_feitio_do_gerempre():
    """
    '1 - 720X557 - 0,30 720 X 557 - F2 - 1 X 0', lido do relatorio de
    verdade: vaga, material, medida, montagem, cores frente X verso.
    """
    linha = protocolo._produto(vaga(1))
    assert linha == "1 - SOLIDA FT4 510 X 400 - F4 - 1 X 0"


def test_a_medida_sai_inteira():
    """A OS guarda 510.00; o papel mostra 510."""
    assert "510 X 400" in protocolo._produto(vaga(1))
    assert "510.0" not in protocolo._produto(vaga(1))


# ----------------------------------------------------------------------
# A folha
# ----------------------------------------------------------------------

def test_a_folha_e_a4_em_pe():
    im = protocolo.folha(dados(), dpi=100)
    larg_mm = im.width / 100.0 * 25.4
    alt_mm = im.height / 100.0 * 25.4
    assert abs(larg_mm - 210) < 1.5
    assert abs(alt_mm - 297) < 1.5
    assert im.height > im.width, "em pe"


def test_saem_as_duas_vias():
    """
    O relatorio repete tudo 467 unidades abaixo - a via do cliente e a da
    casa, para destacar. Uma via so nao serve: nao sobra recibo para
    ninguem.
    """
    assert protocolo.SEGUNDA_VIA == 467
    im = protocolo.folha(dados(), dpi=100)
    escala = 100 / protocolo.DPI_RPF
    # o titulo da segunda via cai dentro da folha
    y = (80 + protocolo.SEGUNDA_VIA) * escala
    assert y < im.height, "a segunda via tem de caber no papel"


def test_as_quatro_vagas_cabem():
    im = protocolo.folha(dados(itens=[vaga(n) for n in (1, 2, 3, 4)]),
                         dpi=100)
    assert im is not None
    assert len(protocolo.BLOCOS_Y) == 4


def test_vaga_vazia_nao_derruba_a_folha():
    """
    O GEREMPRE imprime os quatro blocos sempre, cheios ou vazios. Uma OS
    de um servico so tem de sair igual - com os rotulos e zero.
    """
    im = protocolo.folha(dados(itens=[vaga(1)]), dpi=100)
    assert im is not None


def test_os_sem_item_nenhum_ainda_da_papel():
    """Nao e para explodir: o papel sai em branco e alguem ve."""
    assert protocolo.folha(dados(itens=[]), dpi=100) is not None


# ----------------------------------------------------------------------
# Nenhum campo escreve por cima do outro
# ----------------------------------------------------------------------

def test_nome_comprido_de_cliente_nao_invade_o_contato():
    """
    'SOLIDA GRAFICA (SOLIDA GRAFICA EDITORA LTDA)' nao cabe na coluna, e
    sem corte escrevia por cima do rotulo CONTATO - justo na linha que o
    cliente le primeiro.
    """
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (10, 10), "white")
    tinta = ImageDraw.Draw(im)
    fonte = protocolo._fonte(11)

    largura = 100.0
    cortado = protocolo._cortar(tinta, "S" * 400, fonte, largura)
    assert tinta.textlength(cortado, font=fonte) <= largura
    assert cortado.endswith("...")


def test_o_que_cabe_nao_e_cortado():
    from PIL import Image, ImageDraw
    tinta = ImageDraw.Draw(Image.new("RGB", (10, 10), "white"))
    fonte = protocolo._fonte(11)
    assert protocolo._cortar(tinta, "FIA", fonte, 500.0) == "FIA"


def test_campo_vazio_nao_vira_reticencia():
    from PIL import Image, ImageDraw
    tinta = ImageDraw.Draw(Image.new("RGB", (10, 10), "white"))
    fonte = protocolo._fonte(11)
    assert protocolo._cortar(tinta, "", fonte, 10.0) == ""
    assert protocolo._cortar(tinta, None, fonte, 10.0) == ""
