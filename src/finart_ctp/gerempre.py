# -*- coding: utf-8 -*-
r"""
A OS no GEREMPRE: abrir ordem de servico para a gravacao das chapas.

O GEREMPRE e o programa da empresa, em Firebird 1.5. Nada aqui toca o
banco de producao enquanto GEREMPRE_DSN apontar para a copia de teste -
e e assim que ele vem de fabrica.

COMO UMA OS E MONTADA. Ela tem CABECALHO e ate QUATRO VAGAS de servico.
Foi lido da OS 19140, aberta a mao por um operador:

    cabecalho   OSCOD (do gerador GEN_OSCOD_ID)   OSCLI + OSNCLI
                OSENTD, OSTIME, OSENTG            OSECL = estoque de quem
    vaga <n>    OSTIT<n>    49348 - BASE_CALL. 2027 - LUS CONTABILIDADE
                OSESP<n>    98        OSNESP<n>  SOLIDA FT4
                OSMON<n>    F4        OSALT/OSLAR  510 / 400
                OSLAN<n>    4         quantas CHAPAS, nao quantos arquivos
                OSUNIT<n>   9,00      OSVLU<n>   36,00
                RBCHAPA<n>  1

CUIDADO - ESCREVER AQUI MEXE EM ESTOQUE. O gatilho TR_OS_BEFO da tabela
OS nao e decoracao: quando RBCHAPA<n>=1 ele LANCA MOVIMENTO na tabela
MOV, dando baixa de chapa. Ou seja, abrir OS nao e anotar: e movimentar o
que a empresa tem e o que ela fatura.

    RBCHAPA<n>    = 1  ->  baixa no estoque DO CLIENTE  (ele traz a chapa)
    RBCHAPAPRO<n> = 1  ->  baixa no estoque DA FINART   (chapa propria)

QUANTAS CHAPAS. O preco e por chapa de metal, e um trabalho em
quadricromia gasta quatro. Entao OSLAN = paginas x tintas, que e
exatamente o que a FIA ja mede em cada arte.
"""

import datetime
import io
import json
import os
import re

from .config import (MAIOR_LADO_F4,
                     GEREMPRE_CHAPAS, GEREMPRE_CLIENTES, GEREMPRE_DSN,
                     GEREMPRE_JANELA_DIAS,
                     GEREMPRE_FUNCIONARIO, GEREMPRE_RESPONSAVEL,
                     GEREMPRE_SENHA, GEREMPRE_USUARIO, PASTA_CONTROLE)
from .utils import anotar_pendencia, log

VAGAS = 4                      # a OS tem quatro lugares de servico

# A SITUACAO DA OS, no campo OSSIT.
#
# Lido do banco de producao em 10/09/2026: 19.535 OS em 1 e 42 em 0 - e
# as 42 eram exatamente as dos ultimos dez dias, ainda abertas. Ou seja,
# 1 nao e "o valor normal": e "ja foi entregue". Quase toda OS acaba em
# 1 porque quase todo servico acaba entregue.
#
# O codigo daqui nascia gravando 1 na primeira vaga, por ter olhado a
# maioria sem olhar o tempo. A OS 19603, aberta pela FIA em 09/09/2026,
# saiu ENTREGUE com TRES vagas por causa disso.
#
# CANCELADA fica aqui por completude e para ninguem grava-la por
# engano: com OSSIT = 2 o TR_OS_BEFO toma o caminho que DEVOLVE chapa ao
# estoque. Nada nesta casa escreve esse valor.
PENDENTE = 0
ENTREGUE = 1
CANCELADA = 2                  # o gatilho devolve estoque. Nao escreva.

# Quanto cabe no titulo da vaga. E o tamanho da coluna OSTIT<n> no
# banco, e o Firebird nao corta sozinho: passar disso derruba a
# gravacao inteira com erro de truncamento.
#
# Quem corta e titulo_da_vaga, e ele NAO corta no fim: o fim e o que
# distingue dois servicos da mesma peca. Ver o comentario la.
LETRAS_NO_TITULO = 50
CLIENTE = "cliente"            # a chapa e do cliente
PROPRIA = "propria"            # a chapa e da Finart


class SemLigacao(Exception):
    """Nao deu para falar com o GEREMPRE."""


# ----------------------------------------------------------------------
# O NOME DO SERVIDOR CUSTA 84 SEGUNDOS; O IP CUSTA 6 MILESIMOS
# ----------------------------------------------------------------------
# Medido na maquina da Finart em 14/09/2026, repetidas vezes:
#
#     resolver 'ARTE-JUNIOR' no Windows .....   0,017 s
#     TCP puro ate 192.168.15.27:3050 .......   0,001 s
#     fdb.connect pelo NOME .................  84,203 s
#     fdb.connect pelo IP ...................   0,006 s
#
# Nao e o DNS: o nome resolve em milesimos, e a porta atende na hora. E
# o cliente Firebird tentando outro caminho antes de cair no TCP, e
# esperando ele esgotar. O preco era pago em TODA ligacao - e a FIA liga
# varias vezes por servico. No log do dia, 86 e 87 segundos entre a
# chapa ficar pronta e a OS sair; quase tudo era isto.
#
# Escrever o IP no config_local.py mataria o problema e criaria outro:
# no dia em que o servidor trocar de numero, a FIA para e ninguem sabe
# por que. Entao o NOME continua sendo o que esta na configuracao - que
# e o que uma pessoa entende - e a troca acontece aqui, na hora de
# ligar. Falhando pelo IP, o nome ainda e tentado: custa os 84
# segundos, mas funciona.

def _dsn_pelo_ip(dsn):
    """
    O mesmo DSN com o nome do servidor trocado pelo IP dele.

    Devolve o DSN intacto quando nao ha nome a trocar: caminho local,
    servidor ja escrito em numero, ou nome que nao resolve.
    """
    import socket

    achou = re.match(r"^([^/:\\]+)(/\d+)?:(.+)$", dsn)
    if not achou:
        return dsn
    servidor = achou.group(1)
    if len(servidor) == 1:
        return dsn                       # 'C:' e unidade, nao servidor
    if re.match(r"^[\d.]+$", servidor):
        return dsn                       # ja e numero
    try:
        ip = socket.gethostbyname(servidor)
    except OSError:
        return dsn                       # sem nome nao ha atalho
    return "%s%s:%s" % (ip, achou.group(2) or "", achou.group(3))


