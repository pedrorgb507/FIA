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
