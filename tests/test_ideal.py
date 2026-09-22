# -*- coding: utf-8 -*-
"""
A IDEAL - oitavo cliente, cadastrado em 22/09/2026.

E A PRIMEIRA A JUNTAR DUAS COISAS que ja existiam separadas:

  - DUAS chapas escolhidas pelo TAMANHO DA ARTE, como o EMPORIO;
  - arte que NAO vem no tamanho da chapa e e montada por programa -
    centralizada na largura, pinca no pe -, como a CREATIVE e a PRIME.

Ate aqui quem montava com pinca tinha UMA chapa so. Nada precisou mudar
no motor por causa disso: o montar_na_chapa ja percorria a tabela do
cliente e ficava na primeira que coubesse. Estes testes existem para
que continue assim.
"""
import sys

import pytest

from finart_ctp import monitor as M
from finart_ctp import processador as P
from finart_ctp.config import (FORMATOS_IDEAL, GEREMPRE_CHAPAS,
                               PINCA_IDEAL_MM, ROTULOS_PROVA_IDEAL)


# ----------------------------------------------------------------------
# A chapa sai do TAMANHO DA ARTE
# ----------------------------------------------------------------------

def test_cabendo_no_formato_4_vai_na_pequena():
    """
    Regra do operador: "quando as chapas couberem no formato 4, elas
    serao para a chapa 510x400".

    As medidas sao as dos PDF de setembro dele, lidas antes de escrever
    o cadastro - a maior era 500x320.
    """
    for larg, alt in ((500, 320), (480, 280), (440, 340), (370, 240),
                      (270, 270)):
        assert P.montar_na_chapa(larg, alt, P.IDEAL, corte=10.0) == (510, 400), (
            "arte %sx%s devia caber na pequena" % (larg, alt))


def test_maior_que_o_formato_4_vai_na_grande():
    """"quando o arquivo for maior do que o formato 4, ele sera para a
    chapa 660x530"."""
    for larg, alt in ((600, 400), (640, 480), (520, 300)):
        assert P.montar_na_chapa(larg, alt, P.IDEAL, corte=10.0) == (660, 530), (
            "arte %sx%s devia ir para a grande" % (larg, alt))


def test_o_que_nao_cabe_em_NENHUMA_nao_e_chutado():
    """
    Passando das duas, devolve None - e vira pendencia la na frente.

    Montagem errada nao da erro em lugar nenhum: grava limpa, imprime
    limpa, e o defeito aparece na guilhotina. Entre errar sozinha e
    parar para perguntar, para.
    """
    assert P.montar_na_chapa(700, 500, P.IDEAL, corte=10.0) is None
    assert P.montar_na_chapa(660, 520, P.IDEAL, corte=10.0) is None, (
        "660x520 mais a pinca passa de 530 de altura")


def test_A_ORDEM_DA_TABELA_E_QUE_ESCOLHE_A_PEQUENA():
    """
    A pequena vem PRIMEIRO, e nao e enfeite de arrumacao.

    O montar_na_chapa fica na primeira que couber. Invertendo a ordem
    da FORMATOS_IDEAL, TODO servico iria para a 660x530 - que custa
    R$ 35,00 contra R$ 18,75. Quase o dobro, em toda OS, sem nada dar
    erro em lugar nenhum.
    """
    assert list(FORMATOS_IDEAL) == [(510, 400), (660, 530)], (
        "a pequena tem de ser a primeira da tabela")


# ----------------------------------------------------------------------
# A PINCA
# ----------------------------------------------------------------------

def test_a_pinca_e_de_35mm():
    """3,5 cm, ditado pelo operador para as DUAS maquinas (GTO e ADAST)."""
    assert PINCA_IDEAL_MM == 35
    assert P.pinca_do_cliente(P.IDEAL) == 35


def test_a_pinca_se_mede_DA_MARCA_e_nao_da_borda():
    """
    A licao que ja custou uma chapa 12 mm fora do lugar na CREATIVE.

    Nos PDF da IDEAL a marca fica a ~10 mm do pe do arquivo. A arte
    entao assenta a 35-10 = 25 mm da borda da chapa, e a MARCA cai nos
    35 pedidos. Medir da borda do arquivo poria tudo 10 mm acima.
    """
    chapa = (510, 400)
    _, topo = P.posicao_na_chapa(500, 320, chapa, P.IDEAL, corte=10.0)
    # topo = altura da chapa - base - altura da arte
    assert topo == pytest.approx(400 - (35 - 10) - 320)
    # e a MARCA fica exatamente na pinca
    base_da_arte = 400 - topo - 320
    assert base_da_arte + 10 == pytest.approx(35), "a marca nao caiu na pinca"


