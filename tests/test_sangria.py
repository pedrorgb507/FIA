# -*- coding: utf-8 -*-
r"""
A sangria lida pelos DOIS caminhos - e o que fazer quando eles discordam.

POR QUE DOIS. Cada um cobre o buraco do outro:

  a DECLARADA sai das caixas do PDF - a TrimBox (onde se corta) contra a
  BleedBox (ate onde a arte vai). E de graca, e exata quando esta la.
  Muitos arquivos nao trazem TrimBox nenhuma;

  a DA TINTA rasteriza e olha se o desenho passa da marca de corte para
  fora. Funciona em arquivo que nao declara nada, e custa segundos de
  Ghostscript.

E O QUE ESTE ARQUIVO MAIS SEGURA: arquivo SEM TrimBox nao pode virar "sem
sangria" por omissao. As caixas do PDF caem uma na outra quando faltam -
a especificacao manda a TrimBox valer o MediaBox -, e ai a conta acha
zero e diz "pelado" com toda a confianca. Nao e pelado: e nao declarado,
e isso se pergunta a tinta.

E QUANDO OS DOIS DISCORDAM, o sistema FALA. Arquivo que declara 3 mm de
sangria e mostra a arte parando na linha de corte e justamente o que
engana - montar confiando na declaracao poria o corte 3 mm dentro do
desenho.
"""

import os

import pytest

from finart_ctp import sangria

MM, PT = 25.4, 72.0
PIL = pytest.importorskip("PIL")


# ----------------------------------------------------------------------
# PDF de mentira, para as regras morarem no git sem arte de cliente
# ----------------------------------------------------------------------

def _traco(x0, y0, x1, y1, grossura=0.25):
    """Um traco de caneta, em mm, do jeito que a marca de corte e escrita."""
    return ("0 0 0 1 K %.3f w %.3f %.3f m %.3f %.3f l S\n"
            % (grossura / MM * PT, x0 / MM * PT, y0 / MM * PT,
               x1 / MM * PT, y1 / MM * PT))


def _marcas_de_corte(larg_mm, alt_mm, recuo):
    """
    As quatro marcas de corte, do jeito que o marcas.py reconhece: traco
    curto, na margem lateral, nos DOIS lados e na mesma altura.
    """
    d = 3.0                              # comprimento do tracinho
    return "".join([
        # horizontais (dizem onde cortar embaixo e em cima)
        _traco(0, recuo, d, recuo),
        _traco(larg_mm - d, recuo, larg_mm, recuo),
        _traco(0, alt_mm - recuo, d, alt_mm - recuo),
        _traco(larg_mm - d, alt_mm - recuo, larg_mm, alt_mm - recuo),
        # verticais (dizem onde cortar na esquerda e na direita)
        _traco(recuo, 0, recuo, d),
        _traco(recuo, alt_mm - d, recuo, alt_mm),
        _traco(larg_mm - recuo, 0, larg_mm - recuo, d),
        _traco(larg_mm - recuo, alt_mm - d, larg_mm - recuo, alt_mm),
    ])


def _chapado(x0, y0, larg, alt):
    """Um CMYK chapado nesta area, em mm."""
    return ("0.10 0.90 0.80 0.05 k %.3f %.3f %.3f %.3f re f\n"
            % (x0 / MM * PT, y0 / MM * PT, larg / MM * PT, alt / MM * PT))


