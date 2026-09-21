# -*- coding: utf-8 -*-
r"""
Descobre a IMPOSICAO de uma montagem que a casa ja fez. NAO ESCREVE NADA.

O ler_paginacao_preps.py le a dobra num MODELO do Preps. Este le a dobra
no RESULTADO: recebe a arte e a montagem que saiu dela, e responde qual
pagina da arte caiu em cada celula da chapa.

POR QUE ISTO EXISTE. O catalogo de dobras do paginacao.py saiu dos
modelos de EXEMPLO do Preps - os que vem com o programa. A casa tem
quinze anos de montagem feita a mao, e o que ela de fato faz esta nos
PDFs que ela gravou, nao num modelo. Aqui se pergunta a eles.

COMO ELE ACHA AS CELULAS. Nao por suposicao de grade: pela TINTA. A
montagem tem vao entre as pecas, e vao e papel branco. Somando a tinta
coluna a coluna, os vaos aparecem como vales; o que esta entre dois
vales e uma coluna de pecas. O mesmo nas linhas. Assim a grade sai do
arquivo, e nao de uma conta que eu tenha imaginado.

COMO ELE RECONHECE A PAGINA. Cada celula e reduzida a uma assinatura -
uma miniatura de poucos pixels - e comparada com a assinatura de cada
pagina da arte, nos quatro giros. Fica a de menor diferenca. Miniatura
basta: paginas diferentes de um livro sao MUITO diferentes em mancha, e
o que se quer saber e QUAL pagina, nao se ela esta perfeita.

    python ferramentas/ler_montagem_da_casa.py <arte.pdf> <montagem.pdf>
    python ferramentas/ler_montagem_da_casa.py <arte> <montagem> --pagina 2
"""

import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from finart_ctp.ghostscript import GS                  # noqa: E402

MM = 72.0 / 25.4
# 4 px/mm sao ~100 dpi. A 2 px/mm - a primeira tentativa - toda pagina
# de texto de um livro vira a MESMA mancha cinza, e o reconhecimento
# respondia sempre a mesma pagina, com diferenca baixa e convincente.
PX_MM = 4.0
LADO = 40              # a assinatura tem LADO x LADO pixels
# Acima disto a celula nao reconheceu nada - pegou pedaco de duas pecas,
# ou a grade esta torta. Medido: celula certa fica abaixo de 30, e as
# muito boas abaixo de 5.
LIMITE_DIF = 45.0


def _pillow():
    from PIL import Image
    return Image


def renderizar(pdf, pagina, px_mm=PX_MM):
    """A pagina como imagem cinza, em px_mm pixels por milimetro."""
    Image = _pillow()
    if not GS:
        raise SystemExit("sem Ghostscript nao ha como olhar o arquivo")
    dpi = int(round(px_mm * 25.4))
    tmp = tempfile.mkdtemp(prefix="ler_montagem_")
    saida = os.path.join(tmp, "p.png")
    # -dUseTrimBox: o que interessa e o que esta DENTRO DO CORTE. As
    # marcas do designer vivem fora dele e so atrapalhariam a conta da
    # tinta - virariam 'coluna' onde nao ha peca nenhuma.
    subprocess.run(
        [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pnggray",
         "-dUseTrimBox", "-r%d" % dpi,
         "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-sOutputFile=" + saida, pdf],
        capture_output=True, timeout=600)
    if not os.path.exists(saida):
        raise SystemExit("o Ghostscript nao devolveu a pagina %d de %s"
                         % (pagina, os.path.basename(pdf)))
    return Image.open(saida).convert("L")


def perfil(img, eixo):
    """
    A media de cinza de cada coluna (eixo 0) ou linha (eixo 1).

    Feito com o proprio redimensionamento do Pillow - achatar a imagem
    para um pixel de altura E a media das colunas, e sai em C. Em
    Python, pixel a pixel, uma chapa de 600 mm a 2 px/mm custava
    segundos por pagina.
    """
    Image = _pillow()
    larg, alt = img.size
    if eixo == 0:
        return list(img.resize((larg, 1), Image.BILINEAR).tobytes())
    return list(img.resize((1, alt), Image.BILINEAR).tobytes())


