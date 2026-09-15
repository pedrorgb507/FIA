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
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente, **k: (
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
                        lambda arq, motivo, cliente=None: avisos.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a, **k: pytest.fail("VIVA nao converte"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VIVA)
    assert r["status"] == "erro" and "nao em PDF" in r["motivo"]
    assert "Nao dei andamento" in avisos[0]


def _pagina(monkeypatch, cobertura):
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf, sem_icc=False: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina, sem_icc=False: False)
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
              cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("quadricromia nao e pendencia"))

    r = _roda(tmp_path, "GRADE 1637.pdf")
    assert r["status"] == "ok" and feito["dpi"] == 1000
    assert feito["base"] == "510x400_CMYK_VIVA_GRADE 1637"


def test_fora_da_quadricromia_espera(monkeypatch, tmp_path):
    _pagina(monkeypatch, {"C": .21, "M": 0, "Y": 0, "K": .08})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: avisos.append(motivo))

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
                        lambda arq, motivo, cliente=None: avisos.append(motivo))

    r = _roda(tmp_path, "verniz 1704.pdf")
    assert r["status"] == "erro"
    assert "VERNIZ" in avisos[0] and "confere antes" in avisos[0]


# ----------------------------------------------------------------------
# ARTE ALGUNS MILIMETROS FORA DA CHAPA - 14/09/2026
# ----------------------------------------------------------------------
# "chapa da viva quando vier com tamanho diferente, com poucos
# milimetros de diferenca, pode centralizar na chapa 510x400, e dar
# andamento normal, nao parar mais" - o operador.

def test_o_GRADE_3385_entra_centralizado_na_chapa():
    """
    O caso de verdade: 510 x 399 mm. A chapa saia com 510x399 e nome
    '510x400_CMYK_VIVA_GRADE 3385' - um arquivo que mente sobre o
    proprio tamanho -, e a OS nem abria.
    """
    chapa, dpi, _suf, encaixou = P.chapa_da_pagina(510.0, 399.0, P.VIVA)
    assert chapa == (510, 400)
    assert encaixou is True
    assert dpi == 1000


def test_e_agora_a_OS_sabe_o_preco():
    """
    O que parava o servico nao era a chapa, era o dinheiro: a busca de
    preco e exata. 'nao sei que chapa usar para VIVA 510x399.'
    """
    from finart_ctp.gerempre import chapa_do_servico

    assert chapa_do_servico("VIVA", 510.0, 399.0) is None, \
        "a busca de preco continua sendo exata - quem arruma e a chapa"

    chapa, _dpi, _suf, _enc = P.chapa_da_pagina(510.0, 399.0, P.VIVA)
    achado = chapa_do_servico("VIVA", chapa[0], chapa[1])
    assert achado is not None
    assert achado[1] == "CHAPA VIVA - FT4" and achado[2] == 8.50


def test_NAO_e_caso_so_da_viva():
    """
    O registro tem uma do EMPORIO, 509,764 x 398,992, que saiu 1 mm
    torta e ninguem viu. O conserto vale para todo cliente sem pinca.
    """
    chapa, _dpi, _suf, encaixou = P.chapa_da_pagina(509.764, 398.992,
                                                    P.EMPORIO)
    assert chapa == (510, 400) and encaixou is True


def test_arredondamento_de_PDF_continua_passando_direto():
    """
    161 das 162 chapas ja fechadas desviam 0,0006 mm. Se elas passassem
    a ser centralizadas, TODA chapa da casa mudaria de caminho por nada.
    """
    from finart_ctp.config import ARREDONDAMENTO_MM

    assert ARREDONDAMENTO_MM == 0.1
    assert 0.0006 < ARREDONDAMENTO_MM < 1.0083, \
        "o limiar tem de separar o arredondamento do desvio de verdade"

    chapa, _dpi, _suf, encaixou = P.chapa_da_pagina(510.0, 400.0006, P.VIVA)
    assert encaixou is False
    assert chapa == (510.0, 400.0006)


