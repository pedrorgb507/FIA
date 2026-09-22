# -*- coding: utf-8 -*-
"""
O caminho da VOPRIX de ponta a ponta, sem CorelDRAW nem Ghostscript.

O que importa aqui: o .cdr passa pela Corel antes de tudo, o nome sai
pela regra da VOPRIX, o arquivo aberto na sessao do operador nao e
tocado, e o PDF temporario da conversao some no fim.
"""

import os
import shutil

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.corel import ArquivoEmUso

CDR = "Envelope_Saco_23x31,5_Colegio_Unus.cdr"


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    # teste nenhum pode escrever na pasta de pendencias da maquina de
    # verdade, nem no log: tudo vai para o tmp do pytest.
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# Formato e etiqueta
# ----------------------------------------------------------------------

def test_formato_no_nome():
    assert P.formato_no_nome(510, 400) == "510x400"
    assert P.formato_no_nome(400, 510) == "510x400"      # deitado
    assert P.formato_no_nome(775, 635) == "775x635"
    assert P.formato_no_nome(300, 200) == ""


def test_etiqueta_da_prova_diz_o_cliente():
    assert P.rotulo_prova(510, 400) == "SOLIDA F4"
    assert P.rotulo_prova(510, 400, P.VOPRIX) == "VOPRIX F4"
    assert P.rotulo_prova(300, 200, P.VOPRIX) == ""


def test_o_VOPRIX_SO_TEM_A_F4():
    """
    "voprix nao tem chapas 775x635 somente a solida" - o operador,
    11/09/2026.

    Ate esse dia o VOPRIX caia na tabela da SOLIDA por nao ter a sua, e
    com ela herdava a 775x635. Isso NAO dava erro em lugar nenhum - dava
    coisa pior: a FIA fechava a chapa grande e depois nao conseguia
    lancar a OS, porque GEREMPRE_CHAPAS so tem a 510x400 para ele. A
    gravacao ia para o CTP e ficava sem cobranca ate alguem ler a
    pendencia.

    Agora a medida para na ENTRADA, que e onde ela tem de parar: nao e
    chapa do VOPRIX, entao nao vira chapa nem prova.
    """
    from finart_ctp.config import FORMATOS_VOPRIX, GEREMPRE_CHAPAS

    assert list(FORMATOS_VOPRIX) == [(510, 400)]
    assert P.chapa_prevista(775, 635, P.VOPRIX) is None
    assert P.rotulo_prova(775, 635, P.VOPRIX) == ""

    # a razao de tudo: o que a FIA FECHA e o que ela sabe COBRAR tem de
    # ser a mesma lista. Fechar sem saber cobrar e o defeito calado.
    from finart_ctp.gerempre import chapa_do_servico
    for (l, a) in FORMATOS_VOPRIX:
        assert chapa_do_servico("VOPRIX", l, a), (l, a)
    assert ("VOPRIX", (775, 635)) not in GEREMPRE_CHAPAS


def test_todo_formato_que_a_FIA_FECHA_ela_sabe_COBRAR():
    """
    A regra que o VOPRIX quebrou, agora valendo para TODOS.

    Sao duas listas que precisam andar juntas e moram em lugares
    diferentes: FORMATOS_<cliente> diz o que vira chapa, e
    GEREMPRE_CHAPAS diz o que tem preco. Quando elas discordam, o
    servico e gravado e nao e lancado - e ninguem ve, porque a chapa sai
    perfeita.
    """
    from finart_ctp.gerempre import chapa_do_servico

    faltando = []
    for cliente in (P.SOLIDA, P.VOPRIX, P.FIALHO, P.EMPORIO, P.VIVA,
                    P.CREATIVE):
        for (l, a) in P.formatos_do_cliente(cliente):
            if not chapa_do_servico(cliente, l, a):
                faltando.append("%s %dx%d" % (cliente, l, a))
    assert not faltando, (
        "estes formatos viram chapa e nao tem como ser lancados: %s"
        % ", ".join(faltando))


# ----------------------------------------------------------------------
# Nome de saida: cada cliente com a sua regra
# ----------------------------------------------------------------------

def test_nome_da_chapa_por_cliente():
    assert P.nome_da_chapa(P.SOLIDA, "49576 - Cliente - x.pdf", "R1",
                           775, 635, {"C", "M"}, 0, 1) == "49576R1"
    assert P.nome_da_chapa(P.VOPRIX, CDR, "", 510, 400,
                           {"C", "M"}, 0, 1) == "510x400_CM_VOPRIX_COLEGIO_UNUS_envelope_saco"


def test_nome_da_chapa_voprix_com_duas_paginas():
    n = "Pasta_Bopp_Orelha_44x31_Colegio_Unus.cdr"
    assert (P.nome_da_chapa(P.VOPRIX, n, "", 510, 400, {"C"}, 1, 2)
            == "510x400_C_VOPRIX_COLEGIO_UNUS_pasta_bopp_orelha 02")


# ----------------------------------------------------------------------
# Conversao
# ----------------------------------------------------------------------

