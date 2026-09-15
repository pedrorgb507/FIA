# -*- coding: utf-8 -*-
r"""
O ESTOQUE DE CHAPAS DO CLIENTE, numa folha, todo dia.

    python -m finart_ctp.estoque              a folha da casa, na tela
    python -m finart_ctp.estoque --agora      + o RELATORIO ATUAL, na
                                                pasta do cliente
    python -m finart_ctp.estoque --fechar     fecha o dia que faltou
    python -m finart_ctp.estoque --fechar 11/09      um dia certo
    python -m finart_ctp.estoque VIVA         outro cliente
    python -m finart_ctp.estoque --nao-abrir  so grava

TRES PAPEIS, e nao um:

    ESTOQUE <cliente>.pdf        na PASTA_CONTROLE, reescrito o dia
                                 inteiro. E a folha de dentro da casa
    RELATORIO ATUAL <data> <hora>.pdf    na pasta do cliente, a pedido
    RELATORIO CHAPAS <cliente> (<data>).pdf   na pasta DAQUELE dia, uma
                                 vez, quando o dia fecha. E o que o
                                 cliente recebe

PARA QUE SERVE. A chapa e do cliente: ele manda um lote, a Finart grava
e o saldo cai. Quando o saldo acaba, a gravacao para - e quem descobre
e o operador, na hora em que o servico ja esta na fila. O GEREMPRE
guarda o numero certo, mas mostra um saldo por vez, numa tela, sem
dizer quanto tempo ele ainda dura.

Esta folha responde a pergunta que importa: **quantos dias ainda tem**.

COMO O ARQUIVO ANDA DURANTE O DIA. Um por dia, sempre com o mesmo nome,
reescrito por cima. A FIA olha uma SENTINELA a cada volta do laco - uma
consulta so, 0,14 s - e so redesenha quando o movimento do cliente
mudou. Assim a folha acompanha tambem o que os operadores lancam no
Delphi, que e a maior parte: em 14/09/2026, das cinco OS da SOLIDA,
quatro foram abertas a mao.

    sentinela   COUNT(*), MAX(MOVCOD), SUM(MOVQTD) do dono
                muda em qualquer insercao, remocao ou correcao - e o
                TR_OS_BEFO apaga e refaz TODO o movimento de uma OS a
                cada gravacao, entao contar so o MAX deixaria passar
                uma OS que encolheu.

NAO EXISTE 'ESTOQUE MINIMO' NESTE BANCO. O campo CHAMIN parece ser isso
pelo nome e NAO E: ele guarda o PRECO. Conferido em 14/09/2026 - chapa
98 tem CHAMIN 9 e todas as 843 OS dela cobram 9,00; a 103 tem 13 e as
157 cobram 13,00; FIALHO 10 e 15, VIVA 8,50. Sao os mesmos numeros da
tabela GEREMPRE_CHAPAS. Ler CHAMIN como minimo faria a folha dizer
'175 de minimo 9, tudo bem' na vespera de acabar.

Por isso a folga e medida em DIAS, pelo consumo de verdade: a media do
que saiu nos ultimos dias COM MOVIMENTO (dia util, nao dia de
calendario - contar sabado e domingo esticaria a conta em dois setimos).

SO LE. Nenhuma linha daqui escreve no GEREMPRE.
"""

import datetime
import os
import sys

from .config import (DIAS_PARA_FECHAR_ATRASADO,
                     FECHAMENTO_A_PARTIR_DE, GEREMPRE_CLIENTES,
                     PASTA_CONTROLE, PASTA_DO_CLIENTE, RELATORIO_ATUAL,
                     RELATORIO_DO_DIA)
from .gerempre import perguntar
from .os_impressa import A4_MM, DPI, LOGO, _fonte
from .utils import agora_util, log, pasta_da_data

CLIENTE_PADRAO = "SOLIDA"

# Quantos dias COM MOVIMENTO entram na media de consumo. Vinte cobrem
# cerca de um mes de trabalho e ainda acompanham a subida de servico -
# a SOLIDA saiu de 25 por dia em agosto para 40 em setembro.
DIAS_DA_MEDIA = 20

# Quantos dias de folga acendem o alerta. Tres dias e o tempo que o
# cliente leva para mandar mais - decidido olhando as entradas: elas
# chegam em lotes de 50, 100 e 200, a cada cinco a dez dias.
POUCO_DIA = 3.0

ARQUIVO = "ESTOQUE %s.pdf"      # um por cliente, reescrito por cima

MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
SEMANA = ("segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
          "sexta-feira", "sabado", "domingo")


def _n(v):
    """Decimal do Firebird -> numero de Python. Nulo vira zero."""
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _texto(v):
    """
    O texto do banco em UMA linha.

    Ha titulo com quebra de linha dentro: o '49793 - ANDRE KUBITSCHEK -
    PANFLETO\nR1 8CH (2 JOGOS)' foi digitado assim no Delphi, que
    aceita. Numa tabela isso estoura a linha - e o Pillow nem consegue
    medir texto de varias linhas.
    """
    return " ".join((v or "").split())


# ----------------------------------------------------------------------
# O QUE SE LE DO BANCO
# ----------------------------------------------------------------------

def sentinela(dono, con):
    """
    A impressao digital do movimento deste cliente, numa consulta so.

    Muda a qualquer insercao, remocao ou correcao. E o que permite
    olhar o estoque a cada volta do laco sem pesar: 0,14 s contra 0,37 s
    da folha inteira.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT COUNT(*), MAX(MOVCOD), SUM(MOVQTD) FROM MOV "
                "WHERE MOVCLI = ?", (dono,))
    linha = cur.fetchone() or (0, 0, 0)
    return (int(_n(linha[0])), int(_n(linha[1])), _n(linha[2]))


def chapas_vivas(dono, con):
    """
    As chapas ATIVAS do cliente: [(cod, nome, medida, saldo, preco)].

    CHAINA = 1 e chapa desativada no cadastro. A SOLIDA tem oito
    cadastradas e so duas em uso; as seis paradas carregam saldo antigo
    (a 25 tem 8.662) que nao existe em prateleira nenhuma. Somar aquilo
    daria um estoque de mentira.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT CHACOD, CHANOM, CHAALT, CHALAR, CHAQTD, CHAMIN "
                "FROM CHA WHERE CHACLI = ? AND CHAINA = 0 "
                "ORDER BY CHAQTD DESC", (dono,))
    vivas = []
    for cod, nome, alt, lar, qtd, preco in cur.fetchall():
        vivas.append({"cod": cod, "nome": _texto(nome),
                      "medida": (int(_n(alt)), int(_n(lar))),
                      "saldo": _n(qtd), "preco": _n(preco)})
    return vivas


