# -*- coding: utf-8 -*-
r"""
Qual pagina cai em que lugar - os tres processos da AMERICA.

O teste que mais importa aqui e o que le os MODELOS DO PREPS e compara
com o que o programa responde. Paginacao errada nao da erro em lugar
nenhum: a chapa grava limpa, a tiragem sai limpa, e o defeito aparece
depois de dobrado - um livro com o miolo fora de ordem.

Os modelos do Preps nao estao no Git (sao do programa, instalado na
maquina), entao esses testes PULAM quando o Preps nao esta ali. Os
outros valem em qualquer maquina.
"""

import io
import os
import re

import pytest

from finart_ctp import paginacao as P

PREPS = r"C:\Program Files (x86)\Creo\Preps 5.0\Templates\Sample Templates"


# ----------------------------------------------------------------------
# PARTE 1: que paginas sao de cada caderno
# ----------------------------------------------------------------------

def test_lombada_empilha_pedacos_seguidos():
    """
    Cadernos colados na lombada ficam LADO A LADO, entao cada um leva um
    pedaco seguido do livro.
    """
    cadernos = P.cadernos_do_livro(32, 16, P.LOMBADA)
    assert len(cadernos) == 2
    assert cadernos[0] == list(range(1, 17))
    assert cadernos[1] == list(range(17, 33))


def test_canoa_encaixa_um_dentro_do_outro():
    """
    Na canoa o grampo atravessa todos, entao o caderno de FORA carrega o
    comeco E o fim do livro, e o de dentro carrega o miolo.

    Abrindo o caderno 1 no meio veem-se as paginas 8 e 25 - e entre elas
    esta o caderno 2 inteiro. E o que acontece numa revista grampeada.
    """
    cadernos = P.cadernos_do_livro(32, 16, P.CANOA)
    assert len(cadernos) == 2
    assert cadernos[0] == list(range(1, 9)) + list(range(25, 33))
    assert cadernos[1] == list(range(9, 17)) + list(range(17, 25))


def test_canoa_de_um_caderno_so_e_o_livro_inteiro():
    """Uma revista de 16 paginas grampeada e um caderno so."""
    assert P.cadernos_do_livro(16, 16, P.CANOA) == [list(range(1, 17))]
    assert (P.cadernos_do_livro(16, 16, P.CANOA)
            == P.cadernos_do_livro(16, 16, P.LOMBADA))


def test_os_dois_processos_usam_cada_pagina_uma_vez():
    """
    A conferencia que nao depende de eu entender dobra: junta tudo e
    tem de dar 1..N, sem repetir e sem faltar.
    """
    for processo in (P.CANOA, P.LOMBADA):
        for paginas, por_caderno in ((64, 16), (48, 16), (32, 8), (96, 8)):
            juntas = []
            for c in P.cadernos_do_livro(paginas, por_caderno, processo):
                juntas.extend(c)
            assert sorted(juntas) == list(range(1, paginas + 1)), (
                "%s, %d paginas em cadernos de %d"
                % (processo, paginas, por_caderno))


def test_caderno_que_nao_fecha_PARA():
    """
    Uma folha dobrada da 4 paginas. Caderno de 6 nao existe, e sobra de
    pagina e decisao de gente - pagina em branco no fim muda o livro.
    """
    with pytest.raises(P.NaoSeiPaginar):
        P.cadernos_do_livro(32, 6, P.CANOA)
    with pytest.raises(P.NaoSeiPaginar) as e:
        P.cadernos_do_livro(30, 16, P.CANOA)
    assert "sobram" in str(e.value)


def test_folha_solta_nao_tem_caderno():
    """E o programa diz isso em voz alta, em vez de devolver lista vazia."""
    with pytest.raises(P.NaoSeiPaginar) as e:
        P.cadernos_do_livro(14, 4, P.FOLHA_SOLTA)
    assert "nao tem caderno" in str(e.value)


# ----------------------------------------------------------------------
# PARTE 2: a dobra, conferida contra os modelos do Preps
# ----------------------------------------------------------------------