def test_cdr_aberto_no_corel_fica_para_depois(monkeypatch, tmp_path):
    """A regra que nasceu de erro: arquivo do operador nao se toca."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")

    def em_uso(_, achatar=False):
        raise ArquivoEmUso("'%s' esta aberto no CorelDRAW" % CDR)

    monkeypatch.setattr(P, "converter_cdr", em_uso)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("nao e pendencia, e so esperar"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "adiado"
    assert "CorelDRAW" in r["motivo"]


def test_corel_que_falha_vira_pendencia(monkeypatch, tmp_path):
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")

    def estourou(_):
        raise RuntimeError("CorelDRAW nao gerou o PDF")

    avisos = []
    monkeypatch.setattr(P, "converter_cdr", estourou)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: avisos.append(motivo))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert len(avisos) == 1 and "CorelDRAW" in avisos[0]


def test_temporario_da_conversao_e_apagado(monkeypatch, tmp_path):
    """Mesmo quando o PDF convertido nao presta, a pasta local nao fica."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 nem precisa ser valido")

    monkeypatch.setattr(P, "converter_cdr", lambda _, achatar=False: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"          # PDF ilegivel, o que interessa
    assert not os.path.exists(str(tmp))   # e a pasta local sumiu


def test_pdf_gigante_saido_da_corel_e_barrado(monkeypatch, tmp_path):
    """O caso real: .cdr de 375 MB que a Corel exportou como 2,2 GB."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 fingindo ser enorme")

    # o .cdr cabe; quem estoura o limite e o PDF que a Corel devolveu
    monkeypatch.setattr(P, "converter_cdr", lambda _, achatar=False: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "acima_do_limite",
                        lambda c: "" if c.lower().endswith(".cdr")
                        else "arquivo gigante: 2200 MB, acima do limite")
    monkeypatch.setattr(P, "medir_paginas",
                        lambda *a, **k: pytest.fail("nem deveria abrir o PDF"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: avisos.append((arq, motivo)))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert r["motivo"].startswith("depois de converter, ")
    assert avisos[0][0] == CDR            # a pendencia cita o .cdr original
    assert not os.path.exists(str(tmp))


def test_pdf_grande_demais_fica_guardado_para_a_mao(monkeypatch, tmp_path):
    """
    O que a Corel converteu nao se joga fora: vai para a pasta de
    pendencias, com o nome do original, para o operador seguir dali.
    """
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 os 547 MB da Corel")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _, achatar=False: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "acima_do_limite",
                        lambda c: "" if c.lower().endswith(".cdr")
                        else "arquivo gigante: 547 MB, acima do limite")
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_controle"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)

    guardado = pendencias / "Envelope_Saco_23x31,5_Colegio_Unus.pdf"
    assert guardado.exists(), "o PDF convertido se perdeu"
    assert r["pendencia"] == str(guardado)
    assert not os.path.exists(str(tmp))        # e a temporaria sumiu


def test_pdf_ilegivel_tambem_fica_guardado(monkeypatch, tmp_path):
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 quebrado")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _, achatar=False: (str(pdf), str(tmp)))
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_controle"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert (pendencias / "Envelope_Saco_23x31,5_Colegio_Unus.pdf").exists()


def test_quando_da_certo_nao_sobra_nada_guardado(monkeypatch, tmp_path):
    """Chapa gerada, PDF convertido descartado: a pasta nao vira deposito."""
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _, achatar=False: (str(pdf), str(tmp)))
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(P, "_processar_pdf",
                        lambda *a, **k: {"status": "ok", "saidas": ["x.pdf"],
                                    "motivo": "", "impresso": 1})

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "ok"
    assert not pendencias.exists()
    assert not os.path.exists(str(tmp))


def test_voprix_nao_precisa_de_os(monkeypatch, tmp_path):
    """O nome da VOPRIX nao tem OS - e isso nao pode barrar o arquivo."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    chamou = []

    def converteu(caminho, achatar=False):
        chamou.append(caminho)
        raise RuntimeError("parei aqui de proposito")

    monkeypatch.setattr(P, "converter_cdr", converteu)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert chamou, "barrou por falta de OS antes de tentar converter"
    assert "nao achei numero de OS" not in r["motivo"]


def test_pdf_da_voprix_nao_precisa_de_os_no_nome(monkeypatch, tmp_path):
    """
    O .pdf de cliente do Corel passa pela mesma porta que o .cdr dele.

    22/09/2026, `Folder_4_0_29,7x21,0_Ibccrim.pdf`: o achatamento tinha
    perdido 38% do K, o operador exportou o PDF certo a mao e o salvou
    na pasta - e a FIA o recusou dizendo "nao achei numero de OS no
    nome", que nao tem nada a ver com o que houve.

    Quem nomeia por OS e a SOLIDA. A VOPRIX e a PRIME nomeiam pelo
    servico, e o .cdr delas nunca caiu nessa pergunta porque sai no ramo
    do CorelDRAW antes. O .pdf caia - e em 85 arquivos desses dois
    clientes, nenhum .pdf tinha chegado para mostrar isso.
    """
    pdf = tmp_path / "Folder_4_0_29,7x21,0_Ibccrim.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    for cliente in (P.VOPRIX, P.PRIME):
        r = P.processar(str(pdf), str(tmp_path / "saida"), cliente)
        assert "nao achei numero de OS" not in (r["motivo"] or ""), (
            "%s: PDF dela nao tem OS no nome, e nao precisa ter" % cliente)


def test_solida_sem_os_continua_barrada(monkeypatch, tmp_path):
    """A regra da OS vale so para a SOLIDA, e continua valendo."""
    pdf = tmp_path / "sem numero nenhum.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(pdf), str(tmp_path / "saida"))
    assert r["status"] == "erro" and "nao achei numero de OS" in r["motivo"]


# ----------------------------------------------------------------------
# Monitor: duas pastas, uma saida
# ----------------------------------------------------------------------

def test_clientes_traz_as_duas_pastas(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", r"V:\VOPRIX")
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_EMPORIO", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_VIVA", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_PRIME", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_IDEAL", None)
    lista = M.clientes()
    assert [c[0] for c in lista] == [M.SOLIDA, M.VOPRIX]
    assert [c[2] for c in lista] == [(".pdf",), (".cdr", ".pdf")]


def test_a_voprix_enxerga_o_pdf_que_o_operador_exporta_a_mao(monkeypatch):
    """
    O .cdr e o que a VOPRIX manda, mas quando o achatamento perde tinta
    quem salva o servico e o PDF exportado A MAO na mesma pasta.

    22/09/2026, Folder_4_0_29,7x21,0_Ibccrim: o CorelDRAW perdeu 38% do
    K (0,0714 -> 0,0441), a trava recusou com razao, o operador exportou
    o PDF certo e o deixou na pasta - e a FIA nao olhava .pdf ali. O
    arquivo bom ficou INVISIVEL e o servico parou sem motivo aparente.

    Nao e afrouxar trava nenhuma: e o que a PRIME ja fazia, com o
    comentario dela dizendo "como a VOPRIX".
    """
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", r"V:\VOPRIX")
    for outro in ("FIALHO", "EMPORIO", "VIVA", "CREATIVE", "PRIME"):
        monkeypatch.setattr(M, "BASE_ENTRADA_" + outro, None)
    extensoes = dict((c[0], c[2]) for c in M.clientes())[M.VOPRIX]
    assert ".pdf" in extensoes, (
        "sem .pdf, o PDF que o operador exporta a mao nunca e visto")
    assert ".cdr" in extensoes, "o .cdr continua sendo o que ela manda"


def test_sem_pasta_da_voprix_fica_so_a_solida(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_EMPORIO", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_VIVA", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_CREATIVE", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_PRIME", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_IDEAL", None)
    assert [c[0] for c in M.clientes()] == [M.SOLIDA]


def test_varrer_so_pega_a_extensao_do_cliente(monkeypatch, tmp_path):
    (tmp_path / CDR).write_bytes(b"cdr")
    (tmp_path / "49572 - Cliente - flyer.pdf").write_bytes(b"pdf")

    vistos = []
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente, **k: (
        vistos.append((os.path.basename(caminho), cliente))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    registro = {}
    M.varrer(str(tmp_path), "Z:/saida", registro, None, M.VOPRIX, ".cdr")

    assert vistos == [(CDR, M.VOPRIX)]
    assert len(registro) == 1
    assert list(registro.values())[0]["cliente"] == M.VOPRIX


def test_adiado_nao_entra_no_registro(monkeypatch, tmp_path):
    (tmp_path / CDR).write_bytes(b"cdr")
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda *a, **k: {
        "status": "adiado", "saidas": [], "motivo": "aberto no CorelDRAW"})

    registro = {}
    feitos = M.varrer(str(tmp_path), "Z:/saida", registro, None,
                      M.VOPRIX, ".cdr")

    assert feitos == 0 and registro == {}


# ----------------------------------------------------------------------
# Arte de uma cor so: chapa em escala de cinza
# ----------------------------------------------------------------------

def test_nome_diz_gray_quando_a_arte_e_de_uma_cor():
    assert (P.nome_da_chapa(P.VOPRIX, CDR, "", 510, 400, {"GRAY"}, 0, 1)
            == "510x400_GRAY_VOPRIX_COLEGIO_UNUS_envelope_saco")


def test_gray_no_lugar_das_quatro_tintas(monkeypatch, tmp_path):
    """Arte neutra: uma chapa em cinza, e o nome fala GRAY, nao CMYK."""
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf, sem_icc=False: [
        {"C": 0.0608, "M": 0.0608, "Y": 0.0608, "K": 0.0544}])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina, sem_icc=False: True)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, cinza=cinza, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("qualquer.pdf", CDR, str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m: None, True)

    assert feito["cinza"] is True
    assert feito["dpi"] == 1000
    assert feito["base"] == "510x400_GRAY_VOPRIX_COLEGIO_UNUS_envelope_saco"


