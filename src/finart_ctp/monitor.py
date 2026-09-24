# -*- coding: utf-8 -*-
"""Laco principal: vigia a pasta do dia de cada cliente e manda o que aparecer."""

import os
import sys
import time
from datetime import datetime

from .config import (AVISAR_ARQUIVO_PARADO, BASE_CTP, BASE_ENTRADA,
                     CLIENTES_COM_PORTAO_QUE_NAO_APAGA,
                     SUBPASTA_PARA_CTP,
                     EXTENSOES_DE_ARTE,
                     BASE_ENTRADA_CREATIVE, BASE_ENTRADA_EMPORIO,
                     BASE_ENTRADA_FIALHO, BASE_ENTRADA_IDEAL,
                     BASE_ENTRADA_PRIME,
                     CLIENTES_QUE_SALVAM_A_MONTAGEM,
                     BASE_ENTRADA_VIVA,
                     BASE_ENTRADA_VOPRIX, CLIENTES_COM_FOLHA_DE_ESTOQUE,
                     ESPERA_IMPRESSORA, ESTOQUE_DE_QUANTO_EM_QUANTO,
                     PORTOES,
                     IMPRESSORA,
                     INTERVALO, SUBPASTA_SAIDA)
from . import america, entrada_teams
from . import estoque
from . import tela
from . import fila
from . import gerempre
from .ghostscript import GS
from .processador import (CREATIVE, EMPORIO, FIALHO, IDEAL, PRIME, SOLIDA,
                          VIVA, VOPRIX,
                          processar)
from .nomes import (e_backup_do_corel, e_montagem, e_relatorio,
                    e_verniz, veio_do_portao)
from .utils import (JA_FEITO, NAO_DA_PARA_SABER, abrir_bloco,
                    anotar_pendencia,
                    arquivo_estavel, carregar_registro,
                    chave_arquivo, fechar_bloco,
                    impressao_digital, localizar_pasta_mes, log,
                    pasta_do_dia, quem_esta_rodando,
                    salvar_registro, situacao_no_registro,
                    travar_instancia_unica)


# A primeira linha que a FIA escreve ao subir.
#
# Serve de marca: o relatorio do dia conta quantas vezes ela aparece no
# log para dizer quantas vezes a FIA subiu. Mudar este texto muda essa
# contagem - ver relatorio.py.
ARRANQUE = "FINART CTP no ar - Ctrl+C para parar"


def clientes():
    r"""
    (nome, base_de_entrada, extensoes) de cada pasta vigiada, na ordem.

    Cada cliente tem a sua base - dentro dela, sempre MES\DIA -, e traz um
    tipo de arquivo. A SAIDA e a mesma para todos: a FIA do dia.

    O Fialho olha .pdf E .cdr de proposito: so o PDF vira chapa, mas o
    .cdr precisa ser VISTO para virar pendencia. Arquivo que o programa
    ignora em silencio e servico que ninguem lembra de fazer.
    """
    lista = [(SOLIDA, BASE_ENTRADA, (".pdf",))]
    if BASE_ENTRADA_VOPRIX:
        # .cdr e o que ela manda, e o CorelDRAW converte. O .pdf entra
        # junto desde 22/09/2026, pelo mesmo motivo da PRIME - e porque
        # aqui a falta dele JA CUSTOU: no Folder_4_0_29,7x21,0_Ibccrim o
        # achatamento perdeu 38% do K (0,0714 -> 0,0441), a trava recusou
        # com razao, e o operador exportou o PDF certo A MAO e o salvou na
        # pasta. Medido, o PDF dele bate o K de antes no terceiro decimal.
        # So que a FIA nao olhava .pdf aqui: o arquivo certo ficou na pasta
        # INVISIVEL, e o servico parado sem ninguem ver por que.
        lista.append((VOPRIX, BASE_ENTRADA_VOPRIX, (".cdr", ".pdf")))
    if BASE_ENTRADA_FIALHO:
        lista.append((FIALHO, BASE_ENTRADA_FIALHO, (".pdf", ".cdr")))
    if BASE_ENTRADA_EMPORIO:
        lista.append((EMPORIO, BASE_ENTRADA_EMPORIO, (".pdf",)))
    if BASE_ENTRADA_VIVA:
        lista.append((VIVA, BASE_ENTRADA_VIVA, (".pdf", ".cdr")))
    if BASE_ENTRADA_CREATIVE:
        # o .cdr entra so para VIRAR PENDENCIA, como no Fialho e na VIVA
        lista.append((CREATIVE, BASE_ENTRADA_CREATIVE, (".pdf", ".cdr")))
    if BASE_ENTRADA_PRIME:
        # .cdr e o que ela manda, e o CorelDRAW converte - como a VOPRIX.
        # O .pdf entra junto para NAO passar despercebido: se um chegar,
        # segue o caminho normal, montado na chapa com a pinca.
        lista.append((PRIME, BASE_ENTRADA_PRIME, (".cdr", ".pdf")))
    if BASE_ENTRADA_IDEAL:
        # So PDF, como o EMPORIO. Os nove arquivos de setembro sao todos
        # .pdf, e o operador disse "as chapas vem em pdf". Aparecendo um
        # .cdr um dia, e conversa - nao se acrescenta extensao por via
        # das duvidas, que e como se comeca a processar o que ninguem
        # mandou processar.
        lista.append((IDEAL, BASE_ENTRADA_IDEAL, (".pdf",)))
    return lista


