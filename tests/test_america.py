# -*- coding: utf-8 -*-
r"""
O portao da AMERICA - a pasta PARA CTP.

A AMERICA e o cliente que a casa MONTA. O arquivo dela chega por montar,
e so vira chapa depois que uma pessoa revisa e poe na 'PARA CTP'. Dali em
diante o fechamento e automatico, e termina APAGANDO o arquivo do portao.

O teste que mais importa aqui e o de nao repetir: em 10/09/2026 o portao
imprimiu a MESMA prova tres vezes porque a faxina falhava depois da
impressao e o vigia refazia tudo na volta seguinte.
"""

import io
import os

from finart_ctp import america


def _pdf(caminho, marca=b"", paginas=1):
    """
    Um PDF de VERDADE, que o pypdf abre.

    'marca' entra como texto solto no fim do arquivo, so para dar
    tamanhos diferentes a dois PDFs - e de tamanho que a conferencia
    trata. Falso nao serve: 'chegou_inteira' abre o arquivo, e um
    '%PDF-1.4' seguido de lixo nao abre.
    """
    import pypdf
    w = pypdf.PdfWriter()
    for _ in range(paginas):
        w.add_blank_page(width=200, height=200)
    with io.open(caminho, "wb") as f:
        w.write(f)
        if marca:
            f.write(b"\n% " + marca + b"\n")
    return caminho


# ----------------------------------------------------------------------
# A copia guardada - e o defeito que travou o portao
# ----------------------------------------------------------------------

def test_copia_que_ja_existe_igual_nao_e_mexida(tmp_path):
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    _pdf(str(portao / "x.pdf"), b"mesmo")
    _pdf(str(dia / "x.pdf"), b"mesmo")

    guardada, o_que_fiz = america.guardar_copia(str(portao / "x.pdf"), str(dia))
    assert o_que_fiz == "ja_era_a_mesma"
    assert b"mesmo" in io.open(guardada, "rb").read()


def test_copia_que_nao_existe_e_devolvida(tmp_path):
    """O operador MOVEU em vez de copiar: a copia volta para a pasta do dia."""
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    _pdf(str(portao / "x.pdf"), b"unico")

    guardada, o_que_fiz = america.guardar_copia(str(portao / "x.pdf"), str(dia))
    assert o_que_fiz == "copiei"
    assert os.path.exists(guardada)
    assert b"unico" in io.open(guardada, "rb").read()


def test_outra_com_o_mesmo_nome_nao_trava_o_portao(tmp_path):
    """
    ESTE E O DEFEITO DE 10/09/2026, e ele custou tres folhas de papel.

    A pasta do dia tinha uma montagem com o MESMO NOME e conteudo
    diferente (7.026.787 bytes contra 7.015.188). A funcao dizia 'ja
    existia' e seguia; mais adiante a conferencia comparava as duas, via
    tamanhos diferentes, recusava o apagar - e o arquivo ficava no portao
    para sempre, refeito e REIMPRESSO a cada volta do vigia.

    Quem manda e a do portao: e a que o operador revisou. A antiga e
    posta de lado com a data, porque nao se joga fora montagem de
    ninguem.
    """
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    _pdf(str(portao / "x.pdf"), b"a aprovada, do portao")
    _pdf(str(dia / "x.pdf"), b"a velha")

    guardada, o_que_fiz = america.guardar_copia(str(portao / "x.pdf"), str(dia))

    assert o_que_fiz == "troquei"
    # a guardada passou a ser a do portao...
    assert b"a aprovada, do portao" in io.open(guardada, "rb").read()
    # ...e a antiga NAO se perdeu
    postas_de_lado = [f for f in os.listdir(str(dia)) if "anterior" in f]
    assert len(postas_de_lado) == 1
    velha = io.open(str(dia / postas_de_lado[0]), "rb").read()
    assert b"a velha" in velha

    # e agora o tamanho bate, que e o que destrava o apagar
    ok, porque = america.chegou_inteira(str(portao / "x.pdf"), guardada)
    assert ok, porque


