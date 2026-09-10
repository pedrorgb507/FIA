# -*- coding: utf-8 -*-
r"""
O PROTOCOLO DE ENTREGA - o papel que o cliente assina ao receber.

E o mesmo papel do F12 do GEREMPRE, e sai quando as quatro vagas da OS
fecham: imprime o verso do ultimo arquivo, fecha a OS, tira o protocolo.

POR QUE DESENHAR AQUI, e nao mandar o GEREMPRE imprimir. O relatorio vive
dentro do exe Delphi, compilado, sem fonte: para tira-lo de la seria
preciso abrir o programa, achar a OS e apertar F12 - uma janela na tela
da maquina, no meio do trabalho de alguem. O conteudo esta todo no banco.
E a mesma razao da folha da OS, em os_impressa.py.

DE ONDE VEIO O DESENHO. De duas fontes, e as duas de verdade:

  - o U:\ZAP PROT ENTREGA.rpf, um protocolo renderizado pelo proprio
    GEREMPRE (OS 16577, ZAP CARTOES), de onde sairam as coordenadas de
    cada campo E o retangulo de cada celula, em unidades de 96 dpi;
  - o F12 da OS 19605, impresso pelo operador em 10/09/2026 e conferido
    contra a primeira versao desta folha. Foi ele que mostrou as quatro
    coisas que faltavam, e que estao anotadas onde cada uma foi feita.

DUAS VIAS NA MESMA FOLHA, a segunda 467 unidades abaixo - a do cliente e
a da casa, para destacar - e o ESTOQUE embaixo das duas.

MOSTRA DINHEIRO, ao contrario da folha da OS: aquela e a via de producao
e o papel anda pela oficina; esta e o recibo do cliente.
"""

import os

from .config import IMPRESSORA
from .os_impressa import A4_MM, DPI, LOGO, _data, _fonte, _inteiro

# As coordenadas vieram do .rpf nesta escala: o ReportBuilder rendeu a
# folha A4 em 96 dpi, e 210 mm dao 794 unidades.
DPI_RPF = 96.0
SEGUNDA_VIA = 467              # quanto a segunda via desce

TELEFONE = "Telefone: (62) 3988-7072 / 3988-7052"
EMAIL = "finartdigitalgo@gmail.com"
AVISO = ["Solicitamos que todos os materiais",
         "sejam revisados antes de serem",
         "confeccionados para evitarmos",
         "reimpressões futuras."]

# ----------------------------------------------------------------------
# A GRADE
# ----------------------------------------------------------------------
# Lida dos retangulos de celula do .rpf. A primeira versao desta folha
# saiu SEM LINHA NENHUMA - o texto no lugar certo, mas solto no papel - e
# o operador nao reconheceu como sendo o protocolo dele. A grade nao e
# enfeite: e o que faz o papel parecer o papel.
ESQ, DIR = 40, 752             # as bordas da caixa de cada via
Y_TOPO = 60                    # onde comeca a caixa
Y_CABECALHO = 118              # abaixo do logotipo e do titulo
Y_LINHAS = [148, 170, 192, 214, 236, 258, 280, 302, 324, 346, 368, 390]
Y_RODAPE = 458                 # abaixo de VENDEDOR / aviso / RECEBEDOR

X_OS = 675                     # a vertical que separa o numero da OS
# as verticais da linha do cliente
X_CLI_VALOR, X_CONTATO, X_CONT_VALOR, X_DATA, X_DATA_VALOR = (
    112, 357, 434, 537, 675)
# as verticais das linhas de produto
X_PROD_VALOR, X_UNIT, X_UNIT_VALOR, X_TOT, X_TOT_VALOR = (
    112, 573, 611, 664, 699)
# as verticais das linhas de titulo
X_TIT_VALOR, X_OBS, X_OBS_VALOR = 112, 413, 450
# as verticais da faixa do TOTAL GERAL. Nao sao as das linhas de
# produto: a de x=573 passava POR CIMA do 'TOTAL GERAL', cortando o G.
X_TOTAL_ESQ, X_TOTAL_RS, X_TOTAL_VALOR = 520, 630, 690
# as verticais do rodape
X_AVISO_CAIXA, X_RECEBEDOR_CAIXA = 328, 578

LOGO_XYW = (52, 68, 96)        # x, y, largura do logotipo
CORPO_PX = 11
TITULO_PX = 15
MIUDO_PX = 9                   # os valores de dinheiro saem menores

