# -*- coding: utf-8 -*-
"""
Processa um arquivo do cliente.

Dois clientes passam por aqui, e a diferenca entre eles esta so nas pontas:

  SOLIDA  PDF pronto  -> nome pela OS       49576R1
  VOPRIX  .cdr        -> nome pelo formato  510x400_CM_VOPRIX_Envelope_Saco

O .cdr da VOPRIX vira PDF pelo CorelDRAW da propria maquina (corel.py),
com a predefinicao FINART - a mesma que o operador usa a mao.

Dai em diante ha DOIS caminhos ate a chapa, e a prova impressa e a OS
sao iguais nos dois:

  o longo   separa as tintas no Ghostscript e remonta o PDF. E o de
            sempre, e o de quem precisa girar ou montar a arte na chapa;
  o curto   entrega o PDF do cliente inteiro, e quem separa e a
            gravadora. So para arte que ja chega pronta, no tamanho da
            chapa - hoje a VOPRIX (ENTREGAR_PDF_DIRETO).

O curto nasceu de uma chapa errada: a leitura do Ghostscript passava a
cor pelo perfil ICC embutido pela Corel e remisturava o preto de K
sozinho nas quatro tintas. Os numeros estao em entrega.py.

O arquivo de origem NUNCA e movido nem apagado: a pasta e compartilhada.
Quem controla o que ja foi feito e o registro, em utils.py.
"""

import glob
import os
import re
import shutil
import tempfile
import time

from .config import (AVISAR_QUANDO_NAO_FOR_CMYK,
                     CLIENTES_SEM_TRAVA_DE_RESOLUCAO, ENCAIXE_MAXIMO_MM,
                     ARREDONDAMENTO_MM,
                     CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO,
                     CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO,
                     CLIENTES_QUE_SALVAM_A_MONTAGEM,
                     CLIENTES_QUE_VEM_DO_COREL,
                     ENTREGAR_PDF_DIRETO, FORMATOS, FORMATOS_PRIME,
                     PINCA_PRIME_MM, ROTULOS_PROVA_PRIME,
                     TINTA_QUE_E_SO_TRACO,
                     FORMATOS_CREATIVE, FORMATOS_EMPORIO, FORMATOS_FIALHO,
                     FORMATOS_VIVA, FORMATOS_VOPRIX,
                     IMPRESSORA, IMPRIMIR_ORIGINAL,
                     GIRO_CREATIVE, NOMES_TINTA, PASTA_CONTROLE,
                     PINCA_CREATIVE_MM,
                     ROTULOS_PROVA, ROTULOS_PROVA_CREATIVE,
                     ROTULOS_PROVA_EMPORIO, ROTULOS_PROVA_FIALHO,
                     ROTULOS_PROVA_VIVA, ROTULOS_PROVA_VOPRIX,
                     TAMANHO_MAXIMO_MB, TOLERANCIA_MM)
from .corel import ArquivoEmUso, publicar_pdf
from .entrega import conferir as conferir_entrega
from .entrega import entregar
from .marcas import marcas_de_corte, pistas_da_marca
from .ghostscript import (LIMIAR_TINTA, cobertura_por_pagina, sem_cor_gritante,
                          separar_cinza, separar_tintas, tinta_aparece_sozinha,
                          tintas_da_cobertura)
from .prova import JaImprimiu, imprimir
from .os_impressa import apagar_pdf, folha_da_os, guardar_pdf
from .nomes import (extrair_oss, nome_saida, nome_saida_creative,
                    nome_saida_emporio, nome_saida_fialho, nome_saida_prime,
                    nome_saida_viva, nome_saida_voprix, pede_olho,
                    sufixo_pagina)
from .pdf_builder import conferir_resolucao, montar_pdf, montar_pdf_cinza
from .preflight import PARA, conferir_arte, e_de_resolucao
from .utils import (anotar_pendencia, guardar_para_a_mao, log, nome_livre,
                    renomear_saida_no_registro)

SOLIDA = "SOLIDA"
VOPRIX = "VOPRIX"
FIALHO = "FIALHO"
EMPORIO = "EMPORIO"
VIVA = "VIVA"
CREATIVE = "CREATIVE"
PRIME = "PRIME"


def medir_paginas(pdf):
    """[(largura_mm, altura_mm), ...] - uma por pagina, ja com /Rotate."""
    from pypdf import PdfReader
    r = PdfReader(pdf)
    medidas = []
    for p in r.pages:
        b = p.mediabox
        larg, alt = float(b.width) / 72 * 25.4, float(b.height) / 72 * 25.4
        if ((p.get("/Rotate") or 0) % 360) in (90, 270):
            larg, alt = alt, larg
        medidas.append((larg, alt))
    return medidas


def formatos_do_cliente(cliente=SOLIDA):
    """
    A tabela de chapas desse cliente.

    Cada um tem a sua chapa grande: 775x635 na Solida e na VOPRIX,
    730x600 no Fialho, 660x605 no Emporio. Uma nao vale na outra.
    """
    if cliente == FIALHO:
        return FORMATOS_FIALHO
    if cliente == EMPORIO:
        return FORMATOS_EMPORIO
    if cliente == VIVA:
        return FORMATOS_VIVA
    if cliente == CREATIVE:
        return FORMATOS_CREATIVE
    if cliente == VOPRIX:
        return FORMATOS_VOPRIX
    if cliente == PRIME:
        return FORMATOS_PRIME
    return FORMATOS


def casar_formato(larg, alt, cliente=SOLIDA):
    """Chave do formato cadastrado que bate com a medida, ou None."""
    medido = sorted([larg, alt])
    for chave in formatos_do_cliente(cliente):
        alvo = sorted(chave)
        if (abs(medido[0] - alvo[0]) <= TOLERANCIA_MM and
                abs(medido[1] - alvo[1]) <= TOLERANCIA_MM):
            return chave
    return None


def identificar_formato(larg, alt, cliente=SOLIDA):
    """(dpi, sufixo) do formato que bate, ou (None, None)."""
    chave = casar_formato(larg, alt, cliente)
    return formatos_do_cliente(cliente)[chave] if chave else (None, None)


def formato_no_nome(larg, alt, cliente=SOLIDA):
    """'510x400' - como o formato entra no nome de saida."""
    chave = casar_formato(larg, alt, cliente)
    return "%dx%d" % chave if chave else ""


def encaixar_formato(larg, alt, cliente=SOLIDA):
    """
    Chapa em que essa arte cabe centralizada, ou None.

    So o FIALHO. A arte dele as vezes vem alguns milimetros fora da
    chapa: o 'CAPA Agenda PAULISTA 2027.pdf' mede 520x400 e e chapa
    510x400. Ate ENCAIXE_MAXIMO_MM de diferenca a arte entra
    centralizada - CORTANDO 5 mm de cada lado, no caso dele.

    E corte mesmo, nao reducao: nada e redimensionado, para a arte
    chegar na chapa do tamanho que foi desenhada. Por isso o limite e
    curto - acima dele ninguem sabe o que pode ser cortado.
    """
    if cliente != FIALHO:
        return None
    medido = sorted([larg, alt])
    for chave in formatos_do_cliente(cliente):
        alvo = sorted(chave)
        if (abs(medido[0] - alvo[0]) <= ENCAIXE_MAXIMO_MM and
                abs(medido[1] - alvo[1]) <= ENCAIXE_MAXIMO_MM):
            return chave
    return None


def chapa_no_sentido(chave, larg, alt):
    """A chapa virada no mesmo sentido da arte: (510,400) ou (400,510)."""
    menor, maior = sorted(chave)
    return (menor, maior) if larg <= alt else (maior, menor)


# Girando a folha, qual borda do ARQUIVO vira o pe da chapa. Gire uma
# folha 90 graus para a direita: a borda da direita desce e vira o pe.
LADO_DA_PINCA = {0: "pe", 90: "direita", 180: "topo", 270: "esquerda"}


def giro_da_pagina(larg, alt, cliente):
    """
    Quantos graus girar esta pagina antes de montar na chapa.

    So a Creative, e so quando a arte chega EM PE: girada, ela volta a
    ser o que sempre chega - deitada -, e ai cabe na 510x400.

    Nada e redimensionado. Girar 90 graus e trocar linha por coluna: o
    desenho sai do outro lado do mesmo tamanho, ate o ultimo pixel.
    """
    if cliente != CREATIVE or alt <= larg:
        return 0
    return GIRO_CREATIVE


def pinca_do_cliente(cliente):
    """Quantos mm de pinca esse cliente pede, ou 0 se nao usa."""
    if cliente == CREATIVE:
        return PINCA_CREATIVE_MM
    if cliente == PRIME:
        return PINCA_PRIME_MM
    return 0


def montar_na_chapa(larg, alt, cliente, corte=0.0):
    """
    Chapa em que essa arte MENOR pode ser montada, ou None.

    E o caso da CREATIVE: a arte nao vem no tamanho da chapa - chega
    480x330, por exemplo - e o programa monta na 510x400, trabalho que
    ate hoje se fazia a mao no InDesign.

    Cabe quando, na chapa, ainda sobra a pinca embaixo:

        largura da arte           <=  largura da chapa
        altura da arte + (pinca - corte)  <=  altura da chapa

    'corte' e a distancia da borda de baixo do arquivo ate a marca de
    corte. A pinca se mede DA MARCA, entao o que a arte gasta abaixo dela
    e 'pinca - corte', e nao a pinca inteira.

    Nada e reduzido nem esticado: a arte entra do tamanho que foi
    desenhada, senao o corte cai fora do lugar.
    """
    if not pinca_do_cliente(cliente):
        return None
    # o que fica entre o pe da chapa e a borda de baixo da arte
    base = pinca_do_cliente(cliente) - corte
    if base < 0:
        return None            # marca fundo demais: a arte cairia fora
    # A chapa NAO se vira: a pinca e uma borda fisica dela, a que a
    # maquina segura. Virar a chapa poria a pinca no lugar errado. Quem
    # se vira e a arte, antes de chegar aqui (giro_da_pagina).
    for chapa in formatos_do_cliente(cliente):
        if larg <= chapa[0] + TOLERANCIA_MM and \
                alt + base <= chapa[1] + TOLERANCIA_MM:
            return chapa
    return None


def posicao_na_chapa(larg, alt, chapa, cliente, corte=0.0):
    """
    (esquerda_mm, topo_mm) onde a arte comeca na chapa.

    Centralizada na largura. Na altura manda a PINCA, que fica no PE da
    chapa - e ela se mede da MARCA DE CORTE, nao da borda do arquivo:

        borda de baixo da arte = pinca - corte

    'corte' e a distancia da borda de baixo do arquivo ate a marca de
    corte (marcas.py). No santinho da Creative sao 12,0 mm: a arte encosta
    a 28,0 mm do pe da chapa, e a marca fica nos 40 mm pedidos.

    Medir da borda do arquivo, como se fez primeiro, punha a arte 12 mm
    fora do lugar - o operador viu na hora, olhando a marca.

    Confere com a chapa fechada a mao em 02/09: arte de 480x330 na chapa
    de 510x400, 15,0 mm de cada lado e 28,0 mm entre a borda da arte e a
    da chapa, do lado da pinca.
    """
    pinca = pinca_do_cliente(cliente)
    esquerda = (chapa[0] - larg) / 2.0
    base = pinca - corte                 # da borda da arte ao pe da chapa
    topo = chapa[1] - base - alt
    return esquerda, topo


