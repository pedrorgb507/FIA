# -*- coding: utf-8 -*-
"""
A PRIME - setimo cliente, 14/09/2026.

Ela junta o que ja existia separado: chega em .cdr como a VOPRIX e e
montada na chapa com pinca como a CREATIVE. A pinca sao 28 mm, medidos
DA MARCA DE CORTE.

TODO NUMERO AQUI FOI MEDIDO nos arquivos de 14/09/2026, e conferido
contra o que o GEREMPRE cobrou na OS 19704. Nada e combinado de cabeca.
"""

import pytest

from finart_ctp import config as C
from finart_ctp import gerempre as G
from finart_ctp import marcas as MC
from finart_ctp import processador as P
from finart_ctp.nomes import nome_saida_prime


# ----------------------------------------------------------------------
# A PINCA
# ----------------------------------------------------------------------

def test_a_pinca_da_prime_e_de_28_mm():
    assert P.pinca_do_cliente(P.PRIME) == 28
    assert P.pinca_do_cliente(P.SOLIDA) == 0, "pinca nao se herda"


def test_a_arte_menor_e_montada_na_chapa_pela_MARCA():
    """
    O servico inteiro, medido no 'POLIPECAS - ETQIEUTAS' de 14/09/2026.
    A pasta guarda as duas pontas: a copia de seguranca do Corel (antes
    do operador) e o arquivo salvo (depois).

        COMO CHEGA   pagina 330 x 320, marca de corte a 17,5 mm do pe
        COMO SAI     pagina 510 x 400, 96,4 mm de cada lado,
                     MARCA a 28,0 mm do pe da chapa
    """
    chapa = P.montar_na_chapa(330, 320, P.PRIME, corte=17.5)
    assert chapa == (510, 400)

    esquerda, topo = P.posicao_na_chapa(330, 320, chapa, P.PRIME, corte=17.5)
    assert esquerda == pytest.approx(90.0)
    assert topo == pytest.approx(69.5)

    # a MARCA cai onde o operador a pos: 28 mm do pe da chapa
    marca_no_pe = 400 - (topo + 320) + 17.5
    assert marca_no_pe == pytest.approx(28.0)

    # e a tinta cai onde ela esta no arquivo do operador: a borda do
    # desenho fica a 6,3 mm da esquerda e 4,1 mm do topo da pagina dele
    assert esquerda + 6.3 == pytest.approx(96.4, abs=0.2)
    assert topo + 4.1 == pytest.approx(73.3, abs=0.4)


def test_a_pinca_se_mede_da_marca_e_NAO_da_borda_do_arquivo():
    """
    Medir da borda poria a arte 17,5 mm fora do lugar - e foi esse
    mesmo erro, com 12 mm, que o operador pegou na CREATIVE.
    """
    chapa = (510, 400)
    _, com_marca = P.posicao_na_chapa(330, 320, chapa, P.PRIME, corte=17.5)
    _, sem_marca = P.posicao_na_chapa(330, 320, chapa, P.PRIME, corte=0.0)
    # sem a marca a arte encosta 17,5 mm mais ALTO - a pinca sobraria
    # grande e o corte cairia fora do lugar
    assert com_marca - sem_marca == pytest.approx(17.5)


def test_DUAS_marcas_vale_a_de_CIMA():
    """
    "pode acontecer de vir com duas marcas, voce sempre deve pincar a
    partir do de cima" - o operador.

    Os numeros sao do 'O.S 1034 - WAN SEMANA DO CLIENTE', que e esse
    caso e esta escrito assim dentro do arquivo:

        y = 8,00 mm do pe   esquerda e direita, 4,02 mm  <- a sangria
        y = 9,96 mm do pe   esquerda e direita, 4,02 mm  <- o CORTE
    """
    tracos = [(8.00, 0.4, 4.02), (8.00, 434.7, 4.02),
              (9.96, 0.4, 4.02), (9.96, 434.7, 4.02)]
    achada = MC._dos_dois_lados(tracos, 440.0, lambda y: y)
    assert achada == pytest.approx(9.96, abs=MC.JUNTAS_MM)
    assert achada > 8.0, "pegou a de baixo - a chapa sairia 2 mm fora"


