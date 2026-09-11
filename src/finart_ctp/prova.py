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
import io
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

from .config import IMPRESSORA, PASTA_CONTROLE
from .ghostscript import GS, enviar_para_impressora

# O livro de quem ja imprimiu. Mora na PASTA_CONTROLE, no disco local,
# junto com o registro de chapas - e memoria da maquina, nao da rede.
ARQUIVO_IMPRESSOS = "_impressos.json"

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


class JaImprimiu(Exception):
    """Esta prova ja saiu. Levantada pela trava de copia unica."""


def _livro_de_impressao():
    """O que ja foi impresso: {chave: {quando, folhas, alvo}}."""
    caminho = os.path.join(PASTA_CONTROLE, ARQUIVO_IMPRESSOS)
    try:
        with io.open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return {}


def _anotar_impressao(chave, alvo, folhas):
    """
    Anota que ESTA prova saiu. Grava na hora, e nao no fim do processo.

    Gravar depois foi o defeito das duas vezes: o que vem depois pode
    falhar, e ai o trabalho e refeito - com a impressao junto.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    livro = _livro_de_impressao()
    livro[chave] = {"quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "folhas": folhas, "impressora": alvo}
    caminho = os.path.join(PASTA_CONTROLE, ARQUIVO_IMPRESSOS)
    with io.open(caminho, "w", encoding="utf-8") as f:
        f.write(json.dumps(livro, ensure_ascii=False, indent=1))


def ja_imprimiu(pdf, verso=None):
    """O que ficou anotado sobre esta prova, ou None."""
    return _livro_de_impressao().get(_chave_da_prova(pdf, verso))


def _chave_da_prova(pdf, verso=None):
    """
    A identidade de UMA prova: o arquivo, e a OS que vai no verso.

    A OS entra na chave porque a MESMA arte pode sair de novo para outra
    OS - e ali e prova nova, legitima. O que nao pode e a mesma arte
    sair duas vezes para a mesma OS.
    """
    from .utils import chave_arquivo
    try:
        base = chave_arquivo(pdf)
    except OSError:
        base = os.path.basename(pdf)
    return "%s|verso:%s" % (base, getattr(verso, "_os_numero", "") or "")


def imprimir(pdf, impressora=None, etiquetas=None, verso=None,
             copias=1, de_novo=False, origem=None):
    """
    Imprime a prova: uma folha A4 por pagina da arte.

    etiquetas: texto do formato por pagina ("SOLIDA F4", "SOLIDA F2").
    verso: uma folha ja pronta (imagem do Pillow) para sair no VERSO de
           cada folha de arte - a ORDEM DE SERVICO do GEREMPRE.
    copias: quantas vezes o trabalho vai para a impressora. UMA, sempre,
            a menos que alguem peca mais.
    de_novo: reimprimir algo que JA SAIU. So a pedido de gente.
    origem: o arquivo que IDENTIFICA a prova, quando nao e o 'pdf'. Na
            VOPRIX o 'pdf' e um temporario que a Corel gera de novo a
            cada passada - tamanho e data mudam, e a trava de copia
            unica nao o reconheceria. O .cdr original e o que nao muda.

    Devolve (impressora, quantidade_de_folhas).

    TRAVA DE COPIA UNICA
    --------------------
    Uma prova sai UMA VEZ. Pedida de novo sem 'de_novo=True', esta funcao
    levanta JaImprimiu e NAO manda nada para a impressora.

    Isso nao e zelo: em 10/09/2026 o mesmo trabalho saiu em papel duas
    vezes, por dois defeitos diferentes - o '02020 CHAPA ZIMI' do EMPORIO
    e o flyer da AMERICA. Os dois tinham a mesma forma: alguma coisa
    falhava DEPOIS da impressao, o arquivo nao era dado por feito, e o
    vigia refazia tudo na volta seguinte. De cinco em cinco segundos, ou
    de cinco em cinco minutos, saindo papel.

    Consertar cada laco conserta um laco. A trava aqui protege de TODOS:
    quem imprime passa por esta porta, e esta porta so deixa passar uma
    vez. Os consertos de cada laco continuam valendo - esta e a rede
    embaixo deles.

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
    chave = _chave_da_prova(origem or pdf, verso)
    anotado = _livro_de_impressao().get(chave)
    if anotado and not de_novo:
        raise JaImprimiu(
            "'%s' ja foi impresso em %s (%s folha(s)). Nao imprimi de novo. "
            "Para reimprimir de proposito, de_novo=True"
            % (os.path.basename(pdf), anotado.get("quando", "antes"),
               anotado.get("folhas", "?")))

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

        pronto = _salvar(folhas, os.path.join(tmp, "prova.pdf"))
        for _ in range(max(1, int(copias))):
            enviar_para_impressora(pronto, alvo, duplex=verso is not None)

        # ANOTA AGORA, com o papel ja a caminho. Se anotasse depois de
        # voltar para quem chamou, um tropeco la em cima faria a prova
        # sair de novo - que e exatamente o que ja aconteceu duas vezes.
        _anotar_impressao(chave, alvo, len(imagens))
        return alvo, len(imagens)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
