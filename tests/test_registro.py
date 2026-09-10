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


# ----------------------------------------------------------------------
# Quando NAO DA PARA SABER se a arte ja virou chapa
# ----------------------------------------------------------------------
# Em 09/09/2026, 87 das 156 entradas do registro nao tinham impressao
# digital: sao anteriores ao retrato. Para elas o guarda nao agia - sem
# candidata, respondia 'nao e o mesmo', e a chapa saia de novo.
#
# Nome e tamanho iguais SEM retrato para confirmar e exatamente onde as
# duas respostas erram: 'ja feito' arrisca chapa FALTANDO, 'novo' arrisca
# chapa DUPLICADA. Entao a resposta passa a ser uma terceira, e ela chama
# gente - a regra da casa, que o que sai do padrao vira pendencia em vez
# de chute.
#
# Este bloco substitui o antigo 'registro_antigo_sem_impressao_nao_quebra',
# que afirmava o contrato de dois estados. Ele nao foi apagado por
# descuido: era ele que dizia que entrada sem retrato devolve 'nao e', e e
# essa resposta que agora esta errada.

def _entrada_velha_sem_retrato(arte, **extra):
    """Como o registro guardava antes de existir a impressao digital."""
    entrada = {"arquivo": os.path.basename(str(arte)),
               "saidas": ["49695.pdf"], "status": "ok",
               "quando": "08/09/2026 09:01:18"}
    entrada.update(extra)
    return entrada


def _volta_com_data_nova(arte):
    """A arte reaparece na pasta com data nova, como sempre acontece."""
    os.utime(str(arte), (time.time() + 12, time.time() + 12))


def test_sem_retrato_o_registro_nao_sabe_dizer(tmp_path):
    arte = tmp_path / "49695 - Radio Dente - pasta.pdf"
    arte.write_bytes(b"a arte de sempre")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    situacao, entrada = U.situacao_no_registro(
        {velha: _entrada_velha_sem_retrato(arte)}, str(arte))

    assert situacao == U.NAO_DA_PARA_SABER
    assert entrada["saidas"] == ["49695.pdf"], \
        "precisa devolver a entrada, para o aviso dizer que chapa saiu"


def test_com_retrato_que_bate_o_registro_sabe_que_e_a_mesma(tmp_path):
    arte = tmp_path / "49694 - Gaspar - colinha.pdf"
    arte.write_bytes(b"a arte, exatamente a mesma")
    entrada = _entrada_velha_sem_retrato(
        arte, impressao=U.impressao_digital(str(arte)))
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    situacao, _ = U.situacao_no_registro({velha: entrada}, str(arte))
    assert situacao == U.JA_FEITO


def test_com_retrato_que_nao_bate_e_trabalho_novo(tmp_path):
    """Correcao do cliente: mesmo nome, mesmo tamanho, outro conteudo."""
    arte = tmp_path / "49694 - Gaspar - colinha.pdf"
    arte.write_bytes(b"primeira versao da arte")
    entrada = _entrada_velha_sem_retrato(
        arte, impressao=U.impressao_digital(str(arte)))
    velha = U.chave_arquivo(str(arte))

    arte.write_bytes(b"segunda versao da arte!")      # mesmo tamanho
    _volta_com_data_nova(arte)

    situacao, _ = U.situacao_no_registro({velha: entrada}, str(arte))
    assert situacao == U.TRABALHO_NOVO


def test_sem_nada_parecido_e_trabalho_novo(tmp_path):
    arte = tmp_path / "49800 - Cliente - servico.pdf"
    arte.write_bytes(b"arte nunca vista")
    situacao, entrada = U.situacao_no_registro({}, str(arte))
    assert situacao == U.TRABALHO_NOVO
    assert entrada is None


def test_cliente_diferente_nao_gera_incerteza(tmp_path):
    """
    Nome e tamanho iguais em clientes diferentes nao sao o mesmo trabalho.

    Sem isto, um 'grade.pdf' da VIVA faria o 'grade.pdf' da SOLIDA parar -
    pendencia falsa, que e o comeco de aviso que ninguem le.
    """
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a arte")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    situacao, _ = U.situacao_no_registro(
        {velha: _entrada_velha_sem_retrato(arte, cliente="VIVA")},
        str(arte), "SOLIDA")
    assert situacao == U.TRABALHO_NOVO


