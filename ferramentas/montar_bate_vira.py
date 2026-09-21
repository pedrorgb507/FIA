# -*- coding: utf-8 -*-
r"""
Monta uma grade de pecas numa chapa: bate-vira, ou so frente.

A GRADE E DE CELULAS, e cada celula guarda UMA peca DEITADA - cols x
rows, o vao entre elas, e a montagem centrada na largura. Ate
11/09/2026 isto era 2 x 2 e nada mais: um convite 100x210 pedindo SEIS
na 525x459 nao tinha por onde entrar. O numero de pecas agora vem de
fora, e a sangria vem dele (metade do vao).

BATE-VIRA, CABECA COM CABECA: as duas cabecas se encontram no vao do meio. Como as
pecas sao em pe (150 x 210) e as cabecas tem de se encontrar num vao
VERTICAL, cada uma gira 90 graus - a da esquerda no sentido do relogio
(cabeca para a direita), a da direita no contrario (cabeca para a
esquerda). Assim as duas cabecas apontam para o vao.

A folha vira sobre o eixo VERTICAL e a PINCA CONTINUA SENDO A MESMA
BORDA nas duas passadas - por isso a montagem se parte ao meio por uma
linha vertical, e por isso ela tem de ficar CENTRADA NA LARGURA.

O que este programa NAO faz, e de proposito:

  - nao mexe na cor da arte DE GRACA. Arte que chega em CMYK e lida com
    -dUseFastColor, que le a tinta como esta escrita - passar pelo
    perfil embutido remistura o preto nas quatro tintas (armadilha 1 da
    skill de cor). Mas arte que chega em RGB TEM de ser convertida, e
    ali a mesma flag zera o preto: ver arte_em_cmyk(), que escolhe;
  - nao inventa marca: usa os EPS da propria casa, da pasta Marks do
    Preps;
  - nao salva nada por cima do arquivo do cliente;
  - nao faz FRENTE E VERSO (duas chapas, uma por lado). A conta seria a
    mesma; o que falta e o nome de cada arquivo de saida, que e
    convencao da casa e eu nao invento.

Medidas em MILIMETRO na configuracao; o PDF trabalha em ponto.
"""

import io
import re
import os
import subprocess
import sys

import pypdf
from pypdf import PageObject, Transformation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sangrar.py
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
COLS, ROWS = 2, 2    # a grade PADRAO - o bate-vira de 4 que a casa ja fazia
PECAS = COLS * ROWS

# A SANGRIA NAO E UM NUMERO FIXO - e METADE DO VAO. Regra do operador,
# 11/09/2026. A guilhotina corta DUAS vezes no vao, uma na borda de cada
# peca, e a tira do meio e refugo; metade do vao e a maior sangria que
# cabe sem uma peca invadir a metade da outra.
#
# Ficava 3 fixo aqui, com vao 5. Isso NAO estragava o impresso - a
# sobreposicao de 1 mm caia toda no refugo - mas amarrava a sangria a um
# numero que ninguem lembraria de mudar junto com o vao.
# A conta mora em sangrar.regra_da_sangria, para a montagem e o painel
# usarem a MESMA.
MARCA_COMP = 12.0    # comprimento da marca de corte
# a folga da marca acompanha a sangria: a marca comeca onde a tinta
# acaba. Era 3 fixo, medido nos 2020 modelos do Preps - onde a sangria
# tambem era 3. Sao o mesmo numero, e continuam sendo.
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


def arte_em_cmyk(origem):
    """
    True se a arte JA esta em CMYK; False se ela chega em RGB.

    Quem decide isto e o espaco de cor do ARQUIVO, e a decisao troca o
    rasterizador inteiro. As duas metades sao verdadeiras e opostas:

      - arte em CMYK -> -dUseFastColor=true, que le a tinta como esta
        escrita. Passar pelo perfil embutido remistura o preto de K
        sozinho nas quatro tintas (armadilha 1 da skill de cor, e os
        numeros da PRIME no config.py);
      - arte em RGB  -> conversao GERENCIADA, sem a flag. Ali o
        -dUseFastColor faz o OPOSTO do que se quer: desliga o
        gerenciamento e cai na conta ingenua C=1-R, M=1-G, Y=1-B, que
        nao gera preto nenhum. Todo o escuro sai das tres tintas
        coloridas e o K fica em ZERO.

    Medido no 'IPO-563263 FOLDER -FLYER 148x210mm (1).pdf' da AMERICA,
    16/09/2026 - um PDF todo em ICCBased com /N 3, imagens JPX RGB:

        com a flag    C 0,9942  M 0,9945  Y 0,9949  K 0,0000
        gerenciado    C 0,9925  M 0,9945  Y 0,9948  K 0,8978   (pag 1)
                                                    K 0,4869   (pag 2)

    O operador montou o mesmo arquivo no CorelDRAW nesse dia, e essa
    chapa tem 68,9% de preto dentro da arte. O caminho gerenciado da
    69,2% - 0,3 ponto de diferenca. Com a flag dava 0%, e foi por isso
    que ele viu 'as cores mudaram completamente'.

    O criterio e: achou UMA tinta CMYK, e CMYK. Arte de verdade mistura
    (uma logomarca em Separation dentro de uma pagina RGB), e na duvida
    preservar a porcentagem escrita e o menor risco - e o lado em que
    ja se sabe o que acontece.
    """
    try:
        leitor = pypdf.PdfReader(origem)
    except Exception:
        return True                    # nao consegui ler: fico no antigo

    vistos = set()

    def olhar(obj, fundo=0):
        """Desce pelos espacos de cor. True assim que achar CMYK."""
        if fundo > 12 or obj is None:
            return False
        try:
            obj = obj.get_object()
        except Exception:
            return False
        ident = id(obj)
        if ident in vistos:
            return False
        vistos.add(ident)

        if isinstance(obj, str):
            return obj in ("/DeviceCMYK", "/DeviceN", "/Separation")
        if isinstance(obj, list):
            if obj and str(obj[0]) == "/ICCBased":
                try:
                    return int(obj[1].get_object().get("/N", 0)) == 4
                except Exception:
                    return False
            if obj and str(obj[0]) in ("/Separation", "/DeviceN"):
                return True            # tinta nomeada: chapa propria
            if obj and str(obj[0]) == "/Indexed" and len(obj) > 1:
                return olhar(obj[1], fundo + 1)
            return any(olhar(o, fundo + 1) for o in obj)
        if hasattr(obj, "get"):
            for chave in ("/ColorSpace", "/CS", "/XObject", "/Resources",
                          "/Group", "/Pattern", "/Shading"):
                if chave in obj and olhar(obj[chave], fundo + 1):
                    return True
            if str(obj.get("/Subtype")) == "/Image" and "/ColorSpace" in obj:
                return olhar(obj["/ColorSpace"], fundo + 1)
            for valor in obj.values():
                if olhar(valor, fundo + 1):
                    return True
        return False

    for pagina in leitor.pages:
        if olhar(pagina.get("/Resources"), 0):
            return True

    # E o FLUXO da propria pagina, que e onde mora a cor de quem desenha
    # em vetor: '0 0 0 0.5 k' nao declara /ColorSpace nenhum, e uma arte
    # inteira pode ser CMYK sem haver o que achar nos Resources. E o
    # mesmo tropeco do flyer 15x21, onde a varredura descia nos XObjects
    # e esquecia o fluxo da pagina - ao procurar coisa em PDF, olhe os
    # dois.
    for pagina in leitor.pages:
        try:
            fluxo = pagina.get_contents()
            dados = fluxo.get_data() if fluxo is not None else b""
        except Exception:
            continue
        if re.search(br"(?:^|[\s\]>])[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[kK]"
                     br"(?=[\s/\[<(]|$)", dados):
            return True
    return False


