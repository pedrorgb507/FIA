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
        if "SUM(MOVQTD) FROM MOV" in self.ultimo:
            # duas consultas parecidas: o razao soma TUDO; o
            # movimento_depois soma so o que veio DEPOIS do dia, para
            # desandar o saldo num relatorio atrasado
            if "MOVDIA >" in self.ultimo:
                return self.dados.get("depois", [])
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


def test_o_PRECO_e_a_MEDIA_sairam_da_folha():
    """
    "tire pra mim o preco da gravacao e a media da chapa que sai por
    dia" - o operador, 15/09/2026. O papel vai para o cliente, e o que
    ele precisa e do saldo.

    A media CONTINUA sendo calculada: e ela que pinta de vermelho a
    chapa que esta acabando.
    """
    # o que a folha DESENHA, e nao o que o arquivo menciona: as duas
    # frases continuam aparecendo em comentario, contando por que sairam
    fonte = open(E.__file__, encoding="utf-8").read()
    assert '"%s a gravacao' not in fonte
    assert "sai ~%.0f por dia de trabalho" not in fonte
    assert not hasattr(E, "_dinheiro"), "sobrou o formatador de dinheiro"

    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["media"] > 0, "a conta tem de continuar"
    assert dados["chapas"][0]["folga"] is not None


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


def test_a_coluna_AINDA_DURA_saiu_da_folha():
    """
    "pode retirar esse campo 'ainda dura'" - o operador, 14/09/2026. A
    conta continua sendo feita: e ela que pinta de vermelho a chapa que
    esta acabando, e e ela que sai no resumo do terminal. O que saiu foi
    a coluna.
    """
    fonte = open(E.__file__, encoding="utf-8").read()
    assert "AINDA DURA" not in fonte
    assert not hasattr(E, "SAL_DURA")
    # mas a conta segue de pe
    assert E.dias_de_folga(175, 39.0) is not None


def test_as_colunas_do_saldo_NAO_se_atropelam():
    """
    Sao os numeros que alguem vai ler de relance. Escritos um por cima
    do outro, nenhum deles serve.
    """
    assert E.SAL_CHAPA < E.SAL_MEDIDA < E.SAL_ENTRADA
    assert E.SAL_ENTRADA < E.SAL_SAIDA < E.SAL_SALDO
    assert E.SAL_SALDO <= E.DIREITA


def test_as_colunas_do_movimento_estao_em_ordem():
    assert (E.COL_HORA < E.COL_OS < E.COL_MATERIAL < E.COL_OPERADOR
            < E.COL_CHAPA < E.COL_QTD)
    # o material fica com a maior fatia: e o campo que identifica o servico
    material = E.COL_OPERADOR - E.COL_MATERIAL
    assert material > (E.COL_CHAPA - E.COL_OPERADOR)
    assert material > (E.COL_QTD - E.COL_CHAPA)


# ----------------------------------------------------------------------
# A ROTINA DOS DOIS RELATORIOS - 14/09/2026
# ----------------------------------------------------------------------
# "se eu te pedir um relatorio atual, voce gera na hora e salva na PASTA
# DA SOLIDA, com o nome relatorio atual e o horario; se eu nao te pedir,
# segue a rotina: quando der meia noite o dia se encerra e voce salva o
# relatorio dentro da pasta do dia com nome RELATORIO CHAPAS SOLIDA
# (data), assim quando eu chegar cedo eu envio manualmente para eles
# acompanharem" - o operador.

def pasta_de_cliente(monkeypatch, tmp_path):
    """Uma pasta de cliente de mentira, com o mes e o dia dentro."""
    from finart_ctp import config

    base = tmp_path / "SOLIDA Grafica"
    (base / "SETEMBRO" / "14").mkdir(parents=True)
    (base / "SETEMBRO" / "11").mkdir(parents=True)
    monkeypatch.setattr(config, "BASE_ENTRADA", str(base))
    monkeypatch.setattr(E, "PASTA_DO_CLIENTE", {"SOLIDA": "BASE_ENTRADA"})
    return base


def test_a_pasta_do_cliente_e_lida_do_config_NA_HORA(monkeypatch, tmp_path):
    """
    O mapa guarda o NOME da configuracao, e nao o valor - porque o
    config_local so e aplicado no fim do config.py. A primeira versao
    desta linha derivava o valor e devolvia 'X:\\ENTRADA' com o
    BASE_ENTRADA ja valendo 'V:\\SOLIDA Grafica'. O relatorio iria parar
    numa pasta que nao existe, calado.
    """
    from finart_ctp import config

    base = pasta_de_cliente(monkeypatch, tmp_path)
    assert E.pasta_do_cliente("SOLIDA") == str(base)

    monkeypatch.setattr(config, "BASE_ENTRADA", r"Z:\OUTRO LUGAR")
    assert E.pasta_do_cliente("SOLIDA") == r"Z:\OUTRO LUGAR"