def _pdf(caminho, desenho, larg_mm=106.0, alt_mm=156.0, corte=None,
         sangra=None, girar=0):
    """
    Um PDF de uma pagina com este desenho.

    'corte' e 'sangra' sao (x0, y0, larg, alt) em mm, e viram TrimBox e
    BleedBox. Passando corte=None, NENHUMA TrimBox e escrita - que e o
    caso do arquivo que nao declara nada.
    """
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, FloatObject,
                               NameObject)

    L, A = larg_mm / MM * PT, alt_mm / MM * PT
    w = PdfWriter()
    p = w.add_blank_page(width=L, height=A)
    fluxo = DecodedStreamObject()
    fluxo.set_data(desenho.encode())
    p.replace_contents(fluxo)

    def caixa(r):
        x0, y0, larg, alt = r
        return ArrayObject([FloatObject(v / MM * PT) for v in
                            (x0, y0, x0 + larg, y0 + alt)])

    if corte:
        p.trimbox = caixa(corte)
    if sangra:
        p.bleedbox = caixa(sangra)
    if girar:
        from pypdf.generic import NumberObject
        p[NameObject("/Rotate")] = NumberObject(girar)
    with open(caminho, "wb") as f:
        w.write(f)
    return caminho


# ----------------------------------------------------------------------
# A LEITURA DECLARADA - as caixas do PDF
# ----------------------------------------------------------------------