def conectar():
    """
    Abre a ligacao com o banco. Levanta SemLigacao se nao der.

    Quem chama fecha. Nunca deixamos conexao pendurada: o Firebird 1.5
    do GEREMPRE e o mesmo que os operadores usam o dia inteiro.
    """
    if not GEREMPRE_DSN:
        raise SemLigacao("GEREMPRE_DSN nao esta configurado")
    try:
        import fdb
    except ImportError:
        raise SemLigacao("falta a biblioteca fdb (pip install fdb)")

    from .config import GEREMPRE_CLIENTE_DLL
    try:
        if GEREMPRE_CLIENTE_DLL:
            fdb.load_api(GEREMPRE_CLIENTE_DLL)
    except Exception as e:
        raise SemLigacao(str(e)[:120])

    # SO UM CAMINHO, e isso mudou em 18/09/2026.
    #
    # Antes, falhando pelo IP, tentava-se pelo NOME. Parecia prudencia e
    # era desperdicio: o IP vem de resolver esse mesmo nome. Se o TCP
    # para ele falhou, o nome resolve para o MESMO IPv4 - mais dois IPv6
    # mortos - e leva 84 segundos para chegar ao mesmo erro.
    #
    # Medido nesta maquina:
    #
    #     pelo IP      0,184 s
    #     pelo NOME   63,341 s   (ate 84 s)
    #
    #     fe80::83bb:112b:788f:3ca7               8,0 s  tempo esgotado
    #     2804:3d90:71:3c90:6cad:493a:7acf:130f   8,0 s  tempo esgotado
    #     192.168.15.150                          0,001 s  conectou
    #
    # O mDNS entrega os IPv6 primeiro, e o cliente Firebird os tenta em
    # ordem. A espera nao ajudava ninguem: 324 vezes no log, e nenhuma
    # delas o nome salvou uma ligacao que o IP tinha perdido.
    #
    # O nome so e tentado quando a RESOLUCAO falhou - ai ele e o unico
    # caminho que existe, e vale esperar.
    pelo_ip = _dsn_pelo_ip(GEREMPRE_DSN)
    dsn = pelo_ip if pelo_ip != GEREMPRE_DSN else GEREMPRE_DSN

    try:
        ligacao = fdb.connect(dsn=dsn, user=GEREMPRE_USUARIO,
                              password=GEREMPRE_SENHA, charset="ISO8859_1")
    except Exception as e:
        _avisar_da_queda(dsn, e)
        raise SemLigacao(str(e)[:120])
    _avisar_da_volta()
    return ligacao


# O estado da ligacao, para o log falar UMA vez por queda.
#
# A mensagem antiga saiu 324 vezes em dois dias, sempre igual, uma por
# tentativa. Aviso repetido vira aviso que ninguem le - e o operador
# passou a ver o log como ruido em vez de como noticia. Agora ele diz
# quando CAIU e quando VOLTOU, com quanto tempo passou no meio.
_queda = {"desde": None, "quantas": 0}


def _avisar_da_queda(dsn, erro):
    import time
    _queda["quantas"] += 1
    if _queda["desde"] is None:
        _queda["desde"] = time.time()
        log("o GEREMPRE nao esta atendendo em %s (%s). Sigo tentando a "
            "cada volta; aviso quando voltar."
            % (dsn.split(":")[0], str(erro)[:70]), alerta=True)


def _avisar_da_volta():
    import time
    if _queda["desde"] is None:
        return
    fora = time.time() - _queda["desde"]
    log("o GEREMPRE voltou. Ficou %s fora, em %d tentativa(s)."
        % ("%.0f s" % fora if fora < 90 else "%.0f min" % (fora / 60.0),
           _queda["quantas"]), alerta=True)
    _queda["desde"] = None
    _queda["quantas"] = 0


def chapa_do_servico(cliente, larg_mm, alt_mm):
    """
    (codigo_da_chapa, nome, preco, tipo) para este cliente e formato.

    None quando nao ha combinacao cadastrada - e ai o servico vira
    pendencia em vez de OS com preco chutado.
    """
    medida = tuple(sorted((int(round(larg_mm)), int(round(alt_mm))),
                          reverse=True))
    return GEREMPRE_CHAPAS.get((cliente, medida))


def quantas_chapas(paginas_com_tintas):
    """
    Quantas chapas de METAL o trabalho gasta.

    O preco e por chapa, e quadricromia gasta quatro. Recebe uma lista
    com o conjunto de tintas de cada pagina:

        [{'C','M','Y','K'}]            -> 4
        [{'GRAY'}]                     -> 1
        [{'C','M','Y','K'}, {'GRAY'}]  -> 5
    """
    return sum(max(1, len(tintas)) for tintas in paginas_com_tintas)


# ----------------------------------------------------------------------
# PREPARAR O SQL E O QUE CUSTA CARO - NAO A REDE
# ----------------------------------------------------------------------
# Medido contra a producao em 14/09/2026, com o mesmo SELECT:
#
#     preparado a CADA vez (o que se fazia)   19 a 80 ms
#     preparado UMA vez e reexecutado          0,50 ms
#
# Quarenta a cento e sessenta vezes. E nao e rede: a ida e volta de TCP
# e de 0,39 ms ao SERVIDOR e 1,61 ms a ARTE-JUNIOR, e as duas maquinas
# custam os MESMOS 19 ms por consulta nova. Fosse rede, a mais perto
# seria quatro vezes melhor. O tempo esta no servidor, montando o plano
# da consulta - e ele se paga uma vez so, se a consulta for guardada.
#
# O 'cur.execute(sql)' do fdb prepara toda vez. O 'cur.prep(sql)'
# prepara uma e devolve a consulta pronta, que se reexecuta a vontade -
# desde que o cursor seja FECHADO entre uma execucao e outra, senao vem
# '-502 Attempt to reopen an open cursor'.
#
# As consultas prontas ficam guardadas NO PROPRIO CURSOR: elas nascem
# dele e morrem com ele, entao nao ha o que limpar nem risco de usar a
# de uma conexao noutra.

def _preparadas(cur):
    """O caderninho de consultas prontas deste cursor."""
    guardadas = getattr(cur, "_prontas_da_fia", None)
    if guardadas is None:
        guardadas = {}
        try:
            cur._prontas_da_fia = guardadas
        except AttributeError:
            return None                   # cursor que nao deixa guardar
    return guardadas


def perguntar(cur, sql, parametros=None):
    """
    Executa a consulta, reaproveitando a versao ja preparada.

    Serve para qualquer cursor: o de mentira dos testes nao tem 'prep',
    e ai a consulta segue crua, como sempre foi. Nenhum teste precisa
    saber que isto existe.
    """
    if hasattr(cur, "prep"):
        guardadas = _preparadas(cur)
        if guardadas is not None:
            pronta = guardadas.get(sql)
            if pronta is None:
                try:
                    pronta = cur.prep(sql)
                    guardadas[sql] = pronta
                except Exception:
                    pronta = sql          # nao deu para preparar: vai crua
            # fechar antes: reexecutar sem fechar da -502
            try:
                cur.close()
            except Exception:
                pass
            sql = pronta

    if parametros is None:
        return cur.execute(sql)
    return cur.execute(sql, parametros)


def _cadastro_do_cliente(cur, codigo):
    """Nome e contato do cliente, como o GEREMPRE os copia para a OS."""
    perguntar(cur, "SELECT CLINOM, CLICON, CLITEL FROM CLI WHERE CLICOD = ?",
                (codigo,))
    linha = cur.fetchone()
    if not linha:
        return None, None, None
    return tuple((c or "").strip() if isinstance(c, str) else c
                 for c in linha)


