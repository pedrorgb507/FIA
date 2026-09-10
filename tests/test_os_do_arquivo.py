# -*- coding: utf-8 -*-
r"""
O passo da OS dentro do fluxo, e a trava que o mantem longe do banco.

Em 09/09/2026 esta suite abriu quatro OS na PRODUCAO e baixou chapa em
quatro estoques. Foram desfeitas no mesmo dia e o estoque voltou ao
numero exato, mas o caminho existia. Estes testes existem para que ele
nao volte a existir.
"""

import pytest

from finart_ctp import gerempre, processador


def planos(quantos=1, larg=510.0, alt=400.0, tintas="CMYK"):
    return [{"pagina": i + 1, "base": "x", "dpi": 1000,
             "larg_chapa": larg, "alt_chapa": alt, "usadas": set(tintas),
             "cinza": False, "alvo": None, "deslocamento": None, "girar": 0}
            for i in range(quantos)]


# ----------------------------------------------------------------------
# A trava
# ----------------------------------------------------------------------

def test_nenhum_teste_alcanca_o_gerempre():
    """
    A trava do conftest. Se este teste falhar, a suite voltou a poder
    escrever no banco da empresa - pare tudo e conserte antes de seguir.
    """
    with pytest.raises(gerempre.SemLigacao):
        gerempre.conectar()


def test_o_passo_da_os_fica_neutro_por_padrao():
    """Sem pedir 'com_os', nenhum arquivo vira OS."""
    numero, fechou = processador._os_do_arquivo("ALGO.pdf", processador.VIVA,
                                                planos())
    assert numero is None
    assert fechou is False, "sem OS, nada tem quatro vagas para fechar"


# ----------------------------------------------------------------------
# GEREMPRE fora do ar: a chapa sai, a OS fica para a mao
# ----------------------------------------------------------------------

def test_sem_gerempre_a_chapa_sai_e_a_pendencia_avisa(com_os, monkeypatch,
                                                      tmp_path):
    """
    Banco fora do ar nao pode segurar chapa: o trabalho e entregue e o
    lancamento fica para gente. Mas TEM de avisar - servico que fecha e
    ninguem cobra e prejuizo silencioso.
    """
    from finart_ctp import fila
    avisos = []
    monkeypatch.setattr(fila, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(processador, "anotar_pendencia",
                        lambda nome, motivo, cliente=None: avisos.append(motivo))
    monkeypatch.setattr(processador, "log", lambda *a, **k: None)

    numero, fechou = com_os("GRADE 18.pdf", processador.VIVA, planos())
    assert numero is None
    assert fechou is False, "GEREMPRE fora do ar nao fecha OS nenhuma"
    assert avisos, "tinha de avisar que a OS nao saiu"
    assert "GEREMPRE" in avisos[0]
    assert "mao" in avisos[0].lower()


def test_o_verso_da_prova_sem_os_nao_derruba_nada():
    """Sem numero de OS nao ha verso, e a prova sai so na frente."""
    assert processador._verso_da_os(None) is None


def test_o_verso_da_prova_engole_erro_de_desenho(monkeypatch):
    """
    Falhar ao desenhar a folha da OS nao pode segurar a chapa: a prova
    sai so na frente, que e como saiu ate hoje.
    """
    monkeypatch.setattr(processador, "log", lambda *a, **k: None)
    monkeypatch.setattr(processador, "folha_da_os",
                        lambda n: (_ for _ in ()).throw(RuntimeError("x")))
    assert processador._verso_da_os(19570) is None


# ----------------------------------------------------------------------
# A busca por servico ja lancado: mesmo cliente, e recente
# ----------------------------------------------------------------------

class CursorFalso(object):
    """Guarda o SQL e os valores, e devolve o que mandarem."""

    def __init__(self, linhas=()):
        self.linhas = list(linhas)
        self.sqls = []
        self.valores = []

    def execute(self, sql, valores=()):
        self.sqls.append(sql)
        self.valores.append(list(valores))

    def fetchall(self):
        return self.linhas


def test_a_busca_limita_por_data_e_por_cliente():
    """
    Sem esses dois limites, o 'GRADE 40' da VIVA de 2026 casou com o
    'GRADE 40' da MESMA VIVA de 2024, e a prova saiu com o numero de uma
    OS de dois anos atras impresso no verso.
    """
    import datetime
    cur = CursorFalso()
    hoje = datetime.datetime(2026, 9, 9, 12, 0)
    gerempre.ja_esta_em_os(cur, "GRADE 40", "VIVA", quando=hoje)

    assert cur.sqls, "tinha de consultar"
    for sql in cur.sqls:
        assert "OSENTD >= ?" in sql, "faltou a janela de dias"
        assert "OSCLI = ?" in sql, "faltou o cliente"
    limite, codigo = cur.valores[0][1], cur.valores[0][2]
    assert limite == datetime.date(2026, 8, 10)     # 30 dias antes
    assert codigo == 511                            # a VIVA
    assert limite > datetime.date(2024, 8, 21), \
        "a OS de 2024 tem de ficar de fora"


def test_sem_cliente_a_busca_nao_filtra_por_cliente():
    """Quem nao souber o cliente ainda busca - so que mais largo."""
    cur = CursorFalso()
    gerempre.ja_esta_em_os(cur, "ALGO")
    assert all("OSCLI = ?" not in sql for sql in cur.sqls)
    assert all("OSENTD >= ?" in sql for sql in cur.sqls), \
        "a janela de dias vale sempre"


def test_entre_duas_os_recentes_vale_a_mais_nova():
    cur = CursorFalso([(19000, "GRADE 40"), (19575, "GRADE 40")])
    assert gerempre.ja_esta_em_os(cur, "GRADE 40", "VIVA") == 19575
