# -*- coding: utf-8 -*-
"""
O registro e compartilhado: mais de um programa pode estar rodando.

Nasceu de caso real - uma chapa fechada as 09:20 sumiu do registro as
09:49, quando o outro programa salvou o dicionario dele por cima.
"""

import json
import os
import time

import pytest

import finart_ctp.utils as U


@pytest.fixture(autouse=True)
def controle_no_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "log", lambda *a, **k: None)


def _no_disco(tmp_path):
    with open(str(tmp_path / U.REGISTRO), encoding="utf-8") as f:
        return json.load(f)


def test_salvar_nao_apaga_o_que_o_outro_gravou(tmp_path):
    """Os dois programas comecam iguais e cada um faz um arquivo."""
    U.salvar_registro({"comum": {"arquivo": "ja existia"}})

    programa_a = U.carregar_registro()
    programa_b = U.carregar_registro()

    programa_a["chapa_do_a"] = {"arquivo": "fechada as 09:20"}
    U.salvar_registro(programa_a)

    programa_b["chapa_do_b"] = {"arquivo": "fechada as 09:49"}
    U.salvar_registro(programa_b)

    disco = _no_disco(tmp_path)
    assert "chapa_do_a" in disco, "o segundo apagou o trabalho do primeiro"
    assert "chapa_do_b" in disco
    assert "comum" in disco


def test_quem_salva_recebe_o_conjunto_de_volta(tmp_path):
    """Senao o laco segue com uma lista velha e refaz arquivo dos outros."""
    U.salvar_registro({"do_outro": {"arquivo": "x"}})

    meu = {"meu": {"arquivo": "y"}}
    U.salvar_registro(meu)

    assert "do_outro" in meu and "meu" in meu


def test_o_mais_novo_vence_na_mesma_chave(tmp_path):
    U.salvar_registro({"k": {"status": "erro"}})
    U.salvar_registro({"k": {"status": "ok"}})
    assert _no_disco(tmp_path)["k"]["status"] == "ok"


def test_registro_ilegivel_nao_derruba_a_gravacao(tmp_path):
    """Arquivo pela metade (queda de energia) nao pode travar o programa."""
    (tmp_path / U.REGISTRO).write_text("{isso nao e json", encoding="utf-8")
    U.salvar_registro({"novo": {"arquivo": "z"}})
    assert "novo" in _no_disco(tmp_path)


def test_salvar_nao_remove_nada(tmp_path):
    """
    Consequencia de juntar: apagar uma entrada exige gravar o JSON
    direto. Se um dia alguem 'sumir' uma chave e ela voltar, e por aqui.
    """
    U.salvar_registro({"a": {"x": 1}, "b": {"x": 2}})

    reg = U.carregar_registro()
    del reg["b"]
    U.salvar_registro(reg)

    assert "b" in _no_disco(tmp_path)


# ----------------------------------------------------------------------
# Um programa por maquina
# ----------------------------------------------------------------------

def test_o_segundo_programa_nao_sobe(tmp_path):
    """
    O caso de 08/09/2026: F5 as 11:54 sem fechar a janela das 08:06.
    As duas instancias processaram os mesmos seis arquivos - prova
    impressa em dobro e chapa duplicada no CTP.
    """
    primeiro = U.travar_instancia_unica()
    assert primeiro, "o primeiro programa tem que conseguir subir"
    try:
        assert U.travar_instancia_unica() is None, "o segundo subiu junto"
    finally:
        primeiro.close()


def test_travamento_solta_quando_o_programa_sai(tmp_path):
    """Se travasse para sempre, uma queda de energia deixaria preso."""
    primeiro = U.travar_instancia_unica()
    assert primeiro
    primeiro.close()                       # como quando o processo morre

    segundo = U.travar_instancia_unica()
    assert segundo, "ficou preso depois que o anterior saiu"
    segundo.close()


def test_o_bloqueio_diz_quem_esta_rodando(tmp_path):
    trava = U.travar_instancia_unica()
    try:
        assert "processo" in U.quem_esta_rodando()
    finally:
        trava.close()


