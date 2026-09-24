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

def _pe_medido(monkeypatch, tinta, arte, topo=380.0):
    """Troca a medida do pe, que e a unica coisa que rasteriza aqui."""
    monkeypatch.setattr(america, "medir_o_pe", lambda pdf: (tinta, arte, topo))


def test_desenho_acima_da_pinca_passa_na_conferencia(monkeypatch):
    """
    O desenho das montagens boas comeca a 57,0 (pinca 60) e a 56,5
    (pinca 62) - ele desce ate ~5 mm abaixo da linha de corte, e isso e
    a SANGRIA, que a guilhotina come. A tinta desce mais ainda: sao as
    marcas, a 45-47.
    """
    _pe_medido(monkeypatch, tinta=47.0, arte=57.0)
    recado, pode = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert "conferida" in recado and pode


def test_desenho_ENCOSTADO_no_pe_e_SEM_PINCA(monkeypatch):
    _pe_medido(monkeypatch, tinta=2.0, arte=2.0)
    recado, pode = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert "SEM PINCA" in recado and not pode


def test_a_MARCA_dentro_da_pinca_nao_acusa_nada(monkeypatch):
    """
    Marca de corte a 45 mm numa pinca de 60 e o NORMAL, nao defeito.

    Confundir as duas foi o que obrigava a folga de 20 mm da conta
    antiga - folga que, de quebra, perdoava 20 mm de DESENHO na pinca.
    """
    _pe_medido(monkeypatch, tinta=45.0, arte=57.0)
    _, pode = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert pode


def test_nao_dando_para_medir_a_tinta_nao_se_inventa(monkeypatch):
    """Defeito nosso nao para o cliente: nao medi, entao nao acuso."""
    _pe_medido(monkeypatch, tinta=None, arte=None, topo=None)
    recado, pode = america.conferir_a_pinca("qualquer.pdf", (525, 459))
    assert recado is None and pode


