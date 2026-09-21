# -*- coding: utf-8 -*-
r"""
QUAL PAGINA CAI EM QUAL LUGAR - os tres processos da AMERICA.

Combinado com o operador em 20/09/2026, e ele fechou a pergunta que a
skill de imposicao tinha em aberto desde 10/09 ("caderno e paginacao"):

    "a america usa os 3 tipos de montagem: FOLHA SOLTA, que seriam
    arquivos com poucas paginas, para montagens quase sempre com 1
    formato bate-vira ou 1 formato frente e verso; outra montagem que a
    america usa, geralmente para livros e revistas, e o formato CANOA
    (saddle-stitched), nesse formato monto varios livros, com a
    definicao escrita de cada caderno (caderno 1 frente / caderno 1
    verso); e a america tambem usa o processo de montagem HOT-MELT,
    LOMBADA (perfect-bound), onde os livros ou revistas tem uma
    quantidade de paginas maiores e precisa desse processo para colar as
    paginas na capa."

ESTE MODULO NAO DESENHA NADA. Ele responde uma pergunta so - que pagina
vai em que lugar -, e por isso nao depende de Ghostscript, de CorelDRAW
nem de arquivo nenhum. E conta pura, e conta pura se prova por teste.

--------------------------------------------------------------------
O QUE OS MODELOS DO PREPS ENSINARAM, e foi medido, nao suposto
--------------------------------------------------------------------

Lido em 20/09/2026 pelo ferramentas/ler_paginacao_preps.py:

1. UM LUGAR TEM DUAS PAGINAS. O %SSiPrshPage guarda um PAR - a pagina
   que cai naquele lugar na frente da folha e a que cai no MESMO lugar
   no verso. Um lugar e um pedaco de papel, e papel tem dois lados: a
   montagem do verso nao e uma segunda conta, e a outra metade da mesma.

2. CANOA E LOMBADA IMPOEM IGUAL DENTRO DO CADERNO. Os dois tutoriais do
   Preps - 'A4 Tutorial Saddle.tpl' e 'A4 Tutorial PerfectBound.tpl' -
   trazem o mesmo caderno de 16 paginas com a paginacao IDENTICA, lugar
   por lugar:

       1 2  |  16 15  |  13 14  |  4 3
       8 7  |   9 10  |  12 11  |  5 6

   O que muda entre os dois NAO e a dobra: e (a) como as paginas do
   livro sao repartidas entre os cadernos e (b) a marca de colacao. Foi
   isso que encolheu este modulo para o tamanho que ele tem.

3. E NAO HA UMA DOBRA SO PARA CADA NUMERO DE PAGINAS. O 'A4 Multi.tpl'
   tras outro arranjo de 16, com as mesmas folhas em ordem diferente.
   Por isso os arranjos aqui sao um CATALOGO LIDO, e nao uma formula
   inventada - quem manda e o modelo, como sempre foi nesta casa.

--------------------------------------------------------------------
UM AVISO SOBRE DE ONDE VIERAM ESTES ARRANJOS
--------------------------------------------------------------------

Da instalacao do Preps da BANCADA, que so tem os 58 modelos de exemplo
que vem com o programa. Os 2020 modelos DA CASA estao na maquina da
grafica. Na Finart, rode o leitor neles e confira se a casa dobra assim
tambem - e se nao dobrar, quem manda e a casa.
"""

# ----------------------------------------------------------------------
# OS TRES PROCESSOS
# ----------------------------------------------------------------------
# Os nomes sao os do operador, e a ordem aqui e a de quantas paginas o
# trabalho tem: folha solta e pouca pagina, canoa e livro, lombada e
# livro grande.
FOLHA_SOLTA = "folha solta"
CANOA = "canoa"
LOMBADA = "lombada"

PROCESSOS = (FOLHA_SOLTA, CANOA, LOMBADA)

# O NOME QUE APARECE NA TELA. O operador passou a dizer FLAT-WORK em
# 20/09/2026, ao desenhar a interface dos montadores - e e o termo do
# Preps, que ele usa ha anos. 'Folha solta' e a mesma coisa dita em
# portugues, e continua sendo o nome interno porque ja esta escrito em
# teste e em skill. Duas palavras, uma coisa.
FLAT_WORK = FOLHA_SOLTA
HOTMELT = LOMBADA

ROTULOS = {
    FOLHA_SOLTA: "FLAT-WORK",
    CANOA: "CANOA",
    LOMBADA: "HOTMELT",
}

# Como o operador chama cada um, e como o resto do mundo chama. Serve
# para a tela e para ler ordem de servico escrita a mao.
OUTROS_NOMES = {
    FOLHA_SOLTA: ("folha solta", "avulsa", "flat work"),
    CANOA: ("canoa", "saddle", "saddle-stitched", "grampo", "grampeado"),
    LOMBADA: ("lombada", "hot-melt", "hotmelt", "hot melt", "perfect",
              "perfect-bound", "perfect bound", "colado"),
}

# ----------------------------------------------------------------------
# OS ESTILOS DE VIRA
# ----------------------------------------------------------------------
# Os mesmos tres do painel, e os mesmos tres que o 5o campo do
# %SSiPressSheet do Preps guarda (0, 1 e 3). Duas contas da casa que
# nunca se falaram e concordam.
SO_FRENTE = "so frente"
BATE_VIRA = "bate-vira"
FRENTE_E_VERSO = "frente e verso"


