# -*- coding: utf-8 -*-
"""
Achar a marca de corte no PDF - a cruz que manda na pinca.

Ler por pixel nao deu: duas versoes do detector deram numeros diferentes
para o mesmo arquivo, porque em arte cheia mancha de desenho passa por
risco. A marca, porem, e um traco DESENHADO: no PDF ela tem coordenada
exata, e ali nao ha o que interpretar.

O que separa marca de linha de desenho e a SIMETRIA: a marca aparece nos
dois extremos da folha, na mesma altura. Linha de desenho, nao.

Os quatro lados sao lidos porque a arte da Creative as vezes chega em pe
e e girada: girando, o pe da chapa passa a ser outra borda do arquivo.
"""

from finart_ctp.marcas import marcas_de_corte


def gravar_pdf(caminho, larg_mm, alt_mm, riscos):
    """
    PDF de uma pagina com riscos retos. riscos: [(x0, y0, x1, y1)] em mm,
    medidos do canto de baixo e da esquerda.
    """
    def pt(mm):
        return mm / 25.4 * 72

    partes = ["0.25 w"]
    for x0, y0, x1, y1 in riscos:
        partes.append("%.3f %.3f m %.3f %.3f l S"
                      % (pt(x0), pt(y0), pt(x1), pt(y1)))
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


def horizontal(y, x=8, comp=7):
    """Um risco horizontal na altura y - fala de um corte DE ALTURA."""
    return (x, y, x + comp, y)


def vertical(x, y=6, comp=7):
    """Um risco vertical na coluna x - fala de um corte DE LARGURA."""
    return (x, y, x, y + comp)


# arte deitada de 480x330: a margem da direita comeca por volta daqui
DIREITA = 480 - 20


# ----------------------------------------------------------------------
# Corte de cima e de baixo (marca horizontal)
# ----------------------------------------------------------------------

def test_acha_a_marca_dos_dois_lados(tmp_path):
    arq = gravar_pdf(tmp_path / "a.pdf", 480, 330, [
        horizontal(12.0), horizontal(12.0, DIREITA),        # corte, embaixo
        horizontal(318.0), horizontal(318.0, DIREITA),      # corte, em cima
    ])
    m = marcas_de_corte(arq)
    assert abs(m["pe"] - 12.0) < 0.4
    assert abs(m["topo"] - 12.0) < 0.4


def test_entre_sangria_e_corte_vale_a_de_dentro(tmp_path):
    """
    A arte traz duas marcas em cada beirada: a de fora e a sangria, a de
    DENTRO e o corte. Foi assim nos arquivos da Creative - santinho com
    7,1 e 11,9 mm; folder com 9,0 e 13,1.
    """
    arq = gravar_pdf(tmp_path / "b.pdf", 480, 330, [
        horizontal(7.1), horizontal(7.1, DIREITA),          # sangria
        horizontal(11.9), horizontal(11.9, DIREITA),        # CORTE
    ])
    assert abs(marcas_de_corte(arq)["pe"] - 11.9) < 0.4, \
        "pegou a sangria no lugar do corte"


def test_risco_de_um_lado_so_nao_e_marca(tmp_path):
    """
    Linha de desenho cai de um lado so. Se contasse como marca, a pinca
    sairia do lugar por causa de um detalhe da arte.
    """
    arq = gravar_pdf(tmp_path / "c.pdf", 480, 330, [
        horizontal(12.0), horizontal(12.0, DIREITA),        # marca
        horizontal(25.0),                                   # so a esquerda
    ])
    assert abs(marcas_de_corte(arq)["pe"] - 12.0) < 0.4


def test_traco_no_meio_da_folha_nao_e_marca(tmp_path):
    """A marca mora na margem; no meio da folha e desenho."""
    arq = gravar_pdf(tmp_path / "d.pdf", 480, 330, [
        horizontal(12.0), horizontal(12.0, DIREITA),
        horizontal(20.0, 200), horizontal(20.0, 260),
    ])
    assert abs(marcas_de_corte(arq)["pe"] - 12.0) < 0.4


def test_traco_comprido_nao_e_marca(tmp_path):
    """Marca de corte e curta. Linha comprida e moldura de desenho."""
    arq = gravar_pdf(tmp_path / "e.pdf", 480, 330, [
        horizontal(12.0), horizontal(12.0, DIREITA),
        horizontal(30.0, 0, 60), horizontal(30.0, 420, 60),
    ])
    assert abs(marcas_de_corte(arq)["pe"] - 12.0) < 0.4


# ----------------------------------------------------------------------
# Corte da esquerda e da direita (marca vertical) - para a arte girada
# ----------------------------------------------------------------------

def test_acha_o_corte_das_laterais(tmp_path):
    """
    Girando a arte, o pe da chapa passa a ser uma das laterais do
    arquivo, e a pinca sai da marca DAQUELA borda. Sem ler os quatro
    lados, arte em pe sairia com a pinca do lugar errado.
    """
    arq = gravar_pdf(tmp_path / "v.pdf", 330, 480, [
        vertical(21.0), vertical(21.0, 480 - 13),
        vertical(330 - 21.0), vertical(330 - 21.0, 480 - 13),
    ])
    m = marcas_de_corte(arq)
    assert abs(m["esquerda"] - 21.0) < 0.4
    assert abs(m["direita"] - 21.0) < 0.4


def test_marca_vertical_de_um_lado_so_nao_conta(tmp_path):
    arq = gravar_pdf(tmp_path / "w.pdf", 330, 480, [vertical(21.0)])
    assert marcas_de_corte(arq)["esquerda"] is None


# ----------------------------------------------------------------------
# Quando nao da para ler
# ----------------------------------------------------------------------

def test_sem_marca_nenhuma_nao_inventa(tmp_path):
    """
    Nao achando marca, quem chamou PARA. Chutar a pinca e mandar chapa
    errada para a gravadora.
    """
    arq = gravar_pdf(tmp_path / "f.pdf", 480, 330, [])
    assert not any(marcas_de_corte(arq).values())


def test_arquivo_quebrado_nao_derruba_o_programa(tmp_path):
    ruim = tmp_path / "g.pdf"
    ruim.write_bytes(b"nao sou um PDF")
    assert not any(marcas_de_corte(str(ruim)).values())
