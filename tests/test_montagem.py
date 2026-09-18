# -*- coding: utf-8 -*-
r"""
O portao PARA MONTAR da AMERICA - o que AINDA FALTA montar.

E o irmao da 'PARA CTP', e o contrario dela: na PARA CTP esta o que uma
pessoa ja revisou e vai virar chapa; aqui esta o que chegou POR MONTAR e
ninguem montou ainda.

Por que um portao novo, e nao a pasta do dia: a pasta do dia acumula tres
coisas - o que chegou por montar, a montagem gravada e as copias que
sobem do portao. Com uma pessoa so isso dava, porque ela sabia de cabeca
qual era qual. Com a equipe inteira mexendo, vira "qual desses e o que
falta?". O portao se le sozinho: o que esta la e o que falta.

O que estes testes seguram: a fila nao mente. Arquivo pela metade nao
entra (daria medida errada), arquivo ja montado nao volta (duplicaria
trabalho e arquivo), e a pasta do dia fica fora disso - ela nao e fila de
ninguem.
"""

import io
import os

import pytest

from finart_ctp import montagem


MM = 72.0 / 25.4


def _pdf(caminho, marca=b"", paginas=1, larg_mm=None, alt_mm=None):
    """Um PDF de VERDADE, que o pypdf abre - o mesmo de test_america."""
    import pypdf
    w = pypdf.PdfWriter()
    larg = larg_mm * MM if larg_mm else 200
    alt = alt_mm * MM if alt_mm else 200
    for _ in range(paginas):
        w.add_blank_page(width=larg, height=alt)
    with io.open(caminho, "wb") as f:
        w.write(f)
        if marca:
            f.write(b"\n% " + marca + b"\n")
    return caminho


@pytest.fixture
def sem_ghostscript(monkeypatch):
    """
    A medicao de tintas roda o Ghostscript, que custa segundos por
    arquivo. Aqui ela devolve um numero combinado - o que se testa e o
    que a fila FAZ com a medida, nao o Ghostscript.
    """
    chamadas = []

    def medir(pdf):
        chamadas.append(pdf)
        return 325.0, 430.0, set("CMYK")

    monkeypatch.setattr(montagem.america, "medir", medir)
    return chamadas


@pytest.fixture
def portao(tmp_path, monkeypatch):
    """A pasta do dia da AMERICA com o portao PARA MONTAR dentro."""
    dia = tmp_path / "AMERICA" / "SETEMBRO" / "18"
    porta = dia / montagem.PORTAO
    porta.mkdir(parents=True)
    monkeypatch.setattr(montagem.america, "pasta_do_dia_america",
                        lambda quando=None: (str(dia), None))
    # a espera da rede dorme 2 segundos olhando o tamanho crescer. Na
    # maquina e o que impede montagem de arquivo pela metade; aqui os
    # arquivos ja nascem prontos.
    monkeypatch.setattr(montagem, "arquivos_estaveis", lambda cs: list(cs))
    return dia, porta


# ----------------------------------------------------------------------
# O portao existe, e e dentro da pasta do dia
# ----------------------------------------------------------------------

def test_o_portao_fica_dentro_da_pasta_do_dia(portao):
    dia, porta = portao
    achou_dia, achou_portao = montagem.pastas_da_montagem()
    assert achou_dia == str(dia)
    assert achou_portao == str(porta)


def test_sem_pasta_do_dia_nao_ha_portao(monkeypatch):
    """Dia que a AMERICA nao mandou nada nao tem pasta - e nao e erro."""
    monkeypatch.setattr(montagem.america, "pasta_do_dia_america",
                        lambda quando=None: (None, None))
    assert montagem.pastas_da_montagem() == (None, None)


def test_o_portao_e_irmao_da_PARA_CTP_e_nao_a_mesma_pasta(portao):
    """
    Sao dois portoes na mesma pasta do dia, e com sentidos opostos: um
    guarda o que falta montar, o outro o que ja foi revisado e vai virar
    chapa. Confundi-los faria a fila mostrar chapa pronta como trabalho
    por fazer.
    """
    from finart_ctp import america
    assert montagem.PORTAO != america.PORTAO


