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
                     ENTREGAR_PDF_DIRETO, FORMATOS,
                     FORMATOS_CREATIVE, FORMATOS_EMPORIO, FORMATOS_FIALHO,
                     FORMATOS_VIVA, IMPRESSORA, IMPRIMIR_ORIGINAL,
                     GIRO_CREATIVE, NOMES_TINTA, PASTA_CONTROLE,
                     PINCA_CREATIVE_MM,
                     ROTULOS_PROVA, ROTULOS_PROVA_CREATIVE,
                     ROTULOS_PROVA_EMPORIO, ROTULOS_PROVA_FIALHO,
                     ROTULOS_PROVA_VIVA, ROTULOS_PROVA_VOPRIX,
                     TAMANHO_MAXIMO_MB, TOLERANCIA_MM)
from .corel import ArquivoEmUso, publicar_pdf
from .entrega import conferir as conferir_entrega
from .entrega import entregar
from .marcas import marcas_de_corte
from .ghostscript import (LIMIAR_TINTA, cobertura_por_pagina, sem_cor_gritante,
                          separar_cinza, separar_tintas, tintas_da_cobertura)
from .prova import imprimir
from .os_impressa import apagar_pdf, folha_da_os, guardar_pdf
from .nomes import (extrair_oss, nome_saida, nome_saida_creative,
                    nome_saida_emporio, nome_saida_fialho, nome_saida_viva,
                    nome_saida_voprix, pede_olho, resumo_fialho)
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
    return PINCA_CREATIVE_MM if cliente == CREATIVE else 0


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
        return (larg, alt), dpi, sufixo, False

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
    return tabela.get(chapa_prevista(larg, alt, cliente), "")


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
    if cliente == CREATIVE:
        return nome_saida_creative(nome,
                                   formato_no_nome(larg, alt, cliente),
                                   tintas, indice, total)
    if cliente == FIALHO:
        # o numero entra no laco, olhando a pasta - so quando ha mais de
        # uma chapa com o mesmo nome
        return "%s_FIALHO_%s" % (formato_no_nome(larg, alt, cliente),
                                 resumo_fialho(nome))
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
                 cinza=False, alvo=None, deslocamento=None, girar=0):
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
            tif = separar_cinza(origem, dpi, tmp, pagina)
            saida = nome_livre(pasta_saida, base)
            letras = montar_pdf_cinza(tif, saida, larg, alt, alvo=alvo,
                                      deslocamento=deslocamento)
            conferir(saida, larg, alt, dpi)
            return saida, letras

        separar_tintas(origem, dpi, tmp, pagina)

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


def processar(caminho, pasta_saida, cliente=SOLIDA, aprovado=False):
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
    if cliente == VOPRIX:
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
                              resultado, falhar, aprovado)
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


def _os_do_arquivo(nome, cliente, planos):
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
                    "tintas": len(p["usadas"])} for p in planos]})
    if not servico:
        return None, False

    # a memoria do dia: e ela que enxerga dois arquivos com a mesma OS
    atual = fila.carregar()
    ja_estava = any(s["cliente"] == servico["cliente"]
                    and s["titulo"] == servico["titulo"] for s in atual)
    depois = fila.entrar(servico, atual)
    if not ja_estava and len(depois) == len(atual):
        return None                 # a fila recusou e ja anotou o porque
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
        return folha_da_os(numero)
    except Exception as e:
        log("   nao consegui desenhar a folha da OS %s (%s). A prova sai "
            "so na frente." % (numero, str(e)[:70]), alerta=True)
        return None


