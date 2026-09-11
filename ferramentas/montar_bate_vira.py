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

  - nao mexe na cor da arte. O arquivo ja chega em CMYK e e rasterizado
    com -dUseFastColor, que le a tinta como esta escrita. Passar pelo
    perfil embutido remistura o preto nas quatro tintas (armadilha 1 da
    skill de cor);
  - nao inventa marca: usa os EPS da propria casa, da pasta Marks do
    Preps;
  - nao salva nada por cima do arquivo do cliente;
  - nao faz FRENTE E VERSO (duas chapas, uma por lado). A conta seria a
    mesma; o que falta e o nome de cada arquivo de saida, que e
    convencao da casa e eu nao invento.

Medidas em MILIMETRO na configuracao; o PDF trabalha em ponto.
"""

import io
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


def marcas_em_pdf(linhas_v, linhas_h, caixa, chapa, destino, folga):
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

    try:
        tinha = sangrar.sangria_do_arquivo(origem)
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
    print("'%s' %s e a regra pede %.2f - %s:"
          % (os.path.basename(origem), o_que, alvo_mm,
             "recortei" if tinha > alvo_mm else "criei o que faltava"))
    for pg in relato["paginas"]:
        for borda in sangrar.BORDAS:
            tecnica, porque = pg["decisoes"][borda]
            print("   p%d %-9s %-8s %s" % (pg["pagina"], borda, tecnica,
                                           porque))
    return destino, relato


def montar(origem, destino, chapa=PM52, dpi=None, tmp=None,
           cols=COLS, rows=ROWS, vao=VAO, tipo="bate-vira",
           formato=None, folha=0, assim_mesmo=False):
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
            "nao sei montar '%s'. Hoje eu faco 'bate-vira' e 'so-frente'. "
            "'frente-verso' sao DUAS chapas, e o nome de cada arquivo de "
            "saida e convencao da casa que eu ainda nao tenho." % tipo)
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

    # a frente e o verso: um arquivo de duas paginas, ou dois arquivos
    lados = _pecas(origem, tipo)

    # ANTES de qualquer medida: a sangria pela REGRA - metade do vao.
    # Depois daqui as duas pecas tem exatamente esta medida, venham do
    # jeito que vierem, e ha um numero so para o resto da funcao usar.
    import sangrar
    sangria = sangrar.regra_da_sangria(vao, cols * rows)

    sangria_feita = {}
    novos = {}
    for arquivo, _ in lados:
        if arquivo not in novos:
            novos[arquivo], sangria_feita[arquivo] = \
                _ajustar_sangria(arquivo, tmp, sangria)
    lados = [(novos[a], p) for a, p in lados]

    todo_imagem, maior, menor = True, None, None
    for arquivo in dict.fromkeys(a for a, _ in lados):
        ti, mai, men = resolucao_do_arquivo(arquivo)
        todo_imagem = todo_imagem and ti
        maior = mai if maior is None else max(maior, mai or 0)
        menor = men if menor is None else min(menor, men or men)
    if dpi is None:
        dpi = (int(round(maior)) if todo_imagem and maior
               else dpi_da_chapa(chapa))

    # --- as pecas, ja em imagem (uma em 'so frente', duas no bate-vira) ---
    paginas = [
        pypdf.PdfReader(peca_em_pdf(
            arq, pg, dpi, os.path.join(tmp, "_p%d.pdf" % i))).pages[0]
        for i, (arq, pg) in enumerate(lados)]
    frente = paginas[0]
    verso = paginas[1] if len(paginas) > 1 else None

    # a peca chega com sangria: o CORTE esta para dentro dela
    sang_l = float(frente.mediabox.width) / MM
    sang_a = float(frente.mediabox.height) / MM
    corte_l = sang_l - 2 * sangria
    corte_a = sang_a - 2 * sangria

    # deitada, largura e altura trocam
    dl, da = corte_a, corte_l

    montagem_l = cols * dl + (cols - 1) * vao
    montagem_a = rows * da + (rows - 1) * vao
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

    xs = [x0 + c * (dl + vao) for c in range(cols)]
    ys = [y0 + r * (da + vao) for r in range(rows)]

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
    def celula(col):
        if tipo == "bate-vira" and col >= cols // 2:
            return verso, 90
        return frente, -90

    for y in ys:
        for col, x in enumerate(xs):
            pagina, giro = celula(col)
            por(base, pagina, giro, x - sangria, y - sangria)

    # --- as marcas ---
    linhas_v = [v for x in xs for v in (x, x + dl)]
    linhas_h = [v for y in ys for v in (y, y + da)]
    caixa = (x0, y0, x0 + montagem_l, y0 + montagem_a)
    caminho_marcas, recusadas = marcas_em_pdf(
        linhas_v, linhas_h, caixa, chapa, os.path.join(tmp, "_m.pdf"),
        folga=sangria)
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
    if os.path.exists(cor_eps):
        cor = pypdf.PdfReader(
            eps_em_pdf(cor_eps, os.path.join(tmp, "_c.pdf"))).pages[0]
        cl = float(cor.mediabox.width) / MM      # deitada: o comprimento
        ca = float(cor.mediabox.height) / MM     # deitada: a espessura
        topo = y0 + montagem_a - sangria
        por(base, cor, 90, x0 - (sangria + ENCOSTO_ESCALA) - ca, topo - cl)

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
        "sangria": sangria, "vao": vao, "dpi": dpi,
        "cols": cols, "rows": rows, "tipo": tipo, "pecas": cols * rows,
        "formato": formato, "folha": folha, "cabe_util": cabe_util,
        "cabe_formato": cabe_fmt, "sentido_na_folha": sentido,
        "estourou": bool(estouros),
        "sangria_feita": sangria_feita,
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
               formato=a.formato, folha=a.folha, assim_mesmo=a.assim_mesmo)
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