class NaoSeiPaginar(Exception):
    """
    Falta combinado para paginar isto, e chutar sairia caro.

    A montagem errada nao da erro em lugar nenhum: grava limpa, imprime
    limpa, e o defeito aparece na dobra, depois da tiragem. Entao aqui
    se para.
    """


# ----------------------------------------------------------------------
# PARTE 1: QUE PAGINAS SAO DE CADA CADERNO
# ----------------------------------------------------------------------
# E aqui que canoa e lombada se separam, e a diferenca e fisica:
#
#   CANOA - os cadernos sao ENCAIXADOS um dentro do outro, e o grampo
#   atravessa todos. Entao o caderno de fora carrega o COMECO e o FIM do
#   livro, e o de dentro carrega o miolo.
#
#   LOMBADA - os cadernos sao EMPILHADOS um ao lado do outro, e a cola
#   pega a lombada inteira. Entao cada caderno carrega um pedaco
#   seguido do livro: 1-16, 17-32, 33-48.
#
# Fisicamente da para ver a diferenca num livro pronto: na canoa, abrir
# no meio mostra o grampo; na lombada, abrir no meio mostra cola.


# ----------------------------------------------------------------------
# O CADERNO DUPLICADO, E O QUADRUPLICADO
# ----------------------------------------------------------------------
# Pedido do operador em 21/09/2026:
#
#   "no ultimo caderno de algumas montagens, pode surgir a possibilidade
#   de eu ter de duplicar paginas para preencher a montagem, o que
#   chamamos de caderno duplicado, ou quadruplicado, se a pagina
#   precisar ser usada 4x, a mesma pagina"
#
# O CASO E SEMPRE O ULTIMO CADERNO. Os de dentro fecham a grade inteira;
# o ultimo herda o que sobrou do livro, e o que sobra quase nunca e um
# caderno cheio. Em vez de gravar chapa com celula vazia - que e chapa
# paga para imprimir papel branco -, repete-se a pagina: a mesma arte
# sai duas ou quatro vezes na mesma chapa, e o corte separa as copias.
#
# ENTAO O CADERNO DUPLICADO COME METADE DAS PAGINAS na mesma grade, e o
# quadruplicado, um quarto. A conta de chapas nao muda - a chapa e a
# mesma -, o que muda e quanto de livro ela leva.
REPETICOES = (1, 2, 4)

NOME_DA_REPETICAO = {1: "", 2: "duplicado", 4: "quadruplicado"}


def paginas_do_caderno(colunas, linhas, vira, repeticao=1):
    """
    Quantas paginas do livro um caderno segura, nesta grade e nesta vira.

    'repeticao' e quantas vezes cada pagina sai na chapa: 1 normal, 2 no
    caderno duplicado, 4 no quadruplicado. Repetindo, cabe menos livro
    na mesma chapa - e e de proposito, porque o que sobrou do livro nao
    enche a grade.

    Combinado com o operador em 20/09/2026, e sai do modelo que o painel
    ja tinha: uma CELULA e um pedaco de papel, com frente e verso.

    BATE-VIRA - a chapa e PARTIDA AO MEIO: metade das colunas imprime a
    frente e a outra metade o verso, cabeca com cabeca. Entao as folhas
    de papel sao metade das celulas, e cada uma tem dois lados:

        folhas = colunas*linhas / 2        paginas = colunas*linhas

    FRENTE E VERSO - sao DUAS chapas, e a grade inteira e uma cara do
    papel. Cada celula e uma folha:

        folhas = colunas*linhas            paginas = 2*colunas*linhas

    Repare que o bate-vira segura a METADE das paginas do frente e verso
    na mesma grade - e gasta UMA chapa em vez de duas. Nao ha almoco de
    graca: a chapa do bate-vira e do tamanho de duas.
    """
    if repeticao not in REPETICOES:
        raise NaoSeiPaginar(
            "a pagina sai 1, 2 ou 4 vezes na chapa - %r nao" % (repeticao,))
    celulas = colunas * linhas
    if vira == BATE_VIRA:
        if celulas % 2:
            raise NaoSeiPaginar(
                "o bate-vira parte a chapa ao meio: %d celulas nao dao "
                "duas metades iguais" % celulas)
        cabe = celulas
    elif vira == FRENTE_E_VERSO:
        cabe = 2 * celulas
    elif vira == SO_FRENTE:
        cabe = celulas
    else:
        raise NaoSeiPaginar("nao conheco a vira %r" % (vira,))

    if cabe % repeticao:
        raise NaoSeiPaginar(
            "esta grade segura %d paginas, e %d nao se divide por %d - "
            "um caderno %s precisa de uma grade que feche"
            % (cabe, cabe, repeticao, NOME_DA_REPETICAO[repeticao]))
    return cabe // repeticao


def chapas_do_caderno(vira):
    """Quantas chapas de metal um caderno gasta, por cor."""
    return 2 if vira == FRENTE_E_VERSO else 1


# ----------------------------------------------------------------------
# A ETIQUETA QUE SAI EM CADA CHAPA
# ----------------------------------------------------------------------
# Pedido do operador em 20/09/2026, desenhando a tela dos montadores:
#
#   "ja estarao preenchidos em cada caderno a informacao CAD 01 FRENTE -
#   CAD 02 VERSO - CAD 03 BATE-VIRA, e se eu acrescentar mais
#   informacoes elas virao logo depois dessas padroes, irei acrescentar o
#   nome do livro ou da revista, e a data que foi feito"
#
# NAO E ENFEITE, e o motivo e o mesmo do 'caderno 1 frente': oito
# cadernos de um livro sao ate dezesseis chapas quase iguais na mao de
# quem roda. A parte automatica vem primeiro porque e a que nunca pode
# faltar; o que a pessoa digita vem depois, e some quando ela nao digita
# nada.

