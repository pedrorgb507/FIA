# -*- coding: utf-8 -*-
r"""
Fecha o que estiver na pasta PARA CTP da AMERICA. ESCREVE EM PRODUCAO.

O caminho da AMERICA e diferente dos outros seis clientes: o arquivo dela
chega POR MONTAR. Quem monta e a casa, e a montagem e revisada por gente
antes de virar chapa. Por isso existe o portao:

    V:\AMERICA\<Mes>\<Dia>\             <- o arquivo chega. NAO se toca.
    V:\AMERICA\<Mes>\<Dia>\PARA CTP\    <- so o que esta aqui e fechado.

Este programa cuida do que vem DEPOIS do portao:

    1. le a chapa e mede o que ela tem (tamanho e tintas);
    2. monta o nome pelo protocolo da casa;
    3. GARANTE QUE HA COPIA GUARDADA na pasta do dia;
    4. grava no CTP e CONFERE que chegou inteira;
    5. abre a OS no GEREMPRE, com o razao conferido dos dois lados;
    6. imprime a prova;
    7. so entao APAGA da PARA CTP.

SOBRE O PASSO 7, que e o unico irreversivel:

O operador pediu para apagar, e a razao dele e boa - a PARA CTP e caixa
de entrada, e caixa de entrada que acumula vira deposito, e o servidor
enche. Mas apagar e para sempre, entao o apagar so acontece com TRES
coisas provadas antes:

  - a chapa esta no CTP, do mesmo tamanho em bytes, e abre como PDF;
  - existe copia na pasta do dia, que e o arquivo da casa. Se o operador
    tiver MOVIDO em vez de copiado, este programa devolve a copia para
    la ANTES de apagar - assim nenhuma montagem se perde;
  - nada deu errado nos passos anteriores.

Faltando qualquer uma, o arquivo FICA. Pesar o disco e problema; perder
montagem revisada e pior.
"""

import os
import shutil
from datetime import datetime

import pypdf

from . import gerempre
from .ghostscript import cobertura_por_pagina, tintas_da_cobertura
from .nomes import cores_no_nome, finalizar
from .utils import (arquivo_estavel, carregar_registro, chave_arquivo, log,
                    salvar_registro)

CLIENTE = "AMERICA"
BASE_AMERICA = r"V:\AMERICA"
PORTAO = "PARA CTP"
MM = 72.0 / 25.4


def pasta_do_dia_america(quando=None):
    """(pasta_do_dia, pasta_do_portao) da AMERICA, ou (None, None)."""
    # importado aqui dentro porque o monitor importa ESTE modulo - por
    # cima, os dois se importariam em circulo e nenhum carregaria
    from .monitor import localizar_pasta_mes, pasta_do_dia
    mes = localizar_pasta_mes(BASE_AMERICA)
    if not mes:
        return None, None
    dia = os.path.join(BASE_AMERICA, mes, pasta_do_dia())
    if not os.path.isdir(dia):
        return None, None
    return dia, os.path.join(dia, PORTAO)


def medir(pdf):
    """(largura_mm, altura_mm, tintas) da chapa."""
    pag = pypdf.PdfReader(pdf).pages[0]
    larg = float(pag.mediabox.width) / MM
    alt = float(pag.mediabox.height) / MM
    cob = cobertura_por_pagina(pdf, sem_icc=True)
    tintas = tintas_da_cobertura(cob[0]) if cob else set("CMYK")
    return larg, alt, tintas


def e_preto_e_branco(tintas):
    """Uma cor so, ou cinza. O 'peb' do operador."""
    return tintas <= {"GRAY", "GREY", "K"} or len(tintas) <= 1


def maquina_da_america(maior_lado, tintas):
    """
    (largura, altura) da chapa que recebe este trabalho.

    Regra do operador: ate o formato 4 vai na PM_52; acima dele, colorido
    vai na SM_74 e preto-e-branco vai na MOZP. E a escolha de MAQUINA -
    quem manda e o tamanho do trabalho e a cor, nao o contrario.

    Serve para a FIA saber em que chapa MONTAR. Quando o arquivo ja chega
    montado, quem manda e o tamanho dele; esta funcao vira conferencia.
    """
    from .config import (AMERICA_F4, AMERICA_GRANDE_COR, AMERICA_GRANDE_PB,
                         MAIOR_LADO_F4)
    if maior_lado <= MAIOR_LADO_F4:
        return AMERICA_F4
    return AMERICA_GRANDE_PB if e_preto_e_branco(tintas) else AMERICA_GRANDE_COR


