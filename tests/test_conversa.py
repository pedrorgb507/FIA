# -*- coding: utf-8 -*-
r"""
A conversa com a FIA - a tela onde a equipe pergunta e ela responde.

O QUE ESTE ARQUIVO SEGURA ACIMA DE TUDO: ELA SO LE. O pedido do
operador (25/09/2026) foi poder falar com ela, e fala vira comando facil
demais - um "sim" ouvido errado pelo microfone nao pode virar OS aberta
nem chapa gravada. O banco nao tem restauracao. Ha um teste que le a
fonte e reprova se aparecer caminho de escrita.

Nenhum teste fala com a Anthropic: o Claude aqui e de mentira, e responde
o roteiro que o teste manda.
"""

import io
import json
import os
from types import SimpleNamespace

import pytest

from finart_ctp import config, conversa, servidor


@pytest.fixture
def controle(monkeypatch, tmp_path):
    """Uma PASTA_CONTROLE de mentira, com um dia de trabalho dentro."""
    pasta = tmp_path / "_ctp_ia"
    pasta.mkdir()
    monkeypatch.setattr(config, "PASTA_CONTROLE", str(pasta))
    (pasta / "_log_ctp.txt").write_text(
        "[25/09 10:18:54] '50190 - Flavios - panfleto.pdf': 1 pagina(s)\n"
        "[25/09 10:19:05] GEREMPRE: completei a OS 19990 na vaga 2\n"
        "[25/09 10:24:57] GEREMPRE: abri a OS 19991 para IDEAL\n"
        "[25/09 10:35:58]    OK em 96s: 50190_v2.pdf (C+M+Y+K, 81.6 MB)\n",
        encoding="utf-8")
    (pasta / "_PENDENCIAS.txt").write_text(
        "25/09 10:33 | SOLIDA | 50190 | a vaga 2 da OS 19990 sumiu\n",
        encoding="utf-8")
    (pasta / config.REGISTRO).write_text(json.dumps({
        "50190 - Flavios - panfleto.pdf|1|2": {
            "status": "ok", "saidas": ["50190.pdf"], "motivo": "",
            "quando": "25/09/2026 10:19:05",
            "arquivo": "50190 - Flavios - panfleto.pdf"},
        "49572 - Seu Dori - flyer.pdf|3|4": {
            "status": "ok", "saidas": ["49572.pdf"],
            "arquivo": "49572 - Seu Dori - flyer.pdf"}}), encoding="utf-8")
    (pasta / "_fila_os.json").write_text(json.dumps([
        {"titulo": "50190 - FLAVIOS", "cliente": "SOLIDA"},
        {"titulo": "GRADE 3389", "cliente": "VIVA"},
        {"titulo": "50191 - OUTRO", "cliente": "SOLIDA"}]), encoding="utf-8")
    return pasta


# ----------------------------------------------------------------------
# ELA SO LE
# ----------------------------------------------------------------------

def test_a_conversa_nao_tem_caminho_de_escrita():
    """
    Nada de GEREMPRE, processador, gravacao, nem abrir arquivo para
    escrever. Se um dia alguem quiser que ela aja por voz, isso e decisao
    do operador, com confirmacao na tela - e este teste tem de ser mudado
    de proposito, lendo o porque la em cima.
    """
    fonte = io.open(conversa.__file__, encoding="utf-8").read()
    codigo = "\n".join(l for l in fonte.splitlines()
                       if not l.lstrip().startswith("#"))
    for proibido in ("gerempre", "processador", "salvar_registro",
                     "anotar_pendencia", "os.remove", "shutil",
                     '"w"', "'w'", '"a"', "'a'", "msvcrt"):
        assert proibido not in codigo.split('"""', 2)[-1], proibido


def test_o_vigia_e_perguntado_sem_pegar_a_trava(controle):
    """
    Pegar a trava para 'ver se esta livre' e o erro: conseguindo, a
    conversa passaria a segura-la e o vigia seguinte se recusaria a subir.
    """
    (controle / "_rodando.lock").write_bytes(b"\x00processo 7196, desde 25/09 09:07:29")
    r = conversa.vigia_rodando()
    assert "processo 7196" in r
    assert "OK em 96s" in r            # e a ultima linha do log vai junto


# ----------------------------------------------------------------------
# AS FERRAMENTAS
# ----------------------------------------------------------------------

def test_log_com_filtro_so_traz_o_que_bate(controle):
    r = conversa.ler_log(filtro="19991")
    assert "IDEAL" in r and "50190" not in r


def test_log_sem_nada_que_bata_diz_isso(controle):
    assert "nenhuma linha" in conversa.ler_log(filtro="99999")


def test_linhas_do_log_tem_teto(controle):
    """O teto vem de fora (o Claude escolhe o numero); nao pode passar."""
    assert conversa.ler_log(linhas=10 ** 9).count("\n") <= conversa.LINHAS_DO_LOG_MAXIMO


def test_registro_acha_pelo_numero(controle):
    r = json.loads(conversa.procurar_no_registro("50190"))
    assert len(r) == 1 and r[0]["saidas"] == ["50190.pdf"]
    assert "motivo" not in r[0]        # vazio nao ocupa espaco


