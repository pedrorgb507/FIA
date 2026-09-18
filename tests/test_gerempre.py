# -*- coding: utf-8 -*-
"""
A OS no GEREMPRE.

Escrever aqui NAO e anotar: o gatilho TR_OS_BEFO lanca movimento de
estoque, e o gatilho da MOV soma esse movimento no saldo da chapa. Erro
nesta parte nao aparece na tela de ninguem - aparece no inventario.

Dois defeitos foram encontrados abrindo OS de verdade na copia de teste,
e os dois estragavam CALADOS. Os testes abaixo existem para eles nao
voltarem.
"""

import datetime
import sys

import pytest

from finart_ctp import gerempre


class CursorFalso(object):
    """Um cursor que anota o que foi pedido, sem banco nenhum."""

    def __init__(self):
        self.comandos = []
        # o que o SELECT OSESP1..4 devolve. None = a OS nao existe.
        self.vagas = (0, 0, 0, 0)

    def execute(self, sql, parametros=None):
        self.comandos.append((sql, parametros))

    def fetchone(self):
        ultimo = self.comandos[-1][0]
        if "GEN_ID" in ultimo:
            return (19150,)
        if "FROM CLI" in ultimo:
            return ("SOLIDA GRAFICA (SOLIDA GRAFICA EDITORA LTDA)",
                    "GUSTAVO / EDUARDO", "(62) 3280-3808")
        if "OSESP1" in ultimo:
            return self.vagas
        return None

    def fetchall(self):
        return []


class ConexaoFalsa(object):
    def __init__(self):
        self.cur = CursorFalso()
        self.gravou = False
        self.voltou = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.gravou = True

    def rollback(self):
        self.voltou = True

    def close(self):
        pass


def campos_gravados(con):
    """{campo: valor} do INSERT que foi montado."""
    for sql, parametros in con.cur.comandos:
        if sql.startswith("INSERT INTO OS"):
            nomes = sql.split("(", 1)[1].split(")", 1)[0].split(", ")
            return dict(zip(nomes, parametros))
    return {}


SERVICO = {"titulo": "49713 - Lucas Calil - panfleto Itapuranga",
           "cliente": "SOLIDA", "chapa": (510, 400), "chapas": 4}


# ----------------------------------------------------------------------
# Quantas chapas o trabalho gasta
# ----------------------------------------------------------------------

def test_quadricromia_gasta_quatro_chapas():
    """O preco e por chapa de metal, e CMYK sao quatro."""
    assert gerempre.quantas_chapas([set("CMYK")]) == 4


def test_arte_de_uma_cor_gasta_uma():
    assert gerempre.quantas_chapas([{"GRAY"}]) == 1


def test_frente_e_verso_somam():
    assert gerempre.quantas_chapas([set("CMYK"), set("CMYK")]) == 8
    assert gerempre.quantas_chapas([set("CMYK"), {"GRAY"}]) == 5


# ----------------------------------------------------------------------
# A vaga: preco e tipo de chapa
# ----------------------------------------------------------------------

def test_cliente_que_traz_a_chapa_marca_rbchapa():
    """SOLIDA traz a chapa: cobramos so a gravacao, R$ 9,00."""
    vaga = gerempre.montar_vaga(SERVICO)
    assert vaga["OSESP"] == 98
    assert vaga["OSUNIT"] == 9.00
    assert vaga["OSVLU"] == 36.00
    assert (vaga["RBCHAPA"], vaga["RBCHAPAPRO"]) == (1, 0)


def test_chapa_propria_marca_o_outro_interruptor():
    """VOPRIX usa chapa da Finart: R$ 20,00, chapa mais gravacao."""
    vaga = gerempre.montar_vaga(dict(SERVICO, cliente="VOPRIX"))
    assert vaga["OSESP"] == 12
    assert vaga["OSUNIT"] == 20.00
    assert (vaga["RBCHAPA"], vaga["RBCHAPAPRO"]) == (0, 1)


def test_o_formato_grande_tem_outro_preco():
    vaga = gerempre.montar_vaga(dict(SERVICO, chapa=(775, 635)))
    assert vaga["OSESP"] == 103
    assert vaga["OSUNIT"] == 13.00
    assert vaga["OSMON"] == "F2"


def test_chapa_que_nao_conhecemos_nao_vira_vaga():
    """
    A VOPRIX nao tem chapa grande cadastrada em 2026. Chutar o preco e
    faturar errado - melhor devolver nada e virar pendencia.
    """
    assert gerempre.montar_vaga(dict(SERVICO, cliente="VOPRIX",
                                     chapa=(775, 635))) is None