def _so_letras_e_numeros(texto):
    """'49713 - Lucas Calil' -> '49713LUCASCALIL'. Para comparar titulo."""
    return "".join(c for c in (texto or "").upper() if c.isalnum())


# ----------------------------------------------------------------------
# O TITULO QUE NAO CABE NA OS
# ----------------------------------------------------------------------
# OSTIT guarda 50 letras. Cortar o nome no comeco - que era o que se
# fazia - apaga justamente o fim, e o fim e onde mora o cliente do
# servico. Dois trabalhos da mesma peca ficam com o MESMO titulo no
# GEREMPRE, e ai duas coisas quebram de uma vez:
#
#   - quem le a OS nao distingue um do outro;
#   - a FIA, procurando se o servico ja foi lancado, casa com o do
#     outro e NAO COBRA. Aconteceu em 14/09/2026, na VOPRIX:
#
#       Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Nelore_Bemach
#       Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Colegio_Voolivre
#
#     As 50 primeiras letras sao iguais. A FIA lancou o Voolivre as
#     19:20 e, as 19:23, achou que o Nelore ja estava lancado. A
#     gravacao do Nelore saiu SEM COBRANCA, e o operador teve de
#     arrumar as duas OS a mao.
#
# Regra do operador, naquela noite: "tem que ler o nome completo do
# arquivo, para saber se realmente e o mesmo... a melhor opcao e pegar
# quando os nomes forem iguais, pegar os ultimos nomes".
#
# Entao o nome que nao cabe vai PARTIDO: o comeco, '..', e as ultimas
# palavras.
#
#   ENVELOPE_SACO_23X31,5_4_0_RAPHAEL..NELORE_BEMACH
#   ENVELOPE_SACO_23X31,5_4_0..COLEGIO_VOOLIVRE
#
# SEMPRE que o nome passa de 50 letras, e nao so quando ha colisao a
# vista. Fazer depender do que ja esta na OS daria titulos diferentes
# para o MESMO servico conforme a hora do dia - e ai a FIA nao
# reconheceria mais o que ela propria lancou, e cobraria duas vezes.
# Um titulo tem de ser funcao do nome, e de mais nada.
PARTIDO = ".."                 # o sinal de que o meio ficou de fora
PALAVRAS_DO_FIM = 2            # quantas palavras do fim sempre entram
LETRAS_DO_FIM = 24             # e ate onde elas podem ir

# A MARCA DA REGRAVACAO, no fim do titulo.
#
# Regra do operador, 14/09/2026: "o cliente pediu uma regravacao de
# algum arquivo... nesse caso pode dar andamento, e colocar no nome da
# OS, depois do nome do arquivo, ARQUIVO NOVO, pra gente saber que foi
# uma regravacao".
#
# Ela e o que separa uma segunda cobranca DELIBERADA de uma cobranca em
# dobro. Numa regravacao a arte e a MESMA de proposito - o
# 'AGENDA_2027_ CREDIBRASILIA' de 14/09 e byte a byte igual ao de 08/09,
# mesmo SHA-256 - entao pela chapa ninguem distingue as duas OS. Pelo
# titulo, distingue.
#
# Mora AQUI, e nao na fila que a usa, porque quem corta o titulo e que
# precisa reservar espaco para ela. Cortada depois, ela sumiria
# exatamente nos nomes longos.
MARCA_REGRAVACAO = "ARQUIVO NOVO"

# Onde uma palavra acaba e outra comeca, nestes nomes de arquivo.
_QUEBRA = re.compile(r"[_\s-]+")


def _comecos_de_palavra(nome):
    """As posicoes em que uma palavra comeca, da esquerda para a direita."""
    return [m.end() for m in _QUEBRA.finditer(nome)]


def _o_fim_do_nome(nome):
    """As ultimas palavras do nome, dentro de LETRAS_DO_FIM letras."""
    comecos = _comecos_de_palavra(nome)
    for inicio in comecos[-PALAVRAS_DO_FIM:]:
        if len(nome) - inicio <= LETRAS_DO_FIM:
            return nome[inicio:]
    # nenhuma palavra inteira cabe: leva as ultimas letras e pronto
    return nome[-LETRAS_DO_FIM:]


def _o_comeco_do_nome(nome, cabe):
    """O comeco do nome em ate 'cabe' letras, sem partir palavra."""
    if cabe <= 0:
        return ""
    inteiras = [p for p in _comecos_de_palavra(nome) if p <= cabe + 1]
    if inteiras:
        return nome[:inteiras[-1]].rstrip("_ -")
    return nome[:cabe].rstrip("_ -")


def titulo_da_vaga(nome):
    """
    O que vai em OSTIT: no maximo LETRAS_NO_TITULO letras.

    Nome que cabe vai inteiro, como sempre foi. Nome que nao cabe vai
    PARTIDO - comeco, '..' e as ultimas palavras -, porque e no fim que
    mora o que separa dois servicos parecidos.

    A MARCA_REGRAVACAO, quando o nome termina nela, e reservada ANTES da
    conta das letras e volta no fim, intacta. Cortada junto, ela sumiria
    exatamente nos nomes longos - um defeito num arquivo a cada tantos,
    que e o pior jeito de um defeito aparecer.
    """
    nome = (nome or "").strip()

    marca = ""
    if nome.upper().endswith(" " + MARCA_REGRAVACAO):
        marca = MARCA_REGRAVACAO
        nome = nome[:-(len(MARCA_REGRAVACAO) + 1)].rstrip()

    sobra = LETRAS_NO_TITULO - (len(marca) + 1 if marca else 0)

    if len(nome) > sobra:
        fim = _o_fim_do_nome(nome)
        comeco = _o_comeco_do_nome(nome, sobra - len(PARTIDO) - len(fim))
        nome = (comeco + PARTIDO + fim) if comeco else fim
        nome = nome[:sobra]

    return "%s %s" % (nome, marca) if marca else nome


def _foi_cortado(gravado):
    """
    Este titulo do banco pode estar faltando o fim?

    So quem chegou ao limite da coluna. Um titulo mais curto que isso
    esta inteiro, e comparar com ele e comparar nome com nome.
    """
    return len((gravado or "").strip()) >= LETRAS_NO_TITULO - 1


