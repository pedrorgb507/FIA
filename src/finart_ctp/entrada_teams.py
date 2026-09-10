# -*- coding: utf-8 -*-
r"""
Ponte: traz para a pasta do dia o que o cliente postou no Teams.

O cliente posta o arquivo no canal dele, dentro do time da Finart. Dali
em diante ninguem precisa salvar nada a mao:

    canal do Teams
      -> SharePoint do time         (a Microsoft leva, sozinha)
      -> pasta sincronizada no PC   (o OneDrive baixa, sozinho)
      -> V:\<cliente>\<MES>\<DIA>   (esta ponte)
      -> chapa                      (o monitor.py, que ja existia)

NAO HA TOKEN, SENHA NEM APLICATIVO REGISTRADO. Quem autentica e o
OneDrive que ja roda nesta maquina, com a conta da casa. Isso foi
escolhido de proposito: o caminho que depende de credencial propria e o
que expira as tres da manha de um sabado, e ninguem descobre ate a
segunda, quando as chapas do fim de semana nao sairam.

O ORIGINAL NUNCA E APAGADO. A pasta sincronizada e o SharePoint sao o
MESMO lugar - apagar aqui apagaria o post do cliente la, e ele nao tem
como saber. O que impede o arquivo de vir duas vezes e o registro, nao
a faxina.

A PONTE NAO FALA COM O CLIENTE. Quando um arquivo trava, quem fica
sabendo e o operador, pelo log e pela pendencia - que agora diz de qual
cliente e. Os textos de pendencia sao escritos para quem conhece o
servico ('nao achei numero de OS no nome') e nao para quem mandou o
arquivo. Programa que fala sozinho com cliente se liga depois de meses
vendo o que ele diria.
"""

import io
import json
import os
import shutil
import subprocess
import time

from .config import (BASE_ENTRADA, BASE_ENTRADA_CREATIVE, BASE_ENTRADA_EMPORIO,
                     BASE_ENTRADA_FIALHO, BASE_ENTRADA_VIVA,
                     BASE_ENTRADA_VOPRIX, CAIXAS_TEAMS, CLIENTES_NO_TEAMS,
                     ESPERA_RAJADA, EXTENSOES_DE_ARTE, PASTA_CONTROLE,
                     PASTA_TEAMS, PASTAS_IGNORADAS_TEAMS, RAJADA,
                     REGISTRO_TEAMS)
from .utils import (anotar_pendencia, arquivo_estavel, impressao_digital,
                    localizar_pasta_mes, log, normalizar, pasta_do_dia)


# O que vale a pena atravessar a ponte. E mais largo do que o cliente
# costuma mandar, de proposito: um .cdr da SOLIDA nao vira chapa, mas
# precisa CHEGAR na pasta para o monitor.py transformar em pendencia.
# Arquivo de arte que fica preso do lado de la e servico que ninguem
# lembra de fazer - e la ninguem sequer veria que ele existe.
EXTENSOES_QUE_ATRAVESSAM = (".pdf",) + EXTENSOES_DE_ARTE

# Sinais de que o OneDrive ainda nao baixou o arquivo: ele aparece no
# diretorio, com o tamanho certo, mas o conteudo continua na nuvem. Ler
# um desses dispara o download - que trava se a internet estiver fora.
# Melhor enxergar e esperar do que abrir e pendurar o programa.
RECALL_ON_OPEN = 0x00040000
RECALL_ON_DATA_ACCESS = 0x00400000


# ----------------------------------------------------------------------
# Quais caixas existem
# ----------------------------------------------------------------------

def caixas():
    r"""
    (cliente, pasta_de_origem, base_de_destino) de cada cliente CONFIGURADO.

    Devolve tambem quem esta configurado e cuja pasta NAO existe. Antes
    ficava de fora, calado, e era o buraco mais perigoso da ponte: com o
    OneDrive parado ou deslogado, a lista vinha vazia, nada atravessava,
    e o log passava o dia em branco. O operador achava que o cliente nao
    mandou nada; o cliente achava que a chapa estava saindo.

    Quem reclama da pasta que sumiu e quem for usar a lista.
    """
    bases = {"SOLIDA": BASE_ENTRADA,
             "VOPRIX": BASE_ENTRADA_VOPRIX,
             "FIALHO": BASE_ENTRADA_FIALHO,
             "EMPORIO": BASE_ENTRADA_EMPORIO,
             "VIVA": BASE_ENTRADA_VIVA,
             "CREATIVE": BASE_ENTRADA_CREATIVE}
    lista = []
    for cliente in CLIENTES_NO_TEAMS:
        base = bases.get(cliente)
        if not base:
            continue          # sem pasta no V:, nao ha para onde trazer
        # Caminho proprio ganha do padrao. E a porta para o dia em que o
        # cliente sair da raiz comum - canal privado e link de
        # solicitacao ganham site proprio no SharePoint.
        origem = CAIXAS_TEAMS.get(cliente)
        if not origem and PASTA_TEAMS:
            origem = os.path.join(PASTA_TEAMS, cliente)
        if origem:
            lista.append((cliente, origem, base))
    return lista