def test_marca_de_um_lado_so_NAO_conta():
    """Linha de desenho cai de um lado; marca aparece nos dois."""
    tracos = [(9.96, 0.4, 4.02)]
    assert MC._dos_dois_lados(tracos, 440.0, lambda y: y) is None


def test_as_duas_marcas_nao_precisam_estar_na_altura_EXATA():
    """
    O 'O.S 1035 - MPGO CARTAZES' virou pendencia em 14/09/2026 com a
    marca desenhada e visivel na tela. Ela estava la, dos dois lados:

        esquerda  10,06 mm do pe
        direita    9,96 mm do pe

    0,10 mm e folga de desenho. O programa arredondava cada uma para uma
    grade de 0,3 mm - 10,2 e 9,9, baldes vizinhos - e concluia que a
    marca so aparecia de um lado. Agora a distancia se mede UMA CONTRA A
    OUTRA.
    """
    tracos = [(10.06, 0.4, 4.02), (9.96, 434.7, 4.02)]
    achada = MC._dos_dois_lados(tracos, 440.0, lambda y: y)
    assert achada is not None, "a marca esta desenhada e nao foi vista"
    assert achada == pytest.approx(10.01, abs=0.01), "vale a media das duas"


def test_alturas_LONGE_uma_da_outra_continuam_sendo_coisas_diferentes():
    """A folga nao pode virar porta: 2 mm e outra marca, nao a mesma."""
    tracos = [(12.0, 0.4, 4.02), (9.96, 434.7, 4.02)]
    assert MC._dos_dois_lados(tracos, 440.0, lambda y: y) is None


# ----------------------------------------------------------------------
# TINTA QUE E SO TRACO
# ----------------------------------------------------------------------
# A OS 19704 de 14/09/2026 tem tres itens e tres baixas de estoque:
# -1, -3 e -4. Cada teste abaixo e um deles.

def test_o_amarelo_de_traco_nao_vira_chapa():
    """
    'POLIPECAS - ETQIEUTAS': o amarelo tem 0,56% contra 52,46% das
    outras - 1,07%. O operador gravou CMK e a OS baixou -3.
    """
    cob = {"C": 0.5246, "M": 0.5242, "Y": 0.0056, "K": 0.5246}
    usadas, fora = P.sem_tinta_de_traco(cob, set("CMYK"))
    assert usadas == {"C", "M", "K"}
    assert fora == {"Y"}


def test_o_preto_sozinho_fica_sozinho():
    """'VALDINO - CHAPADO': CMY a 0,06% do K. A OS baixou -1."""
    cob = {"C": 0.0005, "M": 0.0005, "Y": 0.0005, "K": 0.9085}
    usadas, fora = P.sem_tinta_de_traco(cob, set("CMYK"))
    assert usadas == {"K"}


def test_a_quadricromia_de_verdade_fica_inteira():
    """
    'O.S 1034 - WAN SEMANA DO CLIENTE': a tinta mais fraca vale 38,7%
    da mais forte. A OS baixou -4, e nenhuma chapa pode faltar.
    """
    cob = {"C": 0.4547, "M": 0.4810, "Y": 0.5151, "K": 0.1993}
    usadas, fora = P.sem_tinta_de_traco(cob, set("CMYK"))
    assert usadas == set("CMYK")
    assert fora == set()


