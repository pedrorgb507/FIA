# -*- coding: utf-8 -*-
"""
O padrao temporario do FIALHO BRINDES.

So anda o que chega em PDF ja no tamanho da chapa (510x400 ou 730x600).
O resto - Corel, arte fora de medida - para e vira pendencia.

Os nomes usados aqui sao os arquivos de verdade da pasta do cliente.
"""

import os

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.nomes import nome_saida_fialho


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# O NOME INTEIRO DO ARQUIVO - 14/09/2026
# ----------------------------------------------------------------------
# "eles estao mandando arquivos parecidos, muda o nome, entao vamos
# manter o padrao tamanho da chapa, FIALHO, cmyk, so que no final coloca
# o nome completo do arquivo, sem limites de caracteres" - o operador.
#
# A regra anterior resumia o nome a uma palavra 'principal'. A ideia era
# boa e o efeito foi ruim: o Fialho manda muitos arquivos parecidos do
# mesmo cliente final, e o resumo os colapsava no MESMO nome de chapa.

def test_o_nome_do_arquivo_vai_inteiro():
    assert (nome_saida_fialho("FORRO AGENDA unicidades  2027.pdf",
                              "510x400", set("CMYK"))
            == "510x400_FIALHO_CMYK_FORRO AGENDA unicidades 2027")


def test_as_cores_entram_no_nome_como_nos_outros_clientes():
    """VOPRIX, EMPORIO e VIVA ja traziam as tintas. O Fialho ficou igual."""
    assert (nome_saida_fialho("capa.pdf", "510x400", {"K"})
            == "510x400_FIALHO_K_capa")
    assert (nome_saida_fialho("capa.pdf", "510x400", {"C", "M"})
            == "510x400_FIALHO_CM_capa")
    # sem tinta nenhuma nao acontece na pratica, mas nao pode sair vazio
    assert (nome_saida_fialho("capa.pdf", "510x400", set())
            == "510x400_FIALHO_K_capa")


def test_DOIS_ARQUIVOS_PARECIDOS_NAO_COLIDEM_MAIS():
    """
    O caso que derrubou a regra antiga, em 14/09/2026.

    'AGENDA_2027_ CREDI COMIGO capa.pdf' e
    'AGENDA_CADERNO 2027_ CREDI COMIGO.pdf' sao dois servicos diferentes,
    e os dois viravam '510x400_FIALHO_CREDI COMIGO'. Como a numeracao
    olha o que ja esta na pasta, a segunda leva do dia saiu ' 02' e
    ' 03' - um servico de duas paginas com numeracao de tres chapas.
    """
    a = nome_saida_fialho("AGENDA_2027_ CREDI COMIGO capa.pdf",
                          "510x400", set("CMYK"))
    b = nome_saida_fialho("AGENDA_CADERNO 2027_ CREDI COMIGO.pdf",
                          "510x400", set("CMYK"))
    assert a != b, "os dois voltaram a colidir"
    assert a == "510x400_FIALHO_CMYK_AGENDA_2027_ CREDI COMIGO capa"
    assert b == "510x400_FIALHO_CMYK_AGENDA_CADERNO 2027_ CREDI COMIGO"


def test_nome_comprido_NAO_E_CORTADO():
    """
    "sem limites de caracteres". Quem corta perde justamente o pedaco
    que distingue dois arquivos parecidos - que e o defeito que esta
    regra veio consertar.
    """
    n = ("MIOLO caderno sicoob montagen formato 48x66 9 imagem "
         "2 chapas.pdf")
    saida = nome_saida_fialho(n, "730x600", set("CMYK"))
    assert saida == ("730x600_FIALHO_CMYK_MIOLO caderno sicoob montagen "
                     "formato 48x66 9 imagem 2 chapas")
    assert len(saida) > 60


def test_acento_e_caractere_proibido_continuam_caindo():
    """
    O nome vai inteiro, mas ainda passa pelo finalizar: acento em nome de
    chapa e pedido de encrenca - o arquivo atravessa a rede, o RIP e o
    InDesign, e nem todos leem UTF-8 do mesmo jeito.
    """
    assert (nome_saida_fialho("INTRODUÇÃO  unicidades.pdf", "510x400", {"K"})
            == "510x400_FIALHO_K_INTRODUCAO unicidades")
    n = "biocromo  envelope  15,5x22 sem janela com nº.pdf"
    saida = nome_saida_fialho(n, "510x400", {"K"})
    assert "º" not in saida and "  " not in saida
    assert saida.startswith("510x400_FIALHO_K_biocromo envelope")


def test_a_sequencia_entra_no_fim():
    assert (nome_saida_fialho("capa unicidades.pdf", "510x400", {"K"}, 1)
            == "510x400_FIALHO_K_capa unicidades_01")
    assert (nome_saida_fialho("capa unicidades.pdf", "510x400", {"K"}, 12)
            == "510x400_FIALHO_K_capa unicidades_12")