def _extremos(p, corte=0.10):
    """(primeiro, ultimo) indice com tinta - a caixa do desenho."""
    if not p:
        return None
    fundo = max(p)
    limite = fundo - (fundo - min(p)) * corte
    tem = [i for i, v in enumerate(p) if v < limite]
    return (tem[0], tem[-1]) if tem else None


def grade(img, peca_l_mm, peca_a_mm, px_mm=PX_MM, vao_max=20.0):
    """
    ([colunas], [linhas]) em pixels - onde cada peca comeca e acaba.

    A PRIMEIRA VERSAO DISTO NAO FUNCIONOU, e o motivo vale escrito: ela
    procurava os VAOS como faixas sem tinta e juntava as curtas. Mas um
    vao tem cinco milimetros e uma tira branca DENTRO de uma peca pode
    ter vinte - entao nao ha tamanho que separe as duas coisas, e a
    juncao colou a chapa inteira numa celula so.

    O que funciona e usar o que ja se sabe: O TAMANHO DA PECA. Mede-se a
    caixa da tinta na chapa e pergunta-se quantas pecas cabem nela, nos
    dois sentidos. So uma combinacao fecha com vao positivo e pequeno, e
    a conta se confere sozinha: o vao achado na largura tem de bater com
    o achado na altura, porque e o mesmo vao.
    """
    melhor = None
    for pl, pa in ((peca_l_mm, peca_a_mm), (peca_a_mm, peca_l_mm)):
        ex = _eixo(perfil(img, 0), pl, px_mm, vao_max)
        ey = _eixo(perfil(img, 1), pa, px_mm, vao_max)
        if not ex or not ey:
            continue
        # O MESMO VAO NOS DOIS EIXOS e a conferencia: a casa usa um vao
        # so numa montagem. Sentido que exige 5 mm de um lado e 40 do
        # outro nao e o certo - e coincidencia.
        erro = abs(ex[2] - ey[2])
        if melhor is None or erro < melhor[0]:
            melhor = (erro, ex, ey, pl, pa)
    if melhor is None:
        return [], []
    _e, ex, ey, pl, pa = melhor
    return (_faixas(ex, pl, px_mm), _faixas(ey, pa, px_mm))


def _faixas(eixo, peca_mm, px_mm):
    ini, n, vao = eixo
    passo = (peca_mm + vao) * px_mm
    larg = peca_mm * px_mm
    return [(int(round(ini + i * passo)),
             int(round(ini + i * passo + larg - 1))) for i in range(n)]