# ----------------------------------------------------------------------
# Nao repetir: a licao do ZIMI, de novo
# ----------------------------------------------------------------------

def _fonte():
    import inspect
    return inspect.getsource(america.fechar)


def _caminho_principal():
    """
    So o trecho que FAZ o trabalho, do passo 1 em diante.

    Antes dele ha a saida rapida do 'ja fechei este?', que tambem apaga -
    e apagar ali e faxina atrasada, nao o fim do trabalho. Sem separar os
    dois, um teste que procura 'o primeiro os.remove' casa com o bloco
    errado e passa a mentir.
    """
    fonte = _fonte()
    return fonte[fonte.index("# --- 1. a copia guardada"):]


def test_pergunta_pelo_registro_ANTES_de_imprimir():
    """
    'Ja fechei este?' e a primeira pergunta do portao.

    Sem ela, um tropeco em qualquer passo tardio faz o vigia refazer o
    trabalho inteiro na volta seguinte - inclusive a prova. Tres folhas
    do mesmo flyer sairam assim.
    """
    fonte = _fonte()
    assert "carregar_registro()" in fonte
    assert fonte.index("carregar_registro()") < fonte.index("imprimir(")


def test_anota_no_registro_ANTES_de_tentar_apagar():
    """
    O trabalho esta FEITO quando a chapa esta no CTP. O apagar e faxina.

    Anotar depois da faxina foi o defeito: faxina que falha nao pode
    fazer o trabalho ser refeito.
    """
    principal = _caminho_principal()
    assert principal.index("salvar_registro(registro)") < principal.index("os.remove(")


def test_o_apagar_e_o_ultimo_passo():
    """Nada acontece depois de apagar - se apagou, acabou."""
    principal = _caminho_principal()
    depois = principal[principal.index("os.remove("):]
    assert "imprimir(" not in depois
    assert "os_do_servico" not in depois
    assert "shutil.copy2" not in depois


def test_a_faxina_atrasada_nao_refaz_o_trabalho():
    """
    Achando um arquivo JA FECHADO no portao, o portao termina a faxina -
    guarda a copia e tira dali - e mais nada.

    Ele NAO pode abrir OS, NAO pode imprimir e NAO pode gravar chapa: o
    trabalho ja foi feito uma vez, e refazer qualquer um dos tres custa
    dinheiro, papel ou chapa.
    """
    fonte = _fonte()
    # do marcador ate o 'return' que fecha a saida rapida - e NAO ate o
    # passo 1, que ja e o caminho principal e viria junto no recorte
    comeco = fonte.index("relato[\"ja_feito\"] = True")
    bloco = fonte[comeco:fonte.index("return relato", comeco)]
    assert "os.remove(caminho)" in bloco, "a faxina atrasada tem de apagar"
    assert "os_do_servico" not in bloco
    assert "imprimir(" not in bloco
    assert "pasta_saida_do_dia" not in bloco


# ----------------------------------------------------------------------
# O nome e a maquina
# ----------------------------------------------------------------------

def test_o_MONTAGEM_cai_no_nome_da_chapa():
    """
    Na pasta do cliente o '_MONTAGEM' separa a montagem do original. No
    CTP nao ha original com que confundir, entao ele sai - foi assim que
    os operadores fizeram 'CRISTAOS.pdf' virar '525x459_AMERICA_CRISTAOS'.
    """
    nome = america.nome_da_chapa("CRISTAOS_MONTAGEM.pdf", 525, 459, set("CMYK"))
    assert nome == "525x459_CMYK_AMERICA_CRISTAOS"


def test_acento_cai_do_nome_da_chapa():
    """Acento em nome de chapa atravessa rede e RIP - e nem todos leem igual."""
    nome = america.nome_da_chapa("CRISTÃOS.pdf", 525, 459, set("CMYK"))
    assert "CRISTAOS" in nome and "Ã" not in nome


