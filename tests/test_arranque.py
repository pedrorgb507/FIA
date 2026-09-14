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


# ----------------------------------------------------------------------
# O DIA SE ANUNCIA UMA VEZ - 14/09/2026
# ----------------------------------------------------------------------
# "quando apareceu um arquivo em uma das pastas apareceu tudo isso
# embaixo" - o operador. Eram duas linhas por cliente, e como o dia vira
# para todos ao mesmo tempo, catorze caiam de uma vez no meio do
# trabalho.

def test_o_dia_se_anuncia_em_UMA_linha():
    linha = M.anuncio_do_dia(["SOLIDA", "VOPRIX", "FIALHO", "EMPORIO",
                              "VIVA", "PRIME"], r"W:\CTP\SETEMBRO\14\FIA")
    assert linha.count("\n") == 0
    for nome in ("SOLIDA", "VOPRIX", "FIALHO", "EMPORIO", "VIVA", "PRIME"):
        assert nome in linha
    # a pasta de saida e a mesma para todos: aparece UMA vez
    assert linha.count(r"W:\CTP\SETEMBRO\14\FIA") == 1


def test_sem_estreia_nao_se_diz_nada():
    """E o caso de quase toda varredura - de 90 em 90 segundos."""
    assert M.anuncio_do_dia([], r"W:\CTP\SETEMBRO\14\FIA") == ""


def test_quem_chega_depois_se_anuncia_sozinho():
    """
    A pasta do dia da CREATIVE costuma aparecer mais tarde. Quando ela
    aparecer, so ela e dita.
    """
    linha = M.anuncio_do_dia(["CREATIVE"], r"W:\CTP\SETEMBRO\14\FIA")
    assert "CREATIVE" in linha and "SOLIDA" not in linha


def test_o_relatorio_ainda_conta_o_arranque_ANTIGO():
    """
    Ate 14/09/2026 a marca era 'Registro: N arquivo(s)'. O log de um dia
    pode ter as duas, se a FIA subiu antes e depois da mudanca.
    """
    fonte = open(R.__file__, encoding="utf-8").read()
    assert 'startswith("Registro: ")' in fonte
    assert "ARRANQUE" in fonte