def test_varrer_confere_o_registro_de_novo_antes_de_processar(monkeypatch,
                                                              tmp_path):
    """
    Rede de protecao para quando algo mais roda em paralelo: entre uma
    separacao e outra passam minutos, e o registro no disco pode ter
    mudado. Reler antes evita refazer o que outro ja fez.
    """
    import finart_ctp.monitor as M

    (tmp_path / "arte.pdf").write_bytes(b"x")
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar",
                        lambda *a: pytest.fail("outro ja tinha feito"))

    # o disco ja sabe do arquivo; a memoria do nosso laco, nao
    chave = U.chave_arquivo(str(tmp_path / "arte.pdf"))
    monkeypatch.setattr(M, "carregar_registro", lambda: {chave: {"x": 1}})

    assert M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA) == 0


# ----------------------------------------------------------------------
# Arte regravada na pasta com data nova
# ----------------------------------------------------------------------

def test_a_mesma_arte_com_data_nova_nao_e_refeita(monkeypatch, tmp_path):
    """
    O caso do '49694 - Gaspar - colinha.pdf' em 08/09/2026.

    O arquivo foi copiado por cima enquanto a primeira chapa era gerada.
    Nome e tamanho iguais, 12 segundos a mais na data - a chave mudou e o
    programa fez tudo de novo: outra prova impressa e 49694_v2.pdf no CTP,
    identica byte a byte a 49694.pdf.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "49694 - Gaspar - colinha.pdf"
    arte.write_bytes(b"a arte, exatamente a mesma")

    antes = {
        "arquivo": arte.name, "quando": "08/09/2026 08:37:07",
        "saidas": ["49694.pdf"], "status": "ok",
        "impressao": U.impressao_digital(str(arte)),
    }
    chave_velha = U.chave_arquivo(str(arte))

    os.utime(str(arte), (time.time() + 12, time.time() + 12))   # regravada
    assert U.chave_arquivo(str(arte)) != chave_velha, "a chave tinha de mudar"

    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar",
                        lambda *a: pytest.fail("refez a mesma arte"))

    registro = {chave_velha: antes}
    assert M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA) == 0
    assert U.chave_arquivo(str(arte)) in registro, \
        "a chave nova precisa ficar anotada, senao volta na proxima varredura"


def test_arte_corrigida_de_verdade_e_refeita(monkeypatch, tmp_path):
    """
    O outro lado: se a arte MUDOU, tem de ser refeita. O guarda olha o
    conteudo, nao a data - senao uma correcao do cliente seria ignorada.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "49694 - Gaspar - colinha.pdf"
    arte.write_bytes(b"primeira versao da arte")
    antes = {"arquivo": arte.name, "saidas": ["49694.pdf"], "status": "ok",
             "impressao": U.impressao_digital(str(arte))}
    chave_velha = U.chave_arquivo(str(arte))

    arte.write_bytes(b"segunda versao da arte!")      # mesmo tamanho, outro
    os.utime(str(arte), (time.time() + 12, time.time() + 12))
    assert arte.stat().st_size == len(b"primeira versao da arte")
    assert U.chave_arquivo(str(arte)) != chave_velha

    feitos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda *a: feitos.append(a) or
                        {"status": "ok", "saidas": ["49694_v2.pdf"]})

    M.varrer(str(tmp_path), "Z:/saida", {chave_velha: antes}, None, M.SOLIDA)
    assert feitos, "a arte mudou e nao foi refeita"


def test_registro_antigo_sem_impressao_nao_quebra(tmp_path):
    """As entradas gravadas antes deste conserto nao tem o retrato."""
    arte = tmp_path / "arte.pdf"
    arte.write_bytes(b"conteudo")
    velho = {U.chave_arquivo(str(arte)): {"saidas": ["x.pdf"]}}
    assert U.mesmo_trabalho_ja_feito(velho, str(arte)) is None


# ----------------------------------------------------------------------
# Arquivo que aparece na pasta mas nao termina de chegar
# ----------------------------------------------------------------------