def ignorada(nome):
    """True para a pasta que a ponte nunca abre ('Arquivado')."""
    alvo = normalizar(nome)
    return any(normalizar(p) == alvo for p in PASTAS_IGNORADAS_TEAMS)


def so_na_nuvem(caminho):
    """True se o OneDrive ainda nao baixou o conteudo deste arquivo."""
    try:
        atributos = getattr(os.stat(caminho), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(atributos & (RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS))


def onedrive_de_pe():
    """
    True/False se o OneDrive esta rodando, None se nao deu para saber.

    None e diferente de False de proposito: avisar que o OneDrive caiu
    quando na verdade nao se conseguiu perguntar e o tipo de alarme
    falso que ensina o operador a ignorar alarme.
    """
    try:
        saida = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OneDrive.exe"],
                               capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    return "OneDrive.exe" in (saida.stdout or "")


def arquivos_da_caixa(origem):
    r"""
    [(caminho, rotulo)] de tudo na caixa, INCLUSIVE dentro das subpastas.

    O cliente organiza como quiser - uma pasta 'santinhos' com oito
    dentro -, e aquilo e trabalho igual ao que esta solto. O monitor ja
    desce assim na pasta do dia; a ponte lia so o primeiro nivel, e uma
    pasta postada sumia inteira sem uma linha no log.

    'rotulo' e o caminho a partir da caixa ('santinhos\GRADE 40.pdf'),
    para o aviso dizer ONDE o arquivo estava. O nome que vai para a
    pasta do dia e so o do arquivo: a subpasta e organizacao de quem
    manda, nao faz parte do servico.
    """
    def reclamar(erro):
        log("Teams: nao consegui ler %s: %s"
            % (getattr(erro, "filename", "?"), erro), alerta=True)

    achados = []
    for raiz, pastas, arquivos in os.walk(origem, onerror=reclamar):
        pastas[:] = sorted(p for p in pastas if not ignorada(p))
        for nome in sorted(arquivos):
            caminho = os.path.join(raiz, nome)
            achados.append((caminho, os.path.relpath(caminho, origem)))
    return achados


def atravessa(nome):
    """True se este nome de arquivo interessa a ponte."""
    if nome.startswith("~"):
        return False               # sobra de copia, dos dois lados
    return nome.lower().endswith(EXTENSOES_QUE_ATRAVESSAM)


def chave_da_ponte(caminho, rotulo):
    r"""
    A chave do registro da ponte: inclui ONDE o arquivo estava na caixa.

    O chave_arquivo() comum e nome|tamanho|data, e isso basta na pasta
    do dia - la nao ha dois arquivos com o mesmo nome. Na CAIXA ha,
    desde que a ponte passou a descer nas subpastas e achatar tudo:
    'manha\grade.pdf' e 'tarde\grade.pdf' sao dois servicos diferentes.

    Se a chave fosse so o nome, duas artes diferentes do mesmo tamanho,
    sincronizadas no mesmo segundo, dariam a MESMA chave - e a segunda
    seria descartada como 'ja trazida', sem uma linha no log. Um teste
    pegou isso antes de a producao pegar.
    """
    st = os.stat(caminho)
    return "%s|%d|%d" % (rotulo, st.st_size, int(st.st_mtime))


# ----------------------------------------------------------------------
# Registro do que ja atravessou
# ----------------------------------------------------------------------
# Proprio, separado do registro das chapas. Sao duas perguntas
# diferentes: 'ja trouxe este arquivo do Teams?' e 'ja gravei esta arte
# em chapa?'. Misturar as duas faria uma chapa refeita a mao parecer
# arquivo novo do cliente, e vice-versa.

def caminho_registro():
    return os.path.join(PASTA_CONTROLE, REGISTRO_TEAMS)


def carregar_trazidos():
    try:
        with io.open(caminho_registro(), encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return {}


def salvar_trazidos(reg):
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    with io.open(caminho_registro(), "w", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False, indent=1))


# ----------------------------------------------------------------------
# A travessia
# ----------------------------------------------------------------------

def pasta_destino_do_dia(base):
    r"""
    <base>\<MES>\<DIA> de hoje, CRIANDO o que faltar.

    O monitor.py so espera a pasta do dia aparecer; aqui ela e criada.
    A diferenca e proposital: quando o arquivo chega as 7h da manha e
    ninguem abriu a pasta do dia ainda, ele precisa ter onde cair.

    O dia e o de HOJE, e nao o dia em que o cliente postou. Arquivo de
    sabado cai na pasta de segunda, e esta certo: 'pasta do dia' aqui
    quer dizer o dia em que se TRABALHA aquilo. Quando ele postou fica
    guardado na data do proprio arquivo, que o copy2 preserva.
    """
    mes = localizar_pasta_mes(base, criar=True)
    destino = os.path.join(base, mes, pasta_do_dia())
    os.makedirs(destino, exist_ok=True)
    return destino


def destino_livre(pasta, nome):
    """Caminho que ainda nao existe: X.pdf, X_v2.pdf, X_v3.pdf..."""
    base, ext = os.path.splitext(nome)
    alvo = os.path.join(pasta, nome)
    n = 2
    while os.path.exists(alvo):
        alvo = os.path.join(pasta, "%s_v%d%s" % (base, n, ext))
        n += 1
    return alvo


def copiar_inteiro(origem, alvo):
    """
    Copia sem nunca deixar arquivo pela metade com o nome final.

    Escreve num nome temporario comecado por '~' - que o monitor.py
    ignora, por ser o feitio dos backups do Corel - e so entao renomeia.
    Sem isso, o monitor poderia pegar o PDF no meio da copia e gravar
    chapa de arte incompleta.
    """
    parcial = os.path.join(os.path.dirname(alvo),
                           "~" + os.path.basename(alvo) + ".parcial")
    try:
        shutil.copy2(origem, parcial)
        os.replace(parcial, alvo)
    except Exception:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise
    return alvo


def trazer(origem, base, trazidos, avisados=None, cliente=None, rotulo=None):
    """
    Traz UM arquivo para a pasta do dia. True se algo novo atravessou.

    Devolve False - sem barulho - para tudo que ainda nao esta pronto:
    arquivo so na nuvem, arquivo ainda chegando, arquivo ja trazido
    antes. A ponte roda a cada poucos segundos; o que nao passou agora
    passa na proxima.
    """
    avisados = set() if avisados is None else avisados
    nome = os.path.basename(origem)

    if not atravessa(nome):
        return False
    try:
        chave = chave_da_ponte(origem, rotulo or nome)
    except OSError:
        return False
    if chave in trazidos:
        return False

    if so_na_nuvem(origem):
        if chave not in avisados:
            avisados.add(chave)
            log("Teams: '%s' ainda esta so na nuvem. Espero o OneDrive "
                "baixar." % nome)
        return False
    if not arquivo_estavel(origem):
        return False

    destino = pasta_destino_do_dia(base)
    alvo = os.path.join(destino, nome)

    if os.path.exists(alvo):
        # Ja tem arquivo com este nome na pasta do dia. Ou e o mesmo -
        # alguem salvou a mao, o cliente repostou, ou veio de outra
        # subpasta da caixa - ou o cliente mandou uma CORRECAO com o
        # nome antigo. Os dois casos parecem iguais de fora e terminam
        # muito diferente.
        try:
            mesmo = impressao_digital(origem) == impressao_digital(alvo)
        except OSError:
            return False
        if mesmo:
            trazidos[chave] = {"nome": nome, "destino": alvo,
                               "ja_estava_la": True}
            salvar_trazidos(trazidos)
            log("Teams: '%s' ja estava na pasta do dia, igualzinho. Nao "
                "copiei de novo." % nome)
            return False
        # Conteudo diferente com o mesmo nome: NAO sobrescreve. Guarda ao
        # lado e chama gente. Sobrescrever aqui seria trocar a arte
        # debaixo de uma chapa que talvez ja tenha sido gravada.
        alvo = destino_livre(destino, nome)
        anotar_pendencia(nome,
                         "chegou pelo Teams uma versao DIFERENTE de um "
                         "arquivo que ja estava na pasta do dia. Nao "
                         "sobrescrevi: guardei como '%s'. Veja qual das "
                         "duas vale antes de gravar chapa"
                         % os.path.basename(alvo), cliente)

    try:
        copiar_inteiro(origem, alvo)
    except OSError as e:
        # Quase sempre e o OneDrive tentando baixar sem internet.
        if chave not in avisados:
            avisados.add(chave)
            log("Teams: nao consegui trazer '%s': %s" % (nome, e), alerta=True)
        return False

    trazidos[chave] = {"nome": nome, "destino": alvo}
    salvar_trazidos(trazidos)
    log("Teams -> %s" % alvo)
    return True


def pendentes(trazidos):
    """
    [(cliente, caminho, rotulo)] do que atravessaria agora, sem trazer nada.

    Olhar sem tocar: e o que permite DIZER o que vai entrar antes de
    entrar. So enxerga o que ja esta baixado - arquivo ainda na nuvem
    nao conta, porque nao ha como saber se ele vai descer a tempo.
    """
    fila = []
    for cliente, origem, _base in caixas():
        if not os.path.isdir(origem):
            continue
        for caminho, rotulo in arquivos_da_caixa(origem):
            if not atravessa(os.path.basename(caminho)):
                continue
            try:
                chave = chave_da_ponte(caminho, rotulo)
            except OSError:
                continue
            if chave in trazidos or so_na_nuvem(caminho):
                continue
            fila.append((cliente, caminho, rotulo))
    return fila


def anunciar_rajada(trazidos, esperar=True):
    """
    Diz o que vai entrar, e segura, quando muita coisa esperou junto.

    O programa nao e servico: roda enquanto a janela esta aberta. O que
    o cliente postar no fim de semana espera ali, e entra TODO na
    segunda de manha, no minuto em que alguem abre o programa - cada
    arquivo abrindo OS no GEREMPRE de producao, dando baixa de chapa no
    estoque de verdade e imprimindo prova na Konica.

    Antes da ponte isso nao existia: o operador salvava um por um e via
    cada um antes de entrar. Aqui esse olhar volta como um aviso e uma
    pausa - tempo de Ctrl+C se algo estiver obviamente errado.

    Nao pede confirmacao de proposito. Botao de confirmar vira reflexo
    depois de duas semanas, e ai protege menos que nada.

    Devolve quantos estao esperando.
    """
    fila = pendentes(trazidos)
    if len(fila) < RAJADA:
        return len(fila)

    log("")
    log("%d arquivos esperando no Teams. Vao entrar TODOS agora:"
        % len(fila), alerta=True)
    for cliente, _caminho, rotulo in fila:
        log("   %-8s %s" % (cliente, rotulo), alerta=True)
    log("Cada um abre OS no GEREMPRE, da baixa de chapa e imprime prova.",
        alerta=True)
    if esperar and ESPERA_RAJADA > 0:
        log("Comeco em %d segundos. Ctrl+C agora se algo estiver errado."
            % ESPERA_RAJADA, alerta=True)
        time.sleep(ESPERA_RAJADA)
    return len(fila)


def conferir_no_arranque():
    """
    Avisa, uma vez, o que impediria a ponte de andar.

    Roda no arranque do monitor, quando ainda ha alguem olhando a tela.
    """
    lista = caixas()
    if not lista:
        return

    if onedrive_de_pe() is False:
        log("Teams: o OneDrive NAO esta rodando nesta maquina. Nada vai "
            "atravessar ate ele subir.", alerta=True)

    for cliente, origem, _base in lista:
        if not os.path.isdir(origem):
            log("Teams: a pasta do %s NAO existe: %s" % (cliente, origem),
                alerta=True)
            log("       Sincronize a biblioteca do time no OneDrive, ou "
                "corrija PASTA_TEAMS/CAIXAS_TEAMS.", alerta=True)


def rodada(trazidos=None, avisados=None):
    """
    Uma passada por todas as caixas. Devolve quantos arquivos vieram.

    E chamada de dentro do laco do monitor.py, e nao num programa
    separado, para haver UMA janela e UM log: quem ve a chapa sair ve
    tambem de onde o arquivo veio.
    """
    lista = caixas()
    if not lista:
        return 0
    trazidos = carregar_trazidos() if trazidos is None else trazidos
    avisados = set() if avisados is None else avisados

    vieram = 0
    for cliente, origem, base in lista:
        if not os.path.isdir(origem):
            # Configurado mas sem pasta: OneDrive parado, deslogado, ou
            # caminho errado. Reclama UMA vez e segue - calar aqui e
            # deixar o dia inteiro parecer 'o cliente nao mandou nada'.
            marca = "sem pasta|" + origem
            if marca not in avisados:
                avisados.add(marca)
                log("Teams: a pasta do %s sumiu: %s" % (cliente, origem),
                    alerta=True)
            continue
        for caminho, rotulo in arquivos_da_caixa(origem):
            if os.path.isfile(caminho) and trazer(caminho, base, trazidos,
                                                  avisados, cliente, rotulo):
                vieram += 1
    return vieram