# ----------------------------------------------------------------------
# A FILA: o que esta esperando montagem
# ----------------------------------------------------------------------

def test_a_fila_traz_so_o_que_esta_esperando(portao, monkeypatch):
    """
    O teste que o ticket pediu, com os tres casos de uma vez: um arquivo
    pronto, um ainda chegando pela rede e um que ja foi montado antes. So
    o primeiro e trabalho.
    """
    dia, porta = portao
    _pdf(str(porta / "pronto.pdf"), b"pronto")
    _pdf(str(porta / "chegando.pdf"), b"chegando")
    ja_feito = _pdf(str(porta / "ja montado.pdf"), b"ja montado")

    monkeypatch.setattr(montagem, "arquivos_estaveis",
                        lambda cs: [c for c in cs
                                    if "chegando" not in os.path.basename(c)])
    monkeypatch.setattr(montagem, "carregar_montagens",
                        lambda: {montagem.chave_arquivo(ja_feito): {
                            "quem": "Pedro", "quando": "18/09/2026 09:12"}})

    assert [os.path.basename(c) for c in montagem.fila()] == ["pronto.pdf"]


def test_arquivo_que_termina_de_chegar_aparece_na_volta_seguinte(portao,
                                                                monkeypatch):
    """
    Nao entrar por estar chegando nao e recusa - e espera. A volta
    seguinte o encontra, e ai ele e trabalho como qualquer outro.
    """
    dia, porta = portao
    _pdf(str(porta / "grande.pdf"))

    chegando = {"ainda": True}
    monkeypatch.setattr(montagem, "arquivos_estaveis",
                        lambda cs: [] if chegando["ainda"] else list(cs))
    assert montagem.fila() == []

    chegando["ainda"] = False           # terminou de copiar
    assert [os.path.basename(c) for c in montagem.fila()] == ["grande.pdf"]