def test_arte_colorida_continua_em_quadricromia(monkeypatch, tmp_path):
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf, sem_icc=False: [
        {"C": 0.31, "M": 0.08, "Y": 0.05, "K": 0.02}])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina, sem_icc=False: False)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def entregar(origem, saida, base, plano, total):
        feito.update(base=base, cinza=plano["cinza"])
        return os.path.join(saida, base + ".pdf"), ["C", "M"]

    monkeypatch.setattr(P, "_entregar_chapa", entregar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("qualquer.pdf", CDR, str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m: None)

    assert feito["cinza"] is False
    assert feito["base"] == "510x400_CMYK_VOPRIX_COLEGIO_UNUS_envelope_saco"


def _solida(monkeypatch, tmp_path, cob, feito):
    """Roda uma pagina da SOLIDA com esta cobertura e anota o que saiu."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: [cob])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda *a, **k: True)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, cinza=cinza, usadas=set(usadas))
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    return P._processar_pdf("x.pdf", "49700 - Cliente - flyer.pdf",
                            str(tmp_path), P.SOLIDA,
                            {"status": "ok", "saidas": [], "motivo": "",
                             "impresso": None}, lambda m: None)


def test_a_solida_DE_UMA_COR_sai_em_UMA_chapa(monkeypatch, tmp_path):
    """
    "se estiver tudo somente no canal do preto, mandar a chapa pro ctp
    somente preto, mantendo exatamente as porcentagens, e colocar na OS
    do gerempre somente 1 chapa" - o operador, 14/09/2026.

    O caso foi o '49835 - Flor Bela - sacola.pdf': arte inteira no K, e
    saiu como CKMY - quatro chapas no CTP e quatro na OS 19688.

    A SOLIDA estava fora da lista do cinza por um engano de leitura:
    "ela nao para por cor" e sobre a TRAVA, nao sobre o caminho ate o
    CTP.
    """
    feito = {}
    _solida(monkeypatch, tmp_path,
            {"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.38674}, feito)

    assert feito["cinza"] is True
    assert feito["usadas"] == {"GRAY"}, "uma chapa, nao quatro"
    assert feito["base"] == "49700", "o nome da SOLIDA e a OS, e nao muda"


def test_o_preto_COMPOSTO_da_solida_tambem(monkeypatch, tmp_path):
    """
    A SOLIDA nao esta em ENTREGAR_PDF_DIRETO, entao a cobertura dela e
    lida COM o perfil ICC - e o perfil espalha o preto de K sozinho nos
    quatro canais. O mesmo 49835 le C=M=Y=K=0,3867 assim, e C=M=Y=0 com
    K=0,3867 sem o perfil.

    As duas leituras tem de chegar na mesma chapa, senao a correcao
    dependeria de qual caminho a cobertura tomou.
    """
    feito = {}
    _solida(monkeypatch, tmp_path,
            {"C": 0.38674, "M": 0.38674, "Y": 0.38674, "K": 0.38651}, feito)
    assert feito["cinza"] is True
    assert feito["usadas"] == {"GRAY"}


def test_a_solida_COLORIDA_continua_em_quadricromia(monkeypatch, tmp_path):
    """O caminho novo e so para arte de uma cor - o resto nao muda."""
    feito = {}
    _solida(monkeypatch, tmp_path,
            {"C": 0.41, "M": 0.12, "Y": 0.33, "K": 0.08}, feito)
    assert feito["cinza"] is False
    assert feito["usadas"] == set("CMYK")
    assert feito["base"] == "49700"


def test_cobertura_igual_nos_tres_canais_e_preto_composto():
    """Os numeros reais do Blocos_Rio_Quente, que motivaram a regra."""
    assert P.pagina_de_uma_cor({"C": 0.06081, "M": 0.06079,
                                "Y": 0.06080, "K": 0.05444})


def test_preto_puro_tambem_e_uma_cor():
    assert P.pagina_de_uma_cor({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.4212})


def test_arte_colorida_nao_passa_por_cinza():
    assert not P.pagina_de_uma_cor({"C": 0.31, "M": 0.08,
                                    "Y": 0.00, "K": 0.02})
    assert not P.pagina_de_uma_cor({"C": 0.20, "M": 0.20,
                                    "Y": 0.26, "K": 0.05})


def test_pagina_vazia_nao_vira_cinza():
    assert not P.pagina_de_uma_cor({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.0})


# ----------------------------------------------------------------------
# Fora da quadricromia, quem manda fechar e gente
# ----------------------------------------------------------------------

def _monta_pagina(monkeypatch, cobertura, cinza=False):
    """Prepara uma pagina 510x400 com a cobertura pedida."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf, sem_icc=False: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina, sem_icc=False: cinza)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)


def _roda(tmp_path, aprovado=False, nome=CDR, cliente=None):
    return P._processar_pdf("x.pdf", nome, str(tmp_path),
                            cliente or P.VOPRIX,
                            {"status": "ok", "saidas": [], "motivo": "",
                             "impresso": None}, lambda m: None, aprovado)


def test_uma_cor_fecha_sozinha_em_gray(monkeypatch, tmp_path):
    """
    Trava retirada em 10/09/2026, a pedido do operador: 'gera o PDF
    normal, e ao inves de CMYK coloca GRAY, da andamento normal'. So a
    arte de UMA cor (o preto composto que 'cinza' reconhece) passou a
    fechar sozinha - duas ou tres cores continuam esperando gente, e essa
    decisao nao mudou (ver test_duas_cores_tambem_espera).
    """
    _monta_pagina(monkeypatch, {"C": .0608, "M": .0608, "Y": .0608, "K": .0544},
                  cinza=True)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("uma cor nao e mais pendencia"))

    r = _roda(tmp_path)

    assert r["status"] == "ok"
    assert feito["cinza"] is True
    assert feito["base"] == "510x400_GRAY_VOPRIX_COLEGIO_UNUS_envelope_saco"


def test_duas_cores_tambem_espera(monkeypatch, tmp_path):
    _monta_pagina(monkeypatch, {"C": .21, "M": .00, "Y": .00, "K": .08})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    assert _roda(tmp_path)["status"] == "erro"


def test_quadricromia_fecha_sozinha(monkeypatch, tmp_path):
    """O caminho de sempre continua sem pedir licenca a ninguem."""
    _monta_pagina(monkeypatch, {"C": .31, "M": .22, "Y": .18, "K": .09})
    feito = {}

    def entregar(origem, saida, base, plano, total):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_entregar_chapa", entregar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("quadricromia nao e pendencia"))

    r = _roda(tmp_path)
    assert r["status"] == "ok"
    assert feito["base"] == "510x400_CMYK_VOPRIX_COLEGIO_UNUS_envelope_saco"


def test_aprovado_fecha_fora_da_quadricromia(monkeypatch, tmp_path):
    """Depois do 'pode fechar', a mesma pagina passa."""
    _monta_pagina(monkeypatch, {"C": .0608, "M": .0608, "Y": .0608, "K": .0544},
                  cinza=True)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = _roda(tmp_path, aprovado=True)
    assert r["status"] == "ok"
    assert feito["cinza"] is True
    assert feito["base"] == "510x400_GRAY_VOPRIX_COLEGIO_UNUS_envelope_saco"


def test_solida_de_uma_cor_continua_fechando(monkeypatch, tmp_path):
    """A trava e da VOPRIX: a SOLIDA nao para por causa de cor."""
    _monta_pagina(monkeypatch, {"C": .00, "M": .00, "Y": .00, "K": .42})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None, deslocamento=None, girar=0, preto_puro=False, do_corel=False):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("SOLIDA nao pode parar"))

    r = _roda(tmp_path, nome="49700 - Cliente - timbrado.pdf",
              cliente=P.SOLIDA)
    assert r["status"] == "ok" and feito["base"] == "49700"


# ----------------------------------------------------------------------
# O que o programa exige do CorelDRAW ao publicar
# ----------------------------------------------------------------------

def test_ajustes_do_pdf_sao_exigidos_e_nao_herdados(monkeypatch):
    """
    A janela do Corel estava com compressao NENHUMA, e um .cdr de 13 MB
    virava PDF de 1007 MB. O programa nao pode depender do que esta
    marcado na maquina.
    """
    import finart_ctp.corel as CO

    class Ajustes(object):
        pass

    class Documento(object):
        PDFSettings = Ajustes()

    doc = Documento()
    assert CO.ajustar_pdf(doc) == []            # nada faltou
    assert doc.PDFSettings.BitmapCompression == 3     # pdfZIP, sem perda
    assert doc.PDFSettings.CompressText is True


def test_nao_reamostra_a_imagem_do_cliente():
    """
    Reamostrar borra QR code e nao paga: com ZIP o arquivo ja cai 25x, e
    em 800 dpi ele ate engorda.
    """
    from finart_ctp.config import PDF_CORELDRAW

    for ajuste in ("DownsampleColor", "DownsampleGray", "DownsampleMono"):
        assert not PDF_CORELDRAW.get(ajuste), (
            "%s ligado: isso mexe na imagem do cliente" % ajuste)


