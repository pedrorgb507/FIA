# -*- coding: utf-8 -*-
r"""
Monta um bate-vira de 4 pecas (2 frente + 2 verso) numa chapa.

CABECA COM CABECA: as duas cabecas se encontram no vao do meio. Como as
pecas sao em pe (150 x 210) e as cabecas tem de se encontrar num vao
VERTICAL, cada uma gira 90 graus - a da esquerda no sentido do relogio
(cabeca para a direita), a da direita no contrario (cabeca para a
esquerda). Assim as duas cabecas apontam para o vao.

A folha vira sobre o eixo VERTICAL e a PINCA CONTINUA SENDO A MESMA
BORDA nas duas passadas - por isso a montagem se parte ao meio por uma
linha vertical, e por isso ela tem de ficar CENTRADA NA LARGURA.

O que este programa NAO faz, e de proposito:

  - nao mexe na cor da arte. O arquivo ja chega em CMYK e e rasterizado
    com -dUseFastColor, que le a tinta como esta escrita. Passar pelo
    perfil embutido remistura o preto nas quatro tintas (armadilha 1 da
    skill de cor);
  - nao inventa marca: usa os EPS da propria casa, da pasta Marks do
    Preps;
  - nao salva nada por cima do arquivo do cliente.

Medidas em MILIMETRO na configuracao; o PDF trabalha em ponto.
"""

import io
import os
import subprocess
import sys

import pypdf
from pypdf import PageObject, Transformation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from finart_ctp.ghostscript import GS                      # noqa: E402

MM = 72.0 / 25.4                       # milimetro -> ponto

MARCAS_PREPS = r"C:\Program Files (x86)\Creo\Preps 5.0\Marks"


class Chapa(object):
    """A chapa e o que cabe nela."""

    def __init__(self, larg, alt, pinca):
        self.larg = larg
        self.alt = alt
        self.pinca = pinca

    @property
    def util(self):
        """(largura, altura) do que se pode imprimir, tirada a pinca."""
        return self.larg, self.alt - self.pinca


# A chapa da AMERICA: Heidelberg Printmaster 52. Conferida em seis
# graficas da lista do operador, todas com 6 cm - ver a referencia
# chapas-e-pincas.md da skill de imposicao.
PM52 = Chapa(525.0, 459.0, 60.0)

VAO = 5.0            # entre uma peca e a vizinha, de corte a corte
SANGRIA = 3.0        # o padrao da casa, medido em 2020 modelos do Preps
MARCA_COMP = 12.0    # comprimento da marca de corte
MARCA_FOLGA = 3.0    # a marca comeca onde a sangria acaba
MARCA_FIO = 0.5      # em PONTOS, como o operador pediu


def _rodar(*args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[:400])


def peca_em_pdf(origem, pagina, dpi, destino):
    """
    Rasteriza UMA pagina no BleedBox e devolve um PDF de uma imagem so.

    E o 'converter em imagem' do operador: depois disto nao ha fonte,
    nem transparencia, nem vetor que possa dar pau no RIP - ha uma
    imagem CMYK e mais nada.
    """
    _rodar(GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
           "-sDEVICE=pdfimage32", "-r%d" % dpi,
           "-dUseBleedBox", "-dUseFastColor=true",
           "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
           "-sOutputFile=" + destino, origem)
    return destino


def eps_em_pdf(eps, destino):
    """Converte um EPS da biblioteca da casa, sem mexer na cor dele."""
    _rodar(GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
           "-sDEVICE=pdfwrite", "-dEPSCrop",
           "-dColorConversionStrategy=/LeaveColorUnchanged",
           "-sOutputFile=" + destino, eps)
    return destino


