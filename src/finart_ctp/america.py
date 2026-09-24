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
import tempfile
from datetime import datetime

import pypdf

from . import gerempre
from .ghostscript import cobertura_por_pagina, tintas_da_cobertura
from .nomes import cores_no_nome, finalizar
from .utils import (abrir_bloco, arquivo_estavel, carregar_registro,
                    chave_arquivo, fechar_bloco, log, salvar_registro)

# O CLIENTE PADRAO DESTE MODULO.
#
# Ele nasceu so para a AMERICA, e em 24/09/2026 a CARRIER entrou pelo
# mesmo caminho. Em vez de copiar 1356 linhas - que envelheceriam
# separadas, e cada conserto teria de ser feito duas vezes -, o cliente
# virou PARAMETRO, com a AMERICA de padrao: chamada antiga continua
# valendo, e e por isso que os testes que ja existiam nao mudaram.
CLIENTE = "AMERICA"


def _portao(portao=None):
    """
    O portao pedido, ja com a PASTA RESOLVIDA.

    A pasta vem pelo NOME no config ('BASE_AMERICA'), e nao pelo valor:
    o config_local e aplicado depois do bloco que descreve os portoes,
    entao guardar o valor la congelaria o de fabrica. Ver o comentario
    de PORTAO_AMERICA no config, que tem o caso.
    """
    from . import config
    d = dict(portao or config.PORTAO_AMERICA)
    d["base"] = getattr(config, d["base"])
    return d
from .config import (BANCADA,              # noqa: F401  (vem do config)
                     BASE_AMERICA,
                     SUBPASTA_PARA_MONTAR)
PORTAO = "PARA CTP"
MM = 72.0 / 25.4


def pasta_do_dia_america(quando=None, portao=None):
    """(pasta_do_dia, pasta_do_portao) do portao, ou (None, None)."""
    # importado aqui dentro porque o monitor importa ESTE modulo - por
    # cima, os dois se importariam em circulo e nenhum carregaria
    from .monitor import localizar_pasta_mes, pasta_do_dia
    base = _portao(portao)["base"]
    mes = localizar_pasta_mes(base)
    if not mes:
        return None, None
    dia = os.path.join(base, mes, pasta_do_dia())
    if not os.path.isdir(dia):
        return None, None
    return dia, os.path.join(dia, PORTAO)


def medir(pdf):
    """(largura_mm, altura_mm, tintas) da chapa."""
    pag = pypdf.PdfReader(pdf).pages[0]
    larg = float(pag.mediabox.width) / MM
    alt = float(pag.mediabox.height) / MM
    # SO O QUE CAI DENTRO DO CORTE - e daqui sai a sugestao de cor da
    # tela e, por ela, quantas chapas a OS cobra. As marcas de corte do
    # designer vem em cor de registro (CMYK a 100%) e ficam FORA do
    # corte: contando a pagina inteira, arte de preto puro responde
    # 'quatro tintas' e o cliente paga quatro chapas no lugar de uma.
    # Regra do operador, 18/09/2026.
    cob = cobertura_por_pagina(pdf, sem_icc=True, so_o_corte=True)
    tintas = tintas_da_cobertura(cob[0]) if cob else set("CMYK")

    # E A TINTA DE TRACO CAI, pela MESMA conta do resto da casa.
    #
    # O tintas_da_cobertura decide pelo LIMIAR_TINTA, que e 0,0001
    # ABSOLUTO - sujeira de arredondamento. Cruz de corte em cor de
    # registro passa desse valor com folga: medido em 21/09/2026, os dois
    # arquivos da AMERICA davam C 0,0002 contra K 0,1090, e saiam CMYK.
    # Quatro chapas gravadas e cobradas onde devia sair UMA.
    #
    # O so_o_corte ja tirava as marcas que ficam FORA da linha de corte.
    # Estas ficavam DENTRO - e ai so a proporcao resolve: 0,18% da tinta
    # mais forte nao desenha nada, e a conta que sabe disso ja existia.
    #
    # UMA CONTA SO NA CASA: e a mesma funcao que a PRIME e a VOPRIX usam,
    # com o mesmo limite e a mesma confirmacao de 'aparece sozinha em
    # algum pixel'. Duas contas parecidas em lugares diferentes e como
    # nasce o dia em que a tela diz uma coisa e a OS cobra outra.
    # ------------------------------------------------------------------
    # SAO DOIS PASSOS, E O SEGUNDO E O QUE DECIDE.
    #
    # Este comentario DIZIA que aqui havia "a mesma confirmacao de
    # 'aparece sozinha em algum pixel'" que a PRIME e a VOPRIX usam. Nao
    # havia: so a proporcao rodava. O comentario descrevia a intencao e
    # o codigo fazia metade - e comentario que mente e pior que nenhum,
    # porque quem le para de conferir.
    #
    # CUSTOU UMA CHAPA, em 22/09/2026. O 'SORV. VALENTIM - TAMPA 240ml'
    # da AMERICA tem K em 1,06% de cobertura - 2,9% da tinta mais forte.
    # A proporcao o levantou como candidato e nao houve quem perguntasse
    # se ele desenha. Desenha: o K aparece SOZINHO em 451 pixels. A
    # chapa foi para o CTP como _CMY_, sem o preto, a OS cobrou 3 no
    # lugar de 4, e a tampa imprimiria sem o texto - o que so apareceria
    # na maquina.
    #
    # O config.py ja avisava que o numero sozinho nao decide: "um ciano
    # de 5,23% e traco e um K de 6,45% e texto, e nenhum numero separa
    # os dois". A pergunta que separa e outra, e e esta.
    #
    # NAO DANDO PARA MEDIR, A TINTA FICA. Chapa a mais na conta se
    # conserta com uma linha na OS; chapa a menos no CTP so aparece na
    # maquina, com papel e tiragem gastos.
    if cob:
        from .config import CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO
        if CLIENTE in CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO:
            from .ghostscript import tinta_aparece_sozinha
            from .processador import sem_tinta_de_traco
            ficam, candidatas = sem_tinta_de_traco(cob[0], tintas)
            forte = max(cob[0].get(x, 0.0) for x in "CMYK") or 1.0
            de_traco = set()
            for cor in sorted(candidatas):
                sozinha, quantos = tinta_aparece_sozinha(
                    pdf, 1, cor, sem_perfil_=True)
                quanto = cob[0].get(cor, 0.0)
                if sozinha is False:
                    de_traco.add(cor)
                    log("AMERICA: %s tem %.4f (%.1f%% da mais forte) e "
                        "NUNCA aparece sozinha em %d pixels - e traco, "
                        "nao chapa. Nao gravei nem cobrei essa cor"
                        % (cor, quanto, 100.0 * quanto / forte, quantos))
                elif sozinha is True:
                    log("AMERICA: %s tem so %.4f, mas aparece SOZINHA em "
                        "pixel - desenha alguma coisa. Fica."
                        % (cor, quanto))
                else:
                    log("AMERICA: %s parecia traco (%.4f) e nao consegui "
                        "medir se aparece sozinha. FICA - chapa a menos "
                        "no CTP e pior que chapa a mais na conta."
                        % (cor, quanto), alerta=True)
            tintas = set(tintas) - de_traco
    return larg, alt, tintas


