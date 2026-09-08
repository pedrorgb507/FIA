# -*- coding: utf-8 -*-
"""
CREATIVE: a arte chega MENOR que a chapa e o programa a monta nela.

Ate aqui todo cliente mandava a arte ja no tamanho da chapa. A Creative
manda 480x330 para uma chapa de 510x400, e quem monta - centralizando na
largura e deixando a pinca no pe - era o operador, no InDesign.

As medidas foram tiradas da chapa que ele fechou a mao em 02/09/2026,
'510x400_CMYK_CREATIVE_santinho cruvinel': arte de 480x330 com 15 mm de
cada lado e 41,9 mm no pe.
"""

import os

import pytest

import finart_ctp.monitor as M
from finart_ctp.nomes import nome_saida_creative
from finart_ctp.processador import (CREATIVE, EMPORIO, SOLIDA, chapa_da_pagina,
                                    montar_na_chapa, pinca_do_cliente,
                                    posicao_na_chapa, rotulo_prova)

ARTE = "santinho cruvinel.pdf"


# ----------------------------------------------------------------------
# A conta da pinca
# ----------------------------------------------------------------------

def test_a_arte_menor_ganha_a_chapa_de_510x400():
    chapa, dpi, sufixo, montou = chapa_da_pagina(480, 330, CREATIVE)
    assert chapa == (510, 400)
    assert dpi == 1000
    assert montou, "precisa avisar que a arte foi MONTADA, nao so aceita"


def test_a_pinca_se_mede_da_marca_de_corte_e_nao_da_borda():
    """
    O erro que o operador pegou na primeira versao: a arte foi posta a
    40 mm da BORDA do arquivo, e a marca de corte - 12 mm para dentro -
    acabou a 52 mm. Ficaram 12 mm de pinca a mais, e a chapa foi refeita.
    """
    esquerda, topo = posicao_na_chapa(480, 330, (510, 400), CREATIVE,
                                      corte=12.0)
    assert esquerda == 15.0, "a sobra da largura se divide igual"

    borda_da_arte = 400 - topo - 330
    assert borda_da_arte == 28.0, "40 de pinca menos os 12 da marca"

    marca = borda_da_arte + 12.0
    assert marca == pinca_do_cliente(CREATIVE) == 40,         "a MARCA e que tem de ficar nos 40 mm"


def test_medir_da_borda_poria_a_marca_no_lugar_errado():
    """Guarda a diferenca entre as duas contas, para nao voltar atras."""
    _, com_marca = posicao_na_chapa(480, 330, (510, 400), CREATIVE, corte=12.0)
    _, sem_marca = posicao_na_chapa(480, 330, (510, 400), CREATIVE, corte=0.0)
    assert abs(com_marca - sem_marca) == 12.0


def test_bate_com_a_chapa_que_o_operador_fechou_a_mao():
    """
    A chapa do dia 02, medida por dentro do arquivo: arte de 480x330 com
    15,0 mm de cada lado e a borda da arte a 28,0 mm da borda da chapa do
    lado da pinca. A regra tem de cair em cima disso.
    """
    esquerda, topo = posicao_na_chapa(480, 330, (510, 400), CREATIVE,
                                      corte=12.0)
    borda_da_arte = 400 - topo - 330
    assert abs(esquerda - 15.0) < 0.5
    assert abs(borda_da_arte - 28.0) <= 0.5


def test_arte_alta_demais_nao_cabe_com_a_pinca():
    """
    370 de arte + 40 de pinca = 410 numa chapa de 400. Nao cabe - e
    empurrar a arte para dentro da pinca e entregar servico que a
    maquina nao consegue segurar.
    """
    assert montar_na_chapa(480, 370, CREATIVE) is None
    assert chapa_da_pagina(480, 370, CREATIVE)[1] is None


def test_arte_larga_demais_nao_cabe():
    assert montar_na_chapa(520, 300, CREATIVE) is None


def test_arte_no_limite_ainda_cabe():
    """360 + 40 = 400, exatamente a chapa."""
    assert montar_na_chapa(510, 360, CREATIVE) == (510, 400)
    esquerda, topo = posicao_na_chapa(510, 360, (510, 400), CREATIVE)
    assert (esquerda, topo) == (0.0, 0)