def test_fila_conta_por_cliente_e_lista_um(controle):
    assert conversa.fila_de_os() == "SOLIDA 2, VIVA 1"
    assert "50191" in conversa.fila_de_os("solida")


def test_sem_pasta_de_controle_nao_quebra(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PASTA_CONTROLE", str(tmp_path / "nada"))
    for f in conversa.FERRAMENTAS.values():
        texto = f() if f is not conversa.procurar_no_registro else f("x")
        assert isinstance(texto, str) and texto


def test_ferramenta_desconhecida_vira_erro_e_nao_excecao():
    assert conversa.usar_ferramenta("apagar_tudo", {}) == (
        "nao conheco a ferramenta 'apagar_tudo'", True)


def test_argumento_estranho_vira_erro_e_nao_excecao():
    saida, falhou = conversa.usar_ferramenta("ler_log", {"nao_existe": 1})
    assert falhou


def test_cada_descricao_tem_a_sua_ferramenta():
    assert ({d["name"] for d in conversa.DESCRICOES}
            == set(conversa.FERRAMENTAS))


# ----------------------------------------------------------------------
# A CONVERSA
# ----------------------------------------------------------------------

class ClaudeDeMentira:
    """Responde, em ordem, o roteiro que o teste mandou."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.pedidos = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._criar))

    def _criar(self, **pedido):
        self.pedidos.append(json.loads(json.dumps(pedido, default=repr)))
        return self.respostas.pop(0)


def _texto(t):
    return SimpleNamespace(stop_reason="end_turn",
                           content=[SimpleNamespace(type="text", text=t)])


def _usa(nome, **entrada):
    return SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="tool_use", id="t1", name=nome, input=entrada)])


def test_pergunta_que_pede_leitura_le_e_responde(controle):
    claude = ClaudeDeMentira(_usa("ler_log", filtro="50190"),
                             _texto("Saiu sim, as dez e trinta e cinco."))
    r = conversa.responder([{"papel": "eu", "texto": "o 50190 saiu?"}],
                           cliente=claude)
    assert r == {"resposta": "Saiu sim, as dez e trinta e cinco.",
                 "erro": False}
    # o que a ferramenta leu voltou para o Claude
    volta = claude.pedidos[1]["messages"][-1]["content"][0]
    assert volta["type"] == "tool_result" and "50190_v2" in volta["content"]


def test_a_hora_vai_na_pergunta_e_nao_no_sistema(controle):
    """O sistema fica igual o dia todo, para o cache do Claude valer."""
    import datetime
    claude = ClaudeDeMentira(_texto("oi"))
    conversa.responder([{"papel": "eu", "texto": "oi"}], cliente=claude,
                       agora=datetime.datetime(2026, 9, 25, 10, 50))
    pedido = claude.pedidos[0]
    assert "25/09/2026 10:50" in pedido["messages"][-1]["content"]
    assert "10:50" not in json.dumps(pedido["system"])


def test_historico_de_fora_e_podado():
    longo = [{"papel": "eu" if i % 2 == 0 else "fia", "texto": "x" * 10 ** 5}
             for i in range(101)]
    msgs = conversa._mensagens(longo)
    assert len(msgs) <= conversa.MENSAGENS_MAXIMAS
    assert all(len(m["content"]) <= conversa.LETRAS_POR_MENSAGEM for m in msgs)
    assert msgs[0]["role"] == "user" and msgs[-1]["role"] == "user"


def test_historico_lixo_nao_quebra():
    assert conversa._mensagens([None, 3, "x", {"papel": "fia", "texto": "oi"}]) == []
    assert conversa._mensagens(None) == []


def test_sem_chave_quem_responde_sao_as_respostas_prontas(monkeypatch,
                                                          controle):
    """O operador escolheu a opcao de graca: sem chave, nada de erro."""
    monkeypatch.setattr(config, "CHAVE_DO_CLAUDE", None, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = conversa.responder([{"papel": "eu", "texto": "o 50190 saiu?"}])
    assert not r["erro"] and "50190 saiu sim" in r["resposta"]


def test_recusa_nao_vira_silencio(controle):
    claude = ClaudeDeMentira(SimpleNamespace(stop_reason="refusal", content=[]))
    r = conversa.responder([{"papel": "eu", "texto": "x"}], cliente=claude)
    assert r["erro"] and r["resposta"]


def test_circulo_de_ferramentas_para_no_teto(controle):
    claude = ClaudeDeMentira(*[_usa("vigia_rodando")] * conversa.VOLTAS_MAXIMAS)
    r = conversa.responder([{"papel": "eu", "texto": "x"}], cliente=claude)
    assert r["erro"] and len(claude.pedidos) == conversa.VOLTAS_MAXIMAS


def test_sem_internet_a_tela_explica(controle):
    class Caido:
        beta = SimpleNamespace(messages=SimpleNamespace(
            create=lambda **k: (_ for _ in ()).throw(OSError("sem rede"))))
    r = conversa.responder([{"papel": "eu", "texto": "x"}], cliente=Caido())
    assert r["erro"] and "Anthropic" in r["resposta"]


# ----------------------------------------------------------------------
# AS RESPOSTAS PRONTAS - o cerebro sem IA, o que roda hoje
# ----------------------------------------------------------------------

import datetime

DIA = datetime.datetime(2026, 9, 25, 11, 0)


def _pergunta(p):
    return conversa.responder_sem_ia(p, agora=DIA)


def test_numero_de_servico_vem_antes_de_saiu(controle):
    """'o 50190 saiu?' tem 'saiu', mas nao e a pergunta do dia inteiro."""
    r = _pergunta("o 50190 saiu?")
    assert r.startswith("O 50190 saiu sim, hoje \u00e0s 10:19")
    assert "chapa 50190" in r
    # e a pendencia dele vem junto - e o que importa para quem perguntou
    assert "pend\u00eancia dele hoje" in r


def test_numero_que_nao_existe_diz_que_nao_achou(controle):
    assert "N\u00e3o achei nada do 12345" in _pergunta("e o 12345?")


def test_os_pelo_numero_procura_no_log(controle):
    assert "A OS 19991 aparece 1 vez" in _pergunta("e a OS 19991?")


def test_pendencia_repetida_e_dita_uma_vez_so(controle):
    """O 50190 de 25/09/2026 perdeu a vaga duas vezes na mesma OS."""
    linha = ("25/09 10:43 | SOLIDA | 50190 - FLAVIOS | a FIA lancou este "
             "servico na vaga 2 da OS 19990 em 2026, e ele NAO ESTA MAIS "
             "LA. A OS era de outro operador.\n")
    (controle / "_PENDENCIAS.txt").write_text(linha * 2, encoding="utf-8")
    r = _pergunta("tem pendencia?")
    assert r.startswith("Hoje tem 2 pend\u00eancias.")
    assert r.count("sumiu") == 1
    assert "lan\u00e7ar \u00e0 m\u00e3o" in r


def test_sem_pendencia_hoje_e_dia_tranquilo(controle):
    (controle / "_PENDENCIAS.txt").write_text(
        "24/09 17:55 | ontem | coisa\n", encoding="utf-8")
    assert "nenhuma pend\u00eancia" in _pergunta("deu algum problema?")


def test_o_que_saiu_hoje_conta_pelo_log(controle):
    r = _pergunta("o que saiu hoje?")
    assert r.startswith("Hoje j\u00e1 saiu 1 chapa, de 1 arquivo.")


def test_fila_de_um_cliente_nao_repete_o_mesmo_numero(controle):
    (controle / "_fila_os.json").write_text(json.dumps(
        [{"titulo": "50190 - A", "cliente": "SOLIDA"}] * 3
        + [{"titulo": "50176 - B", "cliente": "SOLIDA"}]), encoding="utf-8")
    r = _pergunta("como esta a fila da solida?")
    assert "4 servi\u00e7os" in r and r.count("50190") == 1


def test_vigia_vivo_e_vigia_morto(controle):
    """Pergunta ao Windows pelo processo; a trava nao e tocada."""
    trava = controle / "_rodando.lock"
    trava.write_bytes(b"\x00processo %d, desde 25/09 09:07:30" % os.getpid())
    assert _pergunta("o vigia esta rodando?").startswith(
        "Sim, o vigia est\u00e1 rodando desde as 09:07")
    # PID impar nunca existe no Windows - la eles sao multiplos de 4
    trava.write_bytes(b"\x00processo 4194303, desde 24/09 17:00:00")
    r = _pergunta("o vigia esta rodando?")
    assert r.startswith("N\u00e3o, o vigia est\u00e1 parado")
    assert "dia 24/09" in r


def test_pergunta_que_nao_entende_ensina_o_que_da(controle):
    r = _pergunta("qual a cor do ceu?")
    assert "ainda n\u00e3o sei responder" in r and "50190" in r


def test_acento_entra_na_saida_mas_nao_depois_de_desde():
    assert conversa._com_acento("desde as 11:47, e as 12:00") == \
        "desde as 11:47, e \u00e0s 12:00"
    assert conversa._com_acento("Nao ha") == "N\u00e3o ha"
    assert conversa._com_acento("lancado a mao") == "lan\u00e7ado \u00e0 m\u00e3o"


def test_o_fonte_da_conversa_e_ascii():
    """A casa escreve codigo em ASCII; os acentos vao como \\u."""
    io.open(conversa.__file__, encoding="ascii").read()


# ----------------------------------------------------------------------
# A PAGINA
# ----------------------------------------------------------------------

def test_a_pagina_fala_portugues_do_brasil():
    p = servidor.PAGINA_DA_CONVERSA
    assert p.count('"pt-BR"') == 2          # quem ouve e quem fala
    assert 'fetch("/conversa"' in p


def test_a_fila_da_montagem_leva_ate_a_conversa():
    assert 'href="/conversa"' in servidor.pagina_nao_achei()
