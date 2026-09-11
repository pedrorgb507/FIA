# -*- coding: utf-8 -*-
r"""
Cria sangria em arte que chegou sem ela. NAO ALTERA O ARQUIVO DE ORIGEM.

A pergunta do operador em 11/09/2026: "se o material chegar sem sangria,
voce consegue fazer essa sangria?". Consigo - mas nao sempre, e a parte
que importa e justamente saber QUANDO NAO.

O QUE NUNCA SE FAZ, e e o que quase todo mundo faz: AMPLIAR A ARTE ate
ela cobrir a sangria. Ampliando 150x210 para 156x216 tudo cresce 4% -
o texto, a logomarca, o corte. O impresso deixa de ter o tamanho que foi
pedido. Sangria se ACRESCENTA por fora; nunca se estica o que ja existe.

A SAIDA NUNCA RASTERIZA, e a razao e dupla. Um PDF do designer esta em
CMYK: cada objeto diz quanto tem de ciano, magenta, amarelo e preto, e e
isso que vira as quatro chapas. Rasterizar joga tudo para RGB - tela,
nao papel - e para voltar a CMYK alguem tem de RE-SEPARAR, sem saber o
que era antes: um preto que era so K vira as quatro tintas, e o texto
preto sai com quatro chapas empilhadas, que qualquer desregistro borra;
um Pantone vira a mistura mais parecida. Pelo mesmo caminho morre o
vetor, que deixa de ter contorno e passa a ter pixel.

Entao a sangria aqui e FEITA DE TRANSFORMACAO, nao de pixel: a propria
pagina e colocada NOVE vezes na pagina nova - o miolo, quatro espelhos
nas bordas e quatro nos cantos - cada copia caindo na sua faixa. Um
espelho e so uma matriz com -1 na diagonal. Vetor continua vetor, CMYK
continua CMYK, Pantone continua Pantone, e imagem continua na resolucao
que tinha. Serve igual para arte vetorial e para arte que e uma foto so.

O rasterizador aqui embaixo existe para OLHAR, nunca para produzir: e
pela imagem que se decide o que ha em cada borda. Olhar em RGB nao custa
nada - a decisao sai a mesma, e o arquivo que sai nao passou por ele.

O QUE SE FAZ, e depende do que ha NA BORDA:

  branco    a arte acaba em branco. Nao ha o que sangrar - o papel ja e
            branco. Deixa em branco;
  chapado   a borda e uma cor so, parada. O espelho devolve a mesma cor:
            o resultado e EXATO, ninguem distingue do original;
  espelho   a borda tem foto ou textura que continua. Espelha a faixa
            para fora. E invencao, mas plausivel: a continuacao de uma
            textura e mais textura;
  OLHO      ha um traco, uma moldura ou uma letra PARADA na linha de
            corte. Espelhar duplicaria o traco, e a duplicata apareceria
            no impresso. A sangria sai assim mesmo, para o operador ter
            o que olhar, mas o achado sobe como PARA: quem decide e
            gente.

A conferencia roda POR BORDA - uma arte pode ter as quatro diferentes.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finart_ctp.ghostscript import GS                      # noqa: E402

MM = 25.4
PT = 72.0

BORDAS = ("topo", "base", "esquerda", "direita")

# Quanto a cor pode variar dentro da faixa e ainda contar como "chapado".
# 0-255 por canal; 3 e o ruido de compressao de um JPEG bom.
LIMIAR_CHAPADO = 3.0

# Acima disto (0-255) ha um traco atravessado na faixa da sangria, e
# espelhar duplicaria ele. Medido como a MAIOR mudanca de uma linha para
# a seguinte, andando de fora para dentro.
LIMIAR_TRACO = 34.0

# Perto disto a arte acaba em branco e nao ha o que sangrar.
LIMIAR_BRANCO = 247.0

# Resolucao de quem so OLHA. Nao precisa ser a da chapa: o que se procura
# e um fio na borda, e 150 dpi ja mostra fio de 0,25 mm.
DPI_ANALISE = 150

# Sangria de uma peca sozinha na chapa, que nao tem vizinha nem vao.
SANGRIA_PECA_SOZINHA = 2.5

# Abaixo disto a diferenca e ruido de arredondamento de PDF, nao sangria.
FOLGA_MM = 0.02


def regra_da_sangria(vao_mm, pecas):
    """
    Quanta sangria a peca tem de ter. A REGRA DA CASA, num lugar so.

    Regra do operador, 11/09/2026:

        "a sangria nao precisa ser 3mm, ela pode ficar estabelecida
        metade do vao que estiver no meio - se o vao for 5mm ela fica
        2,5mm, se o vao no meio for 3mm ela fica 1,5mm; e se a montagem
        for somente com 1 imagem, ela fica com sangria para todos os
        lados de 2,5mm como padrao."

    E a medida que o vao comporta, e da para ver por que. A guilhotina
    corta DUAS vezes no vao - uma na borda de cada peca - e a tira do
    meio e refugo. Cada peca sangra para dentro desse refugo, e METADE
    DO VAO e a maior sangria que cabe sem uma invadir a metade da outra:
    as duas se encontram no meio da tira e param ali.

    Cuidado com a explicacao fácil, que eu mesmo escrevi errado antes de
    medir: com vao 5 e sangria 3 as duas sangrias somam 6 e se
    sobrepoem 1 mm - mas essa sobreposicao cai INTEIRA no refugo, entre
    as duas linhas de corte, e nao chega ao impresso. Nao era defeito.
    O que a regra da e outra coisa: cada peca passa a ser dona exata da
    sua metade, ninguem pinta por cima de ninguem, e a sangria deixa de
    ser um numero solto para virar consequencia do vao - se o vao muda,
    ela muda junto, sem ninguem ter de lembrar.

    Peca sozinha nao tem vizinha nem vao - ai o numero e de gosto, e o
    da casa e 2,5.
    """
    if pecas <= 1:
        return SANGRIA_PECA_SOZINHA
    return vao_mm / 2.0


# --------------------------------------------------------------------------
# olhar - rasteriza so para decidir
# --------------------------------------------------------------------------

def rasterizar(pdf, pagina, dpi, caixa="TrimBox"):
    """
    A pagina, na caixa pedida, como imagem RGB do Pillow.

    So para OLHAR. O que sai para a chapa nao passa por aqui.
    """
    import tempfile

    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    tmp = tempfile.mkdtemp(prefix="sangrar_")
    alvo = os.path.join(tmp, "p.png")
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
         "-sDEVICE=png16m", "-r%d" % dpi, "-dUse%s" % caixa,
         "-dUseFastColor=true",
         "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-sOutputFile=" + alvo, pdf],
        capture_output=True, text=True, timeout=1800)
    if not os.path.exists(alvo):
        raise RuntimeError((r.stderr or "o Ghostscript nao rasterizou")[:300])
    im = Image.open(alvo).convert("RGB")
    im.load()
    return im


def _faixa(im, borda, fundo):
    """
    A faixa de 'fundo' pixels junto a uma borda, sempre virada do mesmo
    jeito: a linha 0 e a que ENCOSTA na borda, e andar para baixo e
    andar para DENTRO da arte.

    Virar tudo para o mesmo sentido e o que deixa a conferencia ser uma
    so, em vez de quatro parecidas - e quatro parecidas e onde se
    esconde o erro de sinal.
    """
    L, A = im.size
    if borda == "topo":
        return im.crop((0, 0, L, fundo))
    if borda == "base":
        return im.crop((0, A - fundo, L, A)).transpose(1)     # FLIP_TOP_BOTTOM
    if borda == "esquerda":
        return im.crop((0, 0, fundo, A)).transpose(5)         # ROTATE_270
    if borda == "direita":
        return im.crop((L - fundo, 0, L, A)).transpose(4)     # ROTATE_90
    raise ValueError(borda)


def _medir(faixa):
    """(media, variacao_ao_longo, maior_degrau_atravessando) da faixa."""
    from PIL import ImageStat
    st = ImageStat.Stat(faixa)
    media = sum(st.mean) / 3.0
    ao_longo = sum(st.stddev) / 3.0

    # o degrau: quanto a cor muda de uma linha para a seguinte, andando
    # de fora para dentro. Um traco parado na linha de corte aparece
    # aqui como um degrau grande.
    linhas = []
    L = faixa.size[0]
    for y in range(faixa.size[1]):
        st_l = ImageStat.Stat(faixa.crop((0, y, L, y + 1)))
        linhas.append(sum(st_l.mean) / 3.0)
    degrau = max((abs(b - a) for a, b in zip(linhas, linhas[1:])), default=0.0)
    return media, ao_longo, degrau


def decidir(im, borda, sangria_px):
    """
    (tecnica, porque) para esta borda.

    A faixa olhada e um pouco mais funda que a sangria: e do que esta
    LOGO ADIANTE da linha de corte que se sabe o que viria depois dela.
    """
    fundo = max(3, min(int(sangria_px * 1.5), min(im.size) // 3))
    faixa = _faixa(im, borda, fundo)
    media, ao_longo, degrau = _medir(faixa)

    if media >= LIMIAR_BRANCO and ao_longo <= LIMIAR_CHAPADO:
        return "branco", "a arte acaba em branco (media %.0f)" % media
    if ao_longo <= LIMIAR_CHAPADO and degrau <= LIMIAR_CHAPADO:
        return "chapado", "cor chapada (varia %.1f ao longo)" % ao_longo
    if degrau >= LIMIAR_TRACO:
        return "olho", ("ha um traco atravessado a %.1f de degrau - "
                        "espelhar duplicaria ele" % degrau)
    return "espelho", "textura que continua (varia %.1f)" % ao_longo


def conferir_bordas(pdf, pagina, sangria_mm, dpi=DPI_ANALISE, caixa="TrimBox"):
    """
    {borda: (tecnica, porque)} para a pagina.

    A caixa e a borda A PARTIR DA QUAL se vai inventar. Num arquivo
    pelado e o TrimBox; num que ja traz alguma sangria, e o BleedBox -
    e dali para fora que falta desenho, e e la que se olha se ha fio
    parado que o espelho duplicaria.
    """
    im = rasterizar(pdf, pagina, dpi, caixa)
    s_px = max(2, int(round(sangria_mm / MM * dpi)))
    return {b: decidir(im, b, s_px) for b in BORDAS}


# --------------------------------------------------------------------------
# produzir - transformacao, nunca pixel
# --------------------------------------------------------------------------

def _recortar(pag, dono, caixa):
    """
    Faz a pagina pintar SO dentro desta caixa.

    Com isso as nove copias podem ser colocadas sem recorte nenhum
    depois: cada espelho cai exatamente na sua faixa e em lugar nenhum
    mais, porque o espelho de um retangulo e outro retangulo. Sem isto,
    o que o arquivo por acaso desenhe para fora da caixa - marca de
    corte, informacao de servico na margem - entraria de carona na
    sangria nova.

    A caixa e o BLEEDBOX, e nao o corte: quando o arquivo ja traz alguma
    sangria, ela e boa e fica. O que se inventa e so o que falta DEPOIS
    dela.

    'pag' tem de estar presa a um PdfWriter: desde o pypdf 6 mexer no
    conteudo de uma pagina solta do leitor e 'unreliable', e diz isso em
    aviso. Por isso sangrar_pdf clona o arquivo num writer antes.
    """
    from pypdf.generic import ContentStream, DecodedStreamObject

    dados = ContentStream(pag.get_contents(), dono).get_data()
    cabeca = ("q %.4f %.4f %.4f %.4f re W n\n"
              % (float(caixa.left), float(caixa.bottom),
                 float(caixa.width), float(caixa.height))).encode("latin-1")
    fluxo = DecodedStreamObject()
    fluxo.set_data(cabeca + dados + b"\nQ\n")
    pag.replace_contents(fluxo)
    return pag


def _matrizes(corte, s):
    """
    As nove colocacoes, em pontos. Cada uma e (a, b, c, d, e, f).

    O -1 na diagonal e o espelho. 'e'/'f' sao escolhidos para que a
    dobradica caia EXATAMENTE na linha de corte da pagina nova - e por
    isso que a tinta encosta na linha sem degrau e sem folga.
    """
    x0, y0 = float(corte.left), float(corte.bottom)
    L, A = float(corte.width), float(corte.height)

    # onde a dobradica de cada sentido fica
    dx_nada, dx_esq, dx_dir = s - x0, s + x0, s + 2 * L + x0
    dy_nada, dy_bai, dy_cim = s - y0, s + y0, s + 2 * A + y0

    def m(ex, ey, tx, ty):
        return (ex, 0, 0, ey, tx, ty)

    return [
        ("centro",   m(1, 1, dx_nada, dy_nada)),
        ("esquerda", m(-1, 1, dx_esq, dy_nada)),
        ("direita",  m(-1, 1, dx_dir, dy_nada)),
        ("base",     m(1, -1, dx_nada, dy_bai)),
        ("topo",     m(1, -1, dx_nada, dy_cim)),
        ("inf-esq",  m(-1, -1, dx_esq, dy_bai)),
        ("inf-dir",  m(-1, -1, dx_dir, dy_bai)),
        ("sup-esq",  m(-1, -1, dx_esq, dy_cim)),
        ("sup-dir",  m(-1, -1, dx_dir, dy_cim)),
    ]


VIZINHOS = {"inf-esq": ("base", "esquerda"), "inf-dir": ("base", "direita"),
            "sup-esq": ("topo", "esquerda"), "sup-dir": ("topo", "direita")}


def _so_papel(pag, decisoes, folga_pt=0.5):
    """
    True quando a sangria desta pagina e so papel branco.

    Duas condicoes, e as duas precisam valer. As quatro bordas tem de
    acabar em branco - senao ha o que espelhar. E o desenho nao pode
    passar da area sangrada, senao o que esta la fora entraria de carona
    e precisaria do recorte.
    """
    if any(decisoes[b][0] != "branco" for b in BORDAS):
        return False
    sangra, papel = pag.bleedbox, pag.mediabox
    return (abs(float(sangra.left) - float(papel.left)) <= folga_pt
            and abs(float(sangra.bottom) - float(papel.bottom)) <= folga_pt
            and abs(float(sangra.right) - float(papel.right)) <= folga_pt
            and abs(float(sangra.top) - float(papel.top)) <= folga_pt)


def sangrar_pdf(pdf, destino, sangria_mm=SANGRIA_PECA_SOZINHA,
                dpi_analise=DPI_ANALISE, paginas=None):
    """
    Grava um PDF com EXATAMENTE 'sangria_mm' de sangria por lado.

    Tanto faz quanta o arquivo ja tinha - o que ele tem e bom e fica:

      falta   inventa-se so o que falta, espelhando para fora do que ja
              existe. Um arquivo com 2 mm indo para 2,5 ganha meio
              milimetro espelhado da borda da sangria dele, e nao perde
              os 2 mm que o designer desenhou;
      sobra   recorta-se, e recortar NAO MEXE NO DESENHO - so na caixa.
              Um arquivo com 3 mm indo para 2,5 e o mesmo arquivo com o
              BleedBox meio milimetro menor;
      bate    nao se faz nada.

    O TrimBox continua onde estava e do tamanho que era: quem monta le
    o TrimBox e sabe onde cortar. Nada e rasterizado.
    """
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, FloatObject

    alvo_pt = sangria_mm / MM * PT
    # o molde e um CLONE: o arquivo de origem nunca e tocado, e a pagina
    # clonada esta presa a um writer, que e o que o pypdf 6 exige de quem
    # vai mexer no conteudo
    molde_doc = PdfWriter(clone_from=pdf)
    escritor = PdfWriter()
    relato = {"sangria_mm": sangria_mm, "paginas": [], "precisa_de_olho": []}

    def caixa(*v):
        return ArrayObject([FloatObject(x) for x in v])

    alvo = list(paginas or range(1, len(molde_doc.pages) + 1))
    for n in alvo:
        origem = molde_doc.pages[n - 1]
        corte, sangra = origem.trimbox, origem.bleedbox
        L, A = float(corte.width), float(corte.height)

        tinha = sangria_do_arquivo(pdf, n)
        s = (sangria_mm - tinha) / MM * PT      # o que FALTA, em pontos

        if s <= FOLGA_MM / MM * PT:
            # ja tem o bastante: a sangria nova e um RECORTE da que
            # existe, e recorte e so caixa. O desenho nao e tocado.
            nova = escritor.add_page(origem)
            x0, y0 = float(corte.left), float(corte.bottom)
            fora = caixa(x0 - alvo_pt, y0 - alvo_pt,
                         x0 + L + alvo_pt, y0 + A + alvo_pt)
            nova.mediabox, nova.cropbox, nova.bleedbox = fora, fora, fora
            nova.trimbox = caixa(x0, y0, x0 + L, y0 + A)
            decisoes = {b: ("recortado", "o arquivo ja trazia %.2f mm"
                            % tinha) for b in BORDAS}
            olhos = []
            relato["paginas"].append({
                "pagina": n, "decisoes": decisoes, "olhos": olhos,
                "tinha_mm": tinha, "criou_mm": 0.0,
                "corte_mm": (L / PT * MM, A / PT * MM),
                "com_sangria_mm": ((L + 2 * alvo_pt) / PT * MM,
                                   (A + 2 * alvo_pt) / PT * MM)})
            continue

        # falta sangria: espelha para fora do que JA existe. A analise
        # tambem olha a borda do BleedBox - e dali para fora que se
        # inventa, e nao da linha de corte.
        decisoes = conferir_bordas(pdf, n, sangria_mm - tinha, dpi_analise,
                                   "BleedBox")
        olhos = [b for b in BORDAS if decisoes[b][0] == "olho"]
        SL, SA = float(sangra.width), float(sangra.height)

        if _so_papel(origem, decisoes):
            # As quatro bordas acabam em branco e nao ha nada pintado
            # fora: a sangria e papel, e papel nao se desenha. Entao nao
            # se mexe no conteudo - so se abre a caixa em volta dele.
            # Isto nao e so economia: o cupom da MEGA MOVEIS tem 23 MB
            # de conteudo, e reescrever o desenho para colar branco em
            # volta engordava o arquivo de 8,7 para 23,9 MB e levava 36
            # segundos, para nao mudar um pixel.
            nova = escritor.add_page(origem)
            x0, y0 = float(corte.left), float(corte.bottom)
            fora = caixa(x0 - alvo_pt, y0 - alvo_pt,
                         x0 + L + alvo_pt, y0 + A + alvo_pt)
            nova.mediabox, nova.cropbox, nova.bleedbox = fora, fora, fora
            nova.trimbox = caixa(x0, y0, x0 + L, y0 + A)
        else:
            molde = _recortar(origem, molde_doc, sangra)
            nova = escritor.add_blank_page(width=SL + 2 * s, height=SA + 2 * s)

            for nome, ctm in _matrizes(sangra, s):
                if nome in BORDAS and decisoes[nome][0] == "branco":
                    continue          # papel branco ja e a resposta
                if nome in VIZINHOS:
                    a, b = VIZINHOS[nome]
                    if (decisoes[a][0] == "branco"
                            and decisoes[b][0] == "branco"):
                        continue
                nova.merge_transformed_page(molde, ctm)

            # o conteudo remontado sai CRU do pypdf. Sem isto o arquivo
            # engorda pelo tamanho do desenho descomprimido, que num
            # cupom grande passa dos 20 MB.
            try:
                nova.compress_content_streams()
            except Exception:
                pass                  # comprimir e economia, nao correcao

            # a pagina nova E a area sangrada. O corte fica onde ele
            # estava DENTRO da sangria que veio, mais o que se criou.
            tx = float(corte.left) - float(sangra.left) + s
            ty = float(corte.bottom) - float(sangra.bottom) + s
            fora = caixa(0, 0, SL + 2 * s, SA + 2 * s)
            nova.mediabox, nova.cropbox, nova.bleedbox = fora, fora, fora
            nova.trimbox = caixa(tx, ty, tx + L, ty + A)

        relato["paginas"].append({
            "pagina": n, "decisoes": decisoes, "olhos": olhos,
            "tinha_mm": tinha, "criou_mm": sangria_mm - tinha,
            "corte_mm": (L / PT * MM, A / PT * MM),
            "com_sangria_mm": ((L + 2 * alvo_pt) / PT * MM,
                               (A + 2 * alvo_pt) / PT * MM)})
        for b in olhos:
            relato["precisa_de_olho"].append((n, b, decisoes[b][1]))

    with open(destino, "wb") as f:
        escritor.write(f)
    return relato


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


def ja_tem_sangria(pdf, pagina=1, minimo_mm=1.0):
    """
    (tem, mm_por_lado) - o arquivo ja chega sangrado, e por quanto?

    Um arquivo pelado tem TrimBox igual ao BleedBox: e a arte acabando
    exatamente na linha de corte.
    """
    mm = sangria_do_arquivo(pdf, pagina)
    return mm >= minimo_mm, mm


# --------------------------------------------------------------------------
# arte que e IMAGEM solta, fora de PDF - preserva o modo de cor
# --------------------------------------------------------------------------

def sangrar_imagem(im, sangria_px, decisoes):
    """
    A imagem com a sangria acrescentada POR FORA. Nada e esticado.

    O modo de cor da imagem e MANTIDO: CMYK entra CMYK e sai CMYK. Um
    .convert('RGB') aqui remisturaria o preto de K sozinho nas quatro
    tintas, que e o defeito que esta funcao existe para nao ter.
    """
    from PIL import Image
    L, A = im.size
    s = sangria_px
    # no CMYK o papel e ZERO de tinta; no RGB e 255 de luz
    branco = (0, 0, 0, 0) if im.mode == "CMYK" else (255,) * len(im.getbands())
    nova = Image.new(im.mode, (L + 2 * s, A + 2 * s), branco)
    nova.paste(im, (s, s))

    def encher(borda, tecnica):
        if tecnica == "branco":
            return                      # a tela ja nasceu branca
        if borda in ("topo", "base"):
            tira = (im.crop((0, 0, L, s)) if borda == "topo"
                    else im.crop((0, A - s, L, A))).transpose(1)
            nova.paste(tira, (s, 0 if borda == "topo" else s + A))
        else:
            tira = (im.crop((0, 0, s, A)) if borda == "esquerda"
                    else im.crop((L - s, 0, L, A))).transpose(0)
            nova.paste(tira, (0 if borda == "esquerda" else s + L, s))

    for borda, (tecnica, _) in decisoes.items():
        encher(borda, tecnica)

    # os quatro cantos: espelhados nos dois sentidos. Canto e o encontro
    # de duas bordas, e nenhuma das duas manda sozinha nele.
    for cx, cy, ox, oy in ((0, 0, 0, 0), (L - s, 0, s + L, 0),
                           (0, A - s, 0, s + A), (L - s, A - s, s + L, s + A)):
        canto = im.crop((cx, cy, cx + s, cy + s)).transpose(0).transpose(1)
        nova.paste(canto, (ox, oy))
    return nova


def sangrar_arquivo_de_imagem(caminho, destino, sangria_mm=3.0, dpi=None):
    """Sangra um .tif/.jpg/.png solto, sem mexer no modo de cor."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(caminho)
    im.load()
    dpi = dpi or (im.info.get("dpi") or (300, 300))[0]
    s = max(1, int(round(sangria_mm / MM * dpi)))

    olhar = im.convert("RGB")           # so para DECIDIR
    decisoes = {b: decidir(olhar, b, s) for b in BORDAS}
    nova = sangrar_imagem(im, s, decisoes)
    nova.save(destino, dpi=(dpi, dpi))
    return {"decisoes": decisoes, "modo": im.mode, "dpi": dpi,
            "olhos": [b for b in BORDAS if decisoes[b][0] == "olho"]}


