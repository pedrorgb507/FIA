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

DE ONDE VEIO O DESENHO. Do proprio GEREMPRE: o U:\ZAP PROT ENTREGA.rpf e
um protocolo RENDERIZADO DE VERDADE - a OS 16577, ZAP CARTOES,
30/04/2026 - guardado no formato RLGraphicStorage do ReportBuilder. Dele
sairam os 104 campos com POSICAO EXATA, e nao um layout parecido feito de
memoria. As coordenadas abaixo sao as de la, em unidades de 96 dpi, que
e como o ReportBuilder rendeu.

DUAS VIAS NA MESMA FOLHA. O relatorio repete tudo 467 unidades abaixo -
a via do cliente e a da casa, para destacar. Aqui e igual.

MOSTRA DINHEIRO, e e de proposito - ao contrario da folha da OS, que e a
via de producao e nao mostra. Este papel e do cliente: e o recibo.
"""

import os

from .config import IMPRESSORA
from .os_impressa import A4_MM, DPI, _data, _fonte, _inteiro

# As coordenadas do .rpf estao nesta escala. O ReportBuilder rendeu a
# folha A4 em 96 dpi: 210 mm dao 794 unidades, e os campos vao de x=43
# ate x=726, que sao margens de 11 e 18 mm. Bate.
DPI_RPF = 96.0

# Quanto a segunda via fica abaixo da primeira, nas unidades do .rpf.
SEGUNDA_VIA = 467

# Texto fixo, lido do proprio relatorio - nao inventado.
TELEFONE = "Telefone: (62) 3988-7072 / 3988-7052"
EMAIL = "finartdigitalgo@gmail.com"
AVISO = ["Solicitamos que todos os materiais ",
         "sejam revisados antes de serem ",
         "confeccionados para evitarmos ",
         "reimpressões futuras."]

# (x, y) de cada rotulo fixo, na primeira via.
ROTULOS = [
    (466, 80, "PROTOCOLO DE ENTREGA", True),
    (49, 126, TELEFONE, False),
    (465, 126, EMAIL, False),
    (43, 153, "CLIENTE:", True),
    (363, 153, "CONTATO:", True),
    (543, 153, "DATA DE ENTREGA:", True),
    (43, 174, "ENDEREÇO:", True),
    (528, 374, "TOTAL GERAL", True),
    (636, 374, "R$:", True),
    (588, 399, "NOME DO RECEBEDOR:", True),
    (47, 402, "VENDEDOR: ", True),
]

# Os quatro blocos de servico. Cada um ocupa duas linhas.
BLOCOS_Y = [(199, 221), (243, 265), (287, 308), (330, 352)]

X_PRODUTO_ROTULO = 43
X_PRODUTO = 117
X_UNIT_ROTULO = 579
X_UNIT = 632
X_TOT_ROTULO = 669
X_TOT = 720
X_TITULO_ROTULO = 43
X_TITULO = 118
X_OBS_ROTULO = 419
X_OBS = 454

X_CLIENTE = 118
X_CONTATO = 440
X_ENTREGA = 681
X_ENDERECO = 117
X_OS = 683
Y_OS = 125
X_AVISO = 333
Y_AVISO = 398
PASSO_AVISO = 15
X_TOTAL = 694

CORPO_PX = 11          # altura da letra no .rpf, em 96 dpi
TITULO_PX = 15


def _dinheiro(v):
    """35.0 -> '35,00'. O papel e brasileiro."""
    try:
        return ("%.2f" % float(v or 0)).replace(".", ",")
    except (TypeError, ValueError):
        return "0,00"


def _produto(item):
    """
    '1 - SOLIDA FT4 510 X 400 - F4 - 1 X 0'

    Lido do proprio relatorio: vaga, material, medida, montagem e as
    cores de frente e verso, nessa ordem.
    """
    return "%d - %s %s X %s - %s - %s X %s" % (
        item["vaga"], item["material"],
        _inteiro(item["alt"]), _inteiro(item["lar"]),
        item["montagem"], _inteiro(item["frente"]), _inteiro(item["verso"]))


def _cortar(tinta, texto, fonte, largura_px):
    """
    O texto que cabe em 'largura_px', com reticencias se sobrar.

    O nome do cliente no GEREMPRE vem inteiro - 'SOLIDA GRAFICA (SOLIDA
    GRAFICA EDITORA LTDA)' - e a coluna acaba onde comeca o CONTATO. Sem
    corte, um campo escreve por cima do rotulo do outro e o papel fica
    ilegivel justo na linha que o cliente le primeiro.
    """
    if not texto:
        return ""
    texto = str(texto)
    if tinta.textlength(texto, font=fonte) <= largura_px:
        return texto
    while texto and tinta.textlength(texto + "...", font=fonte) > largura_px:
        texto = texto[:-1]
    return (texto + "...") if texto else ""


def folha(dados, dpi=DPI):
    """
    A folha A4 em pe do protocolo, com as DUAS vias. Imagem do Pillow.

    'dados' e o que gerempre.dados_da_os() devolve - lido do banco depois
    de gravado, e nao o que se pretendia gravar. Campo que nao entrou sai
    em branco no papel, e alguem ve.
    """
    from PIL import Image, ImageDraw

    escala = dpi / DPI_RPF
    larg = int(round(A4_MM[0] / 25.4 * dpi))
    alt = int(round(A4_MM[1] / 25.4 * dpi))
    im = Image.new("RGB", (larg, alt), "white")
    tinta = ImageDraw.Draw(im)

    normal = _fonte(int(round(CORPO_PX * escala)))
    negrito = _fonte(int(round(CORPO_PX * escala)), negrito=True)
    titulo = _fonte(int(round(TITULO_PX * escala)), negrito=True)

    def escrever(x, y, texto, fonte=None, desloca=0):
        if texto is None or texto == "":
            return
        tinta.text((x * escala, (y + desloca) * escala), str(texto),
                   font=fonte or normal, fill="black")

    itens = {i["vaga"]: i for i in dados.get("itens") or []}

    for desloca in (0, SEGUNDA_VIA):
        for x, y, texto, forte in ROTULOS:
            escrever(x, y, texto,
                     titulo if texto == "PROTOCOLO DE ENTREGA"
                     else (negrito if forte else normal), desloca)

        escrever(X_OS, Y_OS, "OS: %s" % dados.get("numero"), negrito, desloca)
        # cada um cabe ate onde comeca o rotulo seguinte
        escrever(X_CLIENTE, 153,
                 _cortar(tinta, dados.get("cliente"), normal,
                         (363 - X_CLIENTE - 4) * escala), normal, desloca)
        escrever(X_CONTATO, 153,
                 _cortar(tinta, dados.get("contato"), normal,
                         (543 - X_CONTATO - 4) * escala), normal, desloca)
        escrever(X_ENTREGA, 153, _data(dados.get("entrega")), normal, desloca)
        escrever(X_ENDERECO, 174,
                 _cortar(tinta, dados.get("endereco"), normal,
                         (740 - X_ENDERECO) * escala), normal, desloca)

        # Os quatro blocos SEMPRE saem, cheios ou vazios - e assim que o
        # relatorio do GEREMPRE faz. Vaga vazia mostra os rotulos e zero.
        for n, (y_prod, y_tit) in enumerate(BLOCOS_Y, start=1):
            item = itens.get(n)
            escrever(X_PRODUTO_ROTULO, y_prod, "PRODUTO:", negrito, desloca)
            escrever(X_UNIT_ROTULO, y_prod, "UNIT.", negrito, desloca)
            escrever(X_TOT_ROTULO, y_prod, "TOT.", negrito, desloca)
            escrever(X_TITULO_ROTULO, y_tit, "TÍTULO:", negrito, desloca)
            escrever(X_OBS_ROTULO, y_tit, "OBS:", negrito, desloca)
            if item:
                escrever(X_PRODUTO, y_prod,
                         _cortar(tinta, _produto(item), normal,
                                 (X_UNIT_ROTULO - X_PRODUTO - 4) * escala),
                         normal, desloca)
                escrever(X_TITULO, y_tit,
                         _cortar(tinta, item["titulo"], normal,
                                 (X_OBS_ROTULO - X_TITULO - 4) * escala),
                         normal, desloca)
                escrever(X_OBS, y_tit,
                         _cortar(tinta, item["obs"], normal,
                                 (X_UNIT_ROTULO - X_OBS - 4) * escala),
                         normal, desloca)
            escrever(X_UNIT, y_prod,
                     _dinheiro(item["unitario"] if item else 0), normal,
                     desloca)
            escrever(X_TOT, y_prod,
                     _dinheiro(item["total"] if item else 0), normal, desloca)

        escrever(X_TOTAL, 374, _dinheiro(dados.get("total_geral")), negrito,
                 desloca)
        escrever(47 + 75, 402, dados.get("responsavel"), normal, desloca)

        for i, linha in enumerate(AVISO):
            escrever(X_AVISO, Y_AVISO + i * PASSO_AVISO, linha, normal,
                     desloca)

    return im


def folha_do_protocolo(numero, con=None, dpi=DPI):
    """O protocolo da OS 'numero', ou None se ela nao existir."""
    from .gerempre import dados_da_os
    dados = dados_da_os(numero, con=con)
    if not dados:
        return None
    return folha(dados, dpi=dpi)


def imprimir_protocolo(numero, con=None, impressora=None, dpi=DPI):
    """
    Tira o protocolo da OS na impressora. Devolve a impressora usada.

    Uma folha so, com as duas vias - nao e frente e verso. Levanta se a
    OS nao existir; quem chama trata, e sem segurar a chapa: quando isto
    roda, a chapa ja esta gravada e a prova ja saiu.
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
