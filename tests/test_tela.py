# -*- coding: utf-8 -*-
"""
A TELA QUE CHAMA - 14/09/2026.

"consegue criar uma tela, para quando houver alguma pendencia no
sistema, quando precisar de mim, essa tela grande abrir automaticamente,
para que eu possa ver e agir mais rapido?" - o operador. E depois, vendo
o modelo: "pode colocar o aviso em tela cheia, pra ficar impossivel nao
ver, esse aviso e gerado exatamente na hora que vc informa um problema,
nao precisa acumular".

Nada aqui abre janela. O que se testa e o que decide se ela abre, o que
ela mostra e - o mais importante - que ela nunca derruba o programa que
grava chapa.
"""

import datetime

from finart_ctp import monitor as M
from finart_ctp import tela as T
from finart_ctp import utils as U


class JanelaViva(object):
    """Um processo de mentira que sobreviveu a partida."""

    returncode = None

    def poll(self):
        return None


def fila(pasta, *itens):
    for arquivo, motivo, cliente in itens:
        T.enfileirar(arquivo, motivo, cliente, pasta=str(pasta))
    return T.por_arquivo(T._ler_json(T.caminho_da_fila(str(pasta)), []))


# ----------------------------------------------------------------------
# A FILA DO QUE MOSTRAR
# ----------------------------------------------------------------------

def test_o_problema_entra_na_fila_na_hora(tmp_path):
    cartoes = fila(tmp_path, ("GRADE 3385.pdf", "nao sei que chapa usar",
                              "VIVA"))
    assert len(cartoes) == 1
    c = cartoes[0]
    assert c["arquivo"] == "GRADE 3385.pdf"
    assert c["cliente"] == "VIVA"
    assert c["motivos"] == [(1, "nao sei que chapa usar")]


def test_UM_arquivo_com_varios_problemas_e_UM_cartao(tmp_path):
    """
    Um .cdr de tres paginas sem marca de corte lanca quatro pendencias
    no mesmo segundo - uma por pagina, mais a do PDF guardado. Foi o
    'O.S 1035 - MPGO CARTAZES.cdr' em 14/09/2026, e no primeiro modelo
    da tela ele tomou os quatro primeiros cartoes sozinho, empurrando
    para fora da vista tudo o que veio depois.
    """
    cartoes = fila(
        tmp_path,
        ("O.S 1035.cdr", "pagina 1: nao achei a marca de corte", "PRIME"),
        ("O.S 1035.cdr", "pagina 2: nao achei a marca de corte", "PRIME"),
        ("O.S 1035.cdr", "pagina 3: nao achei a marca de corte", "PRIME"),
        ("O.S 1035.cdr", "PDF convertido guardado em C:/Finart", "PRIME"))

    assert len(cartoes) == 1
    assert len(cartoes[0]["motivos"]) == 4


def test_o_MESMO_problema_repetido_conta_em_vez_de_repetir(tmp_path):
    """
    Enquanto ninguem resolve, a varredura volta a reclamar. O 'CAPA
    CADERNO _2027' saiu dez vezes entre 09:08 e 09:22.
    """
    cartoes = fila(tmp_path, *[("CAPA 2027.pdf", "mesma OS", "FIALHO")] * 10)
    assert cartoes[0]["motivos"] == [(10, "mesma OS")]


def test_arquivos_diferentes_sao_cartoes_diferentes(tmp_path):
    cartoes = fila(tmp_path, ("um.pdf", "a", "SOLIDA"),
                   ("dois.pdf", "b", "VIVA"))
    assert [c["arquivo"] for c in cartoes] == ["um.pdf", "dois.pdf"]


def test_o_cliente_aparece_mesmo_vindo_so_numa_das_linhas(tmp_path):
    """
    Nem toda pendencia e anotada com o cliente - varias so tem o nome do
    arquivo. Sabendo de quem e, a tela diz.
    """
    cartoes = fila(tmp_path, ("x.pdf", "primeiro", None),
                   ("x.pdf", "segundo", "EMPORIO"))
    assert cartoes[0]["cliente"] == "EMPORIO"


def test_fechar_ESVAZIA_a_fila(tmp_path):
    """
    A tela e o aviso do que esta acontecendo agora, e nao a lista do que
    esta pendente - essa continua no _PENDENCIAS.txt. Sem esvaziar, a
    proxima pendencia reabriria a tela com o dia inteiro dentro.
    """
    fila(tmp_path, ("x.pdf", "algo", "SOLIDA"))
    T.esvaziar(str(tmp_path))
    assert T._ler_json(T.caminho_da_fila(str(tmp_path)), None) == []


# ----------------------------------------------------------------------
# UMA TELA DE CADA VEZ
# ----------------------------------------------------------------------