# --------------------------------------------------------------------------

def _relatar(r):
    for p in r["paginas"]:
        print("pagina %d   corte %.2f x %.2f  ->  com sangria %.2f x %.2f mm"
              % (p["pagina"], p["corte_mm"][0], p["corte_mm"][1],
                 p["com_sangria_mm"][0], p["com_sangria_mm"][1]))
        for borda in BORDAS:
            tecnica, porque = p["decisoes"][borda]
            marca = ">>>" if tecnica == "olho" else "   "
            print("  %s %-9s %-8s %s" % (marca, borda, tecnica, porque))
    if r["precisa_de_olho"]:
        print()
        for n, b, porque in r["precisa_de_olho"]:
            print("PARA  p%d %s: %s" % (n, b, porque))
        print("Nao invento traco - isso quem decide e gente.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("uso: sangrar.py <arquivo.pdf> [sangria_mm]")
    entrada = sys.argv[1]
    mm_ = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    saida = os.path.splitext(entrada)[0] + "_SANGRADO.pdf"

    tem, quanto = ja_tem_sangria(entrada)
    if tem:
        raise SystemExit("este arquivo JA chega com %.2f mm de sangria por "
                         "lado - nao mexo" % quanto)

    _relatar(sangrar_pdf(entrada, saida, mm_))
    print()
    print("gerado: %s" % saida)