def e_preto_e_branco(tintas):
    """Uma cor so, ou cinza. O 'peb' do operador."""
    return tintas <= {"GRAY", "GREY", "K"} or len(tintas) <= 1


def maquina_da_america(maior_lado, tintas, portao=None):
    """
    (largura, altura) da chapa que recebe este trabalho.

    Regra do operador: ate o formato 4 vai na PM_52; acima dele, colorido
    vai na SM_74 e preto-e-branco vai na MOZP. E a escolha de MAQUINA -
    quem manda e o tamanho do trabalho e a cor, nao o contrario.

    Serve para a FIA saber em que chapa MONTAR. Quando o arquivo ja chega
    montado, quem manda e o tamanho dele; esta funcao vira conferencia.
    """
    from .config import MAIOR_LADO_F4
    p = _portao(portao)
    if maior_lado <= MAIOR_LADO_F4:
        return p["pequena"]
    # NA CARRIER AS DUAS SAO A MESMA, e e de proposito: as chapas dela
    # sao da FINART e nao carregam nome de maquina, entao nao ha
    # divisao por cor. A conta e a mesma; o dado e que muda.
    return p["grande_pb"] if e_preto_e_branco(tintas) else p["grande_cor"]


def nome_da_chapa(origem, larg, alt, tintas, portao=None):
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
                                      _portao(portao)["cliente"], base))


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

FOLGA_DAS_MARCAS = 20.0        # quanto a TINTA pode descer abaixo da pinca

# E quanto o DESENHO pode descer - que e outra coisa, e menor.
#
# A arte passa da linha de corte para baixo pela SANGRIA, que a
# guilhotina come. Medido nas montagens boas da AMERICA:
#
#     Receituario Orto Saude (pinca 60)   desenho a 57,0    -3,0
#     PASTA PRE MEETING fv   (pinca 62)   desenho a 56,5    -5,5
#
# e a que nao tem pinca nenhuma, a 'No Auge da Loucura', tem tinta a
# 2,0 mm - quase sessenta abaixo. Entre -5,5 e -58 nao ha o que calibrar:
# 15 mm separa os dois casos com folga de sobra, e o que passar disso nao
# e sangria, e montagem feita sem pinca.
FOLGA_DA_SANGRIA = 15.0


def esta_pincada(pe_arte, pinca):
    """O desenho respeita a faixa que a maquina segura?"""
    return pe_arte is not None and pe_arte >= pinca - FOLGA_DA_SANGRIA


def chapa_de(larg, alt, portao=None):
    """A chapa deste cliente com esta medida, ou None."""
    chapas = _portao(portao)["chapas"]
    medida = tuple(sorted((int(round(larg)), int(round(alt))), reverse=True))
    return medida if medida in chapas else None


def pinca_de(chapa, portao=None):
    """Quantos mm de pinca esta chapa pede."""
    return _portao(portao)["chapas"][chapa][0]


def cabe_na_chapa(larg, alt, chapa, portao=None):
    """A arte cabe nesta chapa, sobrando a pinca embaixo?"""
    return (larg <= chapa[0] + 0.5
            and alt + pinca_de(chapa, portao) <= chapa[1] + 0.5)


def onde_montar(larg, alt, tintas, portao=None):
    """
    (chapa, porque) em que esta arte deve ser montada, ou (None, porque).

    Comeca pela regra de maquina da casa - ate F4 vai na PM_52, acima
    dela colorido vai na SM_74 e preto-e-branco na MOZP - e so procura
    outra se nao couber. Quem manda e caber com a pinca.
    """
    p = _portao(portao)

    daregra = maquina_da_america(max(larg, alt), tintas, portao)
    if cabe_na_chapa(larg, alt, daregra, portao):
        return daregra, "a chapa da regra"

    outras = sorted((c for c in p["chapas"] if c != daregra),
                    key=lambda c: c[0] * c[1])
    for chapa in outras:
        if cabe_na_chapa(larg, alt, chapa, portao):
            return chapa, ("nao cabia na %dx%d da regra com a pinca de "
                           "%.0f mm" % (daregra[0], daregra[1],
                                        pinca_de(daregra, portao)))

    # E SE COUBER DEITADA? Nao giro por conta propria. Sem marca de
    # corte nao da para saber que lado da arte e o pe, e girar errado
    # poe a arte de cabeca para baixo na maquina - chapa perdida e
    # tiragem perdida. Isto e decisao de gente.
    for chapa in [daregra] + outras:
        if cabe_na_chapa(alt, larg, chapa, portao):
            return None, ("so cabe DEITADA na %dx%d - girada 90 graus. "
                          "Nao giro sozinho: sem marca de corte nao sei "
                          "que lado e o pe, e girar errado poe a arte de "
                          "cabeca para baixo na maquina"
                          % (chapa[0], chapa[1]))
    return None, ("nao cabe em chapa nenhuma da %s, nem com a pinca"
                  % p["cliente"])


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