def test_arquivo_ja_montado_nao_volta_para_a_fila(portao, monkeypatch):
    """
    Refazer montagem duplica arquivo E trabalho: sairiam duas montagens
    do mesmo servico na pasta do dia, e alguem revisaria as duas.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "convite.pdf"))
    monkeypatch.setattr(montagem, "carregar_montagens",
                        lambda: {montagem.chave_arquivo(arte): {}})
    assert montagem.fila() == []


def test_a_pasta_do_dia_fora_do_portao_nao_entra_na_fila(portao):
    """
    A pasta do dia tem a montagem gravada e as copias que sobem do
    portao. Nada disso e trabalho por fazer - e por isso que o portao
    existe.
    """
    dia, porta = portao
    _pdf(str(porta / "por montar.pdf"))
    _pdf(str(dia / "montagem de ontem_MONTAGEM.pdf"))
    _pdf(str(dia / "copia que subiu do portao.pdf"))

    assert [os.path.basename(c) for c in montagem.fila()] == ["por montar.pdf"]


def test_a_fila_nao_escreve_nada(portao):
    """
    E o '--olhar' da casa: conferir nao muda nada. O portao e a pasta do
    dia ficam exatamente como estavam.
    """
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))
    _pdf(str(dia / "guardada.pdf"))

    antes = sorted((os.path.relpath(os.path.join(r, f), str(dia)),
                    os.path.getsize(os.path.join(r, f)))
                   for r, _, fs in os.walk(str(dia)) for f in fs)
    montagem.fila()
    depois = sorted((os.path.relpath(os.path.join(r, f), str(dia)),
                     os.path.getsize(os.path.join(r, f)))
                    for r, _, fs in os.walk(str(dia)) for f in fs)
    assert antes == depois


def test_portao_vazio_nao_e_erro(portao):
    assert montagem.fila() == []


def test_portao_que_nao_existe_e_pergunta_DIFERENTE_de_fila_vazia(
        tmp_path, monkeypatch):
    """
    'A equipe montou tudo' e 'ninguem criou a pasta ainda' dao a mesma
    fila vazia e NAO sao a mesma coisa. A pasta do dia e nova todo dia,
    e sem separar as duas a tela mandaria a equipe embora numa manha em
    que so faltava criar a pasta.
    """
    dia = tmp_path / "dia"
    dia.mkdir()
    monkeypatch.setattr(montagem.america, "pasta_do_dia_america",
                        lambda quando=None: (str(dia), None))
    assert montagem.portao_existe() is False

    (dia / montagem.PORTAO).mkdir()
    assert montagem.portao_existe() is True


def test_sem_pasta_do_dia_o_portao_tambem_nao_existe(monkeypatch):
    monkeypatch.setattr(montagem.america, "pasta_do_dia_america",
                        lambda quando=None: (None, None))
    assert montagem.portao_existe() is False


def test_portao_que_nao_existe_ainda_nao_e_erro(tmp_path, monkeypatch):
    """
    O portao e criado por GENTE - ninguem o cria sozinho, igual ao da
    'PARA CTP' da AMERICA. Antes de existir, a fila e vazia - e nao uma
    pilha de erro na tela de quem so quis conferir.
    """
    dia = tmp_path / "dia"
    dia.mkdir()
    monkeypatch.setattr(montagem.america, "pasta_do_dia_america",
                        lambda quando=None: (str(dia), None))
    assert montagem.fila() == []


def test_a_fila_vem_em_ordem(portao):
    """Duas pessoas olhando a fila veem a mesma coisa na mesma ordem."""
    dia, porta = portao
    for nome in ("c.pdf", "a.pdf", "b.pdf"):
        _pdf(str(porta / nome))
    assert [os.path.basename(c) for c in montagem.fila()] == \
        ["a.pdf", "b.pdf", "c.pdf"]


def test_o_que_nao_e_arquivo_de_arte_fica_de_fora(portao):
    """
    A AMERICA manda pelo WhatsApp, e do WhatsApp vem de tudo: a mensagem
    em .txt, o print da conversa, a planilha. Nada disso se monta.
    """
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))
    (porta / "o que ela pediu.txt").write_bytes(b"2 poses na 52")
    (porta / "print da conversa.jpg").write_bytes(b"x")
    (porta / "Thumbs.db").write_bytes(b"x")

    assert [os.path.basename(c) for c in montagem.fila()] == ["arte.pdf"]


def test_a_fila_espera_a_rede_UMA_vez_e_nao_uma_por_arquivo(portao,
                                                            monkeypatch):
    """
    A fila vai atender uma tela de gente. Esperando dois segundos por
    arquivo, um portao com vinte deixaria a tela pendurada quarenta
    segundos - e ninguem entende uma tela que trava quando ha MAIS
    trabalho.
    """
    from finart_ctp import utils
    dia, porta = portao
    for n in range(12):
        _pdf(str(porta / ("arte %02d.pdf" % n)), b"x" * (n + 1))

    dormiu = []
    monkeypatch.setattr(utils.time, "sleep", lambda s: dormiu.append(s))
    monkeypatch.setattr(montagem, "arquivos_estaveis", utils.arquivos_estaveis)

    assert len(montagem.fila()) == 12
    assert dormiu == [utils.ESPERA_DA_REDE]


def test_arquivo_que_sai_do_portao_no_meio_nao_derruba_a_fila(portao,
                                                             monkeypatch):
    """
    Duas pessoas mexendo na mesma pasta: uma confere a fila enquanto a
    outra move um arquivo. Quem so quis olhar nao merece pilha de erro.
    """
    dia, porta = portao
    ficou = _pdf(str(porta / "ficou.pdf"))
    saiu = _pdf(str(porta / "saiu.pdf"))

    de_verdade = montagem.chave_arquivo

    def some_ao_perguntar(caminho):
        if os.path.basename(caminho) == "saiu.pdf" and os.path.exists(saiu):
            os.remove(saiu)
        return de_verdade(caminho)

    monkeypatch.setattr(montagem, "chave_arquivo", some_ao_perguntar)
    assert [os.path.basename(c) for c in montagem.fila()] == ["ficou.pdf"]
    assert os.path.exists(ficou)


def test_subpasta_dentro_do_portao_nao_entra(portao):
    """
    Pasta nao se monta. E o portao e raso de proposito: o que esta nele
    e a lista, e uma lista com galho dentro deixa de se ler sozinha.
    """
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))
    (porta / "antigas").mkdir()
    _pdf(str(porta / "antigas" / "arte velha.pdf"))

    assert [os.path.basename(c) for c in montagem.fila()] == ["arte.pdf"]


# ----------------------------------------------------------------------
# A FILA MEDIDA - o que a tela mostra de cada arquivo
# ----------------------------------------------------------------------
# Cinco coisas, e nenhuma delas e enfeite. A COR em especial: e ela que
# decide entre a SM 74 e a MOZP na regra da casa.

def test_a_fila_medida_diz_tamanho_cor_paginas_e_marca(portao,
                                                       sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"), paginas=2)

    fila = montagem.fila_medida()
    assert len(fila) == 1
    item = fila[0]
    assert item["arquivo"] == "convite.pdf"
    assert (round(item["largura"]), round(item["altura"])) == (325, 430)
    assert item["tintas"] == ["C", "K", "M", "Y"]
    assert item["peb"] is False
    assert item["paginas"] == 2
    # pagina em branco nao tem marca de corte nenhuma
    assert item["tem_marca"] is False
    assert item["marca_no_pe"] is None


def test_preto_e_branco_e_dito_porque_e_ele_que_escolhe_a_maquina(
        portao, monkeypatch):
    """
    Acima do formato 4, colorido vai na SM 74 e preto-e-branco na MOZP. A
    fila que nao diz a cor deixa essa escolha no ar.
    """
    dia, porta = portao
    _pdf(str(porta / "cartaz.pdf"))
    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (650.0, 550.0, {"K"}))

    item = montagem.fila_medida()[0]
    assert item["peb"] is True
    assert item["tintas"] == ["K"]


def test_a_medida_da_fila_e_a_MESMA_conta_da_casa(portao, monkeypatch):
    """
    Nao existe segunda conta na casa. Trocando o medir() da FIA, o numero
    que a tela mostra troca junto - se houvesse uma conta propria aqui, a
    tela e o vigia poderiam discordar sobre o tamanho do mesmo arquivo, e
    ai um dos dois manda chapa errada.
    """
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))
    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (111.0, 222.0, {"M"}))

    item = montagem.fila_medida()[0]
    assert (item["largura"], item["altura"]) == (111.0, 222.0)
    assert item["tintas"] == ["M"]


def test_a_marca_de_corte_e_o_pe_dela_saem_do_arquivo(portao, monkeypatch,
                                                      sem_ghostscript):
    """
    Sem marca de corte a montagem nao sabe que lado e o pe - e e do pe
    que a pinca se mede. Por isso a fila diz se ela existe, e a quantos
    mm da borda ela esta.
    """
    dia, porta = portao
    _pdf(str(porta / "com marca.pdf"))
    monkeypatch.setattr(montagem.marcas, "marcas_de_corte",
                        lambda pdf, pagina=1: {"pe": 11.9, "topo": None,
                                               "esquerda": 10.0,
                                               "direita": 10.0})

    item = montagem.fila_medida()[0]
    assert item["tem_marca"] is True
    assert item["marca_no_pe"] == 11.9


def test_arquivo_que_nao_da_para_medir_AINDA_APARECE_na_fila(portao,
                                                             monkeypatch):
    """
    Some da fila e pior que aparecer sem medida: o arquivo esta no
    portao, e trabalho, e alguem tem de saber que ele existe. A fila diz
    o que nao conseguiu, e nao esconde o servico.
    """
    dia, porta = portao
    _pdf(str(porta / "estranho.pdf"))

    def nao_deu(pdf):
        raise RuntimeError("o Ghostscript nao respondeu")

    monkeypatch.setattr(montagem.america, "medir", nao_deu)

    item = montagem.fila_medida()[0]
    assert item["arquivo"] == "estranho.pdf"
    assert item["largura"] is None
    assert "Ghostscript" in item["erro"]


def test_a_medida_nao_se_refaz_a_cada_OLHADA(portao, sem_ghostscript):
    """
    Medir tinta roda o Ghostscript, que custa segundos por arquivo. A
    tela e atualizada a vontade por gente que esta escolhendo o que
    montar - remedir a cada F5 poria a equipe esperando de novo, que e o
    que esta fila existe para acabar.
    """
    dia, porta = portao
    _pdf(str(porta / "pesado.pdf"))

    primeira = montagem.fila_medida()
    segunda = montagem.fila_medida()

    assert len(sem_ghostscript) == 1, "mediu duas vezes o mesmo arquivo"
    assert primeira[0]["largura"] == segunda[0]["largura"]


def test_arquivo_TROCADO_e_medido_de_novo(portao, sem_ghostscript):
    """
    A AMERICA manda o arquivo corrigido com o mesmo nome. Aproveitar a
    medida velha mostraria o tamanho do arquivo que nao esta mais la.
    """
    dia, porta = portao
    arte = str(porta / "arte.pdf")
    _pdf(arte)
    montagem.fila_medida()

    _pdf(arte, b"agora e outro arquivo, e maior")   # mesmo nome
    montagem.fila_medida()

    assert len(sem_ghostscript) == 2


def test_medida_que_FALHOU_nao_fica_guardada(portao, monkeypatch):
    """
    Ghostscript fora do ar e coisa de momento. Guardando a falha, o
    arquivo ficaria sem medida para sempre, e ninguem saberia por que.
    """
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))

    tentativas = []

    def so_da_na_segunda(pdf):
        tentativas.append(pdf)
        if len(tentativas) == 1:
            raise RuntimeError("fora do ar")
        return 325.0, 430.0, set("CMYK")

    monkeypatch.setattr(montagem.america, "medir", so_da_na_segunda)

    assert montagem.fila_medida()[0]["erro"]
    assert montagem.fila_medida()[0]["largura"] == 325.0
    assert len(tentativas) == 2


def test_a_medida_e_guardada_no_PC_e_nao_na_pasta_do_cliente(portao,
                                                             sem_ghostscript):
    """
    A regra da casa nao muda por causa de uma tela: a FIA nao escreve nem
    apaga nada na pasta do cliente, que e compartilhada. O que ela sabe
    fica no PC dela.
    """
    from finart_ctp import utils
    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))

    antes = sorted((os.path.relpath(os.path.join(r, f), str(dia)))
                   for r, _, fs in os.walk(str(dia)) for f in fs)
    montagem.fila_medida()
    depois = sorted((os.path.relpath(os.path.join(r, f), str(dia)))
                    for r, _, fs in os.walk(str(dia)) for f in fs)

    assert antes == depois
    assert montagem.caminho_das_medidas().startswith(utils.PASTA_CONTROLE)


def test_portao_vazio_da_fila_medida_vazia(portao, sem_ghostscript):
    """E nao um erro: portao vazio e o dia normal de quem ja montou tudo."""
    assert montagem.fila_medida() == []


def test_o_que_nao_entra_na_fila_nao_e_medido(portao, sem_ghostscript):
    """
    Medir o que nao e trabalho e gastar Ghostscript para nada - e o que
    nao e trabalho e a maioria, ao fim do dia.
    """
    dia, porta = portao
    montado = _pdf(str(porta / "ja montado.pdf"))
    montagem.anotar_montagem(montado, {"quem": "Pedro"})
    _pdf(str(dia / "fora do portao.pdf"))

    assert montagem.fila_medida() == []
    assert sem_ghostscript == []


# ----------------------------------------------------------------------
# O REGISTRO DA MONTAGEM - arquivo proprio, e nao o das chapas
# ----------------------------------------------------------------------

def test_o_registro_da_montagem_e_um_arquivo_a_parte(tmp_path, monkeypatch):
    """
    O registro das chapas fechadas (_processados.json) responde outra
    pergunta: 'esta chapa ja foi para o CTP?'. Este responde 'este
    arquivo ja foi montado, e por quem?'. Misturar os dois faria a fila
    sumir com arquivo que so passou pelo CTP - e esconderia trabalho.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    assert montagem.caminho_do_registro() != utils.caminho_registro()
    assert montagem.caminho_do_registro().startswith(str(tmp_path))