def test_a_maquina_sai_do_tamanho_e_da_cor():
    """Ate o F4 na PM52; acima dele, colorido na SM74 e peb na MOZP."""
    assert america.maquina_da_america(510, set("CMYK")) == (525, 459)
    assert america.maquina_da_america(700, set("CMYK")) == (745, 605)
    assert america.maquina_da_america(700, {"GRAY"}) == (650, 550)


def test_o_limite_do_formato_4_e_o_mesmo_do_gerempre():
    """
    560 mm separa F4 de F2 na OS. O numero mora em um lugar so - antes
    estava escrito a mao no gerempre.py e na ferramenta de montagem.
    """
    from finart_ctp.config import MAIOR_LADO_F4
    assert MAIOR_LADO_F4 == 560
    assert america.maquina_da_america(560, set("CMYK")) == (525, 459)
    assert america.maquina_da_america(561, set("CMYK")) == (745, 605)


def test_uma_cor_conta_como_preto_e_branco():
    assert america.e_preto_e_branco({"GRAY"})
    assert america.e_preto_e_branco({"K"})
    assert not america.e_preto_e_branco(set("CMYK"))
    assert not america.e_preto_e_branco({"C", "M"})


# ----------------------------------------------------------------------
# Sem prova, sem chapa - a mesma regra dos outros clientes
# ----------------------------------------------------------------------

def _arma_um_fechamento(monkeypatch, tmp_path, imprimir):
    """
    Um fechar() sem GEREMPRE, sem impressora e sem CTP de verdade. So o
    que interessa aqui e o que acontece quando a prova nao sai.
    """
    import finart_ctp.processador as P
    import finart_ctp.prova as PR
    dia = tmp_path / "dia"; portao = dia / "PARA CTP"; portao.mkdir(parents=True)
    ctp = tmp_path / "ctp"; ctp.mkdir()
    arquivo = str(portao / "x_MONTAGEM.pdf")
    _pdf(arquivo, b"montagem")

    monkeypatch.setattr(america, "medir", lambda p: (525.0, 459.0, set("CMYK")))
    monkeypatch.setattr(america.gerempre, "os_do_servico",
                        lambda s, con=None: (19999, 1, "abri"))
    monkeypatch.setattr(P, "_verso_da_os", lambda n: None)
    monkeypatch.setattr(PR, "imprimir", imprimir)
    import finart_ctp.monitor as M
    monkeypatch.setattr(M, "pasta_saida_do_dia", lambda: str(ctp))
    registro = {}
    monkeypatch.setattr(america, "carregar_registro", lambda: dict(registro))
    monkeypatch.setattr(america, "salvar_registro", lambda r: registro.update(r))
    return arquivo, str(dia), ctp, registro


def test_impressora_fora_do_ar_segura_o_arquivo_no_portao(monkeypatch, tmp_path):
    """
    Papel na mao do operador e o que prova que o servico saiu. Se a prova
    nao sai, NAO se grava chapa, NAO se anota e NAO se apaga: o arquivo
    fica, e a volta seguinte tenta de novo - com a OS reaproveitada e a
    trava de copia unica impedindo prova repetida.
    """
    def cair(*a, **k):
        raise RuntimeError("impressora fora do ar")

    arquivo, dia, ctp, registro = _arma_um_fechamento(monkeypatch, tmp_path, cair)
    relato = america.fechar(arquivo, dia)

    assert relato["prova"] is False
    assert not relato["apagado"]
    assert os.path.exists(arquivo), "o arquivo tem de ficar no portao"
    assert not os.listdir(str(ctp)), "sem prova, nada vai para o CTP"
    assert not registro, "sem prova, nada e anotado"
    assert any("PARO" in p for p in relato["passos"])