PX_POR_MM = 4                  # a medida do pe se faz nesta resolucao
RISCO_MM = 20.0                # menos tinta que isto numa linha e MARCA


def medir_o_pe(pdf):
    """
    (pe_da_tinta, pe_da_arte, topo_da_tinta), em mm do pe da pagina.

    Ou (None, None, None) se nao deu para medir.

    SAO DUAS COISAS DIFERENTES, e confundi-las foi o que deixou passar a
    chapa errada de 17/09/2026:

      pe_da_tinta   onde comeca QUALQUER tinta - e sao as MARCAS de corte
                    e registro, que vivem DENTRO da faixa da pinca de
                    proposito;
      pe_da_arte    onde comeca o DESENHO - e este si nao pode invadir a
                    pinca, porque ali a maquina segura a folha.

    A conta separa os dois pelo que se ve em cada linha: marca de corte e
    risco fino, e desenho e faixa larga. Medido na montagem do
    'Receituario Orto Saude 2026', linha a linha, a 8 px/mm:

        de 63,6 a 73,5 mm      4 px por linha    <- as quatro marcas
        de 73,5 para cima   3438 px por linha    <- o desenho

    Quatro pixels contra tres mil e quatrocentos. Nao e limite apertado
    que se precise calibrar: o RISCO_MM de 20 mm cai no meio de um abismo
    de tres ordens de grandeza.

    POR QUE MEDIR NA IMAGEM, e nao no PDF. O marcas_de_corte le os
    numeros escritos no fluxo da pagina, e numa pagina MONTADA esses
    numeros sao os da arte ANTES de ser deslocada - o merge escreve a
    translacao numa matriz, e o leitor de tracos nao a aplica. Na
    montagem do Receituario ele devolve 16,50 mm, que e onde a marca
    estava dentro da arte, e nao os 60,00 onde ela ficou na chapa.
    Rasterizar custa segundos e nao tem como mentir.
    """
    import subprocess
    import tempfile

    from .ghostscript import GS

    pasta = tempfile.mkdtemp()
    png = os.path.join(pasta, "pe.png")
    try:
        altura_mm = float(pypdf.PdfReader(pdf).pages[0].mediabox.height) / MM
        subprocess.run(
            [GS, "-dNOPAUSE", "-dBATCH", "-dFirstPage=1", "-dLastPage=1",
             "-sDEVICE=png16m", "-r%d" % int(PX_POR_MM * 25.4),
             "-dUseFastColor=true", "-o", png, pdf],
            check=True, capture_output=True, timeout=600)
        from PIL import Image
        with Image.open(png) as im:
            cinza = im.convert("L")
            larg, alt = cinza.size
            pixels = cinza.load()
            # A ESCALA SAI DA IMAGEM, e nao do que eu pedi ao Ghostscript.
            #
            # O -r so aceita numero inteiro de dpi: pedir 4 px/mm vira
            # int(101,6) = 101 dpi, que sao 3,976 px/mm. Dividir pelos 4
            # que eu queria erra 0,6% - 1,5 mm aos 250, 2,4 mm aos 400.
            # Foi um teste sintetico que pegou; num arquivo de cliente
            # isso passaria por folga de medicao.
            px_por_mm = alt / altura_mm
            pe_tinta = pe_arte = topo = None
            for y in range(alt - 1, -1, -1):
                quantos = sum(1 for x in range(larg) if pixels[x, y] < 245)
                if not quantos:
                    continue
                mm = (alt - 1 - y) / px_por_mm
                if pe_tinta is None:
                    pe_tinta = mm
                if pe_arte is None and quantos > RISCO_MM * px_por_mm:
                    pe_arte = mm
                topo = mm
        return pe_tinta, pe_arte, topo
    except Exception:
        return None, None, None
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def ajustar_a_pinca(pdf, chapa, destino, portao=None):
    """
    Sobe o desenho ate a pinca. Devolve (caminho, recado) ou (None, porque).

    Pedido do operador, 17/09/2026: "quando o arquivo for pra pasta PARA
    CTP, e nao estiver pincado voce ja ajusta".

    So se aplica a quem JA CHEGA no tamanho da chapa - quem chega menor e
    assentado pelo montar(), que ja pinca pela marca de corte. Aqui nao ha
    o que assentar: a pagina ja e a chapa, e o que se faz e DESLOCAR o
    conteudo dela para cima.

    E SO SE COUBER. Subir o desenho empurra o topo, e o que passar da
    borda de cima some sem avisar - seria trocar um defeito visivel (arte
    na pinca) por um invisivel (arte cortada). Nao cabendo, devolve o
    motivo e ninguem grava nada.

    CONFERE DEPOIS. O deslocamento e uma conta; que ele tenha acontecido
    e outra coisa, e se mede no arquivo que saiu.
    """
    from .processador import salvar_montagem

    pinca = pinca_de(chapa, portao)
    _, pe_arte, topo = medir_o_pe(pdf)
    if pe_arte is None:
        return None, "nao consegui medir o pe para ajustar"
    if esta_pincada(pe_arte, pinca):
        return None, "ja esta pincada - nao ha o que ajustar"

    subir = pinca - pe_arte
    if topo + subir > chapa[1] - 1.0:
        return None, ("para pincar eu teria de subir %.0f mm, e o desenho "
                      "vai ate %.0f mm numa chapa de %.0f - o topo sairia "
                      "fora. Nao ajusto: arte cortada e pior que arte na "
                      "pinca, porque ninguem ve"
                      % (subir, topo, chapa[1]))

    salvar_montagem(pdf, 1, destino, chapa, 0.0, subir)

    _, agora, _ = medir_o_pe(destino)
    if not esta_pincada(agora, pinca):
        try:
            os.remove(destino)
        except OSError:
            pass
        return None, ("subi %.0f mm e o desenho ficou a %s mm do pe, e nao "
                      "nos %.0f da pinca. Nao mando o que nao conferi"
                      % (subir, "%.1f" % agora if agora else "?", pinca))
    return destino, ("estava SEM PINCA: o desenho comecava a %.0f mm do pe "
                     "numa chapa de pinca %.0f. Subi %.0f mm e conferi - "
                     "agora comeca a %.0f" % (pe_arte, pinca, subir, agora))


