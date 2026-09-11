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
    assert marca == pinca_do_cliente(CREATIVE) == 40, (
        "a MARCA e que tem de ficar nos 40 mm")


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
    assert creative[0][2] == (".pdf", ".cdr"), (
        "o .cdr entra so para virar pendencia, como no Fialho")


def test_sem_a_pasta_configurada_ninguem_vigia(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", None)
    assert not [c for c in M.clientes() if c[0] == M.CREATIVE]


# ----------------------------------------------------------------------
# Arte que chega EM PE
# ----------------------------------------------------------------------

def test_arte_em_pe_e_girada_para_deitar():
    """
    'se o arquivo vier em pe, voce deve so rotacionar ele e deixar da
    forma que sempre vem'. Deitada ja, nao se mexe.
    """
    from finart_ctp.processador import giro_da_pagina

    assert giro_da_pagina(330, 480, CREATIVE) == 270, (
        "em pe: gira para a ESQUERDA, como o operador pediu")
    assert giro_da_pagina(480, 330, CREATIVE) == 0, "deitada: nao mexer"


def test_so_a_creative_gira():
    """
    Nos outros clientes a arte chega no tamanho da chapa e girar seria
    estragar. Um santinho da Solida em pe e 400x510, que e chapa virada.
    """
    from finart_ctp.processador import giro_da_pagina

    for cliente in (SOLIDA, EMPORIO, "VIVA", "FIALHO", "VOPRIX"):
        assert giro_da_pagina(330, 480, cliente) == 0


def test_girando_a_pinca_sai_de_outra_borda_do_arquivo():
    """
    Gire uma folha 90 graus para a direita: a borda da DIREITA desce e
    vira o pe. E de la que a pinca passa a ser medida - usar a marca do
    pe original poria a arte no lugar errado.
    """
    from finart_ctp.processador import LADO_DA_PINCA

    assert LADO_DA_PINCA[0] == "pe"
    assert LADO_DA_PINCA[90] == "direita"
    assert LADO_DA_PINCA[270] == "esquerda"


def test_a_arte_em_pe_cabe_depois_de_girada():
    """
    330x480 nao cabe numa chapa de 510x400 de jeito nenhum. Girada vira
    480x330 e cabe com folga - e por isso que o giro vem antes da conta.
    """
    assert montar_na_chapa(330, 480, CREATIVE, corte=12.0) is None
    assert montar_na_chapa(480, 330, CREATIVE, corte=12.0) == (510, 400)


# ----------------------------------------------------------------------
# O tamanho da arte NUNCA muda
# ----------------------------------------------------------------------

def test_a_arte_entra_do_tamanho_que_veio():
    """
    'voce NUNCA pode alterar o tamanho original do arquivo, apenas
    colocar na 510x400'. A conta da posicao so soma e subtrai margem: o
    que sobra da chapa e margem, nunca reducao da arte.
    """
    for larg, alt, corte in ((480, 330, 12.0), (400, 300, 13.2),
                             (510, 355, 5.0)):
        esquerda, topo = posicao_na_chapa(larg, alt, (510, 400), CREATIVE,
                                          corte)
        # a arte ocupa exatamente o seu tamanho dentro da chapa
        assert abs((esquerda + larg + esquerda) - 510) < 0.01
        assert abs((topo + alt + (400 - topo - alt)) - 400) < 0.01
        assert topo >= 0 and esquerda >= 0, "arte nao pode sair da chapa"


def test_a_chapa_gravada_guarda_o_tamanho_da_arte(tmp_path):
    """
    Prova de ponta a ponta, no pixel: a mancha da arte na chapa tem de
    medir o mesmo que a arte media antes.
    """
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    dpi = 100
    larg_arte, alt_arte = 480, 330
    px_l = int(round(larg_arte / 25.4 * dpi))
    px_a = int(round(alt_arte / 25.4 * dpi))

    tif = tmp_path / "arte.tif"
    Image.new("L", (px_l, px_a), 0).save(str(tif))      # tudo preto

    alvo = (int(round(510 / 25.4 * dpi)), int(round(400 / 25.4 * dpi)))
    esquerda, topo = posicao_na_chapa(larg_arte, alt_arte, (510, 400),
                                      CREATIVE, corte=12.0)
    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(str(tif), saida, 510, 400, alvo=alvo,
                     deslocamento=(int(round(esquerda / 25.4 * dpi)),
                                   int(round(topo / 25.4 * dpi))))

    import re
    import zlib
    dados = open(saida, "rb").read()
    W, H = (int(v) for v in
            re.search(rb"/Width (\d+) /Height (\d+)", dados).groups())
    ini = dados.find(b"stream\n") + 7
    cru = zlib.decompress(dados[ini:dados.find(b"\nendstream", ini)])

    linhas = [y for y in range(H)
              if min(cru[y * W:(y + 1) * W]) < 250]
    colunas = [x for x in range(W) if cru[linhas[0] * W + x] < 250]
    mancha_l = (colunas[-1] - colunas[0] + 1) / dpi * 25.4
    mancha_a = (linhas[-1] - linhas[0] + 1) / dpi * 25.4

    assert abs(mancha_l - larg_arte) < 0.5, "a arte mudou de largura"
    assert abs(mancha_a - alt_arte) < 0.5, "a arte mudou de altura"


# ----------------------------------------------------------------------
# A etiqueta da prova
# ----------------------------------------------------------------------

def test_a_prova_da_creative_leva_o_nome_do_cliente():
    """
    A prova saia com a etiqueta em BRANCO: papel na mesa sem dizer de
    quem e. A etiqueta era procurada pelo tamanho da ARTE, e a arte da
    Creative chega 480x330, que nao e chapa nenhuma - so vira 510x400
    depois de montada.
    """
    assert rotulo_prova(480, 330, CREATIVE) == "CREATIVE F4"


def test_a_etiqueta_vale_tambem_para_a_arte_em_pe():
    """Em pe ela sera girada, e a etiqueta olha a medida ja deitada."""
    assert rotulo_prova(330, 480, CREATIVE) == "CREATIVE F4"


def test_arte_ja_no_tamanho_da_chapa_tambem_leva_etiqueta():
    assert rotulo_prova(510, 400, CREATIVE) == "CREATIVE F4"


def test_as_etiquetas_dos_outros_clientes_nao_mudaram():
    """
    O conserto mexeu numa funcao que serve a todos. Estas sao as
    etiquetas de sempre, e elas tem de continuar iguais.
    """
    from finart_ctp.processador import FIALHO, VOPRIX

    assert rotulo_prova(510, 400, SOLIDA) == "SOLIDA F4"
    assert rotulo_prova(775, 635, SOLIDA) == "SOLIDA F2"
    assert rotulo_prova(775, 635, VOPRIX) == "VOPRIX F2"
    assert rotulo_prova(660, 605, EMPORIO) == "EMPORIO F2"
    assert rotulo_prova(520, 400, FIALHO) == "FIALHO F4"   # entra encaixada
    assert rotulo_prova(510, 400, "VIVA") == "VIVA F4"


def test_arte_que_nao_e_chapa_continua_sem_etiqueta():
    """
    Na Solida, 480x330 nao e chapa e nunca sera montada. Inventar
    etiqueta ali seria dizer na folha uma coisa que nao vai acontecer.
    """
    assert rotulo_prova(480, 330, SOLIDA) == ""


# ----------------------------------------------------------------------
# A prova precisa SAIR
# ----------------------------------------------------------------------

def test_arte_em_pe_tambem_manda_imprimir_a_prova():
    """
    O 'unirv blocos rascunho 13 08.pdf' veio com as duas paginas em pe
    (330x480). As duas chapas foram geradas, mas NENHUMA prova saiu: a
    porteira que decide se vale gastar papel olhava a medida sem girar,
    e 330x480 nao e chapa nenhuma.

    Chapa no CTP sem papel na mesa e servico que ninguem confere.
    """
    from finart_ctp.processador import chapa_prevista

    assert chapa_prevista(330, 480, CREATIVE) == (510, 400)
    assert chapa_prevista(480, 330, CREATIVE) == (510, 400)


def test_a_porteira_da_prova_nao_mudou_para_os_outros():
    from finart_ctp.processador import FIALHO, VOPRIX, chapa_prevista

    assert chapa_prevista(510, 400, SOLIDA) == (510, 400)
    assert chapa_prevista(775, 635, VOPRIX) == (775, 635)
    assert chapa_prevista(520, 400, FIALHO) == (510, 400)   # encaixa
    assert chapa_prevista(480, 330, SOLIDA) is None         # nao e chapa
    assert chapa_prevista(330, 480, EMPORIO) is None


def test_a_prova_sai_para_a_arte_em_pe(monkeypatch, tmp_path):
    """De ponta a ponta: o programa chama a impressora."""
    import finart_ctp.processador as P

    impressoes = []
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", True)
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(330, 480)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf, sem_icc=False: [
        {"C": .3, "M": .3, "Y": .3, "K": .3}])
    monkeypatch.setattr(P, "marcas_de_corte", lambda pdf, pag: {
        "pe": 12.0, "topo": 12.0, "esquerda": 12.0, "direita": 12.0})
    monkeypatch.setattr(P, "imprimir", lambda pdf, etiquetas=None, verso=None, **k:
                        (impressoes.append(etiquetas)
                         or ("KONICA", len(etiquetas))))
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: (str(tmp_path / "x.pdf"), list("CMYK")))
    monkeypatch.setattr(P.os.path, "getsize", lambda c: 1000)

    (tmp_path / "x.pdf").write_bytes(b"x")
    P._processar_pdf("arte.pdf", "unirv blocos.pdf", str(tmp_path), CREATIVE,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None},
                     lambda m: {"status": "erro", "motivo": m}, False)

    assert impressoes, "a prova da arte em pe nao foi impressa"
    assert impressoes[0] == ["CREATIVE F4"], "e sem o nome do cliente"