def test_registro_que_nao_existe_ainda_le_vazio(tmp_path, monkeypatch):
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path / "nao existe"))
    assert montagem.carregar_montagens() == {}


def test_registro_estragado_nao_derruba_a_fila(tmp_path, monkeypatch):
    """
    JSON pela metade - a maquina desligada no meio de uma gravacao - nao
    pode virar tela de erro para a equipe inteira. Le vazio, e o pior que
    acontece e uma montagem ser oferecida duas vezes.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    with io.open(montagem.caminho_do_registro(), "w", encoding="utf-8") as f:
        f.write('{"x": ')
    assert montagem.carregar_montagens() == {}


def test_registro_que_nao_e_dicionario_le_vazio(tmp_path, monkeypatch):
    """
    JSON valido que nao e dicionario - um '[]' - passaria pelo json.load
    e estouraria la na frente, na hora de gravar, com outra cara.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    with io.open(montagem.caminho_do_registro(), "w", encoding="utf-8") as f:
        f.write("[]")

    assert montagem.carregar_montagens() == {}
    # e gravar em cima disso tem de funcionar, nao estourar
    arte = _pdf(str(tmp_path / "arte.pdf"))
    assert montagem.anotar_montagem(arte, {"quem": "Pedro"})
    assert montagem.ja_montado(arte) is True


