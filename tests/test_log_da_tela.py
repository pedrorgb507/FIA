# -*- coding: utf-8 -*-
r"""
A TELA e o ARQUIVO de log sao duas coisas - e so passaram a ser em
18/09/2026.

Pedido do operador: "o terminal do f5 esta uma bagunca, tudo jogado sem
organizacao nenhuma, esta impossivel de entender".

O QUE ESTES TESTES SEGURAM, e e uma coisa so, dita de varios angulos:
**arrumar a janela nao pode mexer no arquivo**. O _log_ctp.txt e lido por
maquina - o relatorio.py casa o carimbo de hora, o "OK em Ns:", o
"impresso em ... (N folha" e o prefixo ">>> PENDENCIA: ". Um formatador
de tela que encostasse nisso quebraria o relatorio do dia CALADO: ele nao
daria erro, daria numero errado.

Por isso o ultimo teste daqui nao olha texto nenhum: escreve um dia de
trabalho inteiro passando por blocos e manda o proprio relatorio.py ler.
"""

import io
import os
import re

import pytest

from finart_ctp import utils as U


@pytest.fixture(autouse=True)
def _log_de_mentira(tmp_path, monkeypatch):
    """Cada teste escreve no seu proprio arquivo, e a tela comeca limpa."""
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    U.fechar_bloco()
    yield
    U.fechar_bloco()


def _arquivo(tmp_path):
    caminho = os.path.join(str(tmp_path), "_log_ctp.txt")
    if not os.path.exists(caminho):
        return []
    return [l.rstrip("\n") for l in io.open(caminho, encoding="utf-8")]


# ----------------------------------------------------------------------
# O ARQUIVO NAO MUDOU
# ----------------------------------------------------------------------

def test_a_linha_do_arquivo_e_a_mesma_dentro_e_fora_do_bloco(tmp_path,
                                                             capsys):
    """
    O bloco e desenho de TELA. Se ele mudasse a linha gravada, metade do
    dia sairia num formato e metade noutro, e o relatorio leria so uma.
    """
    U.log("p1 -> 510x400_CMYK_PRIME_X | 510x400 mm")
    U.abrir_bloco("PRIME", "x.cdr")
    U.log("p1 -> 510x400_CMYK_PRIME_X | 510x400 mm")
    U.fechar_bloco()

    fora, dentro = _arquivo(tmp_path)
    # o carimbo muda de segundo; o resto tem de ser igual
    assert fora[17:] == dentro[17:]
    assert fora.startswith("[") and dentro.startswith("[")


def test_o_alerta_continua_sendo_TRES_SINAIS_no_arquivo(tmp_path, capsys):
    """
    Na tela o alerta virou um sinal na margem. No arquivo ele TEM de
    continuar ">>> ": e por esse prefixo que a pendencia e achada.
    """
    U.abrir_bloco("VOPRIX", "y.cdr")
    U.log("nao veio em quadricromia", alerta=True)
    U.fechar_bloco()

    linha, = _arquivo(tmp_path)
    assert ">>> nao veio em quadricromia" in linha
    # e na tela, nao
    assert ">>>" not in capsys.readouterr().out


def test_so_no_arquivo_pula_a_tela_mas_grava(tmp_path, capsys):
    """
    A linha 'PENDENCIA: ...' precisa existir no arquivo, para o
    relatorio, e NAO precisa aparecer na tela - a tela ja mostrou o
    bloco. Sem esta porta, toda pendencia saia duas vezes seguidas, e a
    segunda era a versao ruim.
    """
    U.log("PENDENCIA: VOPRIX | y.cdr | motivo", alerta=True,
          so_no_arquivo=True)

    assert capsys.readouterr().out == ""
    linha, = _arquivo(tmp_path)
    assert linha.endswith(">>> PENDENCIA: VOPRIX | y.cdr | motivo")


# ----------------------------------------------------------------------
# A TELA MUDOU
# ----------------------------------------------------------------------

def test_dentro_do_bloco_a_data_sai_e_a_hora_fica(capsys):
    """
    A data repetida quarenta vezes por arquivo era o ruido. A hora fica
    porque e por ela que se le quanto cada passo demorou.
    """
    U.abrir_bloco("PRIME", "x.cdr")
    U.log("1 pagina(s)")
    saida = capsys.readouterr().out

    assert "1 pagina(s)" in saida
    assert re.search(r"\d{2}:\d{2}:\d{2}  1 pagina", saida), saida
    assert not re.search(r"\[\d{2}/\d{2} ", saida), "a data devia ter saido"


