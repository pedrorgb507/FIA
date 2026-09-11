# -*- coding: utf-8 -*-
"""A sangria inventada: o que ela nunca pode fazer.

Tres regras, e as tres ja foram quebradas por mim antes de virarem teste:

  1. nao amplia a arte - o corte continua do tamanho que foi pedido;
  2. nao rasteriza e nao mexe na cor - CMYK entra CMYK e sai CMYK,
     porque re-separar transforma um preto de K sozinho nas quatro
     tintas e o texto sai com quatro chapas empilhadas;
  3. nao inventa traco - fio parado na linha de corte chama gente.

O caso de verdade - o flyer 15x21 com a sangria do designer - e arte de
cliente e nao vai para o git. Por isso os PDF sinteticos aqui embaixo
guardam as regras, e o teste do flyer roda so nesta maquina, quando o
arquivo esta na pasta.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ferramentas"))

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw          # noqa: E402

import sangrar                            # noqa: E402

MM, PT = 25.4, 72.0
DPI = 300
S = int(round(3.0 / MM * DPI))            # 3 mm em pixels


# --------------------------------------------------------------------------
# PDF de mentira, para as regras poderem morar no git sem arte de cliente
# --------------------------------------------------------------------------

def _pdf(caminho, desenho, larg_mm=100.0, alt_mm=150.0):
    """Um PDF de uma pagina, PELADO (TrimBox = MediaBox), com este desenho."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject

    L, A = larg_mm / MM * PT, alt_mm / MM * PT
    w = PdfWriter()
    p = w.add_blank_page(width=L, height=A)
    fluxo = DecodedStreamObject()
    fluxo.set_data(desenho(L, A))
    p.replace_contents(fluxo)
    cx = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
    p.trimbox, p.bleedbox, p.cropbox = cx, cx, cx
    with open(caminho, "wb") as f:
        w.write(f)
    return caminho