def test_montagem_SEM_PINCA_nao_chega_ao_CTP(monkeypatch, tmp_path):
    """
    ATE 17/09/2026 ISTO PASSAVA, e o teste se chamava
    'test_a_conferencia_da_pinca_NAO_barra_o_servico' - a conferencia
    avisava e deixava seguir, porque "a montagem foi revisada por gente".

    O operador desfez: "nunca um arquivo pode ir sem pincar para o ctp".
    A faixa da pinca e onde a maquina SEGURA a folha - desenho ali nao
    imprime, e a chapa gravada nao serve. Aviso no log nao para ninguem.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    _pe_medido(monkeypatch, tinta=2.0, arte=2.0)
    monkeypatch.setattr(america, "medir",
                        lambda p: (525.0, 459.0, set("CMYK")))
    # sem saber ajustar, so resta parar
    monkeypatch.setattr(america, "ajustar_a_pinca",
                        lambda p, c, d, portao=None:
                        (None, "nao consegui medir"))
    pronto, passos = america.do_pdf_pronto(arte)
    assert pronto is None, "sem pinca nao vai para o CTP"
    assert any("PARO" in p for p in passos)


def test_montagem_COM_pinca_no_tamanho_da_chapa_segue(monkeypatch, tmp_path):
    """A trava nova nao pode segurar quem esta certo."""
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    _pe_medido(monkeypatch, tinta=47.0, arte=57.0)
    monkeypatch.setattr(america, "medir",
                        lambda p: (525.0, 459.0, set("CMYK")))
    pronto, passos = america.do_pdf_pronto(arte)
    assert pronto == arte
    assert any("conferida" in p for p in passos)


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


# ----------------------------------------------------------------------
# UMA COR NO PRETO: AS MARCAS TAMBEM
# ----------------------------------------------------------------------

def test_as_marcas_saem_em_K_quando_o_trabalho_e_de_uma_cor():
    """
    Regra do operador, 17/09/2026: "na america quando o trabalho for 1
    cor no preto, corte, registro e escala de cor, mantem so o canal do
    preto, para dar saida somente em 1 chapa".

    O caso foi o 'miolo 16x23 caderno padrao juan' de 16/09/2026. A arte
    e K puro nas duas paginas, mas a montagem saia CKMY - e o culpado
    nao era a arte:

        arte      C 0,0000  M 0,0000  Y 0,0000  K 0,0461
        montagem  C 0,0005  M 0,0005  Y 0,0005  K 0,0211

    Os 0,0005 IGUAIS nas tres sao as marcas, desenhadas em cor de
    registro (1 1 1 1) - que e o certo em quadricromia, para o impressor
    ver desencontro. Com UMA chapa nao ha registro a conferir, e a marca
    so servia para fazer o trabalho contar quatro.

    Depois do conserto: C=M=Y=0,00000 exatos, K 0,02140.
    """
    import inspect
    from ferramentas import montar_bate_vira as M

    fonte = inspect.getsource(M.marcas_em_pdf)
    assert "so_preto" in fonte
    assert "0 0 0 1 setcmykcolor" in fonte, "o traco em K"
    assert "1 1 1 1 setcmykcolor" in fonte, "e a cor de registro continua"

    # o registro e a escala saem pelo mesmo interruptor
    eps = inspect.getsource(M.eps_em_pdf)
    assert "so_preto" in eps
    assert "/Gray" in eps

    # e quem decide pergunta ao ARQUIVO, sem o perfil - armadilha 14
    montar = inspect.getsource(M.montar)
    assert "so_preto" in montar
    assert "sem_icc=True" in montar, "com o perfil a resposta sai errada"


# ----------------------------------------------------------------------
# UM ARQUIVO POR PAGINA NO CTP - 17/09/2026
#
# "nunca mande para o ctp arquivo, pdf com duas paginas, se o pdf tiver
# duas paginas igual o ultimo material da america, crie dois arquivos,
# com numeros na frente do nome exemplo 01..02.. e por ai vai (...)
# sempre coloca no ctp 01 pagina 01 arquivo por vez.. ele nao puxa
# multiplas paginas" - o operador.
#
# O caso: 'PASTA PRE MEETING fv.pdf', frente e verso montados a mao num
# arquivo so. A OS cobrou as 8 chapas certas (2 paginas x CMYK) e a
# prova saiu com as duas - so o CTP e que receberia uma chapa de duas
# paginas, e a gravadora puxa uma.
# ----------------------------------------------------------------------

def test_montagem_de_duas_paginas_vira_DOIS_arquivos_no_ctp(monkeypatch,
                                                            tmp_path):
    import pypdf

    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 2))
    _pdf(arquivo, paginas=2)

    relato = america.fechar(arquivo, dia)

    saiu = sorted(os.listdir(str(ctp)))
    assert saiu == ["525x459_CMYK_AMERICA_x_01.pdf",
                    "525x459_CMYK_AMERICA_x_02.pdf"], saiu
    for nome in saiu:
        assert len(pypdf.PdfReader(os.path.join(str(ctp), nome)).pages) == 1
    assert relato["saidas"] == saiu
    assert list(registro.values())[0]["saidas"] == saiu


def test_uma_pagina_segue_indo_inteira_e_sem_numero(monkeypatch, tmp_path):
    """O numero e para quem tem paginas a ordenar. Uma chapa nao tem."""
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 1))
    relato = america.fechar(arquivo, dia)

    assert os.listdir(str(ctp)) == ["525x459_CMYK_AMERICA_x.pdf"]
    assert relato["apagado"], "o fechamento correu inteiro"


def test_o_passo_do_log_conta_os_DOIS_arquivos(monkeypatch, tmp_path):
    """Quem le o log tem de ver o que foi para o CTP, e nao um nome so."""
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 2))
    _pdf(arquivo, paginas=2)

    relato = america.fechar(arquivo, dia)
    linha = [p for p in relato["passos"] if p.startswith("vai para o CTP")][0]
    assert "525x459_CMYK_AMERICA_x_01.pdf" in linha
    assert "525x459_CMYK_AMERICA_x_02.pdf" in linha


def test_as_chapas_de_metal_ja_contavam_as_duas_paginas(monkeypatch, tmp_path):
    """
    A conta da OS nunca esteve errada - 2 paginas x CMYK = 8 chapas.

    Vale fixar: o defeito era SO na entrega, e um conserto que mexesse na
    conta cobraria dobrado.
    """
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 2))
    _pdf(arquivo, paginas=2)

    relato = america.fechar(arquivo, dia)
    assert any("8 chapa(s) de metal" in p for p in relato["passos"])


# ----------------------------------------------------------------------
# A PINCA SE MEDE ATE A MARCA DE CORTE - 17/09/2026
#
# "quando o arquivo e ft4 geralmente vai na chapa pequena deles 525x459,
# mais ela nao foi pincada com 6cm que e a pinca da chapa menor, entao
# esta errado, nunca um arquivo pode ir sem pincar para o ctp" - o
# operador, sobre o 'Receituario Orto Saude 2026'.
#
# A conta antiga punha a BORDA DO ARQUIVO na pinca. Nesse arquivo a
# marca de corte esta 16,5 mm acima da borda, entao a primeira linha de
# corte caiu a 76,4 mm numa chapa de pinca 60 - a montagem inteira subiu,
# e quem mede com a regua acha 76 onde devia achar 60.
#
# As oito montagens que a casa ja tinha feito comecam a tinta entre 45,0
# e 47,3 mm do pe; esta comecava a 63,8. Com o conserto sai 47,3.
# ----------------------------------------------------------------------

def _pdf_com_marca_de_corte(caminho, larg_mm, alt_mm, marca_mm):
    """
    Um PDF com marcas de corte de verdade nos quatro lados.

    As de baixo sao dois tracos HORIZONTAIS, um em cada margem lateral,
    na altura 'marca_mm' - que e como o marcas_de_corte le o pe.
    """
    import pypdf
    from pypdf.generic import (ArrayObject, DecodedStreamObject, FloatObject,
                               NameObject)

    P = 72.0 / 25.4
    larg, alt = larg_mm * P, alt_mm * P

    escritor = pypdf.PdfWriter()
    pagina = escritor.add_blank_page(width=larg, height=alt)
    pagina[NameObject("/MediaBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(larg), FloatObject(alt)])

    partes = [b"0 0 0 RG 0.25 w"]
    for y in (marca_mm, alt_mm - marca_mm):          # pe e topo
        for x0 in (2.0, larg_mm - 12.0):
            partes.append(b"%.2f %.2f m %.2f %.2f l S"
                          % (x0 * P, y * P, (x0 + 10.0) * P, y * P))
    for x in (marca_mm, larg_mm - marca_mm):         # esquerda e direita
        for y0 in (2.0, alt_mm - 12.0):
            partes.append(b"%.2f %.2f m %.2f %.2f l S"
                          % (x * P, y0 * P, x * P, (y0 + 10.0) * P))
    # e a arte, dentro do corte
    partes.append(b"0 0 0 rg %.2f %.2f %.2f %.2f re f"
                  % (marca_mm * P, marca_mm * P,
                     (larg_mm - 2 * marca_mm) * P,
                     (alt_mm - 2 * marca_mm) * P))

    tinta = DecodedStreamObject()
    tinta.set_data(b"\n".join(partes))
    pagina[NameObject("/Contents")] = escritor._add_object(tinta)
    with open(caminho, "wb") as f:
        escritor.write(f)
    return caminho


def test_a_marca_de_corte_e_que_cai_na_pinca(tmp_path):
    arte = _pdf_com_marca_de_corte(str(tmp_path / "a.pdf"), 480, 330, 16.5)
    base, de_onde = america.pe_da_montagem(arte, (525, 459))
    assert round(base, 1) == 43.5, "60 de pinca menos 16,5 de marca"
    assert "marca de corte" in de_onde


def test_a_montagem_assenta_pela_marca_e_nao_pela_borda(tmp_path):
    arte = _pdf_com_marca_de_corte(str(tmp_path / "a.pdf"), 480, 330, 16.5)
    montada = str(tmp_path / "m.pdf")
    america.montar(arte, (525, 459), montada)
    esquerda, pe = _onde_a_arte_ENCOSTOU(montada)
    assert round(pe, 1) == 43.5
    assert round(esquerda, 1) == 22.5, "centrada: (525-480)/2"


def test_a_linha_de_corte_cai_EXATAMENTE_na_pinca(tmp_path):
    """A conferencia que o operador faz com a regua."""
    arte = _pdf_com_marca_de_corte(str(tmp_path / "a.pdf"), 480, 330, 16.5)
    montada = str(tmp_path / "m.pdf")
    america.montar(arte, (525, 459), montada)
    _, pe = _onde_a_arte_ENCOSTOU(montada)
    assert round(pe + 16.5, 1) == 60.0


def test_sem_marca_de_corte_vale_a_borda_do_arquivo(tmp_path):
    """
    Das oito montagens da AMERICA de 15/09/2026, NENHUMA tinha marca
    reconhecivel. Para essas a borda e tudo o que ha, e a conta antiga
    continua sendo a certa - tirar isso pararia o cliente.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "a.pdf"), 480, 330)
    base, de_onde = america.pe_da_montagem(arte, (525, 459))
    assert base == 60.0
    assert "sem marca de corte" in de_onde