def tem_sobreposicao(pdf):
    """
    True se este PDF traz sobreposicao declarada - a nossa ou a de quem
    fechou o arquivo.

    Procura no arquivo cru de proposito: o '/OP true' pode estar num
    ExtGState da pagina, de um Form XObject ou de um recurso herdado, e
    andar por todos custaria mais do que ler os bytes.
    """
    try:
        with io.open(pdf, "rb") as f:
            dados = f.read()
    except Exception:
        return False
    return re.search(rb"/(OP|op)\s+true", dados) is not None


def peca_em_pdf(origem, pagina, dpi, destino, cmyk=None):
    """
    Rasteriza UMA pagina no BleedBox e devolve um PDF de uma imagem so.

    E o 'converter em imagem' do operador: depois disto nao ha fonte,
    nem transparencia, nem vetor que possa dar pau no RIP - ha uma
    imagem CMYK e mais nada.

    A SAIDA e sempre CMYK (pdfimage32). O que muda conforme a entrada e
    COMO se chega nela - ver arte_em_cmyk().
    """
    if cmyk is None:
        cmyk = arte_em_cmyk(origem)

    # A SOBREPOSICAO E O -dUseFastColor NAO CONVIVEM, e isto custou a
    # tarde de 18/09/2026 para descobrir. A flag desliga o pipeline de
    # cor, e com ele o Ghostscript ignora o overprint declarado no PDF -
    # o preto continua recortando o fundo, calado. Medido no 'Timbrado
    # Traumat', no mesmo arquivo e no mesmo comando:
    #
    #     com -dUseFastColor     C dentro do preto = 0     (recortou)
    #     sem ela, com Overprint C dentro do preto = 171   (sobrepos)
    #
    # Entao, quando o PDF traz sobreposicao declarada, a flag SAI e
    # entra o -sOverprint=simulate. O risco conhecido disso e a
    # armadilha 1 da skill de cor - o perfil embutido remisturando o
    # preto de K nas quatro tintas -, e por isso quem chama CONFERE
    # depois (ver conferir_a_cor_sobrevive). Medido neste arquivo, o
    # verde ficou C 171 M 0 Y 48 K 0 dos dois lados, ao ponto, e o preto
    # continuou com K 255.
    if tem_sobreposicao(origem):
        cor = ["-sOverprint=simulate"]
    else:
        cor = ["-dUseFastColor=true"] if cmyk else []

    _rodar(GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
           "-sDEVICE=pdfimage32", "-r%d" % dpi,
           "-dUseBleedBox", *cor,
           "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
           "-sOutputFile=" + destino, origem)
    return destino


def eps_em_pdf(eps, destino, so_preto=False):
    """
    Converte um EPS da biblioteca da casa.

    Normalmente sem mexer na cor dele - a marca de registro e a escala
    vem em cor de registro e assim devem ficar.

    Com so_preto, a cor e levada para CINZA. E o caso da AMERICA quando
    o trabalho e de uma cor no preto: regra do operador em 17/09/2026 -
    "corte, registro e escala de cor, mantem so o canal do preto, para
    dar saida somente em 1 chapa". Deixar em cor de registro poria C, M
    e Y na chapa e o trabalho contaria QUATRO, por causa das marcas.
    """
    cor = ("-dColorConversionStrategy=/Gray" if so_preto
           else "-dColorConversionStrategy=/LeaveColorUnchanged")
    _rodar(GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
           "-sDEVICE=pdfwrite", "-dEPSCrop", cor,
           "-sOutputFile=" + destino, eps)
    return destino


def marcas_em_pdf(linhas_v, linhas_h, caixa, chapa, destino, folga,
                  so_preto=False):
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
        # COR DE REGISTRO, menos quando o trabalho e de uma cor so.
        #
        # Com uma chapa, nao ha registro a conferir - e a marca em 1 1 1 1
        # poria C, M e Y na separacao, fazendo o trabalho contar QUATRO
        # chapas por causa das marcas. Regra do operador, 17/09/2026.
        ("0 0 0 1 setcmykcolor" if so_preto else "1 1 1 1 setcmykcolor"),
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
        traco(x, baixo - folga, x, baixo - folga - MARCA_COMP)
        traco(x, cima + folga, x, cima + folga + MARCA_COMP)
    for y in linhas_h:               # linhas de corte horizontais
        traco(esq - folga, y, esq - folga - MARCA_COMP, y)
        traco(dir_ + folga, y, dir_ + folga + MARCA_COMP, y)

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


def _pecas(origem, tipo="bate-vira"):
    """
    [(arquivo, pagina), ...] - o que vai nas celulas.

    Em 'so-frente' e UMA arte so, repetida. Em 'bate-vira' sao duas: a
    frente e o verso.

    Aceita as duas formas em que a frente e o verso chegam:

      um arquivo de duas paginas   'folder Credenciado Sesc 2026.pdf'
      DOIS arquivos de uma pagina  'CARTA_FRENTE_SETEMBRO.pdf' e
                                   'CARTA_VERSO_SETEMBRO_opcao_2.pdf'

    A segunda e a comum quando o cliente manda por e-mail, e ate
    11/09/2026 a montagem nao a aceitava: lia a pagina 2 de um arquivo
    que so tinha uma. Regra do operador no mesmo dia: "quando eu colocar
    dois arquivos la provavelmente sera frente e verso".

    A ORDEM MANDA: o primeiro e a frente, o segundo e o verso. Nao
    adivinho pelo nome - 'opcao_2' no nome do verso mostra que nome de
    arquivo de cliente nao e lugar de procurar regra.
    """
    if isinstance(origem, (list, tuple)):
        arquivos = list(origem)
    else:
        arquivos = [origem]

    # SO FRENTE: uma arte, repetida em todas as celulas. Nao ha verso
    # para procurar - e nao escolho pagina nem arquivo no lugar de
    # ninguem, porque escolher errado aqui nao da erro em lugar nenhum.
    if tipo == "so-frente":
        if len(arquivos) != 1:
            raise SystemExit(
                "'so frente' e UMA arte repetida: me passe UM arquivo - "
                "recebi %d." % len(arquivos))
        n = len(pypdf.PdfReader(arquivos[0]).pages)
        if n != 1:
            raise SystemExit(
                "'%s' tem %d paginas e em 'so frente' eu repito UMA arte. "
                "Nao sei qual das %d e a boa."
                % (os.path.basename(arquivos[0]), n, n))
        return [(arquivos[0], 1)]

    if len(arquivos) == 1:
        n = len(pypdf.PdfReader(arquivos[0]).pages)
        if n < 2:
            raise SystemExit(
                "'%s' tem %d pagina: para bate-vira preciso da frente E do "
                "verso. Passe os dois arquivos, ou um arquivo de duas "
                "paginas." % (os.path.basename(arquivos[0]), n))
        # MAIS DE DUAS EU NAO ESCOLHO, e ate 18/09/2026 eu escolhia: pegava
        # a 1 e a 2 e seguia calado, e as outras sumiam sem ninguem ver. E
        # o mesmo chute que o 'so frente' logo acima ja recusava - a
        # gravadora nao puxa multiplas paginas, e escolher pagina por
        # alguem e mandar para a chapa o que ninguem escolheu.
        if n > 2:
            raise SystemExit(
                "'%s' tem %d paginas e no bate-vira eu uso DUAS - a frente "
                "e o verso. Nao sei quais das %d sao. Separe as duas num "
                "arquivo, ou passe os dois arquivos."
                % (os.path.basename(arquivos[0]), n, n))
        return [(arquivos[0], 1), (arquivos[0], 2)]

    if len(arquivos) == 2:
        for f in arquivos:
            n = len(pypdf.PdfReader(f).pages)
            if n != 1:
                raise SystemExit(
                    "'%s' tem %d paginas. Com DOIS arquivos eu espero um de "
                    "cada lado - uma pagina cada. Nao sei qual das %d e a "
                    "boa." % (os.path.basename(f), n, n))
        return [(arquivos[0], 1), (arquivos[1], 1)]

    raise SystemExit("me passe um arquivo de duas paginas, ou dois arquivos "
                     "de uma pagina - recebi %d" % len(arquivos))