# ----------------------------------------------------------------------
# O ESTOQUE, embaixo das duas vias
# ----------------------------------------------------------------------
# Nao estava no modelo da ZAP - aquele cliente nao tinha chapa em
# estoque -, e so apareceu no F12 da OS 19605. Lista SO AS CHAPAS QUE
# ESTA OS USOU, com o saldo que o cliente tem agora: 'voce gastou isto,
# sobrou aquilo'. Conferido contra a CHA: 103 = 101 e 98 = 158.
Y_ESTOQUE_TITULO = 1010
Y_ESTOQUE_CABECA = 1042
Y_ESTOQUE_LINHA = 1052
Y_ESTOQUE_PRIMEIRA = 1062
PASSO_ESTOQUE = 20
X_ESTOQUE_CHAPA = 230
X_ESTOQUE_QTD = 500
X_ESTOQUE_ESQ, X_ESTOQUE_DIR = 150, 640


def _dinheiro(v):
    """35.0 -> '35,00'. O papel e brasileiro."""
    try:
        return ("%.2f" % float(v or 0)).replace(".", ",")
    except (TypeError, ValueError):
        return "0,00"


def _produto(item):
    """
    '4 - SOLIDA FT4 510 X 400 - F4 - 1 X 0'

    O NUMERO DA FRENTE E A QUANTIDADE DE CHAPAS, e nao a vaga. Li errado
    do modelo da ZAP, onde a OS tinha uma chapa na vaga 1 e os dois
    numeros calhavam de ser 1. O F12 da OS 19605 desfez a duvida: as
    quatro vagas mostram '4 - ', porque cada uma gasta quatro chapas de
    metal, e as vagas sao 1, 2, 3 e 4.
    """
    return "%s - %s %s X %s - %s - %s X %s" % (
        _inteiro(item["quantas"]), item["material"],
        _inteiro(item["alt"]), _inteiro(item["lar"]),
        item["montagem"], _inteiro(item["frente"]), _inteiro(item["verso"]))


def _cortar(tinta, texto, fonte, largura_px):
    """O texto que cabe em 'largura_px'. Sem isto um campo invade o outro."""
    if not texto:
        return ""
    texto = str(texto)
    if tinta.textlength(texto, font=fonte) <= largura_px:
        return texto
    while texto and tinta.textlength(texto, font=fonte) > largura_px:
        texto = texto[:-1]
    return texto