def nome_da_chapa(origem, larg, alt, tintas):
    """
    '...\\Flyer Semana do Cliente_15x21 (1)_MONTAGEM.pdf'
        -> '525x459_CMYK_AMERICA_Flyer Semana do Cliente_15x21 (1)'

    O protocolo e o mesmo dos outros clientes de formato no nome:
    <formato>_<cores>_<CLIENTE>_<descricao>, e o finalizar() tira acento e
    caractere que o Windows recusa. Foi assim que o 'CRISTAOS.pdf' virou
    '525x459_AMERICA_CRISTAOS' na mao dos operadores.

    O '_MONTAGEM' sai: ele serve para separar a montagem do original
    DENTRO da pasta do cliente, e no CTP nao ha original nenhum com que
    confundir.
    """
    base = os.path.splitext(os.path.basename(origem))[0]
    if base.upper().endswith("_MONTAGEM"):
        base = base[:-len("_MONTAGEM")]
    formato = "%dx%d" % (int(round(larg)), int(round(alt)))
    return finalizar("%s_%s_%s_%s" % (formato, cores_no_nome(tintas) or "K",
                                      CLIENTE, base))


def chegou_inteira(origem, destino):
    """A chapa esta no CTP, do mesmo tamanho, e abre como PDF?"""
    if not os.path.exists(destino):
        return False, "nao esta no CTP"
    if os.path.getsize(destino) != os.path.getsize(origem):
        return False, "tamanho diferente do original"
    try:
        if len(pypdf.PdfReader(destino).pages) < 1:
            return False, "abriu sem pagina"
    except Exception as e:
        return False, "nao abre como PDF: %s" % str(e)[:60]
    return True, ""


def guardar_copia(origem, pasta_dia):
    """
    Garante que a montagem do PORTAO existe na pasta do dia.

    Devolve (caminho_guardado, o_que_fiz), com 'o_que_fiz' em
    'ja_era_a_mesma', 'copiei' ou 'troquei'.

    Se o operador COPIOU para o portao, a mesma ja esta na pasta do dia e
    nada se faz. Se ele MOVEU, a copia volta.

    E SE HOUVER UMA COM O MESMO NOME, MAS DIFERENTE? Aconteceu em
    10/09/2026: a da pasta do dia tinha 7.026.787 bytes e a do portao
    7.015.188 - o operador pos no portao uma versao que nao era a que
    estava guardada. Antes, esta funcao dizia "ja existia" e ia embora;
    la na frente a conferencia comparava as duas, via tamanhos
    diferentes, recusava o apagar, e o arquivo ficava no portao para
    sempre - refeito a cada volta do vigia, IMPRIMINDO DE NOVO toda vez.

    Quem manda e a do PORTAO: e a que o operador revisou e aprovou. Entao
    a antiga e posta de lado com a data no nome - nao se joga fora
    montagem de ninguem - e a do portao passa a ser a guardada.
    """
    guardada = os.path.join(pasta_dia, os.path.basename(origem))
    if not os.path.exists(guardada):
        shutil.copy2(origem, guardada)
        return guardada, "copiei"

    if os.path.getsize(guardada) == os.path.getsize(origem):
        return guardada, "ja_era_a_mesma"

    base, ext = os.path.splitext(guardada)
    selo = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(guardada, "%s (anterior %s)%s" % (base, selo, ext))
    shutil.copy2(origem, guardada)
    return guardada, "troquei"