def chapa_da_pagina(larg, alt, cliente=SOLIDA, corte=0.0):
    """
    (chapa_em_mm, dpi, sufixo, encaixou) da pagina, pela tabela do cliente.

    Primeiro a medida exata, dentro da TOLERANCIA_MM. Nao achando, tenta
    encaixar - e ai a chapa devolvida e a do CADASTRO, nao a da arte,
    porque o que vai ser gravado tem o tamanho da chapa.

    Sem chapa nenhuma: (None, None, None, False).
    """
    chave = casar_formato(larg, alt, cliente)
    if chave:
        dpi, sufixo = formatos_do_cliente(cliente)[chave]
        chapa = chapa_no_sentido(chave, larg, alt)
        perto = (abs(larg - chapa[0]) <= ARREDONDAMENTO_MM
                 and abs(alt - chapa[1]) <= ARREDONDAMENTO_MM)
        if perto or pinca_do_cliente(cliente):
            return (larg, alt), dpi, sufixo, False

        # A ARTE NAO TEM A MEDIDA DA CHAPA - entra CENTRALIZADA nela.
        #
        # "chapa da viva quando vier com tamanho diferente, com poucos
        # milimetros de diferenca, pode centralizar na chapa 510x400, e
        # dar andamento normal, nao parar mais" - o operador, 14/09/2026.
        #
        # Sem isto sai uma chapa que MENTE sobre o proprio tamanho: o
        # 'GRADE 3385' da VIVA foi gerado com 510 x 399 mm e nome
        # '510x400_CMYK_VIVA_GRADE 3385'. E a OS nem chegava a abrir - a
        # busca de preco e exata, e nao ha 399x510 na tabela: "nao sei
        # que chapa usar para VIVA 510x399. Lance a mao".
        #
        # Nao e caso da VIVA: o registro tem uma do EMPORIO,
        # 509,764 x 398,992, que saiu assim e ninguem viu.
        #
        # QUEM TEM PINCA FICA DE FORA, ali em cima. Para a CREATIVE e a
        # PRIME, arte do tamanho da chapa quer dizer 'ja montada'; caindo
        # aqui, ela seria remontada pela marca de corte e sairia do
        # lugar. A arte MENOR delas continua indo por montar_na_chapa.
        return chapa, dpi, sufixo, True

    chave = encaixar_formato(larg, alt, cliente)
    if chave:
        dpi, sufixo = formatos_do_cliente(cliente)[chave]
        return chapa_no_sentido(chave, larg, alt), dpi, sufixo, True

    # arte menor que a chapa, para ser MONTADA nela (Creative)
    chapa = montar_na_chapa(larg, alt, cliente, corte)
    if chapa:
        tabela = formatos_do_cliente(cliente)
        chave = next(c for c in tabela if sorted(c) == sorted(chapa))
        dpi, sufixo = tabela[chave]
        return chapa, dpi, sufixo, True

    return None, None, None, False


def pixels_da_chapa(larg_mm, alt_mm, dpi):
    """Quantos pixels a chapa tem no dpi de gravacao."""
    return (int(round(larg_mm / 25.4 * dpi)), int(round(alt_mm / 25.4 * dpi)))


def chapas_aceitas(cliente=SOLIDA):
    """'510x400 ou 730x600' - para dizer no aviso o que era esperado."""
    return " ou ".join("%dx%d" % c for c in formatos_do_cliente(cliente))


def chapa_prevista(larg, alt, cliente=SOLIDA):
    """
    Em que chapa esta pagina deve entrar, ou None se em nenhuma.

    E a resposta ANTES da separacao, quando ainda nao se leu a marca de
    corte. Serve para duas decisoes que vem cedo: se vale imprimir a
    prova e o que escrever na etiqueta dela.

    Considera o mesmo caminho do processamento de verdade - medida
    exata, encaixe do Fialho, montagem da Creative - e considera o GIRO:
    arte que chega em pe sera girada antes de entrar na chapa, e sem
    isso ela nao casaria com chapa nenhuma.

    Foi por nao considerar o giro que a prova do 'unirv blocos rascunho
    13 08.pdf' nao saiu: as duas paginas vinham 330x480, a porteira nao
    reconheceu chapa e nao imprimiu nada - mas as chapas foram geradas
    do mesmo jeito, e o operador ficou sem o papel na mesa.
    """
    if giro_da_pagina(larg, alt, cliente):
        larg, alt = alt, larg
    return (casar_formato(larg, alt, cliente)
            or encaixar_formato(larg, alt, cliente)
            # cabendo na chapa, e aquela chapa: a folga da marca de corte
            # nao muda de qual chapa se trata
            or montar_na_chapa(larg, alt, cliente,
                               corte=pinca_do_cliente(cliente)))


def rotulo_prova(larg, alt, cliente=SOLIDA):
    """Texto que vai no canto da folha de prova. Vazio se nao reconhecer."""
    tabela = ROTULOS_PROVA
    if cliente == VOPRIX:
        tabela = ROTULOS_PROVA_VOPRIX
    elif cliente == FIALHO:
        tabela = ROTULOS_PROVA_FIALHO
    elif cliente == EMPORIO:
        tabela = ROTULOS_PROVA_EMPORIO
    elif cliente == VIVA:
        tabela = ROTULOS_PROVA_VIVA
    elif cliente == CREATIVE:
        tabela = ROTULOS_PROVA_CREATIVE
    elif cliente == PRIME:
        tabela = ROTULOS_PROVA_PRIME
    return tabela.get(chapa_prevista(larg, alt, cliente), "")


def sem_tinta_de_traco(cob, usadas):
    """
    (tintas que viram chapa, tintas descartadas) - as de traco caem.

    Uma tinta que aparece com 1% do que a mais forte tem nao e chapa: e
    barra de controle, fio de registro, respingo de conversao. Gravar
    uma chapa para ela custa chapa, gravacao e uma linha a mais na OS.

    Medido nas tres OS da PRIME de 14/09/2026, contra o que o GEREMPRE
    baixou do estoque (-1, -3 e -4):

        VALDINO    CMY 0,06% do K    -> 1 chapa, e so o K
        POLIPECAS  Y   1,07%         -> 3 chapas, sem o amarelo
        WAN        K  38,7%          -> 4 chapas, todas de verdade

    Ver TINTA_QUE_E_SO_TRACO. So vale para cliente que esta na lista:
    descartar tinta demais e chapa que FALTA no CTP.
    """
    escala = {t: cob.get(t, 0.0) for t in usadas if t in "CMYK"}
    if not escala:
        return set(usadas), set()
    forte = max(escala.values())
    if forte <= LIMIAR_TINTA:
        return set(usadas), set()
    fora = {t for t, v in escala.items()
            if v < TINTA_QUE_E_SO_TRACO * forte}
    return set(usadas) - fora, fora


def pagina_de_uma_cor(cob, folga=0.02):
    """
    True quando a pagina e preto sozinho - puro ou composto.

    Arte de uma cor nem sempre chega como preto puro: as vezes o preto
    vem composto, com C, M, Y e K juntos. O que denuncia isso e a
    cobertura das tres cores dar o MESMO numero (num arquivo real:
    C 0.06081, M 0.06079, Y 0.06080, K 0.05444). Arte colorida nunca faz
    isso - cada canal tem o seu total.

    ATENCAO A DE ONDE VEM ESSE NUMERO. Durante um tempo este comentario
    dizia que 'a Corel exporta o preto composto', e era falso: a Corel
    escreve '0 0 0 1' no arquivo, com o preto no K. Quem compunha o preto
    era a nossa leitura, ao passar a cor pelo perfil ICC embutido antes
    de contar (ver ghostscript.sem_perfil). Lendo o mesmo arquivo sem o
    perfil, o preto reaparece inteiro no K.

    Rodar esse arquivo como quadricromia daria QUATRO chapas onde o
    trabalho pede uma; e pegar so o canal K daria chapa lavada, porque o
    preto esta espalhado pelos quatro canais.
    """
    cmy = [cob["C"], cob["M"], cob["Y"]]
    if max(cmy) <= LIMIAR_TINTA:
        return cob["K"] > LIMIAR_TINTA               # preto puro
    return (max(cmy) - min(cmy)) <= folga * max(cmy)  # preto composto


# Quanto de CMY ainda conta como TRACO, em proporcao ao K.
#
# O limiar era ABSOLUTO (LIMIAR_TINTA, 0,01%) e isso errou feio em
# 14/09/2026. O 'Bloco_21x29,7_1_1_Engquer' da VOPRIX tem C=M=Y=0,232% e
# K=8,893%: o CMY vale 2,61% do preto - serrilha, nao cor. Pelo limiar
# absoluto ele virou 'preto composto', foi convertido COM o perfil e a
# chapa saiu com 3,94% de tinta onde o arquivo tinha 9,61%. Menos da
# metade, e ninguem veria antes da tiragem.
#
# A proporcao separa os dois casos com folga de ordem de grandeza:
#
#     traco (Bloco da VOPRIX)          CMY = 2,61% do K
#     preto composto de verdade        CMY = 100% do K, ou mais
#         (o 49835 lido com perfil da 100,06%;
#          o exemplo antigo da Corel, 111,7%)
#
# 10% e escolha minha, e esta marcada como tal: quatro vezes acima do
# traco medido e dez vezes abaixo do composto mais magro que ja se viu.
CMY_QUE_AINDA_E_TRACO = 0.10


def preto_so_no_K(cob):
    """
    True quando a arte esta INTEIRA no canal do preto - traco incluido.

    Diferente de pagina_de_uma_cor, que responde 'vale uma chapa so' e
    aceita os dois pretos - o puro e o composto. Aqui a pergunta e outra
    e mais fina: EM QUE CANAL a tinta esta. Ela decide como a chapa e
    gerada, porque preto puro e preto composto pedem caminhos opostos no
    Ghostscript (ver separar_cinza).

    SO FAZ SENTIDO NUMA COBERTURA LIDA SEM O PERFIL ICC. Com o perfil, o
    preto de K sozinho aparece espalhado nos quatro canais e esta conta
    responde False para uma arte que e puro K - foi o que escondeu o
    '49835 - Flor Bela - sacola' da SOLIDA.
    """
    if cob["K"] <= LIMIAR_TINTA:
        return False                     # nao ha preto nenhum
    cmy = max(cob["C"], cob["M"], cob["Y"])
    if cmy <= LIMIAR_TINTA:
        return True                      # K sozinho, sem um traco
    return cmy <= CMY_QUE_AINDA_E_TRACO * cob["K"]