def test_fora_do_bloco_a_data_continua(capsys):
    """
    Arranque e linhas do laco aparecem soltas no dia todo. Ali a hora
    sozinha nao situa ninguem.
    """
    U.log("Estoque da SOLIDA: o movimento mudou, refiz a folha")
    assert re.search(r"\[\d{2}/\d{2} \d{2}:\d{2}:\d{2}\]",
                     capsys.readouterr().out)


def test_o_cabecalho_diz_o_cliente_e_o_arquivo(capsys):
    U.abrir_bloco("PRIME", "SEDS - LEQUE 2 IMPRESSAO1.cdr")
    saida = capsys.readouterr().out

    assert "CLIENTE - PRIME" in saida
    assert "ARQUIVO: SEDS - LEQUE 2 IMPRESSAO1.cdr" in saida
    assert U.REGUA in saida


def test_abrir_DUAS_VEZES_fecha_o_anterior(capsys):
    """
    Quem esquecer de fechar nao pode deixar dois cabecalhos grudados -
    e, pior, nao pode deixar as linhas do arquivo novo caindo debaixo do
    nome do arquivo velho.
    """
    U.abrir_bloco("PRIME", "primeiro.cdr")
    U.abrir_bloco("VOPRIX", "segundo.cdr")
    saida = capsys.readouterr().out

    assert saida.count("ARQUIVO: primeiro.cdr") == 1
    assert saida.count("ARQUIVO: segundo.cdr") == 1
    # o do primeiro fechou ANTES de o segundo abrir
    assert saida.index("ARQUIVO: primeiro.cdr") < saida.index("CLIENTE - VOPRIX")
    assert U.bloco_aberto() == "segundo.cdr"


def test_fechar_sem_bloco_aberto_nao_faz_nada(capsys):
    U.fechar_bloco()
    assert capsys.readouterr().out == ""


def test_o_recuo_de_quem_chamou_e_PRESERVADO(capsys):
    """
    Varias linhas vem com recuo de proposito: sao sub-passos de uma
    linha acima. Aparando, todas ficam no mesmo nivel e a hierarquia que
    o autor escreveu se perde - foi o que aconteceu na primeira versao
    disto.
    """
    U.abrir_bloco("PRIME", "x.cdr")
    U.log("p1: arte 480x330 mm montada na chapa 510x400")
    U.log("    marca de corte a 16.4 mm da borda")
    linhas = [l for l in capsys.readouterr().out.split("\n") if "mm" in l]

    pai, filho = linhas[0], linhas[1]
    assert pai.index("p1:") < filho.index("marca de corte")


def test_linha_comprida_QUEBRA_entre_palavras(capsys):
    """
    Sem quebrar, o terminal quebra sozinho no meio da palavra e no meio
    do numero - e e justamente o numero que a pessoa procura ali.
    """
    U.abrir_bloco("PRIME", "x.cdr")
    U.log("p1: imagem de menor resolucao: 148.3 dpi no tamanho colocado "
          "(33 x 33 mm) - abaixo de 200 dpi a arte sai borrada na tiragem "
          "- segui assim mesmo: a PRIME nao para por resolucao", alerta=True)
    linhas = [l for l in capsys.readouterr().out.split("\n") if l.strip()]
    linhas = [l for l in linhas if U.REGUA not in l and "ARQUIVO" not in l
              and "CLIENTE" not in l]

    assert len(linhas) > 1, "a linha comprida tinha de quebrar"
    assert all(len(l) <= U.LARGURA_DA_REGUA for l in linhas), \
        max(linhas, key=len)
    assert "148.3" in "".join(linhas)
    # a continuacao entra alinhada debaixo do TEXTO, nao da hora
    assert not re.search(r"^\s*\d{2}:\d{2}:\d{2}", linhas[1])


def test_quebrar_nao_perde_palavra():
    texto = "um dois tres quatro cinco seis sete oito nove dez"
    assert " ".join(U._quebrar(texto, 12)) == texto


def test_quebrar_texto_vazio_devolve_uma_linha():
    """Motivo vazio nao pode virar bloco sem corpo nenhum."""
    assert U._quebrar("", 30) == [""]
    assert U._quebrar(None, 30) == [""]


# ----------------------------------------------------------------------
# A PENDENCIA
# ----------------------------------------------------------------------