def fechar(caminho, pasta_dia, con=None, so_olhar=False):
    """Fecha UMA chapa. Devolve um relato do que foi feito."""
    relato = {"arquivo": os.path.basename(caminho), "passos": [],
              "apagado": False, "os": None, "ja_feito": False}

    def passo(texto):
        relato["passos"].append(texto)

    # JA FECHEI ESTE? E a primeira pergunta, e ela e o que separa uma
    # faxina que falhou de um trabalho por fazer. O registro e o mesmo
    # dos outros seis clientes - nome|tamanho|data.
    chave = chave_arquivo(caminho)
    ja = carregar_registro().get(chave)
    if ja and not so_olhar:
        relato["ja_feito"] = True
        passo("JA FECHADO em %s (OS %s, chapa %s). Nao refiz nada."
              % (ja.get("quando", "antes"), ja.get("os", "?"),
                 ", ".join(ja.get("saidas") or []) or "?"))
        # Mas a FAXINA pode ter ficado pela metade - foi o caso em
        # 10/09/2026. Termina-la aqui e seguro: nao abre OS, nao imprime,
        # nao grava chapa. So guarda a copia e tira do portao, que e o
        # que faltava. Sem isto, o arquivo ficaria no portao para sempre,
        # pulado em silencio a cada volta.
        try:
            guardada, o_que_fiz = guardar_copia(caminho, pasta_dia)
            ok, porque = chegou_inteira(caminho, guardada)
            if ok:
                os.remove(caminho)
                relato["apagado"] = True
                passo("faxina terminada agora: tirei do portao (a copia "
                      "esta guardada na pasta do dia)")
            else:
                passo("nao consegui tirar do portao: %s" % porque)
        except Exception as e:
            passo("nao consegui tirar do portao: %s" % str(e)[:70])
        return relato

    larg, alt, tintas = medir(caminho)
    passo("chapa %.0f x %.0f mm, tintas %s"
          % (larg, alt, "".join(sorted(tintas)) or "?"))

    achado = gerempre.chapa_do_servico(CLIENTE, larg, alt)
    if not achado:
        passo("PARO: nao ha chapa cadastrada para %s em %.0fx%.0f"
              % (CLIENTE, larg, alt))
        return relato
    codigo, nome_chapa, preco, tipo = achado
    passo("chapa %s do GEREMPRE: %s, R$ %.2f (%s)"
          % (codigo, nome_chapa, preco, tipo))

    # A regra de maquina concorda com o arquivo que chegou?
    #
    # Se nao concordar, quem manda e o ARQUIVO - ele ja esta montado, e
    # remontar por causa de uma regra seria refazer o trabalho de quem
    # revisou. Mas fica dito: o operador falou "geralmente", e e
    # justamente nos casos fora do geralmente que vale um olho.
    esperada = maquina_da_america(max(larg, alt), tintas)
    medida = tuple(sorted((int(round(larg)), int(round(alt))), reverse=True))
    if medida != esperada:
        passo("ATENCAO: pela regra (%s, %s) este trabalho iria para a "
              "chapa %dx%d, mas o arquivo veio %dx%d. Segui o arquivo."
              % ("maior que F4" if max(larg, alt) > 560 else "ate F4",
                 "peb" if e_preto_e_branco(tintas) else "colorido",
                 esperada[0], esperada[1], medida[0], medida[1]))

    base = nome_da_chapa(caminho, larg, alt, tintas)
    from .monitor import pasta_saida_do_dia
    saida = os.path.join(pasta_saida_do_dia(), base + ".pdf")
    passo("vai para o CTP como: %s.pdf" % base)

    # quantas chapas de METAL: paginas x tintas. Uma pagina em CMYK gasta
    # quatro - e o mesmo OSLAN 4 das OS que a casa ja abriu para a
    # AMERICA nesta chapa.
    paginas = len(pypdf.PdfReader(caminho).pages)
    quantas = paginas * max(1, len(tintas))
    titulo = os.path.splitext(os.path.basename(caminho))[0].upper()
    passo("OS: titulo '%s', %d chapa(s) de metal, R$ %.2f"
          % (titulo[:50], quantas, quantas * preco))

    if so_olhar:
        passo("(so olhando - nada foi escrito)")
        return relato

    # --- 1. a copia guardada, ANTES de qualquer coisa ---
    guardada, o_que_fiz = guardar_copia(caminho, pasta_dia)
    passo("copia na pasta do dia: %s"
          % {"copiei": "devolvida agora",
             "ja_era_a_mesma": "ja existia, e e a mesma",
             "troquei": "havia OUTRA com o mesmo nome - a antiga foi posta "
                        "de lado com a data, e a do portao virou a guardada"
             }[o_que_fiz])
    relato["guardada"] = guardada

    # --- 2. a OS. ESCREVE EM ESTOQUE ---
    servico = {"titulo": titulo[:50], "cliente": CLIENTE,
               "chapa": [larg, alt], "chapas": quantas}
    numero, vaga, o_que_fiz = gerempre.os_do_servico(servico, con=con)
    relato["os"] = numero
    relato["o_que_fiz"] = o_que_fiz
    passo("OS %s, vaga %s (%s)" % (numero, vaga, o_que_fiz))

    # --- 3. a prova, com a OS no verso ---
    try:
        from .processador import _verso_da_os
        from .prova import JaImprimiu, imprimir
        verso = _verso_da_os(numero)
        try:
            _, folhas = imprimir(caminho, etiquetas=["AMERICA PM52"],
                                 verso=verso)
            passo("prova impressa (%d folha%s)"
                  % (folhas, "s" if folhas > 1 else ""))
            relato["prova"] = folhas
        except JaImprimiu as e:
            # A trava pegou: o papel JA saiu. Nao e falha - e a rede
            # embaixo do conserto, funcionando.
            passo("prova NAO repetida: %s" % str(e)[:110])
            relato["prova"] = 0
    except Exception as e:
        # A prova NAO segura a chapa: o papel se reimprime, e a OS ja
        # existe. Mas fica dito, porque e o papel que o operador leva
        # para a maquina.
        passo("AVISO: a prova nao saiu (%s)" % str(e)[:70])
        relato["prova"] = False

    # --- 4. a chapa no CTP ---
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    shutil.copy2(caminho, saida)
    ok, porque = chegou_inteira(caminho, saida)
    if not ok:
        passo("PARO: a chapa nao chegou inteira no CTP (%s). NAO apaguei"
              % porque)
        return relato
    passo("chapa no CTP, conferida (%.1f MB)"
          % (os.path.getsize(saida) / 1048576.0))
    relato["chapa_no_ctp"] = saida

    # --- 5. ANOTAR NO REGISTRO, antes de tentar apagar ---
    #
    # ESTE E O PASSO QUE FALTAVA, e a falta dele custou papel.
    #
    # O trabalho esta FEITO aqui: a OS existe, a prova saiu, a chapa esta
    # no CTP conferida. O apagar que vem depois e faxina.
    #
    # Sem esta anotacao, qualquer tropeco na faxina fazia o vigia refazer
    # TUDO na volta seguinte - inclusive IMPRIMIR DE NOVO. Foi o que
    # aconteceu em 10/09/2026: o apagar recusou por um detalhe da copia
    # guardada, e sairam tres provas do mesmo trabalho, de dois em dois
    # minutos, ate alguem ver.
    #
    # E o mesmo defeito do '02020 - CHAPA ZIMI' do EMPORIO, em outra
    # roupa: FALHA DEPOIS DA IMPRESSAO VIRA LACO DE IMPRESSAO. Quem
    # imprime tem de deixar dito que imprimiu, na hora, antes de fazer
    # mais qualquer coisa.
    registro = carregar_registro()
    registro[chave] = {
        "cliente": CLIENTE, "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "saidas": [os.path.basename(saida)], "os": relato.get("os"),
        "impressao": relato.get("prova"), "guardada": guardada,
    }
    salvar_registro(registro)
    relato["anotado"] = True

    # --- 6. so agora, o apagar ---
    #
    # Duas provas exigidas: a chapa esta no CTP e abre (ja conferido), e
    # a copia guardada e a MESMA que esta no portao.
    guardada_ok, porque = chegou_inteira(caminho, guardada)
    if not guardada_ok:
        passo("nao apaguei: a copia guardada nao confere (%s). O trabalho "
              "esta FEITO e anotado - tire o arquivo do portao a mao"
              % porque)
        return relato
    os.remove(caminho)
    relato["apagado"] = True
    passo("apagado da PARA CTP (a copia fica na pasta do dia)")
    return relato