def _paginas_do_modelo(arquivo, caderno):
    """
    [(frente, verso)] de um caderno de um .tpl, EM ORDEM DE LEITURA.

    Le o arquivo de verdade - nao ha copia dos numeros aqui.

    A ORDENACAO E O PULO DO GATO, e ela custou a primeira rodada destes
    testes. O Preps grava os lugares na ordem do PostScript, em que o y
    cresce PARA CIMA: a fileira de baixo vem primeiro no arquivo. O
    catalogo do paginacao.py conta a linha de CIMA para BAIXO, que e a
    ordem em que se le uma tabela.

    Nenhuma das duas esta errada - sao a mesma chapa escrita de dois
    jeitos. Comparar sem ordenar acusaria diferenca onde nao ha, e foi
    o que aconteceu: '[(4,3), (1,2)] != [(1,2), (4,3)]' com as duas
    dizendo exatamente a mesma coisa.

    Entao ordena-se por POSICAO: de cima para baixo (-y), e dentro da
    fileira da esquerda para a direita (x).
    """
    caminho = os.path.join(PREPS, arquivo)
    lugares = []
    dentro = False
    for linha in io.open(caminho, encoding="latin-1", errors="replace"):
        if linha.startswith("%SSiSignature:"):
            achado = re.search(r"\|([^|]*)\|", linha)
            dentro = bool(achado) and achado.group(1) == caderno
        elif linha.startswith("%SSiPrshPage:") and dentro:
            n = [float(x) for x in re.findall(r"-?\d+\.?\d*", linha)]
            lugares.append((n[0], n[1], int(n[5]), int(n[6])))
    lugares.sort(key=lambda p: (-p[1], p[0]))
    return [(f, v) for _x, _y, f, v in lugares]


def _tem_preps():
    return os.path.isdir(PREPS)


sem_preps = pytest.mark.skipif(not _tem_preps(),
                               reason="o Preps nao esta nesta maquina")


@sem_preps
@pytest.mark.parametrize("arquivo", [
    os.path.join("Metric", "A4 Tutorial Saddle.tpl"),
    os.path.join("Metric", "A4 Tutorial PerfectBound.tpl"),
])
def test_a_dobra_de_16_e_a_do_preps(arquivo):
    """
    O arranjo escrito no paginacao.py e o do modelo, lugar por lugar.

    E OS DOIS MODELOS SAO IGUAIS - e por isso que canoa e lombada
    compartilham o arranjo: o Preps traz a mesma paginacao de 16 no
    tutorial de canoa e no de lombada.
    """
    do_preps = _paginas_do_modelo(arquivo, "16 page SW")
    meu = [(f, v) for _c, _l, _g, f, v
           in P.arranjo(16, P.FRENTE_E_VERSO)["celulas"]]
    assert meu == do_preps


@sem_preps
def test_canoa_e_lombada_dobram_IGUAL_no_preps():
    """
    A prova de que este modulo pode ter um arranjo so para os dois.

    Se um dia isto quebrar, e porque a casa dobra diferente nos dois - e
    ai o arranjo tem de deixar de ser compartilhado.
    """
    canoa = _paginas_do_modelo(os.path.join("Metric", "A4 Tutorial Saddle.tpl"),
                               "16 page SW")
    lombada = _paginas_do_modelo(
        os.path.join("Metric", "A4 Tutorial PerfectBound.tpl"), "16 page SW")
    assert canoa == lombada


@sem_preps
@pytest.mark.parametrize("caderno,vira", [
    ("8 page WT", P.BATE_VIRA),
    ("8 page SW", P.FRENTE_E_VERSO),
    ("4 page wt", P.BATE_VIRA),
])
def test_as_outras_dobras_sao_as_do_preps(caderno, vira):
    do_preps = _paginas_do_modelo(
        os.path.join("Metric", "A4 Tutorial Saddle.tpl"), caderno)
    quantas = int(re.match(r"(\d+)", caderno).group(1))
    meu = [(f, v) for _c, _l, _g, f, v in P.arranjo(quantas, vira)["celulas"]]
    assert meu == do_preps


def test_dobra_que_nao_conheco_PARA():
    """
    Nao ha formula de dobra aqui: ha catalogo lido de modelo. O que nao
    esta no catalogo para, dizendo o que conhece e onde procurar.
    """
    with pytest.raises(P.NaoSeiPaginar) as e:
        P.arranjo(32, P.FRENTE_E_VERSO)
    assert "nao tenho a dobra" in str(e.value)
    assert "ler_paginacao_preps" in str(e.value)


# ----------------------------------------------------------------------
# As duas partes juntas
# ----------------------------------------------------------------------

def test_cada_lugar_carrega_UMA_FOLHA_de_papel():
    """
    A invariante que prende a conta do encaixe inteira.

    Um lugar e um pedaco de papel, e um pedaco de papel tem uma frente e
    um verso que SAO A MESMA FOLHA do livro: as paginas 2i-1 e 2i. Se o
    encaixe da canoa estiver errado por um caderno que seja, algum lugar
    passa a juntar paginas de folhas diferentes e isto quebra.
    """
    for processo in (P.CANOA, P.LOMBADA):
        for livro in P.lugares_do_livro(64, 16, processo, P.FRENTE_E_VERSO):
            for _col, _lin, _giro, frente, verso in livro["lugares"]:
                par = tuple(sorted((frente, verso)))
                assert par[1] == par[0] + 1 and par[0] % 2 == 1, (
                    "%s, caderno %d: o lugar juntou %d com %d, que nao sao "
                    "a mesma folha" % (processo, livro["caderno"], frente,
                                       verso))