def test_centralizada_na_largura():
    """Regra da casa desde a CREATIVE: centralizada na largura."""
    esquerda, _ = P.posicao_na_chapa(400, 300, (510, 400), P.IDEAL, corte=10.0)
    assert esquerda == pytest.approx((510 - 400) / 2.0)


# ----------------------------------------------------------------------
# O GEREMPRE
# ----------------------------------------------------------------------

def test_as_duas_chapas_sao_PROPRIAS_da_finart():
    """
    A IDEAL NAO TEM NENHUMA LINHA NA CHA (zero com CHACLI=133), e e isso
    que prova que ela nao traz chapa - se trouxesse, haveria saldo dela
    ali. As duas saem do estoque da casa.

    Trocar 'propria' por 'cliente' daria baixa no estoque errado: a
    Finart deixaria de baixar a chapa que gastou, e o saldo do cliente
    andaria sem ele ter trazido nada.
    """
    for medida in ((510, 400), (660, 530)):
        _, _, _, dono = GEREMPRE_CHAPAS[("IDEAL", medida)]
        assert dono == "propria", "%s devia ser chapa da Finart" % (medida,)


def test_os_precos_sao_os_que_o_banco_mostra():
    """
    Lidos em 22/09/2026, e um deles quase entrou errado.

      510x400  R$ 18,75  - 359 dos 369 lancamentos da IDEAL, da OS 6 ate
                           a 19889, a mais recente dela
      660x530  R$ 35,00  - 12 usos na casa, TODOS a 35,00

    O operador ditou "18,50" e o banco nao tem esse numero em lugar
    nenhum; ele confirmou o 18,75. Que o 35,00 dele tenha batido ao
    centavo foi o que fez a outra diferenca saltar.

    E CUIDADO AO RECONFERIR: OSVLU e o TOTAL DA LINHA, nao o unitario.
    'vlu=75' nao e um preco - sao quatro chapas a 18,75.
    """
    cod, nome, preco, _ = GEREMPRE_CHAPAS[("IDEAL", (510, 400))]
    assert (cod, preco) == (12, 18.75)
    assert nome == "510X400 - 0,15"

    cod, nome, preco, _ = GEREMPRE_CHAPAS[("IDEAL", (660, 530))]
    assert (cod, preco) == (16, 35.00)
    assert nome == "660X530 - 0,30", "a 660x530 da casa e a de 0,30"


def test_a_chapa_pequena_e_a_MESMA_da_voprix_e_da_creative():
    """
    Codigo 12 nos tres, e esta certo: chapa propria tem dono 0, e o dono
    e que separa o saldo. O que muda entre eles e o PRECO.

    A armadilha e a oposta, e a skill do gerempre a conta: ha chapas com
    o MESMO NOME e donos diferentes. CHA.CHACLI diz de quem e; o nome
    nao diz.
    """
    doze = set()
    for chave, valor in GEREMPRE_CHAPAS.items():
        if valor[0] == 12:
            doze.add(chave[0])
    assert {"IDEAL", "VOPRIX", "CREATIVE"} <= doze


# ----------------------------------------------------------------------
# A entrada e a prova
# ----------------------------------------------------------------------

def test_a_ideal_e_vigiada_e_so_em_PDF():
    """
    "as chapas vem em pdf" - o operador. E os nove arquivos de setembro
    dele sao todos .pdf.

    Nao se acrescenta extensao por via das duvidas: e assim que se
    comeca a processar o que ninguem mandou processar.
    """
    extensoes = dict((c[0], c[2]) for c in M.clientes()).get("IDEAL")
    assert extensoes == (".pdf",), "a IDEAL nao esta sendo vigiada, ou nao so em PDF"


def test_a_etiqueta_da_prova_diz_o_cliente_E_o_formato():
    """Quem pega o papel precisa saber de quem e a chapa e qual formato."""
    assert ROTULOS_PROVA_IDEAL[(510, 400)] == "IDEAL F4"
    assert ROTULOS_PROVA_IDEAL[(660, 530)] == "IDEAL F2"


def test_os_OUTROS_clientes_nao_foram_mexidos():
    """
    Cadastrar um cliente novo nao pode reescrever os que ja funcionam.

    Este e o teste que eu quereria ter tido nas outras vezes: mexer em
    pinca_do_cliente e formatos_do_cliente toca codigo que sete clientes
    atravessam todo dia.
    """
    assert P.pinca_do_cliente(P.CREATIVE) == 40
    assert P.pinca_do_cliente(P.PRIME) == 28
    assert P.pinca_do_cliente(P.SOLIDA) == 0
    assert P.pinca_do_cliente(P.EMPORIO) == 0, "o EMPORIO ja vem no tamanho"
    assert (510, 400) in P.formatos_do_cliente(P.EMPORIO)
    assert (660, 605) in P.formatos_do_cliente(P.EMPORIO), (
        "a chapa grande do EMPORIO e 660x605, nao a 660x530 da IDEAL")
