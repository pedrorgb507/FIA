# -*- coding: utf-8 -*-
r"""
A sangria de um arquivo, lida pelos DOIS caminhos - e a divergencia dita.

SANGRIA e a arte avancando ALEM da linha de corte, para que o corte caia
dentro do desenho e nao no branco do papel. Guilhotina nao acerta a linha
no fio: ela varia um milimetro para cada lado, e sem sangria essa
variacao aparece como um fio branco na borda do impresso.

POR QUE DOIS CAMINHOS, e nao o melhor deles. Cada um cobre o buraco do
outro:

  A DECLARADA sai das caixas do PDF - a TrimBox diz onde se corta, a
  BleedBox diz ate onde a arte vai, e a diferenca e a sangria. E de
  graca e exata quando esta escrita. So que muitos arquivos nao trazem
  TrimBox nenhuma - e ai ela nao responde;

  A DA TINTA rasteriza a pagina e olha se o DESENHO passa da marca de
  corte para fora. Responde em arquivo que nao declara nada, e custa
  segundos de Ghostscript. So que ela depende de haver marca de corte
  reconhecivel - sem marca nao se sabe onde e a linha, e 'passou da
  linha' deixa de querer dizer algo.

A ARMADILHA DA CAIXA QUE FALTA, que e a razao de este modulo existir. A
especificacao do PDF manda: faltando a TrimBox, ela VALE O MEDIABOX.
Entao um arquivo que nao declara nada tem TrimBox igual a BleedBox igual
ao papel, a conta acha ZERO, e a resposta sai 'pelado' com toda a
confianca. Nao e pelado: e NAO DECLARADO. Sao coisas diferentes e a
diferenca decide se a tinta e consultada - por isso a leitura declarada
devolve None, e nao zero, quando a caixa nao esta la.

A OUTRA ARMADILHA E A MARCA DE CORTE SER TINTA. Ela vive fora da linha de
corte de proposito, junto com a marca de registro. Contando 'qualquer
tinta alem da linha', TODO arquivo com marca pareceria sangrado. O que
conta e o DESENHO - faixa larga -, e nao o risco fino: e a mesma
separacao que o america.medir_o_pe faz para a pinca, e os numeros que a
separam (RISCO_MM, PX_POR_MM) vem de la, medidos em arquivo de verdade.

E QUANDO OS DOIS DISCORDAM, ISTO NAO ESCOLHE. Arquivo que declara 3 mm e
mostra a arte parando na linha de corte e justamente o que engana:
confiar na declaracao poria o corte dentro do desenho; confiar so na
tinta mandaria refazer sangria que talvez exista. Os dois numeros sobem
ditos, e quem decide e gente. E a regra da casa - entre errar sozinha e
parar para perguntar, a FIA para.
"""

import os
import shutil
import subprocess
import tempfile

from .america import PX_POR_MM, RISCO_MM

PT = 72.0
MM = 25.4

# Abaixo disto nao e sangria, e arredondamento de caixa de PDF. E o mesmo
# numero que o sangrar.py usa desde que ele existe.
MINIMO_MM = 1.0

# Abaixo disto (0-255) o pixel e tinta. E o mesmo numero que o
# america.medir_o_pe usa escrito a mao no laco dele; mexer la para
# importa-lo daqui seria mexer na conta da PINCA, que e trava paga com
# chapa errada. Ficam dois, e fica dito onde esta o gemeo.
LIMIAR_TINTA = 245

# De onde a medida declarada saiu. Sao constantes, e nao texto solto, para
# quem decide poder comparar sem farejar palavra dentro de frase.
DO_BLEEDBOX = "do BleedBox"
DO_MEDIABOX = ("do MediaBox, que pode incluir a area das marcas de corte")
SEM_TRIMBOX = ("o arquivo nao declara TrimBox - nao da para saber onde ele "
               "quer ser cortado")

