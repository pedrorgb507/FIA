# -*- coding: utf-8 -*-
r"""
Achata SO A ARTE em imagem, deixando marca de corte e registro em vetor.

    python ferramentas\achatar_so_a_arte.py <arquivo.cdr> [dpi]

Pedido do operador em 18/09/2026: "converta em imagem em 800 dpi, mas
nao converta as cruz de corte nem de registro, somente o que for da
arte".

POR QUE ISSO E DIFERENTE DO ACHATAMENTO DA VOPRIX. La tudo vira imagem,
e e o que se quer: o arquivo inteiro e arte. Aqui a pagina JA E a chapa
montada - tem linha de corte, cruz de registro e escala de cor - e essas
tres coisas nao podem virar pixel:

  - a linha de corte e lida pela guilhotina, e traco fino rasterizado a
    800 dpi vira borda cinza de meio pixel;
  - a cruz de registro existe para casar as quatro chapas. Ela e
    desenhada na COR DE REGISTRO, que imprime em todas - virando imagem
    CMYK, ela deixa de ser cor de registro e passa a ser quatro objetos
    separados, um por chapa, que e exatamente o que ela existe para
    detectar;
  - a escala de cor e referencia de densidade. Reamostrada, deixa de
    medir o que devia medir.

COMO SE SEPARA UMA COISA DA OUTRA

Pela COR DE REGISTRO. Toda marca a usa e nenhuma arte usa - e isso nao e
convencao nossa, e o que a cor de registro significa. Lido no
'Luva_Produto_24,0x9,0_4_0_Apoquel.cdr':

    grupo 4,1 x 127,8   REGCOLOR   a escala de cor (55 formas)
    retangulo 321 x 288,7  contorno REGCOLOR   a linha de corte
    dois tracos 3,5 x 6,2  contorno REGCOLOR   as marcas laterais
    grupo 285 x 250,3   sem registro           A ARTE

A regra, e ela desce sozinha na arvore:

    a forma usa cor de registro?           fica em vetor, inteira
    algum descendente dela usa?            desce e decide filho a filho
    ninguem ali usa?                       vira imagem

O primeiro caso e o que impede a escala de cor de ser partida em 55
imagens: o grupo dela PROPRIO e cor de registro, entao ele fica inteiro.

O ORIGINAL NUNCA E ABERTO - trabalha-se numa copia. Achatar e
irreversivel, e .cdr salvo como bitmap perde o texto para sempre.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from finart_ctp import corel                                    # noqa: E402
from finart_ctp.ghostscript import (cobertura_por_pagina,       # noqa: E402
                                    cor_sobreviveu)

MM = 25.4          # o Corel devolve em polegadas
DPI = corel.DPI_DO_ACHATADO      # 900, o padrao da casa


def _e_registro(cor):
    """
    A cor e a COR DE REGISTRO?

    Lida pelo texto que o Corel devolve - 'REGCOLOR,USER,...'. O
    ToString e o que ha de estavel aqui: a constante de tipo muda de
    nome entre versoes, e o prefixo nao.
    """
    try:
        return cor.ToString().upper().startswith("REGCOLOR")
    except Exception:
        return False


def usa_registro(forma):
    """A PROPRIA forma e desenhada em cor de registro?"""
    try:
        f = forma.Fill
        if f.Type == 1 and _e_registro(f.UniformColor):
            return True
    except Exception:
        pass
    try:
        o = forma.Outline
        if o.Width is not None and _e_registro(o.Color):
            return True
    except Exception:
        pass
    return False


def tem_registro_dentro(forma, fundo=0):
    """Ela, ou qualquer descendente dela, usa cor de registro?"""
    if usa_registro(forma):
        return True
    if fundo > 6:
        return False
    try:
        filhos = forma.Shapes
        total = filhos.Count
    except Exception:
        return False
    for i in range(1, total + 1):
        try:
            if tem_registro_dentro(filhos.Item(i), fundo + 1):
                return True
        except Exception:
            continue
    return False


def escolher(forma, marcas, arte, fundo=0):
    """Separa em duas listas: o que fica em vetor e o que vira imagem."""
    if usa_registro(forma):
        marcas.append(forma)
        return
    if tem_registro_dentro(forma):
        try:
            filhos = forma.Shapes
            total = filhos.Count
        except Exception:
            total = 0
        if total and fundo < 6:
            for i in range(1, total + 1):
                escolher(filhos.Item(i), marcas, arte, fundo + 1)
            return
        marcas.append(forma)
        return
    arte.append(forma)


def medida(forma):
    return ("%.1f x %.1f mm em (%.1f, %.1f)"
            % (forma.SizeWidth * MM, forma.SizeHeight * MM,
               forma.PositionX * MM, forma.PositionY * MM))


def achatar_so_a_arte(cdr, destino, dpi=DPI):
    """Devolve (quantas_viraram_imagem, quantas_ficaram_em_vetor)."""
    cdr = os.path.abspath(cdr)
    destino = os.path.abspath(destino)

    app = corel._aplicacao()
    if corel._documento_aberto(app, cdr) is not None:
        raise corel.ArquivoEmUso("'%s' esta aberto no CorelDRAW"
                                 % os.path.basename(cdr))

    pasta = tempfile.mkdtemp(prefix="so_a_arte_")
    copia = os.path.join(pasta, os.path.basename(cdr))
    shutil.copy2(cdr, copia)

    doc = app.OpenDocument(copia)
    try:
        corel.carregar_predefinicao(doc)
        faltaram = corel.ajustar_pdf(doc)
        criticos = [f for f in faltaram if f.startswith("Downsample")]
        if criticos:
            raise RuntimeError("o CorelDRAW nao aceitou desligar a "
                               "reamostragem (%s)" % ", ".join(criticos))

        virou, ficou = 0, 0
        for i in range(1, doc.Pages.Count + 1):
            pagina = doc.Pages.Item(i)
            pagina.Activate()
            marcas, arte = [], []
            for j in range(1, pagina.Layers.Count + 1):
                camada = pagina.Layers.Item(j)
                if not camada.Printable:
                    continue
                for k in range(1, camada.Shapes.Count + 1):
                    escolher(camada.Shapes.Item(k), marcas, arte)

            print("  pagina %d: %d forma(s) de arte -> UMA imagem; "
                  "%d de marca ficam em vetor" % (i, len(arte), len(marcas)))
            for f in marcas[:8]:
                print("     fica: %s" % medida(f))
            if len(marcas) > 8:
                print("     ... e mais %d marca(s)" % (len(marcas) - 8))

            # DE UMA VEZ SO, num ShapeRange.
            #
            # Convertendo forma a forma sairia uma imagem por forma - e o
            # 'O.S 1050 - SEDS FOLDER' da PRIME tem 978 formas de arte.
            # Seriam 978 bitmaps, cada um com sua caixa, no lugar de uma
            # imagem. Alem do peso, e o contrario do que se pediu: "as
            # imagens todas em 1 imagem".
            if arte:
                faixa = app.CreateShapeRange()
                for f in arte:
                    faixa.Add(f)
                # fundo TRANSPARENTE: o bitmap e um retangulo, e opaco
                # ele cobre as marcas que moram dentro da caixa dele -
                # cruz de registro, marca de corte, escala de cor. Ver o
                # comentario em corel.publicar_pdf_achatado.
                imagem = faixa.ConvertToBitmapEx(
                    corel.CDR_IMAGE_CMYK, False, True, dpi,
                    corel.CDR_ANTISERRILHAMENTO, True, False, 95)
                try:
                    imagem.OrderToBack()
                except Exception:
                    pass
                virou += 1
            ficou += len(marcas)

        doc.PublishToPDF(destino)
    finally:
        try:
            doc.Dirty = False
        except Exception:
            pass
        try:
            doc.Close()
        except Exception:
            pass
        shutil.rmtree(pasta, ignore_errors=True)

    if not os.path.exists(destino):
        raise RuntimeError("o CorelDRAW nao gerou o PDF")
    return virou, ficou


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cdr = sys.argv[1]
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else DPI
    base = os.path.splitext(cdr)[0]
    destino = "%s_ARTE EM IMAGEM %ddpi.pdf" % (base, dpi)

    print("origem : %s (%.1f MB)" % (os.path.basename(cdr),
                                     os.path.getsize(cdr) / 1048576.0))
    print("saida  : %s\n" % os.path.basename(destino))

    # a referencia de cor: o mesmo arquivo publicado SEM achatar nada
    ref = os.path.join(tempfile.mkdtemp(), "vetor.pdf")
    print("publicando o vetor, para ter com que comparar...")
    corel.publicar_pdf(cdr, ref)
    antes = cobertura_por_pagina(ref, sem_icc=True)

    print("\nachatando so a arte, a %d dpi..." % dpi)
    virou, ficou = achatar_so_a_arte(cdr, destino, dpi)

    depois = cobertura_por_pagina(destino, sem_icc=True)
    print("\n%d forma(s) viraram imagem, %d ficaram em vetor" % (virou, ficou))
    print("PDF: %.1f MB\n" % (os.path.getsize(destino) / 1048576.0))

    print("  %-5s %9s %9s %9s" % ("", "vetor", "achatado", "difer."))
    for i, (a, d) in enumerate(zip(antes, depois)):
        for t in "CMYK":
            print("  p%d %s  %9.4f %9.4f %+9.4f" % (i + 1, t, a[t], d[t],
                                                    d[t] - a[t]))
        bate, recado = cor_sobreviveu(a, d)
        print("   -> %s\n" % recado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