def test_pdf_de_zero_byte_vira_pendencia(monkeypatch, tmp_path):
    """
    O caso do '49715 49716 49717 49718 - Lucas Calil - panfletos 4mod.pdf'
    em 08/09/2026: salvo com 0 byte e esquecido na pasta. O programa fez
    certo em nao tocar nele - mas ficou calado, e o operador so viu que a
    chapa nao saiu.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "49715 49716 - Lucas Calil - panfletos.pdf"
    arte.write_bytes(b"")

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append((n, m)))
    monkeypatch.setattr(M, "processar",
                        lambda *a: pytest.fail("encostou em arquivo vazio"))

    parados = {}
    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA, parados=parados)
    assert not avisos, "avisou cedo demais - o arquivo pode estar chegando"

    # o tempo passa e ele continua vazio
    parados[str(arte)]["desde"] -= M.AVISAR_ARQUIVO_PARADO + 1
    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA, parados=parados)
    assert len(avisos) == 1, "nao avisou"
    assert "VAZIO" in avisos[0][1]

    # e nao fica repetindo o aviso a cada 5 segundos
    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA, parados=parados)
    assert len(avisos) == 1, "repetiu o aviso"


def test_quando_o_arquivo_chega_de_verdade_o_aviso_some(monkeypatch, tmp_path):
    """Salvou de novo, agora inteiro: processa e esquece a queixa."""
    import finart_ctp.monitor as M

    arte = tmp_path / "49715 - Lucas Calil - panfletos.pdf"
    arte.write_bytes(b"a arte inteira")

    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "processar",
                        lambda *a: {"status": "ok", "saidas": ["49715.pdf"]})

    parados = {str(arte): {"desde": 0, "avisado": True}}
    assert M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA,
                    parados=parados) == 1
    assert str(arte) not in parados


# ----------------------------------------------------------------------
# O programa mudou no disco depois de subir
# ----------------------------------------------------------------------

def test_avisa_quando_o_codigo_muda_no_disco(monkeypatch):
    """
    O Python le o codigo uma vez, ao subir. Em 08/09/2026 o programa
    rodou a tarde inteira com a versao anterior a tres consertos, e
    ninguem tinha como saber.
    """
    import finart_ctp.monitor as M

    avisos = []
    monkeypatch.setattr(M, "log", lambda msg, **k: avisos.append(msg))

    antes = {"monitor.py": 100.0, "utils.py": 200.0}
    monkeypatch.setattr(M, "retrato_do_programa",
                        lambda: {"monitor.py": 100.0, "utils.py": 200.0})
    assert M.avisar_se_o_programa_mudou(antes, False) is False
    assert not avisos

    monkeypatch.setattr(M, "retrato_do_programa",
                        lambda: {"monitor.py": 100.0, "utils.py": 999.0})
    assert M.avisar_se_o_programa_mudou(antes, False) is True
    assert any("MUDOU NO DISCO" in a for a in avisos)
    assert any("utils.py" in a for a in avisos)
    assert not any("monitor.py" in a for a in avisos), \
        "acusou arquivo que nao mudou"


def test_o_aviso_de_codigo_novo_nao_se_repete(monkeypatch):
    """Repetido a cada 5 segundos, viraria paisagem e ninguem leria."""
    import finart_ctp.monitor as M

    avisos = []
    monkeypatch.setattr(M, "log", lambda msg, **k: avisos.append(msg))
    monkeypatch.setattr(M, "retrato_do_programa", lambda: {"x.py": 2.0})

    assert M.avisar_se_o_programa_mudou({"x.py": 1.0}, True) is True
    assert not avisos


# ----------------------------------------------------------------------
# Nada passa em silencio
# ----------------------------------------------------------------------

def test_arte_que_o_cliente_nao_manda_por_ali_vira_pendencia(monkeypatch,
                                                             tmp_path):
    """
    A Creative ja mandou 7 .cdr em dias passados, e o programa so olhava
    .pdf naquela pasta: cada um teria sumido da vista sem uma linha no
    log. Arquivo de trabalho ignorado calado e servico que ninguem
    lembra de fazer.
    """
    import finart_ctp.monitor as M

    (tmp_path / "arte do cliente.psd").write_bytes(b"x")
    (tmp_path / "montagem.ai").write_bytes(b"x")

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append((n, m)))

    estranhos = set()
    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.EMPORIO, (".pdf",),
             estranhos=estranhos)
    assert sorted(n for n, _ in avisos) == ["arte do cliente.psd",
                                            "montagem.ai"]
    assert "EMPORIO" in avisos[0][1] and ".pdf" in avisos[0][1]

    # e nao repete a cada 5 segundos
    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.EMPORIO, (".pdf",),
             estranhos=estranhos)
    assert len(avisos) == 2


def test_lixo_do_windows_continua_passando_batido(monkeypatch, tmp_path):
    """
    Aviso que grita por qualquer coisa vira aviso que ninguem le. Sobra
    de programa e arquivo de sistema nao sao trabalho de ninguem.
    """
    import finart_ctp.monitor as M

    for lixo in ("Thumbs.db", "desktop.ini", "algo.tmp", "~$rascunho.docx",
                 "planilha.xlsx"):
        (tmp_path / lixo).write_bytes(b"x")

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append(n))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.SOLIDA, (".pdf",))
    assert avisos == []


def test_copia_de_seguranca_do_corel_nao_vira_pendencia(monkeypatch, tmp_path):
    """
    A Corel cria uma dessas ao lado de cada arquivo do operador. Sao
    .cdr - arte, pelo tipo -, mas nao sao trabalho: viraria uma pendencia
    inutil por dia, todo dia.
    """
    import finart_ctp.monitor as M

    (tmp_path / "COPIA_DE_SEGURANCA_DE_Panfleto.cdr").write_bytes(b"x")

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append(n))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.EMPORIO, (".pdf",))
    assert avisos == []


# ----------------------------------------------------------------------
# Subpastas dentro da pasta do dia
# ----------------------------------------------------------------------

def test_arquivo_dentro_de_subpasta_e_processado(monkeypatch, tmp_path):
    """
    O operador cria subpastas para se organizar - uma 'noite' com o que
    chegou depois do expediente - e combinou que aquilo e trabalho igual
    ao que esta solto na pasta do dia. Antes o programa so olhava o
    primeiro nivel: o que caisse numa subpasta ficava para sempre sem ser
    visto, sem nem virar pendencia.
    """
    import finart_ctp.monitor as M

    (tmp_path / "GRADE 1.pdf").write_bytes(b"a")
    noite = tmp_path / "noite"
    noite.mkdir()
    (noite / "GRADE 2.pdf").write_bytes(b"b")
    (noite / "mais tarde").mkdir()
    (noite / "mais tarde" / "GRADE 3.pdf").write_bytes(b"c")

    vistos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente: (
        vistos.append(os.path.basename(caminho))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    assert M.varrer(str(tmp_path), "Z:/saida", {}, None, M.VIVA) == 3
    assert sorted(vistos) == ["GRADE 1.pdf", "GRADE 2.pdf", "GRADE 3.pdf"]


def test_o_aviso_diz_em_que_subpasta_esta_o_arquivo(monkeypatch, tmp_path):
    """
    Sem dizer a subpasta, o operador ficaria procurando na pasta do dia
    um arquivo que esta em outro lugar.
    """
    import finart_ctp.monitor as M

    noite = tmp_path / "noite"
    noite.mkdir()
    (noite / "arte solta.psd").write_bytes(b"x")

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append(n))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.VIVA, (".pdf",))
    assert avisos == [os.path.join("noite", "arte solta.psd")]


def test_pasta_do_dia_que_sumiu_nao_vira_pasta_vazia(tmp_path):
    """
    Se a rede cair, o erro tem de estourar. Dizer 'nao ha trabalho
    nenhum' o dia inteiro seria pior do que parar.
    """
    import finart_ctp.monitor as M

    with pytest.raises(OSError):
        M.arquivos_do_dia(str(tmp_path / "nao existe"))
