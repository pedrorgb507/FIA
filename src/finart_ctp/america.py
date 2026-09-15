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



# ----------------------------------------------------------------------
# O ARQUIVO QUE CHEGA NO COREL
# ----------------------------------------------------------------------
# "se eu coloco o arquivo la dentro dessa pasta no corel, voce segue a
# sequencia que vc usa na voprix ou creative, conferir a pinca, se nao
# tiver pincada, colocar do jeito certo... no caso da america nao precisa
# converter em imagem o corel, irei salvar em imagem ja a montagem,
# entao voce gera o pdf dentro da mesma pasta, e da andamento para saida
# do ctp" - o operador, 15/09/2026.
#
# O QUE MUDA EM RELACAO A VOPRIX E A PRIME. Nelas o .cdr e arte solta, e
# a FIA rasteriza a 1000 dpi para virar chapa. Aqui nao: a AMERICA manda
# a MONTAGEM ja pronta, com a imagem dentro do proprio .cdr. Entao o
# .cdr so e PUBLICADO em PDF - o motor da Corel, em vetor, sem
# reamostrar - e esse PDF ja e a chapa.
#
# A PINCA NAO SE MEDE PELA MARCA DE CORTE AQUI, e isso foi medido antes
# de decidir: das oito montagens da AMERICA que existiam na pasta em
# 15/09/2026, NENHUMA tem marca de corte que o marcas_de_corte reconheca.
# Nas que ja vem no tamanho da chapa a marca nem cabe no alcance - a
# faixa dos 40 mm esta vazia, porque a arte comeca acima dela.
#
# O que essas montagens mostram, medindo a TINTA dentro da chapa:
#
#     #1304-26-CONVITE-MEETING_MONTAGEM   525 x 459   pe 46,5 mm
#     Flyer Semana do Cliente_MONTAGEM    525 x 459   pe 45,0 mm
#
# e as duas com a tinta centrada ao milimetro (37,5 e 37,5; 35,0 e 35,0).
# A pinca da PM_52 e 60 mm: ou seja, a ARTE comeca aos 60 e as marcas de
# corte e registro vivem dentro da pinca, uns 15 mm abaixo dela. E por
# isso que a conferencia da tinta tem a FOLGA_DAS_MARCAS.

FOLGA_DAS_MARCAS = 20.0        # quanto a tinta pode descer abaixo da pinca


def chapa_de(larg, alt):
    """A chapa da AMERICA com esta medida, ou None."""
    from .config import CHAPAS_AMERICA
    medida = tuple(sorted((int(round(larg)), int(round(alt))), reverse=True))
    return medida if medida in CHAPAS_AMERICA else None


def pinca_de(chapa):
    """Quantos mm de pinca esta chapa pede."""
    from .config import CHAPAS_AMERICA
    return CHAPAS_AMERICA[chapa][0]


def cabe_na_chapa(larg, alt, chapa):
    """A arte cabe nesta chapa, sobrando a pinca embaixo?"""
    return (larg <= chapa[0] + 0.5
            and alt + pinca_de(chapa) <= chapa[1] + 0.5)


def onde_montar(larg, alt, tintas):
    """
    (chapa, porque) em que esta arte deve ser montada, ou (None, porque).

    Comeca pela regra de maquina da casa - ate F4 vai na PM_52, acima
    dela colorido vai na SM_74 e preto-e-branco na MOZP - e so procura
    outra se nao couber. Quem manda e caber com a pinca.
    """
    from .config import CHAPAS_AMERICA

    daregra = maquina_da_america(max(larg, alt), tintas)
    if cabe_na_chapa(larg, alt, daregra):
        return daregra, "a chapa da regra"

    outras = sorted((c for c in CHAPAS_AMERICA if c != daregra),
                    key=lambda c: c[0] * c[1])
    for chapa in outras:
        if cabe_na_chapa(larg, alt, chapa):
            return chapa, ("nao cabia na %dx%d da regra com a pinca de "
                           "%.0f mm" % (daregra[0], daregra[1],
                                        pinca_de(daregra)))

    # E SE COUBER DEITADA? Nao giro por conta propria. Sem marca de
    # corte nao da para saber que lado da arte e o pe, e girar errado
    # poe a arte de cabeca para baixo na maquina - chapa perdida e
    # tiragem perdida. Isto e decisao de gente.
    for chapa in [daregra] + outras:
        if cabe_na_chapa(alt, larg, chapa):
            return None, ("so cabe DEITADA na %dx%d - girada 90 graus. "
                          "Nao giro sozinho: sem marca de corte nao sei "
                          "que lado e o pe, e girar errado poe a arte de "
                          "cabeca para baixo na maquina"
                          % (chapa[0], chapa[1]))
    return None, "nao cabe em chapa nenhuma da AMERICA, nem com a pinca"