# ----------------------------------------------------------------------
# A sequencia e do dia, nao do arquivo
# ----------------------------------------------------------------------

def test_sequencia_continua_de_onde_o_dia_parou(tmp_path):
    """
    As 11 chapas de UNICIDADES sairam 01 a 11 vindo de tres PDFs. Entao a
    contagem olha a pasta do dia, e nao a pagina do arquivo.
    """
    for n in ("510x400_FIALHO_UNICIDADES_01.pdf",
              "510x400_FIALHO_UNICIDADES_02.pdf",
              "510x400_FIALHO_UNICIDADES_03.pdf"):
        (tmp_path / n).write_bytes(b"chapa")

    assert P.proxima_sequencia(str(tmp_path),
                               "510x400_FIALHO_UNICIDADES") == 4


def test_sequencia_nao_confunde_trabalhos_diferentes(tmp_path):
    (tmp_path / "510x400_FIALHO_UNICIDADES_07.pdf").write_bytes(b"x")
    (tmp_path / "730x600_FIALHO_SICOOB_02.pdf").write_bytes(b"x")

    assert P.proxima_sequencia(str(tmp_path), "730x600_FIALHO_SICOOB") == 3
    assert P.proxima_sequencia(str(tmp_path), "510x400_FIALHO_PAULISTA") == 1


def test_sequencia_em_pasta_que_nem_existe(tmp_path):
    assert P.proxima_sequencia(str(tmp_path / "nao_existe"), "x") == 1


def test_chapa_sozinha_nao_leva_numero(tmp_path):
    """Numero so faz sentido quando ha mais de uma chapa com o mesmo nome."""
    base = "510x400_FIALHO_PAULISTA"
    novo, renumerada = P.numerar_se_preciso(str(tmp_path), base)
    assert novo == base and renumerada is None


def test_segunda_chapa_numera_as_duas(tmp_path):
    """
    Chegando a segunda, a primeira - ja gravada - vira 01 e a nova sai 02.
    Uma com nome limpo e outra numerada esconderia que sao duas.
    """
    base = "510x400_FIALHO_UNICIDADES"
    (tmp_path / (base + ".pdf")).write_bytes(b"primeira")

    novo, renumerada = P.numerar_se_preciso(str(tmp_path), base)

    assert novo == base + "_02"
    assert renumerada == (base + ".pdf", base + "_01.pdf")
    assert (tmp_path / (base + "_01.pdf")).read_bytes() == b"primeira"
    assert not (tmp_path / (base + ".pdf")).exists()


def test_terceira_continua_a_serie(tmp_path):
    base = "510x400_FIALHO_UNICIDADES"
    (tmp_path / (base + "_01.pdf")).write_bytes(b"a")
    (tmp_path / (base + "_02.pdf")).write_bytes(b"b")

    novo, renumerada = P.numerar_se_preciso(str(tmp_path), base)
    assert novo == base + "_03" and renumerada is None


def test_a_serie_ANTIGA_com_espaco_continua_sendo_lida(tmp_path):
    """
    O separador virou '_' em 17/09/2026, mas as chapas gravadas antes
    estao na pasta com ESPACO. Quem le tem de aceitar os dois.

    Sem isso a serie recomecaria do 01 e a chapa nova gravaria por cima
    de uma que ja saiu - e ninguem olhando a pasta saberia.
    """
    base = "510x400_FIALHO_UNICIDADES"
    (tmp_path / (base + " 01.pdf")).write_bytes(b"a")
    (tmp_path / (base + " 02.pdf")).write_bytes(b"b")

    novo, renumerada = P.numerar_se_preciso(str(tmp_path), base)
    assert novo == base + "_03", "continua a serie, com o separador novo"
    assert renumerada is None


def test_arquivo_de_varias_paginas_ja_nasce_numerado(tmp_path):
    """Aqui se sabe, antes de gravar, que virao outras paginas."""
    base = "730x600_FIALHO_SICOOB"
    novo, renumerada = P.numerar_se_preciso(str(tmp_path), base, forcar=True)
    assert novo == base + "_01" and renumerada is None


def test_nome_da_chapa_do_fialho_sai_sem_numero():
    """Quem numera e o laco, olhando a pasta - o nome sai limpo."""
    assert (P.nome_da_chapa(P.FIALHO, "INTRODUÇÃO  unicidades.pdf", "",
                            510, 400, set("CMYK"), 0, 2, None)
            == "510x400_FIALHO_CMYK_INTRODUCAO unicidades")


# ----------------------------------------------------------------------
# Formatos: a tabela do Fialho e outra
# ----------------------------------------------------------------------