def _processar_pdf(pdf, nome, pasta_saida, cliente, resultado, falhar,
                   aprovado=False):
    """
    O caminho comum aos dois clientes, pagina a pagina.

    'pdf' e o arquivo que vai ser lido e impresso - na VOPRIX, o que a
    Corel acabou de gerar. 'nome' e sempre o do arquivo original, que e
    quem manda no nome de saida.
    """
    # Quem vai pelo caminho curto entrega o arquivo e a gravadora separa.
    # Ai a tinta tem de ser contada como esta ESCRITA no arquivo, sem
    # passar pelo perfil embutido: e a conta da gravadora que vale, e e
    # ela que decide o nome da chapa e quantas chapas a OS cobra.
    # Ver ghostscript.sem_perfil, com os numeros.
    sem_icc = cliente in ENTREGAR_PDF_DIRETO

    try:
        medidas = medir_paginas(pdf)
        cobertura = cobertura_por_pagina(pdf, sem_icc=sem_icc)
    except Exception as e:
        return falhar("PDF ilegivel: %s" % e)

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
                motivo = ("pagina %d: nao achei a marca de corte (lado %s), "
                          "e e dela que sai a pinca. Nao montei a chapa - "
                          "chutar a pinca e mandar servico errado"
                          % (i + 1, lado))
                log("   " + motivo, alerta=True)
                anotar_pendencia(nome, motivo)
                problemas.append(motivo)
                continue
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
        elif encaixou:
            log("   p%d: arte %.0fx%.0f mm entra centralizada na chapa "
                "%.0fx%.0f - sobra cortada dos dois lados"
                % (i + 1, larg, alt, larg_chapa, alt_chapa), alerta=True)

        cob = cobertura[i] if i < len(cobertura) else None
        usadas = tintas_da_cobertura(cob) if cob else set("CMYK")

        # Arte de uma cor so chega como preto composto (C, M, Y e K em
        # partes iguais). Vale uma chapa em cinza, nao quatro. Duas
        # perguntas: os totais batem, e nao ha cor gritante em pixel nenhum.
        # Vale para VOPRIX e EMPORIO - os dois ja escrevem GRAY a mao.
        cinza = (cliente in (VOPRIX, EMPORIO, VIVA, CREATIVE)
                 and cob is not None
                 and pagina_de_uma_cor(cob)
                 and sem_cor_gritante(pdf, i + 1, sem_icc=sem_icc))
        # as tintas que estao DENTRO do arquivo, antes de virarem GRAY.
        # E por elas que se sabe se a arte de uma cor foi desenhada com
        # uma tinta so ou com as quatro - e sao coisas bem diferentes na
        # hora de escolher o caminho ate a chapa.
        tintas_do_arquivo = set(usadas)
        if cinza:
            usadas = {"GRAY"}
            log("   p%d: cobertura C %.4f M %.4f Y %.4f K %.4f - arte de "
                "uma cor, a chapa sai em escala de cinza"
                % (i + 1, cob["C"], cob["M"], cob["Y"], cob["K"]), alerta=True)

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

        # Quadricromia fecha sozinha. Fora dela, quem manda fechar e gente:
        # o programa para aqui, com os numeros na tela, e guarda o PDF.
        if (AVISAR_QUANDO_NAO_FOR_CMYK
                and cliente in (VOPRIX, EMPORIO, VIVA, CREATIVE)
                and not aprovado and usadas != set("CMYK")):
            numeros = ("C %.4f M %.4f Y %.4f K %.4f"
                       % (cob["C"], cob["M"], cob["Y"], cob["K"])
                       if cob else "cobertura desconhecida")
            motivo = ("pagina %d: NAO veio em quadricromia - %s (%s). "
                      "Sairia como %s. Nao fechei: confira antes"
                      % (i + 1, "".join(sorted(usadas)) or "?", numeros, base))
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        planos.append({"pagina": i + 1, "base": base, "dpi": dpi,
                       "larg_chapa": larg_chapa, "alt_chapa": alt_chapa,
                       "usadas": usadas, "cinza": cinza, "alvo": alvo,
                       "deslocamento": deslocamento, "girar": girar,
                       "tintas_do_arquivo": tintas_do_arquivo})

    # PASSO 2: A ORDEM DE SERVICO, ANTES DA PROVA.
    #
    # So vira OS o arquivo que passou INTEIRO. Um que parou em alguma
    # pagina ja e pendencia, e quem resolve a pendencia e quem lanca -
    # cobrar meio arquivo e pior do que nao cobrar.
    numero_os = None
    pdf_da_os = None
    if planos and not problemas:
        numero_os, fechou_a_quarta = _os_do_arquivo(nome, cliente, planos)
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
            _, folhas = imprimir(pdf, etiquetas=etiquetas, verso=verso)
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
                    pdf, pasta_saida, base, plano["pagina"],
                    plano["dpi"], plano["larg_chapa"], plano["alt_chapa"],
                    plano["usadas"], plano["cinza"], plano["alvo"],
                    plano["deslocamento"], plano["girar"])
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