def conferir_a_pinca(pdf, chapa, portao=None):
    """
    (recado, pode_seguir) sobre a pinca de uma chapa ja montada.

    ELA BARRA, e ate 17/09/2026 nao barrava. O aviso dizia "confira antes
    de gravar" e deixava passar, com este motivo escrito: "a montagem foi
    feita e revisada por gente, e quem a aprovou sabe mais do que esta
    conta". O operador desfez isso com todas as letras:

        "nunca um arquivo pode ir sem pincar para o ctp"

    E ele tem razao, e a razao e simples: a faixa da pinca e onde a
    maquina SEGURA a folha. Desenho ali nao imprime - nao e questao de
    ficar feio, e chapa gravada que nao serve. Um aviso no log nao para
    ninguem; o arquivo ia para o CTP do mesmo jeito.

    Quem chega no tamanho da chapa nao tem conserto automatico: nao da
    para assentar mais em cima o que ja ocupa a chapa inteira. Entao aqui
    so cabe PARAR, e o arquivo fica no portao para uma pessoa remontar.

    O NUMERO NAO E CHUTE. As montagens da AMERICA que existem comecam a
    tinta entre 45,0 e 47,3 mm numa chapa de pinca 60 - as marcas de
    corte e de registro vivem DENTRO da pinca, uns 14 mm abaixo dela. E
    dai que sai a FOLGA_DAS_MARCAS. A unica que destoa e a 'No Auge da
    Loucura', com a tinta a 2,0 mm: essa e justamente a que nao devia ter
    ido.

    NAO DANDO PARA MEDIR, segue: recusar por nao ter conseguido abrir o
    arquivo seria parar o cliente por defeito nosso.

    QUEM DECIDE E O DESENHO, NAO A TINTA. Ate 17/09/2026 esta conta
    olhava a primeira tinta que aparecesse e perdoava 20 mm de folga,
    porque as marcas de corte moram dentro da pinca. Era conta cega com
    remendo: a folga existia para nao acusar marca, e junto perdoava
    20 mm de DESENHO invadindo a pinca. Agora se mede o desenho, e a
    folga nao precisa existir - ver medir_o_pe.
    """
    _, pe_arte, _ = medir_o_pe(pdf)
    if pe_arte is None:
        return None, True
    pinca = pinca_de(chapa, portao)
    if esta_pincada(pe_arte, pinca):
        return ("pinca conferida: o desenho comeca a %.1f mm do pe "
                "(pinca %.0f)" % (pe_arte, pinca)), True
    return ("SEM PINCA: o desenho comeca a %.0f mm do pe e a pinca da %dx%d "
            "e de %.0f mm - e ali que a maquina segura a folha"
            % (pe_arte, chapa[0], chapa[1], pinca)), False


def pe_da_montagem(pdf, chapa, portao=None):
    """
    (base, de_onde) - a quantos mm do pe da chapa vai a borda do arquivo.

    A PINCA SE MEDE ATE A MARCA DE CORTE. E a mesma regra da CREATIVE, e
    da montagem que a propria casa faz: a PRIMEIRA LINHA DE CORTE cai
    exatamente na medida da pinca. Custou uma chapa 12 mm fora do lugar
    na CREATIVE, e custou de novo aqui em 17/09/2026 - o 'Receituario
    Orto Saude 2026' saiu com a linha de corte a 76,4 mm numa PM 52 de
    pinca 60, porque a conta usava a BORDA DO ARQUIVO.

    O erro nao e so de 16 mm de desperdicio: quem monta a mao poe as
    marcas de corte e de registro ABAIXO da linha de corte, dentro da
    faixa da pinca. Assentando pela borda, a montagem inteira sobe, e o
    operador que mede a pinca com a regua acha 76 onde devia achar 60.
    As duas montagens boas que a casa ja tinha comecam a tinta aos 45,0 e
    aos 46,5 mm - marca de corte, uns 14 mm abaixo dos 60.

    QUANDO NAO HA MARCA, vale a borda do arquivo, que era a conta de
    antes. Nao e chute: das oito montagens da AMERICA de 15/09/2026
    nenhuma trazia marca reconhecivel, e para essas a borda e tudo o que
    ha. Ver o comentario la em cima.
    """
    from .marcas import marcas_de_corte

    pinca = pinca_de(chapa, portao)
    marca = marcas_de_corte(pdf).get("pe")
    if marca is None:
        return pinca, "sem marca de corte - contei da borda do arquivo"
    if marca > pinca:
        # a sobra do proprio arquivo ja e maior que a pinca: encostar
        # mais embaixo poria a borda fora da chapa
        return 0.0, ("a marca de corte esta a %.1f mm da borda, mais que "
                     "a pinca de %.0f - assentei no pe da chapa"
                     % (marca, pinca))
    return pinca - marca, ("da marca de corte, a %.1f mm da borda do "
                           "arquivo" % marca)


# A RESOLUCAO DA AMERICA, por chapa - 23/09/2026.
#
# Regra do operador: "se for formato menor para a 525x459, converte o
# arquivo para 1000 dpi e se for maior para a chapa 745x605, converte
# para 800 dpi".
#
# NAO E A REGRA DO MOTOR. O montar_bate_vira usa 900 ate o formato 4 e
# 800 acima; a da AMERICA e 1000 na pequena. Por isso o dpi vai DITO na
# chamada, em vez de deixar o motor decidir - duas regras parecidas e o
# jeito mais facil de uma virar a outra sem ninguem ver.
DPI_AMERICA = {(525, 459): 1000, (745, 605): 800, (650, 550): 800}
DPI_AMERICA_PADRAO = 800


def dpi_da_america(chapa, portao=None):
    """
    A resolucao desta chapa, pela regra do operador.

    A TABELA VEM DO PORTAO, e o DPI_AMERICA aqui em cima e so o do
    cliente padrao - continua existindo porque os testes o leem pelo
    nome, e porque e onde a regra dele esta escrita.
    """
    tabela = _portao(portao)["dpi"]
    return tabela.get((int(chapa[0]), int(chapa[1])), DPI_AMERICA_PADRAO)