# E de onde saiu a medida da PECA (ver medida_do_corte).
DA_TRIMBOX = "da TrimBox declarada no arquivo"
DO_PAPEL = "do MediaBox - o arquivo nao declara corte"

LADOS = ("pe", "topo", "esquerda", "direita")

# Como cada lado se le numa frase. O recado da sangria vai para a TELA DA
# EQUIPE, e nao para o log: 'no direita' trava a leitura de quem esta
# conferindo arquivo as pressas.
COMO_SE_DIZ = {"pe": "no pe", "topo": "no topo",
               "esquerda": "na esquerda", "direita": "na direita"}


def _mm_escrito(valor):
    """3.0 -> '3,0 mm'. Virgula, que e como a casa escreve medida."""
    return ("%.1f mm" % valor).replace(".", ",")


# ----------------------------------------------------------------------
# CAMINHO 1: o que o arquivo DECLARA
# ----------------------------------------------------------------------

def sangria_do_arquivo(pdf, pagina=1):
    """
    Quantos mm de sangria a pagina tem por lado, pelo BLEEDBOX.

    A caixa certa e o BleedBox, e nao o MediaBox, e a diferenca nao e
    academica. O CARTA_FRENTE de setembro tem MediaBox 233,28 x 320,28
    e corte 210 x 297: medido pelo papel daria 11,64 mm de sangria. Mas
    o BleedBox e 216 x 303 - a sangria e 3 mm, e os outros 8,64 sao a
    area das MARCAS DE CORTE, que nao sangram nada.

    O erro seria caro nos dois sentidos. Um arquivo com marcas e SEM
    sangria - BleedBox igual ao TrimBox - passaria por sangrado, e a
    montagem marcaria o corte 3 mm dentro do desenho. E quem rasteriza
    a peca ja usa -dUseBleedBox: medir por outra caixa seria medir uma
    coisa e cortar outra.

    ESTE E O NOME ANTIGO DA CASA, e ele responde como sempre respondeu -
    um numero, sem dizer de onde veio. O sangrar.py o chama desde que
    existe. Quem precisa saber se a caixa estava LA pergunta ao
    sangria_declarada.
    """
    from pypdf import PdfReader
    pag = PdfReader(pdf).pages[pagina - 1]
    corte = pag.trimbox
    # PDF sem BleedBox: o pypdf devolve o MediaBox, que e o que a
    # especificacao manda mesmo
    sangra = pag.bleedbox
    return min((float(corte.left) - float(sangra.left),
                float(corte.bottom) - float(sangra.bottom),
                float(sangra.right) - float(corte.right),
                float(sangra.top) - float(corte.top))) / PT * MM


def ja_tem_sangria(pdf, pagina=1, minimo_mm=MINIMO_MM):
    """
    (tem, mm_por_lado) - o arquivo ja chega sangrado, e por quanto?

    Um arquivo pelado tem TrimBox igual ao BleedBox: e a arte acabando
    exatamente na linha de corte.
    """
    mm = sangria_do_arquivo(pdf, pagina)
    return mm >= minimo_mm, mm