def _eixo(p, peca_mm, px_mm, vao_max):
    r"""
    (inicio, quantas, vao) das pecas neste eixo - ou None.

    A CAIXA DA TINTA NAO SERVE PARA ACHAR A GRADE, e foi o que a segunda
    versao disto descobriu. Pagina de livro tem margem branca: a tinta
    de duas pecas de 205 mm empilhadas mede 386 mm, nao 410, e a conta
    'quantas pecas cabem na caixa' concluia que nao cabia nenhuma.

    O que se mede aqui e o COMPASSO. Uma grade repete a cada peca mais
    vao, e essa repeticao aparece na autocorrelacao do perfil de tinta.
    Como o tamanho da peca e conhecido, o compasso so pode estar entre
    'peca' e 'peca + vao_max' - uma janela estreita, barata de varrer, e
    que nao tem como cair num multiplo errado.

    Sabido o compasso, o inicio sai dos VAOS: entre uma peca e outra ha
    papel branco, entao desliza-se a grade ate os vaos caírem no lugar
    de menos tinta. E as pecas sao contadas pelos centros que caem
    dentro da mancha, com folga para a margem branca das bordas.
    """
    tinta = [255 - v for v in p]
    total = len(tinta)
    if total < 8 or max(tinta) <= 0:
        return None

    peca_px = peca_mm * px_mm
    caixa = _extremos(p)
    if not caixa:
        return None

    # --- 1. o compasso, entre peca e peca + vao_max ---
    lag0, lag1 = int(round(peca_px)), int(round((peca_mm + vao_max) * px_mm))
    lag1 = min(lag1, total - 4)
    # A CORRELACAO TEM DE SER SEM A MEDIA, e isto custou uma rodada. Com
    # o sinal cru, o que domina a conta e o ENVELOPE - a mancha inteira
    # tem tinta, entao quanto menor o deslocamento mais ela se sobrepoe a
    # si mesma, e o maximo cai sempre no menor lag da janela. Saiu
    # compasso de 135,5 mm (vao de meio milimetro) numa montagem de vao
    # 5,5. Tirando a media, o que sobra e a ONDULACAO - as pecas e os
    # vaos -, e o pico cai no compasso de verdade.
    dentro = tinta[caixa[0]:caixa[1] + 1]
    if len(dentro) < 16:
        return (caixa[0], 1, 0.0)
    media = sum(dentro) / float(len(dentro))
    onda = [t - media for t in tinta]
    base = sum(onda[i] * onda[i] for i in range(caixa[0], caixa[1] + 1, 2))
    base = base / float(max(1, len(range(caixa[0], caixa[1] + 1, 2))))

    melhor_lag, melhor_c = None, -1e18
    for lag in range(max(2, lag0), max(3, lag1 + 1)):
        n = total - lag
        if n < 8:
            break
        c = sum(onda[i] * onda[i + lag] for i in range(0, n, 2)) / float(n)
        if c > melhor_c:
            melhor_c, melhor_lag = c, lag

    # SEM REPETICAO E UMA PECA SO: a ondulacao nao se reencontra em lag
    # nenhum daquela janela.
    if melhor_lag is None or melhor_c < base * 0.12:
        return (caixa[0], 1, 0.0)

    passo = float(melhor_lag)
    vao = passo / px_mm - peca_mm
    if vao < -1.0:
        return (caixa[0], 1, 0.0)
    vao = max(0.0, vao)

    # --- 2. onde a grade comeca: os vaos no lugar de menos tinta ---
    vao_px = max(1, int(round(vao * px_mm)))
    melhor_ini, melhor_soma = caixa[0], None
    for ini in range(max(0, caixa[0] - int(peca_px)), caixa[0] + 1):
        soma, quantos = 0.0, 0
        k = 1
        while True:
            a = int(round(ini + k * passo - vao_px))
            b = int(round(ini + k * passo))
            if b >= caixa[1]:
                break
            soma += sum(tinta[a:b + 1])
            quantos += 1
            k += 1
        if not quantos:
            continue
        media = soma / quantos
        if melhor_soma is None or media < melhor_soma:
            melhor_soma, melhor_ini = media, ini

    # --- 3. quantas pecas: os centros que caem na mancha ---
    folga = peca_px * 0.45
    n = 0
    while True:
        centro = melhor_ini + n * passo + peca_px / 2.0
        if centro > caixa[1] + folga:
            break
        n += 1
        if n > 24:
            break
    return (melhor_ini, max(1, n), round(vao, 2))


def assinatura(img, caixa):
    """A miniatura LADO x LADO de um pedaco, como lista de cinzas."""
    Image = _pillow()
    corte = img.crop(caixa)
    if corte.size[0] < 4 or corte.size[1] < 4:
        return None
    return list(corte.resize((LADO, LADO), Image.BILINEAR).tobytes())


def _diferenca(a, b):
    r"""
    Quanto DUAS assinaturas discordam: 0 = iguais, 100 = nada a ver.

    NAO E A DIFERENCA CRUA DOS CINZAS, e isto tambem custou uma rodada.
    Paginas de miolo tem todas a mesma densidade media, entao a
    diferenca absoluta entre duas paginas QUAISQUER de um livro e
    pequena e parecida - o reconhecimento escolhia quase ao acaso, com
    numeros que pareciam bons.

    O que separa uma pagina da outra e ONDE a tinta esta, nao quanta ha.
    Entao tira-se a media de cada uma e mede-se a correlacao entre as
    duas ondulacoes: casa o desenho, e nao o tom. Pagina em branco, que
    nao tem ondulacao nenhuma, e tratada a parte - senao ela casaria
    com tudo.
    """
    n = float(len(a))
    ma, mb = sum(a) / n, sum(b) / n
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    va = sum(x * x for x in da)
    vb = sum(y * y for y in db)
    if va <= 1e-9 or vb <= 1e-9:
        # uma das duas e lisa: so casam se as duas forem
        return 0.0 if (va <= 1e-9 and vb <= 1e-9) else 100.0
    r = sum(x * y for x, y in zip(da, db)) / (va ** 0.5 * vb ** 0.5)
    return (1.0 - r) * 50.0