def test_chapa_grande_do_fialho_e_730x600():
    assert P.identificar_formato(730, 600, P.FIALHO) == (800, "")
    assert P.identificar_formato(600, 730, P.FIALHO) == (800, "")   # deitado
    assert P.identificar_formato(510, 400, P.FIALHO) == (1000, "")


def test_formato_da_solida_nao_vale_no_fialho():
    """775x635 e chapa da Solida; no Fialho nao existe."""
    assert P.identificar_formato(775, 635, P.FIALHO) == (None, None)
    assert P.identificar_formato(730, 600) == (None, None)


def test_520x400_nao_bate_exato_mas_encaixa():
    """O CAPA Agenda PAULISTA mede 520x400: 10 mm fora, e chapa 510x400."""
    assert P.identificar_formato(520, 400, P.FIALHO) == (None, None)
    assert P.encaixar_formato(520, 400, P.FIALHO) == (510, 400)

    chapa, dpi, _, encaixou = P.chapa_da_pagina(520, 400, P.FIALHO)
    assert (chapa, dpi, encaixou) == ((510, 400), 1000, True)


def test_encaixe_respeita_o_sentido_da_arte():
    """Arte em pe encaixa na chapa em pe: nada e girado nem esticado."""
    chapa, _, _, encaixou = P.chapa_da_pagina(400, 520, P.FIALHO)
    assert chapa == (400, 510) and encaixou


def test_arte_longe_da_chapa_nao_encaixa():
    """Acima do limite ninguem sabe o que pode ser cortado."""
    assert P.encaixar_formato(600, 400, P.FIALHO) is None
    assert P.chapa_da_pagina(600, 400, P.FIALHO)[1] is None


def test_encaixe_nao_vale_para_os_outros_clientes():
    """Corte as cegas so foi combinado com o Fialho."""
    assert P.encaixar_formato(520, 400, P.SOLIDA) is None
    assert P.encaixar_formato(520, 400, P.VOPRIX) is None
    assert P.chapa_da_pagina(520, 400, P.SOLIDA)[1] is None


def test_medida_exata_nao_mexe_no_tamanho_da_arte():
    """
    A arte que tem MESMO a medida da chapa sai do tamanho dela, sem
    passar por encaixe nenhum. 0,0006 mm e o desvio de arredondamento
    que 161 das 162 chapas ja fechadas mostram.
    """
    chapa, dpi, _, encaixou = P.chapa_da_pagina(510.0, 400.0006, P.FIALHO)
    assert chapa == (510.0, 400.0006) and dpi == 1000 and not encaixou


def test_arte_POUCOS_MILIMETROS_fora_entra_centralizada_na_chapa():
    """
    Mudou em 14/09/2026, a pedido do operador. Antes, 512x398 virava uma
    chapa de 512x398 - torta, com nome de 510x400, e sem preco: a busca
    no GEREMPRE e exata e nao ha 398x512 na tabela.
    """
    chapa, dpi, _, encaixou = P.chapa_da_pagina(512, 398, P.FIALHO)
    assert chapa == (510, 400), "a chapa e a CADASTRADA, nao a da arte"
    assert encaixou is True, "sem isto a arte nao e centralizada"
    assert dpi == 1000


def test_etiqueta_sai_mesmo_quando_a_arte_so_encaixa():
    assert P.rotulo_prova(520, 400, P.FIALHO) == "FIALHO F4"


def test_etiqueta_da_prova_do_fialho():
    assert P.rotulo_prova(510, 400, P.FIALHO) == "FIALHO F4"
    assert P.rotulo_prova(730, 600, P.FIALHO) == "FIALHO F2"


# ----------------------------------------------------------------------
# O que nao esta no padrao para aqui
# ----------------------------------------------------------------------

def test_corel_do_fialho_nao_anda_E_NAO_GRITA(monkeypatch, tmp_path):
    """
    O .cdr para, e o aviso e BAIXO - recado, nao tela cheia.

    "se o arquivo vier, sem estar montado, em varias paginas, ou em .cdr,
    voce so baixa pelo whatssap dentro da pasta, mais nao da andamento em
    montagem, SO AVISA que tem um arquivo la esperando analise" - o
    operador, 17/09/2026.

    Ate esse dia isto abria a tela cheia de pendencia. Arte por montar da
    FIALHO nao esta errada: e trabalho normal esperando a vez de alguem
    montar. Gritar por isso e o defeito do verniz outra vez.
    """
    cdr = tmp_path / "CALENDARIO SICRED MONTAGEM.cdr"
    cdr.write_bytes(b"cdr")
    recados, gritos = [], []
    monkeypatch.setattr(P, "anotar_no_arquivo",
                        lambda arq, motivo, cliente=None: recados.append(motivo))
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: gritos.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a, **k: pytest.fail("Fialho nao converte ainda"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.FIALHO)

    assert r["status"] == "erro"
    assert "nao em PDF" in r["motivo"]
    assert "ESPERANDO ANALISE" in recados[0]
    assert gritos == [], "arte por montar nao abre tela cheia"