def _ajustar_sangria(origem, tmp, alvo_mm):
    """
    Poe a peca com EXATAMENTE a sangria que a regra pede. (arquivo, relato).

    Os tres casos, e nenhum deles para o servico:

      chegou pelada   inventa-se a sangria inteira, espelhando;
      chegou com menos  inventa-se so o que falta, a partir da borda da
                      sangria que ela ja tem - o desenho do designer fica;
      chegou com mais   recorta-se, e recortar nao mexe no desenho, so na
                      caixa.

    O ultimo caso e o comum hoje: os arquivos chegam com 3 mm e a regra,
    com vao 5, pede 2,5. O meio milimetro que sobra em cada lado era
    justamente o que fazia as sangrias de duas vizinhas se invadirem.

    Isso tambem resolve frente e verso com sangrias DIFERENTES, que ate
    agora eu parava: os dois saem daqui com a mesma medida, cada um pelo
    seu caminho, e a grade de corte serve aos dois.

    O arquivo de origem nao e tocado: o ajustado sai no temporario.

    Quando alguma borda tem fio parado na linha de corte, a sangria sai
    do mesmo jeito e o aviso sobe junto. Nao paro: a montagem ja nao vai
    sozinha para o portao - a trava no alto de montar() garante que ela
    fica na pasta do dia ate o operador olhar e mover. O lugar do olho
    humano ja existe; o que faltava era ele saber onde olhar.
    """
    import sangrar
    from finart_ctp.sangria import sangria_que_existe

    try:
        # O QUE O ARQUIVO TEM, E NAO O QUE ELE DIZ TER.
        #
        # Era sangria_do_arquivo, que le a caixa e acredita nela. O
        # 'LEILOES PANFLETO' de 18/09/2026 declarava 12,70 mm sem ter
        # BleedBox: o pypdf devolvia o MediaBox, que ali e a area das
        # MARCAS DE CORTE. A conta dizia "tem de sobra", esta funcao
        # recortava a caixa, e a sangria saia BRANCA na chapa.
        #
        # O erro mordia aqui ANTES de chegar no sangrar_pdf: um arquivo
        # que declarasse 2,50 mm de MediaBox sem tinta nenhuma batia com
        # o alvo e voltava na linha seguinte, sem nunca ser conferido.
        tinha, de_onde = sangria_que_existe(origem)
    except Exception as e:
        print("nao consegui ler as caixas de '%s' (%s) - deixei como esta"
              % (os.path.basename(origem), str(e)[:60]))
        return origem, None

    if abs(tinha - alvo_mm) <= sangrar.FOLGA_MM:
        return origem, {"tinha": tinha, "alvo": alvo_mm, "mexi": False}

    destino = os.path.join(tmp, "_sangrada_%s" % os.path.basename(origem))
    relato = sangrar.sangrar_pdf(origem, destino, alvo_mm)
    relato.update({"tinha": tinha, "alvo": alvo_mm, "mexi": True})

    o_que = ("chegou SEM sangria" if tinha <= sangrar.FOLGA_MM
             else "tinha %.2f mm" % tinha)
    if de_onde:
        o_que = "%s (%s)" % (o_que, de_onde)
    print("'%s' %s e a regra pede %.2f - %s:"
          % (os.path.basename(origem), o_que, alvo_mm,
             "recortei" if tinha > alvo_mm else "criei o que faltava"))
    for pg in relato["paginas"]:
        for borda in sangrar.BORDAS:
            tecnica, porque = pg["decisoes"][borda]
            print("   p%d %-9s %-8s %s" % (pg["pagina"], borda, tecnica,
                                           porque))
    return destino, relato


def _meia(g):
    """
    Meia volta: o giro que fica a 180 graus deste, em (-180, 180].

    -90 -> 90 · 90 -> -90 · 0 -> 180 · 180 -> 0

    E a conta de quem TOMBA a folha - o 'frente e verso' de duas chapas.
    NAO e a do bate-vira, que VIRA sobre o eixo vertical e por isso usa
    o espelho (-g). Ver a celula() em montar().
    """
    v = (g + 180) % 360
    return v - 360 if v > 180 else v


def passos_da_grade(inicio, tamanho, folgas, quantos):
    """
    Onde comeca cada coluna (ou linha), com UM VAO POR JUNCAO.

    'folgas' tem um numero por juncao - quantos-1 deles. Vazia ou toda
    zero, as pecas saem encostadas.

    Esta conta e o SAPIENTIA de 16 paginas: peca de 150, quatro colunas,
    folgas 0 / 5 / 0, comecando em 22,5. Sai 22,5 / 172,5 / 327,5 /
    477,5 - os mesmos numeros do modelo do Preps e do PDF que o operador
    montou, conferidos no decimo de milimetro.

    Com o vao espalhado por igual sairia 22,5 / 174,2 / 325,8 / 477,5:
    1,7 mm de erro por coluna, no lugar exato onde a folha dobra.
    """
    saida, onde = [], inicio
    for i in range(quantos):
        saida.append(onde)
        onde += tamanho + (folgas[i] if i < len(folgas) else 0)
    return saida


