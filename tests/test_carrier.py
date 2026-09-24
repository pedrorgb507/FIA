# -*- coding: utf-8 -*-
"""
A CARRIER - o segundo cliente que chega por uma pasta PARA CTP.

Pedido do operador em 24/09/2026: "gostaria de acrescentar como cliente
a Carrier (...) preciso que faca o processo da america, crie uma pasta
PARA CTP, e quando jogarmos la dentro vc segue o caminho de conferir o
arquivo, a pinca, a chapa, enviar para o ctp, gerar a OS no gempre e
tirar a prova, como ja faz com america, 724x615 com 6cm de pinca, e
510X400 com pinca 3,2 cm".

O QUE MUDOU NO CODIGO, e por que nao foi copiar: o america.py tinha
'AMERICA' cravado em 1356 linhas. Duplica-lo daria dois modulos
envelhecendo separados, e cada conserto - a pinca medida da marca, a
copia guardada antes de apagar, a conferencia da chapa inteira - teria
de ser feito duas vezes. Entao o cliente virou PARAMETRO, com a AMERICA
de padrao: por isso os 68 testes que ja existiam nao mudaram uma linha.

ESTE ARQUIVO GUARDA OS DOIS LADOS: que a CARRIER responde com os numeros
dela, e que a AMERICA continua respondendo com os dela.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from finart_ctp import america                                # noqa: E402
from finart_ctp.config import (GEREMPRE_CHAPAS,               # noqa: E402
                               GEREMPRE_CLIENTES, PORTAO_AMERICA,
                               PORTAO_CARRIER, PORTOES)

COLORIDO = {"C", "M", "Y", "K"}
PEB = {"GRAY"}


# ----------------------------------------------------------------------
# As duas chapas, e as pincas que ele ditou
# ----------------------------------------------------------------------

def test_as_duas_chapas_da_carrier():
    assert america.chapa_de(510, 400, PORTAO_CARRIER) == (510, 400)
    assert america.chapa_de(724, 615, PORTAO_CARRIER) == (724, 615)


def test_as_pincas_ditadas_pelo_operador():
    """'724x615 com 6cm de pinca, e 510X400 com pinca 3,2 cm'."""
    assert america.pinca_de((510, 400), PORTAO_CARRIER) == 32.0
    assert america.pinca_de((724, 615), PORTAO_CARRIER) == 60.0


def test_a_chapa_da_AMERICA_nao_serve_a_CARRIER():
    """
    A prova de que a tabela e mesmo por cliente. A 525x459 e da AMERICA;
    pedindo-a a CARRIER, nao ha chapa - e vice-versa.
    """
    assert america.chapa_de(525, 459, PORTAO_CARRIER) is None
    assert america.chapa_de(510, 400, PORTAO_AMERICA) is None


# ----------------------------------------------------------------------
# Qual chapa recebe o trabalho
# ----------------------------------------------------------------------

def test_o_que_cabe_no_formato_4_vai_na_pequena():
    chapa, _ = america.onde_montar(300, 200, COLORIDO, PORTAO_CARRIER)
    assert chapa == (510, 400)


def test_o_que_passa_do_formato_4_vai_na_grande():
    chapa, _ = america.onde_montar(700, 500, COLORIDO, PORTAO_CARRIER)
    assert chapa == (724, 615)


def test_na_CARRIER_o_PRETO_E_BRANCO_nao_muda_de_chapa():
    """
    A AMERICA manda peb para a MOZP e colorido para a SM_74 - sao
    MAQUINAS diferentes. A CARRIER nao tem essa divisao: as chapas dela
    sao da FINART e nao carregam nome de maquina.

    Copiando a regra da AMERICA para ca sem pensar, este teste cai.
    """
    # 600x450 de proposito: cabe NAS DUAS chapas grandes da AMERICA,
    # entao a escolha ali e mesmo pela cor e nao por caber. Com 700x500
    # a MOZP nao caberia e a comparacao nao provaria nada.
    colorida, _ = america.onde_montar(600, 450, COLORIDO, PORTAO_CARRIER)
    preta, _ = america.onde_montar(600, 450, PEB, PORTAO_CARRIER)
    assert colorida == preta == (724, 615)


def test_na_AMERICA_o_PRETO_E_BRANCO_CONTINUA_mudando_de_chapa():
    """O outro lado: nada do que eu fiz mexeu na regra dela."""
    colorida, _ = america.onde_montar(600, 450, COLORIDO, PORTAO_AMERICA)
    preta, _ = america.onde_montar(600, 450, PEB, PORTAO_AMERICA)
    assert colorida == (745, 605), "colorido grande vai na SM_74"
    assert preta == (650, 550), "preto e branco grande vai na MOZP"


def test_o_que_nao_cabe_PARA_dizendo_o_cliente():
    chapa, porque = america.onde_montar(2000, 2000, COLORIDO, PORTAO_CARRIER)
    assert chapa is None
    assert "CARRIER" in porque


# ----------------------------------------------------------------------
# O dpi e o nome da chapa
# ----------------------------------------------------------------------

def test_o_dpi_e_1000_na_pequena_e_800_na_grande():
    """
    Regra da casa, nao invencao: 1000 na pequena como em todo cliente, e
    800 acima do formato 4 - chapa grande em 1000 da arquivo enorme sem
    ninguem ver diferenca.
    """
    assert america.dpi_da_america((510, 400), PORTAO_CARRIER) == 1000
    assert america.dpi_da_america((724, 615), PORTAO_CARRIER) == 800


def test_o_nome_da_chapa_segue_o_padrao_DA_CASA():
    """
    <formato>_<cores>_<CLIENTE>_<descricao>. Nao e invencao minha: e o
    que os operadores ja escrevem a mao no CTP -
    '510X400_CMYK_VOPRIX_Calendario_Mesa_LAS_01' e
    '745x605_GRAY_APARECIDA_Einstein_Env_Kraft'.
    """
    nome = america.nome_da_chapa("x/ADESIVOS BOLAS_MONTAGEM.pdf",
                                 510, 400, COLORIDO, PORTAO_CARRIER)
    assert nome == "510x400_CMYK_CARRIER_ADESIVOS BOLAS"


def test_o_nome_da_AMERICA_continua_dizendo_AMERICA():
    nome = america.nome_da_chapa("x/Flyer_MONTAGEM.pdf",
                                 525, 459, COLORIDO, PORTAO_AMERICA)
    assert nome == "525x459_CMYK_AMERICA_Flyer"


# ----------------------------------------------------------------------
# As pastas
# ----------------------------------------------------------------------

def test_a_CARRIER_tem_SO_a_PARA_CTP():
    """
    'crie uma pasta PARA CTP' - o operador. A montagem dela e feita a mao
    por eles, fora da FIA, entao a PARA MONTAR nao teria quem a enchesse
    nem quem a esvaziasse. Pasta vazia que ninguem usa vira lugar onde
    arquivo se perde.
    """
    assert america.subpastas_do_dia(PORTAO_CARRIER) == ("PARA CTP",)


def test_a_AMERICA_continua_com_as_DUAS():
    subs = america.subpastas_do_dia(PORTAO_AMERICA)
    assert "PARA CTP" in subs and "PARA MONTAR" in subs


def test_a_pasta_vem_do_config_local_e_nao_do_de_fabrica():
    """
    A ARMADILHA EM QUE EU CAI AO ESCREVER ISTO, e que o config ja
    documentava no CAIXAS_TEAMS: o descritor guarda o NOME da
    configuracao, nao o valor, porque o config_local e aplicado DEPOIS do
    bloco dos portoes. Guardando o valor, a AMERICA ficava apontando para
    a pasta de fabrica, que nao existe nesta maquina.

    Portao apontado para pasta errada NAO DA ERRO: ele so nunca acha
    arquivo nenhum, para sempre, em silencio.
    """
    import finart_ctp.config as C
    for portao in PORTOES:
        assert isinstance(portao["base"], str)
        assert portao["base"].startswith("BASE_"), (
            "o portao tem de guardar o NOME da configuracao")
        assert getattr(C, portao["base"])


# ----------------------------------------------------------------------
# O GEREMPRE
# ----------------------------------------------------------------------

def test_a_CARRIER_esta_cadastrada_no_gerempre():
    """479, 'GRAFICA CARRIER' - a unica com esse nome no cadastro."""
    assert GEREMPRE_CLIENTES["CARRIER"] == 479


def test_as_chapas_sao_DA_FINART_e_os_precos_batem_com_o_banco():
    """
    'os valores no gerempre sao as chapas da FINART, o cliente nao
    fornece, chapa pequena 20,00 e chapa grande 35,00' - o operador.

    Conferido contra as 200 OS mais recentes do cliente 479 ANTES de
    escrever, como manda a armadilha 14: item 12 a R$ 20,00 em 235 de 236
    lancamentos, item 17 a R$ 35,00 em 174 de 174, os dois com
    RBCHAPAPRO = 1.

    'propria' e o que faz a baixa sair do estoque da FINART. Trocar por
    'cliente' baixaria chapa de quem nao a forneceu - e isso nao da erro
    em lugar nenhum, so um estoque que nao fecha no fim do mes.
    """
    pequena = GEREMPRE_CHAPAS[("CARRIER", (510, 400))]
    grande = GEREMPRE_CHAPAS[("CARRIER", (724, 615))]
    assert pequena[0] == 12 and pequena[2] == 20.00
    assert pequena[3] == "propria"
    assert grande[0] == 17 and grande[2] == 35.00
    assert grande[3] == "propria"


def test_TODA_chapa_do_portao_tem_cadastro_no_gerempre():
    """
    Senao a chapa grava e a OS nao sai - foi o que aconteceu com a IDEAL,
    cujo cadastro de cliente faltava e so apareceu no SEGUNDO arquivo,
    porque completar OS que ja existe nao precisa do codigo do cliente.
    """
    for portao in PORTOES:
        cliente = portao["cliente"]
        assert cliente in GEREMPRE_CLIENTES, cliente
        for medida in portao["chapas"]:
            assert (cliente, medida) in GEREMPRE_CHAPAS, (cliente, medida)


def test_os_dois_portoes_estao_na_lista_que_o_vigia_varre():
    assert [p["cliente"] for p in PORTOES] == ["AMERICA", "CARRIER"]


def test_a_pasta_do_dia_de_CADA_portao_sai_na_base_DELE(tmp_path,
                                                        monkeypatch):
    """
    O DEFEITO MUDO DE 24/09/2026: o garantir_pastas_do_dia montava o
    caminho com BASE_AMERICA mesmo recebendo o portao da CARRIER, e
    criou a pasta da CARRIER DENTRO da AMERICA.

    E nao deu erro nenhum - ele respondeu 'ja existiam', porque a PARA
    CTP da AMERICA existe mesmo. So olhando o caminho impresso e que
    apareceu.

    Por isso este teste olha ONDE a pasta foi parar, e nao se a chamada
    deu certo.
    """
    import finart_ctp.config as C
    casa_carrier = tmp_path / "carrier"
    casa_america = tmp_path / "america"
    monkeypatch.setattr(C, "BASE_CARRIER", str(casa_carrier))
    monkeypatch.setattr(C, "BASE_AMERICA", str(casa_america))

    dia, _, erro = america.garantir_pastas_do_dia(portao=PORTAO_CARRIER)
    assert erro is None
    assert str(casa_carrier) in dia, "a CARRIER saiu fora da base dela"
    assert str(casa_america) not in dia
    assert os.path.isdir(os.path.join(dia, "PARA CTP"))
    # e a PARA MONTAR NAO se cria aqui - ela nao tem quem a use
    assert not os.path.isdir(os.path.join(dia, "PARA MONTAR"))
    # a AMERICA nem foi tocada
    assert not casa_america.exists()