def rodada(avisados=None):
    """
    Uma volta do vigia no portao da AMERICA. Fecha o que estiver pronto.

    Chamada de dentro do laco do monitor, a cada INTERVALO. Devolve a
    lista de relatos do que foi fechado nesta volta - vazia quando nao
    havia nada, que e o normal.

    NAO ESTOURA para cima: o portao da AMERICA quebrando nao pode derrubar
    o vigia dos outros seis clientes.
    """
    avisados = avisados if avisados is not None else {}
    feitos = []
    try:
        dia, portao = pasta_do_dia_america()
        if not dia or not os.path.isdir(portao):
            return feitos

        for nome in sorted(os.listdir(portao)):
            if not nome.lower().endswith(".pdf"):
                continue
            caminho = os.path.join(portao, nome)
            # Ainda chegando pela rede? Uma chapa tem megabytes, e ler
            # pela metade daria chapa cortada no CTP.
            if not arquivo_estavel(caminho):
                if avisados.get(caminho) != "chegando":
                    avisados[caminho] = "chegando"
                    log("AMERICA: '%s' ainda esta chegando - espero" % nome)
                continue
            avisados.pop(caminho, None)

            log("AMERICA: fechando '%s'" % nome)
            relato = fechar(caminho, dia)
            for p in relato["passos"]:
                log("   %s" % p)
            if relato.get("ja_feito"):
                # nao e erro: e o portao se recusando a refazer. Acontece
                # quando a faxina falhou e o arquivo ficou para tras.
                pass
            elif not relato.get("apagado"):
                log("AMERICA: '%s' NAO foi concluido - o arquivo fica no "
                    "portao" % nome, alerta=True)
            feitos.append(relato)
    except Exception as e:
        log("AMERICA: erro no portao (%s)" % str(e)[:120], alerta=True)
    return feitos