def test_a_segunda_pendencia_NAO_abre_uma_segunda_janela(tmp_path,
                                                         monkeypatch,
                                                         com_tela):
    """
    Duas janelas em tela cheia, uma por cima da outra, seriam duas para
    fechar. A que ja esta no ar le a fila sozinha.
    """
    subiu = []
    monkeypatch.setattr(T, "ESPERAR_O_FILHO", 0)
    monkeypatch.setattr(T.subprocess, "Popen",
                        lambda *a, **k: (subiu.append(a), JanelaViva())[1])

    assert T.chamar("um.pdf", "a", "SOLIDA", pasta=str(tmp_path)) is True
    assert len(subiu) == 1

    T.trancar(str(tmp_path))                 # a janela subiu e bateu
    assert T.chamar("dois.pdf", "b", "VIVA", pasta=str(tmp_path)) is False
    assert len(subiu) == 1, "subiu uma segunda janela"

    # mas o segundo problema esta na fila, para a janela aberta pegar
    cartoes = T.por_arquivo(T._ler_json(T.caminho_da_fila(str(tmp_path)), []))
    assert [c["arquivo"] for c in cartoes] == ["um.pdf", "dois.pdf"]


def test_janela_que_MORREU_nao_tranca_a_tela_para_sempre(tmp_path,
                                                         monkeypatch):
    """
    Uma janela fechada de mau jeito deixaria a tranca para tras, e
    nenhuma pendencia voltaria a abrir a tela - calada, que e o pior
    defeito possivel numa coisa que existe para avisar.

    Por isso a tranca vale pela BATIDA, e nao pela existencia do
    arquivo.
    """
    agora = 1000.0
    T.trancar(str(tmp_path), agora=agora)
    assert T.ha_tela_aberta(str(tmp_path), agora=agora + 5) is True
    assert T.ha_tela_aberta(str(tmp_path),
                            agora=agora + T.ABANDONADA + 1) is False


def test_a_batida_e_mais_curta_que_a_espera():
    """Senao a propria janela viva seria dada por morta entre batidas."""
    assert T.BATIDA * 2 < T.ABANDONADA


def test_sem_tranca_nenhuma_a_tela_abre(tmp_path):
    assert T.ha_tela_aberta(str(tmp_path)) is False


# ----------------------------------------------------------------------
# A TELA NUNCA DERRUBA A GRAVACAO
# ----------------------------------------------------------------------

def test_chamar_nao_levanta_quando_o_processo_nao_sobe(tmp_path,
                                                       monkeypatch,
                                                       com_tela):
    def nao(*a, **k):
        raise OSError("nao consegui criar o processo")

    monkeypatch.setattr(T.subprocess, "Popen", nao)
    assert T.chamar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path)) is False


def test_pendencia_continua_sendo_anotada_mesmo_com_a_tela_quebrada(
        tmp_path, monkeypatch):
    """
    A tela e um aviso. Se ela falhar, o log e o _PENDENCIAS.txt tem de
    sair do mesmo jeito - eles e que sao o registro.
    """
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "TELA_DE_PENDENCIA", True)

    def explodir(*a, **k):
        raise RuntimeError("a tela quebrou")

    monkeypatch.setattr(T, "chamar", explodir)
    U.anotar_pendencia("GRADE 1.pdf", "um motivo qualquer", "VIVA")

    escrito = open(str(tmp_path / "_PENDENCIAS.txt"), encoding="utf-8").read()
    assert "GRADE 1.pdf" in escrito and "um motivo qualquer" in escrito


def test_a_tela_pode_ser_DESLIGADA_por_uma_chave(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "TELA_DE_PENDENCIA", False)
    chamadas = []
    monkeypatch.setattr(T, "chamar", lambda *a, **k: chamadas.append(a))

    U.anotar_pendencia("x.pdf", "motivo", "SOLIDA")
    assert chamadas == []


def test_toda_pendencia_passa_pela_tela(tmp_path, monkeypatch):
    """
    O gancho fica no anotar_pendencia, que e por onde TODAS passam -
    trinta e poucos lugares no programa. Pondo em cada um deles, o
    proximo a ser escrito esqueceria.
    """
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "TELA_DE_PENDENCIA", True)
    chamadas = []
    monkeypatch.setattr(T, "chamar", lambda *a, **k: chamadas.append(a))

    U.anotar_pendencia("GRADE 1.pdf", "motivo", "VIVA")
    assert chamadas == [("GRADE 1.pdf", "motivo", "VIVA")]


def test_anotar_no_arquivo_NAO_abre_a_tela(tmp_path, monkeypatch):
    """
    Ha lugares que so registram, sem alarde - a linha do PDF guardado,
    por exemplo. Eles nao chamam ninguem.
    """
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "TELA_DE_PENDENCIA", True)
    chamadas = []
    monkeypatch.setattr(T, "chamar", lambda *a, **k: chamadas.append(a))

    U.anotar_no_arquivo("x.pdf", "so para o arquivo", "SOLIDA")
    assert chamadas == []


# ----------------------------------------------------------------------
# O MODELO
# ----------------------------------------------------------------------

def test_os_exemplos_tem_a_forma_de_um_cartao_de_verdade():
    """
    O '--modelo' desenha a mesma tela com pendencias de verdade de
    14/09/2026. Exemplo com forma diferente da real mostraria uma tela
    que nao existe.
    """
    for c in T._exemplos():
        assert set(c) == {"quando", "cliente", "arquivo", "motivos"}
        assert c["motivos"] and all(isinstance(n, int) and t
                                    for n, t in c["motivos"])