def test_corel_de_outra_versao_nao_impede_a_conversao(monkeypatch):
    """Propriedade que nao existe e avisada, nao derruba o servico."""
    import finart_ctp.corel as CO

    class Recusa(object):
        def __setattr__(self, nome, valor):
            raise AttributeError(nome)

    class Documento(object):
        PDFSettings = Recusa()

    faltaram = CO.ajustar_pdf(Documento())
    assert sorted(faltaram) == sorted(CO.PDF_CORELDRAW)


# ----------------------------------------------------------------------
# Cliente no nome, e o MODELO quando ainda assim dois baterem
# ----------------------------------------------------------------------

def test_cliente_vem_na_frente_em_maiuscula():
    """Dois 'Panfleto' no mesmo dia so se distinguem pelo cliente."""
    from finart_ctp.nomes import nome_saida_voprix

    a = nome_saida_voprix("Panfleto_15,0x21,0_4_0_M3RIN.cdr",
                          "510x400", set("CMYK"))
    b = nome_saida_voprix("Panfleto_15,0x21,0_4_0_Natura_Aniversario.cdr",
                          "510x400", set("CMYK"))
    assert a == "510x400_CMYK_VOPRIX_M3RIN_panfleto"
    assert b == "510x400_CMYK_VOPRIX_NATURA_ANIVERSARIO_panfleto"
    assert a != b


def test_cliente_sao_os_dois_ultimos_nomes():
    from finart_ctp.nomes import partes_voprix

    # dois nomes
    assert partes_voprix("Panfleto_15,0x21,0_4_0_Natura_Aniversario.cdr") \
        == ("NATURA_ANIVERSARIO", "panfleto")
    # um nome so
    assert partes_voprix("Panfleto_15,0x21,0_4_0_M3RIN.cdr") \
        == ("M3RIN", "panfleto")
    # numero de cor e data no fim nao sao nome
    assert partes_voprix("Papel_Manteiga_15x15_1_0_Kor_31_08.cdr") \
        == ("KOR", "papel_manteiga")
    # palavra de ligacao tambem nao
    assert partes_voprix("Cartaz_29,7x42_4_0_Campeao_Lubrificantes_e_Filtro.cdr") \
        == ("LUBRIFICANTES_FILTRO", "cartaz")


def test_sem_medida_o_cliente_ainda_sai_do_fim():
    from finart_ctp.nomes import partes_voprix

    assert partes_voprix("Mascara_Pasta_Bolsa_Hauany_Martins.cdr") \
        == ("HAUANY_MARTINS", "mascara_pasta_bolsa")


def test_modelo_renomeia_a_primeira_chapa(tmp_path, monkeypatch):
    """
    Combinado: as duas viram MODELO. A que ja estava gravada e renomeada
    para MODELO 1, para as duas ficarem simetricas.
    """
    monkeypatch.setattr(P, "renomear_saida_no_registro", lambda de, para: True)
    base = "510x400_CMYK_VOPRIX_COLEGIO_UNUS_pasta"
    (tmp_path / (base + ".pdf")).write_bytes(b"primeira chapa")

    novo, renomeada = P.resolver_modelo(str(tmp_path), base)

    assert novo == base + " MODELO 2"
    assert renomeada == (base + ".pdf", base + " MODELO 1.pdf")
    assert (tmp_path / (base + " MODELO 1.pdf")).read_bytes() == b"primeira chapa"
    assert not (tmp_path / (base + ".pdf")).exists()


def test_terceira_arte_continua_a_serie(tmp_path):
    base = "510x400_CMYK_VOPRIX_COLEGIO_UNUS_pasta"
    (tmp_path / (base + " MODELO 1.pdf")).write_bytes(b"a")
    (tmp_path / (base + " MODELO 2.pdf")).write_bytes(b"b")

    novo, renomeada = P.resolver_modelo(str(tmp_path), base)
    assert novo == base + " MODELO 3"
    assert renomeada is None            # nao mexe em quem ja esta numerado


def test_nome_livre_nao_vira_modelo_a_toa(tmp_path):
    novo, renomeada = P.resolver_modelo(str(tmp_path), "qualquer_nome")
    assert novo == "qualquer_nome" and renomeada is None


def test_registro_acompanha_a_chapa_renomeada(tmp_path, monkeypatch):
    """Registro que aponta para chapa inexistente nao serve para nada."""
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    U.salvar_registro({"k": {"saidas": ["chapa.pdf", "outra.pdf"]}})

    assert U.renomear_saida_no_registro("chapa.pdf", "chapa MODELO 1.pdf")
    assert U.carregar_registro()["k"]["saidas"] == ["chapa MODELO 1.pdf",
                                                    "outra.pdf"]


def test_nome_da_voprix_tambem_perde_o_acento():
    """A regra do acento vale para todo cliente, nao so para o Emporio."""
    from finart_ctp.nomes import nome_saida_voprix

    assert (nome_saida_voprix("Cartao_23x31_4_0_Otica_Sao_Joao.cdr",
                              "510x400", set("CMYK"))
            == "510x400_CMYK_VOPRIX_SAO_JOAO_cartao")
    assert (nome_saida_voprix("Adesivo_15x21_1_0_Farmácia_Céu.cdr",
                              "510x400", {"K"})
            == "510x400_K_VOPRIX_FARMACIA_CEU_adesivo")


# ----------------------------------------------------------------------
# PRETO PURO x PRETO COMPOSTO - 14/09/2026
# ----------------------------------------------------------------------
# Os dois valem UMA chapa, e ate aqui eram tratados igual. Mas eles pedem
# caminhos OPOSTOS no Ghostscript, e medir mostrou o tamanho do engano
# (PDF de teste com retangulos de tom conhecido, a 72 dpi):
#
#                     COM perfil   SEM perfil
#     K puro   25%        21,6%        25,1%
#     K puro  100%        87,5%       100,0%
#     composto 25%        42,4%        50,2%
#     composto 50%        70,2%       100,0%
#
# Preto puro SEM o perfil sai exato; COM o perfil, o chapado de 100% vira
# 87,5%. Preto composto e o contrario: sem o perfil as quatro tintas
# somam e um meio-tom satura em preto.

def test_preto_so_no_K_separa_os_dois_pretos():
    assert P.preto_so_no_K({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.38674})
    assert not P.preto_so_no_K(
        {"C": 0.38674, "M": 0.38674, "Y": 0.38674, "K": 0.38651})
    # pagina em branco nao e preto puro: nao ha tinta nenhuma
    assert not P.preto_so_no_K({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.0})


def test_separar_cinza_so_tira_o_perfil_quando_mandam(monkeypatch, tmp_path):
    """
    A bandeira tem de chegar ate a linha de comando do Ghostscript - e
    entre 87,5% e 100% de tinta ha um '-dUseFastColor=true'.
    """
    import finart_ctp.ghostscript as G

    chamadas = []

    class Fim(object):
        returncode = 0
        stderr = ""

    def falso(cmd, **k):
        chamadas.append(cmd)
        open(os.path.join(str(tmp_path), "cinza.tif"), "wb").write(b"tif")
        return Fim()

    monkeypatch.setattr(G.subprocess, "run", falso)

    G.separar_cinza("x.pdf", 800, str(tmp_path), 1, sem_perfil=True)
    assert "-dUseFastColor=true" in chamadas[-1]

    G.separar_cinza("x.pdf", 800, str(tmp_path), 1, sem_perfil=False)
    assert "-dUseFastColor=true" not in chamadas[-1]

    # e o padrao e COM perfil: quem nao souber do assunto nao muda o
    # comportamento dos quatro clientes que ja usavam o cinza
    G.separar_cinza("x.pdf", 800, str(tmp_path), 1)
    assert "-dUseFastColor=true" not in chamadas[-1]


