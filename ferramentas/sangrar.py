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

O QUE SE FAZ, e depende do que ha NA BORDA:

  branco    a arte acaba em branco. Nao ha o que sangrar - o papel ja e
            branco. Enche de branco e pronto;
  chapado   a borda e uma cor so, parada. Estende a cor para fora. O
            resultado e EXATO: ninguem distingue do original;
  espelho   a borda tem foto ou textura que continua. Espelha a faixa
            para fora. E invencao, mas plausivel: a continuacao de uma
            textura e mais textura;
  OLHO      ha um traco, uma moldura ou uma letra PARADA na linha de
            corte. Espelhar duplicaria o traco, e a duplicata apareceria
            no impresso. Isto nao se resolve por conta: ou volta para o
            designer, ou alguem decide a mao.

A conferencia roda POR BORDA - uma arte pode ter as quatro diferentes.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finart_ctp.ghostscript import GS                      # noqa: E402

MM = 25.4

# Quanto a cor pode variar dentro da faixa e ainda contar como "chapado".
# 0-255 por canal; 3 e o ruido de compressao de um JPEG bom.
LIMIAR_CHAPADO = 3.0

# Acima disto (0-255) ha um traco atravessado na faixa da sangria, e
# espelhar duplicaria ele. Medido como a MAIOR mudanca de uma linha para
# a seguinte, andando de fora para dentro.
LIMIAR_TRACO = 34.0

# Perto disto a arte acaba em branco e nao ha o que sangrar.
LIMIAR_BRANCO = 247.0


def rasterizar(pdf, pagina, dpi, caixa="TrimBox"):
    """A pagina, na caixa pedida, como imagem RGB do Pillow."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    import tempfile
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
        return im.crop((0, 0, fundo, A)).transpose(5)         # ROTATE_270 -> linha 0 na borda
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


def sangrar_imagem(im, sangria_px, decisoes):
    """A imagem com a sangria acrescentada POR FORA. Nada e esticado."""
    from PIL import Image
    L, A = im.size
    s = sangria_px
    nova = Image.new("RGB", (L + 2 * s, A + 2 * s), "white")
    nova.paste(im, (s, s))

    def encher(borda, tecnica):
        if tecnica == "branco":
            return                      # a tela ja nasceu branca
        if borda in ("topo", "base"):
            tira = (im.crop((0, 0, L, s)) if borda == "topo"
                    else im.crop((0, A - s, L, A)))
            if tecnica == "chapado":
                linha = (im.crop((0, 0, L, 1)) if borda == "topo"
                         else im.crop((0, A - 1, L, A)))
                tira = linha.resize((L, s), Image.NEAREST)
            else:
                tira = tira.transpose(1)                 # FLIP_TOP_BOTTOM
            nova.paste(tira, (s, 0 if borda == "topo" else s + A))
        else:
            tira = (im.crop((0, 0, s, A)) if borda == "esquerda"
                    else im.crop((L - s, 0, L, A)))
            if tecnica == "chapado":
                col = (im.crop((0, 0, 1, A)) if borda == "esquerda"
                       else im.crop((L - 1, 0, L, A)))
                tira = col.resize((s, A), Image.NEAREST)
            else:
                tira = tira.transpose(0)                 # FLIP_LEFT_RIGHT
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


def sangrar(pdf, destino, sangria_mm=3.0, dpi=300, pagina=1):
    """
    Acrescenta sangria e grava um PDF. Devolve o relato por borda.

    O PDF de saida mede CORTE + 2 x sangria, e o corte continua do
    tamanho que era: o que cresceu foi so o que sobra para a guilhotina
    comer.
    """
    from PIL import Image
    im = rasterizar(pdf, pagina, dpi, "TrimBox")
    s = int(round(sangria_mm / MM * dpi))

    decisoes = {b: decidir(im, b, s)
                for b in ("topo", "base", "esquerda", "direita")}
    nova = sangrar_imagem(im, s, decisoes)
    nova.save(destino, "PDF", resolution=dpi)

    return {"decisoes": decisoes, "sangria_px": s,
            "corte_mm": (im.size[0] / dpi * MM, im.size[1] / dpi * MM),
            "com_sangria_mm": (nova.size[0] / dpi * MM,
                               nova.size[1] / dpi * MM),
            "precisa_de_olho": [b for b, (t, _) in decisoes.items()
                                if t == "olho"]}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("uso: sangrar.py <arquivo.pdf> [sangria_mm] [dpi]")
    origem = sys.argv[1]
    mm_ = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    dpi_ = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    destino = os.path.splitext(origem)[0] + "_SANGRADO.pdf"

    r = sangrar(origem, destino, mm_, dpi_)
    print("corte        %.2f x %.2f mm" % r["corte_mm"])
    print("com sangria  %.2f x %.2f mm  (+%.1f de cada lado)"
          % (r["com_sangria_mm"][0], r["com_sangria_mm"][1], mm_))
    print()
    for borda, (tecnica, porque) in r["decisoes"].items():
        marca = ">>>" if tecnica == "olho" else "   "
        print("%s %-9s %-8s %s" % (marca, borda, tecnica, porque))
    if r["precisa_de_olho"]:
        print()
        print("PARA: %s precisa(m) de gente. Nao invento traco."
              % ", ".join(r["precisa_de_olho"]))
    print()
    print("gerado: %s" % destino)