def test_arquivo_sangrado_diz_quanto(tmp_path):
    """TrimBox 100x150 dentro de uma BleedBox 106x156: 3 mm por lado."""
    arq = _pdf(str(tmp_path / "sangrado.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))
    mm, de_onde = sangria.sangria_declarada(arq)
    assert mm == pytest.approx(3.0, abs=0.02)
    assert "BleedBox" in de_onde


def test_arquivo_PELADO_declara_zero(tmp_path):
    """
    TrimBox igual a BleedBox e a arte acabando na linha de corte. Aqui
    zero e resposta de verdade, e nao falta de resposta.
    """
    arq = _pdf(str(tmp_path / "pelado.pdf"), _chapado(0, 0, 106, 156),
               corte=(0, 0, 106, 156), sangra=(0, 0, 106, 156))
    mm, _ = sangria.sangria_declarada(arq)
    assert mm == pytest.approx(0.0, abs=0.02)


def test_arquivo_SEM_TRIMBOX_nao_declara_NADA(tmp_path):
    """
    ESTE E O CASO QUE ENGANA, e o que o ticket pediu por escrito. Faltando
    a TrimBox, a especificacao manda ela valer o MediaBox - e ai a conta
    acha zero e diz 'pelado' com toda a confianca. Nao e pelado: e NAO
    DECLARADO, e a diferenca decide se a tinta e consultada ou nao.
    """
    arq = _pdf(str(tmp_path / "sem caixa.pdf"), _chapado(0, 0, 106, 156))
    mm, porque = sangria.sangria_declarada(arq)
    assert mm is None, "zero por omissao e a resposta errada"
    assert "TrimBox" in porque


def test_TrimBox_sem_BleedBox_e_dito_como_medida_do_PAPEL(tmp_path):
    """
    Sem BleedBox vale o MediaBox, e ele costuma incluir a AREA DAS MARCAS
    DE CORTE, que nao sangram nada - o CARTA_FRENTE de setembro daria
    11,64 mm onde a sangria e 3. A medida serve, mas tem de vir dita, para
    ninguem tomar area de marca por sangria.
    """
    arq = _pdf(str(tmp_path / "so corte.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150))
    mm, de_onde = sangria.sangria_declarada(arq)
    assert mm == pytest.approx(3.0, abs=0.02)
    assert "MediaBox" in de_onde


def test_o_nome_da_casa_continua_respondendo(tmp_path):
    """
    O sangrar.py chama sangria_do_arquivo e ja_tem_sangria ha tempo, e a
    conta mudou de casa - nao de contrato.
    """
    arq = _pdf(str(tmp_path / "s.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))
    assert sangria.sangria_do_arquivo(arq) == pytest.approx(3.0, abs=0.02)
    tem, mm = sangria.ja_tem_sangria(arq)
    assert tem is True and mm == pytest.approx(3.0, abs=0.02)


def test_a_ferramenta_de_sangrar_usa_a_MESMA_conta():
    """Uma conta so na casa: o sangrar.py nao tem a dele."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "ferramentas"))
    import sangrar
    assert sangrar.sangria_do_arquivo is sangria.sangria_do_arquivo
    assert sangrar.ja_tem_sangria is sangria.ja_tem_sangria


# ----------------------------------------------------------------------
# A MEDIDA DO CORTE - a PECA, e nao o papel
# ----------------------------------------------------------------------
# Confundir as duas sai caro no painel: o campo de la e a peca, e a
# sangria entra num campo separado. Um arquivo de 100x150 com 3 mm de
# sangria tem papel de 106x156; preenchendo 106x156, a sangria seria
# contada duas vezes e a peca sairia 6 mm maior do que o cliente pediu.

def test_a_medida_do_corte_sai_da_TRIMBOX_quando_ela_existe(tmp_path):
    arq = _pdf(str(tmp_path / "com corte.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))
    larg, alt, de_onde = sangria.medida_do_corte(arq)
    assert larg == pytest.approx(100.0, abs=0.02)
    assert alt == pytest.approx(150.0, abs=0.02)
    assert "TrimBox" in de_onde


def test_sem_TRIMBOX_a_medida_do_corte_e_o_PAPEL_e_vem_dita(tmp_path):
    """
    E o que ha. Mas tem de vir DITO, porque quem preencher a peca com
    isso e ainda somar sangria conta a sangria duas vezes.
    """
    arq = _pdf(str(tmp_path / "sem corte.pdf"), _chapado(0, 0, 106, 156))
    larg, alt, de_onde = sangria.medida_do_corte(arq)
    assert (larg, alt) == (pytest.approx(106.0, abs=0.02),
                           pytest.approx(156.0, abs=0.02))
    assert "nao declara corte" in de_onde


def test_a_medida_do_corte_respeita_o_ROTATE(tmp_path):
    """
    O /Rotate gira a pagina na hora de mostrar. Ignorando-o, a peca sai
    TRANSPOSTA - 150x100 onde e 100x150 - e o painel monta a chapa
    inteira em cima de uma peca virada.

    A leitura da tinta, vinte linhas abaixo, ja corrigia isto. As duas
    tem de falar da mesma pagina.
    """
    arq = _pdf(str(tmp_path / "girado.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156), girar=90)
    larg, alt, _ = sangria.medida_do_corte(arq)
    assert larg == pytest.approx(150.0, abs=0.02), \
        "girada, a peca de 100x150 se ve 150x100"
    assert alt == pytest.approx(100.0, abs=0.02)


def test_arquivo_quebrado_nao_tem_medida_de_corte(tmp_path):
    ruim = str(tmp_path / "ruim.pdf")
    open(ruim, "wb").write(b"isto nao e PDF")
    larg, alt, porque = sangria.medida_do_corte(ruim)
    assert larg is None and alt is None
    assert "nao consegui abrir" in porque


# ----------------------------------------------------------------------
# A LEITURA PELA TINTA - o desenho passa da marca de corte?
# ----------------------------------------------------------------------

def test_arte_que_passa_da_marca_de_corte_tem_sangria(tmp_path):
    """
    Chapado cobrindo a folha inteira, com a marca de corte a 3 mm da
    borda: o desenho passa 3 mm da linha de corte, e aquilo e sangria.
    """
    arq = _pdf(str(tmp_path / "tinta sangrada.pdf"),
               _chapado(0, 0, 106, 156) + _marcas_de_corte(106, 156, 3.0))
    mm, de_onde = sangria.sangria_pela_tinta(arq)
    assert mm == pytest.approx(3.0, abs=0.6), de_onde


def test_arte_que_para_NA_marca_de_corte_nao_tem_sangria(tmp_path):
    """
    O chapado acaba exatamente onde se corta. Fora da linha so ha as
    marcas - e marca nao e sangria.
    """
    arq = _pdf(str(tmp_path / "tinta pelada.pdf"),
               _chapado(3, 3, 100, 150) + _marcas_de_corte(106, 156, 3.0))
    mm, de_onde = sangria.sangria_pela_tinta(arq)
    assert mm == pytest.approx(0.0, abs=0.6), de_onde


def test_a_MARCA_DE_CORTE_nao_passa_por_sangria(tmp_path):
    """
    A armadilha da casa, a mesma do medir_o_pe: a marca de corte E tinta
    fora da linha de corte. Contando qualquer tinta, TODO arquivo com
    marca pareceria sangrado. O que conta e o DESENHO - faixa larga -, e
    nao o risco fino.
    """
    arq = _pdf(str(tmp_path / "so marca.pdf"),
               _chapado(3, 3, 100, 150) + _marcas_de_corte(106, 156, 3.0))
    onde = sangria.onde_o_desenho_comeca(arq)
    for lado in ("pe", "topo", "esquerda", "direita"):
        assert onde[lado] == pytest.approx(3.0, abs=0.6), (lado, onde)


def test_arquivo_com_ROTATE_e_medido_na_escala_certa(tmp_path):
    """
    O /Rotate gira a pagina na hora de mostrar, e o Ghostscript rasteriza
    JA GIRADO - a imagem sai 156 x 106 onde o MediaBox diz 106 x 156.
    Tirando a escala da altura do MediaBox, a conta erra na proporcao
    entre os dois lados: 3 mm de sangria viravam 4,4, a subtracao dava
    negativo e o arquivo sangrado aparecia como 'nao veio sangrada'.

    O marcas.py ja corrigia o /Rotate (ver DE_ONDE_VEM_CADA_LADO); esta
    leitura nao corrigia, e as duas tem de falar da mesma pagina.

    A ARTE AQUI NAO ENCOSTA NA BORDA DO PAPEL de proposito. Com chapado
    de borda a borda o desenho comeca a ZERO, e zero vezes escala errada
    continua zero - o teste passaria sem provar nada. Aqui ela comeca a
    3 mm da borda, e ai a escala trocada a transforma em 4,4.
    """
    # papel 112x162, corte a 6 mm da borda, arte de 3 a 109 mm: ela passa
    # 3 mm da linha de corte e para 3 mm antes da borda do papel
    desenho = _chapado(3, 3, 106, 156) + _marcas_de_corte(112, 162, 6.0)
    em_pe = _pdf(str(tmp_path / "em pe.pdf"), desenho, 112.0, 162.0)
    girado = _pdf(str(tmp_path / "girado.pdf"), desenho, 112.0, 162.0,
                  girar=90)

    mm_em_pe, porque = sangria.sangria_pela_tinta(em_pe)
    assert mm_em_pe == pytest.approx(3.0, abs=0.6), porque

    mm_girado, de_onde = sangria.sangria_pela_tinta(girado)
    assert mm_girado == pytest.approx(3.0, abs=0.6), de_onde


def test_sem_marca_de_corte_a_tinta_NAO_SABE_responder(tmp_path):
    """
    Sem marca nao se sabe ONDE se corta, e sem isso 'passou da linha' nao
    quer dizer nada. Responder aqui seria chutar.
    """
    arq = _pdf(str(tmp_path / "sem marca.pdf"), _chapado(0, 0, 106, 156))
    mm, porque = sangria.sangria_pela_tinta(arq)
    assert mm is None
    assert "marca de corte" in porque


def _marca_so_em_cima_e_embaixo(larg_mm, alt_mm, recuo):
    """Marca de corte so nos horizontais - os flancos ficam sem linha."""
    d = 3.0
    return "".join([
        _traco(0, recuo, d, recuo),
        _traco(larg_mm - d, recuo, larg_mm, recuo),
        _traco(0, alt_mm - recuo, d, alt_mm - recuo),
        _traco(larg_mm - d, alt_mm - recuo, larg_mm, alt_mm - recuo),
    ])


def test_lado_sem_marca_NAO_ENTRA_na_garantia(tmp_path):
    """
    Sangria e GARANTIA: o lado mais magro e o que aparece branco no
    impresso. Havendo marca so embaixo e em cima, os flancos nao foram
    conferidos por ninguem - e a conta respondia 'tem sangria de 3,0 mm'
    olhando dois lados e calando sobre os outros dois.

    Quando o que se mediu diz que TEM, mas nao se mediu tudo, a resposta
    honesta e 'nao da para garantir'.
    """
    arq = _pdf(str(tmp_path / "meia marca.pdf"),
               # sangra em cima e embaixo, e PARA 10 mm dentro nos flancos
               _chapado(13, 0, 80, 156)
               + _marca_so_em_cima_e_embaixo(106, 156, 3.0))
    mm, porque = sangria.sangria_pela_tinta(arq)
    assert mm is None, (mm, porque)
    assert "esquerda" in porque and "direita" in porque


def test_lado_conferido_que_NAO_tem_sangria_decide_sozinho(tmp_path):
    """
    O contrario da regra acima, e nao e simetrico: um lado sem sangria
    basta para o impresso sair com fio branco. Ai nao falta informacao -
    ja se sabe o bastante para dizer que NAO tem.
    """
    arq = _pdf(str(tmp_path / "pelado em cima.pdf"),
               _chapado(3, 3, 100, 150)
               + _marca_so_em_cima_e_embaixo(106, 156, 3.0))
    mm, porque = sangria.sangria_pela_tinta(arq)
    assert mm == pytest.approx(0.0, abs=0.6), porque


def test_pagina_em_branco_nao_inventa_sangria(tmp_path):
    arq = _pdf(str(tmp_path / "branco.pdf"),
               _marcas_de_corte(106, 156, 3.0))
    mm, porque = sangria.sangria_pela_tinta(arq)
    assert mm is None, porque


def test_arquivo_quebrado_nao_estoura(tmp_path):
    ruim = str(tmp_path / "ruim.pdf")
    open(ruim, "wb").write(b"isto nao e PDF")
    assert sangria.sangria_declarada(ruim)[0] is None
    assert sangria.sangria_pela_tinta(ruim)[0] is None
    assert sangria.ler_a_sangria(ruim)["tem"] is None


# ----------------------------------------------------------------------
# AS DUAS JUNTAS - e o que se diz quando elas discordam
# ----------------------------------------------------------------------

def test_a_medida_do_MEDIABOX_nao_e_a_que_se_MOSTRA(monkeypatch):
    """
    Sem BleedBox vale o MediaBox, que costuma incluir a area das marcas
    de corte: o CARTA_FRENTE de setembro daria 11,64 mm onde a sangria e
    3. As duas leituras CONCORDAM que tem sangria - entao nao ha
    divergencia para avisar -, e por isso o numero que aparece na tela
    tem de ser o medido, e nao o teto.
    """
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (11.64, sangria.DO_MEDIABOX))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (3.1, "da tinta"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["tem"] is True
    assert lido["divergem"] is False
    assert lido["mm"] == 3.1, "o teto do MediaBox nao e medida"
    # e os dois numeros continuam la, para quem quiser conferir
    assert lido["declarada"] == 11.64 and lido["pela_tinta"] == 3.1


def test_com_BLEEDBOX_quem_manda_e_a_caixa_declarada(monkeypatch):
    """
    Havendo BleedBox, a declaracao e exata e de graca - a tinta e medida
    numa imagem de 4 px/mm e traz o erro de arredondamento dela.
    """
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (3.0, sangria.DO_BLEEDBOX))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (2.76, "da tinta"))

    assert sangria.ler_a_sangria("qualquer.pdf")["mm"] == 3.0


def test_as_duas_concordando_a_resposta_e_uma(tmp_path, monkeypatch):
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (3.0, "do BleedBox"))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (2.8, "da tinta"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["tem"] is True
    assert lido["divergem"] is False
    assert lido["declarada"] == 3.0 and lido["pela_tinta"] == 2.8
    assert "as duas" in lido["de_onde"]


def test_as_duas_concordando_que_NAO_tem(tmp_path, monkeypatch):
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (0.0, "do BleedBox"))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (0.1, "da tinta"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["tem"] is False
    assert lido["divergem"] is False


def test_quando_DISCORDAM_o_sistema_fala_o_que_cada_uma_achou(monkeypatch):
    """
    O caso que engana: o arquivo DECLARA 3 mm e a arte para na linha de
    corte. Escolher um dos dois e calar poria o corte dentro do desenho -
    ou mandaria refazer sangria que ja existe.
    """
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (3.0, "do BleedBox"))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (0.0, "da tinta"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["divergem"] is True
    assert lido["tem"] is None, "nao se escolhe um e cala"
    assert "3" in lido["recado"] and "0" in lido["recado"]
    assert "declara" in lido["recado"].lower()
    assert "tinta" in lido["recado"].lower()


def test_sem_TrimBox_quem_responde_e_a_TINTA(monkeypatch):
    """O checkbox do ticket: nao declarar nao vira 'sem sangria'."""
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (None, "sem TrimBox"))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (3.0, "da tinta"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["tem"] is True
    assert lido["divergem"] is False
    assert "tinta" in lido["de_onde"]


def test_sem_TrimBox_e_sem_marca_a_resposta_e_NAO_SEI(monkeypatch):
    """
    Nao declarou e nao da para medir. A FIA para e diz - e nao responde
    'sem sangria', que e o que faria alguem montar errado achando que
    sabia.
    """
    monkeypatch.setattr(sangria, "sangria_declarada",
                        lambda pdf, pagina=1: (None, "sem TrimBox"))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda pdf, pagina=1: (None, "sem marca de corte"))

    lido = sangria.ler_a_sangria("qualquer.pdf")
    assert lido["tem"] is None
    assert lido["divergem"] is False
    assert "TrimBox" in lido["recado"] and "marca de corte" in lido["recado"]


def test_arquivo_sangrado_de_VERDADE_passa_pelos_dois_caminhos(tmp_path):
    """
    Sem nada substituido: as caixas dizem 3 mm, a tinta mostra 3 mm, e os
    dois caminhos chegam juntos na mesma resposta.
    """
    arq = _pdf(str(tmp_path / "de verdade.pdf"),
               _chapado(0, 0, 106, 156) + _marcas_de_corte(106, 156, 3.0),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))
    lido = sangria.ler_a_sangria(arq)
    assert lido["tem"] is True, lido
    assert lido["divergem"] is False, lido["recado"]
    assert lido["declarada"] == pytest.approx(3.0, abs=0.02)
    assert lido["pela_tinta"] == pytest.approx(3.0, abs=0.6)


def test_arquivo_que_MENTE_e_pego_pelos_dois_caminhos(tmp_path):
    """
    O arquivo que engana, montado de verdade: declara TrimBox 3 mm dentro
    da BleedBox, e a arte para na linha de corte. Nenhum dos dois
    caminhos sozinho pegaria isso - o primeiro diria sangrado, o segundo
    nao saberia da declaracao.
    """
    arq = _pdf(str(tmp_path / "mentiroso.pdf"),
               _chapado(3, 3, 100, 150) + _marcas_de_corte(106, 156, 3.0),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))
    lido = sangria.ler_a_sangria(arq)
    assert lido["divergem"] is True, lido
    assert lido["tem"] is None
    assert lido["declarada"] == pytest.approx(3.0, abs=0.02)
    assert lido["pela_tinta"] == pytest.approx(0.0, abs=0.6)


# ----------------------------------------------------------------------
# O QUE O ARQUIVO TEM, CONTRA O QUE ELE DIZ TER
#
# 18/09/2026, o 'LEILOES PANFLETO' da AMERICA: declarava 12,70 mm e a
# sangria saiu BRANCA na chapa. Ele nao traz BleedBox, e sem ela o pypdf
# devolve o MediaBox - que naquele arquivo e a area das MARCAS DE CORTE.
#
# A leitura da tela ja acusava ("AS DUAS LEITURAS DISCORDAM"). Quem nao
# perguntava era o caminho da montagem.
# ----------------------------------------------------------------------


def test_area_das_MARCAS_nao_vale_como_sangria(tmp_path):
    """
    O caso exato do panfleto: margem de 12,7 mm que so tem marca de
    corte, e arte parando na linha de corte.

    Quem pergunta "quanto tem?" para construir em cima nao pode ouvir
    12,7 - construiria nada e chamaria de sangria.
    """
    larg, alt, recuo = 106.0, 156.0, 12.7
    pdf = _pdf(str(tmp_path / "marcas.pdf"),
               _marcas_de_corte(larg, alt, recuo)
               + _chapado(recuo, recuo, larg - 2 * recuo, alt - 2 * recuo),
               larg_mm=larg, alt_mm=alt,
               corte=(recuo, recuo, larg - 2 * recuo, alt - 2 * recuo))

    # a conta velha acredita na caixa
    assert sangria.sangria_do_arquivo(pdf) == pytest.approx(recuo, abs=0.1)

    # a nova pergunta a tinta
    mm, de_onde = sangria.sangria_que_existe(pdf)
    assert mm < 1.0, "a margem e papel: %s mm (%s)" % (mm, de_onde)


def test_BLEEDBOX_declarada_MANDA_e_nao_custa_rasterizar(tmp_path,
                                                         monkeypatch):
    """
    Arquivo bem feito nao paga pela desconfianca. Havendo BleedBox, ela
    foi posta de proposito por quem fez o arquivo e e exata - perguntar
    a tinta ali seria gastar segundos de Ghostscript para chegar num
    numero pior.
    """
    pdf = _pdf(str(tmp_path / "bom.pdf"),
               _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150), sangra=(0, 0, 106, 156))

    def nao_deveria(*a, **k):
        raise AssertionError("nao era para rasterizar")

    monkeypatch.setattr(sangria, "sangria_pela_tinta", nao_deveria)

    mm, de_onde = sangria.sangria_que_existe(pdf)
    assert mm == pytest.approx(3.0, abs=0.01)
    assert de_onde == sangria.DO_BLEEDBOX


def test_a_TINTA_CALADA_devolve_o_que_o_arquivo_DIZ(tmp_path, monkeypatch):
    """
    Nao sabendo, vale a declaracao - e isto e escolha, nao descuido.

    Quem chama esta funcao vai DESENHAR com o numero, e nao ha como
    desenhar um talvez. Chutar zero mandaria inventar sangria por cima
    da que o designer talvez ja tenha desenhado, duplicando a arte dele.
    """
    pdf = _pdf(str(tmp_path / "mudo.pdf"), _chapado(0, 0, 106, 156),
               corte=(3, 3, 100, 150))
    monkeypatch.setattr(sangria, "sangria_pela_tinta",
                        lambda *a, **k: (None, "nao achei marca de corte"))

    mm, _ = sangria.sangria_que_existe(pdf)
    assert mm == pytest.approx(3.0, abs=0.01)


def test_o_numero_DA_TELA_e_o_numero_DA_MONTAGEM(tmp_path):
    """
    Duas regras parecidas em lugares diferentes e como nasce o dia em
    que a tela diz uma coisa e a chapa sai outra. A da tela e o
    ler_a_sangria()['mm']; a da montagem e o sangria_que_existe. Elas
    tem de bater.
    """
    larg, alt, recuo = 106.0, 156.0, 12.7
    pdf = _pdf(str(tmp_path / "igual.pdf"),
               _marcas_de_corte(larg, alt, recuo)
               + _chapado(recuo, recuo, larg - 2 * recuo, alt - 2 * recuo),
               larg_mm=larg, alt_mm=alt,
               corte=(recuo, recuo, larg - 2 * recuo, alt - 2 * recuo))

    da_tela = sangria.ler_a_sangria(pdf)["mm"]
    da_montagem, _ = sangria.sangria_que_existe(pdf)
    assert da_tela == pytest.approx(da_montagem, abs=0.01)
