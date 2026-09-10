# -*- coding: utf-8 -*-
r"""
Preflight: a conferencia da arte ANTES de virar chapa.

E o que um arte-finalista faz de olho no arquivo, e que ate agora a FIA
nao fazia. Ela media a CHAPA - tamanho, resolucao de gravacao - mas nao
olhava para DENTRO da arte. Uma imagem de 300 dpi esticada numa chapa de
1000 grava lisinha e sai borrada na tiragem, sem dar erro em lugar nenhum.

O que se confere aqui:

    resolucao efetiva   quantos dpi a imagem tem NO TAMANHO EM QUE FOI
                        COLOCADA - que nao e o dpi do arquivo dela
    fontes              incorporadas ou nao; fonte que falta e substituida
                        pelo RIP por outra, e o texto muda de forma
    traco fino          risco de espessura zero ou quase; some na chapa
    cor especial        Pantone e verniz que o arquivo declara
    caixas do PDF       TrimBox, BleedBox - o que o arquivo diz do corte

POR QUE ISTO E DIFICIL: o PDF nao diz em que tamanho a imagem ficou. Ele
diz "desenhe esta imagem no quadrado de 1x1" e, antes, aplica uma
transformacao que estica esse quadrado. Para saber o tamanho real e
preciso acompanhar a pilha de transformacoes - q, Q, cm - do comeco ao
fim, inclusive entrando nos grupos (Form XObject). E o que _Percorrer faz.
"""

import math

from .config import (LADO_MINIMO_IMAGEM_MM, RESOLUCAO_EFETIVA_BOA,
                     RESOLUCAO_EFETIVA_MINIMA, TRACO_MINIMO_MM)

PARA = "para"          # nao fecha a chapa sem gente olhar
AVISA = "avisa"        # so anota; o servico segue

# Comeco da mensagem de resolucao. A mensagem e ESCRITA a partir daqui e
# RECONHECIDA a partir daqui (e_de_resolucao), para as duas pontas nao
# envelhecerem separadas: quem consome precisa distinguir este achado dos
# outros, porque ha cliente que nao para por resolucao.
MARCA_RESOLUCAO = "imagem de menor resolucao"


def e_de_resolucao(texto):
    """True quando o achado fala da resolucao da imagem."""
    return texto.startswith(MARCA_RESOLUCAO)