SEPARADOR = " - "


def etiqueta(caderno, lado, extra=""):
    """
    'CAD 01 FRENTE - REVISTA X - 20/09/2026' - do jeito que o operador escreve.

    'lado' e 'frente', 'verso' ou None (o bate-vira, que e uma chapa so).
    O numero vai com DOIS ALGARISMOS: 'CAD 1' e 'CAD 10' lado a lado numa
    pilha de chapa se leem errado de longe.
    """
    if lado is None:
        marca = "BATE-VIRA"
    elif lado in ("frente", "verso"):
        marca = lado.upper()
    else:
        raise NaoSeiPaginar("lado e 'frente', 'verso' ou None, nao %r"
                            % (lado,))
    base = "CAD %02d %s" % (caderno, marca)
    extra = (extra or "").strip()
    return base + SEPARADOR + extra if extra else base


def etiquetas_do_caderno(caderno, vira, extra=""):
    """
    As etiquetas das chapas deste caderno, na ordem em que elas saem.

    Uma no bate-vira e no so frente; duas no frente e verso.
    """
    if vira == FRENTE_E_VERSO:
        return [etiqueta(caderno, "frente", extra),
                etiqueta(caderno, "verso", extra)]
    if vira == BATE_VIRA:
        return [etiqueta(caderno, None, extra)]
    if vira == SO_FRENTE:
        return [etiqueta(caderno, "frente", extra)]
    raise NaoSeiPaginar("nao conheco a vira %r" % (vira,))


def cadernos_do_livro(paginas, por_caderno, processo):
    r"""
    As paginas de cada caderno, em ordem LOCAL (1..por_caderno).

    Devolve [[pagina_do_livro, ...], ...] - uma lista por caderno, e
    dentro dela a pagina do LIVRO que ocupa cada posicao local. Ou seja:
    lista[0][0] e a pagina do livro que e a 'pagina 1' do caderno 1.

    Isso existe para o arranjo de dobra poder ser escrito UMA vez, em
    numeros locais (1..16), e servir aos dois processos. Foi o que os
    tutoriais do Preps mostraram: a dobra e a mesma, o que muda e o que
    se entrega a ela.

    NUMA CANOA de 32 paginas em cadernos de 16:

        caderno 1 (o de fora)  -> 1..8 e 25..32
        caderno 2 (o de dentro)-> 9..16 e 17..24

    Abrindo o caderno 1 no meio veem-se as paginas 8 e 25, e entre elas
    esta o caderno 2 inteiro. E o que acontece com uma revista grampeada
    de verdade.

    NUMA LOMBADA de 32 em cadernos de 16:

        caderno 1 -> 1..16
        caderno 2 -> 17..32
    """
    if processo == FOLHA_SOLTA:
        raise NaoSeiPaginar(
            "folha solta nao tem caderno - cada pagina e uma peca. Use "
            "lugares_de_folha_solta")
    if processo not in (CANOA, LOMBADA):
        raise NaoSeiPaginar("nao conheco o processo %r" % (processo,))
    if por_caderno % 4:
        raise NaoSeiPaginar(
            "caderno de %d paginas nao fecha: uma folha dobrada da 4 "
            "paginas, entao o caderno e sempre multiplo de 4" % por_caderno)
    if paginas % por_caderno:
        raise NaoSeiPaginar(
            "%d paginas nao fecham em cadernos de %d - sobram %d. Quem "
            "decide o que fazer com a sobra (pagina em branco, caderno "
            "menor no fim) e gente"
            % (paginas, por_caderno, paginas % por_caderno))

    quantos = paginas // por_caderno
    metade = por_caderno // 2

    return repartir(paginas, [por_caderno] * quantos, processo)


def repartir(paginas, tamanhos, processo, completo=True):
    r"""
    O mesmo que o cadernos_do_livro, com cadernos de TAMANHOS DIFERENTES.

    'tamanhos' e quantas paginas cada caderno segura, na ordem em que os
    cadernos foram montados - o de fora primeiro, na canoa.

    ISTO EXISTE PORQUE O LIVRO DE VERDADE NAO E UNIFORME. Na tela dos
    montadores o operador vai somando caderno a caderno, e escolhe a vira
    de cada um: um bate-vira segura a metade das paginas de um frente e
    verso na mesma grade, e um caderno personalizado segura o que ele
    disser. Exigir tamanho unico era exigir que o livro coubesse na
    conta, em vez de a conta caber no livro.

    NA LOMBADA os cadernos sao empilhados, entao e so ir fatiando do
    comeco. NA CANOA eles sao encaixados, e a conta come dos DOIS LADOS
    ao mesmo tempo: o de fora leva a primeira e a ultima fatia, o
    seguinte leva as de dentro delas, e assim por diante ate se
    encontrarem no meio.
    """
    # 'completo=False' e para a TELA, que pergunta o tempo todo enquanto
    # o montador ainda esta somando cadernos. A conta das paginas de cada
    # caderno ja esta decidida a essa altura - na canoa, o de fora leva a
    # primeira e a ultima fatia, independente de quantos venham depois -,
    # entao da para desenhar o que ja existe sem mentir. Quem fecha o
    # livro e o chamador, e e ele que tem de ver o 'faltam'.
    if completo and sum(tamanhos) != paginas:
        raise NaoSeiPaginar(
            "os cadernos somam %d paginas e o livro tem %d - quem decide "
            "o que fazer com a diferenca e gente"
            % (sum(tamanhos), paginas))
    if sum(tamanhos) > paginas:
        raise NaoSeiPaginar(
            "os cadernos ja somam %d paginas, e o livro tem %d"
            % (sum(tamanhos), paginas))
    for t in tamanhos:
        if t % 4:
            raise NaoSeiPaginar(
                "caderno de %d paginas nao fecha: uma folha dobrada da 4 "
                "paginas, entao o caderno e sempre multiplo de 4" % t)

    if processo == LOMBADA:
        saida, ini = [], 1
        for t in tamanhos:
            saida.append(list(range(ini, ini + t)))
            ini += t
        return saida

    if processo != CANOA:
        raise NaoSeiPaginar("nao conheco o processo %r" % (processo,))

    # CANOA - come dos dois lados. O 'ini' anda para a frente e o 'fim'
    # anda para tras; quando se cruzam, o livro acabou.
    saida, ini, fim = [], 1, paginas
    for t in tamanhos:
        metade = t // 2
        comeco = list(range(ini, ini + metade))
        acabamento = list(range(fim - metade + 1, fim + 1))
        saida.append(comeco + acabamento)
        ini += metade
        fim -= metade
    return saida