def test_a_proporcao_virou_PENEIRA_e_nao_decisao():
    """
    Ate 16/09/2026 a proporcao decidia sozinha, com 5%. Naquele dia ela
    bateu no proprio limite, e a razao vale mais que o numero:

        ciano da 'Pasta Agil Corretora' (VOPRIX)   5,23%  e TRACO
        K de arte colorida (test_voprix_fluxo)     6,45%  e TEXTO

    Nenhum limiar separa 5,23 de 6,45 - a proporcao nao sabe ONDE a
    tinta esta. Ela passou a levantar CANDIDATO, com folga (10%), e quem
    decide e 'tinta_aparece_sozinha'.
    """
    assert C.TINTA_QUE_E_SO_TRACO == 0.10
    assert 0.0523 < C.TINTA_QUE_E_SO_TRACO, "o ciano da Agil tem de ser visto"
    assert 0.0645 < C.TINTA_QUE_E_SO_TRACO, "o K de texto tambem, e ele FICA"
    assert C.TINTA_QUE_E_SO_TRACO < 0.387, "o WAN nem candidato e"


def test_a_peneira_levanta_o_candidato_e_o_WAN_nem_isso():
    """
    O caso de 16/09/2026, medido na chapa que saiu:

        C 0,00232  M 0,04433  Y 0,04432  K 0,01481

    O ciano vale 5,23% do magenta - vira candidato. Que ele NAO e cor do
    trabalho se prova por pixel, nao por limiar: a 300 dpi ha 8.209
    pixels com ciano e ZERO so com ciano.
    """
    agil = {"C": 0.00232, "M": 0.04433, "Y": 0.04432, "K": 0.01481}
    fica, candidatas = P.sem_tinta_de_traco(agil, set("CMYK"))
    assert candidatas == {"C"}, "so o ciano e candidato"
    assert fica == {"M", "Y", "K"}

    # o WAN e quadricromia de verdade: nem chega a ser candidato
    wan = {"C": 0.4547, "M": 0.4810, "Y": 0.5151, "K": 0.1993}
    assert P.sem_tinta_de_traco(wan, set("CMYK"))[1] == set()


def test_nao_conseguindo_medir_a_tinta_FICA(monkeypatch):
    """
    O erro seguro tem lado: chapa a mais na conta se conserta com uma
    conversa; chapa a menos no CTP so aparece na tiragem.
    """
    from finart_ctp import ghostscript as G
    assert G.tinta_aparece_sozinha("nao_existe.pdf", 1, "C") == (None, 0)
    assert G.tinta_aparece_sozinha("nao_existe.pdf", 1, "Z") == (None, 0)


def test_descartar_tinta_anda_POR_CLIENTE():
    """
    Tinta a menos e chapa que FALTA no CTP, e isso estraga tiragem. So
    entra cliente cujas chapas foram conferidas contra o GEREMPRE.

    A VOPRIX entrou em 16/09/2026, com o caso da Agil Corretora medido
    pixel a pixel.

    A AMERICA entrou em 21/09/2026, e o caso foi medido antes: dois
    arquivos de preto puro - 'Comanda_Barzim' e 'forro de bandeja' -
    saindo CMYK porque as cruzes de corte, DENTRO do corte, davam C
    0,0002 contra K 0,1090. O america.medir() decidia pelo LIMIAR_TINTA,
    que e 0,0001 absoluto, e nao pela proporcao. Quatro chapas gravadas e
    cobradas onde devia sair UMA - e o historico da casa confirma: o
    mesmo trabalho saiu em 1 chapa nas OS 3417, 8101 e 10935.
    """
    assert C.CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO == ("PRIME", "VOPRIX",
                                                       "AMERICA")


def test_a_prime_e_lida_SEM_o_perfil_do_corel():
    """
    A Corel embute um perfil em tudo que publica, e por ele o
    'POLIPECAS' le 53% de amarelo onde o arquivo tem 0,56%:

        com perfil   C 0,5311  M 0,5325  Y 0,5342  K 0,5144
        sem perfil   C 0,5246  M 0,5242  Y 0,0056  K 0,5246

    Contando pelo perfil sairiam QUATRO chapas; foram tres.
    """
    assert "PRIME" in C.CLIENTES_QUE_VEM_DO_COREL
    assert "VOPRIX" in C.CLIENTES_QUE_VEM_DO_COREL

    com_perfil = {"C": 0.5311, "M": 0.5325, "Y": 0.5342, "K": 0.5144}
    sem_perfil = {"C": 0.5246, "M": 0.5242, "Y": 0.0056, "K": 0.5246}
    assert P.sem_tinta_de_traco(com_perfil, set("CMYK"))[0] == set("CMYK")
    assert P.sem_tinta_de_traco(sem_perfil, set("CMYK"))[0] == {"C", "M", "K"}


