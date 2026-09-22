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


# ----------------------------------------------------------------------
# A FRONTEIRA INTEIRA - e este teste nasceu de um defeito de verdade
# ----------------------------------------------------------------------

def test_TODO_cliente_vigiado_TEM_CODIGO_no_gerempre():
    """
    Cadastrar chapa e preco nao basta: sem o CODIGO DO CLIENTE a FIA nao
    consegue ABRIR OS nenhuma.

    22/09/2026, a IDEAL estreou e a segunda arte dela virou pendencia:

        cliente IDEAL nao esta ligado a nenhum codigo do GEREMPRE.
        Lance a mao

    E O JEITO COMO ISSO SE ESCONDEU VALE MAIS QUE O CONSERTO. A PRIMEIRA
    arte dela passou - porque a OS JA EXISTIA, lancada a mao pelo
    operador, e COMPLETAR uma OS nao precisa do codigo do cliente; so
    ABRIR uma nova precisa.

    Metade do cadastro funcionava. A metade que faltava so se revelaria
    no dia em que chegasse um servico sem OS pronta - podia ser hoje,
    podia ser semana que vem, e nesse dia a chapa sairia e a cobranca
    ficaria esperando alguem ler uma pendencia.

    E a mesma forma do defeito do 'hotmelt' na mesma manha: caminho que
    PARECE inteiro porque o caso que o exercita ainda nao passou.
    """
    from finart_ctp.config import GEREMPRE_CLIENTES

    sem_codigo = [nome for nome, _, _ in M.clientes()
                  if not GEREMPRE_CLIENTES.get(nome)]
    assert sem_codigo == [], (
        "vigiados e sem codigo no GEREMPRE - nao conseguem abrir OS: %s"
        % sem_codigo)


def test_TODO_cliente_com_codigo_TEM_CHAPA_com_preco():
    """
    O outro lado da mesma fronteira.

    Cliente com codigo e sem chapa abre a OS e nao sabe o que lancar
    nela - e a chapa ja foi gravada quando isso aparece. As duas listas
    moram em arquivos diferentes e precisam andar juntas.
    """
    from finart_ctp.config import GEREMPRE_CHAPAS, GEREMPRE_CLIENTES

    com_chapa = {chave[0] for chave in GEREMPRE_CHAPAS}
    sem_chapa = sorted(set(GEREMPRE_CLIENTES) - com_chapa)
    assert sem_chapa == [], (
        "tem codigo e nao tem chapa com preco: %s" % sem_chapa)


# ----------------------------------------------------------------------
# O NOME DA CHAPA - e a licao mais cara deste cadastro
# ----------------------------------------------------------------------

def test_o_nome_da_chapa_segue_o_padrao_da_VIVA():
    """
    Ordem do operador, 22/09/2026: "a forma que vc esta nomeando o
    arquivo da IDEAL nao e a correta quando voce envia para o ctp (...)
    o padrao pode seguir como da VIVA".

    Ate entao ela caia no padrao da SOLIDA, e NAO POR DECISAO: o
    nome_da_chapa nao tinha ramo para a IDEAL, entao ela escorregava
    para o nome_saida() do fim, que extrai a OS e devolve so o numero.
    As chapas de 22/09 sairam '116530.pdf' e '116546_v2.pdf'.

    E EU DOCUMENTEI O ERRO COMO SE FOSSE A REGRA. Na skill eu tinha
    escrito, por suposicao, '510x400_CMYK_IDEAL_...'; vi sair '116530',
    concluí que a suposicao e que estava errada, e "corrigi" a skill
    para descrever o comportamento. O operador desfez: a suposicao
    estava certa, quem estava errado era o codigo.

    A LICAO VALE ALEM DESTE CLIENTE: o que o programa FAZ nao e a regra
    da casa. Ver o programa fazer X e escrever "a regra e X" troca um
    defeito por documentacao que o defende - e a documentacao dura mais
    que o defeito.
    """
    nome = P.nome_da_chapa(
        P.IDEAL, "OS 116530 - caixinha brasa express 26.pdf", "",
        510, 400, set("CMYK"), 0, 1)
    assert nome == "510x400_CMYK_IDEAL_OS 116530 - caixinha brasa express 26"
    assert not nome.startswith("116530"), (
        "voltou para o padrao da SOLIDA - so o numero da OS")


def test_a_chapa_grande_troca_o_formato_no_nome():
    """660x530 na frente, sem ninguem escrever a medida a mao."""
    nome = P.nome_da_chapa(
        P.IDEAL, "OS 116513 - Caixa Goberry_14x20x6.pdf", "",
        660, 530, set("CMYK"), 0, 1)
    assert nome.startswith("660x530_CMYK_IDEAL_")


def test_frente_e_verso_saem_F_e_V_como_na_VIVA():
    """Duas paginas viram F e V; tres ou mais, 1, 2, 3."""
    base = "OS 116396 - Miolo Caderno Acqua summer 2027.pdf"
    f = P.nome_da_chapa(P.IDEAL, base, "", 510, 400, set("CMYK"), 0, 2)
    v = P.nome_da_chapa(P.IDEAL, base, "", 510, 400, set("CMYK"), 1, 2)
    assert f.endswith(" F") and v.endswith(" V")


def test_as_TINTAS_do_nome_sao_as_que_a_arte_usa():
    """Arte so de preto nao leva CMYK no nome - e uma chapa, nao quatro."""
    so_k = P.nome_da_chapa(
        P.IDEAL, "OS 116530 - caixinha.pdf", "", 510, 400, set("K"), 0, 1)
    assert "_K_IDEAL_" in so_k, so_k