def _multiplicar(m, n):
    """m aplicada ANTES de n, como o PDF empilha as transformacoes."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D,
            c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def _tamanho(ctm):
    """(largura, altura) em pontos do quadrado 1x1 sob esta transformacao."""
    a, b, c, d, _, _ = ctm
    return math.hypot(a, b), math.hypot(c, d)


def _escala(ctm):
    """Quanto a transformacao estica, para converter espessura de traco."""
    largura, altura = _tamanho(ctm)
    return (largura + altura) / 2.0


class _Percorrer(object):
    """
    Anda pelo conteudo da pagina carregando a transformacao atual.

    Guarda o que interessa: cada imagem colocada, com o tamanho que ficou,
    e a menor espessura de traco que apareceu.
    """

    def __init__(self, leitor):
        self.leitor = leitor
        self.imagens = []          # (nome, px_larg, px_alt, pt_larg, pt_alt)
        self.traco_fino = None     # menor espessura, em pontos
        self.especiais = set()
        self.vistos = set()        # grupos ja percorridos, contra ciclo

    def pagina(self, pag):
        from pypdf.generic import ContentStream
        conteudo = ContentStream(pag.get_contents(), self.leitor)
        recursos = pag.get("/Resources")
        self._andar(conteudo.operations,
                    recursos.get_object() if recursos else {},
                    (1, 0, 0, 1, 0, 0), 0)

    def _andar(self, operacoes, recursos, ctm, fundo):
        if fundo > 8:
            return
        pilha = []
        largura_traco = 1.0

        for operandos, operador in operacoes:
            try:
                if operador == b"q":
                    pilha.append((ctm, largura_traco))
                elif operador == b"Q":
                    if pilha:
                        ctm, largura_traco = pilha.pop()
                elif operador == b"cm":
                    ctm = _multiplicar(tuple(float(v) for v in operandos[:6]),
                                       ctm)
                elif operador == b"w":
                    largura_traco = float(operandos[0])
                    self._anotar_traco(largura_traco, ctm)
                elif operador in (b"S", b"s", b"B", b"b"):
                    self._anotar_traco(largura_traco, ctm)
                elif operador in (b"cs", b"CS"):
                    self._olhar_cor(operandos[0], recursos)
                elif operador == b"Do":
                    self._entrar(operandos[0], recursos, ctm, fundo)
            except (TypeError, ValueError, IndexError, KeyError):
                continue

    def _anotar_traco(self, largura, ctm):
        real = largura * _escala(ctm)
        if self.traco_fino is None or real < self.traco_fino:
            self.traco_fino = real

    def _olhar_cor(self, nome, recursos):
        espacos = recursos.get("/ColorSpace")
        if not espacos:
            return
        espaco = espacos.get_object().get(nome)
        if espaco is None:
            return
        espaco = espaco.get_object()
        if isinstance(espaco, list) and espaco:
            familia = str(espaco[0])
            if familia == "/Separation" and len(espaco) > 1:
                self.especiais.add(str(espaco[1]).lstrip("/"))
            elif familia == "/DeviceN" and len(espaco) > 1:
                for tinta in espaco[1]:
                    self.especiais.add(str(tinta).lstrip("/"))

    def _entrar(self, nome, recursos, ctm, fundo):
        xobjs = recursos.get("/XObject")
        if not xobjs:
            return
        xobjs = xobjs.get_object()
        referencia = xobjs.raw_get(nome) if nome in xobjs else None
        marca = getattr(referencia, "idnum", None)

        obj = xobjs[nome].get_object()
        tipo = obj.get("/Subtype")

        if tipo == "/Image":
            larg_pt, alt_pt = _tamanho(ctm)
            self.imagens.append((str(nome), int(obj["/Width"]),
                                 int(obj["/Height"]), larg_pt, alt_pt))
            return

        if tipo == "/Form":
            if marca is not None and (marca, fundo) in self.vistos:
                return
            if marca is not None:
                self.vistos.add((marca, fundo))
            from pypdf.generic import ContentStream
            proprio = obj.get("/Matrix")
            if proprio:
                ctm = _multiplicar(tuple(float(v) for v in proprio), ctm)
            dentro = obj.get("/Resources")
            self._andar(ContentStream(obj, self.leitor).operations,
                        dentro.get_object() if dentro else recursos,
                        ctm, fundo + 1)


def _fontes_soltas(pag):
    """Nomes das fontes que NAO estao incorporadas no arquivo."""
    soltas = []
    try:
        recursos = pag["/Resources"].get_object()
        fontes = recursos["/Font"].get_object()
    except (KeyError, TypeError):
        return soltas

    for chave in fontes:
        try:
            fonte = fontes[chave].get_object()
            nome = str(fonte.get("/BaseFont", chave)).lstrip("/")
            # fonte composta guarda o desenho na filha
            descendentes = fonte.get("/DescendantFonts")
            if descendentes:
                fonte = descendentes.get_object()[0].get_object()
            desc = fonte.get("/FontDescriptor")
            if desc is None:
                # sem descritor: e uma das 14 padrao do PDF, que o RIP tem
                continue
            desc = desc.get_object()
            if not any(k in desc for k in ("/FontFile", "/FontFile2",
                                           "/FontFile3")):
                soltas.append(nome)
        except (KeyError, TypeError, IndexError):
            continue
    return soltas


def _mm(pontos):
    return pontos / 72.0 * 25.4


def conferir_arte(pdf, pagina=1):
    """
    Confere a arte e devolve [(gravidade, texto)] do que achou.

    Lista vazia quer dizer arte limpa. Gravidade PARA e o que nao fecha
    sem gente olhar; AVISA so vai para o log.
    """
    import pypdf.filters
    from pypdf import PdfReader

    achados = []
    limite = pypdf.filters.MAX_DECLARED_STREAM_LENGTH
    # imagem de chapa passa dos 75 MB que o pypdf aceita por padrao, e sem
    # levantar isto a conferencia calaria justamente nas artes pesadas
    pypdf.filters.MAX_DECLARED_STREAM_LENGTH = 8 << 30
    try:
        try:
            leitor = PdfReader(pdf)
            pag = leitor.pages[pagina - 1]
        except Exception:
            # Arquivo que nem abre nao e problema DAQUI: quem faz a chapa
            # vai esbarrar nele logo adiante e dizer isso direito. O
            # preflight nao pode ser o portao que fecha a producao.
            return achados

        soltas = _fontes_soltas(pag)
        if soltas:
            achados.append((PARA, "fonte NAO incorporada: %s. O RIP vai "
                                  "trocar por outra e o texto muda de forma"
                            % ", ".join(sorted(set(soltas))[:4])))

        andarilho = _Percorrer(leitor)
        try:
            andarilho.pagina(pag)
        except Exception as e:
            achados.append((AVISA, "nao consegui ler o desenho da pagina "
                                   "(%s) - conferi so o que deu"
                            % str(e)[:60]))

        pior = None
        for nome, px_l, px_a, pt_l, pt_a in andarilho.imagens:
            if pt_l <= 0 or pt_a <= 0:
                continue
            larg_mm, alt_mm = _mm(pt_l), _mm(pt_a)
            if min(larg_mm, alt_mm) < LADO_MINIMO_IMAGEM_MM:
                continue        # tirinha de degrade, fio de moldura
            dpi = min(px_l / (pt_l / 72.0), px_a / (pt_a / 72.0))
            if pior is None or dpi < pior[0]:
                pior = (dpi, nome, larg_mm, alt_mm)

        if pior:
            dpi, nome, larg_mm, alt_mm = pior
            # UMA CASA DECIMAL, e nao zero. Com %.0f, a GRADE 41 da VIVA
            # de 10/09/2026 - 566 px em 72 mm, ou 199,67 dpi - aparecia
            # como '200 dpi ... abaixo de 200 dpi'. A trava estava certa
            # e a frase parecia mentira, e frase que parece mentira faz o
            # operador desconfiar do programa inteiro.
            onde = ("%s: %.1f dpi no tamanho colocado (%.0f x %.0f mm)"
                    % (MARCA_RESOLUCAO, dpi, larg_mm, alt_mm))
            if dpi < RESOLUCAO_EFETIVA_MINIMA:
                achados.append((PARA, onde + " - abaixo de %d dpi a arte sai "
                                             "borrada na tiragem"
                                % RESOLUCAO_EFETIVA_MINIMA))
            elif dpi < RESOLUCAO_EFETIVA_BOA:
                achados.append((AVISA, onde + " - o offset pede %d"
                                % RESOLUCAO_EFETIVA_BOA))

        fino = andarilho.traco_fino
        if fino is not None and _mm(fino) < TRACO_MINIMO_MM:
            achados.append((AVISA, "traco de %.3f mm na arte - abaixo de "
                                   "%.2f mm o risco some na chapa"
                            % (_mm(fino), TRACO_MINIMO_MM)))

        especiais = {t for t in andarilho.especiais
                     if t not in ("Cyan", "Magenta", "Yellow", "Black", "All",
                                  "None")}
        if especiais:
            achados.append((AVISA, "cor especial declarada na arte: %s"
                            % ", ".join(sorted(especiais)[:4])))

        try:
            corte, papel = pag.trimbox, pag.mediabox
            if (abs(float(corte.width) - float(papel.width)) > 1
                    or abs(float(corte.height) - float(papel.height)) > 1):
                achados.append((AVISA, "o arquivo declara corte de %.0f x "
                                       "%.0f mm dentro de %.0f x %.0f"
                                % (_mm(float(corte.width)),
                                   _mm(float(corte.height)),
                                   _mm(float(papel.width)),
                                   _mm(float(papel.height)))))
        except Exception:
            pass
    finally:
        pypdf.filters.MAX_DECLARED_STREAM_LENGTH = limite

    return achados