def test_a_prime_junta_preto_composto_MAS_o_POLIPECAS_escapa():
    """
    A PRIME passou a juntar preto composto em 16/09/2026, a pedido do
    operador: "voce mandou alguns pretos em 4 cores, mas tem que ser so
    preto, como e a regra da voprix".

    Este teste existia dizendo o CONTRARIO, e o motivo dele estava certo
    pela metade. O medo era o 'POLIPECAS': lido COM o perfil ele parece
    preto composto, e junta-lo poria um servico de TRES cores em UMA.

    So que a PRIME **nunca e lida com o perfil** - ela esta em
    CLIENTES_QUE_VEM_DO_COREL, e a leitura dela e crua. E na leitura crua
    os dois casos se separam sozinhos, porque 'pagina_de_uma_cor' compara
    C, M e Y ENTRE SI:

        POLIPECAS   cru   C 0,5246  M 0,5242  Y 0,0056   -> Y ausente
        FICHA REF.  cru   C 0,0145  M 0,0145  Y 0,0145   -> as tres iguais

    O amarelo ausente denuncia o servico de tres cores; as tres iguais
    denunciam o preto composto. A protecao nao vinha da PRIME estar fora
    da lista - vinha de ela ser lida sem o perfil. Tirar o perfil e o que
    protege; a lista so diz quem tem permissao.
    """
    assert "PRIME" in C.CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO
    assert "PRIME" in C.CLIENTES_QUE_VEM_DO_COREL, "e o que protege"

    # o POLIPECAS, que NAO pode ser juntado
    polipecas_cru = {"C": 0.5246, "M": 0.5242, "Y": 0.0056, "K": 0.5246}
    assert not P.pagina_de_uma_cor(polipecas_cru), "tres cores, nao preto"
    assert not P.preto_so_no_K(polipecas_cru)

    # e como ele enganaria, se algum dia alguem o lesse com o perfil
    com_perfil = {"C": 0.5311, "M": 0.5325, "Y": 0.5342, "K": 0.5144}
    assert P.pagina_de_uma_cor(com_perfil), "e assim que ele engana"

    # o 'PREF INHUMAS - FICHA REFERENCIA' de 16/09/2026, que PODE
    ficha_cru = {"C": 0.0145, "M": 0.0145, "Y": 0.0145, "K": 0.0547}
    assert P.pagina_de_uma_cor(ficha_cru), "C=M=Y: preto composto"
    assert not P.preto_so_no_K(ficha_cru), "nao e preto PURO, e composto"


# ----------------------------------------------------------------------
# O NOME
# ----------------------------------------------------------------------

def test_o_nome_da_chapa_leva_o_nome_INTEIRO():
    """Lido das chapas que os operadores fecharam a mao em 14/09/2026."""
    assert nome_saida_prime("POLIPECAS - ETQIEUTAS.cdr", "510x400",
                            {"C", "M", "K"}) == \
        "510x400_CMK_PRIME_POLIPECAS - ETQIEUTAS"
    assert nome_saida_prime("VALDINO - CHAPADO.cdr", "510x400",
                            {"GRAY"}) == "510x400_GRAY_PRIME_VALDINO - CHAPADO"
    assert nome_saida_prime("O.S 1034 - WAN SEMANA DO CLIENTE.cdr",
                            "510x400", set("CMYK")) == \
        "510x400_CMYK_PRIME_O.S 1034 - WAN SEMANA DO CLIENTE"