def test_o_livro_inteiro_sai_uma_vez_so():
    """De ponta a ponta: 64 paginas, 4 cadernos, nenhuma pagina perdida."""
    for processo in (P.CANOA, P.LOMBADA):
        vistas = []
        for livro in P.lugares_do_livro(64, 16, processo, P.FRENTE_E_VERSO):
            for _c, _l, _g, frente, verso in livro["lugares"]:
                vistas += [frente, verso]
        assert sorted(vistas) == list(range(1, 65))


def test_a_canoa_poe_a_ultima_pagina_no_caderno_de_FORA():
    """
    A diferenca visivel entre os dois processos, num numero so.

    Na canoa, a pagina 64 sai na MESMA chapa que a pagina 1 - as duas
    sao o caderno de fora. Na lombada, a 64 sai na ultima chapa.
    """
    canoa = P.lugares_do_livro(64, 16, P.CANOA, P.FRENTE_E_VERSO)
    lombada = P.lugares_do_livro(64, 16, P.LOMBADA, P.FRENTE_E_VERSO)

    def onde(livro, pagina):
        for c in livro:
            for _co, _l, _g, f, v in c["lugares"]:
                if pagina in (f, v):
                    return c["caderno"]
        return None

    assert onde(canoa, 1) == 1 and onde(canoa, 64) == 1
    assert onde(lombada, 1) == 1 and onde(lombada, 64) == 4


# ----------------------------------------------------------------------
# PARTE 3: folha solta
# ----------------------------------------------------------------------

def test_folha_solta_so_frente_uma_pagina_por_celula():
    lugares = P.lugares_de_folha_solta(4, 2, 2, P.SO_FRENTE)
    assert [(c, l, f, v) for c, l, _g, f, v in lugares] == [
        (1, 1, 1, 0), (2, 1, 2, 0),
        (1, 2, 3, 0), (2, 2, 4, 0)]


def test_folha_solta_frente_e_verso_duas_por_celula():
    """Cada celula e uma FOLHA: leva duas paginas, uma de cada lado."""
    lugares = P.lugares_de_folha_solta(8, 2, 2, P.FRENTE_E_VERSO)
    assert [(f, v) for _c, _l, _g, f, v in lugares] == [
        (1, 2), (3, 4), (5, 6), (7, 8)]


def test_folha_solta_deixa_celula_vazia_em_vez_de_inventar():
    """
    Sobrando celula, ela sai (0, 0) - e o painel ja a desenha tracejada.
    Inventar repeticao aqui seria decidir aproveitamento, que e do
    operador.
    """
    lugares = P.lugares_de_folha_solta(3, 2, 2, P.SO_FRENTE)
    assert [f for _c, _l, _g, f, _v in lugares] == [1, 2, 3, 0]


def test_folha_solta_que_nao_cabe_PARA():
    with pytest.raises(P.NaoSeiPaginar) as e:
        P.lugares_de_folha_solta(20, 2, 2, P.SO_FRENTE)
    assert "decisao de gente" in str(e.value)


# ----------------------------------------------------------------------
# O nome escrito na chapa
# ----------------------------------------------------------------------

def test_o_nome_do_caderno_e_o_que_o_operador_escreve():
    """
    'caderno 1 frente / caderno 1 verso' - pedido do operador em
    20/09/2026. Oito cadernos sao dezesseis chapas quase iguais, e
    trocar duas e um livro com o miolo fora de ordem.
    """
    assert P.nome_do_caderno(1, "frente") == "caderno 1 frente"
    assert P.nome_do_caderno(3, "verso") == "caderno 3 verso"
    assert P.nome_do_caderno(2) == "caderno 2"


def test_as_chapas_de_um_livro_saem_nomeadas_na_ordem():
    assert P.chapas_do_livro(32, 16, P.CANOA, P.FRENTE_E_VERSO) == [
        "caderno 1 frente", "caderno 1 verso",
        "caderno 2 frente", "caderno 2 verso"]


def test_no_bate_vira_o_caderno_e_UMA_chapa_so():
    """As duas metades saem na mesma chapa - nao ha frente e verso a dizer."""
    assert P.chapas_do_livro(16, 8, P.LOMBADA, P.BATE_VIRA) == [
        "caderno 1", "caderno 2"]