def _giros(dados):
    """As quatro voltas de uma assinatura quadrada."""
    Image = _pillow()
    img = Image.new("L", (LADO, LADO))
    img.putdata(dados)
    return {0: list(img.tobytes()),
            90: list(img.rotate(90, expand=True).tobytes()),
            180: list(img.rotate(180, expand=True).tobytes()),
            270: list(img.rotate(270, expand=True).tobytes())}


def assinaturas_da_arte(arte, quantas=None, px_mm=PX_MM):
    """{pagina: {giro: assinatura}} de cada pagina da arte."""
    import pypdf
    total = len(pypdf.PdfReader(arte).pages)
    if quantas:
        total = min(total, quantas)
    saida = {}
    for n in range(1, total + 1):
        img = renderizar(arte, n, px_mm)
        base = assinatura(img, (0, 0) + img.size)
        if base:
            saida[n] = _giros(base)
    return saida


def ler(arte, montagem, pagina=1, px_mm=PX_MM, limite_paginas=None):
    """
    O que ha em cada celula desta pagina da montagem.

    Devolve {'grade': (cols, linhas), 'celulas': [...]} - cada celula
    com a coluna, a linha, a pagina da arte que mais se parece, o giro e
    a diferenca (quanto menor, mais certo).
    """
    import pypdf

    pag_arte = pypdf.PdfReader(arte).pages[0]
    cx = pag_arte.trimbox or pag_arte.mediabox
    pl, pa = float(cx.width) / MM, float(cx.height) / MM

    img = renderizar(montagem, pagina, px_mm)
    fichas = assinaturas_da_arte(arte, limite_paginas, px_mm)
    melhor = _melhor_grade(img, pl, pa, px_mm, fichas)
    if melhor is None:
        return {"grade": (0, 0), "celulas": [],
                "peca": (round(pl, 1), round(pa, 1)),
                "chapa": (round(img.size[0] / px_mm, 1),
                          round(img.size[1] / px_mm, 1))}
    return dict(melhor,
                peca=(round(pl, 1), round(pa, 1)),
                chapa=(round(img.size[0] / px_mm, 1),
                       round(img.size[1] / px_mm, 1)))


def _celulas_da_grade(img, caixa, nc, nr, pw, ph, px_mm, fichas):
    """As celulas de uma grade candidata, ja reconhecidas."""
    x0b, x1b, y0b, y1b = caixa
    larg, alt = pw * px_mm, ph * px_mm
    # a grade se assenta CENTRADA na mancha: as pecas das bordas tem
    # margem branca, entao a mancha e menor que a montagem, mas esta
    # centrada nela do mesmo jeito
    passo_x = ((x1b - x0b) - larg) / float(nc - 1) if nc > 1 else 0
    passo_y = ((y1b - y0b) - alt) / float(nr - 1) if nr > 1 else 0
    cx = (x0b + x1b) / 2.0 - larg / 2.0 - passo_x * (nc - 1) / 2.0
    cy = (y0b + y1b) / 2.0 - alt / 2.0 - passo_y * (nr - 1) / 2.0

    celulas = []
    for li in range(nr):
        for ci in range(nc):
            x = cx + ci * passo_x
            y = cy + li * passo_y
            a = assinatura(img, (int(x), int(y),
                                 int(x + larg), int(y + alt)))
            if a is None:
                return None
            escolha = (None, None, 1e9)
            for n, voltas in fichas.items():
                for g, dados in voltas.items():
                    d = _diferenca(a, dados)
                    if d < escolha[2]:
                        escolha = (n, g, d)
            celulas.append({"coluna": ci + 1, "linha": li + 1,
                            "pagina": escolha[0], "giro": escolha[1],
                            "diferenca": round(escolha[2], 1),
                            "mm": (round(x / px_mm, 1), round(y / px_mm, 1),
                                   round(larg / px_mm, 1),
                                   round(alt / px_mm, 1))})
    return celulas