def test_dois_programas_gravando_nao_emendam_o_registro(tmp_path,
                                                        monkeypatch):
    """
    O temporario tem o numero do processo no nome. Com nome fixo, dois
    programas gravando ao mesmo tempo escreveriam no MESMO arquivo e o
    renomeado sairia com dois JSON emendados - e ai o registro le vazio e
    TODA montagem ja feita volta para a fila.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    arte = _pdf(str(tmp_path / "arte.pdf"))

    vistos = []
    de_verdade = os.replace
    monkeypatch.setattr(os, "replace",
                        lambda a, b: vistos.append(a) or de_verdade(a, b))
    montagem.anotar_montagem(arte, {"quem": "Pedro"})

    assert str(os.getpid()) in vistos[0], vistos


def test_o_temporario_separa_ATE_duas_linhas_do_mesmo_processo(tmp_path,
                                                              monkeypatch):
    """
    O numero do processo NAO BASTA desde que a fila virou servidor: duas
    pessoas atualizando a tela ao mesmo tempo sao duas LINHAS do mesmo
    processo, com o mesmo numero. Escreveriam no mesmo temporario, e o
    renomeado sairia com dois JSON emendados - ai o registro le vazio e
    toda montagem ja feita volta para a fila.
    """
    import threading

    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    arte = _pdf(str(tmp_path / "arte.pdf"))

    vistos = []
    de_verdade = os.replace
    monkeypatch.setattr(os, "replace",
                        lambda a, b: vistos.append(a) or de_verdade(a, b))

    montagem.anotar_montagem(arte, {"quem": "Pedro"})
    daqui = vistos[0]
    assert str(os.getpid()) in daqui
    assert str(threading.get_ident()) in daqui

    def de_outra_linha():
        montagem.anotar_montagem(arte, {"quem": "Eudson"})

    linha = threading.Thread(target=de_outra_linha)
    linha.start()
    linha.join()
    assert vistos[-1] != daqui, \
        "duas linhas escreveram no MESMO temporario"


def test_duas_pessoas_montando_ao_mesmo_tempo_nao_se_apagam(tmp_path,
                                                            monkeypatch):
    """
    A equipe monta de PCs diferentes e o servidor atende as duas ao mesmo
    tempo. Quem gravasse por ultimo levaria o trabalho do outro - e o
    trabalho, aqui, e a decisao de gente sobre uma chapa.
    """
    import threading
    import time

    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))

    # a gravacao fica LENTA de proposito: sem tranca, uma linha le o
    # registro antes de a outra gravar, e a entrada da primeira se perde
    de_verdade = montagem._gravar_dicionario

    def devagar(caminho, dados):
        time.sleep(0.005)
        de_verdade(caminho, dados)

    monkeypatch.setattr(montagem, "_gravar_dicionario", devagar)

    artes = [_pdf(str(tmp_path / ("arte %d.pdf" % n)), b"x" * n)
             for n in range(1, 9)]
    linhas = [threading.Thread(target=montagem.anotar_montagem,
                               args=(a, {"quem": "quem montou %d" % n}))
              for n, a in enumerate(artes)]
    for t in linhas:
        t.start()
    for t in linhas:
        t.join()

    assert len(montagem.carregar_montagens()) == len(artes)


def test_duas_telas_medindo_ao_mesmo_tempo_nao_perdem_a_medida(portao,
                                                               monkeypatch):
    """
    Duas pessoas dando F5 juntas. Perdendo o retrato de uma delas, o
    Ghostscript roda de novo na proxima olhada - e a espera que esta fila
    veio acabar volta.
    """
    import threading
    import time

    dia, porta = portao
    for n in range(6):
        _pdf(str(porta / ("arte %d.pdf" % n)), b"x" * (n + 1))

    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (325.0, 430.0, set("CMYK")))
    de_verdade = montagem._gravar_dicionario

    def devagar(caminho, dados):
        time.sleep(0.005)
        de_verdade(caminho, dados)

    monkeypatch.setattr(montagem, "_gravar_dicionario", devagar)

    linhas = [threading.Thread(target=montagem.fila_medida) for _ in range(4)]
    for t in linhas:
        t.start()
    for t in linhas:
        t.join()

    guardadas = montagem._ler_dicionario(montagem.caminho_das_medidas())
    assert len(guardadas) == 6, \
        "retrato perdido: o Ghostscript vai rodar de novo"


def test_medir_nao_acontece_com_a_tranca_na_mao(portao, monkeypatch):
    """
    Medir custa SEGUNDOS de Ghostscript. Fazendo isso com a tranca na
    mao, a segunda pessoa que abrir a tela fica esperando a medicao da
    primeira - e a tela trava justamente quando ha mais trabalho.
    """
    import threading

    dia, porta = portao
    _pdf(str(porta / "arte.pdf"))

    livre = []

    def medir_olhando_a_tranca(pdf):
        # de OUTRA linha, porque a tranca e re-entrante: a propria linha
        # que a tem na mao consegue pega-la de novo e nao provaria nada
        def tentar():
            pegou = montagem._TRANCA.acquire(blocking=False)
            livre.append(pegou)
            if pegou:
                montagem._TRANCA.release()

        outra = threading.Thread(target=tentar)
        outra.start()
        outra.join()
        return 325.0, 430.0, set("CMYK")

    monkeypatch.setattr(montagem.america, "medir", medir_olhando_a_tranca)

    montagem.fila_medida()
    assert livre == [True], "a tranca ficou presa durante a medicao"


def test_ja_montado_pergunta_pela_chave_do_arquivo(tmp_path, monkeypatch):
    """
    A chave e a mesma dos outros seis clientes - nome|tamanho|data -, e e
    a que reconhece 'este arquivo aqui', e nao 'um arquivo com este
    nome'.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    arte = _pdf(str(tmp_path / "arte.pdf"))

    assert montagem.ja_montado(arte) is False
    montagem.anotar_montagem(arte, {"quem": "Pedro"})
    assert montagem.ja_montado(arte) is True


