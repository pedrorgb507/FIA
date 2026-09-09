# -*- coding: utf-8 -*-
"""
A prova impressa.

Por que nao mandar o PDF direto para a impressora:
o -dFitPage do Ghostscript 10.03.1 quebra quando precisa GIRAR a pagina
para encaixar (arte deitada indo para folha em pe). Como a chapa e
510x400 mm deitada e a impressora esta em A4 em pe, era exatamente o caso.

Solucao: nao usar encaixe nenhum. A prova ja e montada aqui no tamanho
e no sentido exatos da folha:

  1. rasteriza a arte com o Ghostscript (sem encaixe)
  2. monta um A4 EM PE, girando a arte deitada, com margem
  3. escreve a etiqueta do formato numa faixa em branco, fora da arte
  4. intercala a folha da ORDEM DE SERVICO depois de cada pagina
  5. manda tudo num trabalho so, PEDINDO frente e verso

FRENTE E VERSO SE PEDE. A Konica esta configurada em SIMPLEX - foi lido
no driver, Duplex=1 -, e durante um tempo este arquivo dizia o contrario:
supunha duplex e mandava um trabalho por pagina 'para nao ter verso'. Com
a OS entrando, o resultado foi a arte numa folha e a OS em outra.

Agora o -dDuplex vai explicito em toda impressao, ligado ou desligado,
sem depender do que estiver marcado na impressora naquele dia - ela e
compartilhada, e o padrao dela nao e nosso para mudar.

O que vai para a impressora e sempre esse A4 gerado aqui, nunca o arquivo
do cliente. Assim um PDF esquisito nao tem como derrubar a impressao.
"""

import glob
import os
import shutil
import subprocess
import tempfile

from .config import IMPRESSORA, PASTA_CONTROLE
from .ghostscript import GS, enviar_para_impressora

DPI_PROVA = 150
MARGEM_MM = 6
FAIXA_ROTULO_MM = 14        # faixa em branco no alto, so para a etiqueta
ALTURA_TEXTO_MM = 7
A4_MM = (210.0, 297.0)

FONTES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]


def _rasterizar(pdf, pasta, dpi=DPI_PROVA):
    """Uma imagem por pagina. Devolve os caminhos, em ordem."""
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=jpeg", "-dJPEGQ=85",
         "-r%d" % dpi, "-sOutputFile=" + os.path.join(pasta, "p%03d.jpg"), pdf],
        capture_output=True, text=True, timeout=900)
    imagens = sorted(glob.glob(os.path.join(pasta, "p*.jpg")))
    if not imagens:
        raise RuntimeError((r.stderr or "nao consegui rasterizar")[:300])
    return imagens


def _fonte(tamanho):
    """Arial em negrito se existir; senao a fonte embutida do Pillow."""
    from PIL import ImageFont
    for caminho in FONTES:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                pass
    return ImageFont.load_default()


def montar_folha(im, dpi=DPI_PROVA, etiqueta=""):
    """
    Uma folha A4 em pe com a arte centralizada e a etiqueta no canto.

    A arte deitada e girada aqui. Quando ha etiqueta, o alto da folha
    ganha uma faixa em branco e a arte desce para caber embaixo dela:
    o texto nunca cai por cima do desenho.
    """
    from PIL import Image, ImageDraw

    def px(mm):
        return int(round(mm / 25.4 * dpi))

    faixa = px(FAIXA_ROTULO_MM) if etiqueta else 0
    if im.width > im.height:
        im = im.rotate(90, expand=True)          # deitada -> cabe em pe

    folha = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")
    util = (folha.width - 2 * px(MARGEM_MM),
            folha.height - 2 * px(MARGEM_MM) - faixa)
    escala = min(util[0] / im.width, util[1] / im.height)
    im = im.resize((max(1, int(im.width * escala)),
                    max(1, int(im.height * escala))), Image.LANCZOS)
    folha.paste(im, ((folha.width - im.width) // 2,
                     px(MARGEM_MM) + faixa + (util[1] - im.height) // 2))

    if etiqueta:
        ImageDraw.Draw(folha).text(
            (px(MARGEM_MM), px(MARGEM_MM)), etiqueta,
            fill="black", font=_fonte(px(ALTURA_TEXTO_MM)))
    return folha


def _salvar(folhas, destino, dpi=DPI_PROVA):
    """Grava as folhas prontas num PDF, uma pagina cada."""
    folhas[0].save(destino, "PDF", resolution=dpi, save_all=True,
                   append_images=folhas[1:])
    return destino


def _montar_a4(imagens, destino, dpi=DPI_PROVA, etiquetas=None):
    """
    Monta as imagens em folhas A4 EM PE, centralizadas e com margem.

    A folha e sempre retrato porque e assim que a impressora esta
    configurada: mandar uma pagina deitada obrigaria a impressora a girar,
    que e onde o Ghostscript quebra. Arte deitada e girada aqui mesmo.

    etiquetas: um texto por pagina, escrito numa faixa em branco no alto
    da folha. A arte e empurrada para baixo dessa faixa, entao o texto
    nunca cai por cima do desenho.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    etiquetas = etiquetas or []
    folhas = [montar_folha(Image.open(c).convert("RGB"), dpi,
                           etiquetas[i] if i < len(etiquetas) else "")
              for i, c in enumerate(imagens)]

    folhas[0].save(destino, "PDF", resolution=dpi, save_all=True,
                   append_images=folhas[1:])
    return destino


def imprimir(pdf, impressora=None, etiquetas=None, verso=None):
    """
    Imprime a prova: uma folha A4 por pagina da arte.

    etiquetas: texto do formato por pagina ("SOLIDA F4", "SOLIDA F2").
    verso: uma folha ja pronta (imagem do Pillow) para sair no VERSO de
           cada folha de arte - a ORDEM DE SERVICO do GEREMPRE.

    Devolve (impressora, quantidade_de_folhas).

    COM VERSO a folha da OS entra INTERCALADA, uma depois de cada pagina
    da arte, e o trabalho vai em frente e verso:

        arte p1 | OS | arte p2 | OS  ->  duas folhas, cada uma com a arte
                                         na frente e a OS no verso

    Assim um arquivo de frente e verso rende duas folhas completas, e nao
    uma folha de arte solta com a OS do outro lado da errada.

    O frente e verso e PEDIDO ao imprimir (-dDuplex), e nao herdado da
    impressora. A Konica esta em simplex: durante um tempo o programa
    supos o contrario e a OS saia numa segunda folha.

    SEM VERSO vai tudo num trabalho so, em simplex - uma folha por
    pagina, so na frente, como sempre saiu.
    """
    alvo = impressora or IMPRESSORA
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="prova_", dir=PASTA_CONTROLE)
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None

        imagens = _rasterizar(pdf, tmp)
        etiquetas = etiquetas or []
        folhas = []
        for i, imagem in enumerate(imagens):
            folhas.append(montar_folha(
                Image.open(imagem).convert("RGB"), DPI_PROVA,
                etiquetas[i] if i < len(etiquetas) else ""))
            if verso is not None:
                folhas.append(verso)

        enviar_para_impressora(_salvar(folhas, os.path.join(tmp, "prova.pdf")),
                               alvo, duplex=verso is not None)
        return alvo, len(imagens)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