def _melhor_grade(img, pl, pa, px_mm, fichas):
    r"""
    Experimenta as grades possiveis e fica com a que RECONHECE melhor.

    DUAS HEURISTICAS FALHARAM ANTES DESTA, e as duas pelo mesmo motivo -
    tentavam achar a grade olhando so para a geometria da chapa:

      1. procurar os vaos como faixas sem tinta. Um vao tem 5 mm e uma
         tira branca dentro de uma peca pode ter 20: nao ha tamanho que
         separe os dois, e a chapa inteira virou uma celula;
      2. medir a caixa da tinta e perguntar quantas pecas cabem nela.
         Pagina de livro tem margem branca, entao a caixa e MENOR que a
         montagem e a conta concluia que nao cabia nenhuma. Corrigido
         para autocorrelacao, ela escolheu o sentido errado da peca.

    O que decide de verdade e outra coisa, e ela estava a mao o tempo
    todo: A GRADE CERTA E A QUE CASA. Com a grade certa, cada celula
    reconhece uma pagina DIFERENTE da arte, e com pouca diferenca; com a
    grade errada, as celulas pegam pedacos de duas pecas e reconhecem
    qualquer coisa, repetindo pagina e com diferenca alta.

    Entao se experimenta cada grade que caberia e se pontua pelo
    resultado do reconhecimento. E caro - reconhece tudo varias vezes -
    e e a unica medida que nao depende de eu adivinhar nada.
    """
    caixa_x = _extremos(perfil(img, 0))
    caixa_y = _extremos(perfil(img, 1))
    if not caixa_x or not caixa_y:
        return None
    caixa = (caixa_x[0], caixa_x[1], caixa_y[0], caixa_y[1])
    larg_mm = (caixa_x[1] - caixa_x[0]) / px_mm
    alt_mm = (caixa_y[1] - caixa_y[0]) / px_mm

    candidatos = []
    for pw, ph in ((pl, pa), (pa, pl)):
        # +1 porque a mancha e menor que a montagem: cabe uma peca a
        # mais do que a conta crua diz
        for nc in range(1, int(larg_mm / pw) + 2):
            for nr in range(1, int(alt_mm / ph) + 2):
                if nc * nr > 64:
                    continue
                cel = _celulas_da_grade(img, caixa, nc, nr, pw, ph,
                                        px_mm, fichas)
                if not cel:
                    continue
                difs = [c["diferenca"] for c in cel]
                media = sum(difs) / len(difs)
                repetidas = len(cel) - len(set(c["pagina"] for c in cel))
                candidatos.append(
                    {"grade": (nc, nr), "celulas": cel, "celas": nc * nr,
                     "diferenca_media": round(media, 1),
                     "repetidas": repetidas})

    if not candidatos:
        return None

    # A GRADE MAIOR QUE AINDA CASA, e nao a de melhor media. Esta e a
    # terceira correcao aqui, e veio de ver a chapa 2 dos Canticos sair
    # 2x2 onde a 1 saiu 4x2: com duas celulas so, as duas pegam pedacos
    # grandes e casam com alguma coisa por acaso - media boa, sem
    # repetir, e errado. Media baixa e barata quando ha pouca celula.
    #
    # Entao primeiro se filtra o que RECONHECE de verdade - nenhuma
    # pagina repetida e diferenca media dentro do aceitavel - e entre
    # esses fica o que cobre mais chapa. Nao havendo nenhum, devolve-se
    # o menos ruim, e a diferenca media alta ja diz para desconfiar.
    bons = [c for c in candidatos
            if c["repetidas"] == 0 and c["diferenca_media"] <= LIMITE_DIF]
    if bons:
        bons.sort(key=lambda c: (-c["celas"], c["diferenca_media"]))
        return bons[0]
    candidatos.sort(key=lambda c: (c["diferenca_media"]
                                   + c["repetidas"] * 12.0))
    return candidatos[0]