def _o_numero_da_os_identifica(titulo, gravado, cliente):
    """
    O comeco que sobreviveu ao corte ja identifica o servico?

    Identifica quando o cliente poe o numero da OS no NOME do arquivo -
    hoje a SOLIDA ('49715 49716 - Lucas Calil - panfletos') e o EMPORIO
    ('01954 - CHAPA - Caixa Cyclus'). Ali o comeco carrega o numero que
    a casa deu ao servico, e dois trabalhos diferentes nao repetem esse
    numero.

    NAO identifica nos outros. No VOPRIX o nome comeca pela peca e pelo
    formato - 'Envelope_Saco_23x31,5_4_0_...' -, e foi exatamente isso
    que fez dois servicos parecerem um so em 14/09/2026.

    Contado no registro da FIA: dos 295 arquivos ja fechados, 24 passam
    de 50 letras, e 22 deles sao VOPRIX e EMPORIO. Nos dez do EMPORIO o
    numero vem na frente; nos doze do VOPRIX nao ha numero nenhum.
    """
    from .config import CLIENTES_COM_OS_NO_NOME
    from .nomes import extrair_oss

    if cliente not in CLIENTES_COM_OS_NO_NOME:
        return False
    numeros = extrair_oss(titulo)
    return bool(numeros) and all(n in (gravado or "") for n in numeros)


def ja_esta_em_os(cur, titulo, cliente=None, quando=None, duvidas=None):
    """
    O numero da OS RECENTE em que este servico ja foi lancado, ou None.

    A OS tambem se abre A MAO, e e normal que outro operador tenha
    lancado o servico antes da FIA chegar nele. Faturar duas vezes o
    mesmo servico e pior do que nao faturar.

    Procura nas QUATRO vagas. O titulo no GEREMPRE e o proprio nome do
    arquivo em maiuscula - foi conferido em 330 arquivos de agosto -, mas
    a comparacao ignora espaco, traco e caixa, porque quem digita varia.

    DO MESMO CLIENTE E DOS ULTIMOS DIAS, e as duas coisas custaram caro
    para serem aprendidas. Sem elas, o 'GRADE 40' da VIVA de 09/09/2026
    casou com o 'GRADE 40' da MESMA VIVA de 21/08/2024 - dois anos antes.
    A grafica reaproveita nome de grade o tempo todo, e a busca varria as
    19 mil OS desde sempre. Resultado: a prova saiu com o numero de uma
    OS de 2024 impresso no verso.

    A janela de dias e o que separa 'alguem lancou este servico agora' de
    'a empresa ja usou este nome um dia'.

    SO CASA COM CERTEZA. Ate 14/09/2026 um titulo do banco que batesse
    com as 50 PRIMEIRAS letras do nome valia como prova de que o servico
    ja estava lancado. Nao vale: dois servicos diferentes da mesma peca
    tem as mesmas 50 primeiras letras, e a FIA deixou de cobrar um deles
    (ver o comentario de titulo_da_vaga).

    Agora vale o nome inteiro, ou o titulo PARTIDO que a propria FIA
    grava - os dois carregam o fim do nome. O que casa so pelo comeco,
    contra um titulo que o banco cortou, e DUVIDA: nao devolve numero e,
    havendo lista em 'duvidas', e anotado la com (numero, titulo). Quem
    chamou decide - e a decisao certa e parar e perguntar, porque so
    quem tem o arquivo na mao sabe se e o mesmo servico.
    """
    alvo = _so_letras_e_numeros(titulo)
    if not alvo:
        return None

    # As duas formas que provam identidade, as duas levando o FIM do
    # nome: o nome inteiro (quando ele cabe) e o titulo partido (quando
    # nao cabe). Abaixo do corte as duas sao a mesma string.
    certas = {alvo, _so_letras_e_numeros(titulo_da_vaga(titulo))}

    # E a forma que NAO prova nada: o comeco cru, que e o que o Delphi
    # guarda quando uma pessoa digita um nome comprido na tela.
    comeco_cru = _so_letras_e_numeros(titulo[:LETRAS_NO_TITULO])

    limite = ((quando or datetime.datetime.now()).date()
              - datetime.timedelta(days=GEREMPRE_JANELA_DIAS))
    codigo = GEREMPRE_CLIENTES.get(cliente) if cliente else None

    # UMA CONSULTA, AS QUATRO VAGAS.
    #
    # Eram quatro consultas, uma por vaga, cada uma com um
    # 'UPPER(OSTIT<n>) STARTING WITH ?' na frente. A tabela OS tem UM
    # unico indice, no OSCOD - medido em 15/09/2026 -, entao qualquer
    # outra condicao vira PLAN (OS NATURAL): uma varredura das 19.686
    # linhas, 186 ms. Quatro vagas eram quatro varreduras, 750 ms por
    # servico procurado.
    #
    # Trazendo as quatro vagas de uma vez, e uma varredura so. E o
    # STARTING WITH sai junto, o que alem de mais rapido e mais CERTO:
    # ele distingue maiuscula de minuscula (o '48915 - Heineken' nao
    # achava o '48915 - HEINEKEN', e custou uma busca em branco), e a
    # comparacao que vale sempre foi a de baixo, em Python, que ignora
    # espaco, traco e caixa.
    #
    # O que segura o tamanho da resposta e a JANELA DE DIAS com o
    # cliente: 90 OS, e nao 19 mil.
    sql = "SELECT OSCOD, OSTIT1, OSTIT2, OSTIT3, OSTIT4 FROM OS " \
          "WHERE OSENTD >= ?"
    valores = [limite]
    if codigo:
        sql += " AND OSCLI = ?"
        valores.append(codigo)
    perguntar(cur, sql, valores)

    achados = []
    for linha in cur.fetchall():
        numero = linha[0]
        for gravado in linha[1:]:
            if not gravado:
                continue
            limpo = _so_letras_e_numeros(gravado)
            if limpo in certas:
                achados.append(numero)
            elif (limpo == comeco_cru and _foi_cortado(gravado)
                  and len(titulo) > LETRAS_NO_TITULO):
                # So o comeco bate, e o banco cortou o resto. Vale como
                # prova quando esse comeco ja traz o numero da OS do
                # cliente; nao vale quando ele traz so a peca.
                if _o_numero_da_os_identifica(titulo, gravado, cliente):
                    achados.append(numero)
                elif duvidas is not None:
                    # sem repetir: a mesma OS pode trazer o mesmo titulo
                    # cortado em mais de uma vaga, e dizer a mesma coisa
                    # quatro vezes nao ajuda quem vai ler a pendencia
                    duvida = (numero, (gravado or "").strip())
                    if duvida not in duvidas:
                        duvidas.append(duvida)
    return max(achados) if achados else None


def _proximo_numero(cur):
    """O proximo numero de OS, do mesmo gerador que o GEREMPRE usa."""
    cur.execute("SELECT GEN_ID(GEN_OSCOD_ID, 1) FROM RDB$DATABASE")
    return cur.fetchone()[0]