def proxima_sequencia(pasta_saida, prefixo):
    """
    O proximo numero livre da sequencia do dia para esse trabalho.

    As chapas do Fialho sao numeradas por TRABALHO e por DIA, e nao por
    arquivo: as 11 chapas de UNICIDADES de um dia sairam 01 a 11 mesmo
    vindo de tres PDFs diferentes (forro, introducao e divisoria). Por
    isso a conta se faz olhando a pasta de saida, nao o arquivo de origem.
    """
    padrao = re.compile(r"^%s (\d+)\.pdf$" % re.escape(prefixo), re.IGNORECASE)
    maior = 0
    try:
        nomes = os.listdir(pasta_saida)
    except OSError:
        return 1
    for nome in nomes:
        achou = padrao.match(nome)
        if achou:
            maior = max(maior, int(achou.group(1)))
    return maior + 1


def resolver_modelo(pasta_saida, base):
    """
    (base_a_usar, renomeada) quando outra arte ja ocupa esse nome.

    Combinado com o operador: as duas passam a se chamar MODELO, e a que
    JA ESTAVA GRAVADA e renomeada para 'MODELO 1'. Sem isso ficaria uma
    chapa com nome limpo e outra com numero, e ninguem saberia que sao
    duas artes diferentes do mesmo cliente e produto.

    'renomeada' e (de, para) quando houve renomeacao, ou None.
    """
    padrao = re.compile(r"^%s MODELO (\d+)\.pdf$" % re.escape(base), re.I)
    maior = 0
    try:
        for nome in os.listdir(pasta_saida):
            achou = padrao.match(nome)
            if achou:
                maior = max(maior, int(achou.group(1)))
    except OSError:
        pass

    if maior:                                  # a serie ja existe
        return "%s MODELO %d" % (base, maior + 1), None

    limpo = os.path.join(pasta_saida, base + ".pdf")
    if os.path.exists(limpo):
        primeiro = "%s MODELO 1" % base
        os.replace(limpo, os.path.join(pasta_saida, primeiro + ".pdf"))
        renomear_saida_no_registro(base + ".pdf", primeiro + ".pdf")
        return "%s MODELO 2" % base, (base + ".pdf", primeiro + ".pdf")

    return base, None


def numerar_se_preciso(pasta_saida, base, forcar=False):
    """
    (nome_a_usar, renomeada) - o numero so entra quando ha mais de uma.

    Chapa sozinha nao leva numero: '510x400_FIALHO_PAULISTA', e nao
    '... 01'. Quando aparece a segunda, a primeira - que JA ESTA GRAVADA -
    e renomeada para ' 01' e a nova sai ' 02', igual ao MODELO da VOPRIX:
    uma com nome limpo e outra numerada esconderia que sao duas.

    forcar=True numera desde a primeira. E o arquivo de varias paginas,
    onde ja se sabe, antes de gravar, que virao outras.

    'renomeada' e (de, para) quando houve renomeacao, ou None.
    """
    padrao = re.compile(r"^%s (\d+)\.pdf$" % re.escape(base), re.IGNORECASE)
    maior = 0
    try:
        for nome in os.listdir(pasta_saida):
            achou = padrao.match(nome)
            if achou:
                maior = max(maior, int(achou.group(1)))
    except OSError:
        pass

    if maior:                                   # a serie ja existe
        return "%s %02d" % (base, maior + 1), None

    limpo = os.path.join(pasta_saida, base + ".pdf")
    if os.path.exists(limpo):
        primeiro = "%s 01" % base
        os.replace(limpo, os.path.join(pasta_saida, primeiro + ".pdf"))
        renomear_saida_no_registro(base + ".pdf", primeiro + ".pdf")
        return "%s 02" % base, (base + ".pdf", primeiro + ".pdf")

    return ("%s 01" % base if forcar else base), None


def nome_da_chapa(cliente, nome, sufixo, larg, alt, tintas, indice, total,
                  pasta_saida=None):
    """Nome de saida (sem .pdf), pela regra do cliente."""
    if cliente == VOPRIX:
        return nome_saida_voprix(nome, formato_no_nome(larg, alt, cliente),
                                 tintas, indice, total)
    if cliente == EMPORIO:
        return nome_saida_emporio(nome, formato_no_nome(larg, alt, cliente),
                                  tintas, indice, total)
    if cliente == VIVA:
        return nome_saida_viva(nome, formato_no_nome(larg, alt, cliente),
                               tintas, indice, total)
    if cliente == PRIME:
        return nome_saida_prime(nome, formato_no_nome(larg, alt, cliente),
                                tintas, indice, total)
    if cliente == CREATIVE:
        return nome_saida_creative(nome,
                                   formato_no_nome(larg, alt, cliente),
                                   tintas, indice, total)
    if cliente == FIALHO:
        # o numero entra no laco, olhando a pasta - so quando ha mais de
        # uma chapa com o mesmo nome
        return nome_saida_fialho(nome, formato_no_nome(larg, alt, cliente),
                                 tintas)
    return nome_saida(nome, sufixo or "", indice, total)


def acima_do_limite(caminho):
    """Motivo da recusa por tamanho, ou '' se o arquivo couber."""
    mb = os.path.getsize(caminho) / 1048576
    if mb <= TAMANHO_MAXIMO_MB:
        return ""
    return ("arquivo gigante: %.0f MB, acima do limite de %d MB. "
            "Nao processei - precisa ser tratado a mao"
            % (mb, TAMANHO_MAXIMO_MB))


def converter_cdr(caminho):
    """
    (pdf, pasta_temporaria) do .cdr publicado pelo CorelDRAW.

    O PDF sai no disco local: a Corel exporta arquivos enormes e isso nao
    pode passar pela rede. Quem chamou apaga a pasta no fim.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_cdr_", dir=PASTA_CONTROLE)
    base = os.path.splitext(os.path.basename(caminho))[0]
    try:
        return publicar_pdf(caminho, os.path.join(tmp, base + ".pdf")), tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def salvar_montagem(origem_pdf, pagina, destino, chapa, esquerda, base,
                    girar=0):
    """
    Grava A MONTAGEM: a arte assentada na chapa, em vetor. Devolve o
    caminho.

    Pedido do operador, 14/09/2026: "voce vai salvar de novo na pasta do
    dia com o mesmo nome mas _montagem no final... depois disso vai pegar
    essa montagem e continuar o procedimento normalmente".

    E o passo que ele faz a mao hoje, e serve para duas coisas: fica na
    pasta do dia para ser conferido, e e DELA que a chapa do CTP e
    gerada - entao o que foi para a gravadora e exatamente o que esta
    ali para olhar.

    Vai em VETOR, nao rasterizado: e leve, abre em qualquer lugar e nao
    perde nada. A conta de onde a arte encosta e a mesma de
    posicao_na_chapa - 'base' e o que fica entre o pe da chapa e a borda
    de baixo da arte, ja descontada a marca de corte.
    """
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject

    leitor = PdfReader(origem_pdf)
    arte = leitor.pages[pagina - 1]
    if girar:
        arte.rotate(girar)
        arte.transfer_rotation_to_content()

    caixa = arte.mediabox
    lw, lh = chapa[0] / 25.4 * 72, chapa[1] / 25.4 * 72
    folha = PageObject.create_blank_page(width=lw, height=lh)
    # a arte pode nao comecar em (0,0): o deslocamento se mede da
    # esquerda e do pe DELA, nao da origem do PDF
    tx = esquerda / 25.4 * 72 - float(caixa.left)
    ty = base / 25.4 * 72 - float(caixa.bottom)
    folha.merge_transformed_page(arte, Transformation().translate(tx, ty))
    folha.mediabox = RectangleObject((0, 0, lw, lh))

    escritor = PdfWriter()
    escritor.add_page(folha)
    with open(destino, "wb") as f:
        escritor.write(f)
    return destino


def caminho_da_montagem(origem, indice=0, total=1):
    """O mesmo nome do arquivo, com _montagem no fim, na pasta do dia."""
    pasta = os.path.dirname(origem)
    base = os.path.splitext(os.path.basename(origem))[0]
    pag = sufixo_pagina(indice, total)
    return os.path.join(pasta, "%s_montagem%s.pdf"
                        % (base, " " + pag if pag else ""))


def _pagina_girada(origem, pagina, destino, graus):
    """
    Uma copia de UMA pagina, girada, para separar a partir dela.

    Gira pela FICHA da pagina (/Rotate), nao pelo desenho: o Ghostscript
    ja entrega a separacao deitada, e nenhum pixel e recalculado. Girar a
    imagem depois de separada custaria mais de um giga de memoria por
    chapa, e nao ha razao para pagar isso.
    """
    from pypdf import PdfReader, PdfWriter

    leitor = PdfReader(origem)
    pag = leitor.pages[pagina - 1]
    pag.rotate(graus)
    escritor = PdfWriter()
    escritor.add_page(pag)
    with open(destino, "wb") as f:
        escritor.write(f)
    return destino


def _arte_reprovada(pdf, pagina, nome, aprovado, problemas, cliente=SOLIDA):
    """
    Confere a arte por dentro. True quando a pagina nao deve virar chapa.

    O que e so aviso vai para o log e o servico segue - imagem de 280 dpi
    e arte comum, e parar por isso emperraria a grafica. O que e grave
    para: fonte que falta muda a forma do texto, e imagem esticada demais
    sai borrada na tiragem, com a chapa ja queimada.

    MENOS a resolucao, e menos em quem esta em
    CLIENTES_SEM_TRAVA_DE_RESOLUCAO. Ali o numero de dpi sai no log como
    alerta e a chapa segue - o operador daquele cliente ja liberava na
    mao toda vez, e trava que se libera sempre nao protege ninguem: so
    atrasa o serviço e ensina a ignorar aviso.

    Note que e SO a resolucao. Fonte nao incorporada continua parando
    todo mundo.
    """
    try:
        achados = conferir_arte(pdf, pagina)
    except Exception as e:
        log("   p%d: nao consegui conferir a arte (%s)" % (pagina, str(e)[:60]),
            alerta=True)
        return False

    reprovou = False
    for gravidade, texto in achados:
        liberado = (e_de_resolucao(texto)
                    and cliente in CLIENTES_SEM_TRAVA_DE_RESOLUCAO)
        if gravidade == PARA and not aprovado and not liberado:
            motivo = "pagina %d: %s" % (pagina, texto)
            log("   " + motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            reprovou = True
        else:
            if gravidade == PARA and liberado:
                texto += " - segui assim mesmo: a %s nao para por resolucao" \
                         % cliente
            log("   p%d: %s" % (pagina, texto), alerta=(gravidade == PARA))
    return reprovou


def _gerar_chapa(origem, pasta_saida, base, pagina, dpi, larg, alt, usadas,
                 cinza=False, alvo=None, deslocamento=None, girar=0,
                 preto_puro=False, do_corel=False):
    """
    Separa uma pagina e monta o PDF final. Devolve o caminho gerado.

    Com cinza=True sai UMA chapa em escala de cinza, no lugar das quatro
    da quadricromia: e o caso da arte de uma cor so.

    Com 'alvo' (largura, altura em pixels), a arte entra centralizada no
    tamanho da chapa - sobra cortada, falta em branco.

    Os TIFFs da separacao ficam SEMPRE no disco local: sao varios GB e
    passar isso pela rede tornaria tudo lento.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_p%d_" % pagina, dir=PASTA_CONTROLE)
    try:
        if girar:
            origem = _pagina_girada(origem, pagina,
                                    os.path.join(tmp, "girada.pdf"), girar)
            pagina = 1

        if cinza:
            # preto PURO sai sem o perfil, que e o que mantem a
            # porcentagem; preto COMPOSTO passa pelo perfil, senao as
            # quatro tintas somam. Ver separar_cinza.
            tif = separar_cinza(origem, dpi, tmp, pagina,
                                sem_perfil=preto_puro)
            saida = nome_livre(pasta_saida, base)
            letras = montar_pdf_cinza(tif, saida, larg, alt, alvo=alvo,
                                      deslocamento=deslocamento)
            conferir(saida, larg, alt, dpi)
            # O ANTES E O DEPOIS. Esta e a unica conferencia que olha a
            # TINTA; as outras olham medida e resolucao. Ela apaga a
            # chapa se a porcentagem mudou - ver conferir_uma_cor.
            antes, depois = conferir_uma_cor(origem, pagina, saida,
                                             preto_puro)
            log("   tinta antes %.2f%% (max %.2f%%, chapado %.0f mm2) -> "
                "depois %.2f%% (max %.2f%%, chapado %.0f mm2)"
                % (antes[0], antes[1], antes[2],
                   depois[0], depois[1], depois[2]))
            return saida, letras

        # do_corel: a separacao le a cor como esta ESCRITA no arquivo.
        # A Corel embute perfil, e passar por ele come o chapado - ver
        # separar_tintas. So a quadricromia precisa disto; o cinza ja
        # resolve o seu caso pelo preto_puro.
        separar_tintas(origem, dpi, tmp, pagina, sem_perfil_=do_corel)

        tifs = {}
        for tif in sorted(glob.glob(os.path.join(tmp, "s(*).tif"))):
            tinta = re.search(r"\(([^)]+)\)", os.path.basename(tif)).group(1)
            if tinta in NOMES_TINTA:
                letra = NOMES_TINTA[tinta]
                if letra not in usadas:
                    continue                      # separacao vazia, descarta
            else:
                letra = re.sub(r"[^A-Za-z0-9]+", "", tinta)[:16]
                log("   cor especial: %s" % tinta, alerta=True)
            tifs[letra] = tif

        if not tifs:
            raise RuntimeError("nenhuma tinta encontrada na pagina %d" % pagina)

        saida = nome_livre(pasta_saida, base)
        letras = montar_pdf(tifs, saida, larg, alt, alvo=alvo,
                            deslocamento=deslocamento)
        conferir(saida, larg, alt, dpi)
        return saida, letras
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Quanto a tinta pode variar entre o arquivo e a chapa, em PONTO
# PERCENTUAL. Regra do operador, 14/09/2026: "todos os arquivos que vc
# for converter, 1 cor, conferir o antes e o depois para ver se as
# porcentagens estao as mesmas".
#
# 1,0 e um primeiro numero, e esta marcado como tal. O que se mediu:
# convertendo o '49835 - Flor Bela - sacola' certo, a media saiu 38,66
# contra 38,68 e o maximo 100,00 contra 100,00 - 0,02 de diferenca. Com
# o perfil no caminho, que e o defeito, a media caia para 33,83 e o
# maximo para 87,45 - 5 e 12 pontos. A folga separa os dois casos com
# sobra de dez vezes.
TOLERANCIA_TINTA_PP = 1.0