def test_o_processador_usa_a_regra_da_prime():
    assert P.nome_da_chapa(P.PRIME, "VALDINO - CHAPADO.cdr", "", 510, 400,
                           {"GRAY"}, 0, 1) == \
        "510x400_GRAY_PRIME_VALDINO - CHAPADO"


# ----------------------------------------------------------------------
# DOIS SERVICOS NAO SAO UM SO
# ----------------------------------------------------------------------
# "sao dois servicos diferentes, nao pode ler somente o primeiro nome,
# ou o numero da OS, para pensar que e o mesmo servico... tem que ler
# todo o nome e comparar" - o operador, 14/09/2026.

class CursorFalso(object):
    """Devolve sempre as mesmas OS, seja qual for o SQL."""

    def __init__(self, linhas):
        self.linhas = linhas

    def execute(self, sql, valores=None):
        pass

    def fetchall(self):
        from test_gerempre import com_data
        return com_data(self.linhas)


def test_o_montagem_e_OUTRO_servico(monkeypatch):
    """
    Os dois estavam na pasta em 14/09/2026, com o mesmo numero de O.S
    do cliente na frente. Cada um virou uma chapa e um item da OS.
    """
    monkeypatch.setattr(G, "GEREMPRE_CLIENTES", {"PRIME": 502})
    cur = CursorFalso([(19704, "O.S 1034 - WAN SEMANA DO CLIENTE")])

    assert G.ja_esta_em_os(cur, "O.S 1034 - WAN SEMANA DO CLIENTE",
                           "PRIME") == 19704
    assert G.ja_esta_em_os(cur, "O.S 1034 - WAN SEMANA DO CLIENTE_montagem",
                           "PRIME") is None, \
        "leu so o comeco do nome e achou que era o mesmo servico"


def test_o_numero_da_OS_do_cliente_sozinho_nao_casa(monkeypatch):
    """A PRIME poe a O.S DELA na frente, e ela se repete entre servicos."""
    monkeypatch.setattr(G, "GEREMPRE_CLIENTES", {"PRIME": 502})
    cur = CursorFalso([(19704, "O.S 1034 - WAN SEMANA DO CLIENTE")])
    assert G.ja_esta_em_os(cur, "O.S 1034 - SEDUC BLOCO", "PRIME") is None


def test_a_prime_nao_entra_na_regra_de_OS_repetida_da_fila():
    """
    'O.S 1034' tem quatro digitos e 'extrair_oss' o leria como numero de
    OS nossa. A regra 'dois arquivos com a MESMA OS param' so vale para
    quem traz a NOSSA OS no nome - a SOLIDA e o EMPORIO.
    """
    assert "PRIME" not in C.CLIENTES_COM_OS_NO_NOME


def test_nome_COMPRIDO_reconhece_o_que_a_PROPRIA_FIA_lancou(monkeypatch):
    """
    O banco guarda 50 letras. O que a FIA grava num nome comprido e o
    titulo PARTIDO - comeco, '..' e o fim -, e e por ele que ela
    reconhece o proprio lancamento quando o arquivo volta. Sem isso,
    abriria OS de novo e faturaria duas vezes.
    """
    monkeypatch.setattr(G, "GEREMPRE_CLIENTES", {"PRIME": 502})
    inteiro = "O.S 1167 - SEDS RACISMO CARTAZ INSTITUCIONAL A3 FRENTE E VERSO"
    assert len(inteiro) > G.LETRAS_NO_TITULO
    cur = CursorFalso([(19800, G.titulo_da_vaga(inteiro))])
    assert G.ja_esta_em_os(cur, inteiro, "PRIME") == 19800