def test_marca_mais_funda_que_a_pinca_nao_joga_a_arte_fora_da_chapa(
        tmp_path, monkeypatch):
    """
    Margem maior que a pinca: 10 - 35 daria -25, e a borda do arquivo
    sairia POR BAIXO da chapa. Assenta no pe, e a linha de corte fica
    ACIMA da pinca - sobra, que nao machuca ninguem.

    Nao ha chapa da AMERICA em que isso aconteca hoje: o marcas_de_corte
    so enxerga marca ate 40 mm da borda (BORDA_MM) e as pincas dela sao
    60 e 62, entao a subtracao nunca fica negativa. A guarda existe para
    a pinca pequena que ainda pode aparecer, e o teste a alcanca pela
    unica porta honesta - trocando a pinca.
    """
    monkeypatch.setattr(america, "pinca_de",
                        lambda chapa, portao=None: 10.0)
    arte = _pdf_com_marca_de_corte(str(tmp_path / "a.pdf"), 300, 250, 35.0)
    base, de_onde = america.pe_da_montagem(arte, (525, 459))
    assert base == 0.0
    assert "mais que a pinca" in de_onde


def test_a_pinca_da_745_tambem_sai_da_marca(tmp_path):
    """A pinca e da CHAPA, e a conta e a mesma: 62 na SM 74."""
    arte = _pdf_com_marca_de_corte(str(tmp_path / "a.pdf"), 700, 400, 10.0)
    base, _ = america.pe_da_montagem(arte, (745, 605))
    assert round(base, 1) == 52.0, "62 de pinca menos 10 de marca"


