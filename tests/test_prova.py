# -*- coding: utf-8 -*-
"""
A prova impressa: uma folha A4 em pe por pagina, um trabalho por folha.

Nao depende do Ghostscript: a rasterizacao e substituida por imagens
feitas na hora.
"""

import os

import pytest
from PIL import Image
from pypdf import PdfReader

import finart_ctp.prova as prova


def _imagens(pasta, tamanhos):
    caminhos = []
    for i, (w, h) in enumerate(tamanhos):
        c = os.path.join(str(pasta), "p%03d.jpg" % i)
        Image.new("RGB", (w, h), "white").save(c)
        caminhos.append(c)
    return caminhos


@pytest.fixture
def espiao(monkeypatch):
    """Intercepta o envio para a impressora e guarda o que seria impresso."""
    enviados = []

    def falso_envio(pdf, impressora=None, duplex=False):
        r = PdfReader(pdf)
        pg = r.pages[0]
        enviados.append({
            "paginas": len(r.pages),
            "duplex": duplex,
            "larg_mm": round(float(pg.mediabox.width) / 72 * 25.4),
            "alt_mm": round(float(pg.mediabox.height) / 72 * 25.4),
        })

    monkeypatch.setattr(prova, "enviar_para_impressora", falso_envio)
    return enviados


def _verso():
    """Uma folha de OS de mentira, do tamanho de uma A4 em pe."""
    return Image.new("RGB", (1240, 1754), "white")


def test_sem_os_a_prova_sai_so_na_frente(monkeypatch, tmp_path, espiao):
    """
    Uma pagina por folha, so na frente - como sempre saiu. O simplex e
    PEDIDO, e nao herdado do que estiver marcado na impressora.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)] * 2))
    _, folhas = prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA")

    assert folhas == 2
    assert len(espiao) == 1, "um trabalho so"
    assert espiao[0]["paginas"] == 2
    assert espiao[0]["duplex"] is False


def test_com_os_a_folha_sai_dos_dois_lados(monkeypatch, tmp_path, espiao):
    """
    Uma pagina de arte: uma folha, arte na frente e OS no verso. Isto
    saia em DUAS folhas enquanto o programa supunha que a impressora
    estava em duplex - ela esta em simplex.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    _, folhas = prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA",
                               verso=_verso())

    assert folhas == 1
    assert len(espiao) == 1
    assert espiao[0]["paginas"] == 2, "arte e OS no mesmo trabalho"
    assert espiao[0]["duplex"] is True