def test_o_corel_da_VIVA_continua_gritando(monkeypatch, tmp_path):
    """
    O tom baixo e SO da FIALHO - ela e que manda arte por montar.

    Na VIVA um .cdr e coisa fora do combinado, e continua sendo
    pendencia. Silenciar as duas de uma vez seria inventar regra que
    ninguem pediu.
    """
    cdr = tmp_path / "GRADE 1234.cdr"
    cdr.write_bytes(b"cdr")
    gritos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: gritos.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a, **k: pytest.fail("Viva nao converte"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VIVA)

    assert r["status"] == "erro"
    assert gritos and "montagem ainda e na mao" in gritos[0]


def test_fialho_nao_exige_numero_de_os(monkeypatch, tmp_path):
    """A regra da OS e da Solida: os nomes do Fialho nao tem numero."""
    pdf = tmp_path / "FORRO AGENDA unicidades  2027.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(pdf), str(tmp_path / "saida"), P.FIALHO)
    assert "nao achei numero de OS" not in r["motivo"]


def test_520x400_fecha_centralizado_na_510x400(monkeypatch, tmp_path):
    """O CAPA Agenda PAULISTA: entra centralizado, 5 mm cortados por lado."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(520, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .1, "M": .1, "Y": .1, "K": .1}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, chapa=(larg, alt), alvo=alvo, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("nao e mais pendencia"))

    r = P._processar_pdf("x.pdf", "CAPA Agenda PAULISTA  2027.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert (feito["base"]
            == "510x400_FIALHO_CMYK_CAPA Agenda PAULISTA 2027")
    assert feito["chapa"] == (510, 400)                    # pagina do PDF
    assert feito["alvo"] == (20079, 15748)                 # 510x400 a 1000 dpi


def test_pagina_fora_da_medida_para_E_ESPERA_ANALISE(monkeypatch, tmp_path):
    """
    600x400 nao e chapa da FIALHO: continua parando, agora sem gritar.

    Fora do tamanho da chapa e o sinal de ARTE POR MONTAR - e o segundo
    dos dois sinais que o operador listou, junto com o .cdr.
    """
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(600, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .1, "M": .1, "Y": .1, "K": .1}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    recados, gritos = [], []
    monkeypatch.setattr(P, "anotar_no_arquivo",
                        lambda arq, motivo, cliente=None: recados.append(motivo))
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: gritos.append(motivo))

    r = P._processar_pdf("x.pdf", "arte torta.pdf", str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "erro" and r["saidas"] == []
    assert "600 x 400 mm nao e chapa" in recados[0]
    assert "510x400" in recados[0] and "730x600" in recados[0]
    assert "POR MONTAR" in recados[0] and "Nao dei andamento" in recados[0]
    assert gritos == []


def test_a_pagina_fora_da_medida_de_OUTRO_cliente_continua_pendencia(
        monkeypatch, tmp_path):
    """A trava nova e da FIALHO; no EMPORIO chapa errada e defeito."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(600, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .1, "M": .1, "Y": .1, "K": .1}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    gritos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo=None, cliente=None: gritos.append(motivo))

    P._processar_pdf("x.pdf", "01234 - torta.pdf", str(tmp_path), P.EMPORIO,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m: None)

    assert gritos and "nao e chapa" in gritos[0]