def ler_o_trabalho(arte, montagem, limite_paginas=None, px_mm=PX_MM):
    r"""
    Todas as chapas de uma montagem, com UMA grade so.

    AS CHAPAS DE UM TRABALHO COMPARTILHAM A GRADE, e isto nao e
    suposicao: e o que uma montagem E. Quatro pecas em duas fileiras na
    chapa 1 sao quatro pecas em duas fileiras na chapa 3 - muda o que
    cai em cada celula, nao onde as celulas estao.

    Deixar cada chapa achar a sua grade sozinha era jogar fora essa
    informacao, e o preco apareceu nos Canticos: a chapa 1 saiu 4x2,
    certa e conferida pela regra da soma, e as chapas 2 e 3 sairam 2x2 e
    3x2 porque tinham menos tinta e casaram pior. Agora a grade e
    escolhida na chapa que reconheceu MELHOR, e aplicada em todas.
    """
    import pypdf
    total = len(pypdf.PdfReader(montagem).pages)

    pag_arte = pypdf.PdfReader(arte).pages[0]
    cx = pag_arte.trimbox or pag_arte.mediabox
    pl, pa = float(cx.width) / MM, float(cx.height) / MM
    fichas = assinaturas_da_arte(arte, limite_paginas, px_mm)

    # 1. quem reconhece melhor manda na grade
    imagens, achados = {}, []
    for n in range(1, total + 1):
        img = renderizar(montagem, n, px_mm)
        imagens[n] = img
        r = _melhor_grade(img, pl, pa, px_mm, fichas)
        if r and r["repetidas"] == 0:
            achados.append((r["diferenca_media"], -r["celas"], n, r))
    if not achados:
        return None
    achados.sort(key=lambda x: (x[1], x[0]))     # mais celulas, melhor media
    _d, _c, dona, base = achados[0]
    nc, nr = base["grade"]

    # 2. AS MESMAS CELULAS, NO MESMO LUGAR.
    #
    # Nao basta repetir a GRADE: tem de repetir a POSICAO. Assentar a
    # grade na mancha de cada chapa parece igual e nao e - uma chapa em
    # que a peca do canto tem muito branco tem a mancha menor, a grade
    # se assenta deslocada e todas as celulas pegam meia peca. Foi o que
    # aconteceu nos Canticos: com a grade certa e o assentamento por
    # chapa, as chapas 2 e 3 responderam 'pagina 20' seis vezes.
    #
    # As chapas de um trabalho tem a montagem NO MESMO LUGAR - e por
    # isso que elas se imprimem uma sobre a outra em registro.
    caixas = [(c["mm"][0] * px_mm, c["mm"][1] * px_mm,
               c["mm"][2] * px_mm, c["mm"][3] * px_mm)
              for c in base["celulas"]]

    chapas = []
    for n in range(1, total + 1):
        img = imagens[n]
        if img.size != imagens[dona].size:
            # chapa de tamanho diferente (a capa costuma ser assim) -
            # esta grade nao vale para ela, e dizer isso e melhor que
            # devolver numero
            chapas.append({"chapa": n, "celulas": [], "outra_medida": True,
                           "diferenca_media": None, "grade_daqui": False})
            continue
        cel = []
        for i, (x, y, w, h) in enumerate(caixas):
            a = assinatura(img, (int(x), int(y), int(x + w), int(y + h)))
            escolha = (None, None, 1e9)
            if a is not None:
                for pag, voltas in fichas.items():
                    for g, dados in voltas.items():
                        d = _diferenca(a, dados)
                        if d < escolha[2]:
                            escolha = (pag, g, d)
            cel.append({"coluna": i % nc + 1, "linha": i // nc + 1,
                        "pagina": escolha[0], "giro": escolha[1],
                        "diferenca": round(escolha[2], 1),
                        "mm": (round(x / px_mm, 1), round(y / px_mm, 1),
                               round(w / px_mm, 1), round(h / px_mm, 1))})
        difs = [c["diferenca"] for c in cel] if cel else [99]
        chapas.append({"chapa": n, "celulas": cel,
                       "diferenca_media": round(sum(difs) / len(difs), 1),
                       "grade_daqui": n == dona})
    return {"grade": (nc, nr), "peca": (round(pl, 1), round(pa, 1)),
            "paginas_da_arte": len(fichas), "chapas": chapas,
            "grade_veio_da_chapa": dona}