def montar_vaga(servico):
    """
    Os campos de UMA vaga, a partir de um servico da FIA.

    servico: {'titulo', 'cliente', 'chapa': (larg, alt), 'chapas': n}
    """
    achado = chapa_do_servico(servico["cliente"], *servico["chapa"])
    if not achado:
        return None
    codigo, nome, preco, tipo = achado
    larg, alt = servico["chapa"]
    quantas = servico["chapas"]
    return {
        # PARTIDO quando nao cabe, e nunca cortado no comeco: e no fim
        # do nome que mora o que separa dois servicos parecidos.
        "OSTIT": titulo_da_vaga(servico["titulo"]),
        "OSESP": codigo,
        "OSNESP": nome,
        "OSMON": "F4" if max(larg, alt) <= MAIOR_LADO_F4 else "F2",
        "OSALT": int(round(max(larg, alt))),
        "OSLAR": int(round(min(larg, alt))),
        "OSLAN": quantas,
        "OSCOR": 1,
        "OSUNIT": preco,
        "OSVLU": round(preco * quantas, 2),
        "RBCHAPA": 1 if tipo == CLIENTE else 0,
        "RBCHAPAPRO": 1 if tipo == PROPRIA else 0,
    }


def dados_da_os(numero, con=None):
    """
    Tudo que a folha da ORDEM DE SERVICO precisa, lido do banco.

    Le a OS de volta depois de gravada, em vez de reaproveitar o que foi
    montado na memoria: assim a folha impressa mostra o que EXISTE no
    GEREMPRE. Se um campo nao entrou, aparece em branco no papel, e
    alguem ve.
    """
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT * FROM OS WHERE OSCOD = ?", (numero,))
        linha = cur.fetchone()
        if not linha:
            return None
        d = dict(zip([c[0] for c in cur.description], linha))

        def texto(campo):
            v = d.get(campo)
            return v.strip() if isinstance(v, str) else v

        itens = []
        for i in range(1, VAGAS + 1):
            if not d.get("OSESP%d" % i):
                continue
            itens.append({
                "vaga": i,
                "material": texto("OSNESP%d" % i) or "",
                "codigo": d.get("OSESP%d" % i),
                "alt": d.get("OSALT%d" % i),
                "lar": d.get("OSLAR%d" % i),
                "montagem": texto("OSMON%d" % i) or "",
                "frente": d.get("OSCOR%d" % i) or 0,
                "verso": d.get("OSCOR%d%d" % (i, i)) or 0,
                "quantas": d.get("OSLAN%d" % i) or 0,
                "titulo": texto("OSTIT%d" % i) or "",
                "obs": texto("OSOBS%d" % i) or "",
                "unitario": d.get("OSUNIT%d" % i),
                "total": d.get("OSVLU%d" % i),
            })

        # O ENDERECO VEM DO CADASTRO DO CLIENTE, e nao da OS.
        #
        # A OS tem campos proprios - OSEND_END, OSEND_BAI, OSEND_CID - e
        # eles estao VAZIOS nas 19.577 que existem. Ninguem preenche. O
        # F12 do GEREMPRE puxa da tabela CLI, e foi o papel de verdade da
        # OS 19605 que mostrou: la o endereco sai completo, e a primeira
        # versao da nossa folha saia em branco.
        #
        # A ordem e o feitio sao os do papel deles:
        #   AV B QD 21 LT 04 N 120 - JARDIM SANTO ANTONIO - GOIANIA
        #   - CEP: 74853030 - TEL: (62) 3280-3808
        endereco = " - ".join(p for p in (
            texto("OSEND_END"), texto("OSEND_BAI"), texto("OSEND_CID")) if p)
        if not endereco and d.get("OSCLI"):
            try:
                cur.execute("SELECT CLIEND, CLIBAI, CLICID, CLICEP, CLITEL "
                            "FROM CLI WHERE CLICOD = ?", (d["OSCLI"],))
                c = cur.fetchone()
            except Exception:
                c = None
            if c:
                def limpo(v):
                    return v.strip() if isinstance(v, str) else (v or "")
                partes = [limpo(c[0]), limpo(c[1]), limpo(c[2])]
                if limpo(c[3]):
                    partes.append("CEP: %s" % limpo(c[3]))
                if limpo(c[4]):
                    partes.append("TEL: %s" % limpo(c[4]))
                endereco = " - ".join(p for p in partes if p)
        return {
            "numero": d["OSCOD"],
            "entrada": d.get("OSENTD"),
            "hora": d.get("OSTIME"),
            "entrega": d.get("OSENTG"),
            "cliente": texto("OSNCLI") or "",
            "contato": texto("OSCON") or "",
            "telefone": texto("OSTEL") or "",
            "celular": texto("OSCEL") or "",
            "endereco": endereco,
            "responsavel": texto("OSRESP") or "",
            "total_geral": d.get("OSVTOT"),
            "itens": itens,
        }
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def _vagas_ocupadas(cur, numero):
    """Quais vagas da OS ja tem servico. [1, 2] quer dizer duas cheias."""
    perguntar(cur, "SELECT OSESP1, OSESP2, OSESP3, OSESP4 FROM OS "
                "WHERE OSCOD = ?", (numero,))
    linha = cur.fetchone()
    if not linha:
        return None
    return [i for i, esp in enumerate(linha, start=1) if esp]


def os_com_vaga_livre(cur, cliente, quando=None):
    """
    A OS de hoje deste cliente que ainda tem vaga, ou None.

    Os operadores enchem as quatro vagas, e a FIA faz igual - so que sem
    esperar: entra na primeira arte e vai completando conforme as outras
    fecham. Assim cada arquivo ja sai com o numero da OS impresso no
    verso da prova, que e o que o operador precisa na mao.

    DE QUALQUER OPERADOR, e nao so as dela. Decisao do operador em
    11/09/2026, e ela desfez duas coisas que estavam escritas aqui:

    1. O FILTRO DE DONO SAIU. Havia um 'AND OSUSR_ALT = 32' que queria
       dizer "so as OS que a FIA abriu" - e nao dizia isso. OSUSR_ALT e
       o USUARIO DA ALTERACAO: quando um operador abre uma OS da FIA no
       Delphi e salva, o campo passa a ser dele e a OS some da vista
       dela. Medido em producao em 11/09/2026: das 8 OS pendentes que a
       FIA tinha aberto, 3 ja estavam invisiveis por isso - e para cada
       uma delas ela abriria OUTRA OS do mesmo cliente no mesmo dia, com
       chapa a mais e faturamento dobrado. Ver a armadilha 15.

    2. O MEDO DO NULO NAO TINHA BASE. O motivo escrito aqui dizia que
       numa OS aberta a mao uma vaga vazia "pode estar NULA", e conta
       com nulo da nulo apagaria o saldo da chapa. Fui contar: nos
       campos que o gatilho multiplica, em 19.627 OS, ZERO nulos - o
       Delphi preenche com zero. Era suposicao, e ficou no codigo
       impedindo o aproveitamento das vagas alheias. Ver a armadilha 16.

    O QUE CONTINUA VERDADE, e agora e o unico risco: o Delphi guarda a
    OS inteira na memoria da tela. Quem estiver com ela aberta salva o
    que ESTA VENDO - sem a vaga que a FIA acabou de por - e o
    TR_OS_BEFO refaz os movimentos a partir disso. E nao da para
    detectar antes: sondei 300 OS em producao com FOR UPDATE WITH LOCK e
    nenhuma estava presa, nem a que estava aberta na tela de outra
    maquina. O Delphi nao tranca a linha.

    Por isso completar_os() ANOTA o que escreveu e conferir_completadas()
    rele depois, para ver se sobreviveu. O remedio nao e evitar - e
    perceber.
    """
    codigo = GEREMPRE_CLIENTES.get(cliente)
    if not codigo:
        return None
    hoje = (quando or datetime.datetime.now()).date()
    # SO AS PENDENTES (OSSIT = 0). Uma OS ENTREGUE esta fechada: se
    # aparecesse aqui, um arquivo novo entraria numa OS que ja foi dada
    # por entregue e ja teve protocolo impresso.
    #
    # Isto acompanha o abrir_os, que agora grava PENDENTE. Enquanto
    # procurava OSSIT = 1, a FIA achava a propria OS; se um lado mudar
    # sem o outro, ela deixa de achar e abre UMA OS POR ARQUIVO -
    # faturando quatro vezes o que cabia numa. Ha teste para os dois.
    #
    # OSTIPO 4 e refacao e OSSIT 2 e cancelada: nas duas o gatilho toma
    # o caminho que devolve estoque. Nao se completa uma dessas.
    perguntar(cur, "SELECT OSCOD FROM OS WHERE OSCLI = ? AND OSENTD = ? "
                "AND OSSIT = 0 AND OSTIPO = 0 "
                "AND (OSESP4 = 0 OR OSESP4 IS NULL) "
                "ORDER BY OSCOD DESC",
                (codigo, hoje))
    for (numero,) in cur.fetchall():
        ocupadas = _vagas_ocupadas(cur, numero)
        if ocupadas is not None and len(ocupadas) < VAGAS:
            return numero
    return None