def test_cliente_sem_pasta_nao_quebra():
    assert E.pasta_do_cliente("VIVA") is None


def test_o_nome_do_fechamento_e_o_que_o_operador_pediu():
    assert (E.nome_do_fechamento("SOLIDA", datetime.date(2026, 9, 14))
            == "RELATORIO CHAPAS SOLIDA (14-09-2026).pdf")


def test_o_fechamento_vai_DENTRO_da_pasta_daquele_dia(monkeypatch,
                                                      tmp_path):
    base = pasta_de_cliente(monkeypatch, tmp_path)
    caminho = E.caminho_do_fechamento("SOLIDA", datetime.date(2026, 9, 14))
    assert caminho == str(base / "SETEMBRO" / "14"
                          / "RELATORIO CHAPAS SOLIDA (14-09-2026).pdf")


def test_o_relatorio_ATUAL_vai_na_RAIZ_com_data_e_hora(monkeypatch,
                                                       tmp_path):
    """
    A raiz e a mesma o mes inteiro. So com a hora, o pedido de amanha as
    14h escreveria por cima do de hoje as 14h.
    """
    base = pasta_de_cliente(monkeypatch, tmp_path)
    de_verdade = E.levantar
    monkeypatch.setattr(E, "levantar",
                        lambda c, con=None, dia=None:
                        de_verdade(c, con=ConexaoFalsa(banco()), dia=dia))

    quando = datetime.datetime(2026, 9, 14, 20, 41)
    caminho = E.relatorio_agora("SOLIDA", quando=quando)
    assert os.path.basename(caminho) == "RELATORIO ATUAL 14-09 20h41.pdf"
    assert os.path.dirname(caminho) == str(base)
    assert os.path.exists(caminho)


# ----------------------------------------------------------------------
# O SALDO E O DAQUELE DIA
# ----------------------------------------------------------------------

def test_relatorio_ATRASADO_leva_o_saldo_DAQUELE_dia():
    """
    O saldo que a CHA guarda e o de AGORA. Um relatorio de sexta escrito
    na segunda sairia com o saldo de segunda e o movimento de sexta - e
    o cliente receberia um numero que nunca existiu.

    A conta e exata: tira-se do saldo tudo o que se moveu depois.
    """
    # saldo de agora 200; depois do dia em questao entraram 100 e
    # sairam 30, liquido +70. Entao no fim daquele dia havia 130.
    con = ConexaoFalsa(banco(depois=[(98, 70.0)]))
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["saldo"] == 130.0