def marcas_em_pdf(linhas_v, linhas_h, caixa, chapa, destino):
    """
    Desenha as marcas de corte, em COR DE REGISTRO.

    Cor de registro e 100% das quatro tintas ao mesmo tempo - assim a
    marca sai em TODAS as chapas, no mesmo lugar. Se as quatro casarem,
    ela aparece como um traco preto limpo; se alguma sair do lugar, a
    marca mostra colorido na borda, e e por ela que o impressor enxerga
    o erro de registro. Escrever '0 0 0 1' (so preto) poria a marca em
    uma chapa so, e ela nao serviria para nada.

    As marcas ficam FORA da montagem: cada linha de corte ganha um traco
    em cada ponta. Dentro nao cabe - o vao tem 5 mm e esta cheio de
    sangria.
    """
    esq, baixo, dir_, cima = caixa
    ps = [
        "%!PS-Adobe-3.0",
        "<< /PageSize [%.4f %.4f] >> setpagedevice"
        % (chapa.larg * MM, chapa.alt * MM),
        "1 1 1 1 setcmykcolor",              # <- cor de registro
        "%.3f setlinewidth" % MARCA_FIO,
        "0 setlinecap",
    ]

    def traco(x1, y1, x2, y2):
        ps.append("newpath %.4f %.4f moveto %.4f %.4f lineto stroke"
                  % (x1 * MM, y1 * MM, x2 * MM, y2 * MM))

    for x in linhas_v:               # linhas de corte verticais
        traco(x, baixo - MARCA_FOLGA, x, baixo - MARCA_FOLGA - MARCA_COMP)
        traco(x, cima + MARCA_FOLGA, x, cima + MARCA_FOLGA + MARCA_COMP)
    for y in linhas_h:               # linhas de corte horizontais
        traco(esq - MARCA_FOLGA, y, esq - MARCA_FOLGA - MARCA_COMP, y)
        traco(dir_ + MARCA_FOLGA, y, dir_ + MARCA_FOLGA + MARCA_COMP, y)

    ps.append("showpage")
    caminho_ps = destino + ".ps"
    io.open(caminho_ps, "w", encoding="ascii").write("\n".join(ps) + "\n")
    _rodar(GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
           "-sDEVICE=pdfwrite",
           "-dColorConversionStrategy=/LeaveColorUnchanged",
           "-sOutputFile=" + destino, caminho_ps)
    os.remove(caminho_ps)
    return destino


def por(base, fonte, giro, x, y):
    """
    Poe 'fonte' na 'base' com giro de 0, 90 ou -90, no canto (x, y) em mm.

    (x, y) e o canto INFERIOR ESQUERDO de onde o retangulo girado vai
    ficar. O giro e em torno da origem, entao cada caso precisa de um
    empurrao diferente para voltar ao lugar - e por isso que isto e uma
    funcao, e nao tres linhas soltas espalhadas pelo programa.
    """
    L = float(fonte.mediabox.width)
    A = float(fonte.mediabox.height)
    t = Transformation().rotate(giro)
    if giro == 90:
        t = t.translate(A, 0)
    elif giro == -90:
        t = t.translate(0, L)
    elif giro == 180:
        t = t.translate(L, A)
    t = t.translate(x * MM, y * MM)
    base.merge_transformed_page(fonte, t)


