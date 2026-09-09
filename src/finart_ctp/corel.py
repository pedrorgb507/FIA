# -*- coding: utf-8 -*-
"""
Conversao de .cdr para PDF, usando o proprio CorelDRAW.

Por que a Corel e nao um conversor de terceiros: quem exporta e o motor
da propria Corel, entao cor especial, sobreimpressao, sangria e fonte
saem como no arquivo. Um conversor livre sai "parecido", e parecido nao
serve para gravar chapa.

CUIDADO - a automacao NAO abre uma instancia nova: ela se conecta a
sessao do CorelDRAW que estiver aberta na maquina, a do operador. Duas
regras nasceram de erro cometido:

  1. nunca mexer em Visible (ja escondemos a janela de alguem)
  2. nunca fechar documento que nao fomos nos que abrimos

A regra 2 e a mais importante. O OpenDocument de um arquivo JA ABERTO
devolve o documento do operador; fechar aquilo joga fora o trabalho dele
sem perguntar. Por isso, arquivo aberto na sessao nao e convertido: fica
para a proxima passada, quando a pessoa tiver fechado.

O operador vai ver o arquivo piscar na tela durante a conversao. E o
preco combinado de dividir a maquina.
"""

import os

from .config import (COREL_CMYK, PDF_CORELDRAW, PDF_CORELDRAW_PREDEFINICAO)

PROGID = "CorelDRAW.Application"


class ArquivoEmUso(Exception):
    """O .cdr esta aberto no CorelDRAW do operador."""


def _aplicacao():
    """A sessao do CorelDRAW da maquina. Abre uma se nao houver nenhuma."""
    import win32com.client
    return win32com.client.Dispatch(PROGID)


def disponivel():
    """True se der para falar com o CorelDRAW nesta maquina."""
    try:
        _aplicacao()
        return True
    except Exception:
        return False


def _documento_aberto(app, caminho):
    """O documento do operador, se este arquivo ja estiver aberto."""
    alvo = os.path.normcase(os.path.abspath(caminho))
    try:
        total = app.Documents.Count
    except Exception:
        return None
    for i in range(1, total + 1):
        try:
            doc = app.Documents.Item(i)
            if os.path.normcase(doc.FullFileName) == alvo:
                return doc
        except Exception:
            continue
    return None


def carregar_predefinicao(doc, nome=PDF_CORELDRAW_PREDEFINICAO):
    """
    Carrega pelo NOME a predefinicao da janela de Publicar em PDF.

    Sem isto vale o que estiver marcado na janela naquele dia - e a
    janela e a mesma que o operador usa a mao. Predefinicao se pede, nao
    se herda, pela mesma razao que frente e verso se pede na impressora.

    Depois de carregar, CONFERE a cor de saida. Nao e formalidade: com a
    predefinicao em RGB, o preto cheio deste mesmo arquivo sai como
    RGB 0.216 0.204 0.208 - cinza escuro - e nenhuma etapa adiante
    desfaz isso. Fora do CMYK a conversao PARA.
    """
    if not nome:
        return
    ajustes = doc.PDFSettings
    try:
        ajustes.Load(nome)
    except Exception as e:
        raise RuntimeError(
            "o CorelDRAW nao achou a predefinicao de PDF '%s' (%s). Nao "
            "converto: sem ela vale o que estiver marcado na janela, e "
            "ninguem sabe o que esta marcado" % (nome, str(e)[:80]))

    modo = getattr(ajustes, "ColorMode", None)
    if modo != COREL_CMYK:
        raise RuntimeError(
            "a predefinicao '%s' esta saindo em modo de cor %s, e nao em "
            "CMYK (%d). Nao converto: chapa se grava em CMYK e o que sair "
            "fora dele nao volta" % (nome, modo, COREL_CMYK))


def ajustar_pdf(doc):
    """
    Exige do CorelDRAW os ajustes do PDF_CORELDRAW, em vez de herdar.

    O PublishToPDF usa o que estiver marcado na janela de Publicar em PDF
    da maquina - e o que estava marcado gravava bitmap CRU: um .cdr de
    13 MB virou PDF de 1007 MB, sendo 1006 MB de imagem sem compactar.

    Devolve o que NAO deu para ajustar, para o chamador avisar. Versao de
    Corel diferente pode nao ter alguma dessas propriedades, e isso nao e
    motivo para deixar de converter.
    """
    ajustes = doc.PDFSettings
    faltaram = []
    for nome, valor in PDF_CORELDRAW.items():
        try:
            setattr(ajustes, nome, valor)
            conferido = getattr(ajustes, nome)
            # nao basta mandar: tem versao de Corel que aceita a atribuicao
            # e continua com o valor antigo
            if conferido != valor:
                faltaram.append("%s (pedi %s, ficou %s)"
                                % (nome, valor, conferido))
        except Exception:
            faltaram.append(nome)
    return faltaram


def publicar_pdf(cdr, destino):
    """
    Abre o .cdr e publica em PDF. Devolve o caminho do PDF.

    Levanta ArquivoEmUso se o arquivo estiver aberto na sessao do
    operador: nesse caso nao mexemos nele de jeito nenhum.
    """
    cdr = os.path.abspath(cdr)
    destino = os.path.abspath(destino)
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    app = _aplicacao()
    if _documento_aberto(app, cdr) is not None:
        raise ArquivoEmUso("'%s' esta aberto no CorelDRAW"
                           % os.path.basename(cdr))

    doc = app.OpenDocument(cdr)
    try:
        # A ORDEM IMPORTA. A predefinicao vem primeiro, e e ela que manda
        # em cor, sobreimpressao e sangria - o que o operador ajustou.
        # Os ajustes do PDF_CORELDRAW vem DEPOIS, por cima, e sao dois
        # tipos de coisa que a predefinicao nao tem por que carregar:
        #
        #   compressao SEM PERDA - a FINART guarda bitmap cru. Neste
        #   mesmo arquivo deu 1,2 MB contra 0,6 MB com ZIP, e ja houve
        #   .cdr de 13 MB virar PDF de 1007 MB. Agora esse PDF atravessa
        #   a rede ate o CTP, entao o peso conta em dobro. Foi medido que
        #   o arquivo sai IGUAL: mesma cobertura de tinta na quinta casa;
        #
        #   reamostragem DESLIGADA - rede de seguranca. A FINART ja vem
        #   com as tres desligadas; forcar aqui e o que impede que uma
        #   edicao futura na janela do operador reamostre a arte para
        #   300 dpi sem ninguem perceber.
        carregar_predefinicao(doc)
        faltaram = ajustar_pdf(doc)
        # Compressao que nao pegou custa espaco em disco. Reamostragem que
        # nao pegou custa a TIRAGEM: sai arte de 300 dpi gravada numa chapa
        # de 1000, borrada, e ninguem ve antes de imprimir. Essa nao passa.
        criticos = [f for f in faltaram if f.startswith("Downsample")]
        if criticos:
            raise RuntimeError(
                "o CorelDRAW nao aceitou desligar a reamostragem (%s). "
                "Nao converto: a arte sairia em 300 dpi sem aviso"
                % ", ".join(criticos))
        doc.PublishToPDF(destino)
    finally:
        try:
            doc.Close()          # fechamos apenas o que nos abrimos
        except Exception:
            pass

    if not os.path.exists(destino):
        raise RuntimeError("CorelDRAW nao gerou o PDF de '%s'"
                           % os.path.basename(cdr))
    return destino