# ----------------------------------------------------------------------
# PARTE 2: ONDE CADA FOLHA DO CADERNO CAI NA CHAPA
# ----------------------------------------------------------------------
# O ARRANJO e a dobra escrita em numero. Cada entrada diz, para uma
# celula da grade, quais paginas LOCAIS caem ali - a da frente e a do
# verso - e como a peca entra.
#
# A coluna conta da esquerda para a direita; a LINHA CONTA DE CIMA PARA
# BAIXO, que e a ordem em que se le a tabela e a ordem em que o Preps
# grava. Quem desenha a chapa converte para a sua conta (na chapa o y
# cresce para cima, e a pinca e no pe).
#
# COPIADOS DOS MODELOS DO PREPS, lugar por lugar, e nao deduzidos. A
# fonte de cada um esta escrita ao lado.

_ARRANJOS = {
    # ------------------------------------------------------------------
    # OS DOIS BATE-VIRA SAO OS DA CASA, e nao os dos tutoriais.
    #
    # Trocados em 21/09/2026, a pedido do operador, depois que a
    # varredura dos 194 modelos da AMERICA mostrou que ela dobra outra
    # coisa. Os do tutorial estavam aqui desde 20/09 e nunca chegaram a
    # montar nada - o caderno em bate-vira so passou a existir agora.
    #
    #     tutorial      4 paginas em 1x2      8 paginas em 2x2
    #     a AMERICA     4 paginas em 2x2      8 paginas em 4x2
    #                   56 cadernos           45 cadernos
    #
    # E O PREPS NAO ESCREVE O VERSO NO BATE-VIRA: as N paginas ficam
    # todas na mesma chapa, com o campo de verso em zero, e a folha
    # passa duas vezes. O verso de um lugar e a pagina do lugar
    # ESPELHADO - e o EIXO do espelho muda de modelo para modelo, o que
    # so se descobre conferindo se cada par e uma folha inteira. Ver
    # ferramentas/arranjo_do_template.py.
    # ------------------------------------------------------------------
    # '100 x 148 - Saddle-Stiched_LIVRO AMERICA RCC.tpl', |BV 340 x 240|
    # A folha TOMBA no eixo horizontal: o verso vem do lugar de baixo.
    (4, BATE_VIRA): {
        "grade": (2, 2),
        "vaos": {"x": (0,), "y": (1,)},
        "celulas": [
            (1, 1, "180", 3, 4),
            (2, 1, "180", 2, 1),
            (1, 2, "0", 4, 3),
            (2, 2, "0", 1, 2),
        ],
    },
    # '100 x 150 - Saddle-Stiched_AMERICA LIVRETO FT4_BV.tpl',
    # |CAD 440 x 330|. Aqui a folha VIRA no eixo vertical: o verso vem
    # do lugar espelhado na horizontal. Mesmo processo, eixo diferente -
    # e e por isso que ele nao se supoe.
    (8, BATE_VIRA): {
        "grade": (4, 2),
        "vaos": {"x": (0, 1, 0), "y": (1,)},
        "celulas": [
            (1, 1, "180", 3, 4),
            (2, 1, "180", 6, 5),
            (3, 1, "180", 5, 6),
            (4, 1, "180", 4, 3),
            (1, 2, "0", 2, 1),
            (2, 2, "0", 7, 8),
            (3, 2, "0", 8, 7),
            (4, 2, "0", 1, 2),
        ],
    },
    # |8 page SW| dos dois tutoriais - peca deitada, duas chapas
    #
    # E O UNICO SEM 'vaos', DE PROPOSITO. Os quatro tutoriais dao esta
    # MESMA paginacao, lugar por lugar, e discordam em onde a folha
    # dobra:
    #
    #     A4 Tutorial PerfectBound    x: 0      y: 6
    #     A4 Tutorial Saddle          x: 16     y: 0
    #     Letter Tutorial Saddle      x: 12,7   y: 0
    #     Ltr Tutorial PerfectBound   x: 6,35   y: 6,35
    #
    # Nao ha o que escolher aqui - so ha o que ler, e a casa nao tem
    # modelo de 8 em frente e verso. Chutar poria a dobra no lugar
    # errado, que e o defeito que grava limpo e so aparece na
    # guilhotina. Entao quem pedir este caderno leva recusa, com o
    # recado de ler um modelo da casa primeiro.
    (8, FRENTE_E_VERSO): {
        "grade": (2, 2),
        "celulas": [
            (1, 1, "90", 8, 7),
            (2, 1, "-90", 5, 6),
            (1, 2, "90", 1, 2),
            (2, 2, "-90", 4, 3),
        ],
    },
    # ------------------------------------------------------------------
    # 16 PAGINAS, FRENTE E VERSO - O ARRANJO DA CASA
    #
    # Lido em 21/09/2026 no modelo da propria Finart,
    # '150 x 210 - Saddle-Stiched_CELEBRACAO MIOLO.tpl', caderno
    # |CAD 660 x 480|. O operador o abriu no Preps e mandou olhar:
    # "veja essa montagem do preps, serve para canoa ou hotmelt, mudando
    # apenas a regra (...) perceba que as paginas de cima ficam
    # rotacionadas, e perceba a ordem das paginas".
    #
    # ELE E O DO TUTORIAL VIRADO 180 NA FOLHA, e isso foi conferido
    # numero a numero: invertendo a linha de cima do tutorial sai a de
    # baixo da casa, e vice-versa. Mesma dobra, assentada de cabeca para
    # baixo.
    #
    # E NAO E DETALHE, porque a PINCA fica no PE da chapa: virar a
    # montagem troca quais paginas encostam na faixa que a maquina
    # segura. Duas montagens com a mesma dobra e orientacoes opostas
    # imprimem igual e DOBRAM igual - mas entram na maquina ao
    # contrario.
    #
    # QUEM MANDA E A CASA. Esta skill sempre disse isso: os arranjos
    # vieram dos modelos de EXEMPLO do Preps, e a instrucao escrita era
    # "na Finart, rode o leitor neles e confira se a casa dobra assim
    # tambem - e se nao dobrar, quem manda e a casa". Rodei, nao dobra
    # igual, e a da casa fica.
    #
    # O do tutorial continua escrito aqui embaixo, fora do catalogo, por
    # ser a prova de que os dois sao a mesma dobra.
    # '135 x 210 - Saddle-Stiched_LIVRO AMERICA.tpl', caderno
    # |CAD 03 670 x 320| - lido em 21/09/2026 com
    # ferramentas/arranjo_do_template.py, conferido: fecha em 1..12.
    #
    # ELE ENTROU PORQUE UM LIVRO DE VERDADE PEDIU. O miolo de 228
    # paginas que o operador pos na fila nao fecha em 8 (sobram 4) nem
    # em 16 (sobram 4) - mas fecha em 12, em 19 cadernos exatos. Sem
    # esta dobra, o unico caminho era pagina em branco no fim.
    #
    # Doze e dobra de TRES, e por isso a grade e 2x3 e nao uma potencia
    # de 2. A casa usa: sao 12 cadernos assim nos 194 modelos da AMERICA.
    (12, FRENTE_E_VERSO): {
        "grade": (2, 3),
        "vaos": {"x": (0,), "y": (1, 1)},
        "celulas": [
            (1, 1, "0", 8, 7),
            (2, 1, "0", 5, 6),
            (1, 2, "180", 9, 10),
            (2, 2, "180", 4, 3),
            (1, 3, "0", 12, 11),
            (2, 3, "0", 1, 2),
        ],
    },
    (16, FRENTE_E_VERSO): {
        "grade": (4, 2),
        "vaos": {"x": (0, 1, 0), "y": (1,)},
        "celulas": [
            (1, 1, "180", 5, 6),
            (2, 1, "180", 12, 11),
            (3, 1, "180", 9, 10),
            (4, 1, "180", 8, 7),
            (1, 2, "0", 4, 3),
            (2, 2, "0", 13, 14),
            (3, 2, "0", 16, 15),
            (4, 2, "0", 1, 2),
        ],
    },
}