def test_a_medida_pode_vir_em_qualquer_ordem():
    """400x510 e 510x400 sao a mesma chapa."""
    assert (gerempre.montar_vaga(dict(SERVICO, chapa=(400, 510)))["OSESP"]
            == gerempre.montar_vaga(dict(SERVICO, chapa=(510, 400)))["OSESP"])


# ----------------------------------------------------------------------
# Os dois defeitos que estragaram estoque na copia de teste
# ----------------------------------------------------------------------

def test_todas_as_vagas_vao_zeradas_e_nao_nulas():
    """
    O gatilho faz  total = osvlu1 + osvlu2 + osvlu3 + osvlu4.

    Numa OS de um servico so, as tres vagas vazias iam nulas e o TOTAL DA
    OS saia nulo - a OS existia sem valor nenhum.
    """
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO], con=con)
    campos = campos_gravados(con)
    for i in (1, 2, 3, 4):
        assert campos["OSVLU%d" % i] is not None, "vaga %d nula" % i
    assert campos["OSVLU1"] == 36.00
    assert campos["OSVLU2"] == campos["OSVLU3"] == campos["OSVLU4"] == 0


def test_as_cores_do_verso_vao_zeradas():
    """
    O gatilho faz  movqtd = oslan<n> * (oscor<n> + oscor<n><n>).

    Sem preencher oscor<n><n> - as cores do VERSO - a quantidade do
    movimento saia nula, e o gatilho da MOV faz 'chaqtd = chaqtd +
    movqtd'. O ESTOQUE DA CHAPA virava nulo. Aconteceu de verdade com as
    chapas 98 e 103 na copia de teste.
    """
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO], con=con)
    campos = campos_gravados(con)
    for i in (1, 2, 3, 4):
        assert campos["OSCOR%d%d" % (i, i)] == 0, "verso da vaga %d" % i
    assert campos["OSCOR1"] == 1
    # a conta do gatilho, feita aqui: 4 chapas x (1 frente + 0 verso)
    assert campos["OSLAN1"] * (campos["OSCOR1"] + campos["OSCOR11"]) == 4


def test_os_sete_campos_obrigatorios_vao_preenchidos():
    """
    O banco recusa a gravacao inteira se faltar um deles. Tres sao
    vendedor, operador e conferente - que ninguem preenche, mas que nao
    aceitam nulo.
    """
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO], con=con)
    campos = campos_gravados(con)
    for obrigatorio in ("OSCOD", "OSSIT", "OSTIPO", "OSCLI", "OSCVEN",
                        "OSCOPER", "OSCCONF"):
        assert campos.get(obrigatorio) is not None, obrigatorio


# ----------------------------------------------------------------------
# PENDENTE ate as quatro vagas fecharem
# ----------------------------------------------------------------------
# OSSIT: 0 e PENDENTE, 1 e ENTREGUE, 2 e cancelada.
#
# A FIA nascia marcando 1 - entregue - na primeira vaga. O codigo tinha
# escolhido 1 porque era o valor de 19.078 das 19.122 OS, so que elas
# estao em 1 porque JA FORAM ENTREGUES: as 42 em 0, lidas em 10/09/2026,
# eram justamente as dos ultimos dez dias, ainda abertas. Inferencia de
# sobrevivente.
#
# A prova esta na OS 19603, aberta pela FIA em 09/09/2026: saiu como
# ENTREGUE com TRES vagas.
#
# A regra do operador, dita em 10/09/2026: so fecha com as QUATRO. Nao
# fechando, fica pendente e uma pessoa fecha a mao quando precisar.
# Errar deixando pendente custa uma conferida; errar dando por entregue
# poe no faturamento um servico que ninguem entregou.

def test_os_nova_nasce_pendente():
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO], con=con)
    campos = campos_gravados(con)
    assert campos["OSSIT"] == gerempre.PENDENTE
    assert campos["OSSIT"] == 0, "1 e ENTREGUE, e nada foi entregue ainda"


def test_os_com_as_quatro_vagas_tambem_nasce_pendente():
    """
    A entrega e um passo DEPOIS, e nao um efeito de estar cheia.

    O operador pediu a ordem: imprimir o verso do ultimo arquivo, ai
    marcar entregue e imprimir o protocolo. Marcar na hora de gravar
    inverteria isso.
    """
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO] * 4, con=con)
    assert campos_gravados(con)["OSSIT"] == gerempre.PENDENTE


def test_a_vaga_livre_e_procurada_entre_as_pendentes():
    """
    Se continuasse procurando OSSIT = 1, a FIA nunca acharia a propria OS
    de hoje - ela agora nasce em 0 - e abriria uma OS NOVA por arquivo,
    faturando quatro vezes o que cabia numa.
    """
    cur = CursorFalso()
    gerempre.os_com_vaga_livre(cur, "SOLIDA")
    sql = " ".join(c[0] for c in cur.comandos)
    assert "OSSIT = 0" in sql or "OSSIT=0" in sql
    assert "OSSIT = 1" not in sql


