# -*- coding: utf-8 -*-
"""
Preflight: a conferencia da arte por dentro.

Ate aqui a FIA media a CHAPA - tamanho e resolucao de gravacao - e nao
olhava o que estava desenhado nela. Uma imagem de 150 dpi esticada numa
chapa de 1000 grava lisinha e so mostra o defeito na tiragem.

A parte dificil e que o PDF nao diz em que tamanho a imagem ficou: diz
'desenhe no quadrado de 1x1' e antes estica esse quadrado. Estes testes
montam PDFs com transformacoes de verdade e conferem a conta.
"""

import zlib

import pytest

from finart_ctp.preflight import AVISA, PARA, conferir_arte


def gravar(caminho, larg_pt, alt_pt, conteudo, extras=None, recursos=""):
    """PDF de uma pagina, escrito na mao para controlar cada operador."""
    conteudo = conteudo.encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
         "/Resources << %s >> /Contents 4 0 R >>"
         % (larg_pt, alt_pt, recursos)).encode(),
        b"<< /Length %d >>" % len(conteudo),
    ]
    fluxos = {4: conteudo}
    for corpo, fluxo in (extras or []):
        objs.append(corpo)
        if fluxo is not None:
            fluxos[len(objs)] = fluxo

    with open(caminho, "wb") as f:
        f.write(b"%PDF-1.4\n")
        offsets = []
        for i, corpo in enumerate(objs, start=1):
            offsets.append(f.tell())
            f.write(b"%d 0 obj\n" % i + corpo)
            if i in fluxos:
                f.write(b"\nstream\n" + fluxos[i] + b"\nendstream")
            f.write(b"\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
        for off in offsets:
            f.write(b"%010d 00000 n \n" % off)
        f.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, xref))
    return str(caminho)


def imagem(px_larg, px_alt):
    """Uma imagem cinza de verdade, do tamanho em pixels pedido."""
    dados = zlib.compress(bytes(px_larg * px_alt))
    dic = ("<< /Type /XObject /Subtype /Image /Width %d /Height %d "
           "/ColorSpace /DeviceGray /BitsPerComponent 8 "
           "/Filter /FlateDecode /Length %d >>"
           % (px_larg, px_alt, len(dados))).encode()
    return dic, dados


def mm(v):
    return v / 25.4 * 72


def arte_com_imagem(caminho, px, mm_colocado, cm=None):
    """
    Arte de uma imagem quadrada de 'px' pixels, colocada com 'mm' de lado.

    Sem 'cm' proprio, usa a transformacao simples. Com 'cm', permite
    montar o caso da imagem esticada por um grupo.
    """
    lado = mm(mm_colocado)
    desenho = cm or ("q %.2f 0 0 %.2f 10 10 cm /Im0 Do Q" % (lado, lado))
    return gravar(caminho, mm(300), mm(300), desenho,
                  extras=[imagem(px, px)],
                  recursos="/XObject << /Im0 5 0 R >>")


# ----------------------------------------------------------------------
# Resolucao efetiva - a conta que ninguem faz de cabeca
# ----------------------------------------------------------------------

def test_imagem_esticada_demais_para_o_servico(tmp_path):
    """
    300 pixels espalhados em 100 mm dao 76 dpi. O arquivo da imagem pode
    dizer '300 dpi' na etiqueta dele: o que vale e o tamanho em que foi
    colocada.
    """
    arte = arte_com_imagem(tmp_path / "a.pdf", 300, 100)
    achados = conferir_arte(arte)
    assert any(g == PARA and "76 dpi" in t for g, t in achados), achados


def test_imagem_boa_passa_limpa(tmp_path):
    """1200 px em 100 mm = 305 dpi, que e arte boa."""
    arte = arte_com_imagem(tmp_path / "b.pdf", 1200, 100)
    assert conferir_arte(arte) == []