# O MESMO CADERNO DE 16, COMO O TUTORIAL DO PREPS O ESCREVE.
#
# Nao entra no catalogo - fica aqui como PROVA de que o arranjo da casa e
# este virado 180 na folha. Ha um teste que confronta os dois; se um dia
# alguem "corrigir" o catalogo de volta para o tutorial, ele diz por que
# a casa nao usa esse.
_TUTORIAL_16_FV = [
    (1, 1, "180", 1, 2),
    (2, 1, "180", 16, 15),
    (3, 1, "180", 13, 14),
    (4, 1, "180", 4, 3),
    (1, 2, "0", 8, 7),
    (2, 2, "0", 9, 10),
    (3, 2, "0", 12, 11),
    (4, 2, "0", 5, 6),
]


def arranjos_conhecidos():
    """[(paginas_por_caderno, vira)] - o que ja da para dobrar sozinho."""
    return sorted(_ARRANJOS)


def arranjo(por_caderno, vira):
    """
    A dobra deste caderno: {'grade': (colunas, linhas), 'celulas': [...]}.

    Cada celula e (coluna, linha, giro, pagina_local_frente,
    pagina_local_verso), com a LINHA CONTANDO DE CIMA PARA BAIXO.

    PARA quando nao conhece - e esta e a regra da casa, nao um buraco:
    dobra chutada nao da erro em lugar nenhum ate a guilhotina.
    """
    achado = _ARRANJOS.get((por_caderno, vira))
    if achado is None:
        conhecidos = ", ".join("%d em %s" % (p, v)
                               for p, v in arranjos_conhecidos())
        raise NaoSeiPaginar(
            "nao tenho a dobra de um caderno de %d paginas em %s. "
            "Conheco: %s. A dobra vem de um modelo do Preps, nao de "
            "formula - leia o da casa com ler_paginacao_preps.py"
            % (por_caderno, vira, conhecidos))
    saida = {"grade": achado["grade"],
             "celulas": [tuple(c) for c in achado["celulas"]]}
    if "vaos" in achado:
        saida["vaos"] = {"x": tuple(achado["vaos"]["x"]),
                         "y": tuple(achado["vaos"]["y"])}
    return saida