def test_o_registro_guarda_QUEM_montou(tmp_path, monkeypatch):
    """
    O nome e o que substitui a senha: e por ele que se sabe de quem foi a
    decisao quando a chapa sai errada.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    arte = _pdf(str(tmp_path / "arte.pdf"))

    montagem.anotar_montagem(arte, {"quem": "Pedro"})
    anotado = montagem.carregar_montagens()[montagem.chave_arquivo(arte)]
    assert anotado["quem"] == "Pedro"
    assert anotado["arquivo"] == "arte.pdf"
    assert anotado["quando"], "sem a hora nao da para contar a historia"


def test_anotar_uma_montagem_nao_apaga_a_outra(tmp_path, monkeypatch):
    """
    Duas pessoas montando ao mesmo tempo, de PCs diferentes: quem grava
    por ultimo nao pode levar o trabalho do outro. E a licao do
    salvar_registro, que ja custou uma chapa refeita.
    """
    from finart_ctp import utils
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path))
    uma = _pdf(str(tmp_path / "uma.pdf"), b"uma")
    outra = _pdf(str(tmp_path / "outra.pdf"), b"outra")

    montagem.anotar_montagem(uma, {"quem": "Pedro"})
    montagem.anotar_montagem(outra, {"quem": "Eudson"})

    tudo = montagem.carregar_montagens()
    assert len(tudo) == 2
    assert {e["quem"] for e in tudo.values()} == {"Pedro", "Eudson"}