# ----------------------------------------------------------------------
# SEM PINCA, EU PINCO - 17/09/2026
#
# "quando o arquivo for pra pasta PARA CTP, e nao estiver pincado vc ja
# ajusta, e sempre confere a pinca, para ver se esta pincada" - o
# operador.
#
# Ate a manha desse dia isto so avisava; a tarde passou a PARAR; e agora
# ajusta. Parar era o certo enquanto a FIA nao soubesse fazer - sabendo,
# parar e so empurrar para uma pessoa o que ela pode resolver e conferir.
# ----------------------------------------------------------------------

def test_o_desenho_sobe_ate_a_pinca(monkeypatch, tmp_path):
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    medidas = iter([(2.0, 2.0, 300.0),      # antes: encostada no pe
                    (45.0, 60.0, 358.0)])   # depois: conferida
    monkeypatch.setattr(america, "medir_o_pe", lambda pdf: next(medidas))
    saiu, conta = america.ajustar_a_pinca(arte, (525, 459),
                                          str(tmp_path / "p.pdf"))
    assert saiu, conta
    esquerda, pe = _onde_a_arte_ENCOSTOU(saiu)
    assert round(pe, 1) == 58.0, "subiu a pinca (60) menos onde estava (2)"
    assert round(esquerda, 1) == 0.0, "so sobe; nao mexe na largura"
    assert "Subi 58 mm" in conta


def test_quem_ja_esta_pincada_nao_se_mexe(monkeypatch, tmp_path):
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    _pe_medido(monkeypatch, tinta=47.0, arte=57.0)
    saiu, conta = america.ajustar_a_pinca(arte, (525, 459),
                                          str(tmp_path / "p.pdf"))
    assert saiu is None and "ja esta pincada" in conta
    assert not os.path.exists(str(tmp_path / "p.pdf"))


