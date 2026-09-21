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

    if processo == LOMBADA:
        # EMPILHADOS: cada um leva um pedaco seguido.
        return [list(range(k * por_caderno + 1, (k + 1) * por_caderno + 1))
                for k in range(quantos)]

    # CANOA - ENCAIXADOS. O caderno k leva a k-esima fatia do comeco e a
    # k-esima fatia do fim, e o fim entra na ordem em que ele cai depois
    # da dobra: o caderno de fora acaba na ultima pagina do livro.
    cadernos = []
    for k in range(quantos):
        comeco = list(range(k * metade + 1, (k + 1) * metade + 1))
        fim = list(range(paginas - (k + 1) * metade + 1,
                         paginas - k * metade + 1))
        cadernos.append(comeco + fim)
    return cadernos


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
    # 'A4 Tutorial Saddle.tpl' / '...PerfectBound.tpl' - |4 page wt|
    # Uma coluna, duas linhas, peca deitada. E a dobra mais simples que
    # existe: uma folha, um vinco no meio.
    (4, BATE_VIRA): {
        "grade": (1, 2),
        "celulas": [
            (1, 1, "90", 4, 3),
            (1, 2, "90", 1, 2),
        ],
    },
    # |8 page WT| dos dois tutoriais
    (8, BATE_VIRA): {
        "grade": (2, 2),
        "celulas": [
            (1, 1, "180", 1, 2),
            (2, 1, "180", 8, 7),
            (1, 2, "0", 4, 3),
            (2, 2, "0", 5, 6),
        ],
    },
    # |8 page SW| dos dois tutoriais - peca deitada, duas chapas
    (8, FRENTE_E_VERSO): {
        "grade": (2, 2),
        "celulas": [
            (1, 1, "90", 8, 7),
            (2, 1, "-90", 5, 6),
            (1, 2, "90", 1, 2),
            (2, 2, "-90", 4, 3),
        ],
    },
    # |16 page SW| dos dois tutoriais. E o arranjo que prova que canoa e
    # lombada dobram igual: os dois arquivos trazem estas oito linhas
    # identicas.
    (16, FRENTE_E_VERSO): {
        "grade": (4, 2),
        "celulas": [
            (1, 1, "180", 1, 2),
            (2, 1, "180", 16, 15),
            (3, 1, "180", 13, 14),
            (4, 1, "180", 4, 3),
            (1, 2, "0", 8, 7),
            (2, 2, "0", 9, 10),
            (3, 2, "0", 12, 11),
            (4, 2, "0", 5, 6),
        ],
    },
}


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
    return {"grade": achado["grade"],
            "celulas": [tuple(c) for c in achado["celulas"]]}


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