def linhas_do_arranque(vigiadas):
    """
    [(texto, alerta)] - uma linha por cliente, dizendo se a pasta abriu.

    "eu quero q vc so mostre os clientes q estao funcionando e com pasta
    aberta" - o operador, 14/09/2026.

    Quem nao abriu NAO some da lista: aparece dizendo que nao abriu.
    Cliente que desaparece em silencio e servico que ninguem faz - e a
    pasta de rede que nao respondeu agora pode responder na proxima
    varredura, entao ele continua sendo vigiado do mesmo jeito.
    """
    linhas = []
    for nome, base, _exts in vigiadas:
        if os.path.isdir(base):
            linhas.append(("%-10s OK" % (nome + ":"), False))
        else:
            linhas.append(("%-10s PASTA FORA DO AR - %s" % (nome + ":", base),
                           True))
    return linhas


def anuncio_do_dia(estreando, saida):
    """
    A UMA linha que diz quem passou a ser vigiado hoje, e onde grava.

    Vazia quando ninguem estreou - que e o caso de quase toda varredura.
    """
    if not estreando:
        return ""
    return "Vigiando %s. Gravando em %s" % (", ".join(estreando), saida)


def retrato_do_programa():
    """
    Data de cada arquivo .py do programa. Muda quando o codigo muda.

    So o proprio pacote, que fica no disco local: e uma olhada barata,
    nada de rede.
    """
    pasta = os.path.dirname(os.path.abspath(__file__))
    datas = {}
    for nome in sorted(os.listdir(pasta)):
        if nome.endswith(".py"):
            try:
                datas[nome] = os.path.getmtime(os.path.join(pasta, nome))
            except OSError:
                pass
    return datas


def avisar_se_o_programa_mudou(antes, ja_avisei):
    """
    Avisa quando o codigo mudou no disco depois que o programa subiu.

    O Python le o codigo UMA vez, ao subir. Conserto feito depois disso
    nao vale para a janela que esta aberta - ela segue com a versao
    antiga ate alguem parar e dar F5.

    Isso ja custou caro: em 08/09/2026 o programa rodou a tarde inteira
    com a versao anterior a tres consertos, e ninguem tinha como saber.
    Aqui ele mesmo avisa, uma vez, e diz o que mudou.

    Nao reinicia sozinho de proposito: rodando pelo F5 do VS Code, um
    processo novo se soltaria do depurador e a janela ficaria muda.
    """
    if ja_avisei:
        return True
    agora = retrato_do_programa()
    mudaram = [n for n, quando in agora.items() if antes.get(n) != quando]
    if not mudaram:
        return False

    log("", alerta=False)
    log("O PROGRAMA MUDOU NO DISCO desde que esta janela subiu.",
        alerta=True)
    log("   arquivo(s): %s" % ", ".join(sorted(mudaram)), alerta=True)
    log("   Esta janela SEGUE COM A VERSAO ANTIGA. Pare (Ctrl+C ou o",
        alerta=True)
    log("   quadrado vermelho) e suba de novo para o conserto valer.",
        alerta=True)
    return True


def arquivos_do_dia(entrada):
    r"""
    [(caminho, nome, rotulo)] de tudo que ha na pasta do dia, INCLUSIVE
    dentro das subpastas.

    O operador cria subpastas para se organizar - uma 'noite' com o que
    chegou depois do expediente, por exemplo - e combinou que aquilo e
    trabalho igual ao que esta solto na pasta do dia. Antes o programa
    so olhava o primeiro nivel, e o que estivesse numa subpasta ficava
    para sempre sem ser visto.

    'rotulo' e o caminho a partir da pasta do dia ('noite\GRADE 40.pdf'),
    para o aviso na tela dizer ONDE esta o arquivo. O nome da chapa sai
    do nome do arquivo, como sempre: a subpasta e organizacao de quem
    manda, nao faz parte do servico.
    """
    # Se a pasta do dia sumiu - a rede caiu, alguem renomeou -, o erro
    # tem de estourar. O os.walk sozinho devolveria lista vazia, e o
    # programa passaria o dia dizendo que nao ha trabalho nenhum.
    os.listdir(entrada)

    def reclamar(erro):
        log("Nao consegui ler %s: %s"
            % (getattr(erro, "filename", "?"), erro), alerta=True)

    achados = []
    for raiz, pastas, arquivos in os.walk(entrada, onerror=reclamar):
        pastas.sort()                     # subpastas em ordem, sempre igual
        for nome in sorted(arquivos):
            caminho = os.path.join(raiz, nome)
            achados.append((caminho, nome, os.path.relpath(caminho, entrada)))
    return achados