def _pdf2(caminho, desenho1, desenho2, larg_mm=100.0, alt_mm=150.0):
    """Um PDF de DUAS paginas, pelado - a frente e o verso no mesmo."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject

    L, A = larg_mm / MM * PT, alt_mm / MM * PT
    w = PdfWriter()
    for desenho in (desenho1, desenho2):
        p = w.add_blank_page(width=L, height=A)
        fluxo = DecodedStreamObject()
        fluxo.set_data(desenho(L, A))
        p.replace_contents(fluxo)
        cx = ArrayObject([FloatObject(v) for v in (0, 0, L, A)])
        p.trimbox, p.bleedbox, p.cropbox = cx, cx, cx
    with open(caminho, "wb") as f:
        w.write(f)
    return caminho


def _chapado(L, A):
    """Um CMYK chapado cobrindo a pagina toda."""
    return ("0.10 0.90 0.80 0.05 k 0 0 %.2f %.2f re f\n" % (L, A)).encode()


def _com_moldura(L, A):
    """Fundo claro e um fio preto correndo NA linha de corte."""
    t = 1.0 / MM * PT                     # 1 mm
    return (("0 0 0 0.06 k 0 0 %.2f %.2f re f\n" % (L, A))
            + ("0 0 0 1 K %.3f w %.2f %.2f %.2f %.2f re S\n"
               % (t, t / 2, t / 2, L - t, A - t))
            + ("0.9 0.2 0.1 0 k %.2f %.2f 100 100 re f\n"
               % (L / 3, A / 3))).encode()


def _quase_branco(L, A):
    """Arte que acaba em branco: so um bloco no meio."""
    return ("0.9 0.2 0.1 0 k %.2f %.2f 60 60 re f\n"
            % (L / 2 - 30, A / 2 - 30)).encode()


def _conteudo(pdf, pagina=1):
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    leitor = PdfReader(pdf)
    return ContentStream(leitor.pages[pagina - 1].get_contents(),
                         leitor).get_data()


def _conta(dados, padrao):
    return len(re.findall(padrao, dados))


# --------------------------------------------------------------------------
# regra 1: nao amplia
# --------------------------------------------------------------------------

def test_o_corte_nao_muda_de_tamanho(tmp_path):
    """A regra que quase todo mundo quebra: sangria nao e ampliar."""
    from pypdf import PdfReader
    entrada = _pdf(str(tmp_path / "e.pdf"), _chapado, 100.0, 150.0)
    saida = str(tmp_path / "s.pdf")
    r = sangrar.sangrar_pdf(entrada, saida, 3.0)

    pag = PdfReader(saida).pages[0]
    corte_l = float(pag.trimbox.width) / PT * MM
    corte_a = float(pag.trimbox.height) / PT * MM
    assert abs(corte_l - 100.0) < 0.01, corte_l
    assert abs(corte_a - 150.0) < 0.01, corte_a
    # o papel cresceu 3 mm de cada lado, e so ele
    assert abs(float(pag.mediabox.width) / PT * MM - 106.0) < 0.01
    assert abs(float(pag.mediabox.height) / PT * MM - 156.0) < 0.01
    # e o corte ficou 3 mm para dentro, em todos os lados
    for a, b in ((pag.trimbox.left, pag.mediabox.left),
                 (pag.trimbox.bottom, pag.mediabox.bottom),
                 (pag.mediabox.right, pag.trimbox.right),
                 (pag.mediabox.top, pag.trimbox.top)):
        assert abs((float(a) - float(b)) / PT * MM - 3.0) < 0.01
    assert r["paginas"][0]["corte_mm"][0] == pytest.approx(100.0, abs=0.01)


def test_ja_tem_sangria_reconhece_os_dois_casos(tmp_path):
    pelado = _pdf(str(tmp_path / "p.pdf"), _chapado)
    tem, mm = sangrar.ja_tem_sangria(pelado)
    assert not tem and abs(mm) < 0.01

    sangrado = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(pelado, sangrado, 3.0)
    tem, mm = sangrar.ja_tem_sangria(sangrado)
    assert tem and abs(mm - 3.0) < 0.01


# --------------------------------------------------------------------------
# regra 2: nao rasteriza, nao mexe na cor
# --------------------------------------------------------------------------

def test_cmyk_entra_cmyk_sai(tmp_path):
    """
    Rasterizar a saida jogaria tudo para RGB, e re-separar remisturaria
    o preto de K sozinho nas quatro tintas. O texto preto sairia com
    quatro chapas empilhadas, que qualquer desregistro borra.
    """
    entrada = _pdf(str(tmp_path / "e.pdf"), _com_moldura)
    saida = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(entrada, saida, 3.0)

    antes, depois = _conteudo(entrada), _conteudo(saida)
    cmyk = rb"[\d.]+ [\d.]+ [\d.]+ [\d.]+ [kK][\s]"
    rgb = rb"[\d.]+ [\d.]+ [\d.]+ (?:rg|RG)[\s]"
    assert _conta(antes, cmyk) > 0
    # as nove colocacoes multiplicam os operadores; nenhum vira RGB
    assert _conta(depois, cmyk) >= _conta(antes, cmyk)
    assert _conta(depois, rgb) == 0, "apareceu RGB na saida"


def test_a_saida_nao_e_uma_imagem(tmp_path):
    """Vetor tem de continuar vetor: nada de virar um PNG colado."""
    from pypdf import PdfReader
    entrada = _pdf(str(tmp_path / "e.pdf"), _com_moldura)
    saida = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(entrada, saida, 3.0)

    pag = PdfReader(saida).pages[0]
    xo = pag.get("/Resources", {}).get("/XObject")
    imagens = 0
    if xo:
        alvo = xo.get_object()
        imagens = sum(1 for k in alvo
                      if alvo[k].get_object().get("/Subtype") == "/Image")
    assert imagens == 0, "a saida virou imagem"
    # o pypdf normaliza um operador por linha, entao e 're\nf', nao ' re f'
    dados = _conteudo(saida)
    assert re.search(rb"\bre\s+[fS]\b", dados), "sumiu o desenho vetorial"


def test_o_miolo_nao_e_tocado(tmp_path):
    """A arte dentro do corte tem de sair identica a que entrou."""
    from PIL import ImageChops, ImageStat
    entrada = _pdf(str(tmp_path / "e.pdf"), _com_moldura)
    saida = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(entrada, saida, 3.0)

    a = sangrar.rasterizar(entrada, 1, 150, "TrimBox")
    b = sangrar.rasterizar(saida, 1, 150, "TrimBox")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    erro = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3.0
    assert erro < 1.0, erro


def test_sangria_so_de_papel_nao_reescreve_o_desenho(tmp_path):
    """
    Arte que acaba em branco nos quatro lados: a sangria e papel, e
    papel nao se desenha. So a caixa abre.

    Isto nasceu do cupom da MEGA MOVEIS - 23 MB de desenho. Reescrever
    para colar branco em volta engordava o arquivo de 8,7 para 23,9 MB
    e levava 36 segundos, para nao mudar um pixel.
    """
    entrada = _pdf(str(tmp_path / "e.pdf"), _quase_branco)
    saida = str(tmp_path / "s.pdf")
    r = sangrar.sangrar_pdf(entrada, saida, 3.0)

    assert all(t == "branco" for t, _ in r["paginas"][0]["decisoes"].values())
    # o desenho saiu byte a byte igual: ninguem mexeu nele
    assert _conteudo(saida) == _conteudo(entrada)
    assert os.path.getsize(saida) < os.path.getsize(entrada) * 1.5


# --------------------------------------------------------------------------
# regra 3: nao inventa traco
# --------------------------------------------------------------------------

def test_moldura_na_linha_de_corte_trava(tmp_path):
    """Fio parado no corte: espelhar duplicaria. Tem de chamar gente."""
    entrada = _pdf(str(tmp_path / "e.pdf"), _com_moldura)
    saida = str(tmp_path / "s.pdf")
    r = sangrar.sangrar_pdf(entrada, saida, 3.0)

    olhos = {b for _, b, _ in r["precisa_de_olho"]}
    assert olhos == set(sangrar.BORDAS), olhos
    # mas a sangria SAI - o operador precisa ter o que olhar
    assert os.path.exists(saida)


def test_moldura_fina_tambem_trava():
    """Meio milimetro de fio ja e fio."""
    for espessura_mm in (0.5, 1.0, 2.0):
        art = Image.new("RGB", (900, 1200), (235, 232, 228))
        t = max(1, int(espessura_mm / MM * DPI))
        ImageDraw.Draw(art).rectangle(
            [0, 0, art.size[0] - 1, art.size[1] - 1],
            outline=(20, 20, 20), width=t)
        for borda in sangrar.BORDAS:
            tecnica, porque = sangrar.decidir(art, borda, S)
            assert tecnica == "olho", (espessura_mm, borda, tecnica, porque)


def test_degrade_nao_trava_a_toa():
    """Foto que sangra de verdade: espelha, nao chama gente."""
    art = Image.new("RGB", (900, 1200))
    px = art.load()
    for y in range(1200):
        for x in range(900):
            px[x, y] = (120 + x // 12, 90 + y // 24, 140)
    for borda in sangrar.BORDAS:
        assert sangrar.decidir(art, borda, S)[0] == "espelho"


# --------------------------------------------------------------------------
# imagem solta, fora de PDF
# --------------------------------------------------------------------------

def test_imagem_cmyk_continua_cmyk(tmp_path):
    """Um .convert('RGB') aqui destruiria a separacao do mesmo jeito."""
    art = Image.new("CMYK", (600, 800), (10, 200, 180, 5))
    entrada = str(tmp_path / "e.tif")
    art.save(entrada, dpi=(300, 300))
    saida = str(tmp_path / "s.tif")
    r = sangrar.sangrar_arquivo_de_imagem(entrada, saida, 3.0, dpi=300)

    assert r["modo"] == "CMYK"
    fora = Image.open(saida)
    assert fora.mode == "CMYK"
    assert fora.size == (600 + 2 * S, 800 + 2 * S)
    # a cor da borda e a mesma de dentro, tinta por tinta
    assert fora.getpixel((1, 1)) == (10, 200, 180, 5)


# --------------------------------------------------------------------------
# a montagem sangra sozinha
# --------------------------------------------------------------------------

def test_a_montagem_sangra_sozinha(tmp_path):
    """
    O buraco que isto fecha: montar_bate_vira faz
    'corte_l = sang_l - 2 * SANGRIA', supondo que a peca JA vem
    sangrada. Numa arte pelada a linha de corte cairia 3 mm DENTRO do
    desenho, as marcas sairiam no lugar errado, e nada daria erro.
    """
    import montar_bate_vira as mbv

    pelado = _pdf(str(tmp_path / "p.pdf"), _chapado, 100.0, 150.0)
    saida, relato = mbv._garantir_sangria(pelado, str(tmp_path))

    assert saida != pelado, "nao sangrou"
    assert relato and not relato["ja_vinha"]
    tem, mm = sangrar.ja_tem_sangria(saida)
    assert tem and abs(mm - mbv.SANGRIA) < 0.01
    # e o original ficou intacto
    assert not sangrar.ja_tem_sangria(pelado)[0]


def test_a_montagem_nao_sangra_o_que_ja_vem_sangrado(tmp_path):
    """Sangrar duas vezes engordaria a peca em 6 mm e erraria o corte."""
    import montar_bate_vira as mbv

    pelado = _pdf(str(tmp_path / "p.pdf"), _chapado, 100.0, 150.0)
    sangrado = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(pelado, sangrado, mbv.SANGRIA)

    saida, relato = mbv._garantir_sangria(sangrado, str(tmp_path))
    assert saida == sangrado, "sangrou de novo o que ja estava sangrado"
    assert relato["ja_vinha"]


def test_o_fio_no_corte_sobe_ate_a_montagem(tmp_path):
    """A montagem sai, mas o operador tem de saber onde olhar."""
    import montar_bate_vira as mbv

    entrada = _pdf(str(tmp_path / "e.pdf"), _com_moldura, 100.0, 150.0)
    saida, relato = mbv._garantir_sangria(entrada, str(tmp_path))
    assert os.path.exists(saida)
    bordas = {b for _, b, _ in relato["precisa_de_olho"]}
    assert bordas == set(sangrar.BORDAS), bordas


# --------------------------------------------------------------------------
# a frente e o verso em DOIS arquivos
# --------------------------------------------------------------------------

def test_dois_arquivos_sao_frente_e_verso(tmp_path):
    """
    "quando eu colocar dois arquivos la provavelmente sera frente e
    verso" - o operador, 11/09/2026. E como a CARTA de setembro chega:
    CARTA_FRENTE_SETEMBRO e CARTA_VERSO_SETEMBRO_opcao_2, um arquivo de
    uma pagina cada.

    A ORDEM manda. O 'opcao_2' no nome do verso e a prova de que nome de
    arquivo de cliente nao e lugar de procurar regra.
    """
    import montar_bate_vira as mbv

    f = _pdf(str(tmp_path / "frente.pdf"), _chapado)
    v = _pdf(str(tmp_path / "verso.pdf"), _quase_branco)
    assert mbv._pecas([f, v]) == [(f, 1), (v, 1)]
    # um arquivo de duas paginas continua valendo
    doisp = _pdf2(str(tmp_path / "ambos.pdf"), _chapado, _quase_branco)
    assert mbv._pecas(doisp) == [(doisp, 1), (doisp, 2)]


def test_um_arquivo_de_uma_pagina_so_nao_da_bate_vira(tmp_path):
    """Ate hoje isto lia a pagina 2 de um arquivo que so tinha uma."""
    import montar_bate_vira as mbv

    so_frente = _pdf(str(tmp_path / "f.pdf"), _chapado)
    with pytest.raises(SystemExit) as erro:
        mbv._pecas(so_frente)
    assert "frente E do verso" in str(erro.value)


def test_dois_arquivos_de_varias_paginas_param(tmp_path):
    """Com dois arquivos eu espero um lado em cada. Nao escolho pagina."""
    import montar_bate_vira as mbv

    a = _pdf2(str(tmp_path / "a.pdf"), _chapado, _quase_branco)
    b = _pdf(str(tmp_path / "b.pdf"), _chapado)
    with pytest.raises(SystemExit) as erro:
        mbv._pecas([a, b])
    assert "uma pagina cada" in str(erro.value)


def test_a_sangria_e_a_do_arquivo_nao_a_da_casa(tmp_path):
    """
    O folder do Sesc chega com 2,5 mm: corte 400x300 dentro de um
    BleedBox de 405x305. Com o SANGRIA fixo em 3 a linha de corte sairia
    em 399x299 - 1 mm de erro em cada medida, e nada dava erro.
    """
    import montar_bate_vira as mbv

    pelado = _pdf(str(tmp_path / "p.pdf"), _chapado, 100.0, 150.0)
    dois_e_meio = str(tmp_path / "s.pdf")
    sangrar.sangrar_pdf(pelado, dois_e_meio, 2.5)

    lados = [(dois_e_meio, 1), (dois_e_meio, 1)]
    assert mbv._sangria_das_pecas(lados) == pytest.approx(2.5, abs=0.01)
    assert mbv.SANGRIA == 3.0, "a constante continua sendo o padrao da casa"


def test_sangrias_diferentes_entre_frente_e_verso_param(tmp_path):
    """
    Os dois cortam na mesma grade: com sangrias diferentes, um dos lados
    sai errado, e nao ha escolha que conserte os dois.
    """
    import montar_bate_vira as mbv

    pelado = _pdf(str(tmp_path / "p.pdf"), _chapado, 100.0, 150.0)
    tres = str(tmp_path / "t.pdf")
    meio = str(tmp_path / "m.pdf")
    sangrar.sangrar_pdf(pelado, tres, 3.0)
    sangrar.sangrar_pdf(pelado, meio, 2.5)

    with pytest.raises(SystemExit) as erro:
        mbv._sangria_das_pecas([(tres, 1), (meio, 1)])
    assert "3.00" in str(erro.value) and "2.50" in str(erro.value)


def test_marca_de_corte_no_mediabox_nao_e_sangria(tmp_path):
    """
    A caixa certa e o BLEEDBOX. O CARTA_FRENTE tem MediaBox 233x320 e
    corte 210x297: medido pelo papel daria 11,64 mm de sangria, quando a
    sangria e 3 e o resto e area de marca de corte.

    O erro que isso evitaria e o pior dos dois: um arquivo COM marcas e
    SEM sangria passaria por sangrado.
    """
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject

    L, A = 210.0 / MM * PT, 297.0 / MM * PT
    folga = 11.64 / MM * PT
    caminho = str(tmp_path / "com_marcas.pdf")
    w = PdfWriter()
    p = w.add_blank_page(width=L + 2 * folga, height=A + 2 * folga)
    fluxo = DecodedStreamObject()
    fluxo.set_data(("0.1 0.9 0.8 0.05 k %.2f %.2f %.2f %.2f re f\n"
                    % (folga, folga, L, A)).encode())
    p.replace_contents(fluxo)
    corte = ArrayObject([FloatObject(v) for v in
                         (folga, folga, folga + L, folga + A)])
    p.trimbox, p.bleedbox = corte, corte      # marcas no papel, ZERO sangria
    with open(caminho, "wb") as f:
        w.write(f)

    assert sangrar.sangria_do_arquivo(caminho) == pytest.approx(0.0, abs=0.01)
    assert not sangrar.ja_tem_sangria(caminho)[0]


# --------------------------------------------------------------------------
# o gabarito de verdade
# --------------------------------------------------------------------------

FLYER = os.path.join(os.path.dirname(__file__), "..", "ARQUIVOS TEMP PARA TESTES",
                     "Flyer Semana do Cliente_15x21 (1).pdf")


@pytest.mark.skipif(not os.path.exists(FLYER),
                    reason="arte de cliente; nao vai para o git")
def test_flyer_contra_a_sangria_do_designer(tmp_path):
    """
    O gabarito. O flyer tem 3 mm de sangria feita por gente: joga fora,
    manda a FIA reinventar, e cobra o que importa - onde o designer pos
    TINTA, a FIA nao pode ter deixado PAPEL.

    Comparar a COR com a do designer nao serve, e quase me enganou: na
    borda direita do verso ele desenhou na sangria um verde que nem
    existe dentro do corte, e a diferenca toda estava em tinta que a
    guilhotina come. Fiapo branco, sim, aparece no impresso.
    """
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, ContentStream,
                               DecodedStreamObject, FloatObject)

    pelado = str(tmp_path / "pelado.pdf")
    w = PdfWriter(clone_from=FLYER)
    for pag in w.pages:
        corte = pag.trimbox
        dados = ContentStream(pag.get_contents(), w).get_data()
        cab = ("q %.4f %.4f %.4f %.4f re W n\n"
               % (float(corte.left), float(corte.bottom),
                  float(corte.width), float(corte.height))).encode("latin-1")
        fluxo = DecodedStreamObject()
        fluxo.set_data(cab + dados + b"\nQ\n")
        pag.replace_contents(fluxo)
        cx = ArrayObject([FloatObject(v) for v in
                          (corte.left, corte.bottom, corte.right, corte.top)])
        pag.mediabox, pag.cropbox, pag.trimbox, pag.bleedbox = cx, cx, cx, cx
    with open(pelado, "wb") as f:
        w.write(f)

    assert not sangrar.ja_tem_sangria(pelado)[0]

    saida = str(tmp_path / "sangrado.pdf")
    sangrar.sangrar_pdf(pelado, saida, 3.0)

    BRANCO = 246
    for pagina in (1, 2):
        real = sangrar.rasterizar(FLYER, pagina, 200, "BleedBox")
        feito = sangrar.rasterizar(saida, pagina, 200, "BleedBox")
        if feito.size != real.size:
            feito = feito.resize(real.size, Image.LANCZOS)
        L, A = real.size
        sp = int(round(3.0 / MM * 200))
        faixas = {"topo": (0, 0, L, sp), "base": (0, A - sp, L, A),
                  "esquerda": (0, 0, sp, A), "direita": (L - sp, 0, L, A)}
        for borda, cx2 in faixas.items():
            dr = list(real.crop(cx2).convert("L").get_flattened_data())
            di = list(feito.crop(cx2).convert("L").get_flattened_data())
            tinta = sum(1 for v in dr if v <= BRANCO)
            fiapo = sum(1 for vr, vi in zip(dr, di)
                        if vr <= BRANCO and vi > BRANCO)
            assert tinta, (pagina, borda, "faixa sem tinta nenhuma?")
            # 0,1% e o serrilhado de reamostrar, nao fiapo de verdade
            assert fiapo <= tinta * 0.001, (
                "pagina %d, borda %s: papel em %d dos %d pixels onde o "
                "designer pos tinta" % (pagina, borda, fiapo, tinta))
