# -*- coding: utf-8 -*-
"""
A FOLHA DE ESTOQUE DE CHAPAS - 14/09/2026.

"quero voltar a questao agora dos relatorios, para eu acompanhar
diariamente o estoque de chapas da solida" - o operador.

A folha responde uma pergunta so: QUANTOS DIAS AINDA TEM. Errar essa
conta para cima e deixar a gravacao parar com servico na fila, entao os
testes aqui cuidam dela e das duas armadilhas que ela tem: o CHAMIN,
que parece minimo e e preco, e a chapa desativada, que carrega saldo
que nao existe em prateleira nenhuma.
"""

import datetime
import os

from finart_ctp import estoque as E
from finart_ctp import monitor as M


class CursorFalso(object):
    """Um cursor com o banco da SOLIDA de mentira dentro."""

    def __init__(self, dados):
        self.dados = dados
        self.pedidos = []
        self.ultimo = None

    def execute(self, sql, parametros=None):
        self.pedidos.append((sql, parametros))
        self.ultimo = sql

    def fetchone(self):
        if "MAX(MOVCOD)" in self.ultimo:
            return self.dados["sentinela"]
        if "COUNT(*), SUM(CHAQTD)" in self.ultimo:
            return self.dados.get("paradas", (0, 0))
        if "OSTIT1" in self.ultimo:
            return self.dados["os"]
        return None

    def fetchall(self):
        if "FROM CHA WHERE CHACLI = ? AND CHAINA = 0" in self.ultimo:
            return self.dados["cha"]
        if self.ultimo.startswith("SELECT CHACOD, CHAQTD FROM CHA"):
            return [(c[0], c[4]) for c in self.dados["cha"]]
        if "SUM(MOVQTD) FROM MOV" in self.ultimo and "GROUP BY MOVCHA" \
                in self.ultimo:
            return self.dados["soma_mov"]
        if "SUM(MOVSDA), SUM(MOVENT)" in self.ultimo:
            return self.dados["por_dia"]
        if "MOVCHA, MOVNCH" in self.ultimo:
            return self.dados["do_dia"]
        return []


class ConexaoFalsa(object):
    def __init__(self, dados):
        self.cur = CursorFalso(dados)
        self.fechou = False

    def cursor(self):
        return self.cur

    def close(self):
        self.fechou = True


HOJE = datetime.date(2026, 9, 14)          # uma segunda-feira


def banco(**muda):
    """O retrato da SOLIDA em 14/09/2026, lido da producao naquele dia."""
    dias = []
    for n in range(1, 11):
        dias.append((HOJE - datetime.timedelta(days=n), 40.0, 0.0))
    dias.append((HOJE, 28.0, 100.0))
    dado = {
        "sentinela": (131502, 1235274, 175.0),
        # cod, nome, alt, lar, qtd, preco   (so as ATIVAS)
        "cha": [(98, "SOLIDA FT4", 510, 400, 200.0, 9.0)],
        "soma_mov": [(98, 200.0)],
        "por_dia": [(98, d, s, e) for d, s, e in dias],
        # MOVCHA, MOVNCH, MOVENT, MOVSDA, MOVQTD, MOVNOS, MOVNFU, MOVOBS
        "do_dia": [(98, "SOLIDA FT4", 0.0, 4.0, -4.0, 19688, "JOAOZIMAR",
                    "ORDEM SERVICO NR : 19688"),
                   (98, "SOLIDA FT4", 100.0, 0.0, 100.0, None,
                    "EUDSON JUNIOR", "ENTRADA 14/09/26")],
        # OSTIT1..4, OSESP1..4, OSLAN1..4, OSTIME, OSRESP
        "os": ("49831 - MARUSSA - PANFLETO", "", "", "",
               98, 0, 0, 0, 4, 0, 0, 0,
               datetime.time(10, 19, 20), "FINART (FIA)"),
        "paradas": (5, 15267.0),
    }
    dado.update(muda)
    return dado


# ----------------------------------------------------------------------
# A CONTA DA FOLGA
# ----------------------------------------------------------------------