def paradas(dono, con):
    """(quantas, saldo_somado) das chapas desativadas que ainda tem saldo."""
    cur = con.cursor()
    perguntar(cur, "SELECT COUNT(*), SUM(CHAQTD) FROM CHA "
                "WHERE CHACLI = ? AND CHAINA = 1 AND CHAQTD > 0", (dono,))
    linha = cur.fetchone() or (0, 0)
    return int(_n(linha[0])), _n(linha[1])


def por_dia(dono, con, desde):
    """
    {codigo_da_chapa: [(dia, saiu, entrou)]} do periodo, em ordem.

    Usa MOVSDA e MOVENT, e nao o sinal de MOVQTD: os dois campos ja
    separam entrada de saida, e um dia com as duas coisas (14/09 teve)
    ficaria irreconhecivel somando o liquido.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT MOVCHA, MOVDIA, SUM(MOVSDA), SUM(MOVENT) FROM MOV "
                "WHERE MOVCLI = ? AND MOVDIA >= ? "
                "GROUP BY MOVCHA, MOVDIA ORDER BY MOVCHA, MOVDIA",
                (dono, desde))
    dias = {}
    for cha, dia, saiu, entrou in cur.fetchall():
        dias.setdefault(cha, []).append((dia, _n(saiu), _n(entrou)))
    return dias


def _vagas_da_os(cur, numero):
    """
    (hora, quem_abriu, [{chapa, quantas, titulo}]) de uma OS.

    E daqui que sai o NOME DO MATERIAL. A MOV nao o guarda - ela tem o
    codigo da chapa, a quantidade e o funcionario, e mais nada. Quem
    sabe o que foi gravado e a vaga da OS que gerou o movimento.
    """
    campos = (["OSTIT%d" % i for i in range(1, 5)]
              + ["OSESP%d" % i for i in range(1, 5)]
              + ["OSLAN%d" % i for i in range(1, 5)]
              + ["OSTIME", "OSRESP"])
    perguntar(cur, "SELECT %s FROM OS WHERE OSCOD = ?" % ", ".join(campos),
                (numero,))
    linha = cur.fetchone()
    if not linha:
        return None, "", []

    vagas = []
    for i in range(4):
        titulo = _texto(linha[i])
        if not titulo:
            continue
        vagas.append({"chapa": linha[4 + i], "quantas": _n(linha[8 + i]),
                      "titulo": titulo})
    return linha[12], _texto(linha[13]), vagas


def _casar(movimentos, vagas):
    """
    Diz qual vaga gerou cada movimento.

    O gatilho TR_OS_BEFO lanca as vagas na ordem, mas a lista de
    movimentos vem FILTRADA pelo dono da chapa - uma OS com chapa
    propria da Finart no meio deixaria buracos. Entao case pelo par
    (chapa, quantidade), que e o que o gatilho copia da vaga, e so caia
    na ordem quando isso nao resolver.

    Conferido em producao nas quatro OS da SOLIDA de 14/09/2026: os 16
    movimentos casaram pelo par, um a um.
    """
    livres = list(vagas)
    casadas = []
    for m in movimentos:
        achou = None
        for v in livres:
            if v["chapa"] == m["chapa"] and abs(m["qtd"]) == v["quantas"]:
                achou = v
                break
        if achou is None and livres:
            achou = livres[0]              # o gatilho lanca na ordem
        if achou is not None:
            livres.remove(achou)
        casadas.append(achou)
    return casadas


def do_dia(dono, con, dia):
    """
    O movimento de um dia, linha a linha, com o nome do material.

    Cada um e {hora, os, titulo, quem, chapa, nome, entrou, saiu}.

    A hora nao esta na MOV - MOVDIA e so data. Ela vem do OSTIME da OS
    que gerou o movimento; lancamento a mao (entrada de chapa nova) nao
    tem OS, e fica sem hora.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT MOVCHA, MOVNCH, MOVENT, MOVSDA, MOVQTD, MOVNOS, "
                "MOVNFU, MOVOBS FROM MOV WHERE MOVCLI = ? AND MOVDIA = ? "
                "ORDER BY MOVCOD", (dono, dia))
    linhas = []
    for cha, nome, entrou, saiu, qtd, numero, quem, obs in cur.fetchall():
        linhas.append({"chapa": cha, "nome": _texto(nome),
                       "entrou": _n(entrou), "saiu": _n(saiu),
                       "qtd": _n(qtd), "os": int(_n(numero)) or None,
                       "quem": _texto(quem), "obs": _texto(obs),
                       "hora": None, "titulo": ""})

    for numero in sorted({m["os"] for m in linhas if m["os"]}):
        hora, quem, vagas = _vagas_da_os(cur, numero)
        desta = [m for m in linhas if m["os"] == numero]
        for m, vaga in zip(desta, _casar(desta, vagas)):
            m["hora"] = hora
            # O OPERADOR E QUEM ABRIU A OS (OSRESP), e nao o MOVNFU do
            # movimento. Os dois discordam, e ja custaram caro uma vez:
            # o MOVNFU e de quem SALVOU a OS por ultimo, porque o
            # TR_OS_BEFO apaga e refaz todo o movimento a cada gravacao.
            # A OS 19688 de 14/09/2026 foi aberta pela FIA e os
            # movimentos dela dizem JOAOZIMAR, que so passou por ali
            # depois. Ver a armadilha 15 na skill do gerempre.
            if quem:
                m["quem"] = quem
            if vaga:
                m["titulo"] = vaga["titulo"]

    for m in linhas:
        if not m["titulo"]:
            # entrada de chapa nova, lancada a mao: nao ha OS nem vaga.
            # A observacao do proprio movimento e o que ha de nome.
            m["titulo"] = m["obs"] or ("ENTRADA DE CHAPA" if m["entrou"]
                                       else "")
    return linhas