def _soltar_a_trava_do_pypdf():
    """
    Deixa o pypdf ler fluxo grande - a chapa da AMERICA passa de 300 MB.

    O MAX_DECLARED_STREAM_LENGTH e 75 MB, e e guarda contra PDF
    malicioso, nao limite de correcao. Uma arte de 660x480 a 800 dpi da
    312 MB de imagem, e sem isto a montagem morre com "Declared stream
    length exceeds maximum allowed length" - longe do problema, dentro
    do pypdf, sem dizer de que arquivo.

    OS PDF DAQUI SAO NOSSOS: saem do Ghostscript nesta maquina, a partir
    do arquivo que o operador revisou. Nao ha terceiro no meio.

    JA CAIU UMA VEZ por descuido meu: a primeira versao do montar()
    soltava a trava, e ao reescrever a funcao - quando o operador mandou
    voltar as marcas do cliente - a linha ficou para tras. A montagem
    quebrou no mesmo ponto. Por isso agora ela mora numa funcao com
    nome, e nao solta no meio de outra coisa.
    """
    try:
        import pypdf.filters as filtros
        if getattr(filtros, "MAX_DECLARED_STREAM_LENGTH", 0) < 2_000_000_000:
            filtros.MAX_DECLARED_STREAM_LENGTH = 2_000_000_000
    except Exception:
        pass


def montar(pdf, chapa, destino, portao=None):
    """
    Assenta a arte na chapa: a arte VIRA IMAGEM, as marcas sao DO CLIENTE.

    REGRA DO OPERADOR, 23/09/2026, e ela desfez a da manha:

        "vamos tirar a regra de vc redesenhar as marcas de corte,
        mantenha as marcas do cliente, e por elas vc pinca, a pinca e
        pela cruz de corte do cliente, e vc converte toda a imagem em
        800 dpi"

    De manha tinhamos tentado o contrario - a FIA desenhando as proprias
    marcas - justamente porque ela NAO ACHAVA as do cliente. Ele viu a
    chapa e recusou: as marcas sao dele, e a pinca sai delas.

    O QUE PERMITIU VOLTAR foi consertar a leitura, nao a montagem. O
    marcas._segmentos lia so o fluxo da PAGINA, e neste arquivo a pagina
    tem ZERO bytes: tudo mora em quatro Form XObject. Achava 2 segmentos
    no arquivo inteiro e nenhuma marca - por isso a pinca caia na borda.
    Descendo nos Form, sao 7243 tracos horizontais e a cruz aparece a
    28,00 mm do pe, simetrica com o topo. Ver marcas._andar.

    ENTAO A ORDEM AQUI IMPORTA, e e o miolo desta funcao:

      1. a marca e lida no arquivo ORIGINAL, em vetor, onde ela e exata;
      2. so DEPOIS a pagina inteira vira imagem - marcas junto, porque
         sao do cliente e ficam onde ele as pos;
      3. a imagem e assentada com a borda a (pinca - marca) do pe, e a
         CRUZ DELE cai exatamente na pinca.

    Medir a marca DEPOIS de rasterizar seria procurar traco vetorial num
    PDF que ja nao tem nenhum - e a resposta voltaria "sem marca", que e
    como a chapa saiu errada da primeira vez.
    """
    from .montagem import _motor
    motor = _motor()
    _soltar_a_trava_do_pypdf()

    # 1. A MARCA, NO ORIGINAL - antes de qualquer conversao.
    base, de_onde = pe_da_montagem(pdf, chapa, portao)

    # 2. A PAGINA INTEIRA EM IMAGEM, no dpi da chapa.
    pasta = tempfile.mkdtemp(prefix="america_", dir=os.path.dirname(destino))
    try:
        achatada = os.path.join(pasta, "em_imagem.pdf")
        motor.peca_em_pdf(pdf, 1, dpi_da_america(chapa, portao), achatada)

        # 3. ASSENTADA: centrada na largura, a cruz do cliente na pinca.
        pag = pypdf.PdfReader(achatada).pages[0]
        larg = float(pag.mediabox.width) / MM
        esquerda = (chapa[0] - larg) / 2.0
        from .processador import salvar_montagem
        salvar_montagem(achatada, 1, destino, chapa, esquerda, base)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    return destino


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

    pronto, mais = do_pdf_pronto(destino, pasta_dia, portao)
    return pronto, passos + mais


def do_pdf_pronto(destino, pasta_dia=None, portao=None):
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
        recado, pode = conferir_a_pinca(destino, chapa)
        if recado:
            passos.append(recado)
        if pode:
            return destino, passos

        # NAO ESTA PINCADA - entao eu pinco. "quando o arquivo for pra
        # pasta PARA CTP, e nao estiver pincado voce ja ajusta", o
        # operador em 17/09/2026. Parar seria o certo enquanto eu nao
        # soubesse fazer; sabendo, parar e so empurrar para uma pessoa o
        # que eu posso resolver e conferir.
        ajustada = os.path.splitext(destino)[0] + "_pincada.pdf"
        saiu, conta = ajustar_a_pinca(destino, chapa, ajustada)
        passos.append(conta)
        if not saiu:
            passos.append("PARO: sem pinca nao vai para o CTP. Remonte a "
                          "arte acima da pinca e ponha de volta no portao")
            return None, passos

        # o original NAO se apaga: e o arquivo de quem montou
        try:
            if pasta_dia:
                guardar_copia(destino, pasta_dia)
            os.remove(destino)
        except Exception as e:
            return None, passos + ["nao consegui tirar do portao o arquivo "
                                   "sem pinca (%s)" % str(e)[:60]]
        return saiu, passos

    chapa, porque = onde_montar(larg, alt, tintas)
    if not chapa:
        return None, passos + ["PARO: %s" % porque]

    montada = os.path.splitext(destino)[0] + "_montagem.pdf"
    base, de_onde = pe_da_montagem(destino, chapa, portao)
    try:
        montar(destino, chapa, montada, portao)
    except Exception as e:
        return None, passos + ["nao consegui montar: %s" % str(e)[:90]]
    passos.append("montei na chapa %dx%d (%s), pinca de %.0f mm, centrada: "
                  "%s" % (chapa[0], chapa[1], porque,
                          pinca_de(chapa, portao),
                          os.path.basename(montada)))
    # de onde saiu a conta da pinca, para quem le o log poder conferir
    # com a regua: a primeira linha de corte tem de cair na pinca
    passos.append("   a borda do arquivo ficou a %.1f mm do pe - %s"
                  % (base, de_onde))

    # E SEMPRE CONFERE - "sempre confere a pinca, para ver se esta
    # pincada", o operador em 17/09/2026.
    #
    # Conferir o que eu mesmo acabei de montar nao e desconfianca boba: a
    # conta acontece numa matriz de deslocamento que eu escrevo no PDF, e
    # entre escreve-la e ela valer ha um programa inteiro. Aqui se mede o
    # arquivo que SAIU, com o Ghostscript, que nao sabe o que eu quis.
    _, pe_arte, _ = medir_o_pe(montada)
    pinca = pinca_de(chapa, portao)
    if pe_arte is None:
        passos.append("   nao consegui conferir a pinca no arquivo montado")
    elif not esta_pincada(pe_arte, pinca):
        try:
            os.remove(montada)
        except OSError:
            pass
        return None, passos + [
            "PARO: montei e conferi, e o desenho ficou a %.0f mm do pe em "
            "vez dos %.0f da pinca. Nao mando o que nao confere"
            % (pe_arte, pinca)]
    else:
        passos.append("   pinca conferida no arquivo montado: o desenho "
                      "comeca a %.1f mm do pe (pinca %.0f)"
                      % (pe_arte, pinca))

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