def test_pdf_no_tamanho_certo_fecha(monkeypatch, tmp_path):
    """730x600, o miolo do SICOOB: caminho normal, chapa gerada."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(730, 600), (730, 600)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .2, "M": .2, "Y": .2, "K": .1}] * 2)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feitos.append((base, dpi))
        alvo = os.path.join(saida, base + ".pdf")
        open(alvo, "wb").write(b"chapa")
        return alvo, ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("nao e pendencia"))

    r = P._processar_pdf("x.pdf", "MIOLO caderno sicoob 48x66.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert feitos == [("730x600_FIALHO_CMYK_MIOLO caderno sicoob 48x66_01",
                       800),
                      ("730x600_FIALHO_CMYK_MIOLO caderno sicoob 48x66_02",
                       800)]


# ----------------------------------------------------------------------
# PRETO PURO NAO TEM LISTA DE CLIENTE - 14/09/2026
# ----------------------------------------------------------------------
# "todos os arquivos que vierem somente no canal do preto faca assim, de
# todos os clientes" - o operador. Arte inteira no K e um fato do
# ARQUIVO; nao interessa quem mandou.
#
# O preto COMPOSTO continua por cliente conhecido: ali o arquivo tem as
# quatro tintas escritas dentro dele e somos nos que decidimos, pela
# cobertura, que aquilo era uma chapa so.

def test_fialho_so_no_canal_do_preto_sai_em_UMA_chapa(monkeypatch, tmp_path):
    """Preto puro: uma chapa em cinza, sem perfil, de qualquer cliente."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": 0, "M": 0, "Y": 0, "K": .42}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "sem_cor_gritante", lambda *a, **k: True)
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feitos.append({"base": base, "usadas": set(usadas), "cinza": cinza,
                       "preto_puro": preto_puro})
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("nao e pendencia"))

    r = P._processar_pdf("x.pdf", "FORRO AGENDA unicidades  2027.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert feitos[0]["cinza"] is True
    assert feitos[0]["preto_puro"] is True,         "sem isso a chapa sai pelo perfil e o chapado cai para 87,45%"
    assert feitos[0]["usadas"] == {"GRAY"}
    # UMA chapa na OS, nao quatro
    assert r["chapas"] == [{"chapa": [510, 400], "tintas": 1}]
    assert feitos[0]["base"] ==         "510x400_FIALHO_GRAY_FORRO AGENDA unicidades 2027"


def test_fialho_com_preto_COMPOSTO_continua_em_quadricromia(monkeypatch,
                                                            tmp_path):
    """
    A outra metade da regra. O composto funde quatro chapas numa, e isso
    so anda em cliente conhecido - a FIALHO manda quadricromia de
    verdade (as capas de 14/09/2026 medem C 0,42 M 0,35 Y 0,42 K 0,41).
    """
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(
        P, "cobertura_por_pagina",
        lambda pdf, sem_icc=False: [{"C": .06081, "M": .06079,
                                     "Y": .06080, "K": .05444}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "sem_cor_gritante",
                        lambda *a, **k: pytest.fail(
                            "composto da FIALHO nem chega a ser perguntado"))
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feitos.append({"base": base, "cinza": cinza, "preto_puro": preto_puro})
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    r = P._processar_pdf("x.pdf", "FORRO AGENDA unicidades  2027.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert feitos[0]["cinza"] is False
    assert feitos[0]["preto_puro"] is False
    assert r["chapas"] == [{"chapa": [510, 400], "tintas": 4}]


# ----------------------------------------------------------------------
# Monitor
# ----------------------------------------------------------------------

def test_monitor_vigia_as_pastas_de_todos(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", r"V:\VOPRIX")
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", r"V:\Fialho Brindes")
    monkeypatch.setattr(M, "BASE_ENTRADA_EMPORIO", r"V:\Emporio PRINT")
    monkeypatch.setattr(M, "BASE_ENTRADA_VIVA", r"V:\VIVA ACABAMENTOS")
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", r"V:\Creative")
    monkeypatch.setattr(M, "BASE_ENTRADA_PRIME", r"V:\Prime  Graf")
    lista = M.clientes()
    assert [c[0] for c in lista] == [M.SOLIDA, M.VOPRIX, M.FIALHO,
                                     M.EMPORIO, M.VIVA, M.CREATIVE,
                                     M.PRIME]
    assert lista[2][2] == (".pdf", ".cdr")     # o .cdr entra so para avisar
    assert lista[3][2] == (".pdf",)            # o Emporio so manda PDF
    assert lista[4][2] == (".pdf", ".cdr")     # a VIVA manda os dois
    assert lista[5][2] == (".pdf", ".cdr")     # a Creative, como o Fialho
    # a PRIME manda .cdr; o .pdf entra so para nao passar despercebido
    assert lista[6][2] == (".cdr", ".pdf")


def test_varrer_do_fialho_ve_pdf_e_cdr(monkeypatch, tmp_path):
    (tmp_path / "FORRO AGENDA unicidades  2027.pdf").write_bytes(b"x")
    (tmp_path / "CALENDARIO SICRED MONTAGEM.cdr").write_bytes(b"x")
    (tmp_path / "planilha.xlsx").write_bytes(b"x")

    vistos = []
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente, **k: (
        vistos.append(os.path.basename(caminho))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.FIALHO, (".pdf", ".cdr"))

    assert sorted(vistos) == ["CALENDARIO SICRED MONTAGEM.cdr",
                              "FORRO AGENDA unicidades  2027.pdf"]


# ----------------------------------------------------------------------
# O corte, em pixel
# ----------------------------------------------------------------------

def _imagem_da_chapa(pdf):
    """(largura, altura, bytes) da imagem que ficou dentro do PDF."""
    import re
    import zlib
    dados = open(pdf, "rb").read()
    cab = re.search(rb"/Width (\d+) /Height (\d+)", dados)
    w, h = int(cab.group(1)), int(cab.group(2))
    inicio = dados.index(b"stream\n", cab.end()) + 7
    fim = dados.index(b"\nendstream", inicio)
    return w, h, zlib.decompress(dados[inicio:fim])


def test_arte_maior_e_cortada_igual_dos_dois_lados(tmp_path):
    """Arte 100 de largura na chapa de 80: some 10 de cada lado."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    arte = Image.new("L", (100, 40), 128)
    for x in range(100):
        arte.putpixel((x, 0), x)            # regua para saber o que sobrou
    tif = str(tmp_path / "arte.tif")
    arte.save(tif)

    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400, alvo=(80, 40))

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (80, 40)
    primeira_linha = px[:80]
    assert primeira_linha[0] == 10          # os 10 primeiros foram cortados
    assert primeira_linha[-1] == 89         # e os 10 ultimos tambem


def test_arte_menor_ganha_branco_em_volta(tmp_path):
    """Arte 60 de largura na chapa de 80: 10 de branco de cada lado."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    arte = Image.new("L", (60, 20), 0)      # tudo preto, para o branco saltar
    tif = str(tmp_path / "arte.tif")
    arte.save(tif)

    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400, alvo=(80, 30))

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (80, 30)
    assert px[:80] == b"\xff" * 80          # faixa de cima: branca inteira
    meio = px[15 * 80:16 * 80]              # linha no meio da arte
    assert meio[:10] == b"\xff" * 10        # borda esquerda branca
    assert meio[10:70] == b"\x00" * 60      # arte preta no centro
    assert meio[70:] == b"\xff" * 10        # borda direita branca


def test_sem_alvo_a_imagem_sai_do_tamanho_que_entrou(tmp_path):
    """Quem bate na medida exata nao passa por corte nenhum."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    tif = str(tmp_path / "arte.tif")
    Image.new("L", (50, 30), 77).save(tif)
    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400)

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (50, 30)
    assert px == b"\x4d" * (50 * 30)


# ----------------------------------------------------------------------
# A PASTA 'PARA CTP' DA FIALHO - 17/09/2026
#
# "quando o arquivo vier pelo whattsapp ja montado, no tamanho das chapas
# dele e pincado, coloca na pasta PARA CTP, e de dentro dessa pasta vc
# envia pro ctp, mais dessa vez, SEM DELETAR o arquivo la de dentro, ja
# que esse arquivo so vai ter uma copia" - o operador.
# ----------------------------------------------------------------------

def test_a_pasta_PARA_CTP_da_FIALHO_e_criada_sozinha(tmp_path):
    from finart_ctp import monitor as M
    dia = tmp_path / "Setembro" / "17"
    dia.mkdir(parents=True)
    M.garantir_portao("FIALHO", str(dia))
    assert (dia / "PARA CTP").is_dir()


def test_a_pasta_nao_e_criada_para_quem_nao_pediu(tmp_path):
    """
    A SOLIDA nao manda arte por montar - pasta a mais na pasta dela e
    bagunca que alguem vai ter de explicar.
    """
    from finart_ctp import monitor as M
    dia = tmp_path / "Setembro" / "17"
    dia.mkdir(parents=True)
    M.garantir_portao("SOLIDA", str(dia))
    assert not (dia / "PARA CTP").exists()


def test_criar_a_pasta_duas_vezes_nao_reclama(tmp_path):
    from finart_ctp import monitor as M
    dia = tmp_path / "Setembro" / "17"
    (dia / "PARA CTP").mkdir(parents=True)
    M.garantir_portao("FIALHO", str(dia))       # nao pode estourar
    assert (dia / "PARA CTP").is_dir()


def test_pasta_so_leitura_nao_derruba_o_dia(tmp_path, monkeypatch):
    """
    Pasta de cliente pode nos negar escrita. Isso e recado, nao parada:
    o resto do dia da FIALHO continua andando.
    """
    from finart_ctp import monitor as M
    dia = tmp_path / "Setembro" / "17"
    dia.mkdir(parents=True)

    def negar(*a, **k):
        raise OSError("Acesso negado")

    monkeypatch.setattr(M.os, "makedirs", negar)
    M.garantir_portao("FIALHO", str(dia))       # nao pode estourar


def test_o_que_esta_na_PARA_CTP_e_visto_pelo_vigia(tmp_path):
    """
    Nao precisou de codigo: o arquivos_do_dia ja varre subpasta.

    Este teste existe para PRENDER isso. Se um dia alguem trocar o
    os.walk por um listdir para 'simplificar', a PARA CTP da FIALHO para
    de ser lida e ninguem descobre ate faltar chapa.
    """
    from finart_ctp import monitor as M
    dia = tmp_path / "17"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    (portao / "CAPA AGENDA 2027.pdf").write_bytes(b"%PDF-1.4")
    (dia / "solto.pdf").write_bytes(b"%PDF-1.4")

    achados = {nome: rotulo for _, nome, rotulo in M.arquivos_do_dia(str(dia))}
    assert "CAPA AGENDA 2027.pdf" in achados
    assert achados["CAPA AGENDA 2027.pdf"] == os.path.join("PARA CTP",
                                                           "CAPA AGENDA 2027.pdf")
    assert "solto.pdf" in achados


def test_o_fluxo_comum_NAO_apaga_a_entrada(tmp_path, monkeypatch):
    """
    O "sem deletar o arquivo la de dentro" ja e verdade, e e o que separa
    a PARA CTP da FIALHO da PARA CTP da AMERICA - la o arquivo e apagado
    depois de gravado, porque a copia da casa fica na pasta do dia. Aqui
    nao ha segunda copia.
    """
    portao = tmp_path / "PARA CTP"
    portao.mkdir()
    arte = portao / "CAPA AGENDA 2027.pdf"
    arte.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .2, "M": .2, "Y": .2, "K": .2}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False,
              alvo=None, deslocamento=None, girar=0, preto_puro=False,
              do_corel=False):
        destino = os.path.join(saida, base + ".pdf")
        open(destino, "wb").write(b"chapa")
        return destino, ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    r = P._processar_pdf(str(arte), arte.name, str(tmp_path / "saida"),
                         P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert arte.exists(), "o arquivo do cliente TEM de continuar na pasta"


def test_varias_paginas_no_tamanho_da_chapa_continuam_andando(monkeypatch,
                                                              tmp_path):
    """
    Decisao do operador, 17/09/2026: "no tamanho da chapa, segue".

    'Varias paginas' so para quando as paginas NAO estao no tamanho da
    chapa - e ai o que para nao e a contagem, e o tamanho. Foi o
    AGENDA_2027_TOCANTINS capa.pdf, de duas paginas, que saiu como 01 e
    02 e esta certo assim.
    """
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400), (510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [{"C": .2, "M": .2, "Y": .2, "K": .2}] * 2)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False,
              alvo=None, deslocamento=None, girar=0, preto_puro=False,
              do_corel=False):
        feitos.append(base)
        destino = os.path.join(saida, base + ".pdf")
        open(destino, "wb").write(b"chapa")
        return destino, ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("nao podia ter parado"))
    monkeypatch.setattr(P, "anotar_no_arquivo",
                        lambda *a, **k: pytest.fail("nao podia nem ter avisado"))

    r = P._processar_pdf("x.pdf", "AGENDA_2027_ TOCANTINS capa.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert len(feitos) == 2, "duas paginas no tamanho da chapa sao duas chapas"


# ----------------------------------------------------------------------
# DENTRO DO PORTAO, A FIALHO E A VOPRIX - 17/09/2026, de tarde
#
# "o arquivo que salvei (...) vc vai fazer o mesmo processo que faz na
# VOPRIX, gerar um pdf, e mandar pro ctp, sendo que, cada pagina, num pdf
# diferente, diferenciando no final do nome com _01, _02 (...) ao
# finalizar tudo, apague o arquivo dentro da pasta PARA CTP" - o operador.
#
# A mesma arte PARA na pasta do dia e ANDA dentro da PARA CTP. Nao e
# contradicao: um .cdr solto na pasta do dia e arte por montar; dentro do
# portao e montagem pronta, que alguem acabou de fazer. A pasta e a
# assinatura - nao ha campo, nem marca no arquivo, nem tela para clicar.
# ----------------------------------------------------------------------

def test_o_cdr_no_PORTAO_da_FIALHO_e_convertido(monkeypatch, tmp_path):
    portao = tmp_path / "PARA CTP"
    portao.mkdir()
    cdr = portao / "calend de mesa UNICIDADES  2027.cdr"
    cdr.write_bytes(b"cdr")
    convertidos = []

    def converter(caminho):
        convertidos.append(caminho)
        pdf = str(tmp_path / "convertido.pdf")
        open(pdf, "wb").write(b"%PDF-1.4")
        return pdf, pdf

    monkeypatch.setattr(P, "converter_cdr", converter)
    monkeypatch.setattr(P, "_processar_pdf",
                        lambda *a, **k: {"status": "ok", "saidas": ["x.pdf"],
                                         "motivo": "", "impresso": None,
                                         "do_portao": k.get("do_portao")})

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.FIALHO)

    assert convertidos, "o .cdr do portao tem de passar pelo CorelDRAW"
    assert r["status"] == "ok"
    assert r["do_portao"] is True


def test_o_MESMO_cdr_na_pasta_do_dia_continua_esperando_analise(monkeypatch,
                                                                tmp_path):
    """A pasta e que muda a resposta - o arquivo e o mesmo."""
    cdr = tmp_path / "calend de mesa UNICIDADES  2027.cdr"
    cdr.write_bytes(b"cdr")
    recados = []
    monkeypatch.setattr(P, "anotar_no_arquivo",
                        lambda arq, motivo, cliente=None: recados.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a, **k: pytest.fail("fora do portao nao converte"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.FIALHO)

    assert r["status"] == "erro"
    assert "ESPERANDO ANALISE" in recados[0]


def test_dentro_do_portao_a_chapa_vai_pelo_CAMINHO_CURTO(monkeypatch, tmp_path):
    """
    Como a VOPRIX: o PDF vai inteiro, sem passar pelo Ghostscript.

    Nao e economia - e cor. O perfil ICC que a Corel embute remistura o
    preto do K nas quatro tintas quando alguem rasteriza. Ja custou uma
    chapa da VOPRIX em 09/09/2026.
    """
    portao = tmp_path / "PARA CTP"
    portao.mkdir()
    pdf = portao / "MONTAGEM UNICIDADES.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "medir_paginas", lambda p_: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda p_, sem_icc=False: [{"C": .2, "M": .2, "Y": .2, "K": .2}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("o portao vai pelo curto"))
    entregues = []

    def entregar(origem, pasta_saida, base, plano, total):
        entregues.append(base)
        destino = os.path.join(pasta_saida, base + ".pdf")
        os.makedirs(pasta_saida, exist_ok=True)
        open(destino, "wb").write(b"chapa")
        return destino, ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_entregar_chapa", entregar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    r = P._processar_pdf(str(pdf), pdf.name, str(tmp_path / "saida"), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m, **k: None,
                         do_portao=True)

    assert r["status"] == "ok"
    assert entregues, "tinha de ter entregado pelo caminho curto"


# ----------------------------------------------------------------------
# E O PORTAO SE ESVAZIA - mas a copia sobe antes
# ----------------------------------------------------------------------

def _portao_com_arquivo(tmp_path, conteudo=b"cdr"):
    dia = tmp_path / "Setembro" / "17"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    arq = portao / "calend de mesa UNICIDADES  2027.cdr"
    arq.write_bytes(conteudo)
    return dia, arq


def test_gravou_tudo_o_portao_se_esvazia_E_A_COPIA_SOBE(tmp_path):
    """
    "ao finalizar tudo, apague o arquivo dentro da pasta PARA CTP".

    E, no mesmo dia, "sem deletar o arquivo la de dentro, ja que esse
    arquivo so vai ter uma copia". As duas coisas convivem do jeito que a
    AMERICA ja resolvia: a copia SOBE para a pasta do dia, e so entao o
    portao e esvaziado. Nada se perde.
    """
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)

    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "ok", "saidas": ["510x400_FIALHO_x.pdf"]})

    assert not arq.exists(), "o portao tem de ficar vazio"
    assert (dia / arq.name).exists(), "e a copia tem de estar na pasta do dia"


def test_servico_que_NAO_terminou_fica_no_portao(tmp_path):
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)
    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "erro", "saidas": []})
    assert arq.exists()


def test_status_ok_SEM_chapa_nenhuma_tambem_fica(tmp_path):
    """'ok' com saidas vazias e servico que nao gravou nada."""
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)
    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "ok", "saidas": []})
    assert arq.exists()


def test_arquivo_fora_do_portao_nao_e_apagado_nunca(tmp_path):
    """
    A pasta de entrada e compartilhada e NADA e apagado dela.

    Esta e a regra mais antiga da casa, e o esvaziar do portao e a unica
    excecao - por isso ele confere a pasta antes de qualquer coisa.
    """
    from finart_ctp import monitor as M
    dia = tmp_path / "Setembro" / "17"
    dia.mkdir(parents=True)
    arq = dia / "solto.pdf"
    arq.write_bytes(b"%PDF-1.4")
    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "ok", "saidas": ["x.pdf"]})
    assert arq.exists()


def test_cliente_sem_portao_nao_tem_faxina(tmp_path):
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)
    M.esvaziar_o_portao(str(arq), arq.name, "SOLIDA",
                        {"status": "ok", "saidas": ["x.pdf"]})
    assert arq.exists()


def test_nao_conseguindo_guardar_a_copia_NAO_apaga(tmp_path, monkeypatch):
    """
    Perder a montagem e pior que portao cheio. Sem copia, nao apago.
    """
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)

    def negar(*a, **k):
        raise OSError("Acesso negado")

    monkeypatch.setattr(M.america, "guardar_copia", negar)
    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "ok", "saidas": ["x.pdf"]})
    assert arq.exists(), "sem copia guardada, o arquivo fica"


def test_a_faxina_nunca_estoura_para_cima(tmp_path, monkeypatch):
    """
    O registro JA foi salvo quando esta funcao roda. Se ela estourar, o
    laco do vigia morre com o trabalho ja feito e ninguem sabe onde
    parou.
    """
    from finart_ctp import monitor as M
    dia, arq = _portao_com_arquivo(tmp_path)

    def explodir(*a, **k):
        raise RuntimeError("disco sumiu")

    monkeypatch.setattr(M.os, "remove", explodir)
    M.esvaziar_o_portao(str(arq), arq.name, "FIALHO",
                        {"status": "ok", "saidas": ["x.pdf"]})   # nao estoura
