# -*- coding: utf-8 -*-
"""
A resolucao da chapa: a conferencia que fecha a porta do prejuizo.

Chapa gravada na resolucao errada nao da erro, abre normalmente e sai na
prova reduzida igual as certas. O defeito so aparece na tiragem, com a
chapa queimada e o papel rodando. Por isso a chapa e MEDIDA depois de
pronta, no arquivo, e nao pela variavel que o programa usou.
"""

import os

import pytest

from finart_ctp.pdf_builder import conferir_resolucao, montar_pdf_cinza


def chapa(tmp_path, larg_mm, alt_mm, dpi, nome="chapa.pdf"):
    """Grava uma chapa de verdade, do tamanho e da resolucao pedidos."""
    from PIL import Image
    px_l = int(round(larg_mm / 25.4 * dpi))
    px_a = int(round(alt_mm / 25.4 * dpi))
    tif = tmp_path / "sep.tif"
    Image.new("L", (px_l, px_a), 200).save(str(tif))
    saida = str(tmp_path / nome)
    montar_pdf_cinza(str(tif), saida, larg_mm, alt_mm)
    return saida


def test_chapa_na_resolucao_certa_passa(tmp_path):
    p = chapa(tmp_path, 510, 400, 100)          # 100 dpi para o teste correr
    assert conferir_resolucao(p, 510, 400, 100) == ""


def test_chapa_em_300_dpi_e_barrada(tmp_path):
    """
    O caso que o operador relatou: arquivo convertido em 300 dpi.

    A chapa mede 510x400 mm certinho - o erro nao esta no tamanho, esta
    na quantidade de pixels dentro dele.
    """
    p = chapa(tmp_path, 510, 400, 300)
    erro = conferir_resolucao(p, 510, 400, 1000)
    assert erro, "passou chapa de 300 dpi como se fosse de 1000"
    assert "300 dpi" in erro and "1000" in erro
    assert "borrada" in erro


def test_chapa_do_tamanho_errado_e_barrada(tmp_path):
    p = chapa(tmp_path, 510, 400, 100)
    erro = conferir_resolucao(p, 775, 635, 100)
    assert "largura" in erro


def test_um_pixel_de_arredondamento_nao_e_erro(tmp_path):
    """
    510 mm a 1000 dpi dao 20078,74 pixels - numero quebrado. O que
    arredonda nao pode virar alarme, senao ninguem olha mais nenhum.
    """
    p = chapa(tmp_path, 510, 400, 100)
    assert conferir_resolucao(p, 510, 400, 100) == ""


def test_arquivo_ilegivel_nao_passa_calado(tmp_path):
    ruim = tmp_path / "ruim.pdf"
    ruim.write_bytes(b"%PDF-1.4\nisto nao e uma chapa\n")
    assert conferir_resolucao(str(ruim), 510, 400, 1000)


def test_a_chapa_errada_e_apagada_e_nao_fica_no_ctp(tmp_path, monkeypatch):
    """
    Uma chapa que nao existe da trabalho; uma chapa errada na pasta do
    CTP da prejuizo. Entre as duas, o programa escolhe apagar.
    """
    import finart_ctp.processador as P

    p = chapa(tmp_path, 510, 400, 300, "saiu_errada.pdf")
    assert os.path.exists(p)

    with pytest.raises(RuntimeError) as e:
        P.conferir(p, 510, 400, 1000)

    assert not os.path.exists(p), "a chapa errada ficou na pasta"
    assert "apaguei" in str(e.value)


# ----------------------------------------------------------------------
# A auditoria da pasta ja entregue
# ----------------------------------------------------------------------

def test_auditoria_acha_a_chapa_errada(tmp_path, capsys):
    from finart_ctp import auditoria

    chapa(tmp_path, 510, 400, 1000, "certa.pdf")
    chapa(tmp_path, 510, 400, 300, "errada.pdf")

    problemas = auditoria.auditar(str(tmp_path))
    assert [p[0] for p in problemas] == ["errada.pdf"]
    assert "NAO MANDE RODAR" in capsys.readouterr().out


def test_auditoria_nao_acusa_chapa_feita_a_mao(tmp_path, capsys):
    """
    A chapa que o operador fecha na Corel e vetor, e vetor nao tem dpi -
    quem resolve a resolucao ali e o RIP. Acusar aquilo seria alarme
    falso, e alarme falso ninguem olha duas vezes.
    """
    from finart_ctp import auditoria

    mao = tmp_path / "feita_a_mao.pdf"
    mao.write_bytes(b"%PDF-1.4\n<< /MediaBox [0 0 1445.6693 1133.8583] "
                    b"/Resources << /Font << >> >> >>\n%%EOF\n")

    assert auditoria.auditar(str(tmp_path)) == []
    saida = capsys.readouterr().out
    assert "nao e chapa nossa" in saida