def test_nome_COMPRIDO_cortado_A_MAO_pela_PRIME_e_DUVIDA(monkeypatch):
    """
    Quando quem lancou foi uma pessoa, no Delphi, o banco guarda o
    comeco cru - as 50 primeiras letras. Na PRIME isso NAO identifica o
    servico: a 'O.S 1034' dela se repete entre trabalhos (ver o teste
    acima), entao dois cartazes da mesma O.S tem o mesmo comeco.

    A FIA nao chuta: nao devolve numero, e anota a duvida para quem
    chamou parar e perguntar.
    """
    monkeypatch.setattr(G, "GEREMPRE_CLIENTES", {"PRIME": 502})
    inteiro = "O.S 1167 - SEDS RACISMO CARTAZ INSTITUCIONAL A3 FRENTE E VERSO"
    cur = CursorFalso([(19800, inteiro[:G.LETRAS_NO_TITULO])])

    duvidas = []
    assert G.ja_esta_em_os(cur, inteiro, "PRIME", None, duvidas) is None
    assert duvidas == [(19800, inteiro[:G.LETRAS_NO_TITULO])]


# ----------------------------------------------------------------------
# A CHAPA E O DINHEIRO
# ----------------------------------------------------------------------

def test_a_chapa_da_prime_e_do_CLIENTE():
    """
    1093 lancamentos no GEREMPRE, todos com dono 502. Errar isso baixa
    estoque de quem nao forneceu.
    """
    codigo, nome, preco, tipo = C.GEREMPRE_CHAPAS[("PRIME", (510, 400))]
    assert (codigo, nome, preco, tipo) == \
        (88, "510X400 - PRIME F4", 10.00, "cliente")


def test_a_prime_esta_cadastrada_no_gerempre():
    assert C.GEREMPRE_CLIENTES["PRIME"] == 502


def test_a_prime_so_tem_a_chapa_pequena():
    assert P.formatos_do_cliente(P.PRIME) == {(510, 400): (1000, "")}
    assert P.formatos_do_cliente(P.PRIME)[(510, 400)][0] == 1000, \
        "o operador pediu 1000 dpi"


def test_todo_formato_que_a_prime_FECHA_ela_sabe_COBRAR():
    for medida in P.formatos_do_cliente(P.PRIME):
        assert ("PRIME", medida) in C.GEREMPRE_CHAPAS, medida


def test_a_prova_da_prime_tem_rotulo():
    assert P.rotulo_prova(510, 400, P.PRIME) == "PRIME F4"


# ----------------------------------------------------------------------
# A MONTAGEM FICA NA PASTA DO DIA
# ----------------------------------------------------------------------
# "voce vai salvar de novo na pasta do dia com o mesmo nome mas
# _montagem no final... depois disso vai pegar essa montagem e continuar
# o procedimento normalmente" - o operador, 14/09/2026.

def _pdf_de_teste(caminho, larg_pt, alt_pt, origem=(0, 0)):
    """Uma pagina com um retangulo preto, para ter o que deslocar."""
    from pypdf import PageObject, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject, RectangleObject

    pag = PageObject.create_blank_page(width=larg_pt, height=alt_pt)
    pag.mediabox = RectangleObject((origem[0], origem[1],
                                    origem[0] + larg_pt, origem[1] + alt_pt))
    fluxo = DecodedStreamObject()
    fluxo.set_data(b"0 0 0 rg %d %d 50 30 re f" % origem)
    pag[NameObject("/Contents")] = fluxo
    escritor = PdfWriter()
    escritor.add_page(pag)
    with open(caminho, "wb") as f:
        escritor.write(f)
    return caminho


def _translacao(caminho):
    """(tx, ty) em pontos, lidos do 'cm' que a montagem escreveu."""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream

    leitor = PdfReader(caminho)
    pagina = leitor.pages[0]
    fluxo = ContentStream(pagina.get_contents(), leitor)
    for operandos, operador in fluxo.operations:
        if operador == b"cm":
            return float(operandos[4]), float(operandos[5])
    raise AssertionError("a montagem nao deslocou nada")