def completar_os(numero, servico, con=None, na_tela=True):
    """
    Poe o servico na proxima vaga livre de uma OS que ja existe.

    Devolve o numero da vaga usada.

    O UPDATE dispara o TR_OS_BEFO, que APAGA todos os movimentos desta
    OS e os refaz a partir das quatro vagas. Por isso completar nao
    cobra o item 1 duas vezes: ele e apagado e recriado igual, e o novo
    item entra junto. Foi lido na fonte do gatilho, nao suposto.
    """
    vaga = montar_vaga(servico)
    if vaga is None:
        raise ValueError("nao sei que chapa usar para %s %.0fx%.0f"
                         % (servico["cliente"], servico["chapa"][0],
                            servico["chapa"][1]))
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        ocupadas = _vagas_ocupadas(cur, numero)
        if ocupadas is None:
            raise ValueError("a OS %s nao existe" % numero)
        livres = [i for i in range(1, VAGAS + 1) if i not in ocupadas]
        if not livres:
            raise ValueError("a OS %s ja tem as quatro vagas cheias"
                             % numero)
        n = livres[0]

        campos = {"%s%d" % (chave, n): valor for chave, valor in vaga.items()}
        # OSCOR<n><n> - as cores do VERSO. Zero, e nunca nulo: o gatilho
        # faz oslan * (oscor + oscor<n><n>), e nulo apaga o saldo.
        campos["OSCOR%d%d" % (n, n)] = 0
        nomes = sorted(campos)
        cur.execute("UPDATE OS SET %s WHERE OSCOD = ?"
                    % ", ".join("%s = ?" % c for c in nomes),
                    [campos[c] for c in nomes] + [numero])
        con.commit()
        # SO NO ARQUIVO QUANDO QUEM CHAMOU JA ANUNCIA.
        #
        # Toda OS aparecia DUAS VEZES na janela - esta linha e a de quem
        # chamou, no mesmo segundo, dizendo a mesma coisa com palavras
        # diferentes. No arquivo as duas ficam, e devem ficar: esta e a
        # que prova que a escrita aconteceu, no instante em que
        # aconteceu, e e ela que se procura quando o estoque nao bate.
        log("GEREMPRE: completei a OS %s na vaga %d com '%s'"
            % (numero, n, servico["titulo"][:40]),
            so_no_arquivo=not na_tela)
        # ANOTA PARA CONFERIR DEPOIS. A OS pode ser de outro operador, e
        # se ele estiver com ela aberta na tela o proximo 'salvar' dele
        # escreve o que ESTA VENDO - sem esta vaga. Nao da para impedir
        # nem para detectar na hora; da para PERCEBER depois.
        _anotar_para_conferir(numero, n, servico)
        return n
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


# ----------------------------------------------------------------------
# A CONFERENCIA DA VAGA QUE A FIA COMPLETOU
# ----------------------------------------------------------------------
# Desde 11/09/2026 a FIA completa a OS de QUALQUER operador que tenha
# vaga aberta para o cliente naquele dia. Isso aproveita chapa e evita
# OS repetida - e traz um risco que nao da para evitar nem detectar na
# hora:
#
#   o Delphi guarda a OS inteira na memoria da tela. Se alguem estiver
#   com ela aberta, o proximo 'salvar' dele grava o que ESTA VENDO - sem
#   a vaga que a FIA acabou de por -, e o TR_OS_BEFO apaga e refaz todos
#   os movimentos a partir disso. A vaga some, o estoque volta junto, e
#   ninguem ve erro nenhum.
#
# Sondei 300 OS em producao com FOR UPDATE WITH LOCK, numa transacao
# NOWAIT, com uma delas aberta na tela de outra maquina: nenhuma estava
# presa. O Delphi NAO tranca a linha, entao 'esta aberta agora?' e uma
# pergunta sem resposta.
#
# O que sobra e PERCEBER DEPOIS: anota-se o que foi escrito e rele-se
# mais tarde. Se a vaga sumiu, vira pendencia com nome e numero - o
# servico ja saiu, e alguem precisa cobra-lo a mao.
REGISTRO_COMPLETADAS = "_os_completadas.json"

# Quanto esperar antes da primeira conferida. Nao ha medida por tras
# deste numero - e um palpite razoavel: tempo de alguem terminar de
# mexer numa OS e salvar. Se aparecer caso de gente salvando muito
# depois, ele sobe.
ESPERA_CONFERIR_MIN = 10

# Ate quando insistir. Passado isso, a vaga que sobreviveu e dada por
# assentada e sai da lista - senao ela seria relida para sempre.
VALIDADE_CONFERIR_H = 8


def _caminho_completadas():
    return os.path.join(PASTA_CONTROLE, REGISTRO_COMPLETADAS)