def medida_do_corte(pdf, pagina=1):
    """
    (largura, altura, de_onde) da PECA em mm - o tamanho que se corta.

    NAO E A MEDIDA DO PAPEL, e confundir as duas sai caro no painel: o
    campo de lá e a peca, e a sangria entra num campo separado. Um
    arquivo de 100x150 com 3 mm de sangria tem papel de 106x156;
    preenchendo o painel com 106x156 a sangria seria contada duas vezes,
    e a peca sairia 6 mm maior do que o cliente pediu.

    Com TRIMBOX declarada, ela e a resposta - e exatamente ali que o
    arquivo diz que quer ser cortado. Sem ela, vale o papel: e o que ha,
    e vem dito de onde veio.

    O /ROTATE CONTA AQUI TAMBEM. Ele gira a pagina na hora de mostrar, e
    quem monta ve a pagina girada: uma peca de 100x150 com /Rotate 90 se
    ve 150x100. Ignorando isso, a peca sai TRANSPOSTA e o painel monta a
    chapa inteira em cima de uma peca virada. E a mesma correcao do
    onde_o_desenho_comeca e do entrega.py - as leituras tem de estar
    todas falando da pagina como ela se ve.
    """
    from pypdf import PdfReader
    try:
        pag = PdfReader(pdf).pages[pagina - 1]
    except Exception as e:
        return None, None, "nao consegui abrir o arquivo: %s" % str(e)[:80]

    caixa, de_onde = pag.mediabox, DO_PAPEL
    if pag.get("/TrimBox") is not None:
        caixa, de_onde = pag.trimbox, DA_TRIMBOX
    larg = float(caixa.width) / PT * MM
    alt = float(caixa.height) / PT * MM
    if (int(pag.get("/Rotate") or 0) % 360) in (90, 270):
        larg, alt = alt, larg
    return larg, alt, de_onde


def sangria_declarada(pdf, pagina=1):
    """
    (mm, de_onde) do que o arquivo DECLARA, ou (None, porque).

    DEVOLVE None - E NAO ZERO - QUANDO NAO HA TRIMBOX. E a armadilha do
    cabecalho deste modulo: sem TrimBox a especificacao manda ela valer o
    MediaBox, a conta acha zero, e 'pelado' sai com a cara de resposta.
    Aqui a falta da caixa e dita, para a tinta poder responder no lugar.

    Sem BLEEDBOX vale o MediaBox - que e o que a especificacao manda -,
    mas isso vem DITO no 'de_onde': o MediaBox costuma incluir a area das
    marcas de corte, que nao sangram nada, e ai o numero e um teto e nao
    uma medida.
    """
    from pypdf import PdfReader
    try:
        pag = PdfReader(pdf).pages[pagina - 1]
    except Exception as e:
        return None, "nao consegui abrir o arquivo: %s" % str(e)[:80]

    if pag.get("/TrimBox") is None:
        return None, SEM_TRIMBOX
    de_onde = (DO_BLEEDBOX if pag.get("/BleedBox") is not None
               else DO_MEDIABOX)
    try:
        return sangria_do_arquivo(pdf, pagina), de_onde
    except Exception as e:
        return None, "nao consegui ler as caixas: %s" % str(e)[:80]


# ----------------------------------------------------------------------
# CAMINHO 2: a tinta alem da marca de corte
# ----------------------------------------------------------------------

def _perfis(pdf, pagina):
    """
    (por_linha, por_coluna, largura_px, altura_px) da pagina rasterizada.

    Cada perfil diz QUANTA tinta ha em cada linha e em cada coluna. Sai do
    proprio Pillow, reduzindo a imagem a uma coluna e a uma linha - em C,
    e nao pixel por pixel em Python: uma pagina de 650x550 mm tem cinco
    milhoes e meio de pixels, e varre-la a mao custaria mais que o
    Ghostscript que a gerou.
    """
    from PIL import Image

    from .ghostscript import GS
    pasta = tempfile.mkdtemp(prefix="sangria_")
    png = os.path.join(pasta, "p.png")
    try:
        subprocess.run(
            [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
             "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
             "-sDEVICE=png16m", "-r%d" % int(PX_POR_MM * MM),
             "-dUseFastColor=true", "-o", png, pdf],
            check=True, capture_output=True, timeout=600)
        with Image.open(png) as im:
            # tinta virada em 255, papel em 0 - assim a media de uma
            # linha e proporcional a QUANTA tinta ela tem
            tinta = im.convert("L").point(
                lambda v: 255 if v < LIMIAR_TINTA else 0)
            larg, alt = tinta.size
            # tobytes() de uma imagem "L" e um byte por pixel, na ordem -
            # e nao passa pelo getdata(), que o Pillow esta aposentando
            por_linha = list(tinta.resize((1, alt), Image.BOX).tobytes())
            por_coluna = list(tinta.resize((larg, 1), Image.BOX).tobytes())
        return por_linha, por_coluna, larg, alt
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def _primeira_faixa_larga(perfil, atravessa, px_por_mm, de_tras):
    """
    A quantos mm da borda comeca o DESENHO, andando de fora para dentro.

    'atravessa' e quantos pixels tem a linha no outro sentido: e por ele
    que a media volta a ser contagem. Faixa com menos tinta que RISCO_MM
    e marca de corte, nao desenho - ver o cabecalho.

    Devolve None quando nao ha desenho nenhum, que e o caso da pagina em
    branco e o da pagina que so tem marcas.
    """
    minimo = RISCO_MM * px_por_mm
    indices = range(len(perfil) - 1, -1, -1) if de_tras else range(len(perfil))
    for quantos, i in enumerate(indices):
        # media (0-255) de volta para contagem de pixels com tinta
        if perfil[i] * atravessa / 255.0 > minimo:
            return quantos / px_por_mm
    return None