def test_entregar_recusa_os_incompleta():
    """Tres vagas nao e entrega. Foi o que aconteceu com a OS 19603."""
    con = ConexaoFalsa()
    con.cur.vagas = (98, 98, 98, 0)          # a quarta vazia
    with pytest.raises(ValueError):
        gerempre.entregar_os(19603, con=con)
    assert not con.gravou, "nao pode ter gravado nada"


def test_entregar_marca_entregue_com_as_quatro_cheias():
    con = ConexaoFalsa()
    con.cur.vagas = (98, 98, 103, 103)
    gerempre.entregar_os(19605, con=con)
    gravou = [c for c in con.cur.comandos if "UPDATE OS" in c[0]]
    assert gravou, "tinha de gravar"
    sql, params = gravou[-1]
    assert "OSSIT" in sql
    assert gerempre.ENTREGUE in params and 19605 in params
    assert con.gravou


def test_entregar_nao_encosta_em_ostipo():
    """
    OSTIPO 4 e refacao, e o gatilho devolve estoque. Mexer nele aqui
    apagaria a baixa das quatro chapas.
    """
    con = ConexaoFalsa()
    con.cur.vagas = (98, 98, 103, 103)
    gerempre.entregar_os(19605, con=con)
    sql = " ".join(c[0] for c in con.cur.comandos if "UPDATE OS" in c[0])
    assert "OSTIPO" not in sql


def test_entregar_os_que_nao_existe_nao_grava():
    con = ConexaoFalsa()
    con.cur.vagas = None                     # a OS nao existe
    with pytest.raises(ValueError):
        gerempre.entregar_os(99999, con=con)
    assert not con.gravou


# ----------------------------------------------------------------------
# A OS inteira
# ----------------------------------------------------------------------

def test_a_os_leva_o_cliente_e_o_estoque_certos():
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO], con=con)
    campos = campos_gravados(con)
    assert campos["OSCLI"] == 161
    # OSECL diz de QUAL ESTOQUE sai a chapa; sem isso a baixa vai para o
    # lugar errado
    assert campos["OSECL"] == 161
    assert campos["OSRESP"] == "FINART (FIA)"


def test_quatro_servicos_cabem_numa_os():
    con = ConexaoFalsa()
    gerempre.abrir_os([SERVICO] * 4, con=con)
    campos = campos_gravados(con)
    assert all(campos["OSTIT%d" % i] for i in (1, 2, 3, 4))
    assert sum(campos["OSVLU%d" % i] for i in (1, 2, 3, 4)) == 144.00


def test_o_quinto_servico_nao_cabe():
    with pytest.raises(ValueError, match="vagas"):
        gerempre.abrir_os([SERVICO] * 5, con=ConexaoFalsa())


def test_uma_os_e_de_um_cliente_so():
    """Misturar clientes faturaria um no outro."""
    with pytest.raises(ValueError, match="cliente"):
        gerempre.abrir_os([SERVICO, dict(SERVICO, cliente="VOPRIX")],
                          con=ConexaoFalsa())


def test_cliente_sem_codigo_no_gerempre_nao_abre_os():
    with pytest.raises(ValueError, match="GEREMPRE"):
        gerempre.abrir_os([dict(SERVICO, cliente="ALGUEM")],
                          con=ConexaoFalsa())


def test_chapa_desconhecida_nao_abre_os_com_preco_chutado():
    with pytest.raises(ValueError, match="chapa"):
        gerempre.abrir_os([dict(SERVICO, chapa=(999, 888))],
                          con=ConexaoFalsa())


def test_se_der_erro_no_meio_nada_e_gravado():
    """
    Meia OS lancaria estoque pela metade. Ou entra inteira, ou nao entra.
    """
    class Explode(ConexaoFalsa):
        def commit(self):
            raise RuntimeError("caiu a rede no meio")

    con = Explode()
    with pytest.raises(RuntimeError):
        gerempre.abrir_os([SERVICO], con=con)
    assert con.voltou, "faltou desfazer a transacao"


def test_a_data_e_a_hora_entram_separadas():
    con = ConexaoFalsa()
    quando = datetime.datetime(2026, 9, 8, 20, 38, 40)
    gerempre.abrir_os([SERVICO], quando=quando, con=con)
    campos = campos_gravados(con)
    assert campos["OSENTD"] == datetime.date(2026, 9, 8)
    assert campos["OSTIME"] == datetime.time(20, 38, 40)