def test_o_preto_puro_e_decidido_na_cobertura_CRUA(monkeypatch, tmp_path):
    """
    A armadilha inteira num teste.

    A SOLIDA nao esta em ENTREGAR_PDF_DIRETO, entao a cobertura dela e
    lida COM o perfil - e o perfil espalha o K sozinho pelos quatro
    canais. Decidindo por ela, o '49835 - Flor Bela - sacola' seria dado
    como preto COMPOSTO e a chapa sairia com 87,5% no lugar de 100%.

    Os numeros abaixo sao os do arquivo de verdade.
    """
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])

    def cobertura(pdf, sem_icc=False):
        if sem_icc:                       # a verdade do arquivo
            return [{"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.38674}]
        return [{"C": 0.38674, "M": 0.38674,   # o que o perfil mostra
                 "Y": 0.38674, "K": 0.38651}]

    monkeypatch.setattr(P, "cobertura_por_pagina", cobertura)
    monkeypatch.setattr(P, "sem_cor_gritante", lambda *a, **k: True)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None, deslocamento=None, girar=0,
              preto_puro=False, do_corel=False):
        feito.update(cinza=cinza, preto_puro=preto_puro)
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("x.pdf", "49835 - Flor Bela - sacola.pdf", str(tmp_path),
                     P.SOLIDA, {"status": "ok", "saidas": [], "motivo": "",
                                "impresso": None}, lambda m: None)

    assert feito["cinza"] is True
    assert feito["preto_puro"] is True, \
        "decidiu pela cobertura profilada - a chapa sairia com 87,5%"


# Um nome de arquivo que cada cliente aceita. SOLIDA e EMPORIO exigem a
# OS no nome; os outros nao.
UM_ARQUIVO_DE_CADA_CLIENTE = {
    "SOLIDA": "49835 - Flor Bela - sacola.pdf",
    "VOPRIX": "Bloco_21x29,7_1_1_Engquer_Linha_Viva.cdr",
    "FIALHO": "FORRO AGENDA unicidades  2027.pdf",
    "EMPORIO": "02050 - Logexpress Logistica.pdf",
    "VIVA": "GRADE 1710.pdf",
    "CREATIVE": "santinho cruvinel.pdf",
    "PRIME": "VALDINO - CHAPADO.cdr",
}


@pytest.mark.parametrize("cliente", sorted(UM_ARQUIVO_DE_CADA_CLIENTE))
def test_preto_PURO_sai_em_uma_chapa_em_TODO_cliente(cliente, monkeypatch,
                                                     tmp_path):
    """
    "todos os arquivos que vierem somente no canal do preto faca assim,
    de todos os clientes" - o operador, 14/09/2026.

    Arte inteira no K e um fato do ARQUIVO, nao do cliente. Este teste
    percorre TODOS os clientes que a FIA atende para que ninguem volte a
    ser excluido por engano - foi assim que a FIALHO ficou de fora, e
    seria assim que o proximo ficaria.
    """
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False:
                            [{"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.38674}])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda *a, **k: True)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    # a Creative mede a pinca pela marca de corte; aqui ela nao importa
    monkeypatch.setattr(P, "marcas_de_corte",
                        lambda pdf, pag: {"baixo": 5.0, "cima": 5.0,
                                          "esquerda": 5.0, "direita": 5.0})

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None, deslocamento=None, girar=0,
              preto_puro=False, do_corel=False):
        feito.update(cinza=cinza, preto_puro=preto_puro,
                     usadas=set(usadas), base=base)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    def entregar(pdf, saida, base, plano, total):
        # o caminho CURTO: o PDF vai inteiro para a gravadora, sem
        # rasterizar. So chega aqui quem tem UMA tinta escrita dentro do
        # arquivo - entao a gravadora acha o K e grava a mesma chapa.
        feito.update(entregue=True, cinza=plano["cinza"],
                     preto_puro=plano.get("preto_puro"),
                     usadas=set(plano["usadas"]), base=base)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "_entregar_chapa", entregar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    r = P._processar_pdf("x.pdf", UM_ARQUIVO_DE_CADA_CLIENTE[cliente],
                         str(tmp_path), cliente,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert feito.get("cinza") is True, (
        "%s ficou de fora da regra do preto puro" % cliente)
    assert feito["usadas"] == {"GRAY"}
    # UMA chapa na OS, nao quatro - e isso vale para os dois caminhos
    assert r["chapas"] == [{"chapa": [510, 400], "tintas": 1}], cliente

    if feito.get("entregue"):
        # quem entrega o PDF inteiro nao rasteriza nada, entao nao ha
        # perfil no caminho e a porcentagem chega intacta por construcao
        assert cliente in P.ENTREGAR_PDF_DIRETO
    else:
        assert feito.get("preto_puro") is True, (
            "%s sairia pelo perfil, com o chapado em 87,45 por cento"
            % cliente)


# ----------------------------------------------------------------------
# O ANTES E O DEPOIS DA TINTA - 14/09/2026
# ----------------------------------------------------------------------
# "todos os arquivos que vc for converter, 1 cor, conferir o antes e o
# depois para ver se as porcentagens estao as mesmas" - o operador.
#
# A regra nasceu de um defeito que passou despercebido por nao dar erro:
# a chapa de uma cor saia pelo perfil ICC e o chapado de 100% virava
# 87,5%. Isso nao aparece na tela - so na tiragem, com a chapa queimada.

def test_a_tinta_igual_passa(monkeypatch, tmp_path):
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (38.66, 100.0, 13500.0) if pdf != str(chapa)
                            else (38.68, 100.0, 13520.0))

    antes, depois = P.conferir_uma_cor("origem.pdf", 1, str(chapa), True)
    assert antes[:2] == (38.66, 100.0) and depois[:2] == (38.68, 100.0)
    assert chapa.exists(), "nao era para apagar"


def test_a_tinta_DIFERENTE_apaga_a_chapa(monkeypatch, tmp_path):
    """
    Os numeros sao os do defeito de verdade: media 38,66 -> 33,83 e
    maximo 100,00 -> 87,45. Chapa errada na pasta da prejuizo; chapa que
    nao existe da trabalho.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (38.66, 100.0, 13500.0) if pdf != str(chapa)
                            else (33.83, 87.45, 0.0))

    with pytest.raises(RuntimeError) as erro:
        P.conferir_uma_cor("origem.pdf", 1, str(chapa), True)

    assert "PERDEU densidade" in str(erro.value)
    assert "87.45" in str(erro.value), "o aviso tem de trazer os numeros"
    assert not chapa.exists(), "a chapa errada nao pode ficar na pasta"


def test_so_a_MAXIMA_fora_ja_reprova(monkeypatch, tmp_path):
    """
    A media esconde: um chapado que perde 12 pontos mexe pouco na media
    se for pouca area. O maximo e quem denuncia.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (5.00, 100.0, 200.0) if pdf != str(chapa)
                            else (4.90, 87.45, 200.0))

    with pytest.raises(RuntimeError):
        P.conferir_uma_cor("origem.pdf", 1, str(chapa), True)


def test_o_preto_COMPOSTO_e_registrado_mas_nao_barrado(monkeypatch, tmp_path):
    """
    No composto nao ha identidade para conferir: quatro canais viram um,
    e o numero muda de propósito - um composto de 50% sai 70,2%. Barrar
    ali pararia servico que sempre andou. Os dois valores vao para o log.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (50.0, 50.0, 9000.0) if pdf != str(chapa)
                            else (70.2, 70.2, 9100.0))

    antes, depois = P.conferir_uma_cor("origem.pdf", 1, str(chapa), False)
    assert antes[:2] == (50.0, 50.0) and depois[:2] == (70.2, 70.2)
    assert chapa.exists()


def test_a_folga_separa_os_dois_casos_com_sobra():
    """
    1,0 ponto e um primeiro numero. Ele precisa caber o ruido de serrilha
    (0,02 medido) e barrar o defeito (5 e 12 pontos) - dez vezes de
    sobra para cada lado.
    """
    assert P.TOLERANCIA_TINTA_PP == 1.0
    assert 0.02 < P.TOLERANCIA_TINTA_PP < 5.0


# ----------------------------------------------------------------------
# TRACO DE CMY NAO E PRETO COMPOSTO - 14/09/2026
# ----------------------------------------------------------------------
# O 'Bloco_21x29,7_1_1_Engquer' da VOPRIX quase foi gravado claro pela
# metade. Ele tem C=M=Y=0,232% e K=8,893%: o CMY vale 2,61% do preto, e
# e serrilha, nao cor. Pelo limiar ABSOLUTO de antes ele virou 'preto
# composto', foi convertido COM o perfil, e a chapa saiu com 3,94% de
# tinta onde o arquivo tinha 9,61%.
#
# Medido no PDF que o Corel publica: a perda NAO era do Corel - ele
# entrega media 9,61% e maximo 100%. A perda era nossa.

def test_traco_de_cmy_continua_sendo_preto_puro():
    """2,61% do K e serrilha. 100% do K e preto composto de verdade."""
    bloco = {"C": 0.00232, "M": 0.00232, "Y": 0.00232, "K": 0.08893}
    assert P.preto_so_no_K(bloco), "o traco derrubou a classificacao"

    # os compostos de verdade continuam sendo compostos
    assert not P.preto_so_no_K(
        {"C": 0.38674, "M": 0.38674, "Y": 0.38674, "K": 0.38651})
    assert not P.preto_so_no_K(
        {"C": 0.06081, "M": 0.06079, "Y": 0.06080, "K": 0.05444})


def test_a_folga_do_traco_separa_os_casos_com_ordem_de_grandeza():
    """
    2,61% de um lado, 100% do outro. O numero escolhido precisa caber o
    traco medido com sobra e ficar bem longe do composto mais magro.
    """
    assert P.CMY_QUE_AINDA_E_TRACO == 0.10
    assert 0.0261 < P.CMY_QUE_AINDA_E_TRACO < 1.0

    # na fronteira: 10% do K ainda e traco, 11% ja nao e
    assert P.preto_so_no_K({"C": 0.010, "M": 0.0, "Y": 0.0, "K": 0.100})
    assert not P.preto_so_no_K({"C": 0.011, "M": 0.0, "Y": 0.0, "K": 0.100})


def test_sem_preto_nenhum_nao_e_preto_puro():
    assert not P.preto_so_no_K({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.0})
    assert not P.preto_so_no_K({"C": 0.4, "M": 0.0, "Y": 0.0, "K": 0.0})


def test_no_composto_a_tinta_pode_SUBIR(monkeypatch, tmp_path):
    """
    Juntar quatro canais num so aumenta a tinta de propósito - um
    composto de 50% sai 70,2%. Isso nao pode ser barrado.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (50.0, 50.0, 9000.0) if pdf != str(chapa)
                            else (70.2, 70.2, 9100.0))

    antes, depois = P.conferir_uma_cor("origem.pdf", 1, str(chapa), False)
    assert depois[0] > antes[0]
    assert chapa.exists()


