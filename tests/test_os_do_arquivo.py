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
    assert processador._os_do_arquivo("ALGO.pdf", processador.VIVA,
                                      planos()) is None


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
                        lambda nome, motivo: avisos.append(motivo))
    monkeypatch.setattr(processador, "log", lambda *a, **k: None)

    assert com_os("GRADE 18.pdf", processador.VIVA, planos()) is None
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