def test_prova_que_ja_saiu_nao_segura_o_arquivo(monkeypatch, tmp_path):
    """JaImprimiu nao e falha: o papel ja esta na mao. O fechamento segue."""
    import finart_ctp.prova as PR

    def ja_saiu(*a, **k):
        raise PR.JaImprimiu("ja foi impresso")

    arquivo, dia, ctp, registro = _arma_um_fechamento(monkeypatch, tmp_path, ja_saiu)
    relato = america.fechar(arquivo, dia)

    assert relato["prova"] == 0
    assert relato["apagado"]
    assert registro, "o trabalho foi anotado"
    assert os.listdir(str(ctp)), "a chapa foi para o CTP"


# ----------------------------------------------------------------------
# O ARQUIVO QUE CHEGA NO COREL - 15/09/2026
# ----------------------------------------------------------------------
# "se eu coloco o arquivo la dentro dessa pasta no corel, voce segue a
# sequencia que vc usa na voprix ou creative, conferir a pinca, se nao
# tiver pincada, colocar do jeito certo... voce gera o pdf dentro da
# mesma pasta, e da andamento para saida do ctp" - o operador.

def _pdf_do_tamanho(caminho, larg_mm, alt_mm):
    """
    Um PDF de uma pagina com esta medida E COM DESENHO DENTRO.

    O desenho importa: pagina em branco nao tem o que deslocar, e o
    merge_transformed_page nao escreve matriz nenhuma - o teste passaria
    sem provar nada.
    """
    import pypdf
    from pypdf.generic import (ArrayObject, DecodedStreamObject, FloatObject,
                               NameObject)

    larg = larg_mm / 25.4 * 72
    alt = alt_mm / 25.4 * 72

    escritor = pypdf.PdfWriter()
    pagina = escritor.add_blank_page(width=larg, height=alt)
    pagina[NameObject("/MediaBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(larg), FloatObject(alt)])

    tinta = DecodedStreamObject()
    tinta.set_data(b"0 0 0 rg 0 0 %.2f %.2f re f" % (larg, alt))
    pagina[NameObject("/Contents")] = escritor._add_object(tinta)

    with open(caminho, "wb") as f:
        escritor.write(f)
    return caminho


def _onde_a_arte_ENCOSTOU(montagem):
    """(esquerda_mm, pe_mm) lidos da matriz que a montagem escreveu."""
    import re

    import pypdf

    conteudo = pypdf.PdfReader(montagem).pages[0].get_contents().get_data()
    # o pypdf escreve '1 0.0 0.0 1 tx ty cm' - com os zeros em decimal
    achou = re.search(rb"1 0(?:\.0+)? 0(?:\.0+)? 1 (-?[\d.]+) (-?[\d.]+) cm",
                      conteudo)
    assert achou, "a montagem nao deslocou a arte: %r" % conteudo[:120]
    return (float(achou.group(1)) / 72.0 * 25.4,
            float(achou.group(2)) / 72.0 * 25.4)


def _medida(pdf):
    import pypdf
    pag = pypdf.PdfReader(pdf).pages[0]
    return (float(pag.mediabox.width) / america.MM,
            float(pag.mediabox.height) / america.MM)


# ----------------------------------------------------------------------
# A CHAPA E A PINCA
# ----------------------------------------------------------------------

def test_as_tres_pincas_sao_as_que_o_operador_ditou():
    """
    "chapa 745x605, pinca 6,2cm / chapa 525x459, pinca de 6,0 cm /
    chapa de 650x550, pinca de 6cm" - o operador, 15/09/2026.
    """
    assert america.pinca_de((745, 605)) == 62.0
    assert america.pinca_de((525, 459)) == 60.0
    assert america.pinca_de((650, 550)) == 60.0


def test_reconhece_o_que_JA_vem_no_tamanho_da_chapa():
    """
    Cinco das oito montagens da AMERICA que existiam na pasta em
    15/09/2026 ja vinham 525x459. Essas nao se monta: ja estao prontas.
    """
    assert america.chapa_de(525, 459) == (525, 459)
    assert america.chapa_de(459, 525) == (525, 459), "a ordem nao importa"
    assert america.chapa_de(450, 600) is None


def test_a_pinca_tem_de_CABER_alem_da_arte():
    """De nada serve a arte caber se nao sobra a pinca embaixo dela."""
    assert america.cabe_na_chapa(500, 390, (525, 459))
    # 390 + 60 = 450, cabe nos 459; 400 + 60 = 460, nao cabe
    assert not america.cabe_na_chapa(500, 400, (525, 459))


# ----------------------------------------------------------------------
# EM QUE CHAPA MONTAR
# ----------------------------------------------------------------------

def test_a_regra_da_maquina_manda_quando_cabe():
    chapa, porque = america.onde_montar(500, 390, set("CMYK"))
    assert chapa == (525, 459)
    assert "regra" in porque


def test_nao_cabendo_na_da_regra_procura_outra():
    """
    O 'GUIA IMPRESSO CIRCUITO X_MONTAGEM F4' tem 325x430: entra em F4
    pela regra, mas 430 + 60 passa dos 459 da PM_52.
    """
    chapa, porque = america.onde_montar(325, 430, set("CMYK"))
    assert chapa == (650, 550)
    assert "nao cabia" in porque


def test_arte_que_so_cabe_DEITADA_faz_a_FIA_parar():
    """
    Girar sem marca de corte e chutar que lado e o pe. Errando, a arte
    vai de cabeca para baixo na maquina: chapa perdida e tiragem
    perdida. Isto e decisao de gente.
    """
    chapa, porque = america.onde_montar(450, 600, set("CMYK"))
    assert chapa is None
    assert "DEITADA" in porque and "nao sei que lado e o pe" in porque


def test_arte_maior_que_todas_as_chapas_faz_a_FIA_parar():
    chapa, porque = america.onde_montar(900, 700, set("CMYK"))
    assert chapa is None
    assert "nao cabe" in porque


def test_preto_e_branco_grande_vai_para_a_MOZP():
    chapa, _ = america.onde_montar(600, 440, {"K"})
    assert chapa == (650, 550)


# ----------------------------------------------------------------------
# A MONTAGEM
# ----------------------------------------------------------------------

def test_a_montagem_sai_NO_TAMANHO_da_chapa(tmp_path):
    arte = _pdf_do_tamanho(str(tmp_path / "arte.pdf"), 325, 430)
    fora = str(tmp_path / "arte_montagem.pdf")
    america.montar(arte, (650, 550), fora)
    larg, alt = _medida(fora)
    assert abs(larg - 650) < 0.1 and abs(alt - 550) < 0.1


def test_a_arte_fica_CENTRADA_e_com_a_pinca_no_pe(tmp_path):
    """
    Conferido contra as montagens de verdade da AMERICA, que vem
    centradas ao milimetro: 37,5 e 37,5 numa, 35,0 e 35,0 noutra.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "arte.pdf"), 325, 430)
    fora = str(tmp_path / "m.pdf")
    america.montar(arte, (650, 550), fora)

    esquerda, pe = _onde_a_arte_ENCOSTOU(fora)
    assert abs(esquerda - (650 - 325) / 2.0) < 0.1, "nao centrou"
    assert abs(pe - 60.0) < 0.1, "a arte nao ficou na pinca"


def test_a_pinca_da_745_e_DIFERENTE_das_outras(tmp_path):
    """62 mm, e nao 60. Errar dois milimetros e errar o registro."""
    arte = _pdf_do_tamanho(str(tmp_path / "arte.pdf"), 600, 400)
    fora = str(tmp_path / "m.pdf")
    america.montar(arte, (745, 605), fora)
    _esquerda, pe = _onde_a_arte_ENCOSTOU(fora)
    assert abs(pe - 62.0) < 0.1


# ----------------------------------------------------------------------
# CONFERIR A PINCA DE QUEM JA CHEGA MONTADO
# ----------------------------------------------------------------------

def test_tinta_longe_do_pe_passa_na_conferencia(monkeypatch):
    """
    As montagens de verdade tem a tinta a 45 e 46,5 mm do pe numa chapa
    de pinca 60: as marcas de corte e registro vivem DENTRO da pinca.
    Por isso a folga.
    """
    monkeypatch.setattr(america, "tinta_no_pe", lambda pdf: 45.0)
    recado = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert "conferida" in recado


def test_tinta_ENCOSTADA_no_pe_vira_aviso(monkeypatch):
    monkeypatch.setattr(america, "tinta_no_pe", lambda pdf: 3.0)
    recado = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert "ATENCAO" in recado and "SEM PINCA" in recado


def test_nao_dando_para_medir_a_tinta_nao_se_inventa(monkeypatch):
    monkeypatch.setattr(america, "tinta_no_pe", lambda pdf: None)
    assert america.conferir_a_pinca("qualquer.pdf", (525, 459)) is None


def test_a_conferencia_da_pinca_NAO_barra_o_servico(monkeypatch, tmp_path):
    """
    A montagem foi revisada por gente, e quem a aprovou sabe mais do que
    esta conta. O aviso e aviso.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    monkeypatch.setattr(america, "tinta_no_pe", lambda pdf: 2.0)
    monkeypatch.setattr(america, "medir",
                        lambda p: (525.0, 459.0, set("CMYK")))
    pronto, passos = america.do_pdf_pronto(arte)
    assert pronto == arte, "o aviso nao pode impedir o servico"
    assert any("ATENCAO" in p for p in passos)


# ----------------------------------------------------------------------
# O PORTAO NAO PODE FICAR COM DOIS PDFS
# ----------------------------------------------------------------------

def test_montando_o_PDF_solto_SAI_do_portao(tmp_path, monkeypatch):
    """
    Ficando os dois - o publicado e a montagem -, a volta seguinte do
    vigia acharia DUAS chapas para o mesmo servico: duas gravacoes e
    duas OS.
    """
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)

    cdr = str(portao / "arte.cdr")
    open(cdr, "wb").write(b"nao importa")
    publicado = str(portao / "arte.pdf")
    _pdf_do_tamanho(publicado, 325, 430)

    monkeypatch.setattr(america, "medir",
                        lambda p: (325.0, 430.0, set("CMYK")))

    # o PDF ja esta publicado ao lado; o que se testa e a metade que
    # decide a chapa e arruma o portao
    pronto, passos = america.do_pdf_pronto(publicado, str(dia))
    assert pronto and pronto.endswith("_montagem.pdf")

    sobraram = sorted(p for p in os.listdir(str(portao))
                      if p.lower().endswith(".pdf"))
    assert sobraram == ["arte_montagem.pdf"], sobraram
    assert os.path.exists(str(dia / "arte.pdf")), \
        "o PDF solto tem de ficar guardado, e nao sumir"


def test_o_cdr_SAI_do_portao_mas_NAO_e_apagado(tmp_path):
    """
    O .cdr e a fonte da montagem. Deixa-lo no portao o faria publicar de
    novo a cada volta; apaga-lo nao esta combinado com ninguem.
    """
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    cdr = str(portao / "arte.cdr")
    open(cdr, "wb").write(b"conteudo do corel")

    assert america.guardar_o_corel(cdr, str(dia)) is True
    assert not os.path.exists(cdr), "tinha de sair do portao"
    guardado = str(dia / "arte.cdr")
    assert os.path.exists(guardado)
    assert open(guardado, "rb").read() == b"conteudo do corel"


def test_o_vigia_olha_cdr_alem_de_pdf():
    fonte = open(america.__file__, encoding="utf-8").read()
    assert '(".pdf", ".cdr")' in fonte
