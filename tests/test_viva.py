# -*- coding: utf-8 -*-
"""
VIVA ACABAMENTOS: PDF anda, .cdr espera.

O nome de saida foi lido das chapas que os operadores fecharam a mao:

    510x400_CMYK_VIVA_BOLSA 1524
    510x400_CMYK_VIVA_GRADE 1703 F   e   ... V

Uma chapa so (510x400), e as travas do Emporio valem aqui: fora da
quadricromia espera, e verniz espera sempre.
"""

import os

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.nomes import e_backup_do_corel, nome_saida_viva


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# Nome de saida
# ----------------------------------------------------------------------

def test_nome_e_o_do_arquivo():
    """Os arquivos de verdade da pasta de hoje."""
    assert (nome_saida_viva("GRADE 1637.pdf", "510x400", set("CMYK"))
            == "510x400_CMYK_VIVA_GRADE 1637")
    assert (nome_saida_viva("bolsa 1524.pdf", "510x400", set("CMYK"))
            == "510x400_CMYK_VIVA_bolsa 1524")


def test_frente_e_verso_como_na_solida():
    n = "GRADE 38.pdf"
    assert (nome_saida_viva(n, "510x400", set("CMYK"), 0, 2)
            == "510x400_CMYK_VIVA_GRADE 38 F")
    assert (nome_saida_viva(n, "510x400", set("CMYK"), 1, 2)
            == "510x400_CMYK_VIVA_GRADE 38 V")


def test_tres_paginas_viram_numero():
    n = "GRADE 99.pdf"
    assert (nome_saida_viva(n, "510x400", set("CMYK"), 2, 3)
            == "510x400_CMYK_VIVA_GRADE 99 3")


def test_uma_cor_entra_como_gray_no_nome():
    assert (nome_saida_viva("verniz 1704.pdf", "510x400", {"GRAY"})
            == "510x400_GRAY_VIVA_verniz 1704")


def test_acento_cai_aqui_tambem():
    assert (nome_saida_viva("GRADE ÍNDIO.pdf", "510x400", set("CMYK"))
            == "510x400_CMYK_VIVA_GRADE INDIO")


def test_nome_da_chapa_escolhe_a_regra_da_viva():
    assert (P.nome_da_chapa(P.VIVA, "GRADE 1636.pdf", "", 510, 400,
                            set("CMYK"), 0, 2)
            == "510x400_CMYK_VIVA_GRADE 1636 F")


# ----------------------------------------------------------------------
# A copia de seguranca do CorelDRAW nao e trabalho
# ----------------------------------------------------------------------

def test_backup_do_corel_e_reconhecido():
    """O arquivo real da pasta do dia 04."""
    assert e_backup_do_corel("Cópia_de_segurança_de_verniz 1705.cdr")
    assert e_backup_do_corel("Backup_of_desenho.cdr")
    assert not e_backup_do_corel("verniz 1705.cdr")
    assert not e_backup_do_corel("GRADE 1637.pdf")


def test_varrer_ignora_o_backup_do_corel(monkeypatch, tmp_path):
    """Sem isto, cada backup viraria uma pendencia inutil, todo dia."""
    (tmp_path / "verniz 1705.cdr").write_bytes(b"x")
    (tmp_path / "Cópia_de_segurança_de_verniz 1705.cdr").write_bytes(b"x")
    (tmp_path / "GRADE 1637.pdf").write_bytes(b"x")

    vistos = []
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente: (
        vistos.append(os.path.basename(caminho))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.VIVA, (".pdf", ".cdr"))

    assert sorted(vistos) == ["GRADE 1637.pdf", "verniz 1705.cdr"]


# ----------------------------------------------------------------------
# Formato: uma chapa so
# ----------------------------------------------------------------------

def test_a_viva_tem_uma_chapa_so():
    assert P.identificar_formato(510, 400, P.VIVA) == (1000, "")
    assert P.identificar_formato(400, 510, P.VIVA) == (1000, "")   # deitado
    assert P.identificar_formato(775, 635, P.VIVA) == (None, None)
    assert P.identificar_formato(730, 600, P.VIVA) == (None, None)
    assert P.identificar_formato(660, 605, P.VIVA) == (None, None)


def test_etiqueta_da_prova():
    assert P.rotulo_prova(510, 400, P.VIVA) == "VIVA F4"


def test_encaixe_nao_vale_para_a_viva():
    """Cortar arte no escuro so foi combinado com o Fialho."""
    assert P.encaixar_formato(520, 400, P.VIVA) is None


# ----------------------------------------------------------------------
# O que anda e o que espera
# ----------------------------------------------------------------------

def test_cdr_da_viva_nao_anda(monkeypatch, tmp_path):
    cdr = tmp_path / "verniz 1706.cdr"
    cdr.write_bytes(b"cdr")
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a: pytest.fail("VIVA nao converte"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VIVA)
    assert r["status"] == "erro" and "nao em PDF" in r["motivo"]
    assert "Nao dei andamento" in avisos[0]


def _pagina(monkeypatch, cobertura):
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina: False)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)


def _roda(tmp_path, nome, aprovado=False):
    return P._processar_pdf("x.pdf", nome, str(tmp_path), P.VIVA,
                            {"status": "ok", "saidas": [], "motivo": "",
                             "impresso": None}, lambda m: None, aprovado)


def test_quadricromia_fecha_sozinha(monkeypatch, tmp_path):
    _pagina(monkeypatch, {"C": .31, "M": .22, "Y": .18, "K": .09})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito.update(base=base, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("quadricromia nao e pendencia"))

    r = _roda(tmp_path, "GRADE 1637.pdf")
    assert r["status"] == "ok" and feito["dpi"] == 1000
    assert feito["base"] == "510x400_CMYK_VIVA_GRADE 1637"


def test_fora_da_quadricromia_espera(monkeypatch, tmp_path):
    _pagina(monkeypatch, {"C": .21, "M": 0, "Y": 0, "K": .08})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = _roda(tmp_path, "GRADE 1637.pdf")
    assert r["status"] == "erro"
    assert "NAO veio em quadricromia" in avisos[0]


def test_verniz_espera_mesmo_em_quadricromia(monkeypatch, tmp_path):
    """A VIVA manda muito verniz - e verniz se confere antes."""
    _pagina(monkeypatch, {"C": .3, "M": .2, "Y": .2, "K": .1})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("verniz nao fecha sozinho"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = _roda(tmp_path, "verniz 1704.pdf")
    assert r["status"] == "erro"
    assert "VERNIZ" in avisos[0] and "confere antes" in avisos[0]