def montar(origem, destino, chapa=PM52, dpi=None, tmp=None,
           cols=COLS, rows=ROWS, vao=VAO, tipo="bate-vira",
           formato=None, folha=0, assim_mesmo=False, sangria=None,
           encontro="cabeca", marca_de_corte=True, marca_de_registro=True,
           escala_de_cor=True, giro=-90, lugares=None, lado=None,
           vaos=None,
           etiqueta=None):
    """
    Monta a grade cols x rows na chapa e grava o PDF.

    dpi=None (o normal) deixa o programa decidir: arquivo todo em
    imagem mantem a resolucao que ja tem; com texto ou vetor, vai em
    DPI_QUANDO_HA_TEXTO.

    A SANGRIA SAI DA GRADE, nao de um numero solto: metade do vao,
    2,5 mm na peca sozinha. Mudou o vao ou o numero de pecas, ela muda
    junto - ver sangrar.regra_da_sangria.

    DOIS LIMITES, e eles sao diferentes:

      area util  a chapa menos a pinca - o que a gravadora alcanca;
      formato    a FOLHA que entra na maquina - o que a impressora pega.

    Uma montagem pode caber na chapa e nao caber na folha. 'formato'
    aceita o numero da casa (4, 2, 3, 6...) e 'folha' escolhe qual das
    folhas dele, quando ha mais de uma - o F-04 e 33x48 OU 24x66.
    Sem 'formato' so a area util e conferida.

    assim_mesmo=True manda tocar mesmo nao cabendo. Regra do operador,
    11/09/2026: "a montagem e livre, me avise somente se nao couber
    dentro do formato, area util" - entao nao cabendo eu PARO e conto o
    que houve, e quem responde e ele. Passar assim_mesmo e a resposta.
    """
    if tipo not in ("bate-vira", "so-frente"):
        raise SystemExit(
            "nao sei montar '%s' sozinho. Hoje eu faco 'bate-vira' e "
            "'so-frente'. Para FRENTE E VERSO e para LIVRO, use o "
            "montar_livro(): ele sai num PDF de VARIAS paginas, uma "
            "chapa por pagina, e quem separa uma por arquivo e a entrega "
            "no CTP." % tipo)
    if cols < 1 or rows < 1:
        raise SystemExit("grade invalida: %s x %s" % (cols, rows))
    if tipo == "bate-vira" and cols % 2:
        raise SystemExit(
            "o bate-vira parte a chapa ao meio por uma linha VERTICAL: "
            "metade frente, metade verso. Precisa de colunas PARES, e a "
            "grade pedida tem %d." % cols)
    # A MONTAGEM NUNCA VAI PARA O PORTAO. Regra do operador, e ela e o
    # eixo do processo da AMERICA: a montagem sai na pasta do DIA, com
    # _MONTAGEM no nome, e fica ali esperando. Quem a poe na 'PARA CTP'
    # e o operador, DEPOIS de revisar - e e essa mudanca de pasta que
    # significa "aprovado".
    #
    # Escrever direto no portao pularia a revisao: o vigia pegaria o
    # arquivo na volta seguinte e mandaria para o CTP uma montagem que
    # ninguem olhou. Por isso a regra e uma trava no codigo, e nao uma
    # lembranca de quem escreve.
    partes = os.path.normpath(os.path.abspath(destino)).lower().split(os.sep)
    if "para ctp" in partes:
        raise SystemExit(
            "NAO gravo montagem dentro da 'PARA CTP'. Ela sai na pasta do "
            "dia; quem move para o portao e o operador, depois de revisar.")

    tmp = tmp or os.path.join(os.environ.get("TEMP", "."), "imposicao")
    os.makedirs(tmp, exist_ok=True)

    # AS PECAS QUE ESTA CHAPA PRECISA.
    #
    # Sem 'lugares' e o de sempre: a frente e o verso, um arquivo de
    # duas paginas ou dois arquivos, e a MESMA peca repetida em todas as
    # celulas.
    #
    # Com 'lugares' e um CADERNO, e ai cada celula leva uma pagina
    # DIFERENTE do livro - e a paginacao que o paginacao.py calculou.
    # Entao as pecas sao todas as paginas que este lado usa, cada uma
    # rasterizada uma vez, e a celula escolhe entre elas.
    if lugares:
        usadas = sorted({p for _, _, _, f, v in lugares
                         for p in ((f,) if lado != "verso" else (v,)) if p})
        if not usadas:
            raise SystemExit(
                "este lado do caderno nao tem pagina nenhuma - nao ha "
                "chapa a gravar")
        arquivo_unico = origem if isinstance(origem, str) else origem[0]
        lados = [(arquivo_unico, p) for p in usadas]
    else:
        lados = _pecas(origem, tipo)

    # ONDE A GUILHOTINA PASSA, E ONDE A FOLHA DOBRA.
    #
    # Em FOLHA SOLTA toda junta e corte, e o vao e o mesmo entre todas
    # as pecas - que e como isto funcionou ate 21/09/2026.
    #
    # NUM CADERNO NAO. Onde a folha dobra, as duas paginas sao o mesmo
    # pedaco de papel: elas tem de se ENCOSTAR, e um vao ali abriria uma
    # tira branca no meio da dobra. Os modelos da casa dizem, juncao por
    # juncao, qual e qual - o SAPIENTIA de 16 paginas em 4x2 da
    # 0 / 5 / 0 na largura, e nao 5 / 5 / 5.
    #
    # Espalhar o vao por igual naquele caderno poria as quatro colunas
    # em 22,5 / 174,2 / 325,8 / 477,5 em vez de 22,5 / 172,5 / 327,5 /
    # 477,5: erro de 1,7 mm por coluna, que grava limpo, imprime limpo e
    # so aparece na dobra.
    #
    # ELE VEM ANTES DA SANGRIA de proposito: e a folga que diz quanta
    # sangria cabe.
    if vaos:
        mult_x, mult_y = vaos
        if len(mult_x) != cols - 1 or len(mult_y) != rows - 1:
            raise SystemExit(
                "PAREI - a grade e %dx%d, que pede %d juncao(oes) em x e "
                "%d em y, e me deram %d e %d"
                % (cols, rows, cols - 1, rows - 1, len(mult_x), len(mult_y)))
    else:
        mult_x = (1,) * (cols - 1)
        mult_y = (1,) * (rows - 1)
    folgas_x = [m * vao for m in mult_x]
    # o catalogo conta a linha DE CIMA PARA BAIXO; aqui o y cresce para
    # cima, porque a pinca e no pe. Entao a lista vira.
    folgas_y = list(reversed([m * vao for m in mult_y]))

    # ANTES de qualquer medida: a sangria pela REGRA - metade do vao.
    # Depois daqui as duas pecas tem exatamente esta medida, venham do
    # jeito que vierem, e ha um numero so para o resto da funcao usar.
    # A SANGRIA PODE VIR DE FORA, e ai ela manda. O painel deixa
    # digita-la, e quem digitou sabe algo que a regra nao sabe - a peca
    # que ja chegou com a sangria do designer, por exemplo. Nao vindo, a
    # regra da casa decide, que e o normal.
    import sangrar
    if sangria is None:
        sangria = sangrar.regra_da_sangria(vao, cols * rows)
    sangria = float(sangria)

    # ONDE A FOLHA DOBRA NAO CABE SANGRIA, e isto nao e regra de oficio -
    # e falta de espaco.
    #
    # A sangria da casa e metade do vao, porque a guilhotina corta duas
    # vezes no vao e a tira do meio e refugo. Numa juncao de DOBRA nao ha
    # vao nenhum: as duas pecas se encostam, e qualquer sangria ali entra
    # POR CIMA da pagina vizinha - a de baixo e desenhada primeiro, a de
    # cima cobre o que alcancar.
    #
    # Medido no SAPIENTIA em 21/09/2026, antes desta trava: peca de 150
    # com 2,5 de sangria dava 155 desenhados num passo de 150, e 2,5 mm
    # da pagina 5 saiam cobertos por sangria ESPELHADA da pagina 12. O
    # miolo chegou sem sangria no BleedBox, entao o programa inventou a
    # dele por espelho - e espelhou em cima da pagina do lado.
    #
    # Aqui so se PODA. Quando aparecer um miolo com foto sangrada, a
    # conversa e outra: a sangria e por BORDA, e a mesma peca pode ter
    # dobra de um lado e corte do outro. Hoje ha um numero so para a
    # peca inteira, e o seguro e o menor deles.
    if lugares:
        cabe = min([f / 2.0 for f in folgas_x + folgas_y] or [sangria])
        if sangria > cabe + 0.001:
            print("a sangria cai de %.2f para %.2f: neste caderno ha "
                  "juncao de DOBRA, e ali as pecas se encostam - sangria "
                  "a mais entraria por cima da pagina do lado"
                  % (sangria, cabe))
            sangria = cabe

    sangria_feita = {}
    novos = {}
    for arquivo, _ in lados:
        if arquivo not in novos:
            novos[arquivo], sangria_feita[arquivo] = \
                _ajustar_sangria(arquivo, tmp, sangria)
    lados = [(novos[a], p) for a, p in lados]

    # O PRETO CHEIO PASSA A SOBREPOR, e isto TEM de vir antes de a peca
    # virar imagem: depois de rasterizada nao ha sobreposicao que
    # declarar - cada pixel ja tem as quatro tintas decididas.
    #
    # Regra do operador, 18/09/2026: "sempre o preto fique sobreposto,
    # quando ele for 100% nao pode vazar nas outras cores".
    # sobreposicao.py conta por que isto nao sai do CorelDRAW.
    from finart_ctp.sobreposicao import sobrepor_preto
    sobrepondo, trocados = 0, {}
    for arquivo in dict.fromkeys(a for a, _ in lados):
        alvo = os.path.join(tmp, "_op_" + os.path.basename(arquivo))
        try:
            n = sobrepor_preto(arquivo, alvo)
        except Exception as e:
            print("nao consegui declarar a sobreposicao em '%s' (%s) - "
                  "sigo sem ela" % (os.path.basename(arquivo), e))
            continue
        if n:
            trocados[arquivo] = alvo
            sobrepondo += n
    if trocados:
        lados = [(trocados.get(a, a), p) for a, p in lados]

    todo_imagem, maior, menor = True, None, None
    for arquivo in dict.fromkeys(a for a, _ in lados):
        ti, mai, men = resolucao_do_arquivo(arquivo)
        todo_imagem = todo_imagem and ti
        maior = mai if maior is None else max(maior, mai or 0)
        menor = men if menor is None else min(menor, men or men)
    if dpi is None:
        dpi = (int(round(maior)) if todo_imagem and maior
               else dpi_da_chapa(chapa))

    # O TRABALHO E DE UMA COR NO PRETO?
    #
    # Perguntado ao ARQUIVO, sem o perfil - e a armadilha 14 da skill de
    # cor: o perfil embutido espalha o preto pelas quatro tintas e a
    # resposta sai errada.
    #
    # Sendo de uma cor, as marcas, o registro e a escala saem SO NO K.
    # Regra do operador, 17/09/2026: "na america quando o trabalho for 1
    # cor no preto, corte, registro e escala de cor, mantem so o canal
    # do preto, para dar saida somente em 1 chapa". Em cor de registro
    # elas poriam C, M e Y na chapa, e o trabalho contaria QUATRO - foi
    # o que se mediu no 'miolo 16x23 caderno padrao juan' em 16/09: arte
    # K puro, montagem CKMY, com C=M=Y=0,0005 que eram so as marcas.
    so_preto = True
    for arquivo in dict.fromkeys(a for a, _ in lados):
        try:
            from finart_ctp.ghostscript import cobertura_por_pagina
            from finart_ctp.processador import preto_so_no_K
            # SO O QUE ESTA DENTRO DO CORTE. As marcas do designer vem
            # em cor de registro - CMYK a 100% - e ficam FORA dele:
            # contando a pagina inteira, arte de preto puro responde
            # 'quatro tintas' e o trabalho sai com quatro chapas.
            # Regra do operador, 18/09/2026.
            cobs = cobertura_por_pagina(arquivo, sem_icc=True,
                                        so_o_corte=True)
        except Exception:
            so_preto = False
            break
        if not cobs or not all(preto_so_no_K(c) for c in cobs):
            so_preto = False
            break

    # --- as pecas, ja em imagem (uma em 'so frente', duas no bate-vira) ---
    paginas = [
        pypdf.PdfReader(peca_em_pdf(
            arq, pg, dpi, os.path.join(tmp, "_p%d.pdf" % i))).pages[0]
        for i, (arq, pg) in enumerate(lados)]
    frente = paginas[0]
    verso = paginas[1] if len(paginas) > 1 else None

    # QUAL PECA E QUAL PAGINA DO LIVRO. So o caderno precisa disto: ali
    # a celula pergunta 'quem e a pagina 13?', e nao 'quem e a frente?'.
    peca_da_pagina = {pg: paginas[i] for i, (_, pg) in enumerate(lados)}

    # a peca chega com sangria: o CORTE esta para dentro dela
    sang_l = float(frente.mediabox.width) / MM
    sang_a = float(frente.mediabox.height) / MM
    corte_l = sang_l - 2 * sangria
    corte_a = sang_a - 2 * sangria

    # A FORMA DA CELULA VEM DO GIRO. A ±90 a peca deita e largura e
    # altura trocam; a 0 e a 180 ela entra como o arquivo e.
    #
    # Ate 18/09/2026 isto era `dl, da = corte_a, corte_l` fixo, e a peca
    # nao tinha como ficar em pe: quem invertesse os campos via o painel
    # deitar de novo, e a montagem que sobrava estourava o limite. Duas
    # coisas estavam com o mesmo nome - a MONTAGEM sai deitada (a borda
    # longa entra na pinca, e isso continua valendo), mas a PECA dentro
    # da celula pode entrar de qualquer um dos quatro jeitos. Oito pecas
    # em pe numa grade 4x2 dao uma montagem deitada: as duas convivem.
    # E NUM CADERNO QUEM DA O GIRO E A DOBRA, nao o parametro.
    #
    # O 'giro' desta funcao e o da folha solta, onde quem monta escolhe
    # como a peca entra na celula. Em caderno nao ha escolha: a celula
    # ja vem com o seu giro, lido do modelo do Preps, e as paginas de
    # uma linha saem a 180 para a dobra casar.
    #
    # Esquecer isso custou a primeira montagem do SAPIENTIA: o giro
    # ficou no -90 de fabrica, a peca de 150 x 220 deitou, e a montagem
    # deu 884,9 x 305,0 em vez de 605,0 x 445,0. Nao cabia no util da
    # MOZP, e a recusa foi o unico motivo de eu ter percebido.
    giro_da_celula = giro
    if lugares:
        deitados = {abs(int(g)) % 180 == 90 for _, _, g, _, _ in lugares}
        if len(deitados) > 1:
            raise SystemExit(
                "PAREI - neste caderno umas celulas estao em pe e outras "
                "deitadas, e a grade so tem uma forma de celula. Confira "
                "o arranjo: %s"
                % sorted({str(g) for _, _, g, _, _ in lugares}))
        giro_da_celula = 90 if deitados.pop() else 0

    dl, da = ((corte_a, corte_l) if giro_da_celula in (90, -90)
              else (corte_l, corte_a))

    montagem_l = cols * dl + sum(folgas_x)
    montagem_a = rows * da + sum(folgas_y)
    # --- OS DOIS LIMITES ---
    from finart_ctp.config import cabe_no_formato

    util_l, util_a = chapa.util
    cabe_util = montagem_l <= util_l and montagem_a <= util_a
    cabe_fmt, sentido = (cabe_no_formato(montagem_l, montagem_a, formato, folha)
                         if formato else (None, None))

    estouros = []
    if not cabe_util:
        estouros.append(
            "nao cabe no UTIL DA CHAPA: a montagem da %.1f x %.1f e o util "
            "e %.1f x %.1f (chapa %.0f x %.0f menos a pinca %.0f)"
            % (montagem_l, montagem_a, util_l, util_a,
               chapa.larg, chapa.alt, chapa.pinca))
    if cabe_fmt is False:
        from finart_ctp.config import FORMATOS_DA_CASA
        total, uteis = FORMATOS_DA_CASA[formato][min(
            folha, len(FORMATOS_DA_CASA[formato]) - 1)]
        estouros.append(
            "nao cabe no FORMATO %s: a montagem da %.1f x %.1f e a area util "
            "da folha e %s x %s (folha %s x %s)"
            % (formato, montagem_l, montagem_a, uteis[0], uteis[1],
               total[0], total[1]))

    if estouros and not assim_mesmo:
        raise SystemExit(
            "PAREI - " + "; e ".join(estouros)
            + ". Se for para tocar assim mesmo, mande de novo com "
              "--assim-mesmo.")
    if estouros:
        print("AVISO: a montagem NAO CABE e foi liberada a mao:")
        for e_ in estouros:
            print("   %s" % e_)
    if cabe_fmt is None and formato:
        print("o formato %s nao esta na tabela da casa - conferi so o util "
              "da chapa" % formato)

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

    xs = passos_da_grade(x0, dl, folgas_x, cols)
    ys = passos_da_grade(y0, da, folgas_y, rows)

    base = PageObject.create_blank_page(
        width=chapa.larg * MM, height=chapa.alt * MM)

    # QUEM VAI EM CADA CELULA, e com que giro.
    #
    # BATE-VIRA: a metade ESQUERDA da grade e a frente (gira -90, cabeca
    # para a DIREITA) e a metade DIREITA e o verso (gira +90, cabeca para
    # a ESQUERDA). As duas cabecas se encontram no vao do meio - e por
    # isso que ele precisa de colunas pares.
    #
    # SO FRENTE: a mesma arte em todas as celulas, todas no mesmo
    # sentido. Nao ha cabeca para encontrar cabeca nenhuma; o -90 esta
    # ali so porque a peca e em pe e a celula e deitada.
    # ONDE AS DUAS METADES SE ENCONTRAM, e nao e detalhe de gosto: e o
    # giro de cada peca na chapa. CABECA COM CABECA poe a frente a -90
    # (cabeca para a direita) e o verso a +90; PE COM PE e o contrario.
    #
    # O painel ja desenhava os dois, e quem aprova a montagem aprova o
    # DESENHO. Ate 18/09/2026 este parametro nao existia e o encontro era
    # sempre cabeca: a chapa saia diferente do desenho que a pessoa tinha
    # acabado de olhar, e ninguem veria antes da maquina.
    # O GIRO ESCOLHIDO E A BASE; 'pe com pe' inverte a metade, como
    # sempre fez. Com a base em -90 isto da exatamente o de antes.
    giro_frente = giro if encontro == "cabeca" else _meia(giro)

    # O VERSO DO BATE-VIRA E O ESPELHO DA FRENTE, e por isso e '-giro'.
    #
    # EU TROQUEI ISTO POR '+180' EM 18/09/2026 E ESTAVA ERRADO. O
    # operador pegou no CHECK-LIST RESSONANCIA MAGNETICA, A4 em pe:
    # "o verso nao pode ser 180 graus, tem que ficar com 0 graus como a
    # frente".
    #
    # Ele tem razao, e a razao e a maquina. Sao dois jeitos diferentes
    # de a folha voltar, e cada um pede uma conta:
    #
    #   BATE-VIRA (uma chapa): a folha VIRA sobre o eixo VERTICAL e a
    #   pinca continua na mesma borda. Isso e um ESPELHO horizontal: o
    #   que apontava para a direita passa a apontar para a esquerda, e
    #   o que apontava para CIMA continua apontando para cima. Entao
    #   -90 -> +90, e 0 -> 0.
    #
    #   FRENTE E VERSO (duas chapas): a folha TOMBA sobre o eixo
    #   horizontal, e ai sim o verso fica a 180 da frente.
    #
    # Com ±90 as duas contas dao o mesmo numero (-(-90) = +90 = -90+180),
    # e foi por isso que o erro passou: enquanto a peca so deitava,
    # nenhuma das duas se distinguia da outra. So com a peca EM PE elas
    # se separam - e ai o 180 poe a arte de cabeca para baixo na metade
    # do verso, que e o que ele viu.
    def celula(col):
        if tipo == "bate-vira" and col >= cols // 2:
            return verso, -giro_frente
        return frente, giro_frente

    if lugares:
        # O CADERNO: cada celula tem a SUA pagina e o SEU giro, vindos
        # da paginacao. Lugar sem pagina deste lado (o zero do Preps)
        # fica em branco - nao se inventa pagina, como o paginacao.py ja
        # diz: quem decide o que fazer com lado vazio e quem monta.
        for col, lin, giro_dele, pag_f, pag_v in lugares:
            numero = pag_v if lado == "verso" else pag_f
            if not numero:
                continue
            # DUAS TROCAS DE EIXO, e errar qualquer uma inverte o livro
            # sem dar erro em lugar nenhum:
            #
            # 1. a paginacao conta as celulas a partir de UM, como o
            #    Preps e como quem le a folha; a lista xs/ys comeca em
            #    zero;
            # 2. a LINHA 1 e a de CIMA - e assim que a dobra se le, e
            #    assim que a skill desenha o arranjo de 16. Mas o ys da
            #    montagem sobe do PE para o topo, porque y0 e a pinca.
            #    Entao a linha 1 e o ULTIMO ys.
            c0, l0 = col - 1, rows - lin
            if not (0 <= c0 < len(xs)) or not (0 <= l0 < len(ys)):
                raise SystemExit(
                    "a paginacao pede a celula (%d, %d) e a grade e "
                    "%d x %d - o caderno nao cabe nesta grade"
                    % (col, lin, cols, rows))
            # O GIRO VEM COMO TEXTO do catalogo de dobras ('90', '-90'),
            # porque ele foi copiado lugar por lugar dos modelos do
            # Preps. O 'por' quer numero, e passar a string levanta um
            # TypeError dentro do pypdf, longe daqui.
            por(base, peca_da_pagina[numero], int(giro_dele),
                xs[c0] - sangria, ys[l0] - sangria)
    else:
        for y in ys:
            for col, x in enumerate(xs):
                pagina, giro = celula(col)
                por(base, pagina, giro, x - sangria, y - sangria)

    # --- as marcas ---
    # AS TRES MARCAS SAO ESCOLHA DE QUEM MONTA, e o painel ja tinha as
    # tres caixinhas - elas so nao chegavam ate aqui. Desmarcar 'escala
    # de cor' num trabalho de uma cor no preto nao fazia efeito nenhum.
    linhas_v = [v for x in xs for v in (x, x + dl)]
    linhas_h = [v for y in ys for v in (y, y + da)]
    caixa = (x0, y0, x0 + montagem_l, y0 + montagem_a)
    recusadas = []
    if marca_de_corte:
        caminho_marcas, recusadas = marcas_em_pdf(
            linhas_v, linhas_h, caixa, chapa, os.path.join(tmp, "_m.pdf"),
            folga=sangria, so_preto=so_preto)
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
    if marca_de_registro and os.path.exists(reg_eps):
        reg = pypdf.PdfReader(
            eps_em_pdf(reg_eps, os.path.join(tmp, "_r.pdf"),
                       so_preto=so_preto)).pages[0]
        rl = float(reg.mediabox.width) / MM
        ra = float(reg.mediabox.height) / MM
        meio = y0 + montagem_a / 2.0 - ra / 2.0
        borda = sangria + ENCOSTO
        por(base, reg, 0, x0 - borda - rl, meio)
        por(base, reg, 0, x0 + montagem_l + borda, meio)

    # --- escala de cor: DE PE, no lado esquerdo, em cima ---
    #
    # Girada 90 graus e encostada na lateral esquerda, a 3 mm da sangria,
    # pendurada a partir do alto da montagem. Pedido do operador em
    # 10/09/2026 - antes ela ficava deitada ACIMA da montagem, e ali
    # comia altura de chapa que a arte pode querer.
    #
    # O topo desce a folga da marca para nao encostar na marca de corte de
    # cima, que passa nessa mesma faixa. Abaixo dela nao ha marca nenhuma
    # ate a metade da chapa, entao a barra fica limpa.
    cor_eps = os.path.join(MARCAS_PREPS, "cores finart.eps")
    if escala_de_cor and os.path.exists(cor_eps):
        cor = pypdf.PdfReader(
            eps_em_pdf(cor_eps, os.path.join(tmp, "_c.pdf"),
                       so_preto=so_preto)).pages[0]
        cl = float(cor.mediabox.width) / MM      # deitada: o comprimento
        ca = float(cor.mediabox.height) / MM     # deitada: a espessura
        topo = y0 + montagem_a - sangria
        por(base, cor, 90, x0 - (sangria + ENCOSTO_ESCALA) - ca, topo - cl)

    saida = pypdf.PdfWriter()
    saida.add_page(base)
    with io.open(destino, "wb") as f:
        saida.write(f)

    return {
        "so_preto": so_preto,
        "todo_imagem": todo_imagem, "dpi_maior": maior, "dpi_menor": menor,
        "marcas_recusadas": len(recusadas),
        "chapa": (chapa.larg, chapa.alt), "pinca": chapa.pinca,
        "corte_da_peca": (corte_l, corte_a), "deitada": (dl, da),
        "montagem": (montagem_l, montagem_a),
        "canto": (x0, y0), "colunas": xs, "linhas": ys,
        "sangria": sangria, "vao": vao, "dpi": dpi, "encontro": encontro,
        "marcas": {"corte": marca_de_corte, "registro": marca_de_registro,
                   "escala": escala_de_cor},
        "cols": cols, "rows": rows, "tipo": tipo, "pecas": cols * rows,
        "formato": formato, "folha": folha, "cabe_util": cabe_util,
        "cabe_formato": cabe_fmt, "sentido_na_folha": sentido,
        # OS ESTOUROS SAIEM INTEIROS, e nao so o 'sim, estourou': quem
        # libera uma montagem que nao cabe precisa deixar gravado O QUE
        # nao coube, com numero. 'Nao coube' sozinho nao ensina nada a
        # quem for olhar o historico depois - e o historico existe para
        # que a proxima regra da casa nasca dali.
        "estourou": bool(estouros), "estouros": estouros,
        "sangria_feita": sangria_feita,
    }


