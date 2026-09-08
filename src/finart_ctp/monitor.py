# -*- coding: utf-8 -*-
"""Laco principal: vigia a pasta do dia de cada cliente e manda o que aparecer."""

import os
import sys
import time
from datetime import datetime

from .config import (AVISAR_ARQUIVO_PARADO, BASE_CTP, BASE_ENTRADA,
                     BASE_ENTRADA_EMPORIO,
                     BASE_ENTRADA_FIALHO, BASE_ENTRADA_VIVA,
                     BASE_ENTRADA_VOPRIX, ESPERA_IMPRESSORA, IMPRESSORA,
                     INTERVALO, PASTA_CONTROLE, SUBPASTA_SAIDA)
from .ghostscript import GS
from .processador import EMPORIO, FIALHO, SOLIDA, VIVA, VOPRIX, processar
from .nomes import e_backup_do_corel
from .utils import (anotar_pendencia, arquivo_estavel, carregar_registro,
                    chave_arquivo,
                    impressao_digital, localizar_pasta_mes, log,
                    mesmo_trabalho_ja_feito, pasta_do_dia, quem_esta_rodando,
                    salvar_registro, travar_instancia_unica)


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
        lista.append((VOPRIX, BASE_ENTRADA_VOPRIX, (".cdr",)))
    if BASE_ENTRADA_FIALHO:
        lista.append((FIALHO, BASE_ENTRADA_FIALHO, (".pdf", ".cdr")))
    if BASE_ENTRADA_EMPORIO:
        lista.append((EMPORIO, BASE_ENTRADA_EMPORIO, (".pdf",)))
    if BASE_ENTRADA_VIVA:
        lista.append((VIVA, BASE_ENTRADA_VIVA, (".pdf", ".cdr")))
    return lista


def avisar_arquivo_parado(caminho, nome, parados):
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
    anotar_pendencia(nome, motivo)


def pasta_entrada_do_dia(base):
    r"""<base>\<MES>\<DIA> de hoje, ou None se a pasta ainda nao existe."""
    mes = localizar_pasta_mes(base)
    if not mes:
        return None
    entrada = os.path.join(base, mes, pasta_do_dia())
    return entrada if os.path.isdir(entrada) else None


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
           extensoes=(".pdf",), adiados=None, parados=None):
    """
    Processa o que ainda nao foi feito. Devolve quantos rodaram.

    Se a impressora estiver fora, nada e gerado: a varredura para e so
    volta a tentar depois de ESPERA_IMPRESSORA segundos.

    'adiados' guarda os arquivos que estao abertos no CorelDRAW do
    operador, so para o aviso nao se repetir a cada varredura.
    'parados' faz o mesmo com os que nao terminam de chegar.
    """
    espera = {"ate": 0, "avisado": False} if espera is None else espera
    if time.time() < espera["ate"]:
        return 0
    adiados = set() if adiados is None else adiados
    parados = {} if parados is None else parados

    feitos = 0
    for nome in sorted(os.listdir(entrada)):
        if not nome.lower().endswith(tuple(extensoes)) or nome.startswith("~"):
            continue
        if e_backup_do_corel(nome):
            continue          # copia de seguranca do Corel nao e trabalho
        caminho = os.path.join(entrada, nome)
        if not os.path.isfile(caminho):
            continue
        try:
            chave = chave_arquivo(caminho)
        except OSError:
            continue
        if chave in registro:
            continue
        # Outro programa pode ter feito este arquivo enquanto estavamos
        # ocupados com o anterior - uma separacao leva minutos. Reler o
        # registro custa quase nada e evita chapa duplicada.
        registro.update(carregar_registro())
        if chave in registro:
            continue
        if not arquivo_estavel(caminho):
            # Ainda chegando - ou salvo com 0 byte e parado ali. Nao
            # encosto, mas depois de um tempo aviso: chapa que nao sai
            # sem ninguem saber e pior do que chapa que da erro.
            avisar_arquivo_parado(caminho, nome, parados)
            continue
        parados.pop(caminho, None)

        # A data mudou mas a arte e a mesma? Entao nao ha trabalho novo:
        # so anota a chave nova apontando para as chapas que ja existem.
        # Sem isto, arte regravada por cima sai duas vezes no CTP.
        igual = mesmo_trabalho_ja_feito(registro, caminho)
        if igual is not None:
            log("'%s' voltou para a pasta com data nova, mas e a MESMA arte "
                "de %s. Nao refiz: ja saiu como %s"
                % (nome, igual.get("quando", "antes"),
                   ", ".join(igual.get("saidas") or []) or "nada"))
            registro[chave] = dict(igual, regravado=True)
            salvar_registro(registro)
            continue

        resultado = processar(caminho, saida, cliente)

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
        feitos += 1
    return feitos


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
        print("Nao achei nenhuma pasta de entrada:")
        for nome, base, _ in vigiadas:
            print("    %-7s %s" % (nome, base))
        print("Confira o config_local.py (ou o config.py).")
        sys.exit(1)

    log("Ghostscript: %s" % GS)
    for nome, base, exts in vigiadas:
        log("Entrada %-7s %s  (%s)" % (nome, base, " ".join(exts)))
    log("Saida:   %s" % BASE_CTP)
    log("Os originais NAO sao movidos. Controle em %s" % PASTA_CONTROLE)
    log("Deixe esta janela aberta. Ctrl+C para parar.")

    registro = carregar_registro()
    log("Registro: %d arquivo(s) ja processados antes." % len(registro))
    espera = {"ate": 0, "avisado": False}
    adiados = set()
    parados = {}

    ultima = {}
    while True:
        try:
            for nome, base, exts in vigiadas:
                entrada = pasta_entrada_do_dia(base)
                if not entrada:
                    if ultima.get(nome) != "sem_pasta":
                        ultima[nome] = "sem_pasta"
                        log("%s: esperando a pasta do dia aparecer em %s"
                            % (nome, base))
                    continue

                saida = pasta_saida_do_dia()
                if ultima.get(nome) != entrada:
                    ultima[nome] = entrada
                    log("--- Vigiando %s: %s ---" % (nome, entrada))
                    log("--- Gravando em: %s ---" % saida)

                varrer(entrada, saida, registro, espera, nome, exts,
                       adiados, parados)
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("Encerrado.")
            break
        except Exception as e:
            log("Erro no laco principal: %s" % e, alerta=True)
            time.sleep(INTERVALO)
