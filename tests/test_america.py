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