def montar_livro(origem, destino, paginas, por_caderno, processo, vira,
                 chapa=PM52, cols=None, rows=None, **kw):
    r"""
    O livro inteiro num PDF de VARIAS PAGINAS - uma chapa por pagina.

    Regra do operador, 21/09/2026, depois de a montagem recusar um
    caderno de canoa: *"preciso que na montagem consiga montar multiplas
    paginas, para ir caderno frente e verso, ai quando colocar PARA CTP,
    la sim, voce separa as paginas por chapa, cada pagina em uma chapa,
    e manda para o ctp"*.

    ISSO DESTRAVOU UM IMPASSE QUE DUROU DEZ DIAS. A montagem recusava
    'frente e verso' desde 11/09 com este motivo escrito: *"sao DUAS
    chapas, e o nome de cada arquivo de saida e convencao da casa que eu
    ainda nao tenho"*. A saida nao era descobrir o nome - era nao
    precisar dele: **um arquivo so, com uma chapa por pagina**.

    E a casa JA sabe separar. O `entrega.entregar_no_ctp()` recorta uma
    pagina por arquivo desde 17/09, com o numero na frente do nome -
    porque a gravadora puxa a primeira pagina e ignora o resto. O que
    faltava era alguem gerar o multipagina para ele separar.

    A ORDEM DAS PAGINAS E A ORDEM DA GRAVACAO. A pasta do CTP e lida em
    ordem alfabetica e o numero vai na frente do nome, entao a sequencia
    daqui - caderno 1 frente, caderno 1 verso, caderno 2 frente... - e a
    fila em que as chapas saem da gravadora. Trocar duas e um livro com
    o miolo fora de ordem que so aparece depois de dobrado e cortado.

    Devolve o relato de cada chapa, com a ETIQUETA que vai escrita nela.
    """
    from finart_ctp import paginacao

    # OS CADERNOS PODEM VIR PRONTOS DA TELA, e quando vem sao eles que
    # mandam. O painel deixa o montador somar caderno por caderno, cada
    # um com a SUA vira - e a casa mistura mesmo: o MIOLO CANTICOS saiu
    # com um caderno de 16 em frente e verso e um de 8 em bate-vira, que
    # e como o miolo fecha com menos chapa.
    #
    # Calcular aqui um por_caderno unico jogaria essa escolha fora e
    # montaria um livro que ninguem pediu.
    cadernos_prontos = kw.pop("cadernos", None)
    if cadernos_prontos:
        livro = []
        for c in cadernos_prontos:
            do_livro = [int(n) for n in (c.get("do_livro") or [])]
            vira_dele = c.get("tipo") or c.get("vira") or vira
            if int(c.get("repeticao", 1) or 1) != 1:
                raise SystemExit(
                    "o caderno %s pede a pagina repetida %s vez(es) na "
                    "chapa, e isso eu ainda nao desenho - sairia com "
                    "celulas vazias ou com pagina a mais"
                    % (c.get("numero", "?"), c.get("repeticao")))
            livro.append({
                "caderno": int(c.get("numero") or (len(livro) + 1)),
                "paginas": do_livro,
                "vira": vira_dele,
                "lugares": paginacao.lugares_do_caderno(do_livro, vira_dele),
            })
    else:
        livro = paginacao.lugares_do_livro(paginas, por_caderno, processo,
                                           vira)
        for c in livro:
            c["vira"] = vira
    if not livro:
        raise SystemExit("o livro saiu sem caderno nenhum - confira as "
                         "paginas (%s) e o tamanho do caderno (%s)"
                         % (paginas, por_caderno))

    # O BATE-VIRA EM CADERNO: UMA CHAPA SO, E A FOLHA PASSA DUAS VEZES.
    #
    # Isto aqui era uma RECUSA ate 21/09/2026, e a recusa estava certa
    # enquanto durou: eu tinha o par de cada lugar, mas nao qual pagina
    # cai em qual POSICAO da chapa, e chutar poria metade do miolo fora
    # de ordem sem dar erro nenhum.
    #
    # O que destravou foi o operador mandar o modelo E o resultado: o
    # '150 x 220 - Perfect Bound_SAPIENTIA.tpl' com o 'SAPIENCIA
    # MONTADO.pdf' ao lado, ja montado por ele no Preps. As 29 chapas
    # daquele arquivo sao 14 cadernos de 16 em frente e verso mais UM de
    # 4 em bate-vira - a chapa 29, de 330 x 480 -, e as quatro paginas
    # dela, medidas uma a uma contra o miolo, sao 227 / 226 em cima e
    # 228 / 225 embaixo.
    #
    # O catalogo ja dizia isso, em local: as frentes das celulas do
    # (4, BATE_VIRA) sao 3 / 2 em cima e 4 / 1 embaixo. Bate numero por
    # numero. Entao a regra e simples e agora tem prova atras:
    #
    #     UMA chapa, e cada celula leva a FRENTE do seu lugar.
    #
    # O verso nao se desenha porque ele ja esta la: e a pagina do lugar
    # espelhado, que a mesma chapa imprime quando a folha volta. Por
    # isso este caderno gasta UMA chapa e nao duas.
    # o 'extra' e da ETIQUETA (nome do livro, data) e nao do montar():
    # sai de kw aqui para nao chegar la como parametro desconhecido
    extra = kw.pop("extra", "") or ""
    tmp = kw.pop("tmp", None) or os.path.join(
        os.environ.get("TEMP", "."), "imposicao")
    os.makedirs(tmp, exist_ok=True)

    juntas = pypdf.PdfWriter()
    relatos = []
    for caderno in livro:
        n = caderno["caderno"]
        # A GRADE VEM DO ARRANJO DE CADA CADERNO, e nao de quem chamou:
        # em caderno ela nao e livre - a dobradeira dobra ao meio, e ao
        # meio de novo. E cada caderno pode ter a SUA, porque pode ter
        # tamanho e vira proprios.
        desenho = paginacao.arranjo(len(caderno["paginas"]), caderno["vira"])
        cols_reais, rows_reais = desenho["grade"]
        # E OS VAOS VEM DO ARRANJO TAMBEM. Num caderno, onde a folha
        # dobra as pecas se encostam e so onde se corta e que ha vao -
        # e isso e propriedade da DOBRA, lida do modelo do Preps, nao
        # coisa que se espalhe por igual.
        vaos_reais = paginacao.vaos_do_arranjo(len(caderno["paginas"]),
                                               caderno["vira"])

        # 'frente' e 'verso' sao as duas chapas do caderno, nesta ordem -
        # e a ordem delas no PDF e a fila em que a gravadora as puxa.
        #
        # NO BATE-VIRA SAO UMA SO. A folha passa duas vezes na mesma
        # chapa, entao pedir duas aqui gravaria a segunda a toa - e
        # ainda daria baixa de uma chapa que ninguem usou.
        lados = (("frente",) if caderno["vira"] == paginacao.BATE_VIRA
                 else ("frente", "verso"))
        for lado in lados:
            # na chapa do bate-vira nao se escreve FRENTE: ela e as duas
            # coisas, e quem imprime precisa ler isso nela
            etiqueta = paginacao.etiqueta(
                n, None if caderno["vira"] == paginacao.BATE_VIRA else lado,
                extra)
            parcial = os.path.join(tmp, "_chapa_c%d_%s.pdf" % (n, lado))
            d = montar(origem, parcial, chapa=chapa,
                       cols=cols_reais, rows=rows_reais,
                       tipo="so-frente",        # a paginacao ja mandou
                       lugares=caderno["lugares"], lado=lado,
                       vaos=vaos_reais,
                       etiqueta=etiqueta, **kw)
            d["caderno"], d["lado"], d["etiqueta"] = n, lado, etiqueta
            d["paginas_do_livro"] = [
                (v if lado == "verso" else f)
                for _, _, _, f, v in caderno["lugares"]]
            relatos.append(d)
            juntas.add_page(pypdf.PdfReader(parcial).pages[0])

    with io.open(destino, "wb") as f:
        juntas.write(f)

    return {"destino": destino, "chapas": relatos,
            "paginas_no_pdf": len(relatos),
            "processo": processo, "vira": vira,
            "por_caderno": por_caderno, "cadernos": len(livro)}


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