def test_a_os_entra_intercalada_em_arquivo_de_varias_paginas(
        monkeypatch, tmp_path, espiao):
    """
    Frente e verso da arte rende DUAS folhas completas: arte p1 na frente
    com a OS atras, arte p2 na frente com a OS atras. Sem intercalar, a
    segunda folha sairia com a arte do verso de um lado e nada do outro.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)] * 2))
    _, folhas = prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA",
                               verso=_verso())

    assert folhas == 2
    assert len(espiao) == 1
    assert espiao[0]["paginas"] == 4, "arte, OS, arte, OS"
    assert espiao[0]["duplex"] is True


def test_folha_sai_sempre_a4_em_pe(monkeypatch, tmp_path, espiao):
    # arte deitada E arte em pe: as duas tem que virar A4 retrato
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600),
                                                               (600, 800)]))
    prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA")
    for folha in espiao:
        assert (folha["larg_mm"], folha["alt_mm"]) == (210, 297)


def test_arte_deitada_e_girada_para_caber(tmp_path):
    # a arte deitada tem que ocupar a folha girada, nao encolhida no meio
    imagem = _imagens(tmp_path, [(2000, 1000)])
    destino = os.path.join(str(tmp_path), "prova.pdf")
    prova._montar_a4(imagem, destino, dpi=150)

    pg = PdfReader(destino).pages[0]
    assert float(pg.mediabox.width) < float(pg.mediabox.height)   # retrato


# ----------------------------------------------------------------------
# Etiqueta do formato no canto da folha
# ----------------------------------------------------------------------

def _faixa_do_alto(folha, dpi=150):
    """Recorte do alto da folha, onde a etiqueta e escrita."""
    alto = int(round(prova.FAIXA_ROTULO_MM / 25.4 * dpi))
    return folha.crop((0, 0, folha.width, alto))


def _extremos(imagem):
    """(pixel mais escuro, pixel mais claro) do recorte, em cinza."""
    return imagem.convert("L").getextrema()


def _tem_tinta(imagem):
    """True se houver algum pixel escuro (texto ou arte)."""
    return _extremos(imagem)[0] < 128


def test_etiqueta_aparece_no_alto_da_folha():
    arte = Image.new("RGB", (2000, 1000), "white")      # deitada, em branco
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F4")
    assert _tem_tinta(_faixa_do_alto(folha)), "a etiqueta nao foi escrita"


def test_sem_etiqueta_o_alto_fica_limpo():
    arte = Image.new("RGB", (2000, 1000), "white")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="")
    assert not _tem_tinta(_faixa_do_alto(folha))


def test_etiqueta_nao_cai_por_cima_da_arte():
    # arte toda preta: se a faixa do alto tem branco, a arte foi empurrada
    arte = Image.new("RGB", (2000, 1000), "black")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F4")
    assert _extremos(_faixa_do_alto(folha))[1] > 200,         "a arte invadiu a faixa da etiqueta"


def test_folha_continua_a4_em_pe_com_etiqueta():
    arte = Image.new("RGB", (2000, 1000), "white")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F2")
    assert folha.width < folha.height
    assert abs(folha.width / 150 * 25.4 - 210) < 1


# ----------------------------------------------------------------------
# A TRAVA DE COPIA UNICA
# ----------------------------------------------------------------------
# Em 10/09/2026 o mesmo trabalho saiu em papel duas vezes, por dois
# defeitos diferentes - o ZIMI do EMPORIO e o flyer da AMERICA. Os dois
# tinham a mesma forma: algo falhava DEPOIS da impressao e o vigia
# refazia tudo. Consertar cada laco conserta um laco; a trava protege de
# todos, porque quem imprime passa por esta porta.

def test_a_mesma_prova_nao_sai_duas_vezes(monkeypatch, tmp_path, espiao):
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA")
    assert len(espiao) == 1

    with pytest.raises(prova.JaImprimiu):
        prova.imprimir("arte.pdf", "IMPRESSORA FALSA")
    assert len(espiao) == 1, "nao pode ter ido nada a mais para a impressora"


def test_de_novo_reimprime_a_pedido(monkeypatch, tmp_path, espiao):
    """A trava e para o laco, nao para o operador."""
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA")
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA", de_novo=True)
    assert len(espiao) == 2


def test_copias_saem_no_mesmo_pedido(monkeypatch, tmp_path, espiao):
    """Mais de uma copia se PEDE de uma vez - e continua sendo uma vez."""
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA", copias=3)
    assert len(espiao) == 3
    # e depois disso a trava vale, como para qualquer outra
    with pytest.raises(prova.JaImprimiu):
        prova.imprimir("arte.pdf", "IMPRESSORA FALSA")


def test_arte_que_nao_imprimiu_pode_tentar_de_novo(monkeypatch, tmp_path,
                                                   espiao):
    """
    Impressora fora do ar NAO conta como impresso.

    Este e o outro lado da trava, e sem ele ela seria pior que o
    problema: o papel nao saiu, e o trabalho tem de poder sair depois.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))

    def cair(*a, **k):
        raise RuntimeError("impressora fora do ar")

    monkeypatch.setattr(prova, "enviar_para_impressora", cair)
    with pytest.raises(RuntimeError):
        prova.imprimir("arte.pdf", "IMPRESSORA FALSA")

    # agora a impressora voltou: tem de imprimir, sem pedir 'de_novo'
    monkeypatch.setattr(prova, "enviar_para_impressora",
                        lambda c, alvo, duplex=False: espiao.append(alvo))
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA")
    assert len(espiao) == 1


def test_a_mesma_arte_para_OUTRA_os_e_prova_nova(monkeypatch, tmp_path,
                                                 espiao):
    """
    A trava e por arte E POR OS.

    A mesma arte pode voltar num servico novo - ali a prova e legitima, e
    travar seria segurar trabalho de verdade.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    um, outro = _verso(), _verso()
    um._os_numero, outro._os_numero = 19635, 19640

    prova.imprimir("arte.pdf", "IMPRESSORA FALSA", verso=um)
    prova.imprimir("arte.pdf", "IMPRESSORA FALSA", verso=outro)
    assert len(espiao) == 2

    with pytest.raises(prova.JaImprimiu):
        prova.imprimir("arte.pdf", "IMPRESSORA FALSA", verso=um)


def test_a_trava_reconhece_a_prova_pela_ORIGEM_e_nao_pelo_temporario(
        monkeypatch, tmp_path, espiao):
    """
    A VOPRIX imprime a partir de um PDF que a Corel gera de novo a cada
    passada - tamanho e data mudam, entao a chave mudaria junto e a
    trava nunca pegaria justamente no cliente que mais reconverte.

    Com 'origem' apontando para o .cdr, que nao muda, a segunda passada
    e reconhecida mesmo com outro temporario.
    """
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    cdr = tmp_path / "arte.cdr"
    cdr.write_bytes(b"cdr")

    prova.imprimir(str(tmp_path / "tmp_1.pdf"), "IMPRESSORA FALSA",
                   origem=str(cdr))
    with pytest.raises(prova.JaImprimiu):
        prova.imprimir(str(tmp_path / "tmp_2.pdf"), "IMPRESSORA FALSA",
                       origem=str(cdr))
    assert len(espiao) == 1