def avisar_arquivo_estranho(caminho, nome, cliente, extensoes, estranhos):
    """
    Avisa quando aparece ARTE que este cliente nao manda por aqui.

    O programa so olha as extensoes do cliente. O resto ele pulava calado
    - e arquivo de trabalho largado numa pasta de cliente, ignorado sem
    uma linha no log, e servico que ninguem lembra de fazer.

    So reclama de coisa que E arte (EXTENSOES_DE_ARTE). Lixo do Windows,
    sobra de programa e arquivo temporario continuam passando batido: um
    aviso que grita por qualquer coisa vira aviso que ninguem le.

    Avisa uma vez por arquivo, enquanto o programa estiver de pe.
    """
    if not nome.lower().endswith(EXTENSOES_DE_ARTE):
        return
    if caminho in estranhos or not os.path.isfile(caminho):
        return
    estranhos.add(caminho)
    anotar_pendencia(nome, "e arte, mas o %s so manda %s por esta pasta. "
                           "Nao sei tratar isto sozinho - faca a mao ou me "
                           "diga o que fazer"
                     % (cliente, " ou ".join(extensoes)), cliente)


def avisar_arquivo_parado(caminho, nome, parados, cliente=None):
    """
    Avisa quando um arquivo aparece na pasta mas nao termina de chegar.

    O programa nao encosta em arquivo instavel - se mexesse, geraria
    chapa de arte pela metade. So que ele pulava calado, e um PDF salvo
    com 0 byte ficava ali a tarde inteira sem ninguem saber: para o
    operador, a chapa simplesmente nao saiu.

    Avisa UMA vez por arquivo. Se ele terminar de chegar depois, some
    daqui e e processado normalmente.
    """
    agora = time.time()
    visto = parados.setdefault(caminho, {"desde": agora, "avisado": False})
    if visto["avisado"] or agora - visto["desde"] < AVISAR_ARQUIVO_PARADO:
        return
    visto["avisado"] = True

    try:
        tamanho = os.path.getsize(caminho)
    except OSError:
        return
    minutos = int((agora - visto["desde"]) / 60) or 1
    if tamanho == 0:
        motivo = ("o arquivo esta VAZIO (0 byte) ha %d min. A gravacao nao "
                  "terminou ou falhou - salve de novo, que eu pego sozinho"
                  % minutos)
    else:
        motivo = ("o arquivo ainda esta mudando de tamanho ha %d min (%.1f "
                  "MB agora). Nao encosto nele enquanto nao parar - se "
                  "ninguem esta gravando, salve de novo"
                  % (minutos, tamanho / 1048576))
    anotar_pendencia(nome, motivo, cliente)


def pasta_entrada_do_dia(base):
    r"""<base>\<MES>\<DIA> de hoje, ou None se a pasta ainda nao existe."""
    mes = localizar_pasta_mes(base)
    if not mes:
        return None
    entrada = os.path.join(base, mes, pasta_do_dia())
    return entrada if os.path.isdir(entrada) else None


def garantir_portao(cliente, entrada):
    r"""
    Cria a <dia>\PARA CTP de quem manda arte por montar. Sem barulho.

    Pedido do operador, 17/09/2026, sobre a FIALHO: "quando o arquivo
    vier pelo whattsapp ja montado, no tamanho das chapas dele e pincado,
    coloca na pasta PARA CTP, e de dentro dessa pasta vc envia pro ctp".

    NAO PRECISA DE CODIGO NENHUM PARA FECHAR O QUE CAI AI. O vigia ja
    varre as subpastas da pasta do dia (ver arquivos_do_dia), e o fluxo
    comum nunca apaga a entrada - que e justamente o "sem deletar o
    arquivo la de dentro, ja que esse arquivo so vai ter uma copia".

    Entao a pasta e um COMBINADO entre gente, nao um mecanismo: quem
    baixa do WhatsApp poe aqui o que ja esta montado, e deixa na pasta do
    dia o que ainda precisa de analise. Criar a pasta sozinho e so tirar
    a desculpa de nao ter onde soltar.

    E NAO E A 'PARA CTP' DA AMERICA, que se parece e e o contrario: la o
    arquivo e APAGADO depois de gravado, porque a copia da casa ja ficou
    na pasta do dia. Aqui nao ha segunda copia, e apagar seria perder o
    arquivo do cliente.
    """
    if cliente not in CLIENTES_COM_PORTAO_QUE_NAO_APAGA:
        return
    portao = os.path.join(entrada, SUBPASTA_PARA_CTP)
    if os.path.isdir(portao):
        return
    try:
        os.makedirs(portao)
        log("%s: criei a pasta '%s' na pasta do dia - o que estiver la "
            "dentro eu fecho, e nao apago" % (cliente, SUBPASTA_PARA_CTP))
    except OSError as e:
        # pasta de cliente pode ser so-leitura para nos; nao e motivo
        # para parar o dia
        log("%s: nao consegui criar a '%s' (%s)"
            % (cliente, SUBPASTA_PARA_CTP, str(e)[:60]), alerta=True)


def pasta_saida_do_dia():
    r"""
    <BASE_CTP>\<MES>\<DIA>\FIA - a mesma para todos os clientes.

    O CTP tem a propria arvore de meses, escrita do jeito dele.
    """
    mes = localizar_pasta_mes(BASE_CTP, criar=True)
    return os.path.join(BASE_CTP, mes, pasta_do_dia(), SUBPASTA_SAIDA)


def pastas_do_dia(base=None):
    """(entrada, saida) de hoje, ou (None, None) sem pasta de entrada."""
    entrada = pasta_entrada_do_dia(base or BASE_ENTRADA)
    if not entrada:
        return None, None
    return entrada, pasta_saida_do_dia()