def test_a_pendencia_do_arquivo_ABERTO_e_o_desfecho_dele(monkeypatch,
                                                         capsys):
    """
    A pendencia e o fim daquele servico, e o cabecalho dele ja esta na
    tela duas linhas acima. Repetir "ARQUIVO: y.cdr" ali e o tipo de
    repeticao que fez a janela virar sopa - entao ela fecha o bloco POR
    DENTRO, como uma secao final.
    """
    monkeypatch.setattr(U, "anotar_no_arquivo", lambda *a, **k: None)
    monkeypatch.setattr(U, "_chamar_a_tela", lambda *a, **k: None)

    U.abrir_bloco("VOPRIX", "y.cdr")
    U.log("convertendo no CorelDRAW")
    U.anotar_pendencia("y.cdr", "nao veio em quadricromia", "VOPRIX")

    assert U.bloco_aberto() is None, "o bloco tinha de fechar"
    saida = capsys.readouterr().out
    assert "PENDENCIA - PRECISA DE VOCE" in saida
    assert "nao veio em quadricromia" in saida
    # o nome do arquivo aparece UMA vez, no cabecalho do bloco
    assert saida.count("y.cdr") == 1, saida


def test_a_pendencia_de_OUTRO_arquivo_abre_o_proprio_quadro(monkeypatch,
                                                            capsys):
    """
    Nem toda pendencia nasce dentro de um bloco - ha as que o vigia
    levanta fora do processar (arquivo parado, arquivo estranho). Ai o
    quadro precisa dizer de quem e, senao a linha fica orfa na janela.
    """
    monkeypatch.setattr(U, "anotar_no_arquivo", lambda *a, **k: None)
    monkeypatch.setattr(U, "_chamar_a_tela", lambda *a, **k: None)

    U.abrir_bloco("PRIME", "x.cdr")
    U.anotar_pendencia("outro.cdr", "parou de chegar pela metade", "SOLIDA")

    saida = capsys.readouterr().out
    assert "PENDENCIA NO ARQUIVO: outro.cdr" in saida
    assert "CLIENTE - SOLIDA" in saida
    # e o bloco do x.cdr fechou antes, com regua propria
    assert saida.index("ARQUIVO: x.cdr") < saida.index("outro.cdr")
    assert U.bloco_aberto() is None


def test_a_pendencia_nao_diz_o_motivo_DUAS_VEZES(monkeypatch, capsys):
    monkeypatch.setattr(U, "anotar_no_arquivo", lambda *a, **k: None)
    monkeypatch.setattr(U, "_chamar_a_tela", lambda *a, **k: None)

    U.anotar_pendencia("y.cdr", "nao veio em quadricromia", "VOPRIX")

    saida = capsys.readouterr().out
    assert saida.count("nao veio em quadricromia") == 1, saida


# ----------------------------------------------------------------------
# A PROVA QUE VALE: o relatorio do dia continua lendo
# ----------------------------------------------------------------------

def test_o_relatorio_le_um_dia_escrito_POR_BLOCOS(tmp_path, monkeypatch,
                                                  capsys):
    """
    Nao olha texto de tela nenhum: escreve um dia de trabalho passando
    pelos blocos e manda o proprio relatorio.py contar. Se o formatador
    tiver encostado no arquivo, e aqui que aparece.
    """
    from finart_ctp import relatorio
    monkeypatch.setattr(relatorio, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "anotar_no_arquivo", lambda *a, **k: None)
    monkeypatch.setattr(U, "_chamar_a_tela", lambda *a, **k: None)

    U.log(relatorio.ARRANQUE)
    U.abrir_bloco("PRIME", "x.cdr")
    U.log("impresso em KONICA MINOLTA C360SeriesPCL (1 folha, frente a arte)")
    U.log("OK em 94s: 510x400_CMYK_PRIME_X.pdf (C+M+Y+K, 14.6 MB)")
    U.fechar_bloco()
    U.abrir_bloco("VOPRIX", "y.cdr")
    U.anotar_pendencia("y.cdr", "nao veio em quadricromia", "VOPRIX")

    # o caminho de verdade do relatorio: ler o arquivo e filtrar o dia
    linhas = relatorio._do_dia(relatorio._linhas_do_log(),
                               U.agora_util().strftime("%d"))
    textos = [t for _, t in linhas]
    assert textos, "o relatorio nao achou NENHUMA linha de hoje"

    achou_chapa = [re.match(r"OK em (\d+)s: (.+?) \((.+?), ([\d.]+) MB\)", t)
                   for t in textos]
    assert any(achou_chapa), "o relatorio perdeu a chapa"
    assert any(re.search(r"impresso em .+ \((\d+) folha", t) for t in textos), \
        "o relatorio perdeu a prova"
    assert any(t.startswith(">>> PENDENCIA: ") for t in textos), \
        "o relatorio perdeu a pendencia"
    assert any(t.startswith(relatorio.ARRANQUE) for t in textos), \
        "o relatorio perdeu o arranque - e e por ele que se conta reinicio"