def onde_o_desenho_comeca(pdf, pagina=1):
    """
    {lado: mm da borda} onde o DESENHO comeca, em cada um dos quatro
    lados. O valor e None no lado em que nao se achou desenho.

    Devolve {} quando nao deu para rasterizar - Ghostscript fora do ar,
    arquivo quebrado. Nao estoura: quem chamou decide o que fazer com o
    silencio.

    NAO E 'ONDE COMECA A TINTA'. A marca de corte e tinta, e mora fora da
    linha de corte de proposito. Ver o cabecalho do modulo.
    """
    try:
        por_linha, por_coluna, larg, alt = _perfis(pdf, pagina)
    except Exception:
        return {}

    from pypdf import PdfReader
    try:
        pag = PdfReader(pdf).pages[pagina - 1]
        caixa = pag.mediabox
        alt_mm = float(caixa.height) / PT * MM
        # O /ROTATE GIRA A PAGINA NA HORA DE MOSTRAR, e o Ghostscript
        # rasteriza JA GIRADO: com /Rotate 90 uma pagina de 106x156
        # sai numa imagem de 156x106. Tirando a escala da altura do
        # MediaBox, a conta erra na proporcao entre os dois lados - 3 mm
        # de sangria viravam 4,4, a subtracao dava negativo, e arquivo
        # sangrado aparecia como pelado. O marcas.py ja corrigia isto
        # (ver DE_ONDE_VEM_CADA_LADO); as duas leituras tem de estar
        # falando da MESMA pagina.
        if (int(pag.get("/Rotate") or 0) % 360) in (90, 270):
            alt_mm = float(caixa.width) / PT * MM
    except Exception:
        return {}

    # A ESCALA SAI DA IMAGEM, e nao do que eu pedi ao Ghostscript: o -r
    # so aceita dpi inteiro, e pedir 4 px/mm vira 101 dpi, que sao 3,976.
    # Dividir pelos 4 que eu queria erra 0,6% - 2,4 mm aos 400. E a mesma
    # correcao do america.medir_o_pe, e ela nasceu de um teste sintetico.
    px_por_mm = alt / alt_mm
    return {
        # a linha 0 da imagem e o TOPO da pagina
        "topo": _primeira_faixa_larga(por_linha, larg, px_por_mm, False),
        "pe": _primeira_faixa_larga(por_linha, larg, px_por_mm, True),
        "esquerda": _primeira_faixa_larga(por_coluna, alt, px_por_mm, False),
        "direita": _primeira_faixa_larga(por_coluna, alt, px_por_mm, True),
    }


