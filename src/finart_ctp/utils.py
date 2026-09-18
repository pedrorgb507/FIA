# -*- coding: utf-8 -*-
"""Apoio: log, pasta do mes/dia, registro do que ja foi feito, pendencias."""

import hashlib
import json
import os
import shutil
import time
import unicodedata
from datetime import datetime, timedelta

from .config import (HORA_VIRADA, MESES, PASTA_CONTROLE, PASTA_PENDENCIAS,
                     REGISTRO, TELA_DE_PENDENCIA)


# ----------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------

def normalizar(texto):
    """'MARÇO', 'Marco', 'marco ' -> 'MARCO'. Para comparar nome de pasta."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().upper()


# ----------------------------------------------------------------------
# Pasta do dia:  BASE\SETEMBRO\02
# ----------------------------------------------------------------------

def agora_util():
    """Data de trabalho: antes da HORA_VIRADA ainda conta como o dia anterior."""
    agora = datetime.now()
    if agora.hour < HORA_VIRADA:
        agora -= timedelta(days=1)
    return agora


def pasta_do_dia():
    """Nome da subpasta do dia, ex: '02'."""
    return "%02d" % agora_util().day


def nome_do_mes():
    """Nome canonico do mes de hoje, ex: 'SETEMBRO'."""
    return MESES[agora_util().month - 1]


def localizar_pasta_mes(base, criar=False):
    """
    Nome REAL da pasta do mes dentro de base, do jeito que esta escrita la
    (SETEMBRO, Maio, MARÇO...). Devolve None se nao existir e criar=False.
    """
    alvo = normalizar(nome_do_mes())
    try:
        for nome in os.listdir(base):
            if os.path.isdir(os.path.join(base, nome)) and normalizar(nome) == alvo:
                return nome
    except OSError:
        pass
    if criar:
        os.makedirs(os.path.join(base, nome_do_mes()), exist_ok=True)
        return nome_do_mes()
    return None


def pasta_da_data(base, data, criar=False):
    r"""
    <base>\<MES>\<DIA> de UMA data qualquer, ou None se nao existir.

    O localizar_pasta_mes so sabe o mes de HOJE, e quem fecha o dia
    anterior precisa da pasta de ONTEM - que na virada do mes esta em
    outra pasta de mes. Aqui a data vem por fora.

    O nome do mes e procurado como ESTA ESCRITO la (SETEMBRO, Maio,
    MARCO), que e o mesmo cuidado do localizar_pasta_mes: a pasta e do
    cliente, e cada um escreve do seu jeito.
    """
    alvo = normalizar(MESES[data.month - 1])
    mes = None
    try:
        for nome in os.listdir(base):
            if (os.path.isdir(os.path.join(base, nome))
                    and normalizar(nome) == alvo):
                mes = nome
                break
    except OSError:
        return None

    if mes is None:
        if not criar:
            return None
        mes = MESES[data.month - 1]

    caminho = os.path.join(base, mes, "%02d" % data.day)
    if os.path.isdir(caminho):
        return caminho
    if not criar:
        return None
    try:
        os.makedirs(caminho, exist_ok=True)
        return caminho
    except OSError:
        return None


# ----------------------------------------------------------------------
# Log
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# A TELA E O ARQUIVO SAO DUAS COISAS, e so em 18/09/2026 passaram a ser.
#
# Pedido do operador: "o terminal do f5 esta uma bagunca, tudo jogado sem
# organizacao nenhuma, esta impossivel de entender".
#
# Ele tinha razao, e a causa era uma so: TUDO SAIA PELO MESMO CANO. Cada
# linha levava a data na frente - repetida quarenta vezes por arquivo -,
# e nada dizia onde um servico acabava e o proximo comecava. Quem olhava
# a janela via um rio de linhas e tinha de montar na cabeca a que arquivo
# cada uma pertencia.
#
# O ARQUIVO NAO PODE MUDAR, e e por isso que aqui ha uma separacao em vez
# de uma reescrita: o _log_ctp.txt e LIDO POR MAQUINA. O relatorio.py
# casa o carimbo de hora no comeco da linha, o "OK em Ns: ... (tintas, N
# MB)", o "impresso em ... (N folha" e o prefixo ">>> PENDENCIA: ".
# Mexer no formato do arquivo quebraria o relatorio do dia CALADO - ele
# nao daria erro, daria numero errado.
#
# Entao: o arquivo continua byte a byte como sempre foi, e a TELA ganha
# um formatador. Duas saidas, uma fonte.
# ----------------------------------------------------------------------

LARGURA_DA_REGUA = 74
REGUA = "-" * LARGURA_DA_REGUA

# O bloco ABERTO agora, ou None em cada campo. Mora no modulo, e nao num
# objeto passado adiante, porque o log e chamado de trinta lugares - e
# empurrar um parametro por todos eles so para desenhar uma regua seria
# pior do que a bagunca que se quer arrumar.
_bloco = {"cliente": None, "arquivo": None, "linhas": 0}


def _escrever(texto=""):
    print(texto, flush=True)


def _quebrar(texto, largura):
    """
    O texto em linhas de ate 'largura', quebrando entre palavras.

    Motivo de pendencia e frase inteira, e algumas passam de duzentos
    caracteres. Sem quebrar, o terminal quebra sozinho no meio da palavra
    e no meio do numero - e e justamente o numero (148,3 dpi, 27 x 27 mm)
    que a pessoa esta procurando ali.
    """
    linhas, atual = [], ""
    for palavra in (texto or "").split():
        if atual and len(atual) + 1 + len(palavra) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = "%s %s" % (atual, palavra) if atual else palavra
    if atual:
        linhas.append(atual)
    return linhas or [""]


def abrir_bloco(cliente, arquivo):
    """
    Comeca na TELA o bloco de um arquivo. NAO ESCREVE NO ARQUIVO DE LOG.

    Havendo bloco aberto, fecha o anterior primeiro: quem esquecer de
    fechar nao deixa dois cabecalhos grudados um no outro.
    """
    fechar_bloco()
    _bloco.update({"cliente": cliente, "arquivo": arquivo, "linhas": 0})
    _escrever()
    _escrever(REGUA)
    if cliente:
        _escrever("CLIENTE - %s" % cliente)
    _escrever("ARQUIVO: %s" % arquivo)
    _escrever(REGUA)


def fechar_bloco(com_regua=True):
    """
    Fecha o bloco da tela, se houver um aberto.

    'com_regua=False' fecha SEM desenhar a linha de baixo. Serve para
    quem vai continuar escrevendo dentro do mesmo quadro - hoje e a
    pendencia, que e o desfecho do bloco e nao um bloco novo.
    """
    if _bloco["arquivo"] is None:
        return
    if com_regua:
        _escrever(REGUA)
    _bloco.update({"cliente": None, "arquivo": None, "linhas": 0})


def bloco_aberto():
    """O nome do arquivo cujo bloco esta aberto na tela, ou None."""
    return _bloco["arquivo"]


def _para_a_tela(msg, alerta, quando):
    """
    A linha como ela aparece na JANELA - que nao e como ela vai para o
    arquivo. Devolve uma LISTA, porque texto longo vira mais de uma.

    DENTRO DE UM BLOCO a data sai e fica so a hora: o cabecalho ja disse
    o arquivo e o cliente, e repetir o dia quarenta vezes e o ruido que
    fazia a janela ser ilegivel. A hora fica porque e por ela que se le
    quanto cada passo demorou.

    O RECUO DE QUEM CHAMOU E PRESERVADO, e isso importa mais do que
    parece. Varias linhas vem com tres ou quatro espacos de proposito -
    sao sub-passos de uma linha acima ("p1: arte montada" e, embaixo,
    "marca de corte a 16,4 mm"). Aparando o recuo, todas ficam no mesmo
    nivel e a hierarquia que o autor escreveu se perde.

    FORA DE BLOCO fica a data inteira. Sao as linhas do arranque e as do
    laco - "esperando a pasta do dia", "Estoque da SOLIDA" -, que
    aparecem soltas no dia todo, e ai a hora sozinha nao situa ninguem.

    O ALERTA VIRA UM SINAL NA MARGEM, no lugar do ">>>" colado no texto.
    O ">>>" continua no arquivo, onde e procurado por codigo; na tela,
    sinal na margem esquerda e o que o olho acha correndo a janela.
    """
    if _bloco["arquivo"] is None:
        return ["%s[%s] %s" % ("! " if alerta else "",
                               quando.strftime("%d/%m %H:%M:%S"), msg)]

    _bloco["linhas"] += 1
    recuo = len(msg) - len(msg.lstrip(" "))
    corpo = msg.strip()
    cabeca = "%s%s  %s" % ("! " if alerta else "  ",
                           quando.strftime("%H:%M:%S"), " " * recuo)
    # a continuacao entra debaixo do TEXTO, e nao da hora: assim o olho
    # corre a coluna da esquerda e ve so onde cada linha comeca de
    # verdade
    dentro = " " * len(cabeca)
    largura = max(24, LARGURA_DA_REGUA - len(cabeca))
    pedacos = _quebrar(corpo, largura)
    return [cabeca + pedacos[0]] + [dentro + p for p in pedacos[1:]]


def log(msg, alerta=False, so_no_arquivo=False):
    """
    Escreve a linha nos dois lugares: na tela e no _log_ctp.txt.

    O TEXTO E O MESMO; a forma, nao. Ver o comentario acima.

    'so_no_arquivo' pula a tela. Serve para a linha que o arquivo precisa
    ter mas a janela ja mostrou de outro jeito - hoje e uma so, a
    'PENDENCIA: ...', que o relatorio.py procura por esse prefixo e que
    na tela ja saiu como bloco, quebrada e legivel. Sem isto, toda
    pendencia aparecia duas vezes seguidas, e a segunda era justamente a
    versao ruim.
    """
    quando = datetime.now()
    linha = "[%s] %s%s" % (quando.strftime("%d/%m %H:%M:%S"),
                           ">>> " if alerta else "", msg)
    if not so_no_arquivo:
        for pedaco in _para_a_tela(msg, alerta, quando):
            _escrever(pedaco)
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_log_ctp.txt"), "a",
                  encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def anotar_pendencia(arquivo, motivo, cliente=None):
    """
    Registra um problema que precisa de gente.

    Fica no PC, junto do log, e NAO na pasta do CTP: la so entram as
    chapas. Alem de gravar, imprime um aviso grande na tela, para nao
    passar batido em quem esta olhando a janela do programa.

    'cliente' e opcional e serve para uma coisa so: saber A QUEM
    responder sem ter de procurar. Passou a importar quando o arquivo
    deixou de ser salvo a mao - antes, quem salvava sabia de quem era
    porque tinha acabado de baixar do Teams. Agora ninguem baixa nada, e
    a pendencia e o unico lugar onde esse nome ainda cabe.
    """
    # NA TELA ELA E UM BLOCO, na mesma linguagem visual do resto - regua
    # em cima e embaixo, cabecalho dizendo de quem e o quê. Antes era uma
    # cerca de 66 exclamacoes, que gritava mais alto que tudo e nao dizia
    # mais: no meio de um dia de trabalho, o que se procura correndo a
    # janela e ONDE comeca cada coisa, e nao qual delas grita.
    #
    # E ela FECHA O BLOCO DO ARQUIVO antes de aparecer. A pendencia e o
    # fim daquele servico - deixar o bloco aberto grudaria o proximo
    # arquivo debaixo deste cabecalho.
    # SENDO DO ARQUIVO QUE ESTA ABERTO, ela e o DESFECHO do bloco, e nao
    # um bloco novo: repetir "ARQUIVO: x" duas linhas abaixo de onde ele
    # ja esta escrito e o tipo de repeticao que fez a janela virar sopa.
    no_mesmo = bloco_aberto() == arquivo
    fechar_bloco(com_regua=not no_mesmo)
    if not no_mesmo:
        _escrever()
    _escrever(REGUA)
    if no_mesmo:
        _escrever("PENDENCIA - PRECISA DE VOCE")
    else:
        _escrever("PENDENCIA NO ARQUIVO: %s" % arquivo)
        if cliente:
            _escrever("CLIENTE - %s" % cliente)
    _escrever(REGUA)
    for pedaco in _quebrar(motivo, LARGURA_DA_REGUA - 2):
        _escrever("  %s" % pedaco)
    _escrever(REGUA)
    _escrever()
    # SO NO ARQUIVO: a tela ja mostrou o bloco acima, quebrado e legivel.
    # Esta linha existe para o relatorio.py, que a procura pelo prefixo
    # ">>> PENDENCIA: ". Imprimindo-a tambem, toda pendencia aparecia
    # duas vezes seguidas - e a segunda era a versao ruim.
    log("PENDENCIA: %s%s | %s"
        % ("%s | " % cliente if cliente else "", arquivo, motivo),
        alerta=True, so_no_arquivo=True)
    anotar_no_arquivo(arquivo, motivo, cliente)
    _chamar_a_tela(arquivo, motivo, cliente)


def _chamar_a_tela(arquivo, motivo, cliente=None):
    """
    Poe o problema na tela cheia, na hora em que ele acontece.

    E aqui, e nao no laco do vigia, porque a tela e o aviso do que
    ACABOU de acontecer - o operador pediu assim: "esse aviso e gerado
    exatamente na hora que vc informa um problema, nao precisa
    acumular".

    Nada aqui pode subir: a tela e um aviso, e um aviso que falha nao
    pode derrubar a gravacao da chapa. O import fica dentro da funcao
    porque o tela importa o config, e o config ja importou o utils.
    """
    if not TELA_DE_PENDENCIA:
        return
    try:
        from .tela import chamar
        chamar(arquivo, motivo, cliente, log=lambda t: log(t, alerta=True))
    except Exception as e:
        log("Nao consegui abrir a tela de aviso: %s" % str(e)[:80],
            alerta=True)


def anotar_no_arquivo(arquivo, motivo, cliente=None):
    """Uma linha no _PENDENCIAS.txt, sem o alarde na tela."""
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_PENDENCIAS.txt"), "a",
                  encoding="utf-8") as f:
            f.write("%s | %s%s | %s"
                    % (datetime.now().strftime("%d/%m %H:%M"),
                       "%s | " % cliente if cliente else "",
                       arquivo, motivo) + chr(10))
    except Exception:
        pass


def guardar_para_a_mao(caminho, nome_original):
    """
    Move para a PASTA_PENDENCIAS o arquivo que o programa nao deu conta.

    E o PDF que a Corel gerou. Guardando ele, o trabalho da conversao nao
    se perde: o operador abre esse PDF no Photoshop/InDesign, como sempre
    fez, em vez de converter o .cdr outra vez - que e a parte demorada.

    Devolve o caminho final, ou None se nem isso deu certo.
    """
    try:
        os.makedirs(PASTA_PENDENCIAS, exist_ok=True)
        base = os.path.splitext(os.path.basename(nome_original))[0]
        destino = nome_livre(PASTA_PENDENCIAS, base)
        shutil.move(caminho, destino)
        anotar_no_arquivo(os.path.basename(nome_original),
                          "PDF convertido guardado em %s" % destino)
        return destino
    except Exception as e:
        log("Nao consegui guardar o PDF em %s: %s" % (PASTA_PENDENCIAS, e),
            alerta=True)
        return None


def pendencias_abertas(limite=20):
    """Ultimas pendencias anotadas, a mais recente por ultimo."""
    try:
        with open(os.path.join(PASTA_CONTROLE, "_PENDENCIAS.txt"),
                  encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()][-limite:]
    except OSError:
        return []


# ----------------------------------------------------------------------
# Registro do que ja foi processado
# ----------------------------------------------------------------------
# A pasta de entrada e compartilhada, entao nada e movido de la. Em vez
# disso guardamos nome + tamanho + data de modificacao. Se a arte for
# corrigida e regravada, a chave muda e o arquivo e refeito sozinho.

def chave_arquivo(caminho):
    st = os.stat(caminho)
    return "%s|%d|%d" % (os.path.basename(caminho), st.st_size, int(st.st_mtime))


def impressao_digital(caminho, blocos=1 << 20):
    """
    Resumo do CONTEUDO do arquivo. Dois arquivos com o mesmo resumo sao
    a mesma arte, por mais que a data diga o contrario.

    Le em pedaco de 1 MB para nao carregar 400 MB na memoria de uma vez.
    """
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(blocos), b""):
            h.update(bloco)
    return h.hexdigest()


# ----------------------------------------------------------------------
# O que o registro sabe sobre esta arte
# ----------------------------------------------------------------------
# TRES respostas, e nao duas. Enquanto foram duas - 'e a mesma' e 'nao e'
# -, a segunda escondia dois casos muito diferentes dentro dela: 'olhei o
# conteudo e nao e' e 'nao tenho como olhar'. Confundidos, o segundo era
# tratado como o primeiro, e a chapa saia de novo.
#
# Estes nomes existem para que o monitor decida comparando CONSTANTE, e
# nao texto solto. E o mesmo cuidado do preflight: um teste cai se alguem
# reescrever isto sem mexer aqui.

JA_FEITO = "ja_feito"
NAO_DA_PARA_SABER = "nao_da_para_saber"
TRABALHO_NOVO = "trabalho_novo"


def _pode_ser_deste_cliente(entrada, cliente):
    """
    True quando a entrada antiga nao desmente ser deste cliente.

    Entrada sem cliente anotado nao desmente nada: e antiga demais para
    saber, e na duvida ela conta. Duvida a mais vira pendencia; duvida a
    menos vira chapa duplicada.
    """
    dono = entrada.get("cliente")
    return not cliente or not dono or dono == cliente


def situacao_no_registro(registro, caminho, cliente=None):
    """
    (situacao, entrada_antiga) - o que o registro sabe sobre esta arte.

      JA_FEITO           ha retrato e ele BATE. E a mesma arte, so
                         voltou para a pasta com data nova;
      NAO_DA_PARA_SABER  nome e tamanho batem com um trabalho ja feito,
                         mas aquela entrada nao guardou o retrato do
                         conteudo. Pode ser a mesma arte ou nao, e daqui
                         nao da para decidir;
      TRABALHO_NOVO      nada parecido, ou ha retrato e ele NAO bate.

    A entrada antiga volta junto para o aviso poder dizer QUE chapa saiu
    e QUANDO. Em TRABALHO_NOVO ela e None.

    Nasceu de dois acidentes. Em 08/09/2026 o '49694 - Gaspar -
    colinha.pdf' foi copiado por cima enquanto a primeira chapa saia: 12
    segundos de diferenca na data, chave nova, e o CTP ficou com
    49694.pdf e 49694_v2.pdf identicas byte a byte, 12,4 MB cada. O
    retrato do conteudo nasceu dai.

    So que ele so protege quem ja o tem. Em 09/09/2026, 87 das 156
    entradas do registro eram anteriores ao retrato - e para elas a
    protecao simplesmente nao agia. O '49695 - Radio Dente - pasta.pdf',
    que ja virara chapa em 08/09, voltou pela ponte do Teams e teria sido
    gravado de novo, com OS nova no GEREMPRE de producao e baixa de
    chapa no estoque de verdade.

    NAO CHUTA. Nome e tamanho iguais sem retrato e onde as duas respostas
    erram: 'ja feito' arrisca chapa FALTANDO, 'novo' arrisca chapa
    DUPLICADA. Entao devolve a duvida, e quem decide e gente.

    So abre o arquivo quando ha com o que comparar - a pasta e de rede e
    a varredura passa a cada 5 segundos. Se nenhuma candidata tem
    retrato, a duvida ja esta decidida sem ler um byte.
    """
    nome = os.path.basename(caminho)
    try:
        tamanho = os.path.getsize(caminho)
    except OSError:
        return TRABALHO_NOVO, None

    # So conta quem REALMENTE virou chapa. O registro guarda tambem o que
    # falhou - 'nao achei numero de OS no nome' entra com saidas vazia -,
    # e entrada de erro nao tem chapa nenhuma para duplicar. Se contasse,
    # o arquivo reenviado depois do conserto seria barrado, com um aviso
    # dizendo 'ja virou chapa' sobre uma chapa que nunca existiu.
    #
    # O cliente vale para as DUAS respostas. Dois clientes com arte
    # identica sao dois servicos, cada um com a sua OS e o seu
    # faturamento: reconhecer pelo conteudo e calar deixaria o segundo
    # sem chapa e sem aviso.
    prefixo = "%s|%d|" % (nome, tamanho)
    candidatas = [e for chave, e in registro.items()
                  if chave.startswith(prefixo)
                  and e.get("saidas")
                  and _pode_ser_deste_cliente(e, cliente)]

    com_retrato = [e for e in candidatas if e.get("impressao")]
    if com_retrato:
        try:
            atual = impressao_digital(caminho)
        except OSError:
            atual = None
        if atual is not None:
            for entrada in com_retrato:
                if entrada.get("impressao") == atual:
                    return JA_FEITO, entrada

    if not candidatas:
        # MESMO CONTEUDO, OUTRO NOME.
        #
        # A busca acima casa por NOME e tamanho, e por isso nao viu o
        # '49927 - Lucas Calil - santinhos grade2_2.pdf' de 16/09/2026:
        # byte a byte o mesmo arquivo do 'grade2.pdf' feito nove minutos
        # antes, com '_2' no fim do nome. Saiu segunda OS (19783), oito
        # chapas cobradas de novo, segunda prova impressa, e duas chapas
        # quase identicas no CTP - o pessoal quase gravou em duplicidade.
        #
        # O retrato do conteudo estava no registro e batia. Ninguem o
        # consultou, porque a peneira do nome veio antes.
        #
        # Agora o TAMANHO sozinho levanta as candidatas - e peneira
        # barata e nao depende de como o arquivo foi chamado -, e o
        # retrato decide.
        #
        # E a resposta e DUVIDA, nao 'ja feito': mesmo conteudo com nome
        # diferente pode ser reenvio (nao refazer) ou segundo servico de
        # verdade (refazer e cobrar). So quem tem o pedido na mao sabe.
        # Calar arriscaria chapa faltando; seguir arriscaria o que
        # aconteceu.
        por_tamanho = [e for chave, e in registro.items()
                       if chave.split("|")[1:2] == [str(tamanho)]
                       and e.get("impressao")
                       and e.get("saidas")
                       and _pode_ser_deste_cliente(e, cliente)]
        if por_tamanho:
            try:
                atual = impressao_digital(caminho)
            except OSError:
                atual = None
            if atual is not None:
                for entrada in por_tamanho:
                    if entrada.get("impressao") == atual:
                        return NAO_DA_PARA_SABER, entrada
        return TRABALHO_NOVO, None

    # Nenhum retrato bateu. As que nao TEM retrato continuam podendo ser
    # esta arte - e enquanto uma delas puder, nao da para seguir.
    sem_retrato = [e for e in candidatas if not e.get("impressao")]
    if sem_retrato:
        return NAO_DA_PARA_SABER, sem_retrato[0]
    return TRABALHO_NOVO, None


def caminho_registro():
    return os.path.join(PASTA_CONTROLE, REGISTRO)


def carregar_registro():
    try:
        with open(caminho_registro(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def salvar_registro(reg):
    """
    Grava o registro JUNTANDO com o que ja esta no disco.

    Mais de um programa pode estar rodando na maquina ao mesmo tempo - o
    operador com o F5 aberto e uma rodada avulsa, por exemplo. Cada um
    carrega o registro ao subir e, gravando o proprio dicionario, apagava
    o trabalho do outro.

    Ja aconteceu: uma chapa fechada as 09:20 sumiu do registro as 09:49,
    quando o outro programa salvou o dele. Na proxima varredura o arquivo
    seria refeito - outra prova impressa e chapa duplicada na pasta.

    Relendo antes de gravar, os dois lados se somam. Quem chamou recebe o
    conjunto de volta, para nao seguir com uma lista velha na memoria.

    CUIDADO: como junta, esta funcao NUNCA REMOVE. Apagar uma entrada -
    para refazer um arquivo, por exemplo - e gravar o JSON direto, ou
    apagar o _processados.json inteiro.
    """
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        completo = carregar_registro()      # o que outro programa gravou
        completo.update(reg)                # o nosso e o mais novo
        reg.clear()
        reg.update(completo)

        tmp = caminho_registro() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(completo, f, ensure_ascii=False, indent=1)
        os.replace(tmp, caminho_registro())
    except OSError as e:
        log("Nao consegui gravar o registro: %s" % e, alerta=True)


# ----------------------------------------------------------------------
# Arquivos
# ----------------------------------------------------------------------

def travar_instancia_unica():
    """
    Garante que so UM programa vigia as pastas nesta maquina.

    Duas instancias abertas ao mesmo tempo processam o mesmo arquivo:
    cada uma carrega a sua lista do que ja foi feito ao subir, as duas
    veem o arquivo novo como pendente, as duas imprimem a prova e as duas
    gravam a chapa no CTP.

    Aconteceu em 08/09/2026 - alguem deu F5 as 11:54 sem fechar a janela
    das 08:06 - e seis arquivos sairam em duplicidade no mesmo dia.

    O bloqueio e do sistema operacional, nao um arquivo de aviso: se o
    programa morrer (travou, faltou luz), o Windows solta sozinho e o
    proximo arranque nao fica preso por causa de sobra.

    Devolve o arquivo travado - que precisa ficar ABERTO enquanto o
    programa roda - ou None se ja ha outro rodando.
    """
    try:
        import msvcrt
    except ImportError:
        return True                      # fora do Windows, nao trava

    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    caminho = os.path.join(PASTA_CONTROLE, "_rodando.lock")
    try:
        arquivo = open(caminho, "a+b")
        arquivo.seek(0)
        msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        try:
            arquivo.close()
        except Exception:
            pass
        return None

    try:                                 # deixa quem esta rodando anotado
        arquivo.seek(1)
        arquivo.truncate(1)
        arquivo.write(("processo %d, desde %s"
                       % (os.getpid(),
                          datetime.now().strftime("%d/%m %H:%M:%S"))).encode())
        arquivo.flush()
    except Exception:
        pass
    return arquivo


def quem_esta_rodando():
    """O que o outro programa anotou no bloqueio, para o aviso na tela."""
    try:
        with open(os.path.join(PASTA_CONTROLE, "_rodando.lock"), "rb") as f:
            f.seek(1)
            return f.read(80).decode("utf-8", "ignore").strip()
    except OSError:
        return ""


def renomear_saida_no_registro(de, para):
    """
    Acerta o registro quando uma chapa ja gravada mudou de nome.

    Acontece no MODELO: chegando uma segunda arte com o mesmo nome, a
    primeira vira 'MODELO 1'. O registro guarda o que cada arquivo gerou,
    e um registro que aponta para uma chapa que nao existe mais nao serve
    para nada.
    """
    reg = carregar_registro()
    mexeu = False
    for entrada in reg.values():
        saidas = entrada.get("saidas") or []
        if de in saidas:
            entrada["saidas"] = [para if s == de else s for s in saidas]
            mexeu = True
    if mexeu:
        salvar_registro(reg)
    return mexeu


ESPERA_DA_REDE = 2             # segundos olhando o tamanho crescer


def arquivo_estavel(caminho):
    """True se o arquivo parou de crescer (terminou de copiar pela rede)."""
    return caminho in arquivos_estaveis([caminho])


def arquivos_estaveis(caminhos):
    """
    Quais destes pararam de crescer - UMA espera para a lista inteira.

    A conta e a mesma do arquivo_estavel, e ele passou a ser o caso de um
    arquivo so: mede, espera, mede de novo, e quem nao mudou de tamanho
    terminou de chegar.

    POR QUE A ESPERA E UMA, E NAO UMA POR ARQUIVO. Perguntando um a um,
    uma pasta com vinte arquivos dorme quarenta segundos - e quem esta
    esperando essa resposta e uma tela de gente. A espera existe para dar
    tempo AO ARQUIVO de crescer, e dois segundos passam para todos ao
    mesmo tempo.

    Arquivo que sumiu no meio - movido ou renomeado por alguem enquanto se
    esperava - simplesmente nao volta na lista. Nao e erro: e a resposta
    certa para 'este terminou de chegar?'.
    """
    antes = {}
    for caminho in caminhos:
        try:
            antes[caminho] = os.path.getsize(caminho)
        except OSError:
            pass
    if not antes:
        return []
    time.sleep(ESPERA_DA_REDE)
    prontos = []
    for caminho, tamanho in antes.items():
        try:
            if tamanho > 0 and os.path.getsize(caminho) == tamanho:
                prontos.append(caminho)
        except OSError:
            pass
    return prontos


def nome_livre(pasta, base):
    """Caminho de saida que ainda nao existe: X.pdf, X_v2.pdf, X_v3.pdf..."""
    alvo = os.path.join(pasta, base + ".pdf")
    n = 2
    while os.path.exists(alvo):
        alvo = os.path.join(pasta, "%s_v%d.pdf" % (base, n))
        n += 1
    return alvo