def movimento_depois(dono, con, dia):
    """
    {chapa: quanto andou DEPOIS deste dia}, para desandar o saldo.

    O saldo que a CHA guarda e o de AGORA. Para saber o de quando o dia
    fechou, basta tirar dele tudo o que se moveu desde entao - e o razao
    garante que a conta fecha: CHAQTD = SUM(MOVQTD) daquela chapa.

    Para o dia de hoje isto devolve vazio, e o saldo fica como esta.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT MOVCHA, SUM(MOVQTD) FROM MOV "
                "WHERE MOVCLI = ? AND MOVDIA > ? GROUP BY MOVCHA",
                (dono, dia))
    return {c: _n(q) for c, q in cur.fetchall()}


# ----------------------------------------------------------------------
# A CONFERENCIA COM O RELATORIO DO PROPRIO GEREMPRE
# ----------------------------------------------------------------------
# "o total de estoque sempre tem que bater exatamente com o relatorio do
# gerempre, preciso que vc sempre faca essa comparacao" - o operador,
# 14/09/2026.
#
# O relatorio de estoque do GEREMPRE e um procedimento guardado no
# proprio banco, e ele conta DIFERENTE do que esta folha conta:
#
#   a folha    le CHA.CHAQTD, o saldo que o gatilho mantem, pelo CODIGO
#              da chapa
#   o GEREMPRE soma os MOVIMENTOS - saldo anterior + entradas - saidas -
#              e casa a chapa pelo NOME (movnch = chanom)
#
# Sao dois caminhos independentes para o mesmo numero, e e por isso que
# a comparacao vale: chapa renomeada, chapa com nome repetido, ou
# movimento gravado sem o saldo andar (o gatilho erra em silencio quando
# o par chapa+dono nao existe - armadilha do gerempre) aparecem aqui e
# em nenhum outro lugar.
#
# DOIS NOMES PARA O MESMO PROCEDIMENTO. Ha SP_ESTOQUE e SP_ESTOQUE2,
# com o codigo IDENTICO. Em 14/09/2026 o SP_ESTOQUE estava ILEGIVEL
# neste banco - 'page 73787 is of wrong type' ao ler os parametros dele
# -, e o SP_ESTOQUE2 respondia normalmente. Por isso tenta-se os dois:
# o defeito e do banco, nao do procedimento, e pode ser consertado.
RELATORIOS_DO_GEREMPRE = ("SP_ESTOQUE", "SP_ESTOQUE2")

MARCA_DO_SALDO = "ESTOQUE ATUAL "


def estoque_do_gerempre(dono, con, dia):
    """
    {nome_da_chapa: saldo} como o RELATORIO DO GEREMPRE o calcula.

    Devolve None quando nao deu para rodar o relatorio - e None nao e
    zero: a folha tem de dizer 'nao consegui conferir' em vez de deixar
    quem le achando que conferiu.

    O periodo e o dia inteiro, e nao o mes: o procedimento devolve
    'ESTOQUE ATUAL' = saldo anterior + entradas - saidas, entao com
    datai = dataf = o dia sai o saldo no FIM daquele dia. Conferido
    contra 01/09-14/09 e contra 2015-2026: o mesmo numero, e com uma
    lista trinta vezes menor.
    """
    for nome in RELATORIOS_DO_GEREMPRE:
        try:
            cur = con.cursor()
            cur.execute("SELECT * FROM %s(?, ?, ?)" % nome, (dono, dia, dia))
            saldos = {}
            for linha in cur.fetchall():
                rotulo = _texto(linha[1])
                if rotulo.startswith(MARCA_DO_SALDO):
                    saldos[rotulo[len(MARCA_DO_SALDO):]] = _n(linha[2])
            if saldos:
                return saldos
        except Exception:
            continue                      # tenta o outro nome
    return None


def razao(dono, con):
    """
    {codigo: (saldo_da_CHA, soma_da_MOV)} - a conferencia de sempre.

    CHA.CHAQTD tem de ser a soma dos MOV daquela chapa e daquele dono.
    Em 10/09/2026 as 96 chapas do banco batiam, todas. Quando parar de
    bater, o numero desta folha deixou de valer, e quem le precisa
    saber disso ANTES de decidir comprar chapa.
    """
    cur = con.cursor()
    perguntar(cur, "SELECT CHACOD, CHAQTD FROM CHA WHERE CHACLI = ?", (dono,))
    saldos = {c: _n(q) for c, q in cur.fetchall()}
    perguntar(cur, "SELECT MOVCHA, SUM(MOVQTD) FROM MOV WHERE MOVCLI = ? "
                "GROUP BY MOVCHA", (dono,))
    somas = {c: _n(s) for c, s in cur.fetchall()}
    return {c: (saldos[c], somas.get(c, 0.0)) for c in saldos}


# ----------------------------------------------------------------------
# A CONTA DA FOLGA
# ----------------------------------------------------------------------

def media_por_dia_util(historico):
    """
    Quanto sai por dia de trabalho, pelos ultimos DIAS_DA_MEDIA dias
    que tiveram movimento.

    Dia sem movimento nao entra: feriado e domingo puxariam a media
    para baixo e a folga para cima, que e o erro que custa caro.
    """
    com_saida = [saiu for _, saiu, _ in historico if saiu > 0]
    if not com_saida:
        return 0.0
    ultimos = com_saida[-DIAS_DA_MEDIA:]
    return sum(ultimos) / float(len(ultimos))


def dias_de_folga(saldo, media):
    """Quantos dias uteis o saldo ainda cobre. None quando nao ha consumo."""
    if media <= 0:
        return None
    return saldo / media


def data_do_fim(dias, de=None):
    """
    Em que dia o saldo acaba, pulando sabado e domingo.

    Contar em dias de calendario adiantaria o susto em dois setimos - e
    um estoque que 'dura cinco dias' numa sexta-feira dura ate a sexta
    seguinte, nao ate a quarta.
    """
    if dias is None:
        return None
    de = de or agora_util().date()
    inteiros = int(dias)
    quando = de
    andados = 0
    while andados < inteiros:
        quando += datetime.timedelta(days=1)
        if quando.weekday() < 5:
            andados += 1
    return quando


# ----------------------------------------------------------------------
# O LEVANTAMENTO
# ----------------------------------------------------------------------

def levantar(cliente=CLIENTE_PADRAO, con=None, dia=None):
    """
    Tudo o que a folha mostra, lido do banco numa ligacao so.

    Devolve None quando o cliente nao esta no cadastro da FIA.
    """
    from .gerempre import conectar

    dono = GEREMPRE_CLIENTES.get(cliente)
    if dono is None:
        return None

    proprio = con is None
    con = con or conectar()
    try:
        dia = dia or agora_util().date()
        desde = dia - datetime.timedelta(days=90)

        vivas = chapas_vivas(dono, con)
        historico = por_dia(dono, con, desde)
        conferencia = razao(dono, con)
        movimento = do_dia(dono, con, dia)
        quantas_paradas, saldo_parado = paradas(dono, con)
        depois = movimento_depois(dono, con, dia)
        do_gerempre = estoque_do_gerempre(dono, con, dia)

        for chapa in vivas:
            # O SALDO E O DAQUELE DIA, e nao o de agora. Importa no
            # relatorio que fecha o dia: escrito as 00:00 os dois sao
            # iguais, mas um que ficou para tras - a FIA desligada no
            # fim de semana - sairia com o saldo de hoje e o movimento
            # de sexta, e o cliente receberia um numero que nunca
            # existiu.
            chapa["saldo"] -= depois.get(chapa["cod"], 0.0)
            passado = historico.get(chapa["cod"], [])
            chapa["historico"] = passado
            chapa["media"] = media_por_dia_util(passado)
            chapa["folga"] = dias_de_folga(chapa["saldo"], chapa["media"])
            chapa["acaba"] = data_do_fim(chapa["folga"], dia)
            chapa["entrou_hoje"] = sum(m["entrou"] for m in movimento
                                       if m["chapa"] == chapa["cod"])
            chapa["saiu_hoje"] = sum(m["saiu"] for m in movimento
                                     if m["chapa"] == chapa["cod"])
            cha, mov = conferencia.get(chapa["cod"], (0.0, 0.0))
            chapa["razao_bate"] = abs(cha - mov) < 0.001

            # o mesmo saldo, pelo caminho do GEREMPRE. None quando nao
            # deu para rodar o relatorio dele - e None nao e zero.
            if do_gerempre is None:
                chapa["gerempre"] = None
                chapa["bate_com_o_gerempre"] = None
            else:
                dele = do_gerempre.get(chapa["nome"])
                chapa["gerempre"] = dele
                chapa["bate_com_o_gerempre"] = (
                    dele is not None and abs(chapa["saldo"] - dele) < 0.001)

        return {"cliente": cliente, "dono": dono, "dia": dia,
                "chapas": vivas, "movimento": movimento,
                "paradas": (quantas_paradas, saldo_parado),
                "conferi_o_gerempre": do_gerempre is not None,
                "quando": agora_util(),
                "sentinela": sentinela(dono, con)}
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


# ----------------------------------------------------------------------
# A FOLHA
# ----------------------------------------------------------------------

MARGEM = 14.0
CINZA = (120, 120, 120)
PRETO = (20, 20, 20)
ALERTA = (190, 30, 30)
BARRA = (160, 175, 190)
BARRA_HOJE = (70, 100, 140)
RISCO = (200, 200, 200)


def _dia_por_extenso(d):
    return "%s, %d de %s de %d" % (SEMANA[d.weekday()], d.day,
                                   MESES[d.month - 1], d.year)


def _dinheiro(v):
    """9.0 -> 'R$ 9,00'. Virgula, como o resto dos papeis da casa."""
    return ("R$ %.2f" % v).replace(".", ",")


def _folga_em_texto(chapa):
    """'dura 5 dias uteis - ate 18/09', ou por que nao da para dizer."""
    if chapa["folga"] is None:
        return "sem consumo para calcular"
    dias = int(chapa["folga"])
    if dias < 1:
        return "ACABA HOJE"
    return "dura %d dia%s de trabalho - ate %s" % (
        dias, "" if dias == 1 else "s", chapa["acaba"].strftime("%d/%m"))


# ----------------------------------------------------------------------
# A FOLHA
# ----------------------------------------------------------------------
# Refeita em 14/09/2026, a pedido do operador: "nao gostei do relatorio e
# preciso de mais campos... retire os graficos que mostram os ultimos
# dias, e me mostre com os seguintes campos, horario, numero da OS da
# finart (gerempre), nome do material, operador, chapa usada e
# quantidade, no final gostaria tambem de colocar saldo atual de cada
# chapa, entrada, saida e saldo atual".
#
# O grafico saiu. Ele mostrava a FORMA do consumo, que e coisa de quem
# planeja compra; quem esta no dia quer saber O QUE saiu, de quem e em
# que chapa - e isso e tabela, nao desenho.

MARGEM = 14.0
DIREITA = A4_MM[0] - MARGEM

# As colunas do movimento, em milimetros a partir da borda. O nome do
# material fica com a maior fatia de proposito: ele vem do OSTIT, que
# guarda 50 letras, e cortar justo ele seria perder a unica coisa que
# diz que servico foi aquele.
# Medidas tiradas do texto de verdade, e nao estimadas: 'EUDSON
# JUNIOR' ocupa 25,2 mm, 'SOLIDA 775X635 - 780E' 34,0 mm, e um titulo
# cheio de 44 letras, 77,4 mm.
COL_HORA = MARGEM
COL_OS = MARGEM + 12.0
COL_MATERIAL = MARGEM + 26.0
COL_OPERADOR = MARGEM + 103.0          # sobram 74 mm para o material
COL_CHAPA = MARGEM + 134.0             # e 28 mm para o operador
COL_QTD = DIREITA                      # alinhada a direita

ALTURA_DA_LINHA = 5.3
LINHAS_NA_PRIMEIRA = 26                # o cabecalho come espaco
LINHAS_NAS_OUTRAS = 44

CINZA = (120, 120, 120)
PRETO = (20, 20, 20)
ALERTA = (190, 30, 30)
ENTRADA = (30, 110, 60)
RISCO = (205, 205, 205)
ZEBRA = (246, 245, 243)


def _dia_por_extenso(d):
    return "%s, %d de %s de %d" % (SEMANA[d.weekday()], d.day,
                                   MESES[d.month - 1], d.year)


def _dinheiro(v):
    """9.0 -> 'R$ 9,00'. Virgula, como o resto dos papeis da casa."""
    return ("R$ %.2f" % v).replace(".", ",")


def _folga_em_texto(chapa):
    """'dura 5 dias de trabalho - ate 18/09', ou por que nao da para dizer."""
    if chapa["folga"] is None:
        return "sem consumo para calcular"
    dias = int(chapa["folga"])
    if dias < 1:
        return "ACABA HOJE"
    return "dura %d dia%s de trabalho - ate %s" % (
        dias, "" if dias == 1 else "s", chapa["acaba"].strftime("%d/%m"))


def _cortar(d, texto, fonte, largura_px):
    """O texto que cabe na coluna, terminando em reticencias se sobrar."""
    if d.textlength(texto, font=fonte) <= largura_px:
        return texto
    while texto and d.textlength(texto + "...", font=fonte) > largura_px:
        texto = texto[:-1]
    return texto + "..."


def _paginas_do_movimento(movimento):
    """O movimento repartido em paginas. Sempre ao menos uma."""
    if not movimento:
        return [[]]
    paginas = [movimento[:LINHAS_NA_PRIMEIRA]]
    resto = movimento[LINHAS_NA_PRIMEIRA:]
    while resto:
        paginas.append(resto[:LINHAS_NAS_OUTRAS])
        resto = resto[LINHAS_NAS_OUTRAS:]
    return paginas


def folha(dados, dpi=DPI):
    """
    A folha A4 em pe do estoque. Devolve a PRIMEIRA pagina.

    Dia cheio passa de uma pagina - em 14/09/2026 foram 16 movimentos, e
    uma OS de quatro vagas lanca quatro linhas. Quem quer todas chama
    folhas().
    """
    return folhas(dados, dpi=dpi)[0]


def folhas(dados, dpi=DPI):
    """Todas as paginas da folha, na ordem."""
    from PIL import Image, ImageDraw

    def px(mm):
        return int(round(mm / 25.4 * dpi))

    paginas = _paginas_do_movimento(dados["movimento"])
    quantas = len(paginas)
    feitas = []

    for numero, linhas in enumerate(paginas, start=1):
        pagina = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")
        d = ImageDraw.Draw(pagina)

        g_titulo = _fonte(px(5.6), True)
        g_cliente = _fonte(px(8.6), True)
        g_secao = _fonte(px(3.8), True)
        g_coluna = _fonte(px(2.7), True)
        g_linha = _fonte(px(3.0))
        g_numero = _fonte(px(3.2), True)
        g_texto = _fonte(px(3.2))
        g_miudo = _fonte(px(2.6))

        if numero == 1:
            y = _cabecalho(pagina, d, px, dados, g_titulo, g_cliente, g_texto)
            d.text((px(MARGEM), px(y)), "O QUE ANDOU HOJE", font=g_secao,
                   fill=PRETO)
            d.text((px(DIREITA), px(y + 0.6)),
                   "%d lancamento(s)" % len(dados["movimento"]),
                   font=g_miudo, fill=CINZA, anchor="ra")
            y += 7.0
        else:
            d.text((px(MARGEM), px(14.0)),
                   "ESTOQUE DE CHAPAS - %s   %s"
                   % (dados["cliente"], dados["dia"].strftime("%d/%m/%Y")),
                   font=g_secao, fill=CINZA)
            y = 24.0

        y = _cabecalho_da_tabela(d, px, y, g_coluna)
        y = _linhas_do_movimento(d, px, y, linhas, g_linha)

        if numero == quantas:
            y = _somas_do_dia(d, px, y, dados, g_texto, g_miudo)
            _saldo(d, px, y, dados, g_secao, g_coluna, g_linha, g_numero,
                   g_miudo)

        _rodape(d, px, dados, g_texto, g_miudo, numero, quantas)
        feitas.append(pagina)

    return feitas


def _cabecalho(pagina, d, px, dados, g_titulo, g_cliente, g_texto):
    """O logotipo, o nome do cliente e o dia. Devolve onde continuar."""
    from PIL import Image

    if os.path.exists(LOGO):
        try:
            logo = Image.open(LOGO).convert("RGBA")
            larg = px(38.0)
            alt = int(logo.height * larg / float(logo.width))
            pronto = logo.resize((larg, alt), Image.LANCZOS)
            pagina.paste(pronto, (px(MARGEM), px(13.0)), pronto)
        except OSError:
            pass

    d.text((px(DIREITA), px(12.0)), "ESTOQUE DE CHAPAS", font=g_titulo,
           fill=CINZA, anchor="ra")
    d.text((px(DIREITA), px(17.5)), dados["cliente"], font=g_cliente,
           fill=PRETO, anchor="ra")
    d.text((px(DIREITA), px(29.5)), _dia_por_extenso(dados["dia"]),
           font=g_texto, fill=CINZA, anchor="ra")
    d.text((px(DIREITA), px(34.0)),
           "atualizado as %s" % dados["quando"].strftime("%H:%M"),
           font=g_texto, fill=CINZA, anchor="ra")
    d.line([(px(MARGEM), px(40.0)), (px(DIREITA), px(40.0))], fill=RISCO,
           width=max(1, px(0.3)))
    return 47.0


def _cabecalho_da_tabela(d, px, y, g_coluna):
    for x, texto, ancora in ((COL_HORA, "HORA", "la"),
                             (COL_OS, "OS", "la"),
                             (COL_MATERIAL, "MATERIAL", "la"),
                             (COL_OPERADOR, "OPERADOR", "la"),
                             (COL_CHAPA, "CHAPA USADA", "la"),
                             (COL_QTD, "QUANT.", "ra")):
        d.text((px(x), px(y)), texto, font=g_coluna, fill=CINZA,
               anchor=ancora)
    y += 4.2
    d.line([(px(MARGEM), px(y)), (px(DIREITA), px(y))], fill=RISCO,
           width=max(1, px(0.25)))
    return y + 1.6


def _linhas_do_movimento(d, px, y, linhas, g_linha):
    if not linhas:
        d.text((px(MARGEM), px(y + 1.0)), "nada ainda hoje", font=g_linha,
               fill=CINZA)
        return y + 8.0

    for i, m in enumerate(linhas):
        if i % 2:
            d.rectangle([px(MARGEM - 1.5), px(y - 1.0),
                         px(DIREITA + 1.5), px(y + ALTURA_DA_LINHA - 1.4)],
                        fill=ZEBRA)
        entrada = m["entrou"] > 0
        cor = ENTRADA if entrada else PRETO

        d.text((px(COL_HORA), px(y)),
               m["hora"].strftime("%H:%M") if m["hora"] else "--:--",
               font=g_linha, fill=CINZA)
        d.text((px(COL_OS), px(y)), str(m["os"]) if m["os"] else "-",
               font=g_linha, fill=PRETO)
        d.text((px(COL_MATERIAL), px(y)),
               _cortar(d, m["titulo"] or "-", g_linha,
                       px(COL_OPERADOR - COL_MATERIAL - 3.0)),
               font=g_linha, fill=cor)
        d.text((px(COL_OPERADOR), px(y)),
               _cortar(d, m["quem"], g_linha,
                       px(COL_CHAPA - COL_OPERADOR - 3.0)),
               font=g_linha, fill=CINZA)
        d.text((px(COL_CHAPA), px(y)),
               _cortar(d, m["nome"], g_linha,
                       px(COL_QTD - COL_CHAPA - 9.0)),
               font=g_linha, fill=CINZA)
        d.text((px(COL_QTD), px(y)),
               "+%.0f" % m["entrou"] if entrada else "-%.0f" % m["saiu"],
               font=g_linha, fill=cor, anchor="ra")
        y += ALTURA_DA_LINHA
    return y


def _somas_do_dia(d, px, y, dados, g_texto, g_miudo):
    entrou = sum(m["entrou"] for m in dados["movimento"])
    saiu = sum(m["saiu"] for m in dados["movimento"])
    y += 1.0
    d.line([(px(MARGEM), px(y)), (px(DIREITA), px(y))], fill=RISCO,
           width=max(1, px(0.25)))
    y += 2.2
    d.text((px(COL_MATERIAL), px(y)), "no dia", font=g_miudo, fill=CINZA)
    d.text((px(COL_QTD - 24.0), px(y)), "entraram %.0f" % entrou,
           font=g_texto, fill=ENTRADA, anchor="ra")
    d.text((px(COL_QTD), px(y)), "sairam %.0f" % saiu, font=g_texto,
           fill=PRETO, anchor="ra")
    return y + 12.0


# As colunas do saldo, tambem em milimetros da borda.
SAL_CHAPA = MARGEM
SAL_MEDIDA = MARGEM + 58.0
SAL_ENTRADA = MARGEM + 96.0            # estas quatro vao alinhadas
SAL_SAIDA = MARGEM + 120.0             # a direita
SAL_SALDO = MARGEM + 152.0
SAL_GEREMPRE = DIREITA


def _saldo(d, px, y, dados, g_secao, g_coluna, g_linha, g_numero, g_miudo):
    d.text((px(MARGEM), px(y)), "SALDO DE CADA CHAPA", font=g_secao,
           fill=PRETO)
    y += 7.0

    for x, texto, ancora in ((SAL_CHAPA, "CHAPA", "la"),
                             (SAL_MEDIDA, "MEDIDA", "la"),
                             (SAL_ENTRADA, "ENTRADA", "ra"),
                             (SAL_SAIDA, "SAIDA", "ra"),
                             (SAL_SALDO, "SALDO ATUAL", "ra"),
                             (SAL_GEREMPRE, "NO GEREMPRE", "ra")):
        d.text((px(x), px(y)), texto, font=g_coluna, fill=CINZA,
               anchor=ancora)
    y += 4.2
    d.line([(px(MARGEM), px(y)), (px(DIREITA), px(y))], fill=RISCO,
           width=max(1, px(0.25)))
    y += 2.2

    if not dados["chapas"]:
        d.text((px(MARGEM), px(y)), "nenhuma chapa ativa no cadastro",
               font=g_linha, fill=CINZA)
        return

    for chapa in dados["chapas"]:
        pouco = chapa["folga"] is not None and chapa["folga"] <= POUCO_DIA
        cor = ALERTA if pouco else PRETO
        d.text((px(SAL_CHAPA), px(y)), chapa["nome"], font=g_numero,
               fill=cor)
        d.text((px(SAL_MEDIDA), px(y)),
               "%d x %d mm" % chapa["medida"], font=g_linha, fill=CINZA)
        d.text((px(SAL_ENTRADA), px(y)), "%.0f" % chapa["entrou_hoje"],
               font=g_linha, fill=ENTRADA if chapa["entrou_hoje"] else CINZA,
               anchor="ra")
        d.text((px(SAL_SAIDA), px(y)), "%.0f" % chapa["saiu_hoje"],
               font=g_linha, fill=CINZA, anchor="ra")
        d.text((px(SAL_SALDO), px(y)), "%.0f" % chapa["saldo"],
               font=g_numero, fill=cor, anchor="ra")

        # O MESMO SALDO, PELO CAMINHO DO GEREMPRE. Sao duas contas
        # independentes: a da esquerda vem do saldo que o gatilho
        # mantem; esta vem de somar os movimentos, como o relatorio
        # dele faz. Diferiram? O numero da esquerda nao vale.
        if chapa["bate_com_o_gerempre"] is None:
            dele, cor_dele = "?", CINZA
        elif chapa["bate_com_o_gerempre"]:
            dele, cor_dele = "%.0f" % chapa["gerempre"], CINZA
        else:
            dele = ("%.0f" % chapa["gerempre"]
                    if chapa["gerempre"] is not None else "nao achei")
            cor_dele = ALERTA
        d.text((px(SAL_GEREMPRE), px(y)), dele, font=g_numero,
               fill=cor_dele, anchor="ra")
        y += 5.0
        d.text((px(SAL_CHAPA), px(y)),
               "%s a gravacao   |   sai ~%.0f por dia de trabalho"
               % (_dinheiro(chapa["preco"]), chapa["media"]),
               font=g_miudo, fill=CINZA)
        y += 6.4


def _rodape(d, px, dados, g_texto, g_miudo, numero, quantas):
    base = A4_MM[1] - 16.0
    d.line([(px(MARGEM), px(base - 4.0)), (px(DIREITA), px(base - 4.0))],
           fill=RISCO, width=max(1, px(0.25)))

    # AS DUAS CONFERENCIAS, e nao uma. Sao caminhos independentes para o
    # mesmo numero, e cada um pega um defeito diferente.
    torto = [c for c in dados["chapas"] if not c["razao_bate"]]
    fora = [c for c in dados["chapas"] if c["bate_com_o_gerempre"] is False]

    if not dados.get("conferi_o_gerempre"):
        d.text((px(MARGEM), px(base)),
               "NAO CONSEGUI CONFERIR com o relatorio do GEREMPRE - a "
               "coluna da direita esta vazia. O saldo acima nao foi "
               "confrontado com nada.",
               font=g_texto, fill=ALERTA)
    elif fora:
        d.text((px(MARGEM), px(base)),
               "ATENCAO: %s NAO bate com o relatorio de estoque do "
               "GEREMPRE. Nao use este numero ate alguem olhar."
               % ", ".join(c["nome"] for c in fora),
               font=g_texto, fill=ALERTA)
    elif torto:
        d.text((px(MARGEM), px(base)),
               "ATENCAO: o saldo de %s NAO bate com a soma dos movimentos. "
               "O numero acima nao vale."
               % ", ".join(c["nome"] for c in torto),
               font=g_texto, fill=ALERTA)
    else:
        d.text((px(MARGEM), px(base)),
               "conferido: bate com o relatorio de estoque do GEREMPRE e "
               "com a soma dos movimentos, chapa por chapa",
               font=g_miudo, fill=CINZA)

    quantas_paradas, parado = dados["paradas"]
    if quantas_paradas:
        d.text((px(MARGEM), px(base + 4.0)),
               "ha %d chapa(s) desativada(s) no cadastro carregando %.0f de "
               "saldo antigo - nao entram nesta conta"
               % (quantas_paradas, parado),
               font=g_miudo, fill=CINZA)

    conta = ("pagina %d de %d   |   " % (numero, quantas)) if quantas > 1 else ""
    d.text((px(DIREITA), px(base + 8.0)),
           "%sFINART (FIA) - lido do GEREMPRE, sem escrever nada" % conta,
           font=g_miudo, fill=CINZA, anchor="ra")


# ----------------------------------------------------------------------
# GRAVAR, ABRIR E ACOMPANHAR
# ----------------------------------------------------------------------

def caminho_da_folha(cliente=CLIENTE_PADRAO, pasta=None):
    return os.path.join(pasta or PASTA_CONTROLE, ARQUIVO % cliente)


_RECLAMEI_DA_TRAVA = set()     # de quem ja se disse 'esta aberta'


def gravar(dados, pasta=None, dpi=DPI):
    """
    Grava a folha por cima da de ontem e devolve o caminho, ou None.

    UM arquivo por cliente, e nao um por dia: quem acompanha estoque
    quer o numero de agora, e uma pasta com trinta PDFs por mes seria
    mais um lugar onde procurar. O passado esta todo no GEREMPRE.

    A FOLHA ABERTA NA TELA TRANCA O ARQUIVO. Foi o que aconteceu na
    primeira vez que ela rodou de verdade, em 14/09/2026: o operador
    estava com ela aberta no leitor de PDF, e a troca deu 'WinError 5:
    acesso negado'. No Windows, leitor de PDF aberto segura o arquivo, e
    nao ha como trocar por baixo.

    Entao isto NAO e erro: e 'agora nao da'. Devolve None, diz uma vez
    so, e quem chama tenta de novo na volta seguinte - no minuto em que
    a folha for fechada, ela se atualiza sozinha.
    """
    caminho = caminho_da_folha(dados["cliente"], pasta)
    meio = caminho + ".tmp"
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        # monta ao lado e troca de uma vez: quem abrir a folha no meio
        # da gravacao tem de achar a de antes inteira, nunca meia folha.
        paginas = folhas(dados, dpi=dpi)
        paginas[0].save(meio, "PDF", resolution=dpi, save_all=True,
                        append_images=paginas[1:])
        os.replace(meio, caminho)
        _RECLAMEI_DA_TRAVA.discard(caminho)
        return caminho
    except PermissionError:
        if caminho not in _RECLAMEI_DA_TRAVA:
            _RECLAMEI_DA_TRAVA.add(caminho)
            log("A folha de estoque da %s esta aberta em alguma tela, entao "
                "nao consigo troca-la. Feche o leitor de PDF e ela se "
                "atualiza sozinha." % dados["cliente"])
        _limpar(meio)
        return None
    except (OSError, ValueError) as e:
        log("Nao consegui gravar a folha de estoque: %s" % e, alerta=True)
        _limpar(meio)
        return None


def _limpar(caminho):
    """Tira o arquivo do meio do caminho, sem reclamar se ja nao houver."""
    try:
        os.remove(caminho)
    except OSError:
        pass


def abrir(caminho):
    """Poe a folha na tela, com o leitor de PDF do Windows."""
    if not caminho:
        return False
    try:
        os.startfile(caminho)       # so existe no Windows, e e onde ela roda
        return True
    except (OSError, AttributeError) as e:
        log("Nao consegui abrir a folha de estoque: %s" % e)
        return False


_ULTIMA = {}                        # cliente -> sentinela ja desenhada


def esquecer():
    """Zera a memoria da sentinela. Para os testes e para o arranque."""
    _ULTIMA.clear()


def acompanhar(cliente=CLIENTE_PADRAO, con=None, pasta=None):
    """
    Redesenha a folha SE o movimento do cliente mudou. Devolve o
    caminho quando redesenhou, e None quando nao havia o que fazer.

    E isto que a FIA chama a cada volta do laco. O custo normal e uma
    consulta - 0,14 s - e nao a folha inteira, que leva 0,37 s.
    """
    from .gerempre import conectar, SemLigacao

    dono = GEREMPRE_CLIENTES.get(cliente)
    if dono is None:
        return None

    proprio = con is None
    try:
        con = con or conectar()
    except SemLigacao:
        return None                 # sem banco nao se inventa estoque
    try:
        agora = sentinela(dono, con)
        primeira = cliente not in _ULTIMA
        if not primeira and agora == _ULTIMA[cliente]:
            return None
        dados = levantar(cliente, con=con)
        if not dados:
            return None
        caminho = gravar(dados, pasta=pasta)
        if caminho is None:
            # Nao deu para trocar o arquivo - a folha costuma estar
            # aberta na tela de alguem. A sentinela NAO e guardada: a
            # volta seguinte tenta de novo, e no minuto em que a folha
            # for fechada ela se atualiza. Guardando aqui, o movimento
            # de hoje ficaria de fora para sempre.
            return None
        _ULTIMA[cliente] = dados["sentinela"]
        if not primeira:
            log("Estoque da %s: o movimento mudou, refiz a folha" % cliente)
        return caminho
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass



# ----------------------------------------------------------------------
# OS DOIS RELATORIOS QUE VAO PARA O CLIENTE
# ----------------------------------------------------------------------
# Regra do operador, 14/09/2026: "se eu te pedir um relatorio atual,
# voce gera na hora e salva na PASTA DA SOLIDA, com o nome relatorio
# atual e o horario; se eu nao te pedir, segue a rotina: quando der meia
# noite o dia se encerra e voce salva o relatorio dentro da pasta do dia
# com nome RELATORIO CHAPAS SOLIDA (data), assim quando eu chegar cedo eu
# envio manualmente para eles acompanharem".
#
# A folha de dentro da casa (a ESTOQUE <cliente>.pdf da PASTA_CONTROLE)
# continua como esta: e a que se reescreve o dia inteiro. Estas duas
# saem da MESMA folha, mas sao arquivos que ficam parados - um papel
# que o cliente recebe nao pode mudar depois de enviado.


def pasta_do_cliente(cliente):
    """A pasta daquele cliente no V:, ou None se ele nao tiver uma."""
    from . import config

    chave = PASTA_DO_CLIENTE.get(cliente)
    return getattr(config, chave, None) if chave else None


def guardar(dados, caminho, dpi=DPI):
    """
    Grava a folha num caminho qualquer. Devolve o caminho, ou None.

    Diferente do gravar(): aquele reescreve a folha de dentro da casa e
    engole a trava do leitor de PDF, porque ele tenta de novo daqui a um
    minuto. Este e pedido por gente e escrito uma vez - falhou, tem de
    dizer.
    """
    try:
        pasta = os.path.dirname(caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        paginas = folhas(dados, dpi=dpi)
        paginas[0].save(caminho, "PDF", resolution=dpi, save_all=True,
                        append_images=paginas[1:])
        return caminho
    except (OSError, ValueError) as e:
        log("Nao consegui gravar %s: %s" % (os.path.basename(caminho), e),
            alerta=True)
        return None


def relatorio_agora(cliente=CLIENTE_PADRAO, con=None, quando=None):
    """
    O relatorio ATUAL, a pedido: gera na hora e devolve o caminho.

    Vai na RAIZ da pasta do cliente, com data e hora no nome. A data
    entra junto porque a raiz e a mesma o mes inteiro: so com a hora, o
    pedido de amanha as 14h escreveria por cima do de hoje as 14h.
    """
    base = pasta_do_cliente(cliente)
    if not base:
        log("Nao sei em que pasta guardar o relatorio da %s" % cliente,
            alerta=True)
        return None

    quando = quando or agora_util()
    dados = levantar(cliente, con=con, dia=quando.date())
    if not dados:
        return None
    dados["quando"] = quando

    nome = RELATORIO_ATUAL % (quando.strftime("%d-%m"),
                              quando.strftime("%Hh%M"))
    return guardar(dados, os.path.join(base, nome))


def nome_do_fechamento(cliente, dia):
    return RELATORIO_DO_DIA % (cliente, dia.strftime("%d-%m-%Y"))


def caminho_do_fechamento(cliente, dia, criar=False):
    """Onde o relatorio daquele dia mora, ou None se a pasta nao existe."""
    base = pasta_do_cliente(cliente)
    if not base:
        return None
    pasta = pasta_da_data(base, dia, criar=criar)
    if not pasta:
        return None
    return os.path.join(pasta, nome_do_fechamento(cliente, dia))


def ja_fechado(cliente, dia):
    caminho = caminho_do_fechamento(cliente, dia)
    return bool(caminho) and os.path.exists(caminho)


def fechar_o_dia(cliente, dia, con=None):
    """
    O relatorio de FECHAMENTO daquele dia, dentro da pasta daquele dia.

    Nao refaz o que ja existe: o papel que o cliente recebeu nao muda
    depois. Dia sem movimento nenhum nao gera arquivo - mandar ao
    cliente uma folha vazia e pedir para ele parar de olhar.

    Devolve o caminho quando escreveu, e None quando nao havia o que
    escrever.
    """
    from .gerempre import conectar, SemLigacao

    if ja_fechado(cliente, dia):
        return None

    proprio = con is None
    try:
        con = con or conectar()
    except SemLigacao as e:
        log("Sem GEREMPRE para fechar o dia %s da %s (%s)"
            % (dia.strftime("%d/%m"), cliente, str(e)[:50]))
        return None
    try:
        dados = levantar(cliente, con=con, dia=dia)
        if not dados or not dados["movimento"]:
            return None

        # A folha diz 'atualizado as HH:MM'. Num fechamento isso tem de
        # ser o fim DAQUELE dia, e nao a hora em que a FIA passou por
        # aqui - senao um relatorio de sexta escrito na segunda diria
        # 'atualizado as 08:12' de segunda.
        dados["quando"] = datetime.datetime.combine(
            dia, datetime.time(23, 59))

        caminho = caminho_do_fechamento(cliente, dia, criar=True)
        if not caminho:
            log("Nao achei a pasta do dia %s da %s para guardar o "
                "relatorio" % (dia.strftime("%d/%m"), cliente), alerta=True)
            return None

        escrito = guardar(dados, caminho)
        if escrito:
            log("Fechei o dia %s da %s: %s"
                % (dia.strftime("%d/%m"), cliente,
                   os.path.basename(escrito)), alerta=True)
        return escrito
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def dias_por_fechar(cliente, hoje=None, quantos=None):
    """
    Os dias passados que ainda nao tem relatorio de fechamento.

    O programa nao e servico: roda enquanto a janela esta aberta. Com a
    maquina desligada a meia-noite ninguem fecha o dia, e o operador
    chega cedo e nao acha o relatorio. Entao, ao subir, a FIA olha para
    tras.

    HOJE NAO ENTRA. O dia so fecha quando acaba.
    """
    hoje = hoje or agora_util().date()
    quantos = quantos or DIAS_PARA_FECHAR_ATRASADO
    comeco = _primeiro_dia()
    atrasados = []
    for n in range(1, quantos + 1):
        dia = hoje - datetime.timedelta(days=n)
        if comeco and dia < comeco:
            continue                       # antes de a rotina existir
        if not ja_fechado(cliente, dia):
            atrasados.append(dia)
    return list(reversed(atrasados))       # do mais velho para o mais novo


def _primeiro_dia():
    """A data em que a rotina passou a valer, ou None se nao ha limite."""
    if not FECHAMENTO_A_PARTIR_DE:
        return None
    try:
        return datetime.datetime.strptime(FECHAMENTO_A_PARTIR_DE,
                                          "%Y-%m-%d").date()
    except ValueError:
        return None


def _dia_pedido(texto, hoje=None):
    """
    '11/09' ou '11/09/2026' -> date. Levanta SystemExit se nao der.

    Montado a mao, e nao com strptime de '%d/%m': sem o ano, o Python
    3.15 passa a recusar essa forma - e ela ja avisa, hoje, que e
    ambigua e quebra em 29 de fevereiro.
    """
    hoje = hoje or agora_util().date()
    pedacos = (texto or "").replace("-", "/").split("/")
    try:
        dia = int(pedacos[0])
        mes = int(pedacos[1])
        ano = int(pedacos[2]) if len(pedacos) > 2 else hoje.year
        return datetime.date(ano, mes, dia)
    except (IndexError, ValueError):
        raise SystemExit("nao entendi a data %r. Use 11/09 ou 11/09/2026"
                         % texto)


def main():
    palavras = [a for a in sys.argv[1:] if not a.startswith("-")]
    cliente = CLIENTE_PADRAO
    if palavras and palavras[0].upper() in GEREMPRE_CLIENTES:
        cliente = palavras.pop(0).upper()
    if cliente not in GEREMPRE_CLIENTES:
        raise SystemExit("nao conheco o cliente %r. Conheco: %s"
                         % (cliente, ", ".join(sorted(GEREMPRE_CLIENTES))))

    # --fechar [dia]: o relatorio de FECHAMENTO, na pasta daquele dia.
    # Sem data, fecha o que estiver por fechar.
    if "--fechar" in sys.argv:
        dias = ([_dia_pedido(palavras[0])] if palavras
                else dias_por_fechar(cliente))
        if not dias:
            print("nao ha dia por fechar na %s" % cliente)
            return
        for dia in dias:
            caminho = fechar_o_dia(cliente, dia)
            print("%s -> %s" % (dia.strftime("%d/%m/%Y"),
                                caminho or "nada a guardar"))
        return

    dados = levantar(cliente)
    if not dados:
        raise SystemExit("nao consegui levantar o estoque da %s" % cliente)

    print("ESTOQUE DA %s em %s" % (cliente, dados["dia"].strftime("%d/%m/%Y")))
    for chapa in dados["chapas"]:
        print("   %-26s %6.0f chapas   sai ~%.0f/dia   %s"
              % (chapa["nome"], chapa["saldo"], chapa["media"],
                 _folga_em_texto(chapa)))

    caminho = gravar(dados)
    print()
    print("folha da casa: %s" % caminho)

    # --agora: o relatorio ATUAL, na pasta do cliente, a pedido
    if "--agora" in sys.argv:
        pedido = relatorio_agora(cliente)
        print("para o cliente: %s" % (pedido or "nao consegui guardar"))
        caminho = pedido or caminho

    if "--nao-abrir" not in sys.argv:
        abrir(caminho)


if __name__ == "__main__":
    main()