def test_a_marca_faz_caber_o_que_nao_cabia():
    """
    370 de arte nao cabe medindo da borda (370 + 40 = 410 numa chapa de
    400). Com a marca 12 mm para dentro, o que a arte gasta abaixo dela
    sao 28 mm: 370 + 28 = 398, e cabe.
    """
    assert montar_na_chapa(480, 370, CREATIVE) is None
    assert montar_na_chapa(480, 370, CREATIVE, corte=12.0) == (510, 400)


def test_marca_fundo_demais_nao_monta():
    """
    Marca a 45 mm da borda, com pinca de 40: a arte teria de comecar 5 mm
    ABAIXO do pe da chapa. Nao existe - vira pendencia.
    """
    assert montar_na_chapa(480, 330, CREATIVE, corte=45.0) is None


def test_a_arte_nao_e_reduzida_para_caber():
    """
    Reduzir a arte moveria o corte: o cliente pediu 480 mm e tem de sair
    480 mm. O que nao cabe vira pendencia, nao vira arte menor.
    """
    esquerda, topo = posicao_na_chapa(480, 330, (510, 400), CREATIVE)
    assert 480 + 2 * esquerda == 510
    assert 330 + topo + pinca_do_cliente(CREATIVE) == 400


# ----------------------------------------------------------------------
# So a Creative tem pinca
# ----------------------------------------------------------------------

def test_os_outros_clientes_nao_ganharam_pinca():
    for cliente in (SOLIDA, EMPORIO, "VIVA", "FIALHO", "VOPRIX"):
        assert pinca_do_cliente(cliente) == 0
        assert montar_na_chapa(480, 330, cliente) is None


def test_arte_menor_em_outro_cliente_continua_parando():
    """
    Na Solida, arte de 480x330 nunca foi chapa e continua nao sendo -
    montar sozinho o que ninguem pediu e pior do que parar.
    """
    assert chapa_da_pagina(480, 330, SOLIDA)[1] is None
    assert chapa_da_pagina(480, 330, EMPORIO)[1] is None


# ----------------------------------------------------------------------
# Nome e etiqueta
# ----------------------------------------------------------------------

def test_o_nome_sai_como_o_operador_escreve():
    assert (nome_saida_creative(ARTE, "510x400", set("CMYK"))
            == "510x400_CMYK_CREATIVE_santinho cruvinel")


def test_o_nome_leva_o_formato_da_CHAPA_e_nao_o_da_arte():
    """Quem grava precisa saber o que vai para a maquina: uma 510x400."""
    nome = nome_saida_creative(ARTE, "510x400", set("CMYK"))
    assert nome.startswith("510x400_")
    assert "480" not in nome


def test_frente_e_verso_saem_F_e_V():
    assert nome_saida_creative(ARTE, "510x400", set("CMYK"), 0, 2).endswith(" F")
    assert nome_saida_creative(ARTE, "510x400", set("CMYK"), 1, 2).endswith(" V")


def test_arte_de_uma_cor_sai_GRAY():
    assert "_GRAY_" in nome_saida_creative(ARTE, "510x400", {"GRAY"})


def test_acento_cai_do_nome():
    assert "CAO" in nome_saida_creative("comunicação.pdf", "510x400",
                                        set("CMYK")).upper()


def test_a_etiqueta_da_prova_diz_o_cliente():
    assert rotulo_prova(510, 400, CREATIVE) == "CREATIVE F4"


# ----------------------------------------------------------------------
# A pasta entra no laco
# ----------------------------------------------------------------------

def test_o_monitor_vigia_a_creative(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", r"V:\Creative")
    lista = M.clientes()
    creative = [c for c in lista if c[0] == M.CREATIVE]
    assert creative, "a pasta da Creative nao entrou no laco"
    assert creative[0][2] == (".pdf",), "a Creative so manda PDF"


def test_sem_a_pasta_configurada_ninguem_vigia(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", None)
    assert not [c for c in M.clientes() if c[0] == M.CREATIVE]