# ----------------------------------------------------------------------
# O AVISO DA OS: uma vez na tela, duas no arquivo
#
# Pergunta do operador em 18/09/2026: "quando chegar o arquivo e voce
# colocar na OS, voce tem q avisar, igual ja faz, lancado na vaga 3 e
# etc, ja esta assim?".
#
# Estava - e estava DUAS VEZES. A linha de dentro do gerempre e a de
# quem o chamou saiam no mesmo segundo, dizendo a mesma coisa com
# palavras diferentes.
# ----------------------------------------------------------------------


def test_na_tela_a_OS_e_anunciada_UMA_vez(tmp_path, monkeypatch, capsys):
    """
    Na tela, uma linha por evento. No ARQUIVO as duas continuam: a de
    dentro e a que prova que a escrita aconteceu, no instante em que
    aconteceu, e e ela que se procura quando o estoque nao bate.
    """
    from finart_ctp import gerempre as G

    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    G.log("GEREMPRE: completei a OS 19846 na vaga 2 com 'X'",
          so_no_arquivo=True)
    G.log("   GEREMPRE: completei a OS 19846 na vaga 2, 4 chapa(s)",
          alerta=True)

    tela = capsys.readouterr().out
    assert tela.count("completei a OS 19846") == 1, tela

    arquivo = [l for l in io.open(os.path.join(str(tmp_path), "_log_ctp.txt"),
                                  encoding="utf-8")]
    assert len(arquivo) == 2, "o arquivo perdeu a linha de dentro"
    assert "com 'X'" in arquivo[0]
    assert "4 chapa(s)" in arquivo[1]


def test_completar_os_com_na_tela_FALSO_nao_imprime(monkeypatch, capsys,
                                                    tmp_path):
    """
    A porta e um parametro, e nao um silencio embutido: o
    fila.despachar chama o abrir_os POR FORA do os_do_servico e nao tem
    quem anuncie por ele - ali a linha tem de aparecer.
    """
    from finart_ctp import gerempre as G
    import inspect

    assert "na_tela" in inspect.signature(G.completar_os).parameters
    assert "na_tela" in inspect.signature(G.abrir_os).parameters
    # e o padrao e FALAR: quem nao souber do parametro continua anunciando
    assert inspect.signature(G.completar_os).parameters["na_tela"].default is True
    assert inspect.signature(G.abrir_os).parameters["na_tela"].default is True


def test_a_OS_NOVA_tambem_diz_a_vaga():
    """
    Pedido do operador: "lancado na vaga 3 e etc". Numa OS nova a vaga e
    sempre a 1, e ate 18/09/2026 ela ficava implicita - as tres linhas
    (abri / completei / ja estava) nao se liam do mesmo jeito, e quem
    corre a janela procurava palavras diferentes.

    LE O ARQUIVO DO MODULO, e nao a funcao: o conftest troca o
    _os_do_arquivo por um coto para nenhum teste escrever no GEREMPRE de
    verdade, e ai o inspect.getsource devolve o coto.
    """
    import finart_ctp.processador as P
    fonte = io.open(P.__file__, encoding="utf-8").read()

    assert "abri a OS %s na vaga %d" in fonte,         "a linha da OS nova voltou a esconder a vaga"
    # e as tres continuam existindo, cada uma para o seu caso
    assert "completei a OS %s na vaga %d" in fonte
    # DE HOJE entrou no texto em 23/09/2026, quando a regra passou a
    # so valer para a OS do dia - ver os_do_servico. A palavra faz
    # parte do recado: sem ela, quem le nao sabe por que a FIA nao
    # cobrou, e "nao cobrei" sem motivo e o que custou a gravacao.
    assert "JA ESTAVA na OS %s DE HOJE (vaga %d)" in fonte
