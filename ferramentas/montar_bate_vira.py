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


# AS TRES MAQUINAS DA AMERICA, com as pincas da lista que o operador
# mantem - ver chapas-e-pincas.md na skill de imposicao. A pinca e da
# MAQUINA, nao do formato: seis graficas usam a mesma 525x459, cada uma
# com a sua.
def _chapas_da_america():
    from finart_ctp.config import CHAPAS_AMERICA
    return {apelido: Chapa(float(l), float(a), pinca)
            for (l, a), (pinca, apelido) in CHAPAS_AMERICA.items()}


AMERICA = _chapas_da_america()
PM52 = AMERICA["PM_52"]            # 525 x 459, pinca 60
MOZP = AMERICA["MOZP_FT2"]         # 650 x 550, pinca 60
SM74 = AMERICA["SM_74"]            # 745 x 605, pinca 62


def chapa_para(maior_lado, tintas):
    """
    A chapa da AMERICA que recebe um trabalho deste tamanho e desta cor.

    Regra do operador: ate o formato 4 vai na PM_52; acima dele, colorido
    na SM_74 e preto-e-branco na MOZP. A conta mora em america.py, para
    a montagem e o fechamento escolherem pela MESMA regra.
    """
    from finart_ctp.america import maquina_da_america
    medida = maquina_da_america(maior_lado, tintas)
    for chapa in AMERICA.values():
        if (int(chapa.larg), int(chapa.alt)) == medida:
            return chapa
    raise SystemExit("nao achei chapa da AMERICA para %s" % (medida,))


VAO = 5.0            # entre uma peca e a vizinha, de corte a corte
SANGRIA = 3.0        # o padrao da casa, medido em 2020 modelos do Preps
MARCA_COMP = 12.0    # comprimento da marca de corte
MARCA_FOLGA = 3.0    # a marca comeca onde a sangria acaba
MARCA_FIO = 0.5      # em PONTOS, como o operador pediu
ENCOSTO = 1.0          # marca de REGISTRO: quase encostada na sangria
ENCOSTO_ESCALA = 3.0   # a ESCALA DE COR fica um pouco mais afastada