def test_dia_sem_saida_NAO_entra_na_media():
    """
    Feriado, domingo e dia de maquina parada puxariam a media para
    baixo e a folga para cima - e folga a mais e chapa acabando sem
    ninguem esperar. So contam os dias em que saiu chapa.
    """
    historico = [(HOJE, 40.0, 0.0), (HOJE, 0.0, 100.0), (HOJE, 40.0, 0.0)]
    assert E.media_por_dia_util(historico) == 40.0


def test_a_media_olha_so_os_ultimos_dias():
    """
    A SOLIDA saiu de 25 por dia em agosto para 40 em setembro. Uma
    media da historia inteira diria 30 e daria folga que nao existe.
    """
    velhos = [(HOJE, 4.0, 0.0)] * 60
    novos = [(HOJE, 40.0, 0.0)] * E.DIAS_DA_MEDIA
    assert E.media_por_dia_util(velhos + novos) == 40.0


def test_sem_consumo_nao_se_inventa_prazo():
    assert E.media_por_dia_util([]) == 0.0
    assert E.dias_de_folga(100, 0.0) is None
    assert E.data_do_fim(None) is None


def test_a_folga_PULA_sabado_e_domingo():
    """
    Cinco dias de trabalho a partir de uma segunda acabam na segunda
    seguinte, nao na sexta. Contar calendario adiantaria o susto em
    dois setimos.
    """
    assert E.data_do_fim(5, de=HOJE) == datetime.date(2026, 9, 21)
    # e a sexta continua sendo sexta quando cabe na semana
    assert E.data_do_fim(4, de=HOJE) == datetime.date(2026, 9, 18)


def test_o_texto_da_folga_no_singular():
    chapa = {"folga": 1.4, "acaba": datetime.date(2026, 9, 15)}
    assert "1 dia de trabalho" in E._folga_em_texto(chapa)
    chapa = {"folga": 3.9, "acaba": datetime.date(2026, 9, 17)}
    assert "3 dias de trabalho" in E._folga_em_texto(chapa)


def test_saldo_que_nao_cobre_UM_dia_grita():
    chapa = {"folga": 0.6, "acaba": HOJE}
    assert E._folga_em_texto(chapa) == "ACABA HOJE"


# ----------------------------------------------------------------------
# AS DUAS ARMADILHAS DO CADASTRO
# ----------------------------------------------------------------------

def test_CHAMIN_e_PRECO_e_nao_minimo_de_estoque():
    """
    O nome do campo mente. Conferido em producao: a chapa 98 tem
    CHAMIN 9 e as 843 OS dela cobram 9,00; a 103 tem 13 e cobra 13,00.
    Sao os mesmos numeros de GEREMPRE_CHAPAS.

    Se um dia alguem ler CHAMIN como minimo, a folha dira '175 de
    minimo 9, tudo bem' na vespera de acabar. Este teste amarra o campo
    ao preco da tabela que a FIA usa para faturar.
    """
    from finart_ctp.config import GEREMPRE_CHAPAS

    con = ConexaoFalsa(banco())
    vivas = E.chapas_vivas(161, con)
    assert vivas[0]["preco"] == GEREMPRE_CHAPAS[("SOLIDA", (510, 400))][2]

    # e a folha o chama pelo nome certo: preco, nao minimo
    dados = E.levantar("SOLIDA", con=ConexaoFalsa(banco()), dia=HOJE)
    assert "minimo" not in E.folha.__doc__.lower()
    assert dados["chapas"][0]["preco"] == 9.0


def test_chapa_DESATIVADA_fica_de_fora_da_conta():
    """
    A SOLIDA tem oito chapas cadastradas e duas em uso. As paradas
    carregam 15.267 de saldo antigo - a 25 sozinha tem 8.662 - que nao
    existe em prateleira nenhuma. Somar aquilo daria estoque de
    mentira, e a folha diria que nunca acaba.
    """
    con = ConexaoFalsa(banco())
    E.chapas_vivas(161, con)
    sql = con.cur.pedidos[-1][0]
    assert "CHAINA = 0" in sql, "a consulta trouxe chapa desativada"


def test_as_desativadas_aparecem_no_rodape_como_nota():
    """
    Ficar de fora da conta nao e sumir: quem le precisa saber que ha
    saldo antigo no cadastro, senao a soma do GEREMPRE nunca vai bater
    com esta folha e a folha e que vai parecer errada.
    """
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["paradas"] == (5, 15267.0)