def test_incerteza_ganha_de_trabalho_novo(tmp_path):
    """
    Duas candidatas: uma com retrato que nao bate, outra sem retrato.

    A primeira diz 'nao sou eu'. A segunda nao diz nada - e enquanto uma
    delas puder ser, nao da para seguir.
    """
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"versao A")
    com_retrato = _entrada_velha_sem_retrato(
        arte, impressao=U.impressao_digital(str(arte)), saidas=["1.pdf"])

    arte.write_bytes(b"versao B")                     # mesmo tamanho
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    registro = {velha: com_retrato,
                velha + "x": _entrada_velha_sem_retrato(arte,
                                                        saidas=["2.pdf"])}
    situacao, entrada = U.situacao_no_registro(registro, str(arte))
    assert situacao == U.NAO_DA_PARA_SABER
    assert entrada["saidas"] == ["2.pdf"], "a duvida e sobre a SEM retrato"


def test_erro_antigo_nao_conta_como_chapa_feita(tmp_path):
    """
    Entrada de erro nao gerou chapa nenhuma - nao ha o que duplicar.

    O registro guarda tambem o que FALHOU ('nao achei numero de OS no
    nome'). Se essas contassem, o arquivo reenviado depois do conserto
    seria barrado - e o aviso diria 'ja virou chapa', sobre uma chapa que
    nunca existiu.
    """
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a arte")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    erro = {"arquivo": "grade.pdf", "status": "erro", "saidas": [],
            "motivo": "nao achei numero de OS no nome",
            "quando": "08/09/2026 10:00:00"}
    situacao, _ = U.situacao_no_registro({velha: erro}, str(arte))
    assert situacao == U.TRABALHO_NOVO


def test_erro_antigo_com_retrato_tambem_nao_segura(tmp_path):
    """O mesmo do lado de ca: retrato de um erro nao e chapa feita."""
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a arte")
    erro = {"arquivo": "grade.pdf", "status": "erro", "saidas": [],
            "impressao": U.impressao_digital(str(arte)),
            "quando": "08/09/2026 10:00:00"}
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    situacao, _ = U.situacao_no_registro({velha: erro}, str(arte))
    assert situacao == U.TRABALHO_NOVO


def test_cliente_diferente_nem_mesmo_com_arte_identica(tmp_path):
    """
    Dois clientes com arte identica sao dois servicos, e duas chapas.

    Cada um tem a sua OS e o seu faturamento. Reconhecer pelo conteudo e
    calar seria deixar o segundo sem chapa e sem aviso.
    """
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a mesma arte, byte a byte")
    da_viva = {"arquivo": "grade.pdf", "status": "ok", "saidas": ["1.pdf"],
               "impressao": U.impressao_digital(str(arte)),
               "cliente": "VIVA", "quando": "08/09/2026 10:00:00"}
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    situacao, _ = U.situacao_no_registro({velha: da_viva}, str(arte),
                                         "SOLIDA")
    assert situacao == U.TRABALHO_NOVO


def test_o_incerto_nao_e_relido_a_cada_varredura(monkeypatch, tmp_path):
    """
    A pasta e de rede e a varredura passa a cada 5 segundos.

    O arquivo incerto fica na pasta de proposito, esperando decisao. Se
    cada passada relesse os 46 MB dele para chegar a mesma duvida, a rede
    pagaria a conta o dia inteiro.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"versao A")
    com_retrato = _entrada_velha_sem_retrato(
        arte, impressao=U.impressao_digital(str(arte)), saidas=["1.pdf"])
    arte.write_bytes(b"versao B")                     # mesmo tamanho
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    leituras = []
    de_verdade = U.impressao_digital
    monkeypatch.setattr(U, "impressao_digital",
                        lambda c, *a, **k: (leituras.append(c),
                                            de_verdade(c, *a, **k))[1])
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "anotar_pendencia", lambda *a, **k: None)
    monkeypatch.setattr(M, "processar", lambda *a: pytest.fail("processou"))

    registro = {velha: com_retrato,
                velha + "x": _entrada_velha_sem_retrato(arte,
                                                        saidas=["2.pdf"])}
    incertos = set()
    for _ in range(3):
        M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA,
                 incertos=incertos)
    assert len(leituras) == 1, "releu o arquivo a cada passada"


def test_outro_arquivo_no_mesmo_caminho_avisa_de_novo(monkeypatch, tmp_path):
    """
    O aviso e do ARQUIVO, nao do lugar onde ele estava.

    Resolvida a duvida, o operador poe outro arquivo com o mesmo nome na
    pasta. Se o silencio fosse por caminho, esse segundo nao viraria
    chapa nem aviso - sumiria calado, que e o pior dos dois mundos.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a primeira")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append(m))
    monkeypatch.setattr(M, "processar", lambda *a: pytest.fail("processou"))

    registro = {velha: _entrada_velha_sem_retrato(arte)}
    incertos = set()
    M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA,
             incertos=incertos)

    arte.write_bytes(b"a segunda!!")                  # outro arquivo, mesmo nome
    velha2 = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)
    registro[velha2] = _entrada_velha_sem_retrato(arte, saidas=["49700.pdf"])
    M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA,
             incertos=incertos)

    assert len(avisos) == 2, "o segundo arquivo tambem tem de chamar gente"