def _grade(texto):
    """'2x3' -> (2, 3). Colunas primeiro, como o painel escreve."""
    try:
        c, r = texto.lower().replace("×", "x").split("x")
        return int(c), int(r)
    except Exception:
        raise SystemExit("nao entendi a grade '%s' - escreva assim: 2x3"
                         % texto)


def _chapa(texto):
    """'525x459' -> a Chapa da AMERICA com essa medida, com a pinca dela."""
    l, a = _grade(texto)
    for chapa in AMERICA.values():
        if (int(chapa.larg), int(chapa.alt)) == (l, a):
            return chapa
    raise SystemExit(
        "nao conheco chapa %dx%d na AMERICA. Tenho: %s" %
        (l, a, ", ".join("%.0fx%.0f" % (c.larg, c.alt)
                         for c in AMERICA.values())))


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Monta uma grade de pecas numa chapa da AMERICA.")
    p.add_argument("arquivos", nargs="+",
                   help="a arte; no bate-vira, um PDF de duas paginas ou "
                        "DOIS arquivos (o 1o e a frente, o 2o e o verso)")
    p.add_argument("-o", "--saida", help="o PDF da montagem "
                                         "(por omissao, _MONTAGEM ao lado)")
    p.add_argument("--tipo", default="bate-vira",
                   choices=("bate-vira", "so-frente"))
    p.add_argument("--grade", default="%dx%d" % (COLS, ROWS),
                   help="colunas x linhas, ex. 2x3 (padrao %dx%d)"
                        % (COLS, ROWS))
    p.add_argument("--vao", type=float, default=VAO,
                   help="entre uma peca e a vizinha, de corte a corte "
                        "(padrao %.1f) - a SANGRIA sai daqui" % VAO)
    p.add_argument("--chapa", help="ex. 525x459 (por omissao, a PM 52)")
    p.add_argument("--formato", type=int,
                   help="o formato da casa (4, 2, 3, 6...) - confere se a "
                        "montagem cabe na AREA UTIL da folha")
    p.add_argument("--folha", type=int, default=0,
                   help="qual folha do formato, quando ele tem mais de uma "
                        "(o F-04 e 33x48 OU 24x66); 0 e a primeira")
    p.add_argument("--assim-mesmo", action="store_true", dest="assim_mesmo",
                   help="toca mesmo nao cabendo - sem isto eu paro e conto")
    p.add_argument("--giro", type=int, default=-90, choices=(0, 90, -90, 180),
                   help="como a peca entra na celula: a ±90 ela DEITA, a 0 "
                        "e a 180 fica EM PE (padrao -90, o que a casa "
                        "sempre fez)")
    p.add_argument("--dpi", type=int,
                   help="forca a resolucao; por omissao o programa decide")
    a = p.parse_args()

    cols, rows = _grade(a.grade)
    origem = a.arquivos if len(a.arquivos) > 1 else a.arquivos[0]
    primeiro = a.arquivos[0]
    destino = a.saida or os.path.join(os.path.dirname(primeiro) or ".",
                                      nome_da_montagem(primeiro))

    d = montar(origem, destino, chapa=_chapa(a.chapa) if a.chapa else PM52,
               dpi=a.dpi, cols=cols, rows=rows, vao=a.vao, tipo=a.tipo,
               formato=a.formato, folha=a.folha, assim_mesmo=a.assim_mesmo,
               giro=a.giro)
    print("chapa            %.0f x %.0f mm, pinca %.0f" %
          (d["chapa"][0], d["chapa"][1], d["pinca"]))
    print("grade            %d x %d = %d pecas, %s"
          % (d["cols"], d["rows"], d["pecas"], d["tipo"]))
    if d["formato"]:
        print("formato          %s   %s"
              % (d["formato"],
                 "entra %s x %s na folha" % d["sentido_na_folha"]
                 if d["cabe_formato"] else
                 "NAO CABE na folha" if d["cabe_formato"] is False
                 else "nao esta na tabela da casa"))
    print("peca (corte)     %.2f x %.2f mm  ->  deitada %.2f x %.2f"
          % (d["corte_da_peca"] + d["deitada"]))
    print("montagem         %.2f x %.2f mm (corte a corte)" % d["montagem"])
    print("canto inferior   x %.2f   y %.2f" % d["canto"])
    print("colunas em x     %s" % ["%.2f" % v for v in d["colunas"]])
    print("linhas em y      %s" % ["%.2f" % v for v in d["linhas"]])
    print("sangria %.2f   vao %.1f   (a regra: %s)"
          % (d["sangria"], d["vao"],
             "peca sozinha, o padrao da casa" if d["pecas"] <= 1
             else "metade do vao"))

    olhos = [(os.path.basename(a), n, borda, porque)
             for a, sf in (d["sangria_feita"] or {}).items()
             if sf for n, borda, porque in sf.get("precisa_de_olho", [])]
    if olhos:
        print()
        print("OLHE ANTES DE MOVER PARA A 'PARA CTP':")
        for arq, n, borda, porque in olhos:
            print("   %s p%d %s: %s" % (arq, n, borda, porque))
        print("   A sangria saiu espelhada nessas bordas. Onde ha fio parado")
        print("   na linha de corte, o espelho DUPLICA o fio. Confira na")
        print("   montagem antes de aprovar - eu nao invento traco.")
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