def varrer(entrada, saida, registro, espera=None, cliente=SOLIDA,
           extensoes=(".pdf",), adiados=None, parados=None,
           estranhos=None):
    """
    Processa o que ainda nao foi feito. Devolve quantos rodaram.

    Se a impressora estiver fora, nada e gerado: a varredura para e so
    volta a tentar depois de ESPERA_IMPRESSORA segundos.

    'adiados' guarda os arquivos que estao abertos no CorelDRAW do
    operador, so para o aviso nao se repetir a cada varredura.
    'parados' faz o mesmo com os que nao terminam de chegar e
    'estranhos' com os que o programa nao sabe tratar.
    """
    espera = {"ate": 0, "avisado": False} if espera is None else espera
    if time.time() < espera["ate"]:
        return 0
    adiados = set() if adiados is None else adiados
    parados = {} if parados is None else parados
    estranhos = set() if estranhos is None else estranhos

    feitos = 0
    for caminho, arquivo, nome in arquivos_do_dia(entrada):
        if e_backup_do_corel(arquivo) or arquivo.startswith("~"):
            continue          # copia de seguranca do Corel nao e trabalho
        if e_relatorio(arquivo):
            continue          # o relatorio de estoque e SAIDA nossa
        if cliente in CLIENTES_QUE_SALVAM_A_MONTAGEM and e_montagem(arquivo):
            continue          # a montagem e SAIDA nossa, nao entrada
        if e_verniz(arquivo):
            # FOTOLITO, e nao chapa - de TODO cliente. Calado de
            # proposito: o operador pediu assim em 17/09/2026, e o
            # barulho era o problema - cada verniz abria uma tela cheia
            # que alguem tinha de fechar, para dizer algo que ele ja
            # sabia. Os 11 verniz que passaram por aqui desde 02/09
            # geraram zero chapas.
            #
            # MASCARA entra aqui junto desde 21/09/2026 - e a mesma
            # coisa com outro nome, e os 5 que passaram por aqui
            # geraram zero chapas tambem. Ver nomes.e_verniz.
            continue
        if not arquivo.lower().endswith(tuple(extensoes)):
            avisar_arquivo_estranho(caminho, nome, cliente, extensoes,
                                    estranhos)
            continue
        if not os.path.isfile(caminho):
            continue
        try:
            chave = chave_arquivo(caminho)
        except OSError:
            continue
        if chave in registro:
            # JA FEITO - mas pode ter ficado no portao. A faxina se tenta
            # DE NOVO a cada volta, e nao so na hora em que a chapa saiu.
            #
            # Em 17/09/2026 o calendario da FIALHO gravou as quatro
            # chapas, abriu a OS e imprimiu as provas, e o apagar bateu
            # num WinError 32 - o .cdr de 26 MB ainda estava preso por
            # alguem (o CorelDRAW nao era: zero documentos abertos).
            # Tentando uma vez so, o arquivo ficaria no portao para
            # sempre, e o portao deixaria de dizer o que falta.
            esvaziar_o_portao(caminho, nome, cliente, registro[chave])
            continue
        # Outro programa pode ter feito este arquivo enquanto estavamos
        # ocupados com o anterior - uma separacao leva minutos. Reler o
        # registro custa quase nada e evita chapa duplicada.
        registro.update(carregar_registro())
        if chave in registro:
            esvaziar_o_portao(caminho, nome, cliente, registro[chave])
            continue
        if not arquivo_estavel(caminho):
            # Ainda chegando - ou salvo com 0 byte e parado ali. Nao
            # encosto, mas depois de um tempo aviso: chapa que nao sai
            # sem ninguem saber e pior do que chapa que da erro.
            avisar_arquivo_parado(caminho, nome, parados, cliente)
            continue
        parados.pop(caminho, None)

        # A ARTE QUE VOLTA IGUAL AGORA PASSA, MARCADA - 22/09/2026.
        #
        # Ate hoje isto RECUSAVA: arte identica voltando para a pasta nao
        # virava chapa de novo, so ganhava uma chave nova apontando para
        # a chapa velha. Existia para impedir que arte regravada por cima
        # saisse duas vezes no CTP com duas baixas de estoque.
        #
        # O OPERADOR TIROU, DE TODOS OS CLIENTES: "esse arquivo da
        # creative chegou, mas o cliente pediu pra refazer o mesmo
        # servico (...) depois tire essa trava de TODOS os clientes".
        #
        # O caso foi o 'CUPOM 13 08.pdf' da CREATIVE, de volta na pasta
        # as 16:57 com a MESMA arte de 08/09 - impressao digital igual,
        # bc3001a1... O cliente pediu refacao, e refacao e servico novo:
        # gasta chapa, gasta maquina, e se cobra.
        #
        # E NAO SE APAGOU A PROTECAO - ela virou a OUTRA, que ja existia
        # ao lado e e melhor. O caminho do NAO_DA_PARA_SABER, logo
        # abaixo, deixa passar E MARCA A OS com 'REGRAVACAO'. E a marca
        # que importa: numa refacao a arte e a mesma DE PROPOSITO, e sem
        # ela ninguem distingue, olhando a OS, uma segunda cobranca
        # deliberada de uma cobranca em dobro.
        #
        # O QUE SE PERDE, e o operador decidiu sabendo: arte salva por
        # cima sem querer - o mesmo arquivo caindo na pasta duas vezes
        # por descuido - passa a virar chapa e OS de novo. Era esse o
        # caso do '49694 - Gaspar - colinha.pdf' de 08/09/2026, duas
        # chapas identicas byte a byte com 12 segundos entre elas. Daqui
        # em diante quem percebe isso e gente, pela marca REGRAVACAO na
        # OS - e e por isso que a marca fica.
        situacao, antiga = situacao_no_registro(registro, caminho, cliente)
        if situacao == JA_FEITO:
            log("'%s' voltou para a pasta e e a MESMA arte de %s (ja saiu "
                "como %s). REFACAO: vou refazer, e a OS sai marcada com "
                "'%s'"
                % (nome, antiga.get("quando", "antes"),
                   ", ".join(antiga.get("saidas") or []) or "nada",
                   fila.MARCA_REGRAVACAO),
                alerta=True)
            situacao = NAO_DA_PARA_SABER
        # NAO DA PARA SABER se ja virou chapa: nome e tamanho batem com um
        # trabalho antigo, e aquela entrada do registro e anterior ao
        # retrato do conteudo. Ate 14/09/2026 isto PARAVA e virava
        # pendencia.
        #
        # Regra do operador naquele dia: "o cliente pediu uma regravacao
        # de algum arquivo, ele pode ter alterado alguma coisa e mandou
        # novamente, acontece, nesse caso pode dar andamento, e colocar no
        # nome da OS, depois do nome do arquivo, ARQUIVO NOVO".
        #
        # Entao segue, e a OS sai MARCADA. A marca e o que faz a diferenca:
        # numa regravacao a arte costuma ser a mesma de proposito - o
        # 'AGENDA_2027_ CREDIBRASILIA' de 14/09 e byte a byte igual ao de
        # 08/09, mesmo SHA-256 -, e sem ela ninguem distinguiria, olhando a
        # OS, uma segunda cobranca DELIBERADA de uma cobranca em dobro.
        #
        # O aviso desceu de PENDENCIA para alerta no log: pendencia quer
        # dizer "parou, alguem resolve", e isto nao para mais.
        regravacao = False
        if situacao == NAO_DA_PARA_SABER:
            regravacao = True
            log("'%s': nome e tamanho batem com %s, de %s. Nao da para "
                "conferir se e a mesma arte - segui como REGRAVACAO, e a "
                "OS vai marcada com '%s'"
                % (nome, ", ".join(antiga.get("saidas") or []) or "uma chapa",
                   antiga.get("quando", "antes"), fila.MARCA_REGRAVACAO),
                alerta=True)

        # O BLOCO DA TELA COMECA AQUI e acaba depois do processar.
        #
        # E aqui, e nao dentro do processar, por um motivo: as linhas da
        # REGRAVACAO e do 'voltou para a pasta' saem antes dele e sao
        # daquele arquivo tambem. Abrindo mais para dentro, elas cairiam
        # soltas em cima do cabecalho, que e a bagunca que isto arruma.
        #
        # O QUE JA FOI ADIADO E CONTINUA ABERTO NAO SE ANUNCIA DE NOVO.
        #
        # Arquivo aberto no CorelDRAW de alguem vira 'adiado' e NAO entra
        # no registro - de proposito, para ser tentado quando fecharem.
        # So que isso o traz de volta a CADA volta do vigia, e ate
        # 24/09/2026 cada volta abria um bloco na tela: o operador viu o
        # mesmo 'Cartao de Visitas' encabecando a janela dezenas de vezes
        # em poucos minutos, sem uma palavra de motivo - o motivo e dito
        # UMA vez, logo abaixo, e some no meio da repeticao.
        #
        # Entao, para quem ja esta na lista dos adiados, PERGUNTA-SE
        # PRIMEIRO. Continuando aberto, a volta termina aqui: sem bloco,
        # sem tentativa de conversao, sem linha nenhuma. Fechando o
        # arquivo, ele cai no caminho normal na volta seguinte e o bloco
        # sai como sempre saiu.
        #
        # E CUSTA MENOS: antes, cada volta abria o Corel por COM e
        # tentava converter para so entao descobrir o que ja se sabia.
        if chave in adiados and nome.lower().endswith(".cdr"):
            from .corel import em_uso
            if em_uso(caminho):
                continue
            # fechou: sai da lista e segue, para o bloco sair inteiro
            adiados.discard(chave)

        # So escreve na TELA. Ver o cabecalho do log em utils.
        abrir_bloco(cliente, nome)
        try:
            resultado = processar(caminho, saida, cliente,
                                  regravacao=regravacao)
        finally:
            # FECHA DE QUALQUER JEITO. Estourando no meio, um bloco aberto
            # engoliria o proximo arquivo debaixo deste cabecalho - e a
            # janela mentiria sobre de quem e a linha.
            fechar_bloco()

        if resultado["status"] == "espera":
            # Nada foi gerado. Nao entra no registro, para ser refeito
            # inteiro quando a impressora voltar.
            espera["ate"] = time.time() + ESPERA_IMPRESSORA
            if not espera["avisado"]:
                espera["avisado"] = True
                log("PARADO: %s esta fora do ar." % IMPRESSORA, alerta=True)
                log("        '%s' e os proximos ficam segurados, nenhuma "
                    "chapa sai." % nome, alerta=True)
                quanto = ("%d min" % (ESPERA_IMPRESSORA // 60)
                          if ESPERA_IMPRESSORA >= 60
                          else "%d s" % ESPERA_IMPRESSORA)
                log("        Arrume a impressora; tento de novo a cada %s, "
                    "sozinho." % quanto, alerta=True)
            return feitos

        if resultado["status"] == "adiado":
            # Arte aberta no CorelDRAW de alguem. Nao entra no registro:
            # fica para a proxima passada, quando a pessoa fechar.
            if chave not in adiados:
                adiados.add(chave)
                log("'%s' esta aberto no CorelDRAW. Nao encosto nele; "
                    "converto quando fecharem." % nome, alerta=True)
            continue
        adiados.discard(chave)

        if espera["avisado"]:
            espera["avisado"] = False
            log("Impressora voltou. Retomando a fila.", alerta=True)

        resultado["quando"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resultado["arquivo"] = nome
        resultado["cliente"] = cliente
        try:
            # o retrato do conteudo, para reconhecer a mesma arte se ela
            # voltar para a pasta com data nova
            resultado["impressao"] = impressao_digital(caminho)
        except OSError:
            pass
        registro[chave] = resultado
        salvar_registro(registro)

        # A FAXINA DO PORTAO VEM DEPOIS DE ANOTAR, e nunca antes.
        #
        # E a licao de 10/09/2026 na AMERICA, que custou tres folhas de
        # papel: o trabalho esta FEITO quando a chapa esta no CTP e a OS
        # existe. O apagar e faxina. Anotando so depois da faxina,
        # qualquer tropeco nela fazia a volta seguinte refazer tudo -
        # inclusive IMPRIMIR DE NOVO.
        esvaziar_o_portao(caminho, nome, cliente, resultado)
        feitos += 1
    return feitos


def esvaziar_o_portao(caminho, nome, cliente, resultado):
    """
    Tira da 'PARA CTP' o que ja virou chapa. Nao estoura nunca.

    "ao finalizar tudo, apague o arquivo dentro da pasta PARA CTP" - o
    operador, 17/09/2026. Faz sentido: portao que acumula deixa de dizer
    o que esta por fazer, e passa a ser mais uma pasta.

    MAS ELE TAMBEM DISSE, no mesmo dia: "sem deletar o arquivo la de
    dentro, ja que esse arquivo so vai ter uma copia". As duas coisas
    convivem, e e assim que a AMERICA ja faz: a copia SOBE para a pasta
    do dia, e so entao o portao e esvaziado. Nada se perde, e o portao
    volta a ser uma lista do que falta.

    So mexe quando o servico foi ate o fim - chapa no CTP e status ok.
    Falhou, ficou pela metade, ou nao saiu chapa nenhuma? O arquivo FICA,
    e a proxima volta tenta de novo.
    """
    if cliente not in CLIENTES_COM_PORTAO_QUE_NAO_APAGA:
        return
    if not veio_do_portao(caminho):
        return
    if resultado.get("status") != "ok" or not resultado.get("saidas"):
        return

    pasta_dia = os.path.dirname(os.path.dirname(os.path.abspath(caminho)))
    try:
        guardada, o_que_fiz = america.guardar_copia(caminho, pasta_dia)
        if not os.path.exists(guardada):
            log("'%s': nao consegui guardar a copia na pasta do dia - "
                "deixei no portao" % nome, alerta=True)
            return
        os.remove(caminho)
        log("   tirei do portao: a copia esta na pasta do dia (%s)"
            % {"copiei": "levei agora",
               "ja_era_a_mesma": "ja estava la, igual",
               "troquei": "havia outra com o mesmo nome; a antiga ficou "
                          "com a data no nome"}[o_que_fiz])
    except Exception as e:
        # Portao cheio e incomodo; chapa gravada duas vezes e prejuizo.
        # Como o registro JA foi salvo, nao refaco nada - so aviso.
        log("'%s': gravei tudo, mas nao consegui tirar do portao (%s). "
            "Tire a mao quando puder." % (nome, str(e)[:70]), alerta=True)


def rodada_do_estoque(ultima_olhada, agora=None):
    """
    Refaz a folha de estoque dos clientes que a tem, se for a hora.

    Devolve quando a ultima pergunta foi feita, para a volta seguinte.
    Nada aqui escreve no GEREMPRE, e nada aqui derruba o laco: sem
    banco, a folha simplesmente fica com o numero de antes.
    """
    agora = agora if agora is not None else time.time()
    # None e 'ainda nao olhei' - a folha sai logo na primeira volta,
    # para quem sobe a FIA de manha ja encontrar o numero de hoje.
    if (ultima_olhada is not None
            and agora - ultima_olhada < ESTOQUE_DE_QUANTO_EM_QUANTO):
        return ultima_olhada
    for cliente in CLIENTES_COM_FOLHA_DE_ESTOQUE:
        try:
            estoque.acompanhar(cliente)
        except Exception as e:
            log("Nao consegui refazer a folha de estoque da %s: %s"
                % (cliente, str(e)[:80]))
        fechar_o_que_ficou(cliente)
    return agora


def fechar_o_que_ficou(cliente):
    """
    Escreve o relatorio de fechamento dos dias que ainda nao o tem.

    E o que acontece a meia-noite, sem ninguem mandar: o dia de ontem
    passa a estar 'por fechar' e a volta seguinte do laco o fecha. E e
    tambem o que conserta o dia em que a maquina esteve desligada na
    virada - ao subir, a FIA olha para tras e escreve o que faltou,
    para o operador achar o relatorio quando chegar cedo.

    Custa uma consulta de arquivo por volta quando nao ha nada a fazer:
    'este arquivo existe?'. So vai ao banco tendo dia a fechar.
    """
    try:
        for dia in estoque.dias_por_fechar(cliente):
            estoque.fechar_o_dia(cliente, dia)
    except Exception as e:
        log("Nao consegui fechar o dia da %s: %s" % (cliente, str(e)[:80]))


def main():
    if not GS:
        print("Ghostscript nao encontrado. Instale em ghostscript.com")
        sys.exit(1)
    try:
        import pypdf, PIL          # noqa: F401,E401
    except ImportError as e:
        print("Falta biblioteca (%s).\nRode:  pip install pypdf pillow" % e)
        sys.exit(1)

    # UM programa por maquina. Dois ao mesmo tempo geram chapa duplicada
    # e prova impressa em dobro - aconteceu em 08/09/2026, com seis
    # arquivos, quando alguem deu F5 sem fechar a janela anterior.
    trava = travar_instancia_unica()
    if trava is None:
        print("JA HA UM PROGRAMA DESTES RODANDO nesta maquina.")
        outro = quem_esta_rodando()
        if outro:
            print("   %s" % outro)
        print("")
        print("Dois ao mesmo tempo geram CHAPA DUPLICADA e prova impressa")
        print("em dobro: os dois veem o arquivo novo como pendente.")
        print("Feche a outra janela antes de abrir esta.")
        sys.exit(1)

    vigiadas = clientes()

    # A VOPRIX so anda com o pywin32: e por ele que se fala com o
    # CorelDRAW. Sem a biblioteca, seguimos so com a SOLIDA.
    if any(nome == VOPRIX for nome, _, _ in vigiadas):
        try:
            import win32com.client       # noqa: F401
        except ImportError:
            print("Sem pywin32 nesta maquina: nao da para converter os .cdr\n"
                  "da VOPRIX. Rode  pip install pywin32  e reabra.\n"
                  "Por enquanto, sigo so com a SOLIDA.")
            vigiadas = [c for c in vigiadas if c[0] != VOPRIX]

    if not any(os.path.isdir(base) for _, base, _ in vigiadas):
        # PARA AQUI, e nao segue vigiando o nada.
        #
        # Em 16/09/2026 esta saida foi tirada, porque a FIA "nao mostrava
        # nada" ao subir. A causa era outra - o VS Code aberto como
        # administrador nao enxerga letra mapeada, e nenhuma pasta
        # existia (ver a skill gerempre, armadilha 27). Sem esta parada
        # ela subiria calada, vigiando pasta nenhuma, e ninguem saberia:
        # e o mesmo defeito da armadilha 19 do fechamento, o avisador que
        # falha em silencio.
        print("Nao achei nenhuma pasta de entrada:")
        for nome, base, _ in vigiadas:
            print("    %-7s %s" % (nome, base))
        print("Confira o config_local.py (ou o config.py).")
        print("Se o VS Code estiver como ADMINISTRADOR, letra mapeada "
              "(V:, W:) nao existe para ele - use o caminho de rede "
              "inteiro, \\\\servidor\\...")
        sys.exit(1)

    # O QUE APARECE QUANDO A FIA SOBE.
    #
    # Pedido do operador, 14/09/2026: "quando eu dou F5 o terminal ta
    # ficando uma bagunca... eu quero q vc so mostre os clientes q estao
    # funcionando e com pasta aberta".
    #
    # Sairam daqui o caminho de cada entrada, a pasta de saida, a pasta
    # do Teams, a pasta de controle e a contagem do registro: sao sempre
    # os mesmos e ninguem le doze linhas de caminho de rede toda vez.
    #
    # O QUE NAO SAIU foi o aviso. Cliente cuja pasta nao respondeu
    # aparece dizendo isso, em vez de sumir da lista - cliente que some
    # em silencio e servico que ninguem faz. E ele CONTINUA vigiado: rede
    # cai e volta, e a pasta pode aparecer na proxima varredura.
    log(ARRANQUE)
    if not GS:
        log("ATENCAO: nao achei o Ghostscript - nenhuma chapa vai ser "
            "gravada", alerta=True)
    for texto, alerta in linhas_do_arranque(vigiadas):
        log(texto, alerta=alerta)

    registro = carregar_registro()
    espera = {"ate": 0, "avisado": False}
    adiados = set()
    parados = {}
    estranhos = set()
    codigo = retrato_do_programa()      # para saber se mudou depois
    ja_avisei_do_codigo = False

    esperando = fila.esperando()
    if esperando:
        log("Fila de OS: %s"
            % ", ".join("%s %d" % (c, n) for c, n in esperando.items()))

    trazidos = entrada_teams.carregar_trazidos()
    avisados_teams = set()

    # O que impediria a ponte de andar - OneDrive parado, pasta que nao
    # existe - dito agora, com alguem olhando a tela. E, se muita coisa
    # esperou junta (fim de semana), o que vai entrar e dito ANTES de
    # entrar, com uma pausa para dar tempo de Ctrl+C.
    entrada_teams.conferir_no_arranque()
    entrada_teams.anunciar_rajada(trazidos)

    ultima = {}
    avisados_america = {}
    olhado_o_estoque = None
    while True:
        try:
            # Primeiro a ponte, depois a varredura: o que o cliente
            # postou no Teams cai na pasta do dia e ja e visto na MESMA
            # volta do laco. Na ordem inversa, todo arquivo esperaria a
            # volta seguinte sem motivo.
            entrada_teams.rodada(trazidos, avisados_teams)

            # OS PORTOES - AMERICA e CARRIER.
            #
            # Eles nao entram na lista de 'vigiadas' porque o caminho
            # deles e outro: o arquivo chega POR MONTAR, e o que a FIA
            # fecha nao e a pasta do dia - e a subpasta 'PARA CTP', onde
            # o operador poe a montagem depois de revisar. Ver a skill de
            # imposicao, america.md.
            #
            # UM DE CADA VEZ, E CADA UM COM O SEU 'avisados': o aviso de
            # pasta que nao abre e guardado por portao para nao repetir a
            # cada volta, e um dicionario so faria a queixa da AMERICA
            # calar a da CARRIER.
            #
            # E UM CAINDO NAO DERRUBA O OUTRO: o america.rodada ja nao
            # estoura para cima, e este laco continua valendo para os
            # dois.
            for _portao in PORTOES:
                america.rodada(
                    avisados_america.setdefault(_portao["cliente"], {}),
                    portao=_portao)

            # A CONFERENCIA DAS VAGAS QUE A FIA COMPLETOU.
            #
            # Desde 11/09/2026 ela entra na OS de QUALQUER operador que
            # tenha vaga aberta para o cliente naquele dia. Quem estiver
            # com essa OS na tela salva o que ESTA VENDO e apaga a vaga
            # dela sem que nada de erro. Nao da para detectar na hora -
            # o Delphi nao tranca a linha -, entao releem-se as vagas
            # alguns minutos depois. Sumiu, vira pendencia.
            #
            # E barato: so vai ao banco quando ha vaga vencida para
            # conferir, e nao escreve nada la.
            try:
                gerempre.conferir_completadas()
            except Exception as e:
                log("Nao consegui conferir as vagas completadas: %s"
                    % str(e)[:80])

            # O DIA SE ANUNCIA UMA VEZ, e nao uma vez por cliente.
            #
            # Eram duas linhas para cada um - 'Vigiando X' e 'Gravando
            # em' -, e como o dia vira para todos ao mesmo tempo, isso
            # caia na tela em bloco: catorze linhas, treze delas
            # repetidas, bem no meio do trabalho. Pedido do operador,
            # 14/09/2026: "quando apareceu um arquivo em uma das pastas
            # apareceu tudo isso embaixo".
            #
            # A pasta de saida e a MESMA para todos, entao vai no fim da
            # linha, uma vez. E quem ainda nao tem pasta do dia continua
            # dizendo isso, sozinho, quando for o caso.
            entradas, estreando = [], []
            for nome, base, exts in vigiadas:
                entrada = pasta_entrada_do_dia(base)
                if not entrada:
                    if ultima.get(nome) != "sem_pasta":
                        ultima[nome] = "sem_pasta"
                        log("%s: esperando a pasta do dia aparecer em %s"
                            % (nome, base))
                    continue
                if ultima.get(nome) != entrada:
                    ultima[nome] = entrada
                    estreando.append(nome)
                    garantir_portao(nome, entrada)
                entradas.append((nome, entrada, exts))

            saida = pasta_saida_do_dia()
            anuncio = anuncio_do_dia(estreando, saida)
            if anuncio:
                log(anuncio)

            for nome, entrada, exts in entradas:
                varrer(entrada, saida, registro, espera, nome, exts,
                       adiados, parados, estranhos)

            # A FOLHA DE ESTOQUE DO CLIENTE.
            #
            # Vem DEPOIS da varredura de proposito: o que a FIA acabou
            # de lancar ja entra na folha na mesma volta. Nao gasta
            # ligacao a toa - uma pergunta por minuto, e so redesenha
            # quando o movimento mudou. Falhar aqui nao pode parar o
            # laco: estoque e acompanhamento, chapa e servico.
            olhado_o_estoque = rodada_do_estoque(olhado_o_estoque)

            # A REDE DE SEGURANCA DA TELA DE AVISO. Se ela falhou ao
            # subir na hora da pendencia, sobe agora - o operador ve o
            # aviso um minuto depois em vez de nao ver nunca.
            tela.rodada()

            ja_avisei_do_codigo = avisar_se_o_programa_mudou(
                codigo, ja_avisei_do_codigo)
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("Encerrado.")
            break
        except Exception as e:
            log("Erro no laco principal: %s" % e, alerta=True)
            time.sleep(INTERVALO)