def test_a_montagem_sai_no_TAMANHO_DA_CHAPA(tmp_path):
    from pypdf import PdfReader

    origem = _pdf_de_teste(str(tmp_path / "arte.pdf"), 200, 100)
    destino = str(tmp_path / "arte_montagem.pdf")
    P.salvar_montagem(origem, 1, destino, (510, 400), 90.0, 10.5)

    caixa = PdfReader(destino).pages[0].mediabox
    assert round(float(caixa.width) / 72 * 25.4, 1) == 510.0
    assert round(float(caixa.height) / 72 * 25.4, 1) == 400.0


def test_a_montagem_poe_a_arte_ONDE_A_PINCA_MANDA(tmp_path):
    """
    esquerda e 'base' sao os mesmos numeros de posicao_na_chapa: no
    POLIPECAS, 90,0 mm da esquerda e 10,5 mm do pe.
    """
    origem = _pdf_de_teste(str(tmp_path / "arte.pdf"), 200, 100)
    destino = str(tmp_path / "arte_montagem.pdf")
    P.salvar_montagem(origem, 1, destino, (510, 400), 90.0, 10.5)

    tx, ty = _translacao(destino)
    assert tx / 72 * 25.4 == pytest.approx(90.0, abs=0.01)
    assert ty / 72 * 25.4 == pytest.approx(10.5, abs=0.01)


def test_a_montagem_desconta_a_ORIGEM_da_pagina(tmp_path):
    """
    A mediabox nem sempre comeca em (0,0). Sem descontar, a arte entra
    deslocada e a marca de corte nao cai nos 28 mm.
    """
    origem = _pdf_de_teste(str(tmp_path / "arte.pdf"), 200, 100,
                           origem=(10, 20))
    destino = str(tmp_path / "arte_montagem.pdf")
    P.salvar_montagem(origem, 1, destino, (510, 400), 90.0, 10.5)

    tx, ty = _translacao(destino)
    assert tx == pytest.approx(90.0 / 25.4 * 72 - 10, abs=0.01)
    assert ty == pytest.approx(10.5 / 25.4 * 72 - 20, abs=0.01)


def test_a_montagem_leva_o_nome_do_arquivo_com_montagem_no_fim():
    origem = r"V:\Prime  Graf\SETEMBRO\14\VALDINO - CHAPADO.cdr"
    assert P.caminho_da_montagem(origem) == \
        r"V:\Prime  Graf\SETEMBRO\14\VALDINO - CHAPADO_montagem.pdf"
    # com mais de uma pagina, o sufixo entra depois
    assert P.caminho_da_montagem(origem, 0, 2).endswith("_montagem F.pdf")
    assert P.caminho_da_montagem(origem, 2, 3).endswith("_montagem 3.pdf")


def test_a_montagem_NAO_volta_pela_porta_da_frente():
    """
    Ela e SAIDA. Se o vigia a pegasse, sairia uma segunda chapa e um
    segundo item na OS, do mesmo servico.
    """
    from finart_ctp.nomes import e_montagem

    assert e_montagem("VALDINO - CHAPADO_montagem.pdf")
    assert e_montagem("O.S 1034 - WAN SEMANA DO CLIENTE_montagem.cdr")
    assert e_montagem("X_montagem F.pdf")
    assert e_montagem("X_montagem 02.pdf")

    # e nao pega o que nao e nosso
    assert not e_montagem("VALDINO - CHAPADO.cdr")
    assert not e_montagem("montagem santinhos.pdf")
    assert not e_montagem("X_montagem final.pdf")
    assert not e_montagem("525x459_CMYK_AMERICA_Arte Rifa 2025_MONTAGEM02.pdf")


def test_so_a_prime_deixa_montagem_na_pasta():
    """
    A CREATIVE monta igual e continua sem deixar arquivo: ela sempre
    trabalhou assim e ninguem pediu para mudar.
    """
    assert C.CLIENTES_QUE_SALVAM_A_MONTAGEM == ("PRIME",)