# A conferencia rasteriza as duas vezes, entao nao roda nos 1000 dpi da
# chapa. Mas tambem nao pode rodar baixo demais, e isto foi MEDIDO, nao
# escolhido: a ARTE e vetor, e em resolucao baixa cada traco fino ocupa
# um pixel INTEIRO e chapado. A chapa ja e bitmap e nao infla. Area de
# chapado do 'Bloco' da VOPRIX, o mesmo desenho dos dois lados:
#
#     dpi     arte      chapa certa   razao     chapa errada
#      60   19.031 mm2   8.640 mm2     2,20       184 mm2
#     150   13.496       9.070         1,49       210
#     300   10.839       9.012         1,20       206
#     600    9.586       9.081         1,06       204
#
# A 300 dpi um pixel tem 0,085 mm - da ordem do traco fino - e a arte ja
# esta quase resolvida: 20% acima da chapa, contra 120% a 60 dpi. E
# custa 0,7 s numa chapa 510x400. Abaixo disso a inflacao da arte
# comeria a folga e a conferencia reprovaria chapa boa.
#
# Reduzir a arte por MEDIA DE AREA para casar com a chapa foi tentado e
# NAO serve: da 2.193 mm2 - menos que a propria chapa -, porque o
# Ghostscript nao reamostra por media o bitmap que esta dentro do PDF da
# chapa. Os dois lados tem de ser rasterizados direto, na mesma
# resolucao.
DPI_DA_CONFERENCIA = 300


# Quanto do CHAPADO do arquivo tem de reaparecer na chapa, em area.
#
# Existe para tapar o furo que deixou a chapa do 'Bloco' da VOPRIX sair
# clara: o arquivo do Corel traz as MARCAS DE REGISTRO desenhadas na cor
# registro - 100% das quatro tintas -, e elas atravessam o perfil ICC
# intactas. Entao o maximo da chapa dava 100% mesmo com a arte inteira
# rebaixada, e a conferencia passava. Medido:
#
#     arquivo   100% em 13.500 mm2   (135 cm2 - a arte)
#     chapa     100% em    210 mm2   (2,1 cm2 - so as marcas)
#               87,45% em 8.859 mm2  (a arte, rebaixada)
#
# Um pixel de chapado nao prova nada. A AREA prova.
#
# Um quarto, e nao metade, porque a arte ainda entra 20% inflada a 300
# dpi (ver DPI_DA_CONFERENCIA) e ha desenho mais fino que este. O que
# se mediu, com a mesma arte dos dois lados:
#
#     chapa certa    9.012 / 10.839 = 0,83   - tres vezes acima do corte
#     chapa errada     206 / 10.839 = 0,02   - treze vezes abaixo
#
# A folga tambem cobre a serrilha da borda e o caso raro de arte maior
# que a chapa, onde a sobra e cortada.
CHAPADO_QUE_TEM_DE_SOBRAR = 0.25

# Abaixo de 1 cm2 o 'chapado' pode ser respingo, marca ou um ponto de
# registro, e comparar area vira ruido. Ali so o maximo conta.
CHAPADO_QUE_VALE_CONFERIR_MM2 = 100.0


def _tinta_da_pagina(pdf, pagina, sem_perfil, dpi=DPI_DA_CONFERENCIA,
                     piso=None):
    """
    (media, maxima, area_do_chapado_em_mm2) da pagina, em porcentagem.

    Le em escala de cinza, onde 0 e chapado e 255 e papel - entao a
    tinta e (255 - valor) / 255.

    A area e a do que esta na faixa mais escura: tudo com tinta igual ou
    acima de 'piso'. Sem piso, usa o proprio maximo menos a folga - que
    e como se mede o ARQUIVO. Para a CHAPA passa-se o piso do arquivo,
    senao cada lado responderia sobre um tom diferente e os dois numeros
    nao se comparariam.
    """
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="ctp_conf_", dir=PASTA_CONTROLE)
    try:
        alvo = separar_cinza(pdf, dpi, tmp, pagina, sem_perfil=sem_perfil)
        h = Image.open(alvo).convert("L").histogram()
        total = sum(h) or 1
        media = sum((255 - i) / 255.0 * 100 * q for i, q in enumerate(h)) / total
        usados = [i for i, q in enumerate(h) if q]
        maxima = (255 - min(usados)) / 255.0 * 100 if usados else 0.0
        corte = maxima - TOLERANCIA_TINTA_PP if piso is None else piso
        mm2 = (25.4 / float(dpi)) ** 2
        area = sum(q for i, q in enumerate(h)
                   if (255 - i) / 255.0 * 100 >= corte) * mm2
        return media, maxima, area
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def conferir_uma_cor(origem, pagina, saida, preto_puro):
    """
    Compara a tinta ANTES e DEPOIS, e APAGA a chapa se o CHAPADO caiu.

    Regra do operador, 14/09/2026. Ela nasceu de um defeito que passou
    despercebido justamente por nao dar erro: a chapa de uma cor saia
    pelo perfil ICC e o chapado de 100% virava 87,5%. Ninguem ve isso na
    tela nem na prova reduzida - so na tiragem, com a chapa queimada.

    QUEM MANDA E O MAXIMO, E A MEDIA SO INFORMA. Isto custou meio dia
    para ser entendido, e o motivo e geometrico:

      a ARTE e vetor. Rasterizada, todo traco fino vira pelo menos UM
      pixel inteiro - entao, em baixa resolucao, a media de tinta sai
      inflada. Medida do 'Bloco' da VOPRIX, o mesmo arquivo:

          60 dpi   9,61%      600 dpi   4,96%
         150 dpi   6,88%     1000 dpi   5,10%
         300 dpi   5,58%

      a CHAPA ja e bitmap, gravada em 1000 dpi. Lida em qualquer
      resolucao ela da o mesmo numero, porque reduzir bitmap e tirar
      media - e media de media nao muda.

    Comparar as duas medias em resolucao baixa e comparar geometrias
    diferentes, e a conta acusa perda onde nao ha. Foi o que aconteceu:
    a conferencia deu 'o arquivo tem 9,61% e a chapa 3,94%' e REPROVOU
    uma chapa que, medida a 1000 dpi nos dois lados, dava 5,103% contra
    5,103% - identica ate a terceira casa.

    O MAXIMO nao tem esse vicio. Um chapado de 100% e 100% em qualquer
    resolucao: nenhuma media de pixel vizinho o dilui, porque ele nao e
    tracinho, e area. E era exatamente no maximo que o defeito aparecia -
    100% virando 87,5%.

    A media continua sendo medida e registrada no log, para quem for
    investigar ter o numero na mao. Ela so nao BARRA nada.

    E O MAXIMO SOZINHO TAMBEM NAO BASTA - isto custou uma chapa. O
    arquivo que a Corel publica traz as marcas de registro na cor
    REGISTRO, 100% das quatro tintas, e elas atravessam o perfil ICC sem
    perder nada. Entao a chapa do 'Bloco' da VOPRIX tinha maximo 100% -
    as marcas - com a arte inteira rebaixada de 100% para 87,45%, e
    passou. Por isso a segunda pergunta, que e de AREA: o chapado do
    arquivo reapareceu na chapa, ou virou um carimbo de dois
    centimetros? Ver CHAPADO_QUE_TEM_DE_SOBRAR.
    """
    antes = _tinta_da_pagina(origem, pagina, sem_perfil=preto_puro)
    # a chapa responde sobre o MESMO tom que o arquivo, senao os dois
    # numeros de area falariam de faixas diferentes.
    piso = antes[1] - TOLERANCIA_TINTA_PP
    depois = _tinta_da_pagina(saida, 1, sem_perfil=True, piso=piso)

    def apagar(motivo):
        try:
            os.remove(saida)
        except OSError:
            pass
        raise RuntimeError(
            "a chapa de uma cor PERDEU densidade: %s. (as medias, so para "
            "o registro: %.2f%% e %.2f%%.) Apaguei em vez de mandar clara"
            % (motivo, antes[0], depois[0]))

    # SO A QUEDA reprova. No preto composto a tinta pode ate subir -
    # juntar quatro canais num so aumenta a densidade de propósito -, e
    # no preto puro subir nao acontece. Cair e que nao tem explicacao em
    # nenhum dos dois.
    if antes[1] - depois[1] > TOLERANCIA_TINTA_PP:
        apagar("o ponto mais escuro do arquivo tem %.2f%% de tinta e o da "
               "chapa tem %.2f%% - acima dos %.1f ponto(s) de folga"
               % (antes[1], depois[1], TOLERANCIA_TINTA_PP))

    if (antes[2] >= CHAPADO_QUE_VALE_CONFERIR_MM2
            and depois[2] < antes[2] * CHAPADO_QUE_TEM_DE_SOBRAR):
        apagar("o chapado ENCOLHEU: o arquivo tem %.0f mm2 acima de "
               "%.2f%% de tinta e a chapa tem %.0f mm2 - menos de %.0f%% "
               "do que entrou. O tom caiu e so as marcas ficaram no topo"
               % (antes[2], piso, depois[2],
                  CHAPADO_QUE_TEM_DE_SOBRAR * 100))
    return antes, depois