# ----------------------------------------------------------------------
# A TELA QUE NAO ABRIU - 15/09/2026
# ----------------------------------------------------------------------
# "outra coisa, nao abriu a tela de pendencias para me avisar, o que
# ouve?" - o operador.
#
# A FIA roda pelo F5 do VS Code, e o depurador embrulha o subprocess
# dela para grudar nos processos filhos. O filho subia e caia. O
# 'chamar' devolvia False e NAO DIZIA NADA: a fila ficou escrita no
# disco, o log nao registrou uma linha, e so se soube porque o operador
# reparou.
#
# Avisador que falha em silencio nao serve para nada. Estes testes
# amarram as tres defesas: falar, conferir se o filho vingou, e tentar
# de novo na volta seguinte.


def test_falhar_ao_subir_a_janela_DIZ_no_log(tmp_path, monkeypatch,
                                             com_tela):
    recados = []

    def nao(*a, **k):
        raise OSError("o depurador atrapalhou")

    monkeypatch.setattr(T.subprocess, "Popen", nao)
    assert T.chamar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path),
                    log=recados.append) is False
    assert len(recados) == 1
    assert "NAO ABRIU" in recados[0]
    assert "_PENDENCIAS.txt" in recados[0], \
        "tem de dizer onde a pendencia ficou guardada"


def test_janela_que_SOBE_E_CAI_tambem_e_dita(tmp_path, monkeypatch,
                                             com_tela):
    """
    O caso de 15/09/2026: o Popen devolveu sucesso e o filho morreu na
    partida. Sem olhar depois, isso passa por 'deu certo'.
    """
    class Morreu(object):
        returncode = 1

        def poll(self):
            return 1

    monkeypatch.setattr(T.subprocess, "Popen", lambda *a, **k: Morreu())
    monkeypatch.setattr(T, "ESPERAR_O_FILHO", 0)
    recados = []
    assert T.chamar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path),
                    log=recados.append) is False
    assert len(recados) == 1
    assert "SUBIU E CAIU" in recados[0]


def test_janela_que_VINGA_nao_enche_o_log(tmp_path, monkeypatch, com_tela):
    monkeypatch.setattr(T.subprocess, "Popen",
                        lambda *a, **k: JanelaViva())
    monkeypatch.setattr(T, "ESPERAR_O_FILHO", 0)
    recados = []
    assert T.chamar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path),
                    log=recados.append) is True
    assert recados == []


def test_a_pendencia_FICA_na_fila_mesmo_quando_a_janela_nao_sobe(
        tmp_path, monkeypatch, com_tela):
    """
    E o que permite tentar de novo. Perdendo a fila, o aviso morria com
    a janela que nao subiu.
    """
    monkeypatch.setattr(T.subprocess, "Popen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("nao")))
    T.chamar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path),
             log=lambda t: None)
    fila = T._ler_json(T.caminho_da_fila(str(tmp_path)), [])
    assert len(fila) == 1
    assert fila[0]["arquivo"] == "x.pdf"


def test_a_rodada_do_laco_TENTA_DE_NOVO_o_que_nao_subiu(tmp_path,
                                                        monkeypatch):
    subiu = []
    monkeypatch.setattr(T.subprocess, "Popen",
                        lambda *a, **k: (subiu.append(a), JanelaViva())[1])
    monkeypatch.setattr(T, "ESPERAR_O_FILHO", 0)

    T.enfileirar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path))
    assert T.rodada(pasta=str(tmp_path)) is True
    assert len(subiu) == 1


def test_a_rodada_NAO_sobe_nada_com_a_fila_vazia(tmp_path, monkeypatch):
    subiu = []
    monkeypatch.setattr(T.subprocess, "Popen", lambda *a, **k: subiu.append(a))
    assert T.rodada(pasta=str(tmp_path)) is False
    assert subiu == []


def test_a_rodada_NAO_sobe_uma_segunda_janela(tmp_path, monkeypatch):
    subiu = []
    monkeypatch.setattr(T.subprocess, "Popen", lambda *a, **k: subiu.append(a))
    T.enfileirar("x.pdf", "algo", "SOLIDA", pasta=str(tmp_path))
    T.trancar(str(tmp_path))
    assert T.rodada(pasta=str(tmp_path)) is False
    assert subiu == []


def test_o_laco_chama_a_rede_de_seguranca():
    fonte = open(M.__file__, encoding="utf-8").read()
    assert "tela.rodada()" in fonte


def test_o_depurador_do_VSCODE_nao_gruda_nos_filhos():
    """
    "type": "debugpy" sem "subProcess": false faz o depurador embrulhar
    o subprocess da FIA e tentar grudar no processo da tela. Era essa a
    causa de 15/09/2026.
    """
    import json

    with open(".vscode/launch.json", encoding="utf-8") as f:
        config = json.load(f)
    for c in config["configurations"]:
        assert c.get("subProcess") is False, c.get("name")