def test_quem_tem_PINCA_fica_de_fora():
    """
    Para a CREATIVE e a PRIME, arte do tamanho da chapa quer dizer 'ja
    montada'. Caindo no encaixe, ela seria remontada pela marca de corte
    e sairia do lugar.
    """
    for cliente in (P.CREATIVE, P.PRIME):
        chapa, _dpi, _suf, encaixou = P.chapa_da_pagina(510.0, 399.0, cliente)
        assert encaixou is False, cliente
        assert chapa == (510.0, 399.0), cliente


# ----------------------------------------------------------------------
# O VERSO DE UMA COR ESCONDIDO PELO PERFIL ICC - 15/09/2026
# ----------------------------------------------------------------------
# "material da viva, a grade 3386 ela e 4 cores na frente e 1 cor no
# verso, queria que fizesse esse 1 cor como vc fez o da voprix, vendo as
# porcentagens se vao bater e colocando somente no preto, ai a OS no
# gerempre seria de 5 chapas" - o operador.
#
# O verso saiu com QUATRO chapas e a OS 19730 cobrou oito no lugar de
# cinco. Medido no arquivo de verdade, 'GRADE 3386.pdf':
#
#     com o perfil   C 0,1393  M 0,1435  Y 0,1435  K 0,0634
#     sem o perfil   C 0,0010  M 0,0010  Y 0,0010  K 0,4131
#
# Os 0,1% sao as marcas de registro. A arte esta INTEIRA no K.

CRUA_3386_VERSO = {"C": 0.0010, "M": 0.0010, "Y": 0.0010, "K": 0.4131}
COM_PERFIL_3386_VERSO = {"C": 0.1393, "M": 0.1435, "Y": 0.1435, "K": 0.0634}

# o mesmo, do '49835 - Flor Bela - sacola' da SOLIDA: chapado, e o
# perfil espalha o preto IGUALMENTE nos quatro canais
COM_PERFIL_FLOR_BELA = {"C": 0.3867, "M": 0.3867, "Y": 0.3867, "K": 0.3867}


def test_a_leitura_CRUA_ve_o_preto_puro_do_verso():
    from finart_ctp.processador import preto_so_no_K

    assert preto_so_no_K(CRUA_3386_VERSO) is True


def test_a_leitura_COM_PERFIL_NAO_ve_e_foi_por_isso_que_falhou():
    """
    A trava perguntava a leitura errada. Meio-tom passando pelo perfil
    sai com os canais DESIGUAIS - nao parece nem preto composto.
    """
    from finart_ctp.processador import pagina_de_uma_cor, preto_so_no_K

    assert pagina_de_uma_cor(COM_PERFIL_3386_VERSO) is False
    assert preto_so_no_K(COM_PERFIL_3386_VERSO) is False


def test_o_chapado_enganava_menos_que_o_meio_tom():
    """
    Por que o caso da SOLIDA funcionava e o da VIVA nao: no chapado o
    perfil espalha o preto por igual, e 'pagina_de_uma_cor' aceita isso
    como preto composto. No meio-tom a conta e nao linear.
    """
    from finart_ctp.processador import pagina_de_uma_cor

    assert pagina_de_uma_cor(COM_PERFIL_FLOR_BELA) is True
    assert pagina_de_uma_cor(COM_PERFIL_3386_VERSO) is False


def test_a_decisao_do_preto_puro_NAO_depende_mais_da_leitura_com_perfil():
    """
    O conserto: a pergunta 'em que canal a tinta esta' passou a ser feita
    SEMPRE ao arquivo. Sem isto, o verso do 3386 volta a sair com quatro
    chapas.
    """
    fonte = open(P.__file__, encoding="utf-8").read()
    trecho = fonte[fonte.index("cinza = False"):]
    trecho = trecho[:trecho.index("tintas_do_arquivo")]
    crua = trecho.index("crua = cob if sem_icc else cobertura_crua")
    guarda = trecho.index("pagina_de_uma_cor(cob)")
    assert crua < guarda, \
        "a leitura crua voltou a depender da leitura com perfil"


def test_frente_e_verso_dao_CINCO_chapas_e_nao_oito():
    """
    Quatro da frente em quadricromia, uma do verso em preto. E o que a
    OS tem de cobrar.
    """
    from finart_ctp.gerempre import quantas_chapas

    assert quantas_chapas([set("CMYK"), {"GRAY"}]) == 5
    assert quantas_chapas([set("CMYK"), set("CMYK")]) == 8
