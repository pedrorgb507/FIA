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
"""

import io
import json
import os
import shutil

from .config import (BASE_ENTRADA, BASE_ENTRADA_CREATIVE, BASE_ENTRADA_EMPORIO,
                     BASE_ENTRADA_FIALHO, BASE_ENTRADA_VIVA,
                     BASE_ENTRADA_VOPRIX, EXTENSOES_DE_ARTE, PASTA_CONTROLE,
                     PASTA_TEAMS, REGISTRO_TEAMS)
from .utils import (anotar_pendencia, arquivo_estavel, chave_arquivo,
                    impressao_digital, localizar_pasta_mes, log, pasta_do_dia)


# O que vale a pena atravessar a ponte. E mais largo do que o cliente
# costuma mandar, de proposito: um .cdr da SOLIDA nao vira chapa, mas
# precisa CHEGAR na pasta para o monitor.py transformar em pendencia.
# Arquivo de arte que fica preso do lado de ca e servico que ninguem
# lembra de fazer - e aqui ninguem sequer veria que ele existe.
EXTENSOES_QUE_ATRAVESSAM = (".pdf",) + EXTENSOES_DE_ARTE

# Sinais de que o OneDrive ainda nao baixou o arquivo: ele aparece no
# diretorio, com o tamanho certo, mas o conteudo continua na nuvem. Ler
# um desses dispara o download - que trava se a internet estiver fora.
# Melhor enxergar e esperar do que abrir e pendurar o programa.
RECALL_ON_OPEN = 0x00040000
RECALL_ON_DATA_ACCESS = 0x00400000


def caixas():
    r"""
    (cliente, pasta_de_origem, base_de_destino) de cada caixa vigiada.

    A pasta de origem tem o NOME DO CLIENTE dentro de PASTA_TEAMS. Quem
    nao tiver base configurada fica de fora - e quem nao tiver a pasta
    criada ainda tambem, sem reclamacao: o cliente pode entrar no Teams
    hoje e so postar semana que vem.
    """
    if not PASTA_TEAMS:
        return []
    bases = [("SOLIDA", BASE_ENTRADA),
             ("VOPRIX", BASE_ENTRADA_VOPRIX),
             ("FIALHO", BASE_ENTRADA_FIALHO),
             ("EMPORIO", BASE_ENTRADA_EMPORIO),
             ("VIVA", BASE_ENTRADA_VIVA),
             ("CREATIVE", BASE_ENTRADA_CREATIVE)]
    lista = []
    for cliente, base in bases:
        if not base:
            continue
        origem = os.path.join(PASTA_TEAMS, cliente)
        if os.path.isdir(origem):
            lista.append((cliente, origem, base))
    return lista


def so_na_nuvem(caminho):
    """True se o OneDrive ainda nao baixou o conteudo deste arquivo."""
    try:
        atributos = getattr(os.stat(caminho), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(atributos & (RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS))


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


def trazer(origem, base, trazidos, avisados=None):
    """
    Traz UM arquivo para a pasta do dia. True se algo novo atravessou.

    Devolve False - sem barulho - para tudo que ainda nao esta pronto:
    arquivo so na nuvem, arquivo ainda chegando, arquivo ja trazido
    antes. A ponte roda a cada poucos segundos; o que nao passou agora
    passa na proxima.
    """
    avisados = set() if avisados is None else avisados
    nome = os.path.basename(origem)

    if not nome.lower().endswith(EXTENSOES_QUE_ATRAVESSAM):
        return False
    if nome.startswith("~"):
        return False
    try:
        chave = chave_arquivo(origem)
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
        # alguem salvou a mao, ou o cliente repostou o de sempre - ou o
        # cliente mandou uma CORRECAO com o nome antigo. Os dois casos
        # parecem iguais de fora e terminam muito diferente.
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
                         % os.path.basename(alvo))

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
    for _cliente, origem, base in lista:
        try:
            nomes = sorted(os.listdir(origem))
        except OSError as e:
            log("Teams: nao consegui ler %s: %s" % (origem, e), alerta=True)
            continue
        for nome in nomes:
            caminho = os.path.join(origem, nome)
            if os.path.isfile(caminho) and trazer(caminho, base, trazidos,
                                                  avisados):
                vieram += 1
    return vieram