def sangria_pela_tinta(pdf, pagina=1):
    """
    (mm, de_onde) medido na tinta, ou (None, porque).

    A conta, por lado: a marca de corte diz a quantos mm da borda esta a
    linha de corte; o desenho diz a quantos mm da borda ele comeca. O que
    ha entre uma coisa e a outra e a sangria daquele lado.

    VALE O MENOR DOS LADOS, porque sangria e GARANTIA: o lado mais magro
    e o que vai aparecer branco no impresso.

    E POR ISSO A RESPOSTA E ASSIMETRICA quando nao se conferiu tudo -
    havendo marca em dois lados so, os outros dois nao foram medidos por
    ninguem:

      um lado conferido SEM sangria decide sozinho. Nao falta informacao:
      aquele lado ja vai sair com fio branco, e saber dos outros nao
      mudaria a resposta;

      todos os conferidos COM sangria NAO decidem, se sobrou lado sem
      conferir. Dizer 'tem sangria' olhando metade da peca e prometer
      garantia que ninguem deu - e era o que esta funcao fazia.

    SEM MARCA DE CORTE ELA NAO RESPONDE. Sem saber onde se corta, 'o
    desenho passou da linha' nao quer dizer nada - e chutar aqui e mandar
    montar errado com cara de quem sabia.
    """
    from .marcas import marcas_de_corte

    achadas = marcas_de_corte(pdf, pagina)
    if not any(achadas.get(lado) is not None for lado in LADOS):
        return None, ("nao achei marca de corte - sem ela nao sei onde o "
                      "arquivo quer ser cortado")

    comecos = onde_o_desenho_comeca(pdf, pagina)
    if not comecos:
        return None, "nao consegui rasterizar a pagina para olhar a tinta"

    por_lado, faltou = {}, []
    for lado in LADOS:
        marca, desenho = achadas.get(lado), comecos.get(lado)
        if marca is None or desenho is None:
            faltou.append(lado)
            continue
        por_lado[lado] = max(0.0, marca - desenho)
    if not por_lado:
        return None, ("achei marca de corte, mas nao achei desenho nos "
                      "lados marcados - a pagina esta em branco?")

    magro = min(por_lado, key=lambda lado: por_lado[lado])
    medida = por_lado[magro]
    visto = ("da tinta: %s o desenho passa %s da marca de corte, e e o "
             "lado mais magro dos que conferi"
             % (COMO_SE_DIZ[magro], _mm_escrito(medida)))

    if faltou and medida >= MINIMO_MM:
        return None, ("%s - mas nao conferi %s: sem marca de corte naquele "
                      "lado nao sei onde se corta, e sangria e garantia "
                      "dos QUATRO lados"
                      % (visto, " nem ".join(COMO_SE_DIZ[lado].split()[-1]
                                             for lado in faltou)))
    return medida, visto


# ----------------------------------------------------------------------
# OS DOIS JUNTOS
# ----------------------------------------------------------------------

def _numero_que_se_mostra(declarada, declarada_de, pela_tinta):
    """
    Das duas medidas, a que vale como numero na tela.

    A declarada manda quando saiu do BLEEDBOX: ali ela e exata e de
    graca, e a da tinta carrega o arredondamento de uma imagem de
    4 px/mm. Saindo do MediaBox, ela e um TETO - e teto nao e medida.
    """
    if declarada is not None and declarada_de == DO_BLEEDBOX:
        return declarada
    if pela_tinta is not None:
        return pela_tinta
    return declarada