def vaos_do_arranjo(por_caderno, vira):
    """
    ((x...), (y...)) - ONDE A GUILHOTINA PASSA e onde a folha dobra.

    Um numero por JUNCAO, nao por celula: 1 quer dizer "aqui entra o
    vao", 0 quer dizer "aqui as duas pecas se encostam". Numa grade de
    4 colunas sao tres juncoes.

    A ORDEM E A DAS CELULAS: x da esquerda para a direita, y DE CIMA
    PARA BAIXO - vy[0] e a juncao entre a linha 1 e a 2. Quem desenha a
    chapa conta o y ao contrario (la a pinca e no pe) e tem de virar a
    lista.

    O VAO NAO E IGUAL ENTRE TODAS AS CELULAS, e esse foi o engano que
    esta funcao desfaz. Em folha solta e - toda junta ali e corte, e
    espalhar por igual acerta. NUM CADERNO NAO: onde a folha dobra as
    duas paginas sao o mesmo pedaco de papel, e um vao ali abriria uma
    tira branca no meio da dobra. Medido nos modelos da casa em
    21/09/2026:

        SAPIENTIA     16 pag  4x2   x: 0 5 0    y: 5
        RCC           32 pag  4x4   x: 0 5 0    y: 5 5 5
        LIVRO AMERICA 18 pag  3x3   x: 5 0      y: 5 5
        CAD 03        12 pag  2x3   x: 0        y: 5 5

    O LIVRO AMERICA e a prova de que nao se deduz: mesma peca, grade
    parecida, e o vao na PRIMEIRA juncao em vez da do meio.

    PARA quando o arranjo nao traz os vaos - e o caso do (8, frente e
    verso), onde os quatro tutoriais discordam entre si. Ver o
    comentario dele no catalogo.
    """
    desenho = arranjo(por_caderno, vira)
    if "vaos" not in desenho:
        raise NaoSeiPaginar(
            "sei a ordem das paginas de um caderno de %d em %s, mas nao "
            "sei ONDE ELE DOBRA - e sem isso a montagem sai com vao no "
            "lugar da dobra. Leia um modelo da casa com "
            "ferramentas/arranjo_do_template.py e traga os 'vaos'"
            % (por_caderno, vira))
    colunas, linhas = desenho["grade"]
    vx, vy = desenho["vaos"]["x"], desenho["vaos"]["y"]
    if len(vx) != colunas - 1 or len(vy) != linhas - 1:
        raise NaoSeiPaginar(
            "o caderno de %d em %s tem grade %dx%d, que pede %d juncao(oes) "
            "em x e %d em y - o catalogo traz %d e %d"
            % (por_caderno, vira, colunas, linhas,
               colunas - 1, linhas - 1, len(vx), len(vy)))
    return vx, vy


def lugares_do_caderno(paginas_do_caderno, vira):
    """
    [(coluna, linha, giro, pagina_frente, pagina_verso)] deste caderno.

    Recebe as paginas do LIVRO que o caderno carrega, na ordem local (o
    que o cadernos_do_livro devolve), e troca os numeros locais do
    arranjo pelos numeros de verdade.

    ZERO E 'NADA DESTE LADO', como no Preps: uma pagina local que nao
    existe no caderno sai 0. Nao inventamos pagina em branco aqui -
    quem decide o que fazer com lado vazio e quem monta.
    """
    por_caderno = len(paginas_do_caderno)
    desenho = arranjo(por_caderno, vira)

    def de_verdade(local):
        if not local or local > por_caderno:
            return 0
        return paginas_do_caderno[local - 1]

    return [(col, lin, giro, de_verdade(frente), de_verdade(verso))
            for col, lin, giro, frente, verso in desenho["celulas"]]


def lugares_do_livro(paginas, por_caderno, processo, vira):
    """
    Os cadernos ja paginados: [{'caderno': n, 'lugares': [...]}].

    E o que a tela mostra e o que o motor desenha. O 'caderno 1 frente /
    caderno 1 verso' que o operador escreve a mao em cada montagem sai
    daqui - ver nome_do_caderno.
    """
    saida = []
    for n, paginas_dele in enumerate(
            cadernos_do_livro(paginas, por_caderno, processo), start=1):
        saida.append({"caderno": n,
                      "paginas": list(paginas_dele),
                      "lugares": lugares_do_caderno(paginas_dele, vira)})
    return saida