def cabe_no_curto(plano):
    """
    True quando esta pagina pode ir INTEIRA para a gravadora.

    A pergunta e uma so: a gravadora, lendo o arquivo, chega no mesmo
    numero de chapas que a gente contou?

    Chega, menos num caso: arte de UMA COR desenhada com as QUATRO
    TINTAS. Ali a chapa e uma - e o que o operador sempre fez a mao, e o
    que o caminho longo faz juntando tudo num cinza -, mas o arquivo tem
    C, M, Y e K escritos dentro dele e a gravadora nao tem como adivinhar
    o contrario: sairiam quatro chapas onde a OS cobrou uma.

    Arte de uma cor desenhada com UMA tinta passa: a gravadora encontra
    aquela tinta e grava a mesma chapa que a gente contou.
    """
    return not plano["cinza"] or len(plano["tintas_do_arquivo"]) <= 1


def _entregar_chapa(origem, pasta_saida, base, plano, total):
    """
    Poe a pagina no CTP como ela veio, sem separar tinta nenhuma.

    O caminho curto (ver entrega.py). Quem separa passa a ser a
    gravadora, e por isso as tres perguntas abaixo: nelas o arquivo
    entregue NAO seria o que a chapa precisa, e chutar sai caro.
    """
    if plano["girar"] or plano["alvo"] or plano["deslocamento"]:
        raise RuntimeError(
            "esta pagina precisa ser girada ou montada na chapa, e o "
            "caminho curto entrega o arquivo como ele veio. Nao entreguei")
    if not cabe_no_curto(plano):
        raise RuntimeError(
            "arte de uma cor desenhada com %d tintas: a gravadora nao tem "
            "como saber que e uma chapa so, e gravaria %d. Nao entreguei"
            % (len(plano["tintas_do_arquivo"]),
               len(plano["tintas_do_arquivo"])))

    saida = nome_livre(pasta_saida, base)
    entregar(origem, saida, plano["pagina"], total)
    erro = conferir_entrega(saida, plano["larg_chapa"], plano["alt_chapa"])
    if erro:
        try:
            os.remove(saida)
        except OSError:
            pass
        raise RuntimeError("%s - apaguei em vez de mandar errado" % erro)
    return saida, sorted(plano["usadas"])


def conferir(saida, larg, alt, dpi):
    """
    Mede a chapa recem-gravada e a APAGA se estiver fora.

    Chapa na resolucao errada nao da erro em lugar nenhum: abre, imprime
    na prova reduzida igual as outras, e so mostra o defeito na tiragem,
    com a chapa queimada e o papel rodando. Uma chapa que nao existe da
    trabalho; uma chapa errada na pasta da prejuizo.
    """
    erro = conferir_resolucao(saida, larg, alt, dpi)
    if not erro:
        return
    try:
        os.remove(saida)
    except OSError:
        pass
    raise RuntimeError("%s - apaguei a chapa em vez de mandar errada" % erro)


def processar(caminho, pasta_saida, cliente=SOLIDA, aprovado=False,
              regravacao=False):
    """
    Fluxo completo de um arquivo.

    Devolve {"status": "ok"|"erro"|"espera"|"adiado", "saidas": [...],
    "motivo": "..."}. Nunca levanta excecao para cima.

    "adiado" e so da VOPRIX: o .cdr esta aberto no CorelDRAW do operador
    e nao encostamos nele. Nao entra no registro - fica para a proxima
    passada, quando a pessoa tiver fechado o arquivo.

    Quando a VOPRIX da errado depois de converter, o PDF nao e jogado
    fora: vai para a PASTA_PENDENCIAS, para o trabalho da Corel nao se
    perder e voce continuar dali.

    aprovado=True e a pessoa dizendo "pode fechar": pula o aviso do
    AVISAR_QUANDO_NAO_FOR_CMYK e gera a chapa mesmo fora da quadricromia.
    """
    nome = os.path.basename(caminho)
    # 'chapas' guarda o que cada pagina REALMENTE gerou: o tamanho da
    # chapa e quantas tintas. E daqui que sai a conta da OS - o GEREMPRE
    # cobra por chapa de metal, e quadricromia gasta quatro. Vem do que
    # saiu, e nao do que se esperava que saisse.
    resultado = {"status": "ok", "saidas": [], "chapas": [], "motivo": "",
                 "impresso": None}

    def falhar(motivo):
        log("%s: %s" % (nome, motivo), alerta=True)
        anotar_pendencia(nome, motivo, cliente)
        resultado["status"] = "erro"
        resultado["motivo"] = motivo
        return resultado

    motivo = acima_do_limite(caminho)
    if motivo:
        return falhar(motivo)

    # PASSO 0, so da VOPRIX: o .cdr vira PDF pelo CorelDRAW da maquina.
    temporaria = None
    trabalho = caminho
    if (cliente in CLIENTES_QUE_VEM_DO_COREL
            and nome.lower().endswith(".cdr")):
        try:
            log("'%s': convertendo no CorelDRAW..." % nome)
            trabalho, temporaria = converter_cdr(caminho)
        except ArquivoEmUso as e:
            resultado["status"] = "adiado"
            resultado["motivo"] = str(e)
            return resultado
        except Exception as e:
            return falhar("CorelDRAW nao converteu: %s" % e)
    elif cliente in (FIALHO, VIVA):
        # So anda o que ja vem em PDF, no tamanho da chapa. Corel e arte
        # por montar param aqui e esperam gente.
        if not nome.lower().endswith(".pdf"):
            ext = os.path.splitext(nome)[1] or "sem extensao"
            return falhar("veio em %s, nao em PDF - montagem ainda e na "
                          "mao. Nao dei andamento no servico" % ext)
    elif cliente == CREATIVE:
        # A Creative nao usa OS no nome do arquivo - manda o nome do
        # servico, como a VIVA ('santinho cruvinel.pdf'). Exigir OS aqui
        # pararia todo arquivo dela.
        if not nome.lower().endswith(".pdf"):
            ext = os.path.splitext(nome)[1] or "sem extensao"
            return falhar("veio em %s, nao em PDF" % ext)
    elif not extrair_oss(nome):
        return falhar("nao achei numero de OS no nome")

    try:
        # O PDF que a Corel devolve pode ser muito maior que o .cdr: um
        # arquivo de 375 MB ja virou um PDF de 2,2 GB.
        motivo = acima_do_limite(trabalho)
        if motivo:
            return falhar("depois de converter, " + motivo)

        return _processar_pdf(trabalho, nome, pasta_saida, cliente,
                              resultado, falhar, aprovado,
                              origem=caminho, regravacao=regravacao)
    finally:
        # O que a Corel converteu nao se joga fora so porque nao deu para
        # seguir: fica guardado para a mao, e a conversao nao se repete.
        if temporaria:
            if resultado["status"] == "erro" and os.path.isfile(trabalho):
                guardado = guardar_para_a_mao(trabalho, nome)
                if guardado:
                    resultado["pendencia"] = guardado
                    log("   o PDF convertido ficou em %s - abra ele no "
                        "Photoshop/InDesign, nao precisa converter de novo"
                        % guardado, alerta=True)
            shutil.rmtree(temporaria, ignore_errors=True)


def _os_do_arquivo(nome, cliente, planos, regravacao=False):
    """
    (numero, fechou_a_quarta) da OS deste arquivo: acha, completa ou abre.

    'fechou_a_quarta' diz que ESTE arquivo encheu a ultima vaga - e o
    sinal de que a OS pode ser entregue, depois que a prova sair. So vale
    quando fomos NOS que completamos: numa OS de outra pessoa, dar por
    entregue nao e nosso lugar.

    Devolve (None, False) - e o arquivo segue sem OS, so com a prova -
    quando:

      - o arquivo nao vira servico cobravel (paginas em chapas de
        tamanhos diferentes, por exemplo). A regra mora na fila, que ja
        anota a pendencia;
      - dois arquivos do dia trazem a MESMA OS no nome. Sao dois
        servicos cobrados separados ou um trabalho partido em dois? A
        diferenca e o dobro do valor, e quem decide e gente;
      - o GEREMPRE esta fora do ar. A chapa nao para por causa disso: a
        prova sai sem verso e o lancamento fica para a mao.

    ESCREVER AQUI MEXE EM ESTOQUE - a OS da baixa das chapas na hora.
    """
    from . import fila
    from .gerempre import (COMPLETEI, JA_ESTAVA, VAGAS, SemLigacao,
                       os_do_servico)

    servico = fila.servico_do_arquivo(nome, cliente, {
        "status": "ok",
        "chapas": [{"chapa": [p["larg_chapa"], p["alt_chapa"]],
                    "tintas": len(p["usadas"])} for p in planos]},
        regravacao=regravacao)
    if not servico:
        return None, False

    # a memoria do dia: e ela que enxerga dois arquivos com a mesma OS
    atual = fila.carregar()
    ja_estava = any(s["cliente"] == servico["cliente"]
                    and s["titulo"] == servico["titulo"] for s in atual)
    depois = fila.entrar(servico, atual)
    if not ja_estava and len(depois) == len(atual):
        # A FILA RECUSOU e ja anotou o porque. Devolve o PAR, como todos
        # os outros caminhos: quem chama faz
        # 'numero_os, fechou = _os_do_arquivo(...)', e um None solto
        # estoura com 'cannot unpack non-iterable NoneType object'.
        #
        # Ficou latente ate 14/09/2026, porque so se chega aqui quando a
        # fila recusa - e ela so recusa no caso de dois arquivos com a
        # mesma OS. Quando aconteceu, o estrago nao foi o erro: foi o
        # LACO. A excecao subia antes de o arquivo entrar no registro,
        # entao o vigia o via de novo a cada volta, gravava outra
        # pendencia e estourava outra vez - de 90 em 90 segundos, para
        # sempre.
        return None, False
    fila.salvar(depois)

    try:
        numero, vaga, o_que_fiz = os_do_servico(servico)
    except SemLigacao as e:
        log("   GEREMPRE fora do ar (%s). A chapa sai; a OS fica para a "
            "mao." % e, alerta=True)
        anotar_pendencia(nome, "nao consegui falar com o GEREMPRE para "
                               "abrir a OS: %s. Lance a mao" % str(e)[:70])
        return None, False
    except Exception as e:
        log("   GEREMPRE: nao abri a OS (%s)" % str(e)[:90], alerta=True)
        anotar_pendencia(nome, "nao consegui abrir a OS: %s. Lance a mao"
                         % str(e)[:80])
        return None, False

    # A quarta vaga acabou de fechar? So conta COMPLETEI: em JA_ESTAVA a
    # OS e de outra pessoa. Quem entrega e o passo da prova, DEPOIS que
    # ela sai - a ordem foi pedida assim pelo operador.
    fechou = (o_que_fiz == COMPLETEI and vaga == VAGAS)

    if o_que_fiz == JA_ESTAVA:
        log("   GEREMPRE: '%s' JA ESTAVA na OS %s (vaga %d) - alguem lancou "
            "antes. Nao cobrei de novo; a prova sai com esse numero."
            % (servico["titulo"][:40], numero, vaga), alerta=True)
    elif o_que_fiz == COMPLETEI:
        log("   GEREMPRE: completei a OS %s na vaga %d, %d chapa(s)"
            % (numero, vaga, servico["chapas"]), alerta=True)
    else:
        log("   GEREMPRE: abri a OS %s, %d chapa(s)"
            % (numero, servico["chapas"]), alerta=True)
    return numero, fechou