def test_a_MEDIA_MENOR_sozinha_NAO_reprova(monkeypatch, tmp_path):
    """
    A media cai sem que nada tenha se perdido, e o motivo e geometrico:
    a ARTE e vetor, e rasterizada em resolucao baixa todo traco fino
    vira um pixel inteiro, inflando a media. O mesmo arquivo dava 9,61%
    a 60 dpi e 5,10% a 1000 dpi. A CHAPA ja e bitmap de 1000 dpi e le
    igual em qualquer resolucao.

    Entao a media informa e nao barra. Quem responde sao o maximo e a
    area do chapado - aqui os dois dizem que o chapado atravessou.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (9.61, 100.0, 13500.0) if pdf != str(chapa)
                            else (3.94, 100.0, 13480.0))

    antes, depois = P.conferir_uma_cor("origem.pdf", 1, str(chapa), False)
    assert antes[1] == depois[1] == 100.0
    assert chapa.exists(), "reprovou chapa boa por causa da media"


def test_o_MAXIMO_das_MARCAS_nao_salva_a_chapa(monkeypatch, tmp_path):
    """
    O furo que deixou a chapa do 'Bloco' da VOPRIX sair clara, e que eu
    so entendi depois que o operador disse 'ficou da mesma forma, esta
    com 87% onde antigamente estava com 100%'.

    A Corel desenha as marcas de registro na cor REGISTRO - 100% das
    quatro tintas - e elas atravessam o perfil ICC sem perder nada.
    Entao a chapa tinha maximo 100% com a arte inteira rebaixada, e a
    conferencia que olhava so o maximo passou. Medido no arquivo de
    verdade, a 150 dpi:

        arquivo   100%  em 13.500 mm2   (a arte)
        chapa     100%  em    210 mm2   (so as marcas)
                  87,45% em 8.859 mm2   (a arte, rebaixada)

    Um pixel de chapado nao prova nada; a area prova.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (9.61, 100.0, 13500.0) if pdf != str(chapa)
                            else (3.94, 100.0, 210.0))

    with pytest.raises(RuntimeError) as erro:
        P.conferir_uma_cor("origem.pdf", 1, str(chapa), True)

    assert "ENCOLHEU" in str(erro.value)
    assert not chapa.exists(), "a chapa clara nao pode ficar na pasta"


def test_chapado_PEQUENO_nao_e_conferido_por_area(monkeypatch, tmp_path):
    """
    Abaixo de 1 cm2 o 'chapado' pode ser respingo ou um ponto de
    registro, e comparar area vira ruido. Ali so o maximo conta.
    """
    chapa = tmp_path / "chapa.pdf"
    chapa.write_bytes(b"pdf")
    monkeypatch.setattr(P, "_tinta_da_pagina",
                        lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                            (2.0, 100.0, 40.0) if pdf != str(chapa)
                            else (2.0, 100.0, 5.0))

    P.conferir_uma_cor("origem.pdf", 1, str(chapa), True)
    assert chapa.exists(), "barrou por 35 mm2 de respingo"


def test_a_folga_da_area_aguenta_a_INFLACAO_da_arte_e_barra_o_defeito():
    """
    Os dois lados do corte, medidos no 'Bloco' da VOPRIX a 300 dpi,
    contra os 10.839 mm2 de chapado que a arte tem ali:

        chapa certa    9.012 mm2 = 0,83 do arquivo
        chapa errada     206 mm2 = 0,02 do arquivo

    O corte precisa caber a INFLACAO da arte - que e vetor e conta traco
    fino como chapado inteiro - e ainda assim barrar o defeito.
    """
    assert P.CHAPADO_QUE_TEM_DE_SOBRAR == 0.25
    assert 206.0 / 10839.0 < P.CHAPADO_QUE_TEM_DE_SOBRAR < 9012.0 / 10839.0
    assert P.CHAPADO_QUE_VALE_CONFERIR_MM2 == 100.0


def test_a_conferencia_nao_le_em_resolucao_baixa_demais():
    """
    A 60 dpi a arte deste mesmo arquivo dava 19.031 mm2 de chapado
    contra 8.640 mm2 da chapa CERTA - razao 0,45, que reprovaria chapa
    boa com qualquer corte de metade. A inflacao e da rasterizacao do
    vetor, nao do arquivo. Ver DPI_DA_CONFERENCIA.
    """
    assert P.DPI_DA_CONFERENCIA >= 300
    razao_a_60_dpi = 8640.0 / 19031.0      # chapa CERTA contra a arte
    razao_a_300_dpi = 9012.0 / 10839.0     # a mesma chapa CERTA
    assert razao_a_60_dpi < 0.5 < razao_a_300_dpi,         "a 60 dpi a chapa boa fica abaixo de meio - a inflacao come a folga"


