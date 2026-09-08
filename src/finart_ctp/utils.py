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
                     REGISTRO)


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


# ----------------------------------------------------------------------
# Log
# ----------------------------------------------------------------------

def log(msg, alerta=False):
    r"""Imprime na tela e grava em <PASTA_CONTROLE>\_log_ctp.txt."""
    linha = "[%s] %s%s" % (datetime.now().strftime("%d/%m %H:%M:%S"),
                           ">>> " if alerta else "", msg)
    print(linha, flush=True)
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_log_ctp.txt"), "a",
                  encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def anotar_pendencia(arquivo, motivo):
    """
    Registra um problema que precisa de gente.

    Fica no PC, junto do log, e NAO na pasta do CTP: la so entram as
    chapas. Alem de gravar, imprime um aviso grande na tela, para nao
    passar batido em quem esta olhando a janela do programa.
    """
    barra = "!" * 66
    print("")
    print(barra, flush=True)
    print("!!!  PENDENCIA - PRECISA DE VOCE", flush=True)
    print("!!!  arquivo: %s" % arquivo, flush=True)
    print("!!!  motivo : %s" % motivo, flush=True)
    print(barra, flush=True)
    print("")
    log("PENDENCIA: %s | %s" % (arquivo, motivo), alerta=True)
    anotar_no_arquivo(arquivo, motivo)


def anotar_no_arquivo(arquivo, motivo):
    """Uma linha no _PENDENCIAS.txt, sem o alarde na tela."""
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_PENDENCIAS.txt"), "a",
                  encoding="utf-8") as f:
            f.write("%s | %s | %s" % (datetime.now().strftime("%d/%m %H:%M"),
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


def mesmo_trabalho_ja_feito(registro, caminho):
    """
    A entrada do registro que ja fez ESTE MESMO arquivo, ou None.

    Serve para o caso em que a arte e regravada na pasta sem mudar: o
    cliente manda de novo, o Windows copia por cima, e so a data de
    modificacao muda. A chave e nome|tamanho|data, entao o arquivo passa
    a valer como novo e a chapa sai duas vezes.

    Aconteceu em 08/09/2026 com o '49694 - Gaspar - colinha.pdf': as
    08:36:18 comecou a primeira, as 08:37:16 comecou a segunda, e o CTP
    ficou com 49694.pdf e 49694_v2.pdf identicas byte a byte - 12,4 MB
    cada. A diferenca entre as duas chaves eram 12 segundos de data.

    So compara o conteudo quando ha motivo: mesmo nome e mesmo tamanho.
    Fora disso nem abre o arquivo - a pasta e de rede e a varredura passa
    a cada 5 segundos.
    """
    nome = os.path.basename(caminho)
    try:
        tamanho = os.path.getsize(caminho)
    except OSError:
        return None

    candidatas = [e for chave, e in registro.items()
                  if chave.startswith("%s|%d|" % (nome, tamanho))
                  and e.get("impressao")]
    if not candidatas:
        return None

    try:
        atual = impressao_digital(caminho)
    except OSError:
        return None
    for entrada in candidatas:
        if entrada.get("impressao") == atual:
            return entrada
    return None


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


def arquivo_estavel(caminho):
    """True se o arquivo parou de crescer (terminou de copiar pela rede)."""
    try:
        a = os.path.getsize(caminho)
        time.sleep(2)
        return a == os.path.getsize(caminho) and a > 0
    except OSError:
        return False


def nome_livre(pasta, base):
    """Caminho de saida que ainda nao existe: X.pdf, X_v2.pdf, X_v3.pdf..."""
    alvo = os.path.join(pasta, base + ".pdf")
    n = 2
    while os.path.exists(alvo):
        alvo = os.path.join(pasta, "%s_v%d.pdf" % (base, n))
        n += 1
    return alvo