def tinta_no_pe(pdf):
    """
    A quantos mm do pe da pagina comeca a tinta, ou None se nao der.

    Serve para CONFERIR a pinca de quem ja chega no tamanho da chapa: a
    arte tem de estar la em cima, nao encostada na borda de baixo.
    """
    import re
    import subprocess

    from .ghostscript import GS
    try:
        saiu = subprocess.run(
            [GS, "-dNOPAUSE", "-dBATCH", "-dFirstPage=1", "-dLastPage=1",
             "-sDEVICE=bbox", pdf],
            capture_output=True, text=True, timeout=180)
    except Exception:
        return None
    achou = re.search(r"%%HiResBoundingBox:\s*[\d.]+ ([\d.]+)",
                      saiu.stderr or "")
    return float(achou.group(1)) / MM if achou else None


def conferir_a_pinca(pdf, chapa):
    """
    O recado sobre a pinca de uma chapa que ja chegou montada, ou None.

    NAO BARRA NADA: a montagem foi feita e revisada por gente, e quem a
    aprovou sabe mais do que esta conta. Mas tinta encostada no pe da
    chapa e sinal de montagem sem pinca, e isso vale um aviso.
    """
    pe = tinta_no_pe(pdf)
    if pe is None:
        return None
    pinca = pinca_de(chapa)
    if pe >= pinca - FOLGA_DAS_MARCAS:
        return "pinca conferida: a tinta comeca a %.0f mm do pe (pinca %.0f)" \
            % (pe, pinca)
    return ("ATENCAO: a tinta comeca a %.0f mm do pe e a pinca da %dx%d e "
            "de %.0f mm. Parece montagem SEM PINCA - confira antes de "
            "gravar" % (pe, chapa[0], chapa[1], pinca))


def montar(pdf, chapa, destino):
    """
    Assenta a arte na chapa: centrada, e o pe dela a pinca da borda.

    Em vetor, como a montagem dos outros clientes - o salvar_montagem do
    processador faz a mesma conta, e e ele quem desenha.

    A PINCA SE MEDE DA BORDA DE BAIXO DA ARTE, e nao de uma marca de
    corte: as montagens da AMERICA nao trazem marca que se possa
    reconhecer (ver o comentario la em cima). E uma diferenca real para
    a CREATIVE, onde a pinca sai da marca.
    """
    from .processador import salvar_montagem

    pag = pypdf.PdfReader(pdf).pages[0]
    larg = float(pag.mediabox.width) / MM
    esquerda = (chapa[0] - larg) / 2.0
    return salvar_montagem(pdf, 1, destino, chapa, esquerda,
                           pinca_de(chapa))


def caminho_do_pdf(cdr):
    """O PDF nasce ao lado do .cdr, com o mesmo nome."""
    return os.path.splitext(cdr)[0] + ".pdf"


def converter(cdr, pasta_dia):
    """
    Publica o .cdr em PDF, monta se precisar, e devolve o caminho.

    Devolve None quando nao deu - e ai o .cdr FICA no portao, para a
    proxima volta ou para uma pessoa olhar.
    """
    from . import corel

    passos = []
    destino = caminho_do_pdf(cdr)
    if os.path.exists(destino):
        passos.append("o PDF ja existia ao lado - uso ele")
    else:
        try:
            corel.publicar_pdf(cdr, destino)
        except corel.ArquivoEmUso:
            return None, ["esta aberto no CorelDRAW - espero fechar"]
        except Exception as e:
            return None, ["o CorelDRAW nao converteu: %s" % str(e)[:90]]
        passos.append("publiquei em PDF: %s" % os.path.basename(destino))

    pronto, mais = do_pdf_pronto(destino, pasta_dia)
    return pronto, passos + mais