def test_o_CHAPADO_que_cai_reprova_em_qualquer_um_dos_dois(monkeypatch,
                                                           tmp_path):
    """
    O defeito de verdade, o do 49835: o chapado de 100% saindo com
    87,5%. Reprova tanto no preto puro quanto no composto - cair nao tem
    explicacao em nenhum dos dois.
    """
    for puro in (True, False):
        chapa = tmp_path / ("chapa_%s.pdf" % puro)
        chapa.write_bytes(b"pdf")
        monkeypatch.setattr(P, "_tinta_da_pagina",
                            lambda pdf, pag, sem_perfil, dpi=60, piso=None:
                                (38.66, 100.0, 13500.0) if "chapa_" not in pdf
                                else (33.83, 87.45, 0.0))
        with pytest.raises(RuntimeError) as erro:
            P.conferir_uma_cor("origem.pdf", 1, str(chapa), puro)
        assert "PERDEU densidade" in str(erro.value), puro
        assert not chapa.exists(), puro


# ----------------------------------------------------------------------
# O NOME DIZ QUANTAS CORES - 17/09/2026
#
# "os materiais da voprix, por ultimo agora, nao entendi o erro, eles sao
# em 4 cores, refaca eles da forma correta" - o operador.
#
# Dois arquivos com 4_0 e 4_4 no nome sairam CMY porque o preto era
# pouco, e viraram pendencia na trava da quadricromia:
#
#     Luva_Produto ... C 0,3001  M 0,0338  Y 0,3048  K 0,0273
#     Stopper_CE ..... C 0,6011  M 0,5954  Y 0,6148  K 0,0421
#
# O K desses dois nao aparece sozinho em pixel nenhum - e preto POR CIMA
# de fundo colorido, que e o normal em quadricromia. A pergunta "aparece
# sozinha?" separa bem traco de desenho quando ha area limpa; num
# trabalho chapado ela responde 'nunca' para uma tinta que e chapa.
# ----------------------------------------------------------------------

def test_o_nome_diz_quantas_cores():
    from finart_ctp.nomes import cores_pedidas_voprix as ler
    assert ler("Luva_Produto_24,0x9,0_4_0_Apoquel.cdr") == (4, 0)
    assert ler("Stopper_CE_15,0x21,0_4_4_Apoquel.cdr") == (4, 4)
    assert ler("Bloco_21x29,7_1_1_Engquer_Engenharia.cdr") == (1, 1)
    assert ler("Sacola_Premium_15x14x8_1_0_Pantone_Bold_me.cdr") == (1, 0)


def test_data_no_nome_NAO_vira_especificacao_de_cor():
    """
    'Bloco_Anotacoes_10x15_Mobil_Lubexx_14_09' e de UMA cor, e o 14_09 e
    a data. Lido como 1/4 ou 4/9, a conta sairia errada.

    Sao dois algarismos em cada metade - e so passa digito sozinho.
    """
    from finart_ctp.nomes import cores_pedidas_voprix as ler
    assert ler("Bloco_Anotacoes_10x15_Mobil_Lubexx_14_09.cdr") is None
    assert ler("Ficha_Cadastro_21x30_Dra_Lucena_Rosa_10_09.cdr") is None
    assert ler("Folder_29,7x15_4_4_Chapadeira_09_09.cdr") == (4, 4)


def test_medida_suja_ainda_e_lida():
    """
    A medida nem sempre sai limpa - a unidade vem colada, ou o material
    entra com virgula. Tres dos 45 arquivos da VOPRIX caem assim, e os
    tres dizem 4_0.
    """
    from finart_ctp.nomes import cores_pedidas_voprix as ler
    assert ler("Bloco_anotacoes_10,5x14,8cm_4_0_Ufebrac.cdr") == (4, 0)
    assert ler("Luva_de_Produto_29,7x_6,0_4_0_Simparic_Trio.cdr") == (4, 0)
    assert ler("Pasta_Bopp,43,0x31,0_4_0_Curso_de_Relacoes.cdr") == (4, 0)


def test_quem_nao_diz_continua_nao_dizendo():
    """Nao inventar e metade do trabalho: sem especificacao, None."""
    from finart_ctp.nomes import cores_pedidas_voprix as ler
    assert ler("Lamina_Tecnica_21x29,7_Cytopoint.cdr") is None
    assert ler("Sacola_Promo_M1_22x32x9_HR_Consultoria_Medica.CDR") is None
    assert ler("Caixa_FA_10,0x8,0x2,8_Oliva_Parfum.cdr") is None


def test_dizendo_QUATRO_o_preto_fraco_NAO_e_descartado(monkeypatch, tmp_path):
    """O caso do Stopper, com os numeros medidos nele."""
    cob = {"C": 0.6011, "M": 0.5954, "Y": 0.6148, "K": 0.0421}
    _monta_pagina(monkeypatch, cob)
    monkeypatch.setattr(P, "tinta_aparece_sozinha",
                        lambda *a, **k: pytest.fail(
                            "nem devia perguntar: o nome ja disse 4 cores"))
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False,
              alvo=None, deslocamento=None, girar=0, preto_puro=False,
              do_corel=False):
        feitos.append(set(usadas))
        destino = os.path.join(saida, base + ".pdf")
        os.makedirs(saida, exist_ok=True)
        open(destino, "wb").write(b"chapa")
        return destino, sorted(usadas)

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "_entregar_chapa",
                        lambda origem, saida, base, plano, total:
                        gerar(origem, saida, base, plano["pagina"],
                              plano["dpi"], 0, 0, plano["usadas"]))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    r = P._processar_pdf("x.pdf", "Stopper_CE_15,0x21,0_4_4_Apoquel.cdr",
                         str(tmp_path), P.VOPRIX,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m, **k: None)

    assert r["status"] == "ok", r["motivo"]
    assert feitos and feitos[0] == set("CMYK"), feitos


def test_SEM_o_nome_dizer_a_regra_do_traco_continua_valendo(monkeypatch,
                                                            tmp_path):
    """
    A trava nova nao pode apagar a regra do traco - ela existe porque um
    ciano de 5,23% que so risca linha nao vale uma chapa.
    """
    cob = {"C": 0.0523, "M": 0.5954, "Y": 0.6148, "K": 0.5000}
    _monta_pagina(monkeypatch, cob)
    monkeypatch.setattr(P, "tinta_aparece_sozinha", lambda *a, **k: (False, 0))
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False,
              alvo=None, deslocamento=None, girar=0, preto_puro=False,
              do_corel=False):
        feitos.append(set(usadas))
        destino = os.path.join(saida, base + ".pdf")
        os.makedirs(saida, exist_ok=True)
        open(destino, "wb").write(b"chapa")
        return destino, sorted(usadas)

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "_entregar_chapa",
                        lambda origem, saida, base, plano, total:
                        gerar(origem, saida, base, plano["pagina"],
                              plano["dpi"], 0, 0, plano["usadas"]))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    # aprovado=True porque largar o ciano deixa MYK, e MYK cai na trava
    # da quadricromia - que e outra regra, e nao a que este teste mede.
    # Foi assim que os dois arquivos de 17/09 viraram pendencia: o
    # descarte primeiro, a trava depois.
    P._processar_pdf("x.pdf", "Lamina_Tecnica_21x29,7_Cytopoint.cdr",
                     str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m, **k: None, True)

    assert feitos and "C" not in feitos[0], feitos


def test_o_nome_dizendo_UMA_cor_nao_impede_o_descarte(monkeypatch, tmp_path):
    """
    So a QUADRICROMIA pedida protege. Um '1_0' no nome nao e razao para
    segurar tinta: ali o cliente esta pedindo MENOS chapa, nao mais.
    """
    from finart_ctp.nomes import cores_pedidas_voprix as ler
    assert ler("Sacola_Premium_15x14x8_1_0_Pantone_Bold_me.cdr") == (1, 0)

    cob = {"C": 0.0523, "M": 0.5954, "Y": 0.6148, "K": 0.5000}
    _monta_pagina(monkeypatch, cob)
    perguntou = []
    monkeypatch.setattr(P, "tinta_aparece_sozinha",
                        lambda *a, **k: (perguntou.append(1), (False, 0))[1])
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: ("x.pdf", ["M", "Y", "K"]))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a, **k: None)

    P._processar_pdf("x.pdf", "Sacola_Premium_15x14x8_1_0_Pantone_Bold_me.cdr",
                     str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m, **k: None)
    assert perguntou, "com 1_0 no nome a pergunta do traco continua sendo feita"