def _mult(m, n):
    """Compoe duas matrizes de transformacao do PDF."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a*A + b*C, a*B + b*D, c*A + d*C,
            c*B + d*D, e*A + f*C + E, e*B + f*D + F)


def _aplicar(m, x, y):
    a, b, c, d, e, f = m
    return a*x + c*y + e, b*x + d*y + f


class _OlharDentroDoCorte(object):
    """
    Procura TEXTO ou VETOR dentro da area de corte da pagina.

    So conta o que esta DENTRO DO CORTE. Regra do operador, 10/09/2026:
    "eu digo a parte de dentro dos cortes, sem considerar as marcas de
    corte, que geralmente nao ficam em imagem".

    E ele tem razao: quase todo PDF fechado por designer traz as marcas
    de corte dele em vetor, fora do corte. Contar essas marcas faria todo
    arquivo parecer "tem vetor" e a regra do dpi nunca pegaria. No flyer
    15x21 sao tracos de 0,25 pt numa separacao chamada 'All'.
    """

    def __init__(self, leitor, corte, folga=1.5):
        self.leitor = leitor
        # encolhe o corte um tiquinho: objeto que so encosta na linha de
        # corte por fora (a propria marca) nao conta como estando dentro
        self.corte = (corte[0] + folga, corte[1] + folga,
                      corte[2] - folga, corte[3] - folga)
        self.texto = 0
        self.vetor = 0

    def dentro(self, x, y):
        e, b, d, c = self.corte
        return e <= x <= d and b <= y <= c

    def pagina(self, pag):
        from pypdf.generic import ContentStream
        rec = pag.get("/Resources")
        self.andar(ContentStream(pag.get_contents(), self.leitor).operations,
                   rec.get_object() if rec else {}, (1, 0, 0, 1, 0, 0), 0)

    def andar(self, operacoes, recursos, ctm, fundo):
        if fundo > 8:
            return
        pilha = []
        texto_ctm = None
        for operandos, op in operacoes:
            try:
                if op == b"q":
                    pilha.append(ctm)
                elif op == b"Q":
                    if pilha:
                        ctm = pilha.pop()
                elif op == b"cm":
                    ctm = _mult(tuple(float(v) for v in operandos[:6]), ctm)
                elif op == b"BT":
                    texto_ctm = (1, 0, 0, 1, 0, 0)
                elif op == b"ET":
                    texto_ctm = None
                elif op == b"Tm" and texto_ctm is not None:
                    texto_ctm = tuple(float(v) for v in operandos[:6])
                elif op in (b"Tj", b"TJ") and texto_ctm is not None:
                    x, y = _aplicar(_mult(texto_ctm, ctm), 0, 0)
                    if self.dentro(x, y):
                        self.texto += 1
                elif op in (b"m", b"l"):
                    x, y = _aplicar(ctm, float(operandos[0]),
                                    float(operandos[1]))
                    if self.dentro(x, y):
                        self.vetor += 1
                elif op == b"re":
                    x, y = _aplicar(ctm, float(operandos[0]),
                                    float(operandos[1]))
                    if self.dentro(x, y):
                        self.vetor += 1
                elif op in (b"c", b"v", b"y"):
                    for i in range(0, len(operandos) - 1, 2):
                        x, y = _aplicar(ctm, float(operandos[i]),
                                        float(operandos[i+1]))
                        if self.dentro(x, y):
                            self.vetor += 1
                            break
                elif op == b"Do":
                    self.entrar(operandos[0], recursos, ctm, fundo)
            except (TypeError, ValueError, IndexError, KeyError):
                continue

    def entrar(self, nome, recursos, ctm, fundo):
        from pypdf.generic import ContentStream
        xo = recursos.get("/XObject")
        if not xo:
            return
        xo = xo.get_object()
        if nome not in xo:
            return
        o = xo[nome].get_object()
        if o.get("/Subtype") != "/Form":
            return          # imagem: e justamente o que pode ficar
        proprio = o.get("/Matrix")
        if proprio:
            ctm = _mult(tuple(float(v) for v in proprio), ctm)
        dentro = o.get("/Resources")
        self.andar(ContentStream(o, self.leitor).operations,
                   dentro.get_object() if dentro else recursos,
                   ctm, fundo + 1)


def resolucao_do_arquivo(origem):
    """
    (todo_em_imagem, dpi_maior, dpi_menor) do PDF.

    'todo em imagem' quer dizer que DENTRO DO CORTE nao ha texto nem
    vetor - so imagem colada. Ai rasterizar acima do que o arquivo ja tem
    nao acrescenta detalhe nenhum, so peso, e mantem-se o dpi de origem.

    Usa-se o MAIOR dpi encontrado, nao o menor: no flyer 15x21 a maioria
    das imagens estava em 288 e algumas em 426 - sair em 288 amassaria
    essas.

    Havendo texto ou vetor dentro do corte, a resolucao do arquivo nao
    quer dizer nada (texto e vetor nao tem resolucao) e quem chamou
    escolhe pelo TAMANHO DA CHAPA - ver dpi_da_chapa().
    """
    import pypdf
    from finart_ctp.preflight import _Percorrer

    leitor = pypdf.PdfReader(origem)
    dpis = []
    limpo = True
    for pag in leitor.pages:
        andar = _Percorrer(leitor)
        try:
            andar.pagina(pag)
        except Exception:
            pass
        for _, pxl, pxa, ptl, pta in andar.imagens:
            if ptl > 0 and pta > 0:
                dpis.append(pxl / (ptl / 72.0))
                dpis.append(pxa / (pta / 72.0))
        caixa = pag.trimbox or pag.cropbox
        olho = _OlharDentroDoCorte(
            leitor, (float(caixa.left), float(caixa.bottom),
                     float(caixa.right), float(caixa.top)))
        try:
            olho.pagina(pag)
        except Exception:
            pass
        if olho.texto or olho.vetor:
            limpo = False

    if not dpis:
        return False, None, None
    return limpo, max(dpis), min(dpis)


from finart_ctp.config import MAIOR_LADO_F4       # noqa: E402


def dpi_da_chapa(chapa):
    """
    A resolucao de quem TEM texto ou vetor, pelo tamanho da chapa.

    Regra do operador: 900 dpi ate o formato 4, 800 acima disso. Chapa
    maior em 900 dpi daria arquivo grande demais sem ninguem ver
    diferenca - o mesmo raciocinio que ja existe no config.py, onde a
    510x400 grava em 1000 e a 775x635 em 800.
    """
    return 900 if max(chapa.larg, chapa.alt) <= MAIOR_LADO_F4 else 800



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

    recusadas = []

    def traco(x1, y1, x2, y2):
        """
        Um traco de marca - a menos que ele caia FORA DA CHAPA.

        AS MARCAS DE BAIXO SAEM, mesmo caindo dentro da faixa da pinca.

        Eu tinha feito o contrario, recusando-as por achar que ali nada
        imprime, e o operador corrigiu em 10/09/2026: "percebi que na
        parte de baixo da montagem a cruz de corte na vertical nao saiu,
        elas tem que sair, mas a pinca e realmente calculada pela
        horizontal".

        Ou seja: a medida da pinca continua sendo ate a linha de corte
        HORIZONTAL de baixo - isso nao mudou -, mas as marcas verticais
        que descem dali sao desenhadas do mesmo jeito. Quem grava a chapa
        grava a faixa inteira; e a marca de corte serve ao cortador, que
        precisa dela nas duas pontas da linha.

        O unico motivo para recusar e a marca cair fora da chapa: ali ela
        nao existiria de qualquer forma.
        """
        fora = (min(x1, x2) < 0 or min(y1, y2) < 0
                or max(x1, x2) > chapa.larg or max(y1, y2) > chapa.alt)
        if fora:
            recusadas.append((x1, y1))
            return
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
    return destino, recusadas


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


DPI_QUANDO_HA_TEXTO = 900       # so vale para arquivo com texto/vetor


def montar(origem, destino, chapa=PM52, dpi=None, tmp=None):
    """
    Monta as quatro pecas na chapa e grava o PDF.

    dpi=None (o normal) deixa o programa decidir: arquivo todo em
    imagem mantem a resolucao que ja tem; com texto ou vetor, vai em
    DPI_QUANDO_HA_TEXTO.
    """
    tmp = tmp or os.path.join(os.environ.get("TEMP", "."), "imposicao")
    os.makedirs(tmp, exist_ok=True)

    todo_imagem, maior, menor = resolucao_do_arquivo(origem)
    if dpi is None:
        dpi = (int(round(maior)) if todo_imagem and maior
               else dpi_da_chapa(chapa))

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

    # A PINCA SE MEDE DA MARCA DE CORTE, e a marca de corte de baixo e a
    # PRIMEIRA LINHA DE CORTE da montagem - nao a borda da sangria, nem o
    # comeco da tinta. Regra do operador, 10/09/2026: "a borda de baixo
    # do pdf, voce ajusta a pinca a partir da marca de corte, horizontal".
    #
    # E a mesma licao que a CREATIVE ja tinha ensinado, e que custou uma
    # chapa 12 mm fora do lugar: pinca nao se mede da borda do arquivo.
    #
    # Entao a borda de baixo do PDF e a borda da PINCA, e o primeiro
    # corte cai exatamente em chapa.pinca.
    y0 = chapa.pinca

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
    caminho_marcas, recusadas = marcas_em_pdf(
        linhas_v, linhas_h, caixa, chapa, os.path.join(tmp, "_m.pdf"))
    marcas = pypdf.PdfReader(caminho_marcas).pages[0]
    base.merge_page(marcas)

    # --- registro: nas duas pontas do lado MAIOR, centrado ---
    #
    # ENCOSTADO NA SANGRIA, nao depois das marcas. Pedido do operador em
    # 10/09/2026: "pode comecar logo apos a sangria da imagem acabar,
    # 1 mm separado, quase encostado mesmo". Quanto mais perto da arte,
    # menos papel a folha precisa ter de sobra em volta.
    # EM PE, DOS DOIS LADOS, a 1 mm da sangria.
    #
    # Cheguei a deixar deitado e so a esquerda, por ler errado um pedido
    # do operador - ele falava da ESCALA DE COR e eu entendi marca de
    # registro. Ele desfez: "a marca de registro esta perfeito do jeito
    # que tinha colocado a vez anterior". Dois lados importam: com um so,
    # da para ver desencontro de tinta, mas nao da para ver ESQUADRO -
    # a folha entrando torta desloca um lado para um jeito e o outro para
    # o contrario, e isso so aparece comparando as duas pontas.
    reg_eps = os.path.join(MARCAS_PREPS, "Registro 90°.eps")
    if not os.path.exists(reg_eps):
        reg_eps = os.path.join(MARCAS_PREPS, "2 Registro.eps")
    if os.path.exists(reg_eps):
        reg = pypdf.PdfReader(
            eps_em_pdf(reg_eps, os.path.join(tmp, "_r.pdf"))).pages[0]
        rl = float(reg.mediabox.width) / MM
        ra = float(reg.mediabox.height) / MM
        meio = y0 + montagem_a / 2.0 - ra / 2.0
        borda = SANGRIA + ENCOSTO
        por(base, reg, 0, x0 - borda - rl, meio)
        por(base, reg, 0, x0 + montagem_l + borda, meio)

    # --- escala de cor: DE PE, no lado esquerdo, em cima ---
    #
    # Girada 90 graus e encostada na lateral esquerda, a 3 mm da sangria,
    # pendurada a partir do alto da montagem. Pedido do operador em
    # 10/09/2026 - antes ela ficava deitada ACIMA da montagem, e ali
    # comia altura de chapa que a arte pode querer.
    #
    # O topo desce MARCA_FOLGA para nao encostar na marca de corte de
    # cima, que passa nessa mesma faixa. Abaixo dela nao ha marca nenhuma
    # ate a metade da chapa, entao a barra fica limpa.
    cor_eps = os.path.join(MARCAS_PREPS, "cores finart.eps")
    if os.path.exists(cor_eps):
        cor = pypdf.PdfReader(
            eps_em_pdf(cor_eps, os.path.join(tmp, "_c.pdf"))).pages[0]
        cl = float(cor.mediabox.width) / MM      # deitada: o comprimento
        ca = float(cor.mediabox.height) / MM     # deitada: a espessura
        topo = y0 + montagem_a - MARCA_FOLGA
        por(base, cor, 90, x0 - (SANGRIA + ENCOSTO_ESCALA) - ca, topo - cl)

    saida = pypdf.PdfWriter()
    saida.add_page(base)
    with io.open(destino, "wb") as f:
        saida.write(f)

    return {
        "todo_imagem": todo_imagem, "dpi_maior": maior, "dpi_menor": menor,
        "marcas_recusadas": len(recusadas),
        "chapa": (chapa.larg, chapa.alt), "pinca": chapa.pinca,
        "corte_da_peca": (corte_l, corte_a), "deitada": (dl, da),
        "montagem": (montagem_l, montagem_a),
        "canto": (x0, y0), "colunas": xs, "linhas": ys,
        "sangria": SANGRIA, "vao": VAO, "dpi": dpi,
    }


def nome_da_montagem(origem):
    """
    O nome que a montagem tem de ter: o mesmo do arquivo, mais _MONTAGEM.

    Regra da casa, e ela ja existia antes de mim - a pasta da AMERICA de
    10/09/2026 traz 'CRISTAOS.pdf' ao lado de 'CRISTAOS_MONTAGEM.cdr', e
    as OS do GEREMPRE guardam titulos como 'SANTINHO LUIS E LULA_MONTAGEM'.
    E SUFIXO, no fim do nome, e nao prefixo.

    O nome de origem vai INTEIRO, sem limpeza: e ele que amarra a
    montagem ao arquivo que a gerou, e quem procura procura por ele.
    """
    base, ext = os.path.splitext(os.path.basename(origem))
    return "%s_MONTAGEM%s" % (base, ext or ".pdf")


if __name__ == "__main__":
    origem = sys.argv[1]
    destino = (sys.argv[2] if len(sys.argv) > 2
               else os.path.join(os.path.dirname(origem) or ".",
                                 nome_da_montagem(origem)))
    d = montar(origem, destino)
    print("chapa            %.0f x %.0f mm, pinca %.0f" %
          (d["chapa"][0], d["chapa"][1], d["pinca"]))
    print("peca (corte)     %.2f x %.2f mm  ->  deitada %.2f x %.2f"
          % (d["corte_da_peca"] + d["deitada"]))
    print("montagem         %.2f x %.2f mm (corte a corte)" % d["montagem"])
    print("canto inferior   x %.2f   y %.2f" % d["canto"])
    print("colunas em x     %s" % ["%.2f" % v for v in d["colunas"]])
    print("linhas em y      %s" % ["%.2f" % v for v in d["linhas"]])
    print("sangria %.1f   vao %.1f" % (d["sangria"], d["vao"]))
    if d["todo_imagem"]:
        print("arquivo TODO EM IMAGEM (%.0f a %.0f dpi) - mantido em %d dpi,"
              % (d["dpi_menor"], d["dpi_maior"], d["dpi"]))
        print("   que e a resolucao que ele ja tinha. Subir nao criaria")
        print("   detalhe, so peso.")
    else:
        print("o arquivo tem texto ou vetor - rasterizado em %d dpi" % d["dpi"])
    if d["marcas_recusadas"]:
        print()
        print("AVISO: %d marca(s) cairiam FORA da chapa e nao foram"
              % d["marcas_recusadas"])
        print("   desenhadas. Confira o tamanho da montagem.")
    print()
    print("gerado: %s" % destino)
