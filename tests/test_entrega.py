# -*- coding: utf-8 -*-
"""
O caminho curto: o PDF do cliente vai inteiro para o CTP.

Em 09/09/2026 uma pasta da VOPRIX foi gravada com o preto fora do lugar:
no arquivo ele estava no canal K ('0 0 0 1', escrito assim dentro do
PDF) e na chapa tinha virado C, M e Y com o K vazio. Nao foi a Corel nem
o cliente - foi a nossa leitura, que passava a cor pelo perfil ICC
embutido no arquivo antes de separar.

Estes testes cuidam do caminho que nao le a cor: entrega o arquivo e
deixa a separacao com a gravadora.
"""

import os

import pytest

from finart_ctp import entrega
from finart_ctp import processador as P


def _pdf(caminho, larg_mm=510.0, alt_mm=400.0, paginas=1, camadas=False):
    """Um PDF de verdade, no tamanho da chapa."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject

    escritor = PdfWriter()
    for _ in range(paginas):
        escritor.add_blank_page(width=larg_mm / 25.4 * 72,
                                height=alt_mm / 25.4 * 72)
    if camadas:
        escritor._root_object[NameObject("/OCProperties")] = DictionaryObject({
            NameObject("/OCGs"): ArrayObject(),
            NameObject("/D"): DictionaryObject(
                {NameObject("/Order"): ArrayObject()}),
        })
    with open(caminho, "wb") as f:
        escritor.write(f)
    return caminho


def _paginas(caminho):
    from pypdf import PdfReader
    return len(PdfReader(caminho).pages)


# ----------------------------------------------------------------------
# Entregar
# ----------------------------------------------------------------------

def test_pagina_unica_e_copia_byte_por_byte(tmp_path):
    """
    Uma pagina: nem o pypdf encosta no arquivo.

    E a razao de o caminho curto existir. Todo programa que ABRE o PDF
    para regravar tem uma chance de mudar a cor - foi assim que o preto
    saiu do K.
    """
    origem = _pdf(str(tmp_path / "arte.pdf"))
    destino = str(tmp_path / "chapa.pdf")
    entrega.entregar(origem, destino, pagina=1, total=1)

    with open(origem, "rb") as a, open(destino, "rb") as b:
        assert a.read() == b.read()


def test_de_varias_paginas_sai_uma_chapa_por_pagina(tmp_path):
    origem = _pdf(str(tmp_path / "arte.pdf"), paginas=3)
    for pagina in (1, 2, 3):
        destino = str(tmp_path / ("chapa%d.pdf" % pagina))
        entrega.entregar(origem, destino, pagina=pagina, total=3)
        assert _paginas(destino) == 1


def test_a_ficha_das_camadas_vai_junto(tmp_path):
    """
    /OCProperties e a ficha das CAMADAS do arquivo, e mora no catalogo -
    fora da pagina. Montando um documento novo em volta da pagina, ela
    fica para tras, e o que estava escondido (guia de corte, gabarito de
    verniz) fica com visibilidade indefinida na gravadora.
    """
    from pypdf import PdfReader

    origem = _pdf(str(tmp_path / "arte.pdf"), paginas=2, camadas=True)
    destino = str(tmp_path / "chapa.pdf")
    entrega.entregar(origem, destino, pagina=2, total=2)

    assert "/OCProperties" in PdfReader(destino).trailer["/Root"]


# ----------------------------------------------------------------------
# Conferir o que foi entregue
# ----------------------------------------------------------------------

def test_entrega_do_tamanho_certo_passa(tmp_path):
    assert entrega.conferir(_pdf(str(tmp_path / "c.pdf")), 510, 400) == ""


def test_entrega_fora_de_tamanho_e_recusada(tmp_path):
    arquivo = _pdf(str(tmp_path / "c.pdf"), larg_mm=520.0)
    erro = entrega.conferir(arquivo, 510, 400)
    assert "520" in erro and "largura" in erro


def test_entrega_com_duas_paginas_e_recusada(tmp_path):
    """Duas paginas no CTP sao duas chapas na fila, e a OS cobrou uma."""
    arquivo = _pdf(str(tmp_path / "c.pdf"), paginas=2)
    assert "2 paginas" in entrega.conferir(arquivo, 510, 400)


# ----------------------------------------------------------------------
# Quem pode ir pelo caminho curto
# ----------------------------------------------------------------------

def _plano(**mudanca):
    plano = {"pagina": 1, "base": "x", "dpi": 1000,
             "larg_chapa": 510.0, "alt_chapa": 400.0,
             "usadas": set("CMYK"), "cinza": False, "alvo": None,
             "deslocamento": None, "girar": 0,
             "tintas_do_arquivo": set("CMYK")}
    plano.update(mudanca)
    return plano


def test_quadricromia_cabe_no_curto():
    assert P.cabe_no_curto(_plano())


def test_uma_cor_com_uma_tinta_cabe_no_curto():
    """K sozinho: a gravadora acha uma tinta e grava uma chapa. Bate."""
    assert P.cabe_no_curto(_plano(cinza=True, usadas={"GRAY"},
                                  tintas_do_arquivo={"K"}))


def test_uma_cor_com_quatro_tintas_nao_cabe_no_curto():
    """
    A chapa e uma, mas o arquivo tem C, M, Y e K escritos dentro. A
    gravadora nao tem como adivinhar: gravaria quatro onde a OS cobrou
    uma. Essa volta pelo caminho longo, que junta tudo num cinza.
    """
    assert not P.cabe_no_curto(_plano(cinza=True, usadas={"GRAY"},
                                      tintas_do_arquivo=set("CMYK")))


def test_pagina_que_precisa_girar_nao_e_entregue(tmp_path):
    """O caminho curto entrega o arquivo como ele veio - girado, nao."""
    with pytest.raises(RuntimeError, match="girada ou montada"):
        P._entregar_chapa(_pdf(str(tmp_path / "a.pdf")), str(tmp_path),
                          "chapa", _plano(girar=270), 1)


def test_entrega_fora_de_tamanho_nao_fica_na_pasta(tmp_path):
    """Chapa errada na pasta do CTP e pior que chapa faltando."""
    origem = _pdf(str(tmp_path / "a.pdf"), larg_mm=520.0)
    saida = tmp_path / "ctp"
    saida.mkdir()
    with pytest.raises(RuntimeError, match="apaguei"):
        P._entregar_chapa(origem, str(saida), "chapa", _plano(), 1)
    assert os.listdir(str(saida)) == []


# ----------------------------------------------------------------------
# O fluxo inteiro da VOPRIX
# ----------------------------------------------------------------------

CDR = "Envelope_Saco_23x31,5_Colegio_Unus.cdr"


def _rodar(monkeypatch, tmp_path, cobertura, cinza=False, aprovado=False):
    origem = _pdf(str(tmp_path / "arte.pdf"))
    saida = tmp_path / "ctp"
    saida.mkdir()
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante",
                        lambda pdf, pagina, sem_icc=False: cinza)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    resultado = P._processar_pdf(origem, CDR, str(saida), P.VOPRIX,
                                 {"status": "ok", "saidas": [], "motivo": "",
                                  "impresso": None}, lambda m: None, aprovado)
    return origem, saida, resultado


def test_a_voprix_entrega_o_arquivo_do_cliente(monkeypatch, tmp_path):
    """Ponta a ponta: o que chega na pasta do CTP e o PDF do cliente."""
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao era para separar"))
    origem, saida, r = _rodar(monkeypatch, tmp_path,
                              {"C": .31, "M": .22, "Y": .18, "K": .09})

    assert r["status"] == "ok"
    entregue = saida / "510x400_CMYK_VOPRIX_COLEGIO_UNUS_envelope_saco.pdf"
    assert entregue.exists()
    with open(origem, "rb") as a:
        assert entregue.read_bytes() == a.read()


def test_a_conta_da_os_e_a_da_gravadora(monkeypatch, tmp_path):
    """
    Quatro tintas no arquivo, quatro chapas na OS. Quem grava e a
    gravadora, entao a conta tem de ser a que ELA vai fazer.
    """
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao era para separar"))
    _, _, r = _rodar(monkeypatch, tmp_path,
                     {"C": .31, "M": .22, "Y": .18, "K": .09})
    assert r["chapas"] == [{"chapa": [510, 400], "tintas": 4}]


def test_uma_cor_com_quatro_tintas_volta_para_o_caminho_longo(monkeypatch,
                                                              tmp_path):
    """
    Aprovada a mao, ela ainda sai em UMA chapa - pelo caminho longo, que
    junta as quatro tintas num cinza so. Era o que ja acontecia.
    """
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None, deslocamento=None, girar=0):
        feito.update(base=base, cinza=cinza)
        return _pdf(os.path.join(saida, base + ".pdf")), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)
    _, _, r = _rodar(monkeypatch, tmp_path,
                     {"C": .0608, "M": .0608, "Y": .0608, "K": .0544},
                     cinza=True, aprovado=True)

    assert r["status"] == "ok"
    assert feito["cinza"] is True
    assert feito["base"] == "510x400_GRAY_VOPRIX_COLEGIO_UNUS_envelope_saco"