def _entregar_e_protocolar(numero, nome):
    """
    Fecha a OS e tira o protocolo. So depois de a prova ter saido.

    NUNCA SEGURA A CHAPA. A chapa ja esta gravada e a prova ja saiu
    quando isto roda; falhar aqui e um lancamento que ficou para a mao,
    e nao um servico perdido. Por isso tudo vira aviso e pendencia, e
    nada e levantado para cima.

    O entregar_os confere as quatro vagas por conta propria - aqui nao
    se decide nada sobre isso.
    """
    from .gerempre import SemLigacao, entregar_os

    try:
        entregar_os(numero)
    except SemLigacao as e:
        log("   GEREMPRE fora do ar (%s). A OS %s fica PENDENTE."
            % (e, numero), alerta=True)
        anotar_pendencia(nome, "as quatro vagas da OS %s fecharam, mas o "
                               "GEREMPRE estava fora do ar. Ela ficou "
                               "PENDENTE - feche a mao" % numero)
        return
    except Exception as e:
        log("   nao consegui entregar a OS %s (%s)" % (numero, str(e)[:80]),
            alerta=True)
        anotar_pendencia(nome, "as quatro vagas da OS %s fecharam, mas nao "
                               "consegui marcar ENTREGUE: %s. Feche a mao"
                         % (numero, str(e)[:60]))
        return

    # O protocolo e papel de cliente, e nao segura nada se falhar.
    try:
        from .protocolo import imprimir_protocolo
        imprimir_protocolo(numero)
    except ImportError:
        log("   OS %s entregue. O protocolo ainda nao e impresso pela FIA "
            "- tire pelo F12." % numero, alerta=True)
    except Exception as e:
        log("   OS %s entregue, mas nao saiu o protocolo (%s)"
            % (numero, str(e)[:70]), alerta=True)
        anotar_pendencia(nome, "a OS %s foi entregue, mas o protocolo nao "
                               "imprimiu: %s. Tire pelo F12"
                         % (numero, str(e)[:60]))


def _verso_da_os(numero):
    """
    A folha da OS para sair no verso da prova, ou None.

    Falhar aqui nao pode segurar a chapa: sem o verso a prova sai so na
    frente, que e como saiu ate hoje.
    """
    if not numero:
        return None
    try:
        folha = folha_da_os(numero)
        # O numero viaja COLADO na folha porque a trava de copia unica
        # (prova.imprimir) o usa na chave: a mesma arte pode sair de novo
        # para OUTRA OS, e ali a prova e legitima. Sem isto, a trava
        # seguraria servico de verdade.
        folha._os_numero = numero
        return folha
    except Exception as e:
        log("   nao consegui desenhar a folha da OS %s (%s). A prova sai "
            "so na frente." % (numero, str(e)[:70]), alerta=True)
        return None