def test_nao_subo_o_que_nao_CABE(monkeypatch, tmp_path):
    """
    Arte cortada no topo e pior que arte na pinca: a primeira ninguem ve.

    Desenho de 2 a 440 numa chapa de 459: para pincar eu teria de subir
    58, e o topo iria a 498.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    _pe_medido(monkeypatch, tinta=2.0, arte=2.0, topo=440.0)
    saiu, conta = america.ajustar_a_pinca(arte, (525, 459),
                                          str(tmp_path / "p.pdf"))
    assert saiu is None
    assert "o topo sairia fora" in conta
    assert not os.path.exists(str(tmp_path / "p.pdf"))


def test_ajuste_que_nao_confere_e_JOGADO_FORA(monkeypatch, tmp_path):
    """
    O deslocamento e uma conta; que ele tenha acontecido e outra coisa.

    Se a medida depois nao der a pinca, o arquivo sai do disco - mandar
    para o CTP o que eu nao conferi seria pior que nao ter tentado.
    """
    arte = _pdf_do_tamanho(str(tmp_path / "x.pdf"), 525, 459)
    medidas = iter([(2.0, 2.0, 300.0), (2.0, 2.0, 300.0)])   # nao andou
    monkeypatch.setattr(america, "medir_o_pe", lambda pdf: next(medidas))
    destino = str(tmp_path / "p.pdf")
    saiu, conta = america.ajustar_a_pinca(arte, (525, 459), destino)
    assert saiu is None
    assert "Nao mando o que nao conferi" in conta
    assert not os.path.exists(destino)


def test_a_montagem_SEM_PINCA_e_pincada_e_segue_para_o_CTP(monkeypatch,
                                                           tmp_path):
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    arte = _pdf_do_tamanho(str(portao / "x.pdf"), 525, 459)
    monkeypatch.setattr(america, "medir",
                        lambda p: (525.0, 459.0, set("CMYK")))
    medidas = iter([(2.0, 2.0, 300.0),      # a conferencia acusa
                    (2.0, 2.0, 300.0),      # o ajuste mede de novo
                    (45.0, 60.0, 358.0)])   # e confere depois de subir
    monkeypatch.setattr(america, "medir_o_pe", lambda pdf: next(medidas))

    pronto, passos = america.do_pdf_pronto(arte, str(dia))

    assert pronto and pronto.endswith("_pincada.pdf")
    assert any("SEM PINCA" in p for p in passos)
    assert not os.path.exists(arte), "o sem-pinca sai do portao"
    assert (dia / "x.pdf").exists(), "mas a copia dele fica guardada"


def test_depois_de_MONTAR_a_pinca_tambem_e_conferida(monkeypatch, tmp_path):
    """
    "sempre confere a pinca" - inclusive no que a propria FIA montou.

    Nao e desconfianca boba: a conta acontece numa matriz que a FIA
    escreve no PDF, e entre escreve-la e ela valer ha um programa
    inteiro. Quem mede e o Ghostscript, que nao sabe o que a FIA quis.
    """
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    arte = _pdf_do_tamanho(str(portao / "x.pdf"), 480, 330)
    monkeypatch.setattr(america, "medir",
                        lambda p: (480.0, 330.0, set("CMYK")))
    monkeypatch.setattr(america, "medir_o_pe",
                        lambda pdf: (47.0, 57.0, 367.0))
    pronto, passos = america.do_pdf_pronto(arte, str(dia))
    assert pronto and pronto.endswith("_montagem.pdf")
    assert any("pinca conferida no arquivo montado" in p for p in passos)


def test_montagem_que_NAO_confere_nao_vai_para_o_CTP(monkeypatch, tmp_path):
    dia = tmp_path / "dia"
    portao = dia / "PARA CTP"
    portao.mkdir(parents=True)
    arte = _pdf_do_tamanho(str(portao / "x.pdf"), 480, 330)
    monkeypatch.setattr(america, "medir",
                        lambda p: (480.0, 330.0, set("CMYK")))
    monkeypatch.setattr(america, "medir_o_pe",
                        lambda pdf: (2.0, 2.0, 300.0))
    pronto, passos = america.do_pdf_pronto(arte, str(dia))
    assert pronto is None
    assert any("montei e conferi" in p for p in passos)


# ----------------------------------------------------------------------
# A MEDIDA QUE SEPARA MARCA DE DESENHO
# ----------------------------------------------------------------------

def test_medir_o_pe_separa_a_marca_fina_do_desenho_largo(tmp_path):
    """
    Medido na montagem do Receituario, a 8 px/mm: as marcas dao 4 px por
    linha e o desenho 3438. Aqui o mesmo, em miniatura.
    """
    import pypdf
    from pypdf.generic import (ArrayObject, DecodedStreamObject, FloatObject,
                               NameObject)

    P = 72.0 / 25.4
    larg, alt = 200.0 * P, 300.0 * P
    escritor = pypdf.PdfWriter()
    pagina = escritor.add_blank_page(width=larg, height=alt)
    pagina[NameObject("/MediaBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(larg), FloatObject(alt)])
    fluxo = DecodedStreamObject()
    fluxo.set_data(
        # uma marca fina de 10 mm, comecando aos 20 mm do pe
        b"0 0 0 RG 0.25 w %.2f %.2f m %.2f %.2f l S\n"
        # e o desenho, largo, a partir dos 50 mm
        b"0 0 0 rg %.2f %.2f %.2f %.2f re f"
        % (10 * P, 20 * P, 20 * P, 20 * P,
           10 * P, 50 * P, 180 * P, 200 * P))
    pagina[NameObject("/Contents")] = escritor._add_object(fluxo)
    caminho = str(tmp_path / "m.pdf")
    with open(caminho, "wb") as f:
        escritor.write(f)

    tinta, desenho, topo = america.medir_o_pe(caminho)
    assert abs(tinta - 20.0) < 1.5, "a marca fina e a primeira tinta"
    assert abs(desenho - 50.0) < 1.5, "mas o desenho comeca bem acima"
    assert abs(topo - 250.0) < 1.5


def test_a_folga_da_sangria_separa_o_bom_do_sem_pinca():
    """
    Os numeros vieram dos arquivos, nao de cabeca:

        Receituario (pinca 60)      desenho a 57,0     -3,0
        PASTA PRE MEETING (62)      desenho a 56,5     -5,5
        No Auge da Loucura (60)     tinta   a  2,0    -58,0

    Entre -5,5 e -58 nao ha o que calibrar.
    """
    assert america.esta_pincada(57.0, 60.0)
    assert america.esta_pincada(56.5, 62.0)
    assert not america.esta_pincada(2.0, 60.0)
    assert america.esta_pincada(None, 60.0) is False


def test_a_regra_de_maquina_da_america_e_a_do_operador():
    """
    "quando for do tamanho maior do que o formato 4, e for colorido sera
    na chapa 745x605 com 6,2cm de pinca" - o operador, 17/09/2026,
    confirmando o que ja valia desde 10/09.
    """
    grande_colorido = america.maquina_da_america(600, set("CMYK"))
    assert grande_colorido == (745, 605)
    assert america.pinca_de(grande_colorido) == 62.0
    assert america.maquina_da_america(600, {"K"}) == (650, 550)
    assert america.maquina_da_america(560, set("CMYK")) == (525, 459)


# ----------------------------------------------------------------------
# A BANCADA - a maquina de fora da grafica, 20/09/2026
#
# "estou no notebook em casa, e o projeto da america foi mexido por
# ultimo na empresa, mas quero fazer alguns testes por aqui... quando eu
# der o comando mandar para ctp, voce manda para essa pasta, para que eu
# veja se esta tudo correto" - o operador.
#
# Fora da grafica faltam DUAS coisas, e so duas: o GEREMPRE e a
# impressora da prova. A bancada pula esses dois passos e faz o resto de
# verdade - copia guardada, chapa no CTP conferida, registro, faxina.
# ----------------------------------------------------------------------

def _bancada(monkeypatch, ligada=True):
    """Liga (ou desliga) a bancada dentro do america, sem tocar no config."""
    monkeypatch.setattr(america, "BANCADA", ligada)


def test_bancada_fecha_a_chapa_sem_gerempre_e_sem_impressora(monkeypatch,
                                                              tmp_path):
    """
    O caminho inteiro anda numa maquina que nao tem banco nem impressora.

    As duas de mentira aqui ESTOURAM se forem chamadas: o teste nao prova
    que a bancada 'passou por cima' de nada - prova que ela nao encostou.
    """
    def nao_me_chame(*a, **k):
        raise AssertionError("a bancada nao pode chamar isto")

    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, nao_me_chame)
    monkeypatch.setattr(america.gerempre, "os_do_servico", nao_me_chame)
    _bancada(monkeypatch)

    relato = america.fechar(arquivo, dia)

    assert os.listdir(str(ctp)) == ["525x459_CMYK_AMERICA_x.pdf"]
    assert relato["apagado"], "a faxina tambem acontece na bancada"
    assert registro, "o trabalho e anotado, como na Finart"
    assert os.path.exists(os.path.join(dia, "x_MONTAGEM.pdf")), \
        "a copia da casa continua na pasta do dia"


def test_bancada_NAO_inventa_numero_de_os(monkeypatch, tmp_path):
    """
    Sem banco, a OS e None - e o relato diz isso em todas as letras.

    Um numero de mentira viajaria no registro e no relato com cara de OS
    de verdade, e um dia alguem iria procura-lo no GEREMPRE.
    """
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 1))
    _bancada(monkeypatch)

    relato = america.fechar(arquivo, dia)

    assert relato["os"] is None
    assert list(registro.values())[0]["os"] is None
    assert any(p.startswith("BANCADA: NAO abri OS") for p in relato["passos"])
    assert any("NAO imprimi a prova" in p for p in relato["passos"])


def test_bancada_desligada_nao_muda_nada(monkeypatch, tmp_path):
    """
    Na maquina da grafica o caminho continua o de sempre: OS e prova.

    E o outro lado da trava - a bancada so existe onde foi ligada a mao.
    """
    chamadas = []
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path,
        lambda *a, **k: (chamadas.append("prova"), 1)[1])
    monkeypatch.setattr(america.gerempre, "os_do_servico",
                        lambda s, con=None: (chamadas.append("os"),
                                             (19999, 1, "abri"))[1])
    _bancada(monkeypatch, ligada=False)

    relato = america.fechar(arquivo, dia)

    assert chamadas == ["os", "prova"]
    assert relato["os"] == 19999


def test_bancada_e_gerempre_nao_convivem():
    """
    A trava do arranque: config_local com as duas para o programa.

    O perigo nao e a bancada existir - e ela chegar na maquina da grafica
    sem ninguem perceber. Ali seria chapa gravada e entregue SEM OS, e
    nada daria erro em lugar nenhum ate o fim do mes.
    """
    import pytest

    from finart_ctp.config import conferir_a_bancada

    # cada uma sozinha passa
    conferir_a_bancada(False, r"127.0.0.1/3050:C:\GEREMPRE\bdados\neo.fdb")
    conferir_a_bancada(True, "")

    with pytest.raises(RuntimeError) as e:
        conferir_a_bancada(True, r"127.0.0.1/3050:C:\GEREMPRE\bdados\neo.fdb")
    assert "sem cobranca" in str(e.value)


# ----------------------------------------------------------------------
# A TINTA DE TRACO, E OS DOIS PASSOS QUE DECIDEM
# ----------------------------------------------------------------------
# A proporcao levanta o CANDIDATO; quem decide e a pergunta que ela nao
# faz - esta tinta aparece SOZINHA em algum pixel?

def _valentim(monkeypatch, cobertura, sozinha):
    """
    O caso de 22/09/2026 montado a mao: cobertura conhecida e a resposta
    do 'aparece sozinha' ditada, para o teste nao depender de separar
    uma chapa de verdade a cada rodada.
    """
    from finart_ctp import ghostscript
    monkeypatch.setattr(america, "cobertura_por_pagina",
                        lambda *a, **k: [cobertura])
    vistas = []

    def _sozinha(pdf, pagina, tinta, **k):
        vistas.append(tinta)
        return sozinha, 451

    monkeypatch.setattr(ghostscript, "tinta_aparece_sozinha", _sozinha)
    return vistas


def test_a_tinta_que_APARECE_SOZINHA_fica_mesmo_sendo_pouca(tmp_path,
                                                            monkeypatch):
    """
    O 'SORV. VALENTIM - TAMPA 240ml', 22/09/2026, medido no arquivo:

        C 0,23931   M 0,20570   Y 0,36601   K 0,01057

    O K vale 2,9% da tinta mais forte - candidato a traco pela
    proporcao. E ele aparece SOZINHO em 451 pixels: desenha alguma
    coisa, provavelmente o texto da tampa.

    O QUE ACONTECEU SEM ESTE TESTE. O caminho da AMERICA rodava so a
    proporcao - o segundo passo estava escrito no comentario e nao no
    codigo. A chapa foi para o CTP como _CMY_, sem o preto; a OS cobrou
    3 no lugar de 4; e a tampa imprimiria sem o texto, o que so
    apareceria na maquina.
    """
    pdf = str(tmp_path / "tampa.pdf")
    _pdf_do_tamanho(pdf, 525.0, 459.0)
    vistas = _valentim(monkeypatch,
                       {"C": 0.23931, "M": 0.20570, "Y": 0.36601,
                        "K": 0.01057},
                       sozinha=True)

    larg, alt, tintas = america.medir(pdf)
    assert tintas == set("CMYK"), \
        "o K desenha em 451 pixels e tinha de ficar"
    assert vistas == ["K"], "so o candidato se mede - medir o resto e caro"


def test_a_tinta_que_NUNCA_aparece_sozinha_cai(tmp_path, monkeypatch):
    """
    O caso que a regra nasceu para pegar: cruz de corte em cor de
    registro, DENTRO do corte. Ela nao desenha forma nenhuma - so
    enriquece tom -, e tirar nao muda o impresso.

    Medido em 21/09/2026 nos dois AMERICA: C 0,0002 contra K 0,1090.
    """
    pdf = str(tmp_path / "comanda.pdf")
    _pdf_do_tamanho(pdf, 525.0, 459.0)
    _valentim(monkeypatch,
              {"C": 0.0002, "M": 0.0002, "Y": 0.0002, "K": 0.1090},
              sozinha=False)

    larg, alt, tintas = america.medir(pdf)
    assert tintas == {"K"}, "as tres de traco tinham de cair"


def test_nao_dando_para_medir_a_tinta_FICA(tmp_path, monkeypatch):
    """
    Chapa a mais na conta se conserta com uma linha na OS; chapa a menos
    no CTP so aparece na maquina, com papel e tiragem gastos. Entao a
    duvida decide a favor de gravar.
    """
    pdf = str(tmp_path / "duvida.pdf")
    _pdf_do_tamanho(pdf, 525.0, 459.0)
    _valentim(monkeypatch,
              {"C": 0.23931, "M": 0.20570, "Y": 0.36601, "K": 0.01057},
              sozinha=None)

    larg, alt, tintas = america.medir(pdf)
    assert tintas == set("CMYK"), "sem medida, a tinta fica"


# ----------------------------------------------------------------------
# A resolucao da AMERICA
#
# Regra do operador, 23/09/2026: "se for formato menor para a 525x459,
# converte o arquivo para 1000 dpi e se for maior para a chapa 745x605,
# converte para 800 dpi".
#
# NAO E A REGRA DO MOTOR, e e por isso que ela tem teste proprio: o
# montar_bate_vira usa 900 ate o formato 4 e 800 acima. Duas regras
# parecidas e o jeito mais facil de uma virar a outra sem ninguem ver -
# e ninguem veria, porque dpi errado nao da erro em lugar nenhum: a
# chapa grava, imprime, e so um olho treinado nota depois.
# ----------------------------------------------------------------------

def test_o_dpi_da_america_e_o_que_o_operador_ditou():
    assert america.dpi_da_america((525, 459)) == 1000
    assert america.dpi_da_america((745, 605)) == 800


def test_a_pequena_da_america_NAO_usa_os_900_do_motor():
    """
    O motor da 900 no formato 4; a AMERICA pediu 1000. Se alguem trocar
    esta tabela pela do motor, e aqui que se percebe.
    """
    assert america.dpi_da_america((525, 459)) != 900


def test_chapa_que_nao_esta_na_tabela_cai_no_menor_dpi():
    """
    Na duvida, 800: dpi a mais so pesa o arquivo, e chapa grande em 1000
    da PDF enorme sem ninguem ver diferenca.
    """
    assert america.dpi_da_america((650, 550)) == 800
    assert america.dpi_da_america((999, 999)) == 800


# ----------------------------------------------------------------------
# A pinca conferida no portao
#
# Ate 23/09/2026 o fechar() - o caminho do PARA CTP - mandava para o CTP
# sem conferir a pinca. So o outro caminho conferia. O buraco entrou
# junto com a montagem do portao, no mesmo dia, e contraria uma regra que
# o operador ditou com todas as letras em 17/09:
#
#     "nunca um arquivo pode ir sem pincar para o ctp"
#
# Ele nao dava erro: a chapa ia inteira para o CTP, gravava e imprimia. O
# defeito aparece na maquina, que segura a folha em cima do desenho.
# ----------------------------------------------------------------------

def test_chapa_sem_pinca_NAO_vai_para_o_ctp_pelo_portao(monkeypatch,
                                                        tmp_path):
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 1))
    monkeypatch.setattr(america, "conferir_a_pinca",
                        lambda p, c, portao=None: ("SEM PINCA: o desenho comeca a 2 mm "
                                      "do pe", False))
    relato = america.fechar(arquivo, dia)

    assert not os.listdir(str(ctp)), "chapa sem pinca nao pode ir ao CTP"
    assert os.path.exists(arquivo), "o arquivo fica no portao, para gente"
    assert not registro, "o que nao saiu nao se anota como feito"
    assert any("PARO" in p for p in relato["passos"])


def test_a_pinca_boa_deixa_o_portao_seguir(monkeypatch, tmp_path):
    """
    A trava barra o que esta errado, e NAO atrapalha o que esta certo -
    senao ela para a grafica em vez de proteger a chapa.
    """
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 1))
    monkeypatch.setattr(america, "conferir_a_pinca",
                        lambda p, c, portao=None: ("pinca conferida: o desenho comeca a "
                                      "60,0 mm do pe (pinca 60)", True))
    relato = america.fechar(arquivo, dia)

    assert os.listdir(str(ctp)), "a chapa boa vai para o CTP"
    assert registro, "o trabalho foi anotado"
    assert any("pinca conferida" in p for p in relato["passos"])


def test_so_olhar_nao_confere_nem_manda_nada(monkeypatch, tmp_path):
    """
    O 'so olhar' existe para dizer o que FARIA. Medir a pinca ali custaria
    um Ghostscript por arquivo a cada varredura, sem ninguem pedir.
    """
    arquivo, dia, ctp, registro = _arma_um_fechamento(
        monkeypatch, tmp_path, lambda *a, **k: (None, 1))
    chamou = []
    monkeypatch.setattr(america, "conferir_a_pinca",
                        lambda p, c, portao=None: (chamou.append(p), (None, True))[1])
    america.fechar(arquivo, dia, so_olhar=True)

    assert not chamou, "so olhar nao mede nada"
    assert not os.listdir(str(ctp))