def test_para_HOJE_o_saldo_fica_como_esta():
    """Nao ha movimento depois de hoje, entao nada muda."""
    con = ConexaoFalsa(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["saldo"] == 200.0


def test_a_consulta_do_saldo_passado_olha_so_o_que_veio_DEPOIS():
    con = ConexaoFalsa(banco())
    E.movimento_depois(161, con, HOJE)
    sql = con.cur.pedidos[-1][0]
    assert "MOVDIA >" in sql and "MOVDIA >=" not in sql


# ----------------------------------------------------------------------
# QUANDO O DIA FECHA
# ----------------------------------------------------------------------

def test_dia_JA_fechado_nao_e_refeito(monkeypatch, tmp_path):
    """
    O papel que o cliente recebeu nao muda depois. Refazer daria dois
    relatorios do mesmo dia com numeros diferentes.
    """
    base = pasta_de_cliente(monkeypatch, tmp_path)
    pronto = (base / "SETEMBRO" / "14"
              / "RELATORIO CHAPAS SOLIDA (14-09-2026).pdf")
    pronto.write_bytes(b"ja estava aqui")

    assert E.ja_fechado("SOLIDA", datetime.date(2026, 9, 14)) is True
    assert E.fechar_o_dia("SOLIDA", datetime.date(2026, 9, 14)) is None
    assert pronto.read_bytes() == b"ja estava aqui"


def test_dia_SEM_movimento_nao_vira_arquivo(monkeypatch, tmp_path):
    """Mandar ao cliente uma folha vazia e pedir para ele parar de olhar."""
    pasta_de_cliente(monkeypatch, tmp_path)
    con = ConexaoFalsa(banco(do_dia=[]))
    assert E.fechar_o_dia("SOLIDA", datetime.date(2026, 9, 11),
                          con=con) is None


def test_o_fechamento_diz_a_hora_DAQUELE_dia(monkeypatch, tmp_path):
    """
    A folha escreve 'atualizado as HH:MM'. Num relatorio de sexta feito
    na segunda, isso nao pode ser a hora de segunda.
    """
    pasta_de_cliente(monkeypatch, tmp_path)
    guardados = []
    monkeypatch.setattr(E, "guardar",
                        lambda d, c, dpi=None: guardados.append(d) or c)

    con = ConexaoFalsa(banco())
    E.fechar_o_dia("SOLIDA", datetime.date(2026, 9, 11), con=con)
    assert guardados[0]["quando"] == datetime.datetime(2026, 9, 11, 23, 59)


def test_HOJE_nunca_entra_na_lista_de_fechar(monkeypatch, tmp_path):
    """O dia so fecha quando acaba."""
    pasta_de_cliente(monkeypatch, tmp_path)
    monkeypatch.setattr(E, "FECHAMENTO_A_PARTIR_DE", "")
    dias = E.dias_por_fechar("SOLIDA", hoje=datetime.date(2026, 9, 16))
    assert datetime.date(2026, 9, 16) not in dias
    assert datetime.date(2026, 9, 15) in dias


def test_a_rotina_nao_fecha_dia_ANTERIOR_a_ela(monkeypatch, tmp_path):
    """
    Sem isto, a rotina nasceria despejando cinco relatorios retroativos
    na pasta do cliente - papeis que ninguem pediu, com data de uma
    semana atras.
    """
    pasta_de_cliente(monkeypatch, tmp_path)
    monkeypatch.setattr(E, "FECHAMENTO_A_PARTIR_DE", "2026-09-14")
    dias = E.dias_por_fechar("SOLIDA", hoje=datetime.date(2026, 9, 16))
    assert dias == [datetime.date(2026, 9, 14), datetime.date(2026, 9, 15)]


def test_os_atrasados_saem_do_mais_VELHO_para_o_mais_novo(monkeypatch,
                                                          tmp_path):
    pasta_de_cliente(monkeypatch, tmp_path)
    monkeypatch.setattr(E, "FECHAMENTO_A_PARTIR_DE", "")
    dias = E.dias_por_fechar("SOLIDA", hoje=datetime.date(2026, 9, 16))
    assert dias == sorted(dias)


def test_data_pedida_a_mao_aceita_as_duas_formas():
    assert E._dia_pedido("11/09", hoje=datetime.date(2026, 9, 14)) == \
        datetime.date(2026, 9, 11)
    assert E._dia_pedido("11/09/2025") == datetime.date(2025, 9, 11)


# ----------------------------------------------------------------------
# O VIGIA NAO PODE LER O PROPRIO RELATORIO COMO ARTE
# ----------------------------------------------------------------------

def test_o_vigia_PULA_o_relatorio_de_estoque():
    """
    O relatorio do dia mora DENTRO da pasta do dia do cliente - a mesma
    de onde a arte vem. Sem esta trava, a FIA o leria como arte na volta
    seguinte, gravaria uma chapa do proprio relatorio e ainda abriria OS
    cobrando por ela.
    """
    from finart_ctp.nomes import e_relatorio

    assert e_relatorio("RELATORIO CHAPAS SOLIDA (14-09-2026).pdf")
    assert e_relatorio("RELATORIO ATUAL 14-09 20h41.pdf")
    assert e_relatorio(os.path.join("V:", "SOLIDA", "SETEMBRO", "14",
                                    "RELATORIO CHAPAS SOLIDA (14-09).pdf"))


def test_o_vigia_NAO_pula_arte_de_verdade():
    """
    Nenhum dos 295 arquivos ja processados comeca com 'RELATORIO' - mas
    uma trava larga demais faria a FIA ignorar servico calada, que e
    pior do que gravar chapa errada.
    """
    from finart_ctp.nomes import e_relatorio

    for nome in ("49825 - RITA - SANTAO URNA.pdf", "GRADE 3385.pdf",
                 "RELATORIOS DA EMPRESA - PANFLETO.pdf",
                 "O.S 1035 - MPGO CARTAZES.cdr"):
        assert not e_relatorio(nome), nome


def test_a_varredura_chama_a_trava_do_relatorio():
    fonte = open(M.__file__, encoding="utf-8").read()
    assert "e_relatorio(arquivo)" in fonte


# ----------------------------------------------------------------------
# O LUGAR DA ROTINA NO LACO
# ----------------------------------------------------------------------

def test_o_laco_fecha_o_dia_junto_com_a_folha(monkeypatch):
    monkeypatch.setattr(M.estoque, "acompanhar", lambda c: None)
    fechados = []
    monkeypatch.setattr(M.estoque, "dias_por_fechar",
                        lambda c: [datetime.date(2026, 9, 15)])
    monkeypatch.setattr(M.estoque, "fechar_o_dia",
                        lambda c, d: fechados.append((c, d)))

    M.rodada_do_estoque(None, agora=1000.0)
    assert fechados == [("SOLIDA", datetime.date(2026, 9, 15))]


def test_falhar_o_fechamento_NAO_derruba_o_laco(monkeypatch):
    monkeypatch.setattr(M.estoque, "acompanhar", lambda c: None)
    recados = []
    monkeypatch.setattr(M, "log", lambda t, **k: recados.append(t))

    def explodir(cliente):
        raise RuntimeError("o V: caiu")

    monkeypatch.setattr(M.estoque, "dias_por_fechar", explodir)
    assert M.rodada_do_estoque(None, agora=1000.0) == 1000.0
    assert any("fechar o dia" in t for t in recados)


# ----------------------------------------------------------------------
# A CONFERENCIA COM O RELATORIO DO PROPRIO GEREMPRE - 14/09/2026
# ----------------------------------------------------------------------
# "o total de estoque sempre tem que bater exatamente com o relatorio do
# gerempre, preciso que vc sempre faca essa comparacao" - o operador.
#
# Sao dois caminhos independentes para o mesmo numero:
#
#   a folha    le CHA.CHAQTD, pelo CODIGO da chapa
#   o GEREMPRE soma os movimentos e casa a chapa pelo NOME
#
# Conferido contra producao em 14/09/2026, quatro dias diferentes
# (14/09, 11/09, 10/09 e 08/09): os oito numeros bateram.


class CursorComRelatorio(CursorFalso):
    """Um cursor que tambem sabe responder o SP_ESTOQUE do GEREMPRE."""

    def __init__(self, dados, quebrados=()):
        CursorFalso.__init__(self, dados)
        self.quebrados = quebrados
        self.chamados = []

    def execute(self, sql, parametros=None):
        for nome in E.RELATORIOS_DO_GEREMPRE:
            if "FROM %s(" % nome in sql:
                self.chamados.append(nome)
                if nome in self.quebrados:
                    # e assim que o Firebird recusa: ele nem prepara
                    raise RuntimeError(
                        "procedure %s does not return any values" % nome)
        CursorFalso.execute(self, sql, parametros)

    def fetchall(self):
        for nome in E.RELATORIOS_DO_GEREMPRE:
            if "FROM %s(" % nome in (self.ultimo or ""):
                return self.dados.get("relatorio", [])
        return CursorFalso.fetchall(self)


def com_relatorio(dados=None, quebrados=(), saldos=None):
    """Uma conexao de mentira com o relatorio do GEREMPRE dentro."""
    dados = dados or banco()
    saldos = {"SOLIDA FT4": 200.0} if saldos is None else saldos
    # o procedimento devolve (cliente, chapa, quantidade, data, obs, usuario)
    linhas = [("SOLIDA", "SOLIDA FT4", -4.0, HOJE, "", "JOAOZIMAR"),
              (None, "SALDO ANTERIOR SOLIDA FT4", 104.0, None, None, None),
              (None, "TOTAL ENTRADA SOLIDA FT4", 100.0, None, None, None),
              (None, "TOTAL SAIDA SOLIDA FT4", 4.0, None, None, None)]
    for nome, valor in saldos.items():
        linhas.append((None, "ESTOQUE ATUAL " + nome, valor,
                       None, None, None))
    dados["relatorio"] = linhas

    con = ConexaoFalsa(dados)
    con.cur = CursorComRelatorio(dados, quebrados)
    return con


def test_o_relatorio_do_gerempre_e_lido_chapa_a_chapa():
    con = com_relatorio()
    lido = E.estoque_do_gerempre(161, con, HOJE)
    assert lido == {"SOLIDA FT4": 200.0}


def test_so_a_linha_do_ESTOQUE_ATUAL_conta():
    """
    O procedimento devolve tambem SALDO ANTERIOR, TOTAL ENTRADA e TOTAL
    SAIDA, e todos com a palavra 'SOLIDA FT4' no fim. Pegar a linha
    errada poria 104 no lugar de 200.
    """
    con = com_relatorio()
    lido = E.estoque_do_gerempre(161, con, HOJE)
    assert list(lido.values()) == [200.0]


def test_o_relatorio_e_pedido_para_UM_dia_so():
    """
    Com datai = dataf = o dia, o procedimento devolve o saldo no FIM
    daquele dia - e a lista sai trinta vezes menor do que pedindo o mes.
    Conferido: 28 linhas contra 171, o mesmo numero no fim.
    """
    con = com_relatorio()
    E.estoque_do_gerempre(161, con, HOJE)
    sql, parametros = con.cur.pedidos[-1]
    assert parametros == (161, HOJE, HOJE)


def test_SP_ESTOQUE_quebrado_cai_no_SP_ESTOQUE2():
    """
    Em 14/09/2026 o SP_ESTOQUE deste banco estava ILEGIVEL - 'page 73787
    is of wrong type' ao ler os parametros dele - e o SP_ESTOQUE2, de
    codigo identico, respondia. O defeito e do banco e pode ser
    consertado, entao tentam-se os dois, nessa ordem.
    """
    con = com_relatorio(quebrados=("SP_ESTOQUE",))
    assert E.estoque_do_gerempre(161, con, HOJE) == {"SOLIDA FT4": 200.0}
    assert con.cur.chamados == ["SP_ESTOQUE", "SP_ESTOQUE2"]


def test_os_dois_quebrados_devolvem_NONE_e_nao_zero():
    """
    None e 'nao consegui conferir'; zero seria 'o estoque acabou'. A
    folha precisa poder dizer a diferenca - dar por conferido o que nao
    foi e o unico jeito de esta conferencia piorar as coisas.
    """
    con = com_relatorio(quebrados=("SP_ESTOQUE", "SP_ESTOQUE2"))
    assert E.estoque_do_gerempre(161, con, HOJE) is None


def test_relatorio_vazio_tambem_e_NAO_CONSEGUI():
    con = com_relatorio(saldos={})
    assert E.estoque_do_gerempre(161, con, HOJE) is None


# ----------------------------------------------------------------------
# O QUE A FOLHA FAZ COM A CONFERENCIA
# ----------------------------------------------------------------------

def test_quando_bate_a_folha_diz_que_conferiu():
    con = com_relatorio(saldos={"SOLIDA FT4": 200.0})
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["conferi_o_gerempre"] is True
    assert dados["chapas"][0]["gerempre"] == 200.0
    assert dados["chapas"][0]["bate_com_o_gerempre"] is True


def test_quando_NAO_bate_a_folha_marca_a_chapa():
    """
    Sao caminhos independentes. Diferiram, um dos dois esta errado - e
    a folha nao pode escolher qual, so avisar.
    """
    con = com_relatorio(saldos={"SOLIDA FT4": 173.0})
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["bate_com_o_gerempre"] is False
    assert E.folhas(dados, dpi=72)          # e desenha assim mesmo


def test_chapa_que_o_relatorio_do_gerempre_NAO_TRAZ_e_divergencia():
    """
    O GEREMPRE casa a chapa pelo NOME (movnch), e a folha pelo CODIGO.
    Chapa renomeada some do relatorio dele e continua na folha - que e
    exatamente um dos defeitos que esta conferencia existe para pegar.
    """
    con = com_relatorio(saldos={"OUTRO NOME QUALQUER": 200.0})
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["gerempre"] is None
    assert dados["chapas"][0]["bate_com_o_gerempre"] is False


def test_sem_conferencia_a_folha_DIZ_que_nao_conferiu():
    """
    O pior desfecho possivel seria a folha sair igual a de sempre, sem
    a conferencia e sem ninguem notar.
    """
    con = com_relatorio(quebrados=("SP_ESTOQUE", "SP_ESTOQUE2"))
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["conferi_o_gerempre"] is False
    assert dados["chapas"][0]["bate_com_o_gerempre"] is None
    assert E.folhas(dados, dpi=72)


def test_a_coluna_do_gerempre_esta_na_folha():
    fonte = open(E.__file__, encoding="utf-8").read()
    assert "NO GEREMPRE" in fonte
    assert E.SAL_SALDO < E.SAL_GEREMPRE <= E.DIREITA


def test_o_relatorio_do_gerempre_nao_derruba_o_levantamento():
    """
    Ele e uma conferencia. Falhando, a folha sai com o numero da casa e
    a conferencia em branco - o estoque nao pode deixar de ser mostrado
    porque um procedimento do banco parou.
    """
    class Explode(CursorComRelatorio):
        def execute(self, sql, parametros=None):
            if "SP_ESTOQUE" in sql:
                raise RuntimeError("o banco caiu no meio")
            CursorFalso.execute(self, sql, parametros)

    con = ConexaoFalsa(banco())
    con.cur = Explode(banco())
    dados = E.levantar("SOLIDA", con=con, dia=HOJE)
    assert dados["chapas"][0]["saldo"] == 200.0
    assert dados["conferi_o_gerempre"] is False
