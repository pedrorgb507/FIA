# -*- coding: utf-8 -*-
"""
A fila de servicos esperando OS.

Duas regras que o operador deu:

  - junta ate QUATRO do mesmo cliente e ai abre. Com uma, duas ou tres
    vagas, ESPERA O DIA SEGUINTE - nao se abre OS pela metade so porque
    o dia acabou;
  - a OS tambem se abre A MAO. Se outro operador ja lancou o servico, a
    FIA tira da fila calada. Faturar duas vezes e pior que nao faturar.
"""

import pytest

from finart_ctp import fila


@pytest.fixture(autouse=True)
def fila_no_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(fila, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(fila, "log", lambda *a, **k: None)


def servico(titulo, cliente="SOLIDA", chapas=4):
    return {"titulo": titulo, "cliente": cliente,
            "chapa": [510, 400], "chapas": chapas}


class ConexaoFalsa(object):
    """Um GEREMPRE de mentira: sabe o que ja foi lancado e o que abriu."""

    def __init__(self, ja_lancados=()):
        self.ja_lancados = set(ja_lancados)
        self.abertas = []

    def cursor(self):
        return self

    def close(self):
        pass


@pytest.fixture
def gerempre_falso(monkeypatch):
    def montar(con):
        monkeypatch.setattr(fila, "conectar", lambda: con)
        monkeypatch.setattr(fila, "ja_esta_em_os",
                            lambda cur, titulo: (18651 if titulo in
                                                 con.ja_lancados else None))

        def abrir(servicos, con=None):
            numero = 19000 + len(con.abertas)
            con.abertas.append(list(servicos))
            return numero
        monkeypatch.setattr(fila, "abrir_os", abrir)
        return con
    return montar


# ----------------------------------------------------------------------
# Juntar ate quatro
# ----------------------------------------------------------------------

def test_tres_servicos_esperam_o_dia_seguinte(gerempre_falso):
    con = gerempre_falso(ConexaoFalsa())
    f = []
    for i in range(3):
        f = fila.entrar(servico("arte %d" % i), f)

    f, abertas = fila.despachar(f, con=con)
    assert abertas == [], "abriu OS pela metade"
    assert len(f) == 3, "e os tres tem de continuar esperando"


def test_o_quarto_servico_abre_a_os(gerempre_falso):
    con = gerempre_falso(ConexaoFalsa())
    f = []
    for i in range(4):
        f = fila.entrar(servico("arte %d" % i), f)

    f, abertas = fila.despachar(f, con=con)
    assert len(abertas) == 1
    assert f == [], "a fila tem de esvaziar"
    assert len(con.abertas[0]) == 4


def test_o_que_sobra_de_hoje_soma_com_o_de_amanha(gerempre_falso):
    """Duas hoje, duas amanha, e a OS sai amanha com as quatro."""
    con = gerempre_falso(ConexaoFalsa())
    f = []
    for i in range(2):
        f = fila.entrar(servico("hoje %d" % i), f)
    f, abertas = fila.despachar(f, con=con)
    assert abertas == []

    for i in range(2):
        f = fila.entrar(servico("amanha %d" % i), f)
    f, abertas = fila.despachar(f, con=con)

    assert len(abertas) == 1
    titulos = [s["titulo"] for s in con.abertas[0]]
    assert titulos == ["hoje 0", "hoje 1", "amanha 0", "amanha 1"], \
        "a ordem de chegada tem de ser respeitada"


def test_cada_cliente_tem_a_sua_fila(gerempre_falso):
    """Uma OS e de um cliente so - misturar faturaria um no outro."""
    con = gerempre_falso(ConexaoFalsa())
    f = []
    for i in range(4):
        f = fila.entrar(servico("solida %d" % i, "SOLIDA"), f)
    for i in range(2):
        f = fila.entrar(servico("viva %d" % i, "VIVA"), f)

    f, abertas = fila.despachar(f, con=con)
    assert len(abertas) == 1
    assert {s["cliente"] for s in con.abertas[0]} == {"SOLIDA"}
    assert len(f) == 2, "os dois da VIVA continuam esperando"


def test_oito_servicos_viram_duas_os(gerempre_falso):
    con = gerempre_falso(ConexaoFalsa())
    f = []
    for i in range(8):
        f = fila.entrar(servico("arte %d" % i), f)
    f, abertas = fila.despachar(f, con=con)
    assert len(abertas) == 2
    assert f == []


# ----------------------------------------------------------------------
# Outro operador fechou a OS na mao
# ----------------------------------------------------------------------

def test_servico_ja_lancado_a_mao_sai_da_fila(gerempre_falso):
    """
    Aconteceu de verdade e e normal: alguem lanca a OS a mao antes de a
    FIA chegar nela. Se ela abrisse assim mesmo, o cliente pagaria duas
    vezes pela mesma chapa.
    """
    con = gerempre_falso(ConexaoFalsa(ja_lancados={"arte 1"}))
    f = []
    for i in range(4):
        f = fila.entrar(servico("arte %d" % i), f)

    f, abertas = fila.despachar(f, con=con)
    assert abertas == [], "sobraram tres - nao da OS"
    assert [s["titulo"] for s in f] == ["arte 0", "arte 2", "arte 3"]


def test_a_os_sai_sem_o_que_ja_foi_lancado(gerempre_falso):
    con = gerempre_falso(ConexaoFalsa(ja_lancados={"arte 0"}))
    f = []
    for i in range(5):
        f = fila.entrar(servico("arte %d" % i), f)

    f, abertas = fila.despachar(f, con=con)
    assert len(abertas) == 1
    assert [s["titulo"] for s in con.abertas[0]] == ["arte 1", "arte 2",
                                                     "arte 3", "arte 4"]


# ----------------------------------------------------------------------
# Nada se perde
# ----------------------------------------------------------------------

def test_o_mesmo_servico_nao_entra_duas_vezes():
    f = fila.entrar(servico("arte"), [])
    f = fila.entrar(servico("arte"), f)
    assert len(f) == 1


def test_gerempre_fora_do_ar_nao_perde_a_fila(monkeypatch):
    """
    Sem ligacao, ninguem perde nada: o servico continua esperando e sai
    na proxima vez que o banco responder.
    """
    from finart_ctp.gerempre import SemLigacao

    def cair():
        raise SemLigacao("banco fora do ar")
    monkeypatch.setattr(fila, "conectar", cair)

    f = [servico("arte %d" % i) for i in range(4)]
    f, abertas = fila.despachar(f)
    assert abertas == []
    assert len(f) == 4


def test_a_fila_sobrevive_ao_desligar():
    """Se a FIA for desligada, o que ela fechou continua esperando."""
    f = fila.entrar(servico("arte 1"), [])
    f = fila.entrar(servico("arte 2"), f)
    fila.salvar(f)
    assert [s["titulo"] for s in fila.carregar()] == ["arte 1", "arte 2"]


def test_erro_ao_abrir_uma_os_nao_derruba_as_outras(gerempre_falso,
                                                    monkeypatch):
    con = gerempre_falso(ConexaoFalsa())

    def abrir_quebrado(servicos, con=None):
        if servicos[0]["cliente"] == "SOLIDA":
            raise RuntimeError("o banco reclamou")
        con.abertas.append(list(servicos))
        return 19999
    monkeypatch.setattr(fila, "abrir_os", abrir_quebrado)

    f = []
    for i in range(4):
        f = fila.entrar(servico("solida %d" % i, "SOLIDA"), f)
    for i in range(4):
        f = fila.entrar(servico("viva %d" % i, "VIVA"), f)

    f, abertas = fila.despachar(f, con=con)
    assert abertas == [19999], "a VIVA tinha de passar"
    assert len(f) == 4, "os da SOLIDA continuam na fila, para tentar depois"


def test_quantos_estao_esperando():
    f = [servico("a", "SOLIDA"), servico("b", "SOLIDA"), servico("c", "VIVA")]
    assert fila.esperando(f) == {"SOLIDA": 2, "VIVA": 1}


# ----------------------------------------------------------------------
# Dois arquivos com a mesma OS
# ----------------------------------------------------------------------

def test_dois_arquivos_com_a_mesma_os_param_e_perguntam(monkeypatch):
    """
    Aconteceu em 08/09: '49728 - EDNA - COLINHAS 4MOD' e
    '49728 - EDNA - COLINHAS 4MOD 1', a mesma OS em dois arquivos.

    Dois servicos cobrados separados dao R$ 104; um so com as chapas
    somadas da o mesmo valor, mas numa linha - e ha caso em que e um
    trabalho so partido em dois arquivos, e ai cobrar dois e cobrar a
    mais. Nao ha regra: a FIA para e pergunta.
    """
    avisos = []
    monkeypatch.setattr(fila, "anotar_pendencia",
                        lambda n, m: avisos.append((n, m)))

    f = fila.entrar(servico("49728 - EDNA - COLINHAS 4MOD"), [])
    f = fila.entrar(servico("49728 - EDNA - COLINHAS 4MOD 1"), f)

    assert len(f) == 1, "o segundo nao pode entrar calado"
    assert avisos and "MESMA OS" in avisos[0][1]
    assert "COLINHAS 4MOD" in avisos[0][1]


def test_os_diferentes_no_mesmo_dia_entram_normalmente(monkeypatch):
    monkeypatch.setattr(fila, "anotar_pendencia",
                        lambda n, m: pytest.fail("nao era para reclamar"))
    f = fila.entrar(servico("49713 - LUCAS CALIL - PANFLETO ITAPURANGA"), [])
    f = fila.entrar(servico("49714 - LUCAS CALIL - PANFLETO ITUMBIARA"), f)
    assert len(f) == 2


def test_arquivo_com_varias_os_no_nome(monkeypatch):
    """
    '49715 49716 49717 49718 - ...' traz quatro OS num arquivo so, e isso
    e normal. Mas se depois chegar um arquivo com a 49716, e o mesmo
    caso: para e pergunta.
    """
    avisos = []
    monkeypatch.setattr(fila, "anotar_pendencia",
                        lambda n, m: avisos.append(m))
    f = fila.entrar(servico("49715 49716 49717 49718 - LUCAS - PANFLETOS"), [])
    assert len(f) == 1 and not avisos

    f = fila.entrar(servico("49716 - LUCAS - OUTRO PANFLETO"), f)
    assert len(f) == 1, "a 49716 ja estava em outro arquivo"
    assert avisos


def test_cliente_diferente_com_numero_igual_nao_confunde(monkeypatch):
    """
    A numeracao e de cada cliente: a OS 02037 do Emporio nao tem nada a
    ver com a 02037 de outro.
    """
    monkeypatch.setattr(fila, "anotar_pendencia",
                        lambda n, m: pytest.fail("clientes diferentes"))
    f = fila.entrar(servico("02037 - CHAPA - CAIXAS", "EMPORIO"), [])
    f = fila.entrar(servico("02037 - ALGO", "SOLIDA"), f)
    assert len(f) == 2


# ----------------------------------------------------------------------
# O titulo cortado no tamanho da coluna
# ----------------------------------------------------------------------

def test_titulo_comprido_e_cortado_antes_de_gravar():
    """
    A coluna OSTIT cabe 50 letras e o Firebird NAO corta sozinho: passar
    disso derruba a gravacao inteira com erro de truncamento.
    """
    from finart_ctp.gerempre import LETRAS_NO_TITULO, montar_vaga

    comprido = "49715 49716 49717 49718 - LUCAS CALIL - PANFLETOS 4MOD"
    assert len(comprido) > LETRAS_NO_TITULO
    vaga = montar_vaga(servico(comprido))
    assert len(vaga["OSTIT"]) == LETRAS_NO_TITULO
    assert vaga["OSTIT"].startswith("49715 49716 49717 49718")