def test_resolucao_no_meio_do_caminho_so_avisa(tmp_path):
    """
    1000 px em 100 mm = 254 dpi. Nao e o ideal, mas parar servico por
    isso emperraria a grafica: a maioria da arte comum vive nessa faixa.
    """
    arte = arte_com_imagem(tmp_path / "c.pdf", 1000, 100)
    achados = conferir_arte(arte)
    assert [g for g, _ in achados] == [AVISA]
    assert "254 dpi" in achados[0][1]


def test_tirinha_de_degrade_nao_conta(tmp_path):
    """
    Degrade e fio de moldura sao feitos de proposito com poucos pixels
    esticados. Medido num folder real da Creative: uma tira de 4 x 210 mm
    a 182 dpi pararia o servico inteiro, e ninguem ve a diferenca.
    """
    fino = "q %.2f 0 0 %.2f 10 10 cm /Im0 Do Q" % (mm(4), mm(210))
    arte = gravar(tmp_path / "d.pdf", mm(300), mm(300), fino,
                  extras=[imagem(30, 1500)],
                  recursos="/XObject << /Im0 5 0 R >>")
    assert conferir_arte(arte) == []


def test_a_conta_segue_a_transformacao_do_grupo(tmp_path):
    """
    O caso que quebra ferramenta ingenua: a imagem esta dentro de um
    grupo que ele proprio estica tudo pela metade. Quem le so o 'cm' de
    dentro erra o tamanho pela metade, e o dpi pelo dobro.
    """
    dentro = b"q %.2f 0 0 %.2f 0 0 cm /Im0 Do Q" % (mm(100), mm(100))
    grupo = ("<< /Type /XObject /Subtype /Form /BBox [0 0 1000 1000] "
             "/Resources << /XObject << /Im0 5 0 R >> >> /Length %d >>"
             % len(dentro)).encode()

    arte = gravar(tmp_path / "e.pdf", mm(300), mm(300),
                  "q 2 0 0 2 0 0 cm /Fm0 Do Q",
                  extras=[imagem(1200, 1200), (grupo, dentro)],
                  recursos="/XObject << /Fm0 6 0 R >>")

    achados = conferir_arte(arte)
    # 1200 px em 200 mm (100 dobrados pelo grupo) = 152 dpi, nao 305
    assert any("152 dpi" in t for _, t in achados), achados
    assert any(g == PARA for g, _ in achados)


# ----------------------------------------------------------------------
# Fontes
# ----------------------------------------------------------------------

def test_fonte_nao_incorporada_para_o_servico(tmp_path):
    """
    Fonte que falta o RIP troca por outra, e o texto muda de forma sem
    avisar ninguem - larguras diferentes, linha que reflui, nome de
    cliente escrito com a letra errada.
    """
    fonte = (b"<< /Type /Font /Subtype /Type1 /BaseFont /HelveticaNeue-Bold "
             b"/FontDescriptor 6 0 R >>")
    descritor = b"<< /Type /FontDescriptor /FontName /HelveticaNeue-Bold >>"
    arte = gravar(tmp_path / "f.pdf", mm(100), mm(100), "BT ET",
                  extras=[(fonte, None), (descritor, None)],
                  recursos="/Font << /F1 5 0 R >>")

    achados = conferir_arte(arte)
    assert any(g == PARA and "HelveticaNeue-Bold" in t for g, t in achados)


def test_fonte_incorporada_passa(tmp_path):
    fonte = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Boa "
             b"/FontDescriptor 6 0 R >>")
    descritor = (b"<< /Type /FontDescriptor /FontName /Boa "
                 b"/FontFile2 7 0 R >>")
    arquivo = b"<< /Length 4 >>"
    arte = gravar(tmp_path / "g.pdf", mm(100), mm(100), "BT ET",
                  extras=[(fonte, None), (descritor, None),
                          (arquivo, b"abcd")],
                  recursos="/Font << /F1 5 0 R >>")
    assert conferir_arte(arte) == []