# ----------------------------------------------------------------------
# O PLANO DO LIVRO - o que a tela dos montadores mostra
# ----------------------------------------------------------------------
# Desenhado com o operador em 20/09/2026:
#
#   "se clicarmos na opcao canoa, voce ja sabera o numero de paginas,
#   entao dara a opcao para inserir caderno bate-vira ou frente e verso,
#   ou caderno personalizado, e a partir do momento que eu for clicando
#   vai criando o caderno 1, o 2 e assim por diante, ate o ultimo
#   caderno"
#
# ELE SOMA, E NAO ESCOLHE. O montador vai acrescentando caderno por
# caderno e a tela responde quanto falta - ela nunca decide quantos
# cadernos o livro tem nem de que tipo. E a mesma regra do painel desde
# 11/09/2026: mostrar nao e decidir.
#
# E POR ISSO ELE TEM DE FUNCIONAR INCOMPLETO. Enquanto o livro nao
# fecha, o plano existe do mesmo jeito, dizendo o que ja esta posto e o
# que falta. Uma conta que so responde no fim nao serve a quem esta
# montando.


def plano_do_livro(paginas, cadernos, processo, extra=""):
    r"""
    O livro inteiro, caderno por caderno, com etiqueta e paginas.

    'cadernos' e a lista que o montador foi somando, na ordem:

        [{"vira": BATE_VIRA, "paginas": 8},
         {"vira": FRENTE_E_VERSO, "paginas": 16}]

    Devolve um dicionario que a tela desenha e a ordem imprime:

        cadernos  cada um com numero, vira, paginas do LIVRO, quantas
                  chapas e as ETIQUETAS ja prontas
        usadas    quantas paginas ja foram postas em caderno
        faltam    quantas ainda nao
        fecha     as duas contas baterem
        chapas    quantas chapas de metal, por cor
    """
    if processo not in (CANOA, LOMBADA):
        raise NaoSeiPaginar(
            "plano de livro e de canoa ou de lombada - %r nao tem caderno"
            % (processo,))

    tamanhos = [int(c["paginas"]) for c in cadernos]
    usadas = sum(tamanhos)
    fatias = repartir(paginas, tamanhos, processo, completo=False)

    saida = []
    for n, (c, paginas_dele) in enumerate(zip(cadernos, fatias), start=1):
        vira = c["vira"]
        rep = int(c.get("repeticao", 1))
        saida.append({
            "numero": n,
            "vira": vira,
            "repeticao": rep,
            "repeticao_nome": NOME_DA_REPETICAO.get(rep, ""),
            "paginas": len(paginas_dele),
            "do_livro": paginas_dele,
            # A CHAPA E A MESMA: repetir a pagina nao gasta chapa a
            # mais, gasta menos LIVRO na chapa que ja ia sair.
            "chapas": chapas_do_caderno(vira),
            "etiquetas": etiquetas_do_caderno(n, vira, extra),
        })

    return {
        "processo": processo,
        "rotulo": ROTULOS[processo],
        "paginas": paginas,
        "cadernos": saida,
        "usadas": usadas,
        "faltam": paginas - usadas,
        "fecha": usadas == paginas,
        "chapas": sum(c["chapas"] for c in saida),
    }


# ----------------------------------------------------------------------
# PARTE 3: FOLHA SOLTA - o que a casa ja faz hoje
# ----------------------------------------------------------------------
# Aqui NAO HA caderno e NAO HA dobra: cada pagina e uma peca inteira, e
# a unica pergunta e quantas cabem e de que lado saem. E o caminho do
# montar_bate_vira.py de hoje, escrito na mesma lingua dos outros dois
# para a tela poder tratar os tres do mesmo jeito.


def lugares_de_folha_solta(paginas, colunas, linhas, vira):
    """
    [(coluna, linha, giro, frente, verso)] - a grade, preenchida em ordem.

    SO FRENTE       cada celula leva uma pagina, e o verso sai 0.
    FRENTE E VERSO  cada celula e uma FOLHA: leva duas paginas, uma de
                    cada lado. Sao duas chapas.
    BATE-VIRA       idem, mas as duas chapas viram uma so - quem cuida
                    disso e o desenho, nao a paginacao. Aqui a conta e a
                    mesma do frente e verso.

    A ordem de preenchimento e a de leitura: esquerda para a direita, de
    cima para baixo. Sobrando celula, ela sai vazia (0, 0) - e o painel
    ja desenha celula vazia tracejada, no canto longe da pinca.
    """
    if vira not in (SO_FRENTE, BATE_VIRA, FRENTE_E_VERSO):
        raise NaoSeiPaginar("nao conheco a vira %r" % (vira,))
    por_celula = 1 if vira == SO_FRENTE else 2
    celulas = colunas * linhas
    if paginas > celulas * por_celula:
        raise NaoSeiPaginar(
            "%d paginas nao cabem em %d celulas a %d por celula - "
            "seriam %d chapas, e quantas chapas e decisao de gente"
            % (paginas, celulas, por_celula, celulas * por_celula))

    lugares = []
    proxima = 1

    def pegar():
        """A proxima pagina, ou 0 quando o livro acabou."""
        nonlocal proxima
        if proxima > paginas:
            return 0
        proxima += 1
        return proxima - 1

    for lin in range(1, linhas + 1):
        for col in range(1, colunas + 1):
            frente = pegar()
            verso = pegar() if por_celula == 2 else 0
            lugares.append((col, lin, "0", frente, verso))
    return lugares