def folha(dados, estoque=None, dpi=DPI):
    """
    A folha A4 do protocolo: duas vias e o estoque. Imagem do Pillow.

    'dados' e o que gerempre.dados_da_os() devolve; 'estoque' e uma lista
    de (nome_da_chapa, saldo) - so as chapas que esta OS usou.
    """
    from PIL import Image, ImageDraw

    e = dpi / DPI_RPF
    im = Image.new("RGB", (int(round(A4_MM[0] / 25.4 * dpi)),
                           int(round(A4_MM[1] / 25.4 * dpi))), "white")
    tinta = ImageDraw.Draw(im)

    normal = _fonte(int(round(CORPO_PX * e)))
    negrito = _fonte(int(round(CORPO_PX * e)), negrito=True)
    titulo = _fonte(int(round(TITULO_PX * e)), negrito=True)
    miudo = _fonte(int(round(MIUDO_PX * e)))

    def txt(x, y, s, fonte=None, dy=0):
        if s in (None, ""):
            return
        tinta.text((x * e, (y + dy) * e), str(s), font=fonte or normal,
                   fill="black")

    def linha(x1, y1, x2, y2, dy=0):
        tinta.line([(x1 * e, (y1 + dy) * e), (x2 * e, (y2 + dy) * e)],
                   fill="black", width=max(1, int(round(e))))

    itens = {i["vaga"]: i for i in dados.get("itens") or []}

    for dy in (0, SEGUNDA_VIA):
        # ---- a caixa e a grade ----
        linha(ESQ, Y_TOPO, DIR, Y_TOPO, dy)
        linha(ESQ, Y_RODAPE, DIR, Y_RODAPE, dy)
        linha(ESQ, Y_TOPO, ESQ, Y_RODAPE, dy)
        linha(DIR, Y_TOPO, DIR, Y_RODAPE, dy)
        linha(ESQ, Y_CABECALHO, DIR, Y_CABECALHO, dy)
        for y in Y_LINHAS:
            linha(ESQ, y, DIR, y, dy)
        linha(X_OS, Y_CABECALHO, X_OS, Y_LINHAS[0], dy)

        # verticais da linha do cliente
        for x in (X_CLI_VALOR, X_CONTATO, X_CONT_VALOR, X_DATA, X_DATA_VALOR):
            linha(x, Y_LINHAS[0], x, Y_LINHAS[1], dy)
        # a do endereco: so a do rotulo
        linha(X_CLI_VALOR, Y_LINHAS[1], X_CLI_VALOR, Y_LINHAS[2], dy)
        # as quatro duplas de produto/titulo
        for n in range(4):
            topo_p, base_p = Y_LINHAS[2 + n * 2], Y_LINHAS[3 + n * 2]
            base_t = Y_LINHAS[4 + n * 2]
            for x in (X_PROD_VALOR, X_UNIT, X_UNIT_VALOR, X_TOT, X_TOT_VALOR):
                linha(x, topo_p, x, base_p, dy)
            for x in (X_TIT_VALOR, X_OBS, X_OBS_VALOR):
                linha(x, base_p, x, base_t, dy)
        # a faixa do total, com as divisorias dela
        for x in (X_TOTAL_ESQ, X_TOTAL_RS, X_TOTAL_VALOR):
            linha(x, Y_LINHAS[10], x, Y_LINHAS[11], dy)
        linha(X_AVISO_CAIXA, Y_LINHAS[11], X_AVISO_CAIXA, Y_RODAPE, dy)
        linha(X_RECEBEDOR_CAIXA, Y_LINHAS[11], X_RECEBEDOR_CAIXA, Y_RODAPE, dy)

        # ---- o logotipo e o titulo ----
        if os.path.exists(LOGO):
            try:
                from PIL import Image as Im
                logo = Im.open(LOGO).convert("RGB")
                larg = int(round(LOGO_XYW[2] * e))
                altura = int(round(logo.height * larg / logo.width))
                im.paste(logo.resize((larg, altura), Im.LANCZOS),
                         (int(round(LOGO_XYW[0] * e)),
                          int(round((LOGO_XYW[1] + dy) * e))))
            except Exception:
                pass
        txt(466, 80, "PROTOCOLO DE ENTREGA", titulo, dy)

        # ---- cabecalho ----
        txt(47, 126, TELEFONE, negrito, dy)
        txt(463, 126, EMAIL, negrito, dy)
        txt(683, 125, "OS: %s" % dados.get("numero"), negrito, dy)

        # ---- cliente / contato / entrega ----
        txt(42, 153, "CLIENTE:", negrito, dy)
        txt(117, 153, _cortar(tinta, dados.get("cliente"), normal,
                              (X_CONTATO - 117 - 3) * e), normal, dy)
        txt(362, 153, "CONTATO:", negrito, dy)
        txt(439, 153, _cortar(tinta, dados.get("contato"), normal,
                              (X_DATA - 439 - 3) * e), normal, dy)
        txt(542, 153, "DATA DE ENTREGA:", negrito, dy)
        txt(680, 153, _data(dados.get("entrega")), normal, dy)

        # ---- endereco: vem do CADASTRO DO CLIENTE, e nao da OS ----
        # A OS tem campos proprios de endereco e eles estao vazios em
        # todas as 19.577 - o F12 puxa da tabela CLI. Foi o papel de
        # verdade que mostrou: a OS 19605 saiu com o endereco completo,
        # e a primeira versao desta folha saiu em branco.
        txt(42, 174, "ENDEREÇO:", negrito, dy)
        txt(116, 174, _cortar(tinta, dados.get("endereco"), normal,
                              (DIR - 116 - 3) * e), normal, dy)

        # ---- as quatro vagas ----
        for n in range(1, 5):
            y_p = Y_LINHAS[2 + (n - 1) * 2] + 5
            y_t = Y_LINHAS[3 + (n - 1) * 2] + 5
            item = itens.get(n)
            txt(42, y_p, "PRODUTO:", negrito, dy)
            txt(578, y_p, "UNIT.", negrito, dy)
            txt(668, y_p, "TOT.", negrito, dy)
            txt(42, y_t, "TÍTULO:", negrito, dy)
            txt(418, y_t, "OBS:", negrito, dy)
            if item:
                txt(116, y_p, _cortar(tinta, _produto(item), normal,
                                      (X_UNIT - 116 - 3) * e), normal, dy)
                txt(117, y_t, _cortar(tinta, item["titulo"], normal,
                                      (X_OBS - 117 - 3) * e), normal, dy)
                txt(453, y_t, _cortar(tinta, item["obs"], normal,
                                      (X_UNIT - 453 - 3) * e), normal, dy)
            txt(618, y_p + 2, _dinheiro(item["unitario"] if item else 0),
                miudo, dy)
            txt(706, y_p + 2, _dinheiro(item["total"] if item else 0),
                miudo, dy)

        # ---- total geral ----
        txt(534, Y_LINHAS[10] + 5, "TOTAL GERAL", negrito, dy)
        txt(638, Y_LINHAS[10] + 5, "R$:", negrito, dy)
        txt(700, Y_LINHAS[10] + 6, _dinheiro(dados.get("total_geral")),
            normal, dy)

        # ---- rodape ----
        # VENDEDOR sai VAZIO: no papel de verdade ele e do vendedor que
        # atendeu, e a FIA nao vende. A primeira versao punha 'FIA' ali.
        txt(47, Y_LINHAS[11] + 12, "VENDEDOR:", negrito, dy)
        txt(588, Y_LINHAS[11] + 9, "NOME DO RECEBEDOR:", negrito, dy)
        for i, l in enumerate(AVISO):
            txt(333, Y_LINHAS[11] + 6 + i * 14, l, normal, dy)

    # ---- o estoque, uma vez so, embaixo das duas vias ----
    if estoque:
        txt(360, Y_ESTOQUE_TITULO, "ESTOQUE", negrito)
        txt(X_ESTOQUE_CHAPA, Y_ESTOQUE_CABECA, "CHAPA", miudo)
        txt(X_ESTOQUE_QTD, Y_ESTOQUE_CABECA, "QTD", miudo)
        linha(X_ESTOQUE_ESQ, Y_ESTOQUE_LINHA, X_ESTOQUE_DIR, Y_ESTOQUE_LINHA)
        for i, (nome, saldo) in enumerate(estoque):
            y = Y_ESTOQUE_PRIMEIRA + i * PASSO_ESTOQUE
            txt(X_ESTOQUE_CHAPA, y, nome, miudo)
            txt(X_ESTOQUE_QTD, y, _inteiro(saldo), miudo)

    return im


