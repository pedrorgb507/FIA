# -*- coding: utf-8 -*-
"""
Da chapa fechada ao servico de OS.

Esta e a peca que liga as duas metades do programa: a FIA fechava chapa e
sabia abrir OS, mas nada levava uma coisa a outra. O que decide a conta e
o que SAIU, e nao o que se esperava que saisse.

Tres coisas nao viram OS, e as tres de proposito - cobrar errado e pior
que nao cobrar:

  - arquivo que deu problema em alguma pagina (ja e pendencia);
  - arquivo que nao gerou chapa nenhuma;
  - arquivo cujas paginas sairam em chapas de tamanhos DIFERENTES: uma
    vaga da OS tem um tamanho so, e cada tamanho tem outro preco.
"""

import pytest

from finart_ctp import fila


@pytest.fixture(autouse=True)
def fila_no_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(fila, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(fila, "log", lambda *a, **k: None)


def resultado(chapas, status="ok"):
    return {"status": status, "saidas": ["x.pdf"] * len(chapas),
            "chapas": chapas, "motivo": ""}


def cmyk(larg=510, alt=400):
    return {"chapa": [larg, alt], "tintas": 4}


# ----------------------------------------------------------------------
# A conta das chapas
# ----------------------------------------------------------------------

def test_uma_pagina_em_quadricromia_gasta_quatro_chapas():
    s = fila.servico_do_arquivo("49914 - Heineken.pdf", "SOLIDA",
                                resultado([cmyk()]))
    assert s["chapas"] == 4
    assert s["chapa"] == [510, 400]
    assert s["cliente"] == "SOLIDA"


def test_duas_paginas_em_quadricromia_gastam_oito():
    """Frente e verso em CMYK sao oito chapas de metal, nao duas."""
    s = fila.servico_do_arquivo("GRADE 38.pdf", "VIVA",
                                resultado([cmyk(), cmyk()]))
    assert s["chapas"] == 8


def test_arte_de_uma_cor_gasta_uma_chapa_so():
    """A pagina que saiu em GRAY vale uma chapa, nao quatro."""
    s = fila.servico_do_arquivo("TIMBRADO.pdf", "VOPRIX",
                                resultado([{"chapa": [510, 400],
                                            "tintas": 1}]))
    assert s["chapas"] == 1


def test_paginas_de_cores_diferentes_somam_o_que_cada_uma_gastou():
    s = fila.servico_do_arquivo("MISTO.pdf", "VOPRIX",
                                resultado([cmyk(),
                                           {"chapa": [510, 400],
                                            "tintas": 1}]))
    assert s["chapas"] == 5


# ----------------------------------------------------------------------
# O titulo
# ----------------------------------------------------------------------

def test_o_titulo_e_o_nome_do_arquivo_em_caixa_alta_sem_extensao():
    """
    Conferido em 330 arquivos de agosto: o GEREMPRE guarda o titulo em
    caixa alta, e a extensao nao entra.
    """
    s = fila.servico_do_arquivo("49914 - Heineken - display table top.pdf",
                                "SOLIDA", resultado([cmyk()]))
    assert s["titulo"] == "49914 - HEINEKEN - DISPLAY TABLE TOP"


def test_o_sublinhado_da_voprix_continua_igual():
    s = fila.servico_do_arquivo("TIMBRADO_21X29,7_4_0_DRA_SUZANA.pdf",
                                "VOPRIX", resultado([cmyk()]))
    assert s["titulo"] == "TIMBRADO_21X29,7_4_0_DRA_SUZANA"


# ----------------------------------------------------------------------
# O que NAO vira OS
# ----------------------------------------------------------------------

def test_arquivo_com_problema_nao_vira_os():
    """
    Uma pagina parou e virou pendencia. Cobrar meio arquivo e pior que
    nao cobrar: quem resolver a pendencia e quem lanca.
    """
    r = resultado([cmyk()], status="erro")
    assert fila.servico_do_arquivo("ALGO.pdf", "SOLIDA", r) is None


def test_arquivo_que_nao_gerou_chapa_nao_vira_os():
    assert fila.servico_do_arquivo("ALGO.pdf", "SOLIDA",
                                   resultado([])) is None


def test_chapas_de_tamanhos_diferentes_param_e_perguntam(monkeypatch):
    """
    Uma vaga da OS tem um tamanho de chapa so, e cada tamanho tem outro
    preco. Dividir o arquivo em duas vagas e decisao de gente.
    """
    avisos = []
    monkeypatch.setattr(fila, "anotar_pendencia",
                        lambda nome, motivo: avisos.append((nome, motivo)))
    r = resultado([cmyk(510, 400), cmyk(775, 635)])
    assert fila.servico_do_arquivo("MISTO.pdf", "SOLIDA", r) is None
    assert avisos, "tinha de virar pendencia"
    assert "tamanhos diferentes" in avisos[0][1]


def test_status_espera_e_adiado_nao_viram_os():
    """
    'espera' e impressora fora, 'adiado' e .cdr aberto no Corel de
    alguem. Nos dois casos nao saiu chapa nenhuma.
    """
    for status in ("espera", "adiado"):
        r = {"status": status, "saidas": [], "chapas": [], "motivo": ""}
        assert fila.servico_do_arquivo("ALGO.pdf", "VOPRIX", r) is None


def test_resultado_velho_sem_o_campo_chapas_nao_quebra():
    """
    O registro em disco tem resultados gravados antes deste campo
    existir. Ler um deles nao pode derrubar o programa.
    """
    r = {"status": "ok", "saidas": ["x.pdf"], "motivo": ""}
    assert fila.servico_do_arquivo("ALGO.pdf", "SOLIDA", r) is None


# ----------------------------------------------------------------------
# E entra na fila
# ----------------------------------------------------------------------

def test_o_servico_montado_entra_na_fila_e_espera_companhia():
    s = fila.servico_do_arquivo("49914 - Heineken.pdf", "SOLIDA",
                                resultado([cmyk()]))
    f = fila.entrar(s, [])
    assert len(f) == 1
    assert fila.esperando(f) == {"SOLIDA": 1}


def test_quatro_arquivos_fechados_enchem_uma_os():
    f = []
    for n in range(4):
        s = fila.servico_do_arquivo("4991%d - ALGO.pdf" % n, "SOLIDA",
                                    resultado([cmyk()]))
        f = fila.entrar(s, f)
    assert fila.esperando(f) == {"SOLIDA": 4}
    grupo = fila.por_cliente(f)["SOLIDA"]
    assert sum(s["chapas"] for s in grupo) == 16


# ----------------------------------------------------------------------
# A fila nao pode mexer na lista de quem chamou
# ----------------------------------------------------------------------

def test_entrar_devolve_lista_nova_e_nao_mexe_na_recebida():
    """
    Custou a primeira OS da VIVA: com append, a lista devolvida ERA a
    recebida, entao comparar o tamanho antes e depois dava sempre igual
    e o programa concluia que a fila havia recusado o servico. A OS nao
    era aberta, e ninguem via - nao havia erro nenhum, so silencio.
    """
    antes = []
    s = fila.servico_do_arquivo("GRADE 18.pdf", "VIVA", resultado([cmyk()]))
    depois = fila.entrar(s, antes)

    assert antes == [], "a lista de quem chamou nao pode mudar"
    assert len(depois) == 1
    assert depois is not antes
    assert len(depois) > len(antes), "e assim que quem chama sabe que entrou"


def test_o_mesmo_servico_duas_vezes_nao_cresce_a_fila():
    s = fila.servico_do_arquivo("GRADE 18.pdf", "VIVA", resultado([cmyk()]))
    f = fila.entrar(s, [])
    assert len(fila.entrar(s, f)) == 1