# ----------------------------------------------------------------------
# A VAGA DE QUALQUER OPERADOR, e a conferencia que vem depois
# ----------------------------------------------------------------------
# Decisao do operador em 11/09/2026: a FIA passa a completar a OS de
# QUALQUER um que tenha vaga aberta para o cliente naquele dia.
#
# O que isso desfez, e os dois motivos sao MEDIDOS e nao opiniao:
#
#   o filtro 'OSUSR_ALT = 32' nao queria dizer "OS da FIA". OSUSR_ALT e o
#   usuario da ALTERACAO - das 8 OS pendentes que ela tinha aberto em
#   producao, 3 ja estavam invisiveis porque um operador as salvara;
#
#   o medo do nulo era suposicao: zero nulos em 19.627 OS.
#
# O que ficou de risco, e que nao da para evitar: quem esta com a OS na
# tela salva por cima. Por isso a vaga completada e anotada e relida.

def test_a_vaga_livre_nao_filtra_mais_por_dono():
    """
    'OSUSR_ALT = 32' fazia a FIA perder as proprias OS assim que um
    operador as salvasse - e abrir outra para o mesmo cliente no mesmo
    dia, com chapa a mais e faturamento dobrado.
    """
    cur = CursorFalso()
    gerempre.os_com_vaga_livre(cur, "SOLIDA")
    sql = " ".join(c[0] for c in cur.comandos)
    assert "OSUSR_ALT" not in sql, "voltou a filtrar por dono"
    assert "OSSIT = 0" in sql, "e continua so nas pendentes"
    assert "OSTIPO = 0" in sql, "refacao e cancelada continuam de fora"


def test_completar_anota_a_vaga_para_conferir(tmp_path, monkeypatch):
    """Sem o caderninho nao ha como perceber que a vaga sumiu."""
    monkeypatch.setattr(gerempre, "PASTA_CONTROLE", str(tmp_path))
    con = ConexaoFalsa()
    con.cur.vagas = (98, 0, 0, 0)            # so a vaga 1 esta cheia
    vaga = gerempre.completar_os(19650, SERVICO, con=con)

    anotadas = gerempre._ler_completadas()
    assert len(anotadas) == 1
    assert anotadas[0]["os"] == 19650
    assert anotadas[0]["vaga"] == vaga == 2
    assert anotadas[0]["titulo"] == SERVICO["titulo"]
    assert anotadas[0]["cliente"] == "SOLIDA"


def test_a_conferencia_espera_antes_de_reler(tmp_path, monkeypatch):
    """
    Reler na hora nao provaria nada: o operador ainda nem salvou. E ir ao
    banco a cada volta do laco, para nada, seria so barulho.
    """
    monkeypatch.setattr(gerempre, "PASTA_CONTROLE", str(tmp_path))

    def nao_me_chame():
        raise AssertionError("foi ao banco antes da hora")
    monkeypatch.setattr(gerempre, "conectar", nao_me_chame)

    con = ConexaoFalsa()
    con.cur.vagas = (98, 0, 0, 0)
    gerempre.completar_os(19650, SERVICO, con=con)
    assert gerempre.conferir_completadas() == (0, 0)