def _conferir(r):
    r"""
    Diz se a leitura fecha - e e isto que a separa de um chute bonito.

    DUAS CONFERENCIAS, e as duas sao de ofício, nao de programa:

    1. CADA PAGINA UMA VEZ. Juntando todas as celulas de todas as
       chapas, tem de sair 1..N sem repetir. Pagina faltando com outra
       repetida e uma celula lida errado, e o par diz qual.

    2. A SOMA DA CANOA. Num par lado a lado da mesma face, as duas
       paginas somam P+1 - a regra vale para o livro grampeado inteiro.
       Foi ela que provou, nos Canticos, que a leitura da chapa 1 estava
       certa antes de eu ter qualquer outra evidencia.

    Achar o erro e melhor que nao te-lo: uma celula errada no meio de
    vinte e quatro e conserto de dez segundos, e sem a conferencia ela
    passaria por leitura boa.
    """
    todas = [c["pagina"] for ch in r["chapas"] for c in ch["celulas"]
             if c["pagina"]]
    n = r["paginas_da_arte"]
    print()
    print("CONFERENCIA")
    faltam = sorted(set(range(1, n + 1)) - set(todas))
    repetidas = sorted(set(p for p in todas if todas.count(p) > 1))
    if not faltam and not repetidas and len(todas) == n:
        print("   cada pagina uma vez: 1..%d, fecha" % n)
    else:
        print("   paginas lidas %d de %d" % (len(set(todas)), n))
        if faltam:
            print("   FALTAM: %s" % faltam)
        if repetidas:
            print("   REPETIDAS: %s" % repetidas)
        print("   (falta + repete = celula lida errado, e o par diz qual)")

    nc = r["grade"][0]
    if nc % 2 == 0:
        erros = []
        for ch in r["chapas"]:
            ps = [c["pagina"] for c in ch["celulas"]]
            for i in range(0, len(ps), 2):
                if i + 1 < len(ps) and ps[i] and ps[i + 1]:
                    if ps[i] + ps[i + 1] != n + 1:
                        erros.append((ch["chapa"], ps[i], ps[i + 1]))
        if not erros:
            print("   soma da canoa: todo par da %d, fecha" % (n + 1))
        else:
            print("   soma da canoa (devia dar %d):" % (n + 1))
            for chapa, a, b in erros:
                print("      chapa %d: %s + %s = %s" % (chapa, a, b, a + b))


def principal():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__.strip().splitlines()[-3].strip())
    arte, montagem = args[0], args[1]
    pagina = 1
    if "--pagina" in sys.argv:
        pagina = int(sys.argv[sys.argv.index("--pagina") + 1])
    limite = None
    if "--ate" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--ate") + 1])

    if "--todas" in sys.argv:
        r = ler_o_trabalho(arte, montagem, limite_paginas=limite)
        if not r:
            raise SystemExit("nao consegui reconhecer grade nenhuma")
        print("arte      %s  (%d paginas)"
              % (os.path.basename(arte), r["paginas_da_arte"]))
        print("montagem  %s" % os.path.basename(montagem))
        print("peca      %g x %g mm" % r["peca"])
        print("grade     %d x %d  (lida na chapa %d)"
              % (r["grade"][0], r["grade"][1], r["grade_veio_da_chapa"]))
        for ch in r["chapas"]:
            paginas = [c["pagina"] for c in ch["celulas"]]
            nc = r["grade"][0]
            linhas = [paginas[i:i + nc] for i in range(0, len(paginas), nc)]
            print()
            print("  chapa %d   diferenca media %.1f%s"
                  % (ch["chapa"], ch["diferenca_media"] or 0,
                     "   <- a grade veio daqui" if ch["grade_daqui"]
                     else ("   (outra medida - grade nao vale)"
                           if ch.get("outra_medida") else "")))
            for li in linhas:
                print("     " + "  ".join("%4s" % p for p in li))
        _conferir(r)
        return

    r = ler(arte, montagem, pagina, limite_paginas=limite)
    print("arte      %s" % os.path.basename(arte))
    print("montagem  %s, pagina %d" % (os.path.basename(montagem), pagina))
    print("chapa     %g x %g mm     peca %g x %g mm"
          % (r["chapa"][0], r["chapa"][1], r["peca"][0], r["peca"][1]))
    print("grade     %d colunas x %d linhas" % r["grade"])
    print()
    print("   col linha   pagina  giro   dif   x,y,larg,alt (mm)")
    for c in r["celulas"]:
        print("   %3d %5d   %6s  %4s  %5.1f   %s"
              % (c["coluna"], c["linha"], c["pagina"], c["giro"],
                 c["diferenca"], c["mm"]))


if __name__ == "__main__":
    principal()
