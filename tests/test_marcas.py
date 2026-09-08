# -*- coding: utf-8 -*-
"""
Achar a marca de corte no PDF - a cruz que manda na pinca.

Ler por pixel nao deu: duas versoes do detector deram numeros diferentes
para o mesmo arquivo, porque em arte cheia mancha de desenho passa por
risco. A marca, porem, e um traco DESENHADO: no PDF ela tem coordenada
exata, e ali nao ha o que interpretar.

O que separa marca de linha de desenho e a SIMETRIA: a marca aparece nos
dois lados da folha, na mesma altura. Linha de desenho, nao.
"""

import zlib

from finart_ctp.marcas import marcas_de_corte


def pdf_com_marcas(caminho, larg_mm, alt_mm, marcas):
    """
    Grava um PDF com riscos horizontais nas duas laterais.

    marcas: [(altura_mm_do_pe, x_mm, comprimento_mm), ...]
    """
    def pt(mm):
        return mm / 25.4 * 72

    partes = ["0.25 w"]
    for y, x, comp in marcas:
        partes.append("%.3f %.3f m %.3f %.3f l S"
                      % (pt(x), pt(y), pt(x + comp), pt(y)))
    conteudo = " ".join(partes).encode()

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.4f %.4f] "
         "/Contents 4 0 R >>" % (pt(larg_mm), pt(alt_mm))).encode(),
        b"<< /Length %d >>" % len(conteudo),
    ]
    with open(caminho, "wb") as f:
        f.write(b"%PDF-1.4\n")
        offsets = []
        for i, corpo in enumerate(objs, start=1):
            offsets.append(f.tell())
            f.write(b"%d 0 obj\n" % i + corpo)
            if i == 4:
                f.write(b"\nstream\n" + conteudo + b"\nendstream")
            f.write(b"\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
        for off in offsets:
            f.write(b"%010d 00000 n \n" % off)
        f.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, xref))
    return str(caminho)


DIREITA = 480 - 20      # onde comeca a marca do lado direito de uma arte
                        # de 480 mm de largura


def test_acha_a_marca_dos_dois_lados(tmp_path):
    arq = pdf_com_marcas(tmp_path / "a.pdf", 480, 330, [
        (12.0, 8, 7), (12.0, DIREITA, 7),          # corte, embaixo
        (318.0, 8, 7), (318.0, DIREITA, 7),        # corte, em cima
    ])
    pe, topo = marcas_de_corte(arq)
    assert abs(pe - 12.0) < 0.4
    assert abs(topo - 12.0) < 0.4


def test_entre_sangria_e_corte_vale_a_de_dentro(tmp_path):
    """
    A arte traz duas marcas em cada beirada: a de fora e a sangria, a de
    DENTRO e o corte. Foi assim nos dois arquivos da Creative - santinho
    com 7,1 e 11,9 mm; folder com 9,0 e 13,1.
    """
    arq = pdf_com_marcas(tmp_path / "b.pdf", 480, 330, [
        (7.1, 8, 7), (7.1, DIREITA, 7),            # sangria
        (11.9, 8, 7), (11.9, DIREITA, 7),          # CORTE
    ])
    pe, _ = marcas_de_corte(arq)
    assert abs(pe - 11.9) < 0.4, "pegou a sangria no lugar do corte"


def test_risco_de_um_lado_so_nao_e_marca(tmp_path):
    """
    Linha de desenho cai de um lado so. Se contasse como marca, a pinca
    sairia do lugar por causa de um detalhe da arte.
    """
    arq = pdf_com_marcas(tmp_path / "c.pdf", 480, 330, [
        (12.0, 8, 7), (12.0, DIREITA, 7),          # marca de verdade
        (25.0, 8, 7),                              # desenho, so a esquerda
    ])
    pe, _ = marcas_de_corte(arq)
    assert abs(pe - 12.0) < 0.4


def test_traco_no_meio_da_folha_nao_e_marca(tmp_path):
    """A marca mora na margem lateral; no meio e desenho."""
    arq = pdf_com_marcas(tmp_path / "d.pdf", 480, 330, [
        (12.0, 8, 7), (12.0, DIREITA, 7),
        (20.0, 200, 7), (20.0, 260, 7),            # meio da folha
    ])
    pe, _ = marcas_de_corte(arq)
    assert abs(pe - 12.0) < 0.4


def test_traco_comprido_nao_e_marca(tmp_path):
    """Marca de corte e curta. Linha comprida e moldura de desenho."""
    arq = pdf_com_marcas(tmp_path / "e.pdf", 480, 330, [
        (12.0, 8, 7), (12.0, DIREITA, 7),
        (30.0, 0, 60), (30.0, 420, 60),            # 60 mm: comprida demais
    ])
    pe, _ = marcas_de_corte(arq)
    assert abs(pe - 12.0) < 0.4


def test_sem_marca_nenhuma_devolve_None(tmp_path):
    """
    Nao achando marca, quem chamou PARA. Chutar a pinca e mandar chapa
    errada para a gravadora.
    """
    arq = pdf_com_marcas(tmp_path / "f.pdf", 480, 330, [])
    assert marcas_de_corte(arq) == (None, None)


def test_arquivo_quebrado_nao_derruba_o_programa(tmp_path):
    ruim = tmp_path / "g.pdf"
    ruim.write_bytes(b"nao sou um PDF")
    assert marcas_de_corte(str(ruim)) == (None, None)
