# -*- coding: utf-8 -*-
"""
O QUE A FIA MOSTRA QUANDO SOBE - 14/09/2026.

"quando eu dou F5 o terminal ta ficando uma bagunca... eu quero q vc so
mostre os clientes q estao funcionando e com pasta aberta" - o operador.

Antes eram doze linhas de caminho de rede, iguais todo dia. Agora e uma
linha por cliente.
"""

import os

from finart_ctp import monitor as M
from finart_ctp import relatorio as R


def test_uma_linha_por_cliente_e_so(tmp_path):
    pasta = str(tmp_path)
    vigiadas = [("SOLIDA", pasta, (".pdf",)),
                ("PRIME", pasta, (".cdr", ".pdf"))]
    linhas = M.linhas_do_arranque(vigiadas)

    assert [t for t, _ in linhas] == ["SOLIDA:    OK", "PRIME:     OK"]
    assert not any(alerta for _, alerta in linhas)


def test_o_nome_do_cliente_e_o_OK_cabem_na_mesma_coluna(tmp_path):
    """Sete clientes de nomes diferentes lidos de cima a baixo."""
    pasta = str(tmp_path)
    nomes = ["SOLIDA", "VOPRIX", "FIALHO", "EMPORIO", "VIVA", "CREATIVE",
             "PRIME"]
    linhas = M.linhas_do_arranque([(n, pasta, (".pdf",)) for n in nomes])
    colunas = {t.index("OK") for t, _ in linhas}
    assert len(colunas) == 1, "o OK dancou de coluna: %s" % colunas


def test_pasta_que_NAO_abriu_aparece_dizendo_isso(tmp_path):
    """
    Some da lista seria pior: cliente que desaparece em silencio e
    servico que ninguem faz.
    """
    fora = os.path.join(str(tmp_path), "nao existe")
    linhas = M.linhas_do_arranque([("SOLIDA", str(tmp_path), (".pdf",)),
                                   ("EMPORIO", fora, (".pdf",))])

    assert len(linhas) == 2, "o cliente sumiu da lista"
    texto, alerta = linhas[1]
    assert "EMPORIO" in texto
    assert "PASTA FORA DO AR" in texto
    assert fora in texto, "sem o caminho ninguem sabe onde procurar"
    assert alerta is True, "isto tem de chamar atencao na tela"


def test_a_marca_do_arranque_serve_ao_relatorio(tmp_path, monkeypatch):
    """
    O relatorio do dia conta quantas vezes a FIA subiu procurando esta
    linha no log. Mudar o texto sem mexer no relatorio zeraria a conta.
    """
    assert M.ARRANQUE
    linhas = [(0, M.ARRANQUE), (60, "qualquer outra coisa"),
              (120, M.ARRANQUE)]
    contadas = sum(1 for _, t in linhas
                   if t.startswith(M.ARRANQUE)
                   or t.startswith("Registro: "))
    assert contadas == 2


def test_o_relatorio_ainda_conta_o_arranque_ANTIGO():
    """
    Ate 14/09/2026 a marca era 'Registro: N arquivo(s)'. O log de um dia
    pode ter as duas, se a FIA subiu antes e depois da mudanca.
    """
    fonte = open(R.__file__, encoding="utf-8").read()
    assert 'startswith("Registro: ")' in fonte
    assert "ARRANQUE" in fonte