def test_fonte_padrao_do_pdf_nao_e_problema(tmp_path):
    """As 14 fontes basicas todo RIP tem. Reclamar delas seria ruido."""
    fonte = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    arte = gravar(tmp_path / "h.pdf", mm(100), mm(100), "BT ET",
                  extras=[(fonte, None)],
                  recursos="/Font << /F1 5 0 R >>")
    assert conferir_arte(arte) == []


# ----------------------------------------------------------------------
# Traco fino
# ----------------------------------------------------------------------

def test_traco_de_espessura_zero_e_avisado(tmp_path):
    """
    O classico: espessura 0 quer dizer 'a linha mais fina que a maquina
    conseguir'. Na tela aparece; na chapa de 1000 dpi da 0,025 mm e some
    na impressao.
    """
    arte = gravar(tmp_path / "i.pdf", mm(100), mm(100),
                  "0 w 10 10 m 200 200 l S")
    assert any(g == AVISA and "some na chapa" in t
               for g, t in conferir_arte(arte))


def test_marca_de_corte_nao_e_traco_fino(tmp_path):
    """
    0,25 pt e a espessura padrao das marcas de corte, e ela imprime
    perfeitamente. Com o limite errado a FIA reclamava de cinco arquivos
    em cinco da Solida - e aviso que aparece sempre nao e aviso.
    """
    arte = gravar(tmp_path / "j.pdf", mm(100), mm(100),
                  "0.25 w 10 10 m 200 200 l S")
    assert conferir_arte(arte) == []


def test_traco_esticado_pela_transformacao_conta_esticado(tmp_path):
    """
    Espessura tambem passa pela transformacao: 0,02 pt dentro de um
    'cm' que multiplica por 10 vale 0,2 pt na folha, e imprime.
    """
    arte = gravar(tmp_path / "k.pdf", mm(100), mm(100),
                  "q 10 0 0 10 0 0 cm 0.02 w 1 1 m 20 20 l S Q")
    assert conferir_arte(arte) == []


# ----------------------------------------------------------------------
# Robustez: preflight nao pode derrubar a producao
# ----------------------------------------------------------------------

def test_arquivo_quebrado_nao_derruba(tmp_path):
    ruim = tmp_path / "l.pdf"
    ruim.write_bytes(b"nao sou um PDF")
    assert conferir_arte(str(ruim)) == []


def test_pagina_sem_desenho_nenhum(tmp_path):
    assert conferir_arte(gravar(tmp_path / "m.pdf", mm(100), mm(100), "")) == []


def test_o_preflight_para_a_pagina_mas_nao_o_programa(monkeypatch, tmp_path):
    """
    Achado grave vira pendencia e a pagina nao fecha - mas o laco segue,
    e as outras paginas do arquivo continuam.
    """
    import finart_ctp.processador as P

    avisos = []
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda n, m: avisos.append(m))
    monkeypatch.setattr(P, "conferir_arte",
                        lambda pdf, pag: [(PARA, "fonte NAO incorporada: X")])

    problemas = []
    assert P._arte_reprovada("x.pdf", 2, "arte.pdf", False, problemas) is True
    assert "pagina 2" in avisos[0] and "fonte" in avisos[0]

    # com o operador liberando na mao, passa
    assert P._arte_reprovada("x.pdf", 2, "arte.pdf", True, []) is False


def test_conferencia_que_explode_nao_para_a_chapa(monkeypatch):
    """
    Se o preflight quebrar num arquivo estranho, ele nao pode virar
    portao fechado: a chapa que ja saia antes tem de continuar saindo.
    """
    import finart_ctp.processador as P

    def explodir(pdf, pagina):
        raise RuntimeError("PDF de outro planeta")

    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(P, "conferir_arte", explodir)
    assert P._arte_reprovada("x.pdf", 1, "arte.pdf", False, []) is False