# ----------------------------------------------------------------------
# A SENTINELA
# ----------------------------------------------------------------------

def test_a_sentinela_conta_MAIS_que_o_maior_numero():
    """
    O TR_OS_BEFO APAGA e refaz todo o movimento de uma OS a cada
    gravacao. Uma OS que perde uma vaga fica com MENOS movimento e o
    MAX(MOVCOD) nao desce - entao so o MAX deixaria passar. Por isso
    vao junto o COUNT e a SOMA.
    """
    con = ConexaoFalsa(banco())
    E.sentinela(161, con)
    sql = con.cur.pedidos[-1][0]
    for pedaco in ("COUNT(*)", "MAX(MOVCOD)", "SUM(MOVQTD)"):
        assert pedaco in sql
    assert sql.count("SELECT") == 1, "tem de ser UMA consulta so"


def test_a_folha_so_e_refeita_quando_o_movimento_MUDA(tmp_path,
                                                      monkeypatch):
    escritas = []
    monkeypatch.setattr(E, "gravar",
                        lambda dados, pasta=None: escritas.append(1) or "x")
    E.esquecer()

    dados = banco()
    con = ConexaoFalsa(dados)
    assert E.acompanhar("SOLIDA", con=con) == "x"      # a primeira sempre
    assert E.acompanhar("SOLIDA", con=con) is None     # nada mudou
    assert len(escritas) == 1

    dados["sentinela"] = (131503, 1235275, 171.0)      # alguem lancou
    assert E.acompanhar("SOLIDA", con=con) == "x"
    assert len(escritas) == 2


def test_sem_GEREMPRE_a_folha_fica_como_estava(monkeypatch):
    """Sem banco nao se inventa estoque - e nao se derruba o laco."""
    from finart_ctp import gerempre

    def cair():
        raise gerempre.SemLigacao("o servidor esta fora do ar")

    monkeypatch.setattr(gerempre, "conectar", cair)
    E.esquecer()
    assert E.acompanhar("SOLIDA") is None


def test_cliente_que_nao_existe_nao_quebra():
    assert E.acompanhar("NAO EXISTE") is None
    assert E.levantar("NAO EXISTE") is None


# ----------------------------------------------------------------------
# O LEVANTAMENTO E A FOLHA
# ----------------------------------------------------------------------

def test_o_levantamento_junta_o_dia_com_o_saldo():
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)

    chapa = dados["chapas"][0]
    assert chapa["saldo"] == 200.0
    assert chapa["entrou_hoje"] == 100.0
    assert chapa["saiu_hoje"] == 4.0
    assert chapa["media"] > 0
    assert chapa["razao_bate"] is True


def test_o_razao_que_NAO_bate_e_dito_na_folha():
    """
    CHA.CHAQTD tem de ser a soma dos MOV daquela chapa. Quando deixar
    de ser, o numero grande da folha nao vale - e quem le precisa saber
    disso ANTES de decidir comprar chapa.
    """
    con = ConexaoFalsa(banco(soma_mov=[(98, 173.0)]))
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["razao_bate"] is False

    pagina = E.folha(dados, dpi=72)
    assert pagina.size[0] > 0          # desenhou assim mesmo, com o aviso


def test_a_folha_sai_em_A4_em_pe():
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    pagina = E.folha(dados, dpi=150)
    largura, altura = pagina.size
    assert altura > largura
    assert abs(largura - 210 / 25.4 * 150) < 2
    assert abs(altura - 297 / 25.4 * 150) < 2


def test_dia_sem_movimento_nenhum_ainda_desenha():
    """De manha cedo a folha existe e diz 'nada ainda'."""
    con = ConexaoFalsa(banco(do_dia=[]))
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["movimento"] == []
    assert E.folha(dados, dpi=72)


def test_cliente_sem_chapa_ativa_nao_quebra():
    con = ConexaoFalsa(banco(cha=[], soma_mov=[]))
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"] == []
    assert E.folha(dados, dpi=72)


def test_o_dinheiro_sai_com_VIRGULA():
    assert E._dinheiro(9.0) == "R$ 9,00"
    assert E._dinheiro(8.5) == "R$ 8,50"