def do_pdf_pronto(destino, pasta_dia=None):
    """
    O que fazer com o PDF ja publicado: conferir a pinca ou montar.

    Separado do 'converter' porque esta metade nao depende do CorelDRAW
    - e e ela que decide em que chapa a arte vai e onde ela encosta.
    """
    passos = []
    larg, alt, tintas = medir(destino)
    passos.append("a arte saiu %.0f x %.0f mm, tintas %s"
                  % (larg, alt, "".join(sorted(tintas)) or "?"))

    chapa = chapa_de(larg, alt)
    if chapa:
        passos.append("ja veio no tamanho da chapa %dx%d - nao monto nada"
                      % chapa)
        recado = conferir_a_pinca(destino, chapa)
        if recado:
            passos.append(recado)
        return destino, passos

    chapa, porque = onde_montar(larg, alt, tintas)
    if not chapa:
        return None, passos + ["PARO: %s" % porque]

    montada = os.path.splitext(destino)[0] + "_montagem.pdf"
    try:
        montar(destino, chapa, montada)
    except Exception as e:
        return None, passos + ["nao consegui montar: %s" % str(e)[:90]]
    passos.append("montei na chapa %dx%d (%s), pinca de %.0f mm, "
                  "centrada: %s" % (chapa[0], chapa[1], porque,
                                    pinca_de(chapa),
                                    os.path.basename(montada)))

    # O PDF SOLTO SAI DO PORTAO, e isto nao e arrumacao: ficando os
    # dois, a volta seguinte do vigia acharia DUAS chapas para o mesmo
    # servico - duas gravacoes e duas OS. Ele vai para a pasta do dia,
    # onde nao atrapalha e continua existindo se alguem quiser ver a
    # arte antes de ser assentada.
    try:
        if pasta_dia:
            guardar_copia(destino, pasta_dia)
        os.remove(destino)
        passos.append("tirei o PDF solto do portao (esta na pasta do dia): "
                      "so a montagem vira chapa")
    except Exception as e:
        return None, passos + [
            "PARO: montei, mas nao consegui tirar o PDF solto do portao "
            "(%s). Ficando os dois, sairiam duas chapas e duas OS"
            % str(e)[:70]]
    return montada, passos


def guardar_o_corel(cdr, pasta_dia):
    """
    Tira o .cdr do portao, com copia garantida na pasta do dia.

    MOVE, nao apaga: o .cdr e a fonte da montagem, e apagar fonte nao
    esta combinado com ninguem. Deixa-lo no portao tambem nao serve -
    ele seria publicado de novo a cada volta.
    """
    guardada, _ = guardar_copia(cdr, pasta_dia)
    if os.path.exists(guardada) and os.path.abspath(guardada) != \
            os.path.abspath(cdr):
        os.remove(cdr)
        return True
    return False

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
    #
    # SEM PROVA, SEM CHAPA - a mesma regra dos outros seis clientes (ver
    # IMPRIMIR_ORIGINAL no config): papel na mao do operador e o que
    # prova que o servico saiu. Se a impressora estiver fora do ar, o
    # arquivo FICA no portao e a volta seguinte tenta de novo. E seguro
    # tentar de novo: a OS ja existe e sera reaproveitada (JA_ESTAVA), e
    # a trava de copia unica garante que uma prova que SAIU nao sai
    # outra vez.
    from .processador import _verso_da_os
    from .prova import JaImprimiu, imprimir
    verso = _verso_da_os(numero)
    try:
        _, folhas = imprimir(caminho, etiquetas=["AMERICA %s" % nome_chapa],
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
        passo("PARO: a prova nao saiu (%s). Sem prova nao gravo chapa - o "
              "arquivo fica no portao e tento na proxima volta"
              % str(e)[:70])
        relato["prova"] = False
        return relato

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
            baixo = nome.lower()
            if not baixo.endswith((".pdf", ".cdr")):
                continue
            caminho = os.path.join(portao, nome)

            # O QUE VEM NO COREL PASSA ANTES POR AQUI. Publicado o PDF -
            # e montado, se precisar -, o .cdr sai do portao e o PDF fica.
            # Quem o fecha e a volta seguinte, pelo caminho de sempre: um
            # passo por vez, e cada um deixa rastro no log.
            if baixo.endswith(".cdr"):
                if not arquivo_estavel(caminho):
                    if avisados.get(caminho) != "chegando":
                        avisados[caminho] = "chegando"
                        log("AMERICA: '%s' ainda esta chegando - espero"
                            % nome)
                    continue
                avisados.pop(caminho, None)
                log("AMERICA: convertendo '%s'" % nome)
                pronto, passos = converter(caminho, dia)
                for p in passos:
                    log("   %s" % p)
                if not pronto:
                    log("AMERICA: '%s' NAO virou PDF - o arquivo fica no "
                        "portao" % nome, alerta=True)
                    continue
                if guardar_o_corel(caminho, dia):
                    log("   tirei o .cdr do portao (a copia esta na pasta "
                        "do dia)")
                feitos.append({"arquivo": nome, "passos": passos,
                               "apagado": False, "os": None,
                               "convertido": os.path.basename(pronto)})
                continue

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