def test_a_vaga_que_sobreviveu_sai_da_lista_no_fim(tmp_path, monkeypatch):
    monkeypatch.setattr(gerempre, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(gerempre, "ja_esta_em_os",
                        lambda cur, t, c=None, q=None, d=None: 19650)

    con = ConexaoFalsa()
    con.cur.vagas = (98, 0, 0, 0)
    gerempre.completar_os(19650, SERVICO, con=con)

    depois = datetime.datetime.now() + datetime.timedelta(
        minutes=gerempre.ESPERA_CONFERIR_MIN + 1)
    conferidas, sumidas = gerempre.conferir_completadas(agora=depois, con=con)
    assert (conferidas, sumidas) == (1, 0)
    assert len(gerempre._ler_completadas()) == 1, "ainda dentro da validade"

    # passada a validade, assenta e sai da lista
    muito_depois = datetime.datetime.now() + datetime.timedelta(
        hours=gerempre.VALIDADE_CONFERIR_H + 1)
    gerempre.conferir_completadas(agora=muito_depois, con=con)
    assert gerempre._ler_completadas() == []


def test_a_vaga_que_SUMIU_vira_pendencia(tmp_path, monkeypatch):
    """
    O caso que isto existe para pegar: a OS era de outro operador, ele
    estava com ela aberta, salvou o que estava vendo, e o TR_OS_BEFO
    refez os movimentos sem a vaga da FIA. O servico ja saiu - alguem
    precisa cobra-lo a mao.
    """
    monkeypatch.setattr(gerempre, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(gerempre, "ja_esta_em_os",
                        lambda cur, t, c=None, q=None, d=None: None)

    recados = []
    monkeypatch.setattr(gerempre, "anotar_pendencia",
                        lambda arq, motivo, cliente=None:
                            recados.append((arq, motivo, cliente)))

    con = ConexaoFalsa()
    con.cur.vagas = (98, 0, 0, 0)
    gerempre.completar_os(19650, SERVICO, con=con)

    depois = datetime.datetime.now() + datetime.timedelta(
        minutes=gerempre.ESPERA_CONFERIR_MIN + 1)
    conferidas, sumidas = gerempre.conferir_completadas(agora=depois, con=con)

    assert (conferidas, sumidas) == (1, 1)
    assert len(recados) == 1
    arquivo, motivo, cliente = recados[0]
    assert arquivo == SERVICO["titulo"]
    assert "19650" in motivo and "A MAO" in motivo
    assert cliente == "SOLIDA"
    assert gerempre._ler_completadas() == [], "sumida nao fica se repetindo"


def test_a_conferencia_nao_escreve_no_banco(tmp_path, monkeypatch):
    """Ela e uma releitura. Escrever aqui mexeria em estoque."""
    monkeypatch.setattr(gerempre, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(gerempre, "ja_esta_em_os",
                        lambda cur, t, c=None, q=None, d=None: None)
    monkeypatch.setattr(gerempre, "anotar_pendencia",
                        lambda *a, **k: None)

    con = ConexaoFalsa()
    con.cur.vagas = (98, 0, 0, 0)
    gerempre.completar_os(19650, SERVICO, con=con)
    antes = len(con.cur.comandos)

    depois = datetime.datetime.now() + datetime.timedelta(
        minutes=gerempre.ESPERA_CONFERIR_MIN + 1)
    gerempre.conferir_completadas(agora=depois, con=con)

    novos = [sql for sql, _ in con.cur.comandos[antes:]]
    for sql in novos:
        for proibido in ("UPDATE", "INSERT", "DELETE"):
            assert proibido not in sql.upper(), sql


# ----------------------------------------------------------------------
# LIGAR PELO IP - 14/09/2026
# ----------------------------------------------------------------------
# Ligar pelo NOME do servidor custava 84,203 s, toda vez. Pelo IP,
# 0,006 s. Nao e o DNS (o nome resolve em 0,017 s) nem a rede (a porta
# atende em 0,001 s): e o cliente Firebird tentando outro caminho antes
# de cair no TCP. A FIA liga varias vezes por servico, e isso aparecia
# no log como 86 segundos entre a chapa pronta e a OS aberta.
#
# O conserto nao fixa o IP na configuracao - o nome fica escrito, e a
# troca acontece na hora de ligar.

CAMINHO_DO_BANCO = r"C:\NeoGerempre\bdados\neobdados.fdb"


def resolvedor(monkeypatch, tabela):
    """Troca a resolucao de nome do Windows por uma tabela de mentira."""
    import socket

    def procurar(nome):
        if nome not in tabela:
            raise socket.gaierror("nao resolve: %s" % nome)
        return tabela[nome]

    monkeypatch.setattr(socket, "gethostbyname", procurar)


def test_o_nome_do_servidor_vira_IP(monkeypatch):
    resolvedor(monkeypatch, {"ARTE-JUNIOR": "192.168.15.27"})
    assert (gerempre._dsn_pelo_ip("ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
            == "192.168.15.27/3050:" + CAMINHO_DO_BANCO)


def test_a_LETRA_DE_UNIDADE_nao_e_nome_de_servidor(monkeypatch):
    r"""
    'C:\GEREMPRE FIA TESTE\...' e caminho local. Tratar o 'C' como
    servidor faria a copia de teste deixar de abrir.
    """
    resolvedor(monkeypatch, {"C": "1.2.3.4"})
    local = r"C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb"
    assert gerempre._dsn_pelo_ip(local) == local


def test_quem_ja_e_numero_fica_como_esta(monkeypatch):
    resolvedor(monkeypatch, {})
    dsn = r"127.0.0.1/3050:C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb"
    assert gerempre._dsn_pelo_ip(dsn) == dsn


def test_nome_que_NAO_resolve_devolve_o_DSN_intacto(monkeypatch):
    """Sem atalho, mas sem quebrar: o Firebird que tente do jeito dele."""
    resolvedor(monkeypatch, {})
    dsn = "SERVIDOR-NOVO/3050:" + CAMINHO_DO_BANCO
    assert gerempre._dsn_pelo_ip(dsn) == dsn


def _fdb_falso(monkeypatch, tentados, cai=lambda dsn: False):
    class FdbFalso(object):
        @staticmethod
        def load_api(_):
            pass

        @staticmethod
        def connect(dsn=None, **k):
            tentados.append(dsn)
            if cai(dsn):
                raise IOError("recusou")
            return "ligacao"

    monkeypatch.setitem(sys.modules, "fdb", FdbFalso)


def test_falhando_pelo_IP_NAO_se_tenta_o_nome(monkeypatch, com_conectar):
    """
    ATE 18/09/2026 SE TENTAVA, e era desperdicio.

    O teste antigo dizia "se o IP mudar de dono, a FIA ainda tenta pelo
    nome". Nao muda: o IP VEM de resolver esse mesmo nome, microssegundos
    antes. Falhando o TCP para ele, o nome resolve para o MESMO IPv4 - e
    mais dois IPv6 mortos - e leva 84 segundos para chegar ao mesmo erro.

    Medido nesta casa: IP 0,184 s, nome 63,341 s. A mensagem "tentando
    pelo nome, o que demora" saiu 324 vezes em dois dias, e nenhuma
    delas o nome salvou uma ligacao que o IP tinha perdido.
    """
    resolvedor(monkeypatch, {"ARTE-JUNIOR": "192.168.15.27"})
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN",
                        "ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
    monkeypatch.setattr(gerempre, "log", lambda *a, **k: None)
    gerempre._queda.update({"desde": None, "quantas": 0})

    tentados = []
    _fdb_falso(monkeypatch, tentados, cai=lambda dsn: True)

    with pytest.raises(gerempre.SemLigacao):
        gerempre.conectar()
    assert tentados == ["192.168.15.27/3050:" + CAMINHO_DO_BANCO], tentados


def test_sem_resolucao_o_nome_E_o_caminho(monkeypatch, com_conectar):
    """
    Nao resolvendo o nome, nao ha atalho - e ai o nome e a unica porta
    que existe. Vale esperar por ela.
    """
    resolvedor(monkeypatch, {})
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN",
                        "ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
    monkeypatch.setattr(gerempre, "log", lambda *a, **k: None)
    gerempre._queda.update({"desde": None, "quantas": 0})

    tentados = []
    _fdb_falso(monkeypatch, tentados)
    assert gerempre.conectar() == "ligacao"
    assert tentados == ["ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO]


def test_a_queda_e_avisada_UMA_vez_e_a_volta_tambem(monkeypatch,
                                                    com_conectar):
    """
    A mensagem antiga saiu uma por tentativa - 324 linhas iguais em dois
    dias. Aviso repetido vira aviso que ninguem le, e o operador passa a
    ver o log como ruido em vez de como noticia.
    """
    resolvedor(monkeypatch, {"ARTE-JUNIOR": "192.168.15.27"})
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN",
                        "ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
    gerempre._queda.update({"desde": None, "quantas": 0})
    ditos = []
    monkeypatch.setattr(gerempre, "log",
                        lambda t, **k: ditos.append(t))

    fora = {"sim": True}
    _fdb_falso(monkeypatch, [], cai=lambda dsn: fora["sim"])

    for _ in range(5):                       # cinco voltas do laco
        with pytest.raises(gerempre.SemLigacao):
            gerempre.conectar()
    assert len(ditos) == 1, ditos
    assert "nao esta atendendo" in ditos[0]

    fora["sim"] = False
    gerempre.conectar()
    assert len(ditos) == 2
    assert "voltou" in ditos[1] and "5 tentativa(s)" in ditos[1]


def test_voltando_sem_ter_caido_nao_se_anuncia_nada(monkeypatch,
                                                    com_conectar):
    """Ligacao que sempre funcionou nao merece linha nenhuma no log."""
    resolvedor(monkeypatch, {"ARTE-JUNIOR": "192.168.15.27"})
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN",
                        "ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
    gerempre._queda.update({"desde": None, "quantas": 0})
    ditos = []
    monkeypatch.setattr(gerempre, "log", lambda t, **k: ditos.append(t))
    _fdb_falso(monkeypatch, [])
    gerempre.conectar()
    gerempre.conectar()
    assert ditos == []


def test_falhando_dos_dois_jeitos_e_SemLigacao(monkeypatch, com_conectar):
    resolvedor(monkeypatch, {"ARTE-JUNIOR": "192.168.15.27"})
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN",
                        "ARTE-JUNIOR/3050:" + CAMINHO_DO_BANCO)
    monkeypatch.setattr(gerempre, "log", lambda *a, **k: None)

    class FdbFalso(object):
        @staticmethod
        def load_api(_):
            pass

        @staticmethod
        def connect(dsn=None, **k):
            raise IOError("o servidor esta fora do ar")

    monkeypatch.setitem(sys.modules, "fdb", FdbFalso)
    with pytest.raises(gerempre.SemLigacao) as caiu:
        gerempre.conectar()
    assert "fora do ar" in str(caiu.value)


def test_um_DSN_local_so_e_tentado_UMA_vez(monkeypatch, com_conectar):
    """Sem nome a trocar, nao ha duas tentativas iguais."""
    local = r"C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb"
    monkeypatch.setattr(gerempre, "GEREMPRE_DSN", local)
    tentados = []

    class FdbFalso(object):
        @staticmethod
        def load_api(_):
            pass

        @staticmethod
        def connect(dsn=None, **k):
            tentados.append(dsn)
            raise IOError("nao")

    monkeypatch.setitem(sys.modules, "fdb", FdbFalso)
    with pytest.raises(gerempre.SemLigacao):
        gerempre.conectar()
    assert tentados == [local]


# ----------------------------------------------------------------------
# DOIS SERVICOS QUE VIRAM UM SO NO CORTE DAS 50 LETRAS - 14/09/2026
# ----------------------------------------------------------------------
# A VOPRIX mandou dois envelopes no mesmo dia:
#
#   Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Colegio_Voolivre
#   Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Nelore_Bemach
#
# As 50 primeiras letras sao IGUAIS. A FIA lancou o Voolivre as 19:20 e,
# as 19:23, olhou o Nelore, casou com o titulo cortado do outro e disse
# "ja esta lancado, nao cobrei de novo". A gravacao do Nelore saiu sem
# cobranca, e o operador teve de refazer as duas OS a mao.
#
# "tem que ler o nome completo do arquivo, para saber se realmente e o
# mesmo... a melhor opcao e pegar quando os nomes forem iguais, pegar os
# ultimos nomes" - o operador, na mesma noite.

VOOLIVRE = ("ENVELOPE_SACO_23X31,5_4_0_RAPHAEL _BRANDAO_MACHADO_"
            "COLEGIO_VOOLIVRE")
NELORE = ("ENVELOPE_SACO_23X31,5_4_0_RAPHAEL _BRANDAO_MACHADO_"
          "NELORE_BEMACH")


class CursorComTitulos(object):
    """Um cursor que devolve titulos gravados, iguais nas quatro vagas."""

    def __init__(self, linhas, vagas=(0, 0, 0, 0)):
        self.linhas = linhas
        self.vagas = vagas
        self.ultimo = None

    def execute(self, sql, parametros=None):
        self.ultimo = sql

    def fetchall(self):
        return self.linhas if "OSTIT" in (self.ultimo or "") else []

    def fetchone(self):
        if "OSESP1" in (self.ultimo or ""):
            return self.vagas
        return None


def test_os_dois_envelopes_tem_o_MESMO_comeco():
    """O ponto de partida: por isso o corte no comeco nao servia."""
    assert VOOLIVRE[:gerempre.LETRAS_NO_TITULO] == \
        NELORE[:gerempre.LETRAS_NO_TITULO]
    assert VOOLIVRE != NELORE


def test_o_titulo_gravado_separa_os_dois():
    um = gerempre.titulo_da_vaga(VOOLIVRE)
    dois = gerempre.titulo_da_vaga(NELORE)

    assert um != dois, "os dois continuam iguais no GEREMPRE"
    assert len(um) <= gerempre.LETRAS_NO_TITULO
    assert len(dois) <= gerempre.LETRAS_NO_TITULO
    # e cada um leva o nome que o distingue
    assert "COLEGIO_VOOLIVRE" in um
    assert "NELORE_BEMACH" in dois
    # o comeco tambem continua la: e por ele que se sabe que peca e
    assert um.startswith("ENVELOPE_SACO") and dois.startswith("ENVELOPE_SACO")


def test_o_NELORE_nao_e_dado_por_lancado_por_causa_do_VOOLIVRE():
    """O defeito exato de 14/09/2026, em uma linha."""
    cur = CursorComTitulos([(19703, gerempre.titulo_da_vaga(VOOLIVRE))])
    duvidas = []
    assert gerempre.ja_esta_em_os(cur, NELORE, "VOPRIX", None, duvidas) is None
    assert duvidas == [], "nem duvida: os titulos sao visivelmente outros"


def test_o_que_a_FIA_lancou_ela_reconhece_de_volta():
    """
    A outra metade: o MESMO servico, voltando. Tem de casar, ou a FIA
    abre OS de novo e cobra duas vezes.
    """
    cur = CursorComTitulos([(19703, gerempre.titulo_da_vaga(NELORE))])
    assert gerempre.ja_esta_em_os(cur, NELORE, "VOPRIX") == 19703


def test_titulo_cortado_A_MAO_no_VOPRIX_e_DUVIDA_e_nao_resposta():
    """
    Quando quem lancou foi uma pessoa no Delphi, o banco guarda o comeco
    cru. No VOPRIX o comeco e a peca e o formato - nao identifica nada -,
    entao isso e duvida: pode ser este servico ou o irmao dele.
    """
    cur = CursorComTitulos([(19703, NELORE[:gerempre.LETRAS_NO_TITULO])])
    duvidas = []
    assert gerempre.ja_esta_em_os(cur, NELORE, "VOPRIX", None,
                                  duvidas) is None
    assert len(duvidas) == 1
    assert duvidas[0][0] == 19703


def test_na_duvida_a_FIA_PARA_e_nao_cobra_nem_deixa_de_cobrar(monkeypatch):
    """
    Cobrar seria arriscar cobranca em dobro; nao cobrar seria dar a
    gravacao. As duas escolhas sao de gente - entao levanta, e o
    processador anota a pendencia 'lance a mao'.
    """
    monkeypatch.setattr(gerempre, "GEREMPRE_CLIENTES", {"VOPRIX": 420})
    cur = CursorComTitulos([(19703, NELORE[:gerempre.LETRAS_NO_TITULO])])

    class Con(object):
        def cursor(self):
            return cur

        def close(self):
            pass

    servico = {"titulo": NELORE, "cliente": "VOPRIX",
               "chapa": (510, 400), "chapas": 4}
    with pytest.raises(ValueError) as caiu:
        gerempre.os_do_servico(servico, con=Con())
    recado = str(caiu.value)
    assert "19703" in recado
    assert "MESMO" in recado and "lance a mao" in recado.lower()


def test_quem_traz_a_NOSSA_OS_no_nome_continua_sendo_reconhecido():
    """
    A SOLIDA e o EMPORIO poem o numero da OS na frente do nome, e esse
    numero nao se repete entre servicos. Ali o comeco cortado ja diz
    quem e - e transformar isso em pendencia seria barulho a toa: sao
    dez dos 24 nomes longos do registro.
    """
    nome = "01954 - CHAPA - CAIXA CYCLUS CREME FACIAL NOVA EMBALAGEM AJUSTADA"
    assert len(nome) > gerempre.LETRAS_NO_TITULO
    cur = CursorComTitulos([(19750, nome[:gerempre.LETRAS_NO_TITULO])])
    duvidas = []
    assert gerempre.ja_esta_em_os(cur, nome, "EMPORIO", None,
                                  duvidas) == 19750
    assert duvidas == []


def test_nome_que_CABE_continua_indo_inteiro_e_intocado():
    """A grande maioria. Nada aqui pode mudar o que ja funcionava."""
    for nome in ("GRADE 3385", "49713 - LUCAS CALIL - PANFLETO ITAPURANGA",
                 "PL - CURRICULO FRED NOVO"):
        assert gerempre.titulo_da_vaga(nome) == nome


def test_o_titulo_partido_nao_parte_palavra_no_fim():
    """
    'os ultimos NOMES', e nao as ultimas letras: um fim cortado no meio
    de uma palavra nao serve para ninguem reconhecer o servico.
    """
    gravado = gerempre.titulo_da_vaga(NELORE)
    fim = gravado.split(gerempre.PARTIDO)[-1]
    assert NELORE.endswith(fim)
    assert NELORE[len(NELORE) - len(fim) - 1] in "_ -", \
        "o fim comecou no meio de uma palavra: %r" % fim


def test_a_marca_da_regravacao_NUNCA_e_comida_pelo_corte():
    gravado = gerempre.titulo_da_vaga(NELORE + " " + gerempre.MARCA_REGRAVACAO)
    assert len(gravado) <= gerempre.LETRAS_NO_TITULO
    assert gravado.endswith(gerempre.MARCA_REGRAVACAO)
    assert "NELORE_BEMACH" in gravado, "perdeu o que distingue o servico"


def test_o_titulo_e_funcao_do_NOME_e_de_mais_nada():
    """
    Nao depende do que ja esta na OS, nem da hora, nem da ordem de
    chegada. Se dependesse, o MESMO servico ganharia titulos diferentes
    em dias diferentes - e a FIA deixaria de reconhecer o que ela propria
    lancou, cobrando duas vezes.
    """
    assert gerempre.titulo_da_vaga(NELORE) == gerempre.titulo_da_vaga(NELORE)
    assert gerempre.montar_vaga(
        {"titulo": NELORE, "cliente": "VOPRIX", "chapa": (510, 400),
         "chapas": 4})["OSTIT"] == gerempre.titulo_da_vaga(NELORE)
