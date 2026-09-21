# -*- coding: utf-8 -*-
r"""
As LINHAS DE CORTE de uma montagem, lidas nas MARCAS. NAO ESCREVE NADA.

A marca de corte e um traco curto na margem, exatamente na linha em que
a guilhotina corta. Ela e a medida mais precisa que existe numa
montagem, e por um motivo simples: ela NAO E a arte. Nao depende de a
pagina ter margem branca, nem de sangria, nem de fundo chapado.

POR QUE ISTO SUBSTITUIU A MEDIDA POR TINTA. A primeira tentativa media
os vaos pela tinta da montagem - andava peca a peca e contava o branco.
Ela respondia, respondia com numeros convincentes, e estava ERRADA: nos
Canticos deu 'vao de 10 mm em todas as tres fronteiras'. As marcas de
corte do mesmo arquivo dizem 135 | 135 |5| 135 | 135 - duas fronteiras
com vao ZERO e uma com 5. A tinta mentia porque a pagina tem margem
branca e a conta nao tem como saber onde a margem acaba e o vao comeca.

    python ferramentas/ler_marcas_da_montagem.py <montagem.pdf>
    python ferramentas/ler_marcas_da_montagem.py <montagem.pdf> --pagina 3
"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from finart_ctp.ghostscript import GS                  # noqa: E402

# 8 px/mm (~203 dpi). A marca de corte tem 0,25 pt - a 4 px/mm ela some
# no arredondamento em algumas montagens.
PX = 8.0


def _pillow():
    from PIL import Image
    return Image


def renderizar(pdf, pagina, px_mm=PX):
    """A chapa inteira como imagem cinza - SEM recortar no corte."""
    Image = _pillow()
    if not GS:
        raise SystemExit("sem Ghostscript nao ha como olhar o arquivo")
    tmp = tempfile.mkdtemp(prefix="marcas_")
    saida = os.path.join(tmp, "p.png")
    # NAO se usa -dUseTrimBox aqui: as marcas moram FORA do corte, e
    # recortar no corte joga fora justamente o que se quer medir.
    subprocess.run(
        [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pnggray",
         "-r%d" % int(round(px_mm * 25.4)),
         "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-sOutputFile=" + saida, pdf], capture_output=True, timeout=900)
    if not os.path.exists(saida):
        raise SystemExit("o Ghostscript nao devolveu a pagina %d de %s"
                         % (pagina, os.path.basename(pdf)))
    return Image.open(saida).convert("L")


def _grupos(perfil, px_mm, corte=0.25):
    """[mm] do centro de cada mancha de tinta isolada neste perfil."""
    tinta = [255 - v for v in perfil]
    pico = max(tinta) if tinta else 0
    if pico <= 0:
        return []
    limite = pico * corte
    saida, ini = [], None
    for i, t in enumerate(tinta):
        if t > limite and ini is None:
            ini = i
        elif t <= limite and ini is not None:
            saida.append(round((ini + i - 1) / 2.0 / px_mm, 2))
            ini = None
    if ini is not None:
        saida.append(round((ini + len(tinta) - 1) / 2.0 / px_mm, 2))
    return saida


def _numa_fita(img, de_mm, ate_mm, eixo, px_mm):
    """Os grupos de tinta numa fita da margem."""
    Image = _pillow()
    larg, alt = img.size
    a, b = int(de_mm * px_mm), int(ate_mm * px_mm)
    if eixo == 0:
        if b > alt:
            return []
        fita = img.crop((0, a, larg, b))
        return _grupos(list(fita.resize((larg, 1), Image.BILINEAR).tobytes()),
                       px_mm)
    if b > larg:
        return []
    fita = img.crop((a, 0, b, alt))
    return _grupos(list(fita.resize((1, alt), Image.BILINEAR).tobytes()),
                   px_mm)


def linhas_de_corte(img, eixo, px_mm=PX):
    """
    [mm] das linhas de corte neste eixo, lidas na melhor fita da margem.

    A FITA SE PROCURA, e nao se adivinha: a marca fica a alguns
    milimetros da borda, mas quanto depende da montagem. Varre-se a
    margem dos dois lados e fica a fita que devolve mais linhas -
    margem sem marca devolve zero ou uma, e a com marcas devolve todas.
    """
    larg, alt = img.size[0] / px_mm, img.size[1] / px_mm
    fundo = alt if eixo == 0 else larg
    melhor = []
    for base in (0.0, fundo - 14.0):
        for de in range(0, 12, 2):
            achado = _numa_fita(img, base + de, base + de + 6, eixo, px_mm)
            # ruido de arte devolve dezenas de grupos; marca de corte
            # devolve poucos e espacados
            if 2 <= len(achado) <= 24 and len(achado) > len(melhor):
                melhor = achado
    return melhor


def ler(pdf, pagina=1, px_mm=PX):
    """{'chapa', 'x', 'y', 'passos_x', 'passos_y'} de uma pagina."""
    img = renderizar(pdf, pagina, px_mm)
    xs = linhas_de_corte(img, 0, px_mm)
    ys = linhas_de_corte(img, 1, px_mm)
    passos = lambda v: [round(b - a, 1) for a, b in zip(v, v[1:])]
    return {"chapa": (round(img.size[0] / px_mm, 1),
                      round(img.size[1] / px_mm, 1)),
            "x": xs, "y": ys,
            "passos_x": passos(xs), "passos_y": passos(ys)}


def contar(passos, tolerancia=1.5):
    """
    (peca_mm, [vaos]) a partir dos passos entre linhas de corte.

    O passo GRANDE e a peca; os pequenos sao vao. Numa montagem de
    caderno a lista sai assim: [150, 150, 5, 150, 150] - quatro pecas
    encostadas duas a duas, com um vao de 5 entre os pares.
    """
    if not passos:
        return None, []
    peca = max(passos)
    vaos = [p for p in passos if p < peca - tolerancia]
    return peca, vaos


def principal():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(
            "uso: python ferramentas/ler_marcas_da_montagem.py <montagem.pdf>")
    pagina = 1
    if "--pagina" in sys.argv:
        pagina = int(sys.argv[sys.argv.index("--pagina") + 1])

    r = ler(args[0], pagina)
    print("%s  pagina %d" % (os.path.basename(args[0]), pagina))
    print("chapa     %g x %g mm" % r["chapa"])
    for eixo, nome in ((("x", "passos_x"), "colunas"),
                       (("y", "passos_y"), "linhas")):
        linhas, passos = r[eixo[0]], r[eixo[1]]
        peca, vaos = contar(passos)
        print()
        print("%s" % nome.upper())
        print("   linhas de corte: %s" % linhas)
        print("   passos         : %s" % passos)
        if peca:
            print("   peca %g mm     vaos %s"
                  % (peca, vaos if vaos else "nenhum (todas encostadas)"))


if __name__ == "__main__":
    principal()