def ler_a_sangria(pdf, pagina=1, minimo_mm=MINIMO_MM):
    """
    As duas leituras e a conclusao:

        {"tem": True | False | None,
         "mm": mm | None,              <- o numero que se MOSTRA
         "declarada": mm | None, "pela_tinta": mm | None,
         "declarada_de": texto | None,
         "de_onde": texto, "divergem": bool, "recado": texto}

    O 'mm' NAO E SEMPRE A DECLARADA. Havendo BleedBox, a declaracao e
    exata e de graca, e ela manda. Mas sem BleedBox a declarada sai do
    MediaBox, que costuma incluir a area das marcas de corte - o
    CARTA_FRENTE de setembro daria 11,64 mm onde a sangria e 3. Ali as
    duas leituras CONCORDAM que tem sangria, entao nao ha divergencia
    para avisar, e mostrar o teto passaria por medida. Nesse caso manda a
    tinta, que mediu o desenho de verdade.

    'tem' e None quando nao da para saber - e isso e resposta, nao falha.
    Acontece em dois casos, e os dois estao no recado: nenhuma das duas
    leituras respondeu, ou as duas responderam COISAS DIFERENTES.

    DIVERGENCIA NAO SE RESOLVE AQUI, de proposito. Um arquivo que declara
    3 mm e mostra a arte parando na linha de corte engana das duas
    maneiras: confiando na declaracao, o corte cai dentro do desenho;
    confiando na tinta, manda-se refazer sangria que talvez exista.
    Escolher um e calar e o unico jeito garantido de errar sem ninguem
    ver.

    A DIVERGENCIA SE MEDE NA CONCLUSAO, e nao no numero. 3,0 e 2,6 sao
    medidas diferentes da mesma coisa - as duas dizem 'tem sangria' -, e
    tratar isso como briga enche a tela de aviso que nao muda nada. O que
    diverge de verdade e uma dizer tem e a outra dizer nao tem.
    """
    declarada, porque_d = sangria_declarada(pdf, pagina)
    pela_tinta, porque_t = sangria_pela_tinta(pdf, pagina)

    lido = {"declarada": declarada, "pela_tinta": pela_tinta,
            "declarada_de": porque_d if declarada is not None else None,
            "mm": _numero_que_se_mostra(declarada, porque_d, pela_tinta),
            "tem": None, "de_onde": None, "divergem": False, "recado": ""}

    diz_d = None if declarada is None else declarada >= minimo_mm
    diz_t = None if pela_tinta is None else pela_tinta >= minimo_mm

    if diz_d is None and diz_t is None:
        lido["recado"] = ("nao da para saber se tem sangria: %s; e %s"
                          % (porque_d, porque_t))
        return lido

    if diz_d is None or diz_t is None:
        # uma das duas ficou calada, e a outra e a resposta. E o caso do
        # arquivo sem TrimBox, que NAO vira 'sem sangria' por omissao
        lido["tem"] = diz_d if diz_t is None else diz_t
        sozinha = porque_d if diz_t is None else porque_t
        muda = porque_t if diz_t is None else porque_d
        lido["de_onde"] = sozinha
        lido["recado"] = ("%s %s (%s). A outra leitura nao respondeu: %s"
                          % ("tem sangria de" if lido["tem"] else "sem "
                             "sangria -",
                             _mm_escrito(declarada if diz_t is None
                                         else pela_tinta),
                             sozinha, muda))
        return lido

    if diz_d == diz_t:
        lido["tem"] = diz_d
        lido["de_onde"] = "as duas leituras concordam"
        lido["recado"] = ("%s: declarada %s (%s), medida na tinta %s"
                          % ("tem sangria" if diz_d else "SEM sangria",
                             _mm_escrito(declarada), porque_d,
                             _mm_escrito(pela_tinta)))
        return lido

    # AS DUAS DISCORDAM. Ninguem escolhe por ninguem.
    lido["divergem"] = True
    lido["de_onde"] = "as duas leituras discordam"
    lido["recado"] = (
        "AS DUAS LEITURAS DISCORDAM, e arquivo que declara uma coisa e "
        "mostra outra e o que engana: o arquivo DECLARA %s de sangria "
        "(%s), e na TINTA o desenho %s (%s). Confira antes de montar."
        % (_mm_escrito(declarada), porque_d,
           "passa %s da marca de corte" % _mm_escrito(pela_tinta) if diz_t
           else "para na linha de corte - passa %s" % _mm_escrito(pela_tinta),
           porque_t))
    return lido