def _processar_pdf(pdf, nome, pasta_saida, cliente, resultado, falhar,
                   aprovado=False, origem=None, regravacao=False):
    """
    O caminho comum aos dois clientes, pagina a pagina.

    'pdf' e o arquivo que vai ser lido e impresso - na VOPRIX, o que a
    Corel acabou de gerar. 'nome' e sempre o do arquivo original, que e
    quem manda no nome de saida. 'origem' e o CAMINHO do original: e por
    ele que a trava de copia unica reconhece a prova, porque o temporario
    da Corel nasce diferente a cada passada.
    """
    origem = origem or pdf
    # Quem vai pelo caminho curto entrega o arquivo e a gravadora separa.
    # Ai a tinta tem de ser contada como esta ESCRITA no arquivo, sem
    # passar pelo perfil embutido: e a conta da gravadora que vale, e e
    # ela que decide o nome da chapa e quantas chapas a OS cobra.
    # Ver ghostscript.sem_perfil, com os numeros.
    sem_icc = cliente in CLIENTES_QUE_VEM_DO_COREL

    try:
        medidas = medir_paginas(pdf)
        cobertura = cobertura_por_pagina(pdf, sem_icc=sem_icc)
    except Exception as e:
        return falhar("PDF ilegivel: %s" % e)

    # A COBERTURA CRUA - sem o perfil ICC -, lida SO SE PRECISAR.
    #
    # Quem nao esta em ENTREGAR_PDF_DIRETO tem a cobertura lida COM o
    # perfil, e o perfil espalha o preto de K sozinho pelos quatro
    # canais. Para saber em que canal a tinta esta de verdade - que e o
    # que decide como gerar a chapa de uma cor - nao ha como escapar de
    # uma segunda passada do inkcov.
    #
    # Ela custa uma chamada do Ghostscript, entao so acontece quando a
    # arte JA foi reconhecida como de uma cor: e raro, e ai vale.
    cru = {}

    def cobertura_crua(pagina):
        if not cru:
            try:
                cru["p"] = cobertura_por_pagina(pdf, sem_icc=True)
            except Exception:
                cru["p"] = []
        lista = cru["p"]
        return lista[pagina - 1] if pagina - 1 < len(lista) else None

    total = len(medidas)
    if not total:
        return falhar("PDF sem paginas")

    log("'%s': %d pagina(s)" % (nome, total))
    os.makedirs(pasta_saida, exist_ok=True)
    problemas = []

    # PASSO 1: CONFERIR cada pagina, sem gerar nada e sem imprimir.
    #
    # A ordem mudou por pedido do operador: a folha que vai para a
    # maquina leva a arte na frente e a ORDEM DE SERVICO no verso, entao
    # o numero da OS tem de existir antes da prova sair. E o numero so
    # pode ser tirado depois de saber quantas chapas o trabalho gasta,
    # que e o que esta conferencia mede.
    #
    # Conferir e rapido; gerar chapa leva minutos. Por isso as duas
    # coisas foram separadas: a prova continua saindo cedo, como sempre
    # saiu, e a gravacao vem depois dela.
    planos = []
    for i, (larg, alt) in enumerate(medidas):
        # De qual arquivo, e de qual pagina dele, a chapa vai ser
        # gravada. E o proprio arquivo - a menos que haja MONTAGEM, e ai
        # passa a ser ela (ver salvar_montagem).
        fonte_da_chapa, pagina_da_chapa = pdf, i + 1

        # Arte EM PE e girada para deitar - 'deixar da forma que sempre
        # vem'. Girando, largura e altura trocam de lugar, e o pe da
        # chapa passa a ser outra borda do arquivo.
        girar = giro_da_pagina(larg, alt, cliente)
        if girar:
            larg, alt = alt, larg
            log("   p%d: a arte veio EM PE (%.0fx%.0f mm). Girei %d graus "
                "para deitar - %.0fx%.0f mm, o tamanho de sempre"
                % (i + 1, alt, larg, girar, larg, alt), alerta=True)

        # Onde esta a marca de corte desta pagina. So a Creative usa:
        # e dela que a pinca se mede, e nao da borda do arquivo.
        corte = 0.0
        if pinca_do_cliente(cliente) and not casar_formato(larg, alt,
                                                           cliente):
            lado = LADO_DA_PINCA[girar % 360]
            corte_pe = marcas_de_corte(pdf, i + 1).get(lado)
            if corte_pe is None:
                # SEM MARCA, PINCA DA BASE DA CHAPA.
                #
                # Ate 16/09/2026 isto parava o servico e virava pendencia,
                # com o argumento de que chutar a pinca manda servico
                # errado. O operador desfez a recusa naquele dia, no
                # 'PREF. INHUMAS - PASTAS' da PRIME: "o que voce deu
                # pendencia, que nao achou a marca de corte, quando e
                # assim, pince a partir da base da chapa".
                #
                # E nao e chute: sem marca, a borda de baixo do arquivo E
                # a referencia que existe - corte = 0 faz a pinca ser
                # medida dali. O que se perde e a correcao de quando a
                # marca esta acima da borda; com marca nenhuma nao ha o
                # que corrigir.
                #
                # Fica ALTO no log, e nao calado: e uma decisao tomada
                # por regra, e quem olhar o dia precisa saber que aquela
                # chapa saiu sem marca para conferir.
                aviso = ("pagina %d: nao achei a marca de corte (lado %s). "
                         "Pincei a partir da BASE da chapa, como o operador "
                         "mandou em 16/09/2026" % (i + 1, lado))
                pista = pistas_da_marca(pdf, i + 1, lado)
                if pista:
                    aviso += ". O que eu vi: " + pista
                log("   " + aviso, alerta=True)
                corte_pe = 0.0
            corte = corte_pe

        chapa, dpi, sufixo, encaixou = chapa_da_pagina(larg, alt, cliente,
                                                       corte)

        if not dpi:
            motivo = ("pagina %d: %.0f x %.0f mm nao e chapa (%s)"
                      % (i + 1, larg, alt, chapas_aceitas(cliente)))
            if cliente == FIALHO:
                motivo += " - nao dei andamento no servico"
            log("   " + motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        larg_chapa, alt_chapa = chapa
        alvo = pixels_da_chapa(larg_chapa, alt_chapa, dpi) if encaixou else None
        deslocamento = None
        if encaixou and pinca_do_cliente(cliente):
            esquerda, topo = posicao_na_chapa(larg, alt, chapa, cliente,
                                              corte)
            deslocamento = (int(round(esquerda / 25.4 * dpi)),
                            int(round(topo / 25.4 * dpi)))
            log("   p%d: arte %.0fx%.0f mm montada na chapa %.0fx%.0f"
                % (i + 1, larg, alt, larg_chapa, alt_chapa), alerta=True)
            log("       marca de corte a %.1f mm da borda da arte; a arte "
                "encosta a %.1f mm do pe da chapa,"
                % (corte, pinca_do_cliente(cliente) - corte), alerta=True)
            log("       deixando a PINCA de %d mm da marca ate a borda. "
                "%.1f mm de cada lado."
                % (pinca_do_cliente(cliente), esquerda), alerta=True)

            # A MONTAGEM FICA NA PASTA DO DIA - ver salvar_montagem.
            # Daqui para a frente e ELA que anda: a chapa do CTP sai da
            # montagem, e nao do arquivo solto. Assim o que foi gravado
            # e exatamente o que ficou na pasta para ser conferido.
            if cliente in CLIENTES_QUE_SALVAM_A_MONTAGEM:
                destino = caminho_da_montagem(origem, i, total)
                try:
                    salvar_montagem(pdf, i + 1, destino, chapa, esquerda,
                                    pinca_do_cliente(cliente) - corte,
                                    girar)
                except Exception as e:
                    motivo = ("pagina %d: nao consegui salvar a montagem "
                              "em %s: %s" % (i + 1, destino, e))
                    log("   " + motivo, alerta=True)
                    anotar_pendencia(nome, motivo)
                    problemas.append(motivo)
                    continue
                log("   p%d: montagem salva em %s"
                    % (i + 1, os.path.basename(destino)), alerta=True)
                # a chapa sai DELA, que ja esta no tamanho da chapa:
                # nada mais a encaixar, a deslocar nem a girar
                fonte_da_chapa, pagina_da_chapa = destino, 1
                alvo = deslocamento = None
                girar = 0
        elif encaixou:
            log("   p%d: arte %.0fx%.0f mm entra centralizada na chapa "
                "%.0fx%.0f - sobra cortada dos dois lados"
                % (i + 1, larg, alt, larg_chapa, alt_chapa), alerta=True)

        cob = cobertura[i] if i < len(cobertura) else None
        usadas = tintas_da_cobertura(cob) if cob else set("CMYK")

        # Tinta que e so traco nao vira chapa - ver sem_tinta_de_traco.
        # O log diz o que caiu e com que numero: e chapa a menos no CTP
        # e na OS, e ninguem deve descobrir isso pela tiragem.
        if cob and cliente in CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO:
            fica, candidatas = sem_tinta_de_traco(cob, usadas)
            # A PROPORCAO SO LEVANTA O CANDIDATO. Quem decide e a
            # pergunta que ela nao faz: a tinta aparece SOZINHA em algum
            # pixel? Ver ghostscript.tinta_aparece_sozinha - e o conserto
            # de 16/09/2026, quando um ciano de 5,23% era traco e um K de
            # 6,45% era texto, e nenhum numero separava os dois.
            de_traco = set()
            for t in sorted(candidatas):
                sozinha, quantos = tinta_aparece_sozinha(
                    pdf, i + 1, t, sem_perfil_=sem_icc)
                if sozinha is False:
                    de_traco.add(t)
                    log("   p%d: %s tem %.4f de cobertura (%.1f%% da mais "
                        "forte) e NUNCA aparece sozinha em %d pixels - e "
                        "traco, nao chapa. Nao gravei nem cobrei essa cor"
                        % (i + 1, t, cob[t],
                           100.0 * cob[t] / max(cob[x] for x in "CMYK"),
                           quantos), alerta=True)
                elif sozinha is True:
                    log("   p%d: %s tem so %.4f de cobertura, mas aparece "
                        "SOZINHA em pixel - desenha alguma coisa. Fica."
                        % (i + 1, t, cob[t]), alerta=True)
                else:
                    log("   p%d: %s parecia traco (%.4f) e eu nao consegui "
                        "medir se aparece sozinha. FICA - chapa a menos no "
                        "CTP e pior que chapa a mais na conta."
                        % (i + 1, t, cob[t]), alerta=True)
            usadas = set(usadas) - de_traco

        # Arte de uma cor vale UMA chapa, nao quatro. Duas perguntas: os
        # totais batem (preto puro OU composto), e nao ha cor gritante em
        # pixel nenhum.
        #
        # A SOLIDA ENTROU EM 14/09/2026, e o motivo de ela estar fora era
        # um engano meu. O comentario aqui dizia "a SOLIDA nunca precisou:
        # ela nao para por cor" - e sao duas coisas diferentes. Nao parar
        # por cor e sobre a TRAVA, que pergunta a gente antes de fechar
        # arte fora da quadricromia. Sair em uma chapa e sobre o CAMINHO
        # ate o CTP, e disso ela precisa igual aos outros.
        #
        # O caso: '49835 - Flor Bela - sacola.pdf', 14/09/2026. Medido, o
        # arquivo tem a arte INTEIRA no K - C 0, M 0, Y 0, K 0,38674 - e
        # saiu como CKMY, quatro chapas no CTP e quatro na OS 19688.
        # Pedido do operador: "se estiver tudo somente no canal do preto,
        # mandar a chapa pro ctp somente preto, mantendo exatamente as
        # porcentagens, e colocar na OS do gerempre somente 1 chapa".
        #
        # CUIDADO AO LER A COBERTURA DELA: a SOLIDA nao esta em
        # ENTREGAR_PDF_DIRETO, entao 'sem_icc' e False e a contagem passa
        # pelo perfil ICC embutido - que ESPALHA o preto de K sozinho nos
        # quatro canais. O mesmo arquivo le C=M=Y=K=0,3867 com perfil e
        # C=M=Y=0, K=0,3867 sem ele. As duas leituras respondem True em
        # pagina_de_uma_cor, uma pelo caminho do preto composto e a outra
        # pelo do preto puro - por isso a deteccao funciona dos dois
        # jeitos. Mas quem olhar so a lista de tintas vai ver CKMY e achar
        # que e quadricromia.
        #
        # PRETO PURO NAO TEM LISTA DE CLIENTE - 14/09/2026. "todos os
        # arquivos que vierem somente no canal do preto faca assim, de
        # todos os clientes", o operador. Arte inteira no K e um fato do
        # ARQUIVO, nao do cliente: seja quem for que mandou, ela vale uma
        # chapa e tem de sair com a porcentagem que entrou.
        #
        # O PRETO COMPOSTO continua na lista. E outra pergunta, e bem
        # mais delicada: ali o arquivo tem as quatro tintas escritas
        # dentro dele e a gente decide, pela cobertura, que aquilo era
        # para ser uma chapa so. Errar nisso funde quatro chapas numa. O
        # operador pediu o preto PURO; quando quiser o composto tambem,
        # e so tirar a lista daqui.
        # O PRETO PURO SE DECIDE NA LEITURA CRUA, E SO NELA - 15/09/2026.
        #
        # Ate hoje a leitura crua so era consultada DEPOIS de a leitura
        # com perfil ja ter dito 'isto vale uma chapa so'. Mas e
        # justamente o perfil que esconde o preto puro, e nem sempre ele
        # esconde do mesmo jeito:
        #
        #   '49835 - Flor Bela'  chapado    com perfil C=M=Y=K=0,3867
        #                                   -> parece preto composto, passa
        #   'GRADE 3386' verso   meio-tom   com perfil C 0,139 M 0,144
        #                                   Y 0,144 K 0,063 -> NAO passa
        #
        # Os dois sao K sozinho no arquivo. O primeiro e chapado, e o
        # perfil espalha o preto igualmente nos quatro canais; o segundo
        # tem meio-tom, e a conta do perfil e nao linear - os canais saem
        # desiguais e 'pagina_de_uma_cor' responde False.
        #
        # O verso do GRADE 3386 da VIVA saiu com QUATRO chapas por causa
        # disso, e a OS 19730 cobrou oito no lugar de cinco. Lido sem o
        # perfil, o mesmo verso e C 0,001 M 0,001 Y 0,001 K 0,4131 - os
        # 0,1% sao as marcas de registro.
        #
        # Entao a pergunta 'em que canal a tinta esta' passa a ser feita
        # SEMPRE ao arquivo, e nunca ao perfil. Custa uma passada a mais
        # do inkcov por arquivo - e ela e mais BARATA que a com perfil:
        # 0,9 s contra 2,3 s no proprio GRADE 3386, porque nao ha
        # conversao de cor a fazer.
        cinza = False
        crua = cob if sem_icc else cobertura_crua(i + 1)
        preto_puro = bool(crua and preto_so_no_K(crua))

        # O PRETO COMPOSTO continua sendo decidido pela leitura com
        # perfil, e continua preso a lista de clientes: ali o arquivo
        # tem as quatro tintas escritas dentro dele, e fundir as quatro
        # numa e decisao bem mais delicada.
        composto = (not preto_puro and cob is not None
                    and pagina_de_uma_cor(cob)
                    and cliente in CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO)

        if ((preto_puro or composto)
                and sem_cor_gritante(pdf, i + 1, sem_icc=sem_icc)):
            cinza = True
        else:
            # cor gritante em algum pixel, ou composto de cliente que
            # nao junta: segue quadricromia, e 'preto_puro' nao pode
            # ficar ligado a toa.
            preto_puro = False
        # as tintas que estao DENTRO do arquivo, antes de virarem GRAY.
        # E por elas que se sabe se a arte de uma cor foi desenhada com
        # uma tinta so ou com as quatro - e sao coisas bem diferentes na
        # hora de escolher o caminho ate a chapa.
        tintas_do_arquivo = set(usadas)
        if cinza:
            usadas = {"GRAY"}
            log("   p%d: cobertura C %.4f M %.4f Y %.4f K %.4f - arte de "
                "uma cor, a chapa sai em escala de cinza (%s)"
                % (i + 1, cob["C"], cob["M"], cob["Y"], cob["K"],
                   "preto puro, so no K" if preto_puro
                   else "preto composto nas quatro tintas"), alerta=True)

        # PREFLIGHT: a conferencia da arte por dentro. Ate aqui a FIA so
        # media a chapa; agora ela olha o que esta DESENHADO nela - imagem
        # esticada, fonte que falta, fio de cabelo, cor especial. Nada
        # disso da erro em lugar nenhum: aparece so na tiragem.
        if _arte_reprovada(pdf, i + 1, nome, aprovado, problemas,
                           cliente):
            continue

        base = nome_da_chapa(cliente, nome, sufixo, larg_chapa, alt_chapa,
                             usadas, i, total, pasta_saida)
        log("   p%d -> %s | %.0fx%.0f mm | %d dpi | tintas: %s"
            % (i + 1, base, larg_chapa, alt_chapa, dpi,
               "".join(sorted(usadas)) or "?"))

        # Trabalho que sempre precisa de olho, por mais que o resto esteja
        # em ordem: verniz. Pedido do operador do EMPORIO - e so dele: na
        # SOLIDA um arquivo com 'verniz' no nome sempre fechou sozinho, e
        # mudar isso pararia servico que hoje anda.
        if (cliente in (EMPORIO, VIVA, CREATIVE) and pede_olho(nome)
                and not aprovado):
            motivo = ("pagina %d: o nome diz VERNIZ. Sairia como %s. "
                      "Nao fechei: verniz se confere antes" % (i + 1, base))
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        # Quadricromia fecha sozinha, e ARTE DE UMA COR SO (o caso GRAY)
        # TAMBEM - desde 10/09/2026, por decisao do operador: "vamos
        # retirar a trava, gera o PDF normal, o nome sai GRAY e da
        # andamento normal". E 'cinza' e exatamente essa pergunta: ja
        # passou pelas duas perguntas (preto composto ou puro, e nenhuma
        # cor gritante em pixel nenhum) antes de virar chapa sozinha.
        #
        # Quem ainda para aqui e a arte de DUAS ou TRES tintas, e a
        # tinta unica que NAO e neutra (um spot color sozinho, por
        # exemplo) - 'cinza' e False nesses casos. Essas continuam sendo
        # a decisao que muda de trabalho para trabalho, e continuam
        # sendo de gente.
        #
        # O PRECO DISSO: com a trava, o palpite do cinza era conferido
        # por uma pessoa antes de virar chapa. Agora ele fecha sozinho.
        # Se 'pagina_de_uma_cor' e 'sem_cor_gritante' errarem juntos,
        # sai uma chapa cinza de uma arte colorida sem ninguem olhando -
        # e e por isso que as duas perguntas continuam sendo feitas, e a
        # linha no log continua sendo alerta.
        if (AVISAR_QUANDO_NAO_FOR_CMYK
                and cliente in (VOPRIX, EMPORIO, VIVA, CREATIVE)
                and not aprovado
                and usadas != set("CMYK") and not cinza):
            numeros = ("C %.4f M %.4f Y %.4f K %.4f"
                       % (cob["C"], cob["M"], cob["Y"], cob["K"])
                       if cob else "cobertura desconhecida")
            motivo = ("pagina %d: NAO veio em quadricromia - %s (%s). "
                      "Sairia como %s. Nao fechei: confira antes"
                      % (i + 1, "".join(sorted(usadas)) or "?", numeros, base))
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        planos.append({"pagina": pagina_da_chapa, "base": base, "dpi": dpi,
                       "arquivo": fonte_da_chapa,
                       "larg_chapa": larg_chapa, "alt_chapa": alt_chapa,
                       "usadas": usadas, "cinza": cinza,
                       "preto_puro": preto_puro, "alvo": alvo,
                       "deslocamento": deslocamento, "girar": girar,
                       "tintas_do_arquivo": tintas_do_arquivo})

    # PASSO 2: A ORDEM DE SERVICO, ANTES DA PROVA.
    #
    # So vira OS o arquivo que passou INTEIRO. Um que parou em alguma
    # pagina ja e pendencia, e quem resolve a pendencia e quem lanca -
    # cobrar meio arquivo e pior do que nao cobrar.
    numero_os = None
    # ZERADA AQUI, e nao so dentro do 'if' abaixo.
    #
    # Ela so era atribuida quando o arquivo passava INTEIRO. Num arquivo
    # com pendencia - pagina fora da quadricromia, por exemplo - o bloco
    # da OS e pulado, e a leitura mais adiante estourava
    # UnboundLocalError. O estouro caia no 'except' da impressao, que
    # entende qualquer falha ali como IMPRESSORA FORA DO AR: o resultado
    # vira 'espera', NAO entra no registro, e o arquivo e tentado de novo
    # a cada 5 minutos.
    #
    # A prova ja tinha saido antes do estouro. Entao o efeito era papel
    # saindo de 5 em 5 minutos, para sempre, do mesmo trabalho - foi o
    # que aconteceu em 10/09/2026 com o '02020 - 02021 - 02033 - CHAPA -
    # 3 MODELOS CAIXAS ZIMI.pdf' do EMPORIO, e o operador viu a pilha
    # antes de eu ver o log.
    fechou_a_quarta = False
    pdf_da_os = None
    if planos and not problemas:
        numero_os, fechou_a_quarta = _os_do_arquivo(
            nome, cliente, planos, regravacao)
        if numero_os:
            resultado["os"] = numero_os

    # PASSO 3: a prova impressa. Com OS, sai a arte na frente e a ordem
    # de servico no verso da MESMA folha. Sem OS - arquivo com pendencia,
    # ou GEREMPRE fora do ar -, sai so a frente, como sempre saiu.
    #
    # A prova nunca deixa de sair por causa da OS: e o papel que o
    # operador leva para a maquina.
    if IMPRIMIR_ORIGINAL and any(chapa_prevista(larg, alt, cliente)
                                 for larg, alt in medidas):
        verso = _verso_da_os(numero_os)
        # o PDF da OS em disco enquanto o servico anda, para quem quiser
        # abrir e conferir. Apagado no 'finally', para a pasta nao encher
        pdf_da_os = guardar_pdf(verso, numero_os) if verso else None
        try:
            etiquetas = [rotulo_prova(l, a, cliente) for l, a in medidas]
            _, folhas = imprimir(pdf, etiquetas=etiquetas, verso=verso,
                                 origem=origem)
            log("   impresso em %s (%d folha%s, %s)"
                % (IMPRESSORA, folhas, "s" if folhas > 1 else "",
                   "frente a arte, verso a OS %s" % numero_os if verso
                   else "so frente"))
            resultado["impresso"] = folhas
            # A PROVA SAIU E ERA O ULTIMO ARQUIVO DA OS. So agora ela e
            # dada por entregue - a ordem foi pedida assim: imprime o
            # verso do ultimo arquivo, ai fecha e tira o protocolo.
            #
            # Aqui dentro do 'try' de proposito: se a prova nao sair, a
            # OS NAO fecha. Papel na mao do operador e o que prova que o
            # servico saiu; sem ele, entregue seria chute.
            if fechou_a_quarta:
                _entregar_e_protocolar(numero_os, nome)
        except JaImprimiu as e:
            # A TRAVA DE COPIA UNICA pegou. Isto NAO e impressora fora do
            # ar: e o contrario - o papel ja saiu. Tratar como falha
            # poria o arquivo em 'espera', e espera vira nova tentativa,
            # que e justamente o laco que a trava existe para cortar.
            #
            # Entao o arquivo SEGUE: a prova ja esta na mao do operador.
            log("   %s" % e, alerta=True)
            resultado["impresso"] = 0
        except Exception as e:
            # Sem prova, sem chapa: segura o arquivo e tenta de novo
            # depois. A OS que ja saiu nao vira duas: na proxima passada
            # o titulo e achado nela e o numero e reaproveitado.
            log("   NAO IMPRIMIU (%s): %s" % (IMPRESSORA, e), alerta=True)
            resultado["status"] = "espera"
            resultado["motivo"] = "impressora fora: %s" % e
            resultado["impresso"] = False
            apagar_pdf(pdf_da_os)
            return resultado

    # PASSO 4: por a chapa na pasta do CTP. Pelo caminho longo - separar
    # e remontar - ou pelo curto, entregando o PDF do cliente. O nome de
    # saida, o tamanho e a conferencia final valem nos dois.
    for plano in planos:
        base = plano["base"]

        # O NOME SO SE FECHA NA HORA DE GRAVAR. Estas tres regras olham
        # os arquivos que JA ESTAO na pasta de saida, entao dependem das
        # chapas anteriores existirem em disco. Na conferencia, que agora
        # vem antes, nenhuma existe ainda: as duas paginas de um mesmo
        # arquivo escolheriam o mesmo nome, e a segunda sobrescreveria a
        # primeira. Aconteceu no Fialho, num teste, antes de ir para a
        # rua.

        # No Fialho o numero so aparece quando ha mais de uma chapa com o
        # mesmo nome. Arquivo de varias paginas ja nasce numerado.
        if cliente == FIALHO:
            base, renumerada = numerar_se_preciso(pasta_saida, base,
                                                  forcar=total > 1)
            if renumerada:
                aviso = ("outra chapa ja tinha o nome %s: ela passou a se "
                         "chamar %s e esta saiu como %s.pdf"
                         % (renumerada[0], renumerada[1], base))
                log("   ATENCAO: " + aviso, alerta=True)
                anotar_pendencia(nome, aviso)

        # Duas artes diferentes com o mesmo nome de saida. Na VOPRIX as
        # duas viram MODELO; nos outros clientes segue o _v2 de sempre.
        if cliente == VOPRIX:
            base, renomeada = resolver_modelo(pasta_saida, base)
            if renomeada:
                aviso = ("outra arte ja tinha o nome %s: ela passou a se "
                         "chamar %s e esta saiu como %s.pdf"
                         % (renomeada[0], renomeada[1], base))
                log("   ATENCAO: " + aviso, alerta=True)
                anotar_pendencia(nome, aviso)
        elif os.path.exists(os.path.join(pasta_saida, base + ".pdf")):
            aviso = ("ja existe %s.pdf (outra arte com o mesmo nome de "
                     "saida); este saiu como _v2" % base)
            log("   ATENCAO: " + aviso, alerta=True)
            anotar_pendencia(nome, aviso)

        inicio = time.time()
        try:
            # A arte de uma cor feita com as quatro tintas volta pelo
            # caminho longo, que e onde ela sempre foi resolvida: o
            # tiffgray junta tudo numa chapa so. Pelo curto sairiam
            # quatro.
            if cliente in ENTREGAR_PDF_DIRETO and cabe_no_curto(plano):
                saida, letras = _entregar_chapa(pdf, pasta_saida, base,
                                                plano, total)
            else:
                saida, letras = _gerar_chapa(
                    plano.get("arquivo") or pdf, pasta_saida, base,
                    plano["pagina"],
                    plano["dpi"], plano["larg_chapa"], plano["alt_chapa"],
                    plano["usadas"], plano["cinza"], plano["alvo"],
                    plano["deslocamento"], plano["girar"],
                    plano.get("preto_puro", False),
                    cliente in CLIENTES_QUE_VEM_DO_COREL)
        except Exception as e:
            motivo = "pagina %d: %s" % (plano["pagina"], e)
            if numero_os:
                motivo += (" - a OS %s ja foi aberta para este arquivo, "
                           "confira se ela deve ficar" % numero_os)
            log("   FALHOU: %s" % motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        mb = os.path.getsize(saida) / 1048576
        log("   OK em %.0fs: %s (%s, %.1f MB)"
            % (time.time() - inicio, os.path.basename(saida),
               "+".join(letras), mb))
        resultado["saidas"].append(os.path.basename(saida))
        resultado.setdefault("chapas", []).append(
            {"chapa": [plano["larg_chapa"], plano["alt_chapa"]],
             "tintas": len(plano["usadas"])})

    # o servico acabou: o PDF da OS sai da pasta. Ele so existia para
    # ser conferido enquanto a chapa era gravada.
    apagar_pdf(pdf_da_os)

    if problemas:
        resultado["status"] = "erro"
        resultado["motivo"] = " ; ".join(problemas)
    return resultado