def estoque_da_os(numero, con=None):
    """
    [(nome_da_chapa, saldo)] das chapas que ESTA OS usou.

    So as dela, e nao o estoque inteiro do cliente: o papel diz 'voce
    gastou isto, sobrou aquilo'. A SOLIDA tem oito chapas cadastradas e o
    F12 da OS 19605 mostrou duas - as duas que aquela OS gastou.

    O saldo e o de AGORA, lido da CHA, e nao o de quando a OS foi aberta.
    """
    from .gerempre import conectar

    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT OSESP1, OSESP2, OSESP3, OSESP4, OSECL FROM OS "
                    "WHERE OSCOD = ?", (numero,))
        linha = cur.fetchone()
        if not linha:
            return []
        dono = linha[4]
        codigos = []
        for c in linha[:4]:
            if c and c not in codigos:
                codigos.append(c)

        saldos = []
        for codigo in codigos:
            cur.execute("SELECT CHANOM, CHAQTD FROM CHA "
                        "WHERE CHACOD = ? AND CHACLI = ?", (codigo, dono))
            r = cur.fetchone()
            if r:
                saldos.append(((r[0] or "").strip(), r[1]))
        return saldos
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def folha_do_protocolo(numero, con=None, dpi=DPI):
    """O protocolo da OS 'numero', ou None se ela nao existir."""
    from .gerempre import dados_da_os
    dados = dados_da_os(numero, con=con)
    if not dados:
        return None
    return folha(dados, estoque=estoque_da_os(numero, con=con), dpi=dpi)


def imprimir_protocolo(numero, con=None, impressora=None, dpi=DPI):
    """
    Tira o protocolo da OS na impressora. Devolve a impressora usada.

    Uma folha so, com as duas vias e o estoque - nao e frente e verso.
    Levanta se a OS nao existir; quem chama trata, e sem segurar a chapa:
    quando isto roda, a chapa ja esta gravada e a prova ja saiu.
    """
    import shutil
    import tempfile

    from .ghostscript import enviar_para_impressora

    imagem = folha_do_protocolo(numero, con=con, dpi=dpi)
    if imagem is None:
        raise ValueError("a OS %s nao existe" % numero)

    pasta = tempfile.mkdtemp(prefix="_protocolo_")
    try:
        caminho = os.path.join(pasta, "protocolo_%s.pdf" % numero)
        imagem.save(caminho, "PDF", resolution=dpi)
        alvo = impressora or IMPRESSORA
        enviar_para_impressora(caminho, alvo, duplex=False)
        return alvo
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