def test_sem_retrato_nem_abre_o_arquivo(tmp_path, monkeypatch):
    """
    A pasta e de rede e a varredura passa a cada 5 segundos.

    Se nenhuma candidata tem retrato, nao ha com o que comparar - ler o
    arquivo seria puro desperdicio.
    """
    arte = tmp_path / "grade.pdf"
    arte.write_bytes(b"a arte")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    monkeypatch.setattr(U, "impressao_digital",
                        lambda *a, **k: pytest.fail("abriu o arquivo a toa"))
    situacao, _ = U.situacao_no_registro(
        {velha: _entrada_velha_sem_retrato(arte)}, str(arte))
    assert situacao == U.NAO_DA_PARA_SABER


def test_incerteza_vira_pendencia_e_nao_vira_chapa(monkeypatch, tmp_path):
    """
    O caso do '49695 - Radio Dente - pasta.pdf' em 09/09/2026.

    Ja virava chapa em 08/09. Voltou pela ponte do Teams e teria sido
    gravado de novo: OS nova no GEREMPRE de producao, baixa de chapa no
    estoque de verdade e prova na Konica.
    """
    import finart_ctp.monitor as M

    arte = tmp_path / "49695 - Radio Dente - pasta.pdf"
    arte.write_bytes(b"a arte de sempre")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append((n, m,
                                                                  cliente)))
    monkeypatch.setattr(M, "processar",
                        lambda *a: pytest.fail("gravou sem poder confirmar"))

    registro = {velha: _entrada_velha_sem_retrato(arte, cliente="SOLIDA")}
    assert M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA) == 0

    assert avisos, "tinha de chamar gente"
    nome, motivo, cliente = avisos[0]
    assert nome == arte.name
    assert "49695.pdf" in motivo, "o aviso tem de dizer que chapa saiu"
    assert "08/09/2026" in motivo, "e quando ela saiu"
    assert cliente == "SOLIDA", "e de quem e o arquivo"
    assert U.chave_arquivo(str(arte)) not in registro, \
        "o incerto nao entra no registro, senao some para sempre"


def test_o_arquivo_incerto_fica_na_pasta(monkeypatch, tmp_path):
    """Nao se pede o arquivo de novo ao cliente por duvida nossa."""
    import finart_ctp.monitor as M

    arte = tmp_path / "49695 - Radio Dente - pasta.pdf"
    arte.write_bytes(b"a arte de sempre")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "anotar_pendencia", lambda *a, **k: None)
    monkeypatch.setattr(M, "processar", lambda *a: pytest.fail("processou"))

    M.varrer(str(tmp_path), "Z:/saida",
             {velha: _entrada_velha_sem_retrato(arte)}, None, M.SOLIDA)
    assert arte.exists()


def test_a_incerteza_so_chama_gente_uma_vez(monkeypatch, tmp_path):
    """Aviso que se repete a cada 5 segundos vira aviso que ninguem le."""
    import finart_ctp.monitor as M

    arte = tmp_path / "49695 - Radio Dente - pasta.pdf"
    arte.write_bytes(b"a arte de sempre")
    velha = U.chave_arquivo(str(arte))
    _volta_com_data_nova(arte)

    avisos = []
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "carregar_registro", lambda: {})
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda n, m, cliente=None: avisos.append(n))
    monkeypatch.setattr(M, "processar", lambda *a: pytest.fail("processou"))

    registro = {velha: _entrada_velha_sem_retrato(arte)}
    incertos = set()
    for _ in range(3):
        M.varrer(str(tmp_path), "Z:/saida", registro, None, M.SOLIDA,
                 incertos=incertos)
    assert len(avisos) == 1


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