# ----------------------------------------------------------------------
# GRAVAR
# ----------------------------------------------------------------------

def test_a_folha_e_UMA_por_cliente_e_nao_uma_por_dia(tmp_path):
    """
    Quem acompanha estoque quer o numero de agora. Uma pasta com trinta
    PDFs por mes seria mais um lugar onde procurar - e o passado esta
    todo no GEREMPRE.
    """
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    um = E.gravar(dados, pasta=str(tmp_path))
    dois = E.gravar(dados, pasta=str(tmp_path))
    assert um == dois
    assert len(list(tmp_path.iterdir())) == 1


def test_gravar_troca_o_arquivo_no_fim_e_nao_escreve_por_cima(tmp_path):
    """
    A folha costuma estar aberta no leitor de PDF de alguem. Escrever
    direto por cima falharia no meio e deixaria um arquivo quebrado -
    entao ela e montada ao lado e trocada de uma vez.
    """
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    caminho = E.gravar(dados, pasta=str(tmp_path))
    assert caminho.endswith(".pdf")
    sobras = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert not sobras, "ficou lixo para tras: %s" % sobras


def test_gravar_em_pasta_que_nao_da_devolve_None(tmp_path, monkeypatch):
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    monkeypatch.setattr(E, "log", lambda *a, **k: None)

    def nao(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(E.os, "makedirs", nao)
    assert E.gravar(dados, pasta=str(tmp_path / "fundo")) is None


# ----------------------------------------------------------------------
# O LUGAR DELA NO LACO
# ----------------------------------------------------------------------

def test_o_laco_NAO_pergunta_ao_banco_a_cada_volta(monkeypatch):
    """
    O laco roda de 5 em 5 segundos. Perguntar sempre seriam 17 mil
    consultas por dia num Firebird 1.5 que os operadores usam o dia
    inteiro.
    """
    perguntas = []
    monkeypatch.setattr(M.estoque, "acompanhar",
                        lambda c: perguntas.append(c))

    quando = M.rodada_do_estoque(None, agora=1000.0)
    assert perguntas == ["SOLIDA"]
    assert quando == 1000.0

    M.rodada_do_estoque(quando, agora=1005.0)          # a volta seguinte
    assert len(perguntas) == 1, "perguntou de novo cedo demais"

    M.rodada_do_estoque(quando, agora=1000.0 + M.ESTOQUE_DE_QUANTO_EM_QUANTO)
    assert len(perguntas) == 2


def test_falhar_a_folha_NAO_derruba_o_laco(monkeypatch):
    """Estoque e acompanhamento; chapa e servico. Um nao segura o outro."""
    recados = []
    monkeypatch.setattr(M, "log", lambda t, **k: recados.append(t))

    def explodir(cliente):
        raise RuntimeError("o banco caiu no meio")

    monkeypatch.setattr(M.estoque, "acompanhar", explodir)
    assert M.rodada_do_estoque(None, agora=1000.0) == 1000.0
    assert any("folha de estoque" in t for t in recados)


def test_a_folha_sai_logo_no_arranque(monkeypatch):
    """Com a memoria zerada, a primeira volta ja desenha."""
    perguntas = []
    monkeypatch.setattr(M.estoque, "acompanhar",
                        lambda c: perguntas.append(c))
    M.rodada_do_estoque(None, agora=1.0)
    assert perguntas == ["SOLIDA"]


# ----------------------------------------------------------------------
# A FOLHA ABERTA NA TELA TRANCA O ARQUIVO - 14/09/2026
# ----------------------------------------------------------------------
# Na primeira vez que ela rodou de verdade, o operador estava com a
# folha aberta no leitor de PDF e a troca deu 'WinError 5: acesso
# negado'. No Windows, leitor de PDF aberto segura o arquivo.
#
# Isso nao e erro: e 'agora nao da'. O que nao pode acontecer e o
# movimento do dia ficar de fora para sempre porque a unica tentativa
# caiu num minuto em que a folha estava aberta.

def trancar(monkeypatch):
    """Faz a troca do arquivo falhar como o Windows faz."""
    def negar(*a, **k):
        raise PermissionError(5, "Acesso negado")

    monkeypatch.setattr(E.os, "replace", negar)


def test_folha_aberta_na_tela_nao_vira_erro(tmp_path, monkeypatch):
    recados = []
    monkeypatch.setattr(E, "log", lambda t, **k: recados.append((t, k)))
    E._RECLAMEI_DA_TRAVA.clear()
    trancar(monkeypatch)

    dados = E.levantar("SOLIDA", con=ConexaoFalsa(banco()), dia=HOJE)
    assert E.gravar(dados, pasta=str(tmp_path)) is None

    assert len(recados) == 1
    texto, como = recados[0]
    assert "aberta" in texto and "Feche" in texto
    assert not como.get("alerta"), "isto nao e para piscar em vermelho"


def test_a_reclamacao_da_trava_sai_UMA_vez(tmp_path, monkeypatch):
    """A cada minuto, o dia inteiro, encheria o log sozinha."""
    recados = []
    monkeypatch.setattr(E, "log", lambda t, **k: recados.append(t))
    E._RECLAMEI_DA_TRAVA.clear()
    trancar(monkeypatch)

    dados = E.levantar("SOLIDA", con=ConexaoFalsa(banco()), dia=HOJE)
    for _ in range(5):
        E.gravar(dados, pasta=str(tmp_path))
    assert len(recados) == 1


def test_a_folha_trancada_NAO_deixa_lixo_para_tras(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "log", lambda *a, **k: None)
    E._RECLAMEI_DA_TRAVA.clear()
    trancar(monkeypatch)

    dados = E.levantar("SOLIDA", con=ConexaoFalsa(banco()), dia=HOJE)
    E.gravar(dados, pasta=str(tmp_path))
    assert list(tmp_path.iterdir()) == [], "ficou o .tmp na pasta"


def test_o_que_nao_foi_gravado_e_TENTADO_DE_NOVO(tmp_path, monkeypatch):
    """
    O defeito que este teste barra: guardar a sentinela antes de saber
    se a folha foi gravada. Feito assim, um minuto de folha aberta
    apagaria o movimento do dia do relatorio ate o dia seguinte.
    """
    monkeypatch.setattr(E, "log", lambda *a, **k: None)
    E._RECLAMEI_DA_TRAVA.clear()
    E.esquecer()

    con = ConexaoFalsa(banco())
    trancar(monkeypatch)
    assert E.acompanhar("SOLIDA", con=con, pasta=str(tmp_path)) is None

    # a folha fechou; a volta seguinte tem de refazer, sem esperar que o
    # movimento mude de novo
    monkeypatch.undo()
    monkeypatch.setattr(E, "log", lambda *a, **k: None)
    caminho = E.acompanhar("SOLIDA", con=con, pasta=str(tmp_path))
    assert caminho and os.path.exists(caminho)


# ----------------------------------------------------------------------
# O NOME DO MATERIAL E O OPERADOR - 14/09/2026
# ----------------------------------------------------------------------
# "preciso de mais campos, mais informacoes... horario, numero da OS da
# finart (gerempre), nome do material, operador, chapa usada e
# quantidade" - o operador.
#
# A MOV nao guarda nenhum dos dois direito: ela tem o codigo da chapa, a
# quantidade e um nome de funcionario que nem sempre e quem fez. O nome
# do material mora na VAGA da OS que gerou o movimento, e e preciso
# saber QUAL vaga.

class CursorComOS(object):
    """Um cursor com uma OS de quatro vagas e o movimento dela."""

    def __init__(self, movimentos, os_):
        self.movimentos = movimentos
        self.os_ = os_
        self.ultimo = None

    def execute(self, sql, parametros=None):
        self.ultimo = sql

    def fetchall(self):
        if "MOVCHA, MOVNCH" in self.ultimo:
            return self.movimentos
        return []

    def fetchone(self):
        if "OSTIT1" in self.ultimo:
            return self.os_
        return None


class SoUmCursor(object):
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur


# a OS 19688 de 14/09/2026, lida da producao: quatro vagas, duas chapas
OS_19688 = ("49831 - MARUSSA - PANFLETO",
            "49833 - UNIMED MORRINHOS - TIMBRADO",
            "49835 - FLOR BELA - SACOLA",
            "49839 - LUCAS CALIL - CARTA CENTRAL",
            98, 103, 103, 103,
            4, 4, 1, 4,
            datetime.time(10, 19, 20), "FINART (FIA)")

# MOVCHA, MOVNCH, MOVENT, MOVSDA, MOVQTD, MOVNOS, MOVNFU, MOVOBS
MOV_19688 = [
    (98, "SOLIDA FT4", 0.0, 4.0, -4.0, 19688, "JOAOZIMAR", ""),
    (103, "SOLIDA 775X635 - 780E", 0.0, 4.0, -4.0, 19688, "JOAOZIMAR", ""),
    (103, "SOLIDA 775X635 - 780E", 0.0, 1.0, -1.0, 19688, "JOAOZIMAR", ""),
    (103, "SOLIDA 775X635 - 780E", 0.0, 4.0, -4.0, 19688, "JOAOZIMAR", ""),
]


def test_cada_movimento_acha_o_NOME_DO_MATERIAL_dele():
    """
    Quatro vagas, duas chapas e uma quantidade repetida: so a ordem nao
    resolveria, e so a chapa tambem nao.
    """
    con = SoUmCursor(CursorComOS(MOV_19688, OS_19688))
    linhas = E.do_dia(161, con, HOJE)
    assert [m["titulo"] for m in linhas] == [
        "49831 - MARUSSA - PANFLETO",
        "49833 - UNIMED MORRINHOS - TIMBRADO",
        "49835 - FLOR BELA - SACOLA",
        "49839 - LUCAS CALIL - CARTA CENTRAL"]


def test_a_hora_vem_da_OS_porque_a_MOV_so_tem_a_DATA():
    con = SoUmCursor(CursorComOS(MOV_19688, OS_19688))
    linhas = E.do_dia(161, con, HOJE)
    assert all(m["hora"] == datetime.time(10, 19, 20) for m in linhas)


def test_o_operador_e_quem_ABRIU_a_OS_e_nao_o_nome_da_MOV():
    """
    Os dois discordam, e a diferenca ja custou caro uma vez. A OS 19688
    foi aberta pela FIA, e os movimentos dela dizem JOAOZIMAR - porque o
    TR_OS_BEFO apaga e refaz TODO o movimento a cada gravacao, e quem
    fica no MOVNFU e quem salvou por ULTIMO.

    Dizer JOAOZIMAR ali poria no relatorio um servico como sendo de quem
    so passou por perto depois. Ver a armadilha 15 da skill.
    """
    con = SoUmCursor(CursorComOS(MOV_19688, OS_19688))
    linhas = E.do_dia(161, con, HOJE)
    assert all(m["quem"] == "FINART (FIA)" for m in linhas)


def test_entrada_A_MAO_nao_tem_OS_nem_vaga_e_mesmo_assim_aparece():
    """
    Chapa nova que chega e lancada direto no estoque, sem OS. Ela nao
    tem hora nem material - mas e o maior numero do dia, e sumir dali
    seria o relatorio nao bater com o saldo.
    """
    entrada = [(98, "SOLIDA FT4", 100.0, 0.0, 100.0, None, "EUDSON JUNIOR",
                "ENTRADA 14/09/26")]
    con = SoUmCursor(CursorComOS(entrada, None))
    linhas = E.do_dia(161, con, HOJE)
    assert len(linhas) == 1
    assert linhas[0]["titulo"] == "ENTRADA 14/09/26"
    assert linhas[0]["quem"] == "EUDSON JUNIOR"
    assert linhas[0]["hora"] is None
    assert linhas[0]["entrou"] == 100.0


def test_titulo_com_QUEBRA_DE_LINHA_vira_uma_linha_so():
    """
    O titulo '49793 - ANDRE KUBITSCHEK - PANFLETO' + quebra + 'R1 8CH (2
    JOGOS)' foi digitado assim no Delphi, que aceita. Numa tabela isso
    estoura a linha, e o Pillow nem consegue medir texto de varias
    linhas - a folha inteira deixava de sair.
    """
    quebrado = ("49793 - ANDRE KUBITSCHEK - PANFLETO" + chr(10)
                + "R1 8CH (2 JOGOS)",
                "", "", "", 103, 0, 0, 0, 8, 0, 0, 0,
                datetime.time(8, 17, 28), "JOAOZIMAR")
    mov = [(103, "SOLIDA 775X635 - 780E", 0.0, 8.0, -8.0, 19678,
            "JOAOZIMAR", "")]
    con = SoUmCursor(CursorComOS(mov, quebrado))
    linhas = E.do_dia(161, con, HOJE)
    assert chr(10) not in linhas[0]["titulo"]
    assert linhas[0]["titulo"].endswith("R1 8CH (2 JOGOS)")


def test_o_casamento_funciona_com_uma_vaga_faltando():
    """
    A lista de movimentos vem FILTRADA pelo dono da chapa. Uma OS com
    chapa propria da Finart no meio deixa um buraco, e casar pela ordem
    passaria o titulo errado para a linha seguinte.
    """
    movimentos = [{"chapa": 103, "qtd": -4.0}, {"chapa": 103, "qtd": -1.0}]
    vagas = [{"chapa": 98, "quantas": 4.0, "titulo": "a da Finart"},
             {"chapa": 103, "quantas": 4.0, "titulo": "certo"},
             {"chapa": 103, "quantas": 1.0, "titulo": "tambem certo"}]
    casadas = E._casar(movimentos, vagas)
    assert [v["titulo"] for v in casadas] == ["certo", "tambem certo"]


# ----------------------------------------------------------------------
# A FOLHA NOVA
# ----------------------------------------------------------------------

def test_o_grafico_dos_ultimos_dias_SAIU():
    """
    "retire os graficos que mostram os ultimos dias" - o operador. Ele
    mostrava a FORMA do consumo, que e coisa de quem planeja compra;
    quem esta no dia quer saber o que saiu, de quem e em que chapa.
    """
    fonte = open(E.__file__, encoding="utf-8").read()
    assert "o que saiu nos ultimos" not in fonte


def test_dia_cheio_passa_de_UMA_pagina():
    """
    Uma OS de quatro vagas lanca quatro linhas. Cortar no fim da folha
    esconderia lancamento, e lancamento escondido num relatorio de
    estoque e pior do que relatorio nenhum.
    """
    um = {"hora": None, "os": 1, "titulo": "x", "quem": "y",
          "nome": "SOLIDA FT4", "entrou": 0.0, "saiu": 4.0, "chapa": 98}
    poucos = E._paginas_do_movimento([um] * 10)
    assert len(poucos) == 1

    muitos = E._paginas_do_movimento([um] * 90)
    assert len(muitos) > 1
    assert sum(len(p) for p in muitos) == 90, "sumiu lancamento no meio"


def test_sem_movimento_nenhum_ainda_ha_uma_pagina():
    assert E._paginas_do_movimento([]) == [[]]


def test_a_folga_CURTA_cabe_na_coluna():
    """
    A forma por extenso ocupa 46,6 mm e a coluna tem 44 - ela escrevia
    por cima do saldo na primeira versao.
    """
    chapa = {"folga": 5.7, "acaba": datetime.date(2026, 9, 21)}
    assert E._folga_curta(chapa) == "5 dias - ate 21/09"
    assert len(E._folga_curta(chapa)) < len(E._folga_em_texto(chapa))


def test_as_colunas_do_saldo_NAO_se_atropelam():
    """
    O saldo e a folga sao os dois numeros que alguem vai ler de relance.
    Escritos um por cima do outro, nenhum dos dois serve.
    """
    assert E.SAL_SALDO < E.SAL_DURA
    assert E.SAL_ENTRADA < E.SAL_SAIDA < E.SAL_SALDO
    assert E.SAL_CHAPA < E.SAL_MEDIDA < E.SAL_ENTRADA


def test_as_colunas_do_movimento_estao_em_ordem():
    assert (E.COL_HORA < E.COL_OS < E.COL_MATERIAL < E.COL_OPERADOR
            < E.COL_CHAPA < E.COL_QTD)
    # o material fica com a maior fatia: e o campo que identifica o servico
    material = E.COL_OPERADOR - E.COL_MATERIAL
    assert material > (E.COL_CHAPA - E.COL_OPERADOR)
    assert material > (E.COL_QTD - E.COL_CHAPA)