# ----------------------------------------------------------------------
# O PROTOCOLO DO ACHATAMENTO - VOPRIX, 17/09/2026
#
# "estou percebendo que eles nao estao mandando os arquivos como antes,
# convertido as imagens todas em 1 imagem, e somente os textos e objetos
# sem converter, isso e perigoso, pode sumir algum objeto (...) no corel
# mesmo, converta tudo em imagem 900 dpi, CMYK, gera o pdf e confere as
# cores se estao batendo" - o operador.
# ----------------------------------------------------------------------

def test_a_folga_veio_de_medida_e_nao_de_cabeca():
    """
    Os tres .cdr da VOPRIX de 17/09, achatados de verdade:

        Stopper_CE     C +0,0168  M +0,0172  Y +0,0163  K -0,0040
        Luva_Produto   C +0,0111  M -0,0007  Y +0,0107  K -0,0014
        Luva_Simparic  C +0,0033  M +0,0119  Y +0,0033  K +0,0042

    O desvio e quase sempre para CIMA: o antisserrilhamento cria pixel de
    cobertura parcial em cada borda. O maior foi +0,0172, e a folga e o
    dobro disso.
    """
    from finart_ctp.ghostscript import FOLGA_DO_ACHATAMENTO as folga
    assert folga > 0.0172 * 1.5, "sem margem, arquivo denso vira pendencia"
    assert folga < 0.046, "acima disto o defeito do perfil ICC passaria"


@pytest.mark.parametrize("rotulo,antes,depois", [
    ("Stopper", {"C": .6011, "M": .5954, "Y": .6148, "K": .0421},
                {"C": .6179, "M": .6126, "Y": .6311, "K": .0381}),
    ("Luva", {"C": .3001, "M": .0338, "Y": .3048, "K": .0273},
             {"C": .3112, "M": .0331, "Y": .3155, "K": .0259}),
    ("Simparic", {"C": .2000, "M": .3000, "Y": .2000, "K": .1000},
                 {"C": .2033, "M": .3119, "Y": .2033, "K": .1042}),
])
def test_o_ruido_medido_nos_arquivos_de_verdade_PASSA(rotulo, antes, depois):
    from finart_ctp.ghostscript import cor_sobreviveu
    bate, recado = cor_sobreviveu(antes, depois)
    assert bate, "%s devia passar: %s" % (rotulo, recado)


def test_tinta_que_SOME_e_barrada_sem_folga_nenhuma():
    """Cor que existia e zerou e objeto perdido - o medo do operador."""
    from finart_ctp.ghostscript import cor_sobreviveu
    bate, recado = cor_sobreviveu(
        {"C": .60, "M": .59, "Y": .61, "K": .0421},
        {"C": .60, "M": .59, "Y": .61, "K": .0000})
    assert not bate
    assert "TINTA PERDIDA" in recado and "K" in recado


def test_tinta_fraca_que_perde_um_terco_tambem_e_barrada():
    """
    Numero absoluto sozinho e cego para tinta fraca.

    O K do Stopper e 0,0421. Caindo para 0,010 ele perde 76% e nem chega
    perto da folga de 0,035 - seria o defeito do perfil ICC em miniatura,
    passando batido.
    """
    from finart_ctp.ghostscript import cor_sobreviveu
    bate, recado = cor_sobreviveu(
        {"C": .60, "M": .59, "Y": .61, "K": .0421},
        {"C": .60, "M": .59, "Y": .61, "K": .0100})
    assert not bate
    assert "perdeu 76%" in recado


def test_o_defeito_do_perfil_ICC_de_09_09_seria_pego():
    """
    Os numeros reais daquele dia, quando o preto do K saiu remisturado
    nas quatro tintas e ninguem viu ate a chapa.
    """
    from finart_ctp.ghostscript import cor_sobreviveu
    bate, recado = cor_sobreviveu(
        {"C": .0464, "M": .0468, "Y": .0084, "K": .0558},
        {"C": .1019, "M": .1049, "Y": .0683, "K": .0097})
    assert not bate, recado


def test_variacao_minuscula_em_tinta_minuscula_nao_acusa():
    """
    Uma tinta de 0,002 caindo para 0,001 'perdeu 50%' e nao quer dizer
    nada. Sem o piso, todo arquivo viraria pendencia.
    """
    from finart_ctp.ghostscript import cor_sobreviveu
    bate, _ = cor_sobreviveu({"C": .60, "M": .59, "Y": .61, "K": .0020},
                             {"C": .60, "M": .59, "Y": .61, "K": .0010})
    assert bate


def test_o_achatado_da_VOPRIX_e_conferido_contra_o_vetor(monkeypatch,
                                                         tmp_path):
    """
    Duas publicacoes de proposito: o vetor e a REFERENCIA de cor, e sem
    referencia a conferencia nao existe.
    """
    import finart_ctp.processador as PR
    publicados = []

    def vetor(cdr, destino):
        publicados.append(("vetor", destino))
        open(destino, "wb").write(b"%PDF-1.4")
        return destino

    def achatado(cdr, destino, dpi=900):
        publicados.append(("achatado", destino))
        open(destino, "wb").write(b"%PDF-1.4")
        return destino

    monkeypatch.setattr(PR, "publicar_pdf", vetor)
    monkeypatch.setattr(PR, "publicar_pdf_achatado", achatado)
    monkeypatch.setattr(PR, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False:
                        [{"C": .30, "M": .03, "Y": .30, "K": .027}])

    pdf, tmp = PR.converter_cdr(str(tmp_path / "x.cdr"), achatar=True)
    assert [t for t, _ in publicados] == ["vetor", "achatado"]
    assert pdf.endswith("_achatado.pdf"), pdf
    shutil.rmtree(tmp, ignore_errors=True)


def test_cor_que_nao_bate_NAO_vira_chapa(monkeypatch, tmp_path):
    """Perdendo cor no achatamento, o servico para em vez de gravar."""
    import finart_ctp.processador as PR
    monkeypatch.setattr(PR, "publicar_pdf",
                        lambda c, d: (open(d, "wb").write(b"%PDF"), d)[1])
    monkeypatch.setattr(PR, "publicar_pdf_achatado",
                        lambda c, d, dpi=900: (open(d, "wb").write(b"%PDF"), d)[1])
    leituras = iter([[{"C": .30, "M": .03, "Y": .30, "K": .0558}],
                     [{"C": .30, "M": .03, "Y": .30, "K": .0000}]])
    monkeypatch.setattr(PR, "cobertura_por_pagina",
                        lambda pdf, sem_icc=False: next(leituras))

    with pytest.raises(RuntimeError) as erro:
        PR.converter_cdr(str(tmp_path / "x.cdr"), achatar=True)
    assert "cor nao bateu" in str(erro.value)


def test_sem_achatar_publica_UMA_vez_so(monkeypatch, tmp_path):
    """Quem nao esta na lista continua como sempre foi - uma publicacao."""
    import finart_ctp.processador as PR
    quantas = []
    monkeypatch.setattr(PR, "publicar_pdf",
                        lambda c, d: (quantas.append(1),
                                      open(d, "wb").write(b"%PDF"), d)[2])
    monkeypatch.setattr(PR, "publicar_pdf_achatado",
                        lambda *a, **k: pytest.fail("nao devia achatar"))
    pdf, tmp = PR.converter_cdr(str(tmp_path / "x.cdr"))
    assert len(quantas) == 1
    shutil.rmtree(tmp, ignore_errors=True)


def test_so_a_VOPRIX_achata_hoje():
    from finart_ctp.config import CLIENTES_QUE_ACHATAM_NO_COREL as lista
    assert lista == ("VOPRIX",)