def montar(origem, destino, chapa=PM52, dpi=900, tmp=None):
    """Monta as quatro pecas na chapa e grava o PDF."""
    tmp = tmp or os.path.join(os.environ.get("TEMP", "."), "imposicao")
    os.makedirs(tmp, exist_ok=True)

    # --- as duas pecas, ja em imagem ---
    frente = pypdf.PdfReader(
        peca_em_pdf(origem, 1, dpi, os.path.join(tmp, "_f.pdf"))).pages[0]
    verso = pypdf.PdfReader(
        peca_em_pdf(origem, 2, dpi, os.path.join(tmp, "_v.pdf"))).pages[0]

    # a peca chega com sangria: o CORTE esta para dentro dela
    sang_l = float(frente.mediabox.width) / MM
    sang_a = float(frente.mediabox.height) / MM
    corte_l = sang_l - 2 * SANGRIA
    corte_a = sang_a - 2 * SANGRIA

    # deitada, largura e altura trocam
    dl, da = corte_a, corte_l

    montagem_l = 2 * dl + VAO
    montagem_a = 2 * da + VAO
    util_l, util_a = chapa.util
    if montagem_l > util_l or montagem_a > util_a:
        raise SystemExit(
            "a montagem (%.1f x %.1f) nao cabe no util da chapa (%.1f x %.1f)"
            % (montagem_l, montagem_a, util_l, util_a))

    # CENTRADA NA LARGURA - exigencia do vira, nao gosto: o eixo do giro
    # e a linha vertical do meio, e ela tem de cair no meio da folha.
    x0 = (chapa.larg - montagem_l) / 2.0
    # na altura sobra escolha; fica centrada no que ha acima da pinca
    y0 = chapa.pinca + (util_a - montagem_a) / 2.0

    xs = [x0, x0 + dl + VAO]
    ys = [y0, y0 + da + VAO]

    base = PageObject.create_blank_page(
        width=chapa.larg * MM, height=chapa.alt * MM)

    # coluna da esquerda = FRENTE, cabeca para a DIREITA  -> gira -90
    # coluna da direita  = VERSO,  cabeca para a ESQUERDA -> gira +90
    for y in ys:
        por(base, frente, -90, xs[0] - SANGRIA, y - SANGRIA)
        por(base, verso, 90, xs[1] - SANGRIA, y - SANGRIA)

    # --- as marcas ---
    linhas_v = [xs[0], xs[0] + dl, xs[1], xs[1] + dl]
    linhas_h = [ys[0], ys[0] + da, ys[1], ys[1] + da]
    caixa = (x0, y0, x0 + montagem_l, y0 + montagem_a)
    marcas = pypdf.PdfReader(
        marcas_em_pdf(linhas_v, linhas_h, caixa, chapa,
                      os.path.join(tmp, "_m.pdf"))).pages[0]
    base.merge_page(marcas)

    # --- registro: nas duas pontas do lado MAIOR, centrado ---
    reg_eps = os.path.join(MARCAS_PREPS, "Registro 90\u00b0.eps")
    if not os.path.exists(reg_eps):
        reg_eps = os.path.join(MARCAS_PREPS, "2 Registro.eps")
    if os.path.exists(reg_eps):
        reg = pypdf.PdfReader(
            eps_em_pdf(reg_eps, os.path.join(tmp, "_r.pdf"))).pages[0]
        rl = float(reg.mediabox.width) / MM
        ra = float(reg.mediabox.height) / MM
        meio = y0 + montagem_a / 2.0 - ra / 2.0
        folga = MARCA_FOLGA + MARCA_COMP + 2.0
        por(base, reg, 0, x0 - folga - rl, meio)
        por(base, reg, 0, x0 + montagem_l + folga, meio)

    # --- escala de cor: canto superior esquerdo ---
    cor_eps = os.path.join(MARCAS_PREPS, "cores finart.eps")
    if os.path.exists(cor_eps):
        cor = pypdf.PdfReader(
            eps_em_pdf(cor_eps, os.path.join(tmp, "_c.pdf"))).pages[0]
        ca = float(cor.mediabox.height) / MM
        por(base, cor, 0, x0, y0 + montagem_a + MARCA_FOLGA + MARCA_COMP + 3.0)

    saida = pypdf.PdfWriter()
    saida.add_page(base)
    with io.open(destino, "wb") as f:
        saida.write(f)

    return {
        "chapa": (chapa.larg, chapa.alt), "pinca": chapa.pinca,
        "corte_da_peca": (corte_l, corte_a), "deitada": (dl, da),
        "montagem": (montagem_l, montagem_a),
        "canto": (x0, y0), "colunas": xs, "linhas": ys,
        "sangria": SANGRIA, "vao": VAO, "dpi": dpi,
    }


if __name__ == "__main__":
    origem = sys.argv[1]
    destino = sys.argv[2] if len(sys.argv) > 2 else "montagem.pdf"
    d = montar(origem, destino)
    print("chapa            %.0f x %.0f mm, pinca %.0f" %
          (d["chapa"][0], d["chapa"][1], d["pinca"]))
    print("peca (corte)     %.2f x %.2f mm  ->  deitada %.2f x %.2f"
          % (d["corte_da_peca"] + d["deitada"]))
    print("montagem         %.2f x %.2f mm (corte a corte)" % d["montagem"])
    print("canto inferior   x %.2f   y %.2f" % d["canto"])
    print("colunas em x     %s" % ["%.2f" % v for v in d["colunas"]])
    print("linhas em y      %s" % ["%.2f" % v for v in d["linhas"]])
    print("sangria %.1f   vao %.1f   %d dpi" %
          (d["sangria"], d["vao"], d["dpi"]))
    print()
    print("gerado: %s" % destino)