# ----------------------------------------------------------------------
# O NOME QUE VAI ESCRITO NA CHAPA
# ----------------------------------------------------------------------
# Pedido do operador, 20/09/2026, sobre a canoa: "monto varios livros,
# com a definicao escrita de cada caderno (caderno 1 frente / caderno 1
# verso)".
#
# NAO E ENFEITE. Quem recebe as chapas na maquina tem varias parecidas
# na mao - oito cadernos de um livro sao dezesseis chapas quase iguais -,
# e trocar duas e um livro com o miolo fora de ordem que so aparece
# depois de dobrado e cortado.


def nome_do_caderno(caderno, lado=None):
    """
    'caderno 1 frente', 'caderno 1 verso' - do jeito que o operador escreve.

    Sem lado, devolve so 'caderno 1' - que e o caso do bate-vira, em que
    as duas metades saem na MESMA chapa e nao ha o que distinguir.
    """
    if lado is None:
        return "caderno %d" % caderno
    if lado not in ("frente", "verso"):
        raise NaoSeiPaginar("lado e 'frente' ou 'verso', nao %r" % (lado,))
    return "caderno %d %s" % (caderno, lado)


def chapas_do_livro(paginas, por_caderno, processo, vira):
    """
    Os nomes das chapas que este livro gasta, na ordem.

    Serve para a conta da OS e para o operador conferir antes de montar:
    um livro de 64 paginas em cadernos de 16, frente e verso, sao QUATRO
    cadernos e OITO chapas - e e bom ver os oito nomes antes de gravar.
    """
    quantos = len(cadernos_do_livro(paginas, por_caderno, processo))
    if vira == BATE_VIRA:
        return [nome_do_caderno(n) for n in range(1, quantos + 1)]
    nomes = []
    for n in range(1, quantos + 1):
        nomes.append(nome_do_caderno(n, "frente"))
        nomes.append(nome_do_caderno(n, "verso"))
    return nomes


# ======================================================================
# O TESTE DA SOMA
# ======================================================================
# Entrou em 21/09/2026, da skill de imposicao grafica que o operador
# gravou. E a conferencia mais rapida que existe para imposicao, e a
# casa nao a tinha:
#
#     canoa     p + q = P + 1            depende do LIVRO inteiro
#     lombada   p + q = 2S + n - 1       depende SO do caderno
#                                        (S = onde comeca, n = tamanho)
#
# PROVA CONTRA O PREPS DA CASA, e foi ela que me convenceu: o ultimo
# caderno do 'Miolo Sapientia Crucis' - 4 paginas comecando na 225 -
# preve soma 453. O arquivo que o operador montou no Preps poe 227|226 e
# 228|225. Somam 453 os dois.
#
# POR QUE ELE PEGA O QUE MAIS DOI: montagem errada nao da erro em lugar
# nenhum. Grava limpa, imprime limpa, e o defeito aparece na dobra,
# depois da tiragem. Esta conta acha pagina trocada de caderno e pagina
# no lugar errado da chapa, em um piscar, antes de existir chapa.


def soma_esperada(processo, paginas_do_livro=None, comeca_em=None,
                  tamanho=None):
    """
    Quanto tem de somar um par que a dobra encosta.

    >>> soma_esperada(CANOA, paginas_do_livro=16)
    17
    >>> soma_esperada(LOMBADA, comeca_em=225, tamanho=4)
    453
    """
    if processo == CANOA:
        if not paginas_do_livro:
            raise ValueError("a canoa depende do total do livro")
        return paginas_do_livro + 1
    if not comeca_em or not tamanho:
        raise ValueError("a lombada depende de onde o caderno comeca "
                         "e de quantas paginas ele tem")
    return 2 * comeca_em + tamanho - 1


def pares_que_a_dobra_encosta(lugares):
    """
    Os pares de celulas que ficam lado a lado depois de dobrado.

    O GIRO DECIDE O SENTIDO, e isto me custou uma passada errada: eu
    tinha suposto colunas vizinhas sempre, e quatro dos cinco arranjos
    da casa passaram. O quinto - o (8, 'frente e verso') - reprovou com
    8+5=13 onde devia dar 9.

    Nao era defeito do arranjo: as pecas dele saem GIRADAS 90 graus, e
    peca deitada dobra no outro eixo. Conferindo por LINHA, ele da 8+1
    e 5+4 - nove os dois. A suposicao e que estava errada, e o dado
    corrigiu.

        peca em pe (giro 0 ou 180)   -> o par e de COLUNAS vizinhas
        peca deitada (giro 90/-90)   -> o par e de LINHAS vizinhas
    """
    deitada = any(str(c[2]) in ("90", "-90") for c in lugares)
    grupos = {}
    for c in lugares:
        fora, dentro = (c[0], c[1]) if deitada else (c[1], c[0])
        grupos.setdefault(fora, {})[dentro] = c
    for grupo in grupos.values():
        ordem = sorted(grupo)
        for i in range(0, len(ordem) - 1, 2):
            yield grupo[ordem[i]], grupo[ordem[i + 1]]


def conferir_a_soma(lugares, esperado):
    """
    Devolve a lista do que NAO bateu - vazia quer dizer que passou.

    Cada item e (lado, pagina_a, pagina_b, soma), com 'lado' em
    'frente'/'verso'. Devolver a lista, e nao um True, e de proposito:
    quem for olhar precisa saber QUAL par furou para achar a pagina.
    """
    fora = []
    for a, b in pares_que_a_dobra_encosta(lugares):
        for indice, lado in ((3, "frente"), (4, "verso")):
            soma = a[indice] + b[indice]
            if soma != esperado:
                fora.append((lado, a[indice], b[indice], soma))
    return fora