def fechar(caminho, pasta_dia, con=None, so_olhar=False, portao=None):
    """
    Fecha UMA chapa. Devolve um relato do que foi feito.

    NA BANCADA (BANCADA no config) os passos 2 e 3 - a OS e a prova -
    saem de cena, porque a maquina de fora da grafica nao tem GEREMPRE
    nem impressora de chapa. Todo o resto acontece de verdade: a copia
    guardada, a chapa no CTP conferida, o registro e a limpeza do
    portao. A OS fica None, e o relato diz em todas as letras que nao
    houve OS - numero inventado e pior que numero nenhum.
    """
    # O CLIENTE DESTE PORTAO. Era a constante CLIENTE do modulo ate
    # 24/09/2026, quando a CARRIER entrou pelo mesmo caminho.
    cliente = _portao(portao)["cliente"]
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

    # NAO VEIO NO TAMANHO DA CHAPA? EU PONHO NELA - 23/09/2026.
    #
    # Regra do operador: "quando coloco no PARA CTP um arquivo, se for
    # arquivo que cabe no formato 4, vc revisa, veja a pinca, se ja
    # estiver no tamanho da chapa 525x459 e com a pinca de 6 cm, so da
    # andamento normal; se tiver fora do formato da chapa, e estiver no
    # formato 4, voce coloca na chapa 525x459, e pinca com 6 cm, e da
    # andamento; se o arquivo for maior, ele vai entrar na chapa
    # 745x605, com pinca de 6,2 cm".
    #
    # ATE HOJE ISTO PARAVA, e parar estava certo enquanto a FIA nao
    # sabia montar: ela pedia uma chapa com aquela medida exata ao
    # GEREMPRE e, nao achando, devolvia o arquivo para o portao. O caso
    # que derrubou a regra foi o 'FOLDER 2 DOBRAS 63X21 - MONTADO -
    # CERTO.pdf': ele chega 660 x 480 mm, que e TAMANHO DE PAPEL e nao
    # de chapa - "o cad 480x660 e so o tamanho do papel que eu coloquei,
    # nao o tamanho da chapa", como ele ja tinha dito em 21/09.
    #
    # O portao ja sabia fazer isso no outro caminho (ver onde_montar e
    # montar, usados quando a arte chega solta). O que faltava era a
    # montagem REVISADA poder passar por la tambem.
    #
    # O ORIGINAL NAO SE PERDE: a copia vai para a pasta do dia antes de
    # ele sair do portao, e e a montagem que segue viagem.
    if not chapa_de(larg, alt, portao):
        chapa_nova, porque = onde_montar(larg, alt, tintas, portao)
        if not chapa_nova:
            passo("PARO: %s" % porque)
            return relato
        if so_olhar:
            passo("montaria na chapa %dx%d (%s), pinca de %.0f mm"
                  % (chapa_nova[0], chapa_nova[1], porque,
                     pinca_de(chapa_nova, portao)))
            return relato
        montada = os.path.splitext(caminho)[0] + "_na_chapa.pdf"
        base, de_onde = pe_da_montagem(caminho, chapa_nova, portao)
        try:
            montar(caminho, chapa_nova, montada, portao)
        except Exception as e:
            passo("PARO: nao consegui montar na chapa (%s)" % str(e)[:80])
            return relato
        passo("nao veio no tamanho da chapa - montei na %dx%d (%s), "
              "pinca de %.0f mm, centrada"
              % (chapa_nova[0], chapa_nova[1], porque,
                 pinca_de(chapa_nova, portao)))
        passo("   a borda do arquivo ficou a %.1f mm do pe - %s"
              % (base, de_onde))
        try:
            guardar_copia(caminho, pasta_dia)
            os.remove(caminho)
        except Exception as e:
            passo("PARO: montei, mas nao consegui tirar do portao o "
                  "arquivo original (%s) - ficando os dois, sairiam duas "
                  "chapas e duas OS" % str(e)[:60])
            return relato
        caminho = montada
        larg, alt, tintas = medir(caminho)
        passo("a chapa montada: %.0f x %.0f mm, tintas %s"
              % (larg, alt, "".join(sorted(tintas)) or "?"))

    # A PINCA SE CONFERE SEMPRE, montada aqui ou nao.
    #
    # "nunca um arquivo pode ir sem pincar para o ctp" - o operador, em
    # 17/09/2026, e vale para as duas metades da regra de 23/09: quem ja
    # chega no tamanho da chapa ("vc revisa, veja a pinca") e quem acabou
    # de ser montado.
    #
    # Conferir o que a propria FIA montou nao e desconfianca boba: a
    # conta acontece numa matriz escrita no PDF, e entre escreve-la e ela
    # valer ha um programa inteiro. Quem mede aqui e o Ghostscript, que
    # nao sabe o que a FIA quis.
    #
    # E O MEDIDOR E DE PIXEL, de proposito. Depois da conversao a marca
    # do cliente virou imagem, e perguntar por traco vetorial devolveria
    # "sem marca" - que e como a chapa saiu errada de manha. O medir_o_pe
    # separa risco fino de desenho largo, entao a sangria de 2,75 mm que
    # desce abaixo do corte nao passa por invasao da pinca.
    chapa_atual = chapa_de(larg, alt, portao)
    if chapa_atual and not so_olhar:
        recado, pode = conferir_a_pinca(caminho, chapa_atual,
                                        portao)
        if recado:
            passo(recado)
        if not pode:
            passo("PARO: nao mando para o CTP chapa sem pinca")
            return relato

    achado = gerempre.chapa_do_servico(cliente, larg, alt)
    if not achado:
        passo("PARO: nao ha chapa cadastrada para %s em %.0fx%.0f"
              % (cliente, larg, alt))
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

    base = nome_da_chapa(caminho, larg, alt, tintas, portao)
    from .entrega import chegou_por_pagina, entregar_no_ctp, nome_da_pagina
    from .monitor import pasta_saida_do_dia

    # quantas chapas de METAL: paginas x tintas. Uma pagina em CMYK gasta
    # quatro - e o mesmo OSLAN 4 das OS que a casa ja abriu para a
    # AMERICA nesta chapa.
    paginas = len(pypdf.PdfReader(caminho).pages)

    # UM ARQUIVO POR PAGINA - a gravadora nao puxa multiplas paginas.
    #
    # A montagem que o programa faz sai sempre com uma pagina so, mas o
    # portao aceita o que o operador puser nele, e ele monta frente e
    # verso a mao. Em 17/09/2026 o 'PASTA PRE MEETING fv.pdf' foi para o
    # CTP com as duas paginas dentro: a OS cobrou as 8 chapas certas, a
    # prova saiu com as duas, e mesmo assim so uma seria gravada.
    nomes = ([base] if paginas <= 1
             else [nome_da_pagina(base, n) for n in range(1, paginas + 1)])
    passo("vai para o CTP como: %s"
          % ", ".join(n + ".pdf" for n in nomes))
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
    #
    # NA BANCADA NAO HA OS, e nao ha numero nenhum para por no lugar.
    # Inventar um seria pior do que nao ter: ele iria para o registro,
    # para o verso da prova e para o relato com cara de OS de verdade, e
    # um dia alguem o procuraria no GEREMPRE. O relato diz o que houve.
    if BANCADA:
        passo("BANCADA: NAO abri OS - esta maquina nao fala com o GEREMPRE. "
              "Na Finart este passo cobra %d chapa(s), R$ %.2f"
              % (quantas, quantas * preco))
    else:
        servico = {"titulo": titulo[:50], "cliente": cliente,
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
    #
    # NA BANCADA NAO HA IMPRESSORA DE CHAPA, e o 'sem prova, sem chapa'
    # fica de fora junto com ela. A regra nao afrouxou: ela existe para
    # que o operador tenha na mao o papel do servico que SAIU - e da
    # bancada nao sai servico nenhum, so arquivo de teste numa pasta
    # desta maquina.
    if BANCADA:
        passo("BANCADA: NAO imprimi a prova - nao ha impressora de chapa "
              "aqui. Na Finart ela sairia com a OS no verso")
        relato["prova"] = 0
    else:
        from .processador import _verso_da_os
        from .prova import JaImprimiu, imprimir
        verso = _verso_da_os(numero)
        try:
            _, folhas = imprimir(caminho,
                                 etiquetas=["AMERICA %s" % nome_chapa],
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

    # --- 4. a chapa no CTP, UM ARQUIVO POR PAGINA ---
    saidas = entregar_no_ctp(caminho, pasta_saida_do_dia(), base)
    if paginas <= 1:
        # com uma pagina a prova e a mais forte que existe: byte por byte
        ok, porque = chegou_inteira(caminho, saidas[0])
    else:
        ok, porque = chegou_por_pagina(saidas, paginas)
    if not ok:
        passo("PARO: a chapa nao chegou inteira no CTP (%s). NAO apaguei"
              % porque)
        return relato
    passo("chapa no CTP, conferida (%d arquivo%s, %.1f MB)"
          % (len(saidas), "s" if len(saidas) > 1 else "",
             sum(os.path.getsize(s) for s in saidas) / 1048576.0))
    relato["chapa_no_ctp"] = saidas[0]
    relato["saidas"] = [os.path.basename(s) for s in saidas]

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
        "cliente": cliente, "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "saidas": relato["saidas"], "os": relato.get("os"),
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


# As duas subpastas que a pasta do dia da AMERICA tem de ter. A ordem
# aqui e a ordem do trabalho: o arquivo chega na PARA MONTAR, e sai
# montado pela PARA CTP.
PORTOES_DO_DIA = (SUBPASTA_PARA_MONTAR, PORTAO)


def subpastas_do_dia(portao=None):
    """
    As subpastas que a pasta do dia deste cliente tem de ter.

    A CARRIER TEM SO A 'PARA CTP' - pedido do operador em 24/09/2026:
    "crie uma pasta PARA CTP". A montagem dela e feita a mao por eles,
    fora da FIA, entao a 'PARA MONTAR' nao teria quem a enchesse nem
    quem a esvaziasse. Pasta vazia que ninguem usa vira lugar onde
    arquivo se perde.
    """
    return (PORTOES_DO_DIA if _portao(portao)["para_montar"]
            else (PORTAO,))


def garantir_pastas_do_dia(quando=None, portao=None):
    r"""
    Cria <BASE>\<MES>\<DIA> e, dentro dela, a PARA MONTAR e a PARA CTP.

    Devolve (pasta_do_dia, [o que foi criado agora], recado_de_erro). Com
    tudo ja no lugar, a lista vem vazia e o recado vem None - que e o
    caso de toda volta do laco menos a primeira do dia.

    NAO ESTOURA: a base da AMERICA esta no servidor, e rede caida nao
    pode derrubar o vigia dos outros clientes nem a tela da equipe.

    POR QUE A FIA CRIA, e nao gente. Pedido do operador em 18/09/2026.
    Antes, a pasta era combinado entre pessoas, e o preco era uma tarefa
    diaria caindo justamente em cima de quem o sistema existe para
    desamarrar: a pasta do dia e nova todo dia, e sem ela a equipe nao
    tinha onde soltar o que chegou por montar.

    O QUE ISSO CUSTA, e e o motivo de eu ter perguntado antes de fazer:
    enquanto o portao era criado por gente, a pasta faltando queria dizer
    'ninguem preparou o dia ainda' - coisa normal de uma manha cedo. Com
    a FIA criando, faltar passa a querer dizer OUTRA coisa, e uma coisa
    ruim: ou a FIA nao rodou hoje, ou nao conseguiu escrever no servidor.
    A tela da fila diz isso com essas palavras, e nao manda mais ninguem
    criar pasta na mao.

    E POR ISSO OS DOIS PROCESSOS CHAMAM AQUI - o vigia a cada volta e o
    servidor da fila ao desenhar a tela. Sao processos separados de
    proposito (um cair nao derruba o outro), e se so o vigia criasse, a
    equipe abrindo a tela antes de alguem ligar a FIA veria o erro sem
    haver erro nenhum. Quem chegar primeiro cria; makedirs com
    exist_ok=True nao se importa de perder a corrida.

    O MES TAMBEM E CRIADO, e so no dia 1o isso importa. O nome sai do
    localizar_pasta_mes, que primeiro PROCURA o mes ja escrito do jeito
    do cliente (SETEMBRO, Setembro, setembro) e so escreve um novo quando
    nao acha nenhum - senao o dia 1o de outubro nasceria numa segunda
    pasta de outubro, ao lado da que o cliente ja usava.
    """
    from .monitor import localizar_pasta_mes, pasta_do_dia

    criados = []
    try:
        # A BASE VEM DO PORTAO, e nao do BASE_AMERICA.
        #
        # Esquecer isto criou a pasta da CARRIER DENTRO da AMERICA, em
        # 24/09/2026, e sem dar erro nenhum: a funcao respondeu 'ja
        # existiam' porque a PARA CTP da AMERICA realmente existe. So
        # olhando o caminho impresso e que apareceu.
        base = _portao(portao)["base"]
        mes = localizar_pasta_mes(base, criar=True)
        if not mes:
            return None, criados, "nao achei nem consegui criar a pasta do mes"
        dia = os.path.join(base, mes, pasta_do_dia())
        if not os.path.isdir(dia):
            os.makedirs(dia, exist_ok=True)
            criados.append(os.path.basename(dia))
        for sub in subpastas_do_dia(portao):
            alvo = os.path.join(dia, sub)
            if not os.path.isdir(alvo):
                os.makedirs(alvo, exist_ok=True)
                criados.append(sub)
        return dia, criados, None
    except OSError as e:
        # Pasta de cliente no servidor: pode estar fora do ar, ou
        # so-leitura para nos. Nenhum dos dois e motivo para parar o dia.
        return None, criados, str(e)[:160]


def rodada(avisados=None, portao=None):
    """
    Uma volta do vigia no portao deste cliente. Fecha o que estiver pronto.

    Chamada de dentro do laco do monitor, a cada INTERVALO. Devolve a
    lista de relatos do que foi fechado nesta volta - vazia quando nao
    havia nada, que e o normal.

    NAO ESTOURA para cima: o portao da AMERICA quebrando nao pode derrubar
    o vigia dos outros seis clientes.
    """
    avisados = avisados if avisados is not None else {}
    feitos = []
    try:
        # A PASTA DO DIA E OS DOIS PORTOES, ANTES DE OLHAR PARA DENTRO.
        #
        # Toda volta, e de graca quando ja existe: o makedirs so escreve
        # na primeira do dia. Falhar aqui NAO para a rodada - a pasta
        # pode existir e so o portao ter falhado, e ai ainda ha o que
        # fechar.
        cliente = _portao(portao)["cliente"]
        _, criados, erro = garantir_pastas_do_dia(quando=None, portao=portao)
        if criados:
            log("%s: preparei a pasta do dia - criei %s"
                % (cliente, ", ".join("'%s'" % c for c in criados)))
        if erro and avisados.get("_pastas") != erro:
            # UMA VEZ POR MOTIVO, e nao a cada volta: sem isto, servidor
            # fora do ar escreve uma linha por minuto e afoga o log.
            avisados["_pastas"] = erro
            log("%s: nao consegui preparar a pasta do dia (%s)"
                % (cliente, erro),
                alerta=True)
        elif not erro:
            avisados.pop("_pastas", None)

        # A PASTA chama-se pasta_portao, e nao 'portao': desde
        # 24/09/2026 'portao' e o CLIENTE - o descritor que diz qual
        # cliente esta sendo varrido. Os dois com o mesmo nome no mesmo
        # escopo se atropelavam em silencio.
        dia, pasta_portao = pasta_do_dia_america(portao=portao)
        if not dia or not os.path.isdir(pasta_portao):
            return feitos

        for nome in sorted(os.listdir(pasta_portao)):
            baixo = nome.lower()
            if not baixo.endswith((".pdf", ".cdr")):
                continue
            caminho = os.path.join(pasta_portao, nome)

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
                abrir_bloco(cliente, nome)
                try:
                    log("convertendo no CorelDRAW")
                    pronto, passos = converter(caminho, dia)
                    for p in passos:
                        log("   %s" % p)
                finally:
                    fechar_bloco()
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

            abrir_bloco(cliente, nome)
            try:
                log("fechando a montagem revisada")
                relato = fechar(caminho, dia, portao=portao)
                for p in relato["passos"]:
                    log("   %s" % p)
            finally:
                fechar_bloco()
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