def _ler_completadas():
    try:
        with io.open(_caminho_completadas(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _gravar_completadas(lista):
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    with io.open(_caminho_completadas(), "w", encoding="utf-8") as f:
        f.write(json.dumps(lista, ensure_ascii=False, indent=1))


def _anotar_para_conferir(numero, vaga, servico):
    """Guarda o que acabou de ser escrito, para reler mais tarde."""
    try:
        lista = _ler_completadas()
        lista.append({
            "os": numero,
            "vaga": vaga,
            "titulo": servico["titulo"],
            "cliente": servico.get("cliente"),
            "quando": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        _gravar_completadas(lista)
    except Exception as e:
        # nao derruba a gravacao da OS por causa do caderninho
        log("GEREMPRE: nao consegui anotar a OS %s para conferir (%s)"
            % (numero, str(e)[:60]), alerta=True)


def conferir_completadas(agora=None, con=None):
    """
    Rele as vagas que a FIA completou e avisa as que sumiram.

    Devolve (conferidas, sumidas). Nao escreve no banco - so le.

    Procura pelo TITULO nas quatro vagas, e nao na vaga onde foi posto:
    quem salva por cima pode ter reorganizado a OS, e o servico estar
    vivo em outro lugar. O que importa e ele estar LANCADO em algum
    lugar, nao estar na vaga 2.
    """
    lista = _ler_completadas()
    if not lista:
        return 0, 0

    agora = agora or datetime.datetime.now()
    espera = datetime.timedelta(minutes=ESPERA_CONFERIR_MIN)
    validade = datetime.timedelta(hours=VALIDADE_CONFERIR_H)

    def quando(reg):
        try:
            return datetime.datetime.fromisoformat(reg["quando"])
        except Exception:
            return agora

    devidas = [r for r in lista if agora - quando(r) >= espera]
    if not devidas:
        return 0, 0

    proprio = con is None
    try:
        con = con or conectar()
    except SemLigacao as e:
        log("GEREMPRE: sem ligacao para conferir as vagas (%s)" % str(e)[:60])
        return 0, 0

    ficam, sumidas, conferidas = [], 0, 0
    try:
        cur = con.cursor()
        for reg in lista:
            if agora - quando(reg) < espera:
                ficam.append(reg)
                continue
            conferidas += 1
            try:
                # Aqui a pergunta nao e 'ja foi cobrado?', e sim 'a vaga
                # ainda esta la?'. Um titulo que bate so pelo comeco
                # serve de resposta: alguem pode ter reescrito o fim a
                # mao - foi o que o operador fez em 14/09/2026 -, e isso
                # nao e a vaga ter sumido.
                perto = []
                achou = ja_esta_em_os(cur, reg["titulo"], reg.get("cliente"),
                                      quando(reg), perto) or bool(perto)
            except Exception as e:
                log("GEREMPRE: nao consegui reler a OS %s (%s)"
                    % (reg["os"], str(e)[:60]))
                ficam.append(reg)          # tenta de novo na volta seguinte
                continue

            if achou:
                # sobreviveu. Passada a validade, sai da lista.
                if agora - quando(reg) < validade:
                    ficam.append(reg)
                continue

            sumidas += 1
            log("GEREMPRE: a vaga %s da OS %s SUMIU - '%s'"
                % (reg["vaga"], reg["os"], reg["titulo"][:45]), alerta=True)
            anotar_pendencia(
                reg["titulo"],
                "a FIA lancou este servico na vaga %s da OS %s em %s, e ele "
                "NAO ESTA MAIS LA. A OS era de outro operador; quem estava "
                "com ela aberta na tela salvou por cima, e o gatilho refez "
                "os movimentos sem esta vaga. O servico ja saiu: ele precisa "
                "ser lancado A MAO, ou a gravacao fica sem cobranca."
                % (reg["vaga"], reg["os"], reg["quando"]),
                reg.get("cliente"))
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass

    _gravar_completadas(ficam)
    return conferidas, sumidas


def entregar_os(numero, con=None):
    """
    Marca a OS como ENTREGUE. So com as QUATRO vagas cheias.

    Regra do operador, dita em 10/09/2026: a FIA so fecha OS completa.
    Faltando vaga, a OS fica pendente e uma pessoa a fecha a mao quando
    houver necessidade - alguem que sabe se aquele servico saiu mesmo.

    Os dois erros nao custam igual, e por isso o programa erra sempre
    para o mesmo lado: deixar pendente o que ja saiu custa uma conferida
    de quem fecha o dia; dar por entregue o que nao saiu poe no
    faturamento um servico que ninguem entregou, e isso so aparece
    quando o cliente reclama.

    CONFERE AS VAGAS AQUI DENTRO, e nao confia em quem chamou. E a unica
    porta para o valor ENTREGUE; se a conferencia morasse no chamador,
    bastaria uma chamada nova em outro lugar para a trava sumir.

    NAO ENCOSTA em OSTIPO. Com OSTIPO 4 - refacao - o TR_OS_BEFO toma o
    caminho que DEVOLVE as chapas ao estoque; passar perto disso aqui
    apagaria a baixa das quatro.

    E um UPDATE, entao o gatilho apaga e refaz os movimentos desta OS a
    partir das quatro vagas. As quantidades nao mudam - o estoque fica
    igual, so as linhas da MOV sao reescritas com codigo novo. Foi lido
    na fonte do gatilho, e conferido no razao: 96 de 96 chapas batendo
    em 10/09/2026.
    """
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        ocupadas = _vagas_ocupadas(cur, numero)
        if ocupadas is None:
            raise ValueError("a OS %s nao existe" % numero)
        if len(ocupadas) < VAGAS:
            raise ValueError(
                "a OS %s tem %d de %d vagas cheias. Nao dou por entregue "
                "pela metade - fica pendente para alguem fechar a mao"
                % (numero, len(ocupadas), VAGAS))

        cur.execute("UPDATE OS SET OSSIT = ? WHERE OSCOD = ?",
                    (ENTREGUE, numero))
        con.commit()
        log("GEREMPRE: OS %s ENTREGUE - as quatro vagas fecharam" % numero)
        return True
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


JA_ESTAVA = "ja_estava"        # nao escrevi nada: o servico ja fora lancado
COMPLETEI = "completei"        # entrou numa vaga de uma OS da FIA
ABRI = "abri"                  # OS nova


def os_do_servico(servico, con=None, quando=None):
    """
    A OS deste servico. Devolve (numero, vaga, o_que_fiz).

    Tres caminhos, nesta ordem:

      1. JA_ESTAVA - o servico ja esta numa OS. Outro operador lancou a
         mao, ou a propria FIA lancou antes e o arquivo voltou. Devolve
         aquele numero e NAO ESCREVE NADA: o estoque nao anda de novo, e
         a prova sai com o numero certo no verso. Faturar duas vezes e
         pior que nao faturar;
      2. COMPLETEI - ha uma OS de hoje, deste cliente, aberta pela FIA e
         com vaga: o servico entra nela;
      3. ABRI - nao ha nenhuma: abre uma nova, na primeira vaga.

    'o_que_fiz' existe porque os tres se parecem de fora e sao coisas
    muito diferentes por dentro. Sem ele o aviso na tela dizia 'vaga 3'
    para um servico que ja estava lancado e no qual nada foi escrito.
    """
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        duvidas = []
        numero = ja_esta_em_os(cur, servico["titulo"], servico["cliente"],
                               quando, duvidas)
        if numero:
            ocupadas = _vagas_ocupadas(cur, numero) or []
            return numero, (ocupadas[-1] if ocupadas else 1), JA_ESTAVA

        # DUVIDA, e duvida aqui e dinheiro. Ha na OS um titulo que o
        # banco cortou e cujo comeco e igual ao deste nome: pode ser
        # este mesmo servico, lancado a mao por alguem, e ai cobrar de
        # novo e cobrar duas vezes; pode ser OUTRO servico da mesma peca,
        # e ai nao cobrar e dar a gravacao de graca.
        #
        # As 50 letras que o banco guarda nao dizem qual dos dois e, e
        # nao ha de onde tirar o resto: quem digitou nao deixou o nome
        # inteiro em lugar nenhum. Entao para, e quem tem o arquivo na
        # mao resolve em dez segundos.
        if duvidas:
            achado, gravado = duvidas[0]
            raise ValueError(
                "na OS %s ha '%s', que so cabe ate a %da letra e comeca "
                "igual a este nome. Nao da para saber daqui se e o MESMO "
                "servico ou outro da mesma peca - nao cobrei nada. Confira "
                "e lance a mao"
                % (achado, gravado, LETRAS_NO_TITULO))

        numero = os_com_vaga_livre(cur, servico["cliente"], quando)
        if numero:
            return (numero,
                    completar_os(numero, servico, con=con,
                                 na_tela=False),
                    COMPLETEI)

        # na_tela=False: quem chamou o os_do_servico anuncia, e com
        # mais contexto (quantas chapas). O fila.despachar, que chama
        # o abrir_os por fora daqui, continua anunciando.
        numero = abrir_os([servico], quando=quando, con=con,
                          na_tela=False)
        return numero, 1, ABRI
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def abrir_os(servicos, quando=None, con=None, na_tela=True):
    """
    Abre UMA OS com ate quatro servicos. Devolve o numero da OS.

    Todos os servicos tem de ser do mesmo cliente - a OS e por cliente.
    Grava tudo numa transacao so: ou entra a OS inteira, ou nao entra
    nada. Meia OS lancaria estoque pela metade.
    """
    if not servicos:
        raise ValueError("nenhum servico para lancar")
    if len(servicos) > VAGAS:
        raise ValueError("a OS tem %d vagas, vieram %d servicos"
                         % (VAGAS, len(servicos)))
    clientes = {s["cliente"] for s in servicos}
    if len(clientes) > 1:
        raise ValueError("uma OS e de um cliente so, vieram: %s"
                         % ", ".join(sorted(clientes)))

    cliente = servicos[0]["cliente"]
    codigo = GEREMPRE_CLIENTES.get(cliente)
    if not codigo:
        raise ValueError("cliente %s nao esta ligado a nenhum codigo do "
                         "GEREMPRE" % cliente)

    vagas = []
    for servico in servicos:
        vaga = montar_vaga(servico)
        if vaga is None:
            raise ValueError("nao sei que chapa usar para %s %.0fx%.0f"
                             % (cliente, servico["chapa"][0],
                                servico["chapa"][1]))
        vagas.append(vaga)

    quando = quando or datetime.datetime.now()
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        numero = _proximo_numero(cur)
        nome, contato, telefone = _cadastro_do_cliente(cur, codigo)

        campos = {
            "OSCOD": numero,
            "OSENTD": quando.date(),
            "OSTIME": quando.time().replace(microsecond=0),
            "OSENTG": quando.date(),
            "OSCLI": codigo,
            "OSNCLI": nome,
            "OSCON": contato,
            "OSTEL": telefone,
            # de que estoque sai a chapa do cliente
            "OSECL": codigo,
            "OSNECLI": nome,
            # O banco exige sete campos: OSCOD, OSSIT, OSTIPO, OSCLI,
            # OSCVEN, OSCOPER e OSCCONF. Os tres ultimos sao vendedor,
            # operador e conferente, e nas 19.122 OS que existem eles
            # estao em ZERO - ninguem preenche. Deixar de fora derruba a
            # gravacao inteira com 'validation error'.
            # PENDENTE, e nao ENTREGUE. A OS nasce aberta e so fecha
            # quando as quatro vagas estiverem cheias - ver entregar_os.
            "OSSIT": PENDENTE,
            "OSTIPO": 0,
            "OSCVEN": 0,
            "OSCOPER": 0,
            "OSCCONF": 0,
            "OSORD": 1,
            "OSRESP": GEREMPRE_RESPONSAVEL,
            # quem abriu: o codigo vai no movimento de estoque pelo
            # gatilho (MOVFUN), e o nome fica visivel na propria OS
            "OSUSR_ALT": GEREMPRE_FUNCIONARIO,
        }
        # ZERO EM TODAS AS QUATRO VAGAS, ANTES DE PREENCHER. Em SQL,
        # qualquer conta com nulo da nulo, e o gatilho faz duas contas
        # que passam por aqui. As duas foram vistas quebrando no banco de
        # teste, e as duas estragam em silencio:
        #
        #   total = osvlu1 + osvlu2 + osvlu3 + osvlu4
        #       numa OS de um servico so, as tres vagas vazias eram nulas
        #       e o TOTAL DA OS saia nulo.
        #
        #   movqtd = oslan<n> * (oscor<n> + oscor<n><n>)
        #       oscor<n><n> e o numero de cores do VERSO. Sem preencher,
        #       a quantidade do movimento saia nula - e o gatilho da MOV
        #       faz 'chaqtd = chaqtd + movqtd', entao o ESTOQUE DA CHAPA
        #       virava nulo. Aconteceu com as chapas 98 e 103 na copia.
        for i in range(1, VAGAS + 1):
            campos["OSVLU%d" % i] = 0
            campos["OSLAN%d" % i] = 0
            campos["OSCOR%d" % i] = 0
            campos["OSCOR%d%d" % (i, i)] = 0      # cores do verso
            campos["OSESP%d" % i] = 0
            campos["RBCHAPA%d" % i] = 0
            campos["RBCHAPAPRO%d" % i] = 0

        for i, vaga in enumerate(vagas, start=1):
            for chave, valor in vaga.items():
                campos["%s%d" % (chave, i)] = valor

        nomes = sorted(campos)
        cur.execute("INSERT INTO OS (%s) VALUES (%s)"
                    % (", ".join(nomes), ", ".join(["?"] * len(nomes))),
                    [campos[n] for n in nomes])
        con.commit()
        # SO NO ARQUIVO QUANDO QUEM CHAMOU JA ANUNCIA.
        #
        # Toda OS aparecia DUAS VEZES na janela - esta linha e a de quem
        # chamou, no mesmo segundo, dizendo a mesma coisa com palavras
        # diferentes. No arquivo as duas ficam, e devem ficar: esta e a
        # que prova que a escrita aconteceu, no instante em que
        # aconteceu, e e ela que se procura quando o estoque nao bate.
        log("GEREMPRE: abri a OS %s para %s com %d servico(s)"
            % (numero, cliente, len(vagas)), so_no_arquivo=not na_tela)
        return numero
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass
