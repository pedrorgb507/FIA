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
import shutil

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
    Medir tinta e medir sangria rodam o Ghostscript, que custa segundos
    por arquivo. Aqui os dois devolvem numero combinado - o que se testa
    e o que a fila FAZ com a medida, e nao o Ghostscript.

    Quem testa a sangria poe o seu proprio ler_a_sangria por cima.
    """
    chamadas = []

    def medir(pdf):
        chamadas.append(pdf)
        return 325.0, 430.0, set("CMYK")

    monkeypatch.setattr(montagem.america, "medir", medir)
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(
                            _SANGRIA_CALADA, recado="(nao medido neste teste)"))
    return chamadas


# A forma que o sangria.ler_a_sangria devolve. Esta escrita aqui de
# proposito: quando ela mudar, os testes que a substituem quebram - e e
# assim que se descobre que a fila deixou de receber um campo.
_SANGRIA_CALADA = {"tem": None, "mm": None, "declarada": None,
                   "pela_tinta": None, "declarada_de": None,
                   "de_onde": None, "divergem": False, "recado": ""}


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


def test_a_fila_diz_se_o_arquivo_JA_VEIO_SANGRADO(portao, sem_ghostscript,
                                                  monkeypatch):
    """
    Para ninguem montar como se tivesse sangria o que nao tem. A fila
    carrega as DUAS leituras, e nao so a conclusao: e com elas que a tela
    fala quando as duas discordam.
    """
    dia, porta = portao
    _pdf(str(porta / "flyer.pdf"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(
                            _SANGRIA_CALADA, tem=True, mm=3.0, declarada=3.0,
                            pela_tinta=2.8, declarada_de="do BleedBox",
                            de_onde="as duas leituras concordam",
                            recado="tem sangria"))

    item = montagem.fila_medida()[0]
    assert item["sangria"] is True
    assert item["sangria_mm"] == 3.0
    assert item["sangria_declarada"] == 3.0
    assert item["sangria_pela_tinta"] == 2.8
    assert item["sangria_divergem"] is False


def test_sangria_que_NAO_SE_SABE_nao_vira_sem_sangria_na_fila(
        portao, sem_ghostscript, monkeypatch):
    """
    Arquivo sem TrimBox e sem marca de corte nao foi medido por ninguem.
    Virar False aqui faria a tela dizer 'nao veio sangrada' com a cara de
    quem mediu.
    """
    dia, porta = portao
    _pdf(str(porta / "sem caixa.pdf"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(
                            _SANGRIA_CALADA, recado="nao da para saber"))

    item = montagem.fila_medida()[0]
    assert item["sangria"] is None
    assert item["sangria_mm"] is None
    assert "nao da para saber" in item["sangria_recado"]


def test_a_DIVERGENCIA_da_sangria_sobe_na_fila(portao, sem_ghostscript,
                                               monkeypatch):
    """
    Quem mostra o recado e a tela, mas quem o carrega e a fila - se a
    divergencia se perdesse aqui, a tela nao teria o que dizer.
    """
    dia, porta = portao
    _pdf(str(porta / "mentiroso.pdf"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(
                            _SANGRIA_CALADA, declarada=3.0, pela_tinta=0.0,
                            mm=3.0, declarada_de="do BleedBox",
                            de_onde="as duas leituras discordam",
                            divergem=True,
                            recado="AS DUAS LEITURAS DISCORDAM"))

    item = montagem.fila_medida()[0]
    assert item["sangria_divergem"] is True
    assert item["sangria"] is None
    assert "DISCORDAM" in item["sangria_recado"]


def test_a_leitura_da_sangria_e_a_do_modulo_da_casa(portao, sem_ghostscript):
    """
    Uma conta so: a fila nao le caixa de PDF nem rasteriza por conta
    propria - ela pergunta ao sangria.py, o mesmo que o sangrar.py usa.
    """
    fonte = open(montagem.__file__, encoding="utf-8").read()
    assert "sangria.ler_a_sangria(" in fonte
    # o que se proibe e LER a caixa, e nao falar dela: o comentario que
    # conta a regra tem de poder nomear a TrimBox
    for proibido in (".trimbox", ".bleedbox", '"/TrimBox"', '"/BleedBox"',
                     ".mediabox"):
        assert proibido not in fonte, \
            "%s no montagem.py: a leitura de caixa mora no sangria.py" \
            % proibido


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


def test_retrato_de_uma_VERSAO_ANTIGA_e_medido_de_novo(portao,
                                                       sem_ghostscript):
    """
    A chave do retrato e do ARQUIVO - nome|tamanho|data -, e o arquivo
    nao muda quando o codigo muda. Sem a versao, o que ja estava no
    portao quando a sangria entrou na fila ficaria com 'nao da para
    saber' para sempre, sem ninguem entender por que.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "arte.pdf"))
    montagem.fila_medida()
    assert len(sem_ghostscript) == 1

    velho = montagem._ler_dicionario(montagem.caminho_das_medidas())
    chave = montagem.chave_arquivo(arte)
    velho[chave] = dict(velho[chave], versao=montagem.VERSAO_DA_MEDIDA - 1)
    velho[chave].pop("sangria", None)
    montagem._gravar_dicionario(montagem.caminho_das_medidas(), velho)

    item = montagem.fila_medida()[0]
    assert len(sem_ghostscript) == 2, "aproveitou retrato de versao velha"
    assert "sangria" in item


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
# O QUE O PAINEL RECEBE - e a copia em JavaScript que morre
# ----------------------------------------------------------------------
# O painel era pagina solta, e por isso carregava uma COPIA da tabela de
# formatos e das chapas em JavaScript. Servido, ele recebe as de verdade
# - e ai a tela e o vigia param de poder discordar.

def test_as_chapas_do_painel_saem_do_CONFIG():
    from finart_ctp.config import CHAPAS_AMERICA

    chapas = montagem.chapas_da_casa()
    assert len(chapas) == len(CHAPAS_AMERICA)
    for c in chapas:
        medida = (c["l"], c["a"])
        assert medida in CHAPAS_AMERICA, medida
        pinca, apelido = CHAPAS_AMERICA[medida]
        assert c["pinca"] == pinca
        assert c["id"] == apelido


def test_as_chapas_vem_da_menor_para_a_maior():
    """
    A ordem e a que o operador ve na tela, e a primeira e a que fica
    escolhida quando nao ha arquivo. Comecar pela maior faria a PM 52 -
    a chapa do dia a dia - ser a ultima.
    """
    chapas = montagem.chapas_da_casa()
    areas = [c["l"] * c["a"] for c in chapas]
    assert areas == sorted(areas)
    assert chapas[0]["id"] == "PM_52"


def test_o_preco_da_chapa_sai_do_GEREMPRE_e_nao_da_mao():
    """
    O painel soma o custo das chapas. O numero e o mesmo que a OS cobra -
    dois lugares com preco diferente e cliente cobrado errado.
    """
    from finart_ctp.config import GEREMPRE_CHAPAS

    for c in montagem.chapas_da_casa():
        _, _, preco, _ = GEREMPRE_CHAPAS[("AMERICA", (c["l"], c["a"]))]
        assert c["preco"] == preco


def test_os_formatos_do_painel_saem_do_CONFIG():
    from finart_ctp.config import FORMATOS_DA_CASA

    formatos = montagem.formatos_da_casa()
    assert len(formatos) == len(FORMATOS_DA_CASA)
    for numero, folhas in FORMATOS_DA_CASA.items():
        servidas = formatos[str(numero)]
        assert len(servidas) == len(folhas)
        for servida, (total, util) in zip(servidas, folhas):
            assert servida["total"] == list(total)
            assert servida["util"] == list(util)


def test_o_formato_4_continua_com_as_DUAS_folhas():
    """
    Um numero de formato pode ter mais de uma folha, e nao e erro de
    digitacao: o F-04 e 33x48 OU 24x66. Achatar isso faria o painel
    escolher por conta propria.
    """
    assert len(montagem.formatos_da_casa()["4"]) == 2
    assert len(montagem.formatos_da_casa()["6"]) == 3


def test_a_maquina_SUGERIDA_e_a_da_regra_da_casa():
    """
    Ate o formato 4 na PM 52; acima, colorido na SM 74 e preto-e-branco
    na MOZP. E a MESMA funcao que o vigia usa - nao ha uma regra da tela
    e outra da casa.
    """
    from finart_ctp import america

    pequeno = montagem.sugestoes_para(
        {"largura": 325.0, "altura": 430.0, "tintas": ["C", "M", "Y", "K"],
         "peb": False, "paginas": 1})
    assert pequeno["chapa"] == "PM_52"

    grande_cor = montagem.sugestoes_para(
        {"largura": 600.0, "altura": 700.0, "tintas": ["C", "M", "Y", "K"],
         "peb": False, "paginas": 1})
    assert grande_cor["chapa"] == "SM_74"

    grande_pb = montagem.sugestoes_para(
        {"largura": 600.0, "altura": 700.0, "tintas": ["K"], "peb": True,
         "paginas": 1})
    assert grande_pb["chapa"] == "MOZP_FT2"

    # e a regra e literalmente a do america.py
    assert america.maquina_da_america(700.0, {"K"}) == (650, 550)


def test_a_cor_sugerida_sai_das_TINTAS_que_se_mediram():
    """O painel tem tres fichas de cor, e a medida decide qual."""
    assert montagem.sugestoes_para({"peb": True, "tintas": ["K"]})["cor"] \
        == "PB"
    assert montagem.sugestoes_para(
        {"peb": False, "tintas": ["C", "K"]})["cor"] == "2"
    assert montagem.sugestoes_para(
        {"peb": False, "tintas": ["C", "M", "Y", "K"]})["cor"] == "CMYK"


def test_o_numero_de_PAGINAS_vira_sugestao_de_tipo():
    """
    Pagina nao tem campo no painel - ela vira sugestao de tipo, que e o
    unico lugar onde essa medida muda uma decisao. Uma pagina nao tem
    verso; duas tem frente e verso, e na MESMA chapa (ver o teste do
    bate-vira mais abaixo). Tres ou mais nao se adivinha.
    """
    assert montagem.sugestoes_para({"paginas": 1})["tipo"] == "so-frente"
    assert montagem.sugestoes_para({"paginas": 5})["tipo"] is None


def test_sem_medida_nao_se_sugere_NADA():
    """
    Arquivo que nao deu para medir nao pode ganhar sugestao inventada -
    seria a tela escolhendo chapa por conta propria.
    """
    nada = montagem.sugestoes_para({"largura": None, "altura": None,
                                    "tintas": [], "peb": None,
                                    "paginas": None})
    assert nada["chapa"] is None
    assert nada["cor"] is None
    assert nada["tipo"] is None


def test_os_dados_do_painel_trazem_o_arquivo_ESCOLHIDO(portao,
                                                       sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"), paginas=2)
    _pdf(str(porta / "outro.pdf"))

    dados = montagem.dados_do_painel("convite.pdf")
    assert dados["arquivo"]["arquivo"] == "convite.pdf"
    assert dados["arquivo"]["paginas"] == 2
    assert dados["arquivo"]["sugestao"]["chapa"] == "PM_52"
    # e as tabelas da casa vem junto, que e o ponto do ticket
    assert dados["formatos"]["4"]
    assert dados["clientes"]["AMERICA"]["chapas"]


def test_arquivo_que_nao_esta_na_FILA_nao_abre_o_painel(portao,
                                                        sem_ghostscript):
    """
    So se monta o que esta esperando montagem. E isto tambem e o que
    impede um nome vindo de fora de virar caminho para outra pasta.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    _pdf(str(dia / "fora do portao.pdf"))

    assert montagem.dados_do_painel("fora do portao.pdf")["arquivo"] is None
    assert montagem.dados_do_painel(r"..\..\segredo.pdf")["arquivo"] is None
    assert montagem.dados_do_painel("nem existe.pdf")["arquivo"] is None


def test_o_painel_abre_SEM_arquivo_e_ainda_serve_as_tabelas(portao,
                                                            sem_ghostscript):
    """O painel continua servindo para conferir uma montagem no vazio."""
    dados = montagem.dados_do_painel(None)
    assert dados["arquivo"] is None
    assert dados["formatos"] and dados["clientes"]


def test_o_TAMANHO_pre_preenchido_e_o_do_CORTE_e_nao_o_do_PAPEL(
        portao, monkeypatch):
    """
    O campo do painel e a PECA, e a sangria entra separada. Preenchendo
    com a medida do papel, a sangria seria contada duas vezes - e a peca
    sairia 6 mm maior do que o cliente pediu.
    """
    dia, porta = portao
    _pdf(str(porta / "com sangria.pdf"))
    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (106.0, 156.0, set("CMYK")))
    monkeypatch.setattr(montagem.sangria, "medida_do_corte",
                        lambda pdf, pagina=1: (100.0, 150.0, "da TrimBox"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(_SANGRIA_CALADA))

    escolhido = montagem.dados_do_painel("com sangria.pdf")["arquivo"]
    assert (escolhido["corte_largura"], escolhido["corte_altura"]) == \
        (100.0, 150.0)
    # e a medida do papel nao se perde: ela e que casa com a chapa
    assert (escolhido["largura"], escolhido["altura"]) == (106.0, 156.0)


def test_sem_TRIMBOX_a_peca_sai_do_papel_MENOS_a_sangria(portao, monkeypatch):
    """
    O arquivo nao declara corte, mas a tinta mediu 3 mm de sangria. Papel
    de 106x156 com 3 mm por lado E uma peca de 100x150 - nao e chute, e a
    definicao.

    Preenchendo a peca com 106x156 e ainda somando a sangria no campo de
    sangria, ela seria contada DUAS VEZES: a peca sairia 6 mm maior do
    que o cliente pediu, e o corte cairia dentro do desenho.
    """
    dia, porta = portao
    _pdf(str(porta / "sem caixa.pdf"))
    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (106.0, 156.0, set("CMYK")))
    monkeypatch.setattr(
        montagem.sangria, "medida_do_corte",
        lambda pdf, pagina=1: (106.0, 156.0,
                               "do MediaBox - o arquivo nao declara corte"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(
                            _SANGRIA_CALADA, tem=True, mm=3.0,
                            pela_tinta=3.0, de_onde="da tinta"))

    escolhido = montagem.dados_do_painel("sem caixa.pdf")["arquivo"]
    assert (escolhido["corte_largura"], escolhido["corte_altura"]) == \
        (100.0, 150.0)
    assert "sangria medida" in escolhido["corte_de"]


def test_sem_TRIMBOX_e_sem_sangria_a_peca_fica_o_papel_e_isso_vem_DITO(
        portao, monkeypatch):
    """
    Nao se sabe o corte nem a sangria. Ai a peca fica sendo o papel - e o
    que ha - mas o painel tem de DIZER, para quem monta conferir a
    medida em vez de confiar nela.
    """
    dia, porta = portao
    _pdf(str(porta / "nada.pdf"))
    monkeypatch.setattr(montagem.america, "medir",
                        lambda p: (106.0, 156.0, set("CMYK")))
    monkeypatch.setattr(
        montagem.sangria, "medida_do_corte",
        lambda pdf, pagina=1: (106.0, 156.0,
                               "do MediaBox - o arquivo nao declara corte"))
    monkeypatch.setattr(montagem.sangria, "ler_a_sangria",
                        lambda pdf, pagina=1: dict(_SANGRIA_CALADA))

    escolhido = montagem.dados_do_painel("nada.pdf")["arquivo"]
    assert (escolhido["corte_largura"], escolhido["corte_altura"]) == \
        (106.0, 156.0)
    assert "nao declara corte" in escolhido["corte_de"]


def test_TRES_TINTAS_nao_ganham_sugestao_de_cor(portao, sem_ghostscript):
    """
    O painel tem tres fichas de cor - CMYK (4 chapas), preto e branco (1)
    e duas cores (2). Um trabalho de TRES tintas nao tem ficha: sugerir
    CMYK cobraria uma chapa a mais, e sugerir 'duas cores' cobraria uma a
    menos. Sem ficha certa, quem escolhe e gente.
    """
    assert montagem.sugestoes_para(
        {"peb": False, "tintas": ["C", "K", "M"]})["cor"] is None
    # e a fila continua mostrando o que mediu, para a pessoa ver por que
    assert montagem.sugestoes_para(
        {"peb": False, "tintas": ["C", "M", "Y", "K"]})["cor"] == "CMYK"


# ----------------------------------------------------------------------
# O BOTAO MONTA DE VERDADE - a ordem executada
# ----------------------------------------------------------------------
# Tudo que a tela coletou vira UMA ordem, e uma funcao recebe esse objeto
# e faz o trabalho. E o seam da spec: se prova o que a funcao faz com a
# ordem, e nao que uma funcao chamou outra.
#
# O MOTOR DE IMPOSICAO E SUBSTITUIDO aqui - ele ja tem prova propria em
# test_imposicao_grade.py, com pixel e tudo. O que estes testes seguram e
# a ORDEM DOS PASSOS e as tres travas, que e onde mora o prejuizo.

def _ordem(**o):
    """Uma ordem de montagem completa, do jeito que a tela a monta."""
    base = {"arquivo": "convite.pdf", "chapa": "PM_52",
            "imagens_frente": 2, "imagens_verso": 2,
            "colunas": 2, "linhas": 2, "vao": 5.0, "sangria": 2.5,
            "formato": 4, "folha": 0, "tipo": "bate-vira",
            "quem": "Pedro", "maquina_trocada": None,
            "liberado_sem_caber": False}
    base.update(o)
    return base


@pytest.fixture
def motor(monkeypatch, tmp_path):
    """
    O motor de imposicao substituido: grava um PDF de mentira no destino
    e guarda o que recebeu, para os testes lerem.
    """
    recebido = {}

    class _Chapa(object):
        """A forma que o motor le - a medida vem do config."""

        def __init__(self, larg, alt, pinca):
            self.larg, self.alt, self.pinca = larg, alt, pinca

    class DeMentira(object):
        # nome diferente do de fora: 'Chapa = Chapa' num corpo de classe
        # torna o nome local e a leitura da direita falha
        Chapa = _Chapa

        @staticmethod
        def nome_da_montagem(origem):
            base, ext = os.path.splitext(os.path.basename(origem))
            return "%s_MONTAGEM%s" % (base, ext or ".pdf")

        @staticmethod
        def montar(origem, destino, **k):
            recebido["origem"] = origem
            recebido["destino"] = destino
            recebido.update(k)
            _pdf(destino, b"a montagem")
            return {"montagem": (200.0, 300.0), "cols": k.get("cols"),
                    "rows": k.get("rows"), "estourou": False}

    monkeypatch.setattr(montagem, "_motor", lambda: DeMentira)
    # a pinca do arquivo que SAIU - medida de verdade no fechamento, e
    # substituida aqui. O caso de ela nao conferir tem teste proprio.
    monkeypatch.setattr(montagem.america, "medir_o_pe",
                        lambda pdf: (60.0, 60.0, 300.0))
    return recebido


def test_montar_pela_tela_grava_na_PASTA_DO_DIA_com_o_sufixo(portao, motor,
                                                             sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    r = montagem.executar(_ordem())

    assert r["feito"] is True, r["porque"]
    assert os.path.basename(r["montagem"]) == "convite_MONTAGEM.pdf"
    assert os.path.dirname(r["montagem"]) == str(dia)
    assert os.path.exists(r["montagem"])


def test_a_montagem_NUNCA_vai_para_a_PARA_CTP(portao, motor, sem_ghostscript):
    """
    TRAVA 1, e ela e o eixo do processo: escrever no portao de saida
    pularia a revisao, e a mudanca de pasta E o 'aprovado'. O vigia
    pegaria na volta seguinte e mandaria para o CTP uma montagem que
    ninguem olhou.
    """
    dia, porta = portao
    (dia / "PARA CTP").mkdir()
    _pdf(str(porta / "convite.pdf"))

    r = montagem.executar(_ordem())

    assert "para ctp" not in r["montagem"].lower()
    assert os.listdir(str(dia / "PARA CTP")) == []


def test_o_ORIGINAL_sai_do_portao_e_NAO_e_apagado(portao, motor,
                                                  sem_ghostscript):
    """
    TRAVA 3: ficando os dois no portao, a volta seguinte do vigia acharia
    DUAS chapas do mesmo servico - duas gravacoes e duas OS. E o original
    e a FONTE da montagem: apagar nao esta combinado com ninguem.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"), b"o original")

    montagem.executar(_ordem())

    assert not os.path.exists(str(porta / "convite.pdf")), \
        "o original ficou no portao"
    guardado = str(dia / "convite.pdf")
    assert os.path.exists(guardado), "o original foi APAGADO"
    assert b"o original" in io.open(guardado, "rb").read()


def test_a_pinca_e_medida_NO_ARQUIVO_QUE_SAIU(portao, motor, monkeypatch,
                                              sem_ghostscript):
    """
    TRAVA 2: entre escrever a matriz de deslocamento no PDF e ela valer ha
    um programa inteiro. A conta pode estar certa e o arquivo sair errado.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    medidos = []
    monkeypatch.setattr(montagem.america, "medir_o_pe",
                        lambda pdf: medidos.append(pdf) or (60.0, 60.0, 300.0))

    r = montagem.executar(_ordem())

    assert medidos == [r["montagem"]], \
        "mediu %r, e tinha de medir a montagem que saiu" % medidos


def test_montagem_que_NAO_CONFERE_a_pinca_e_APAGADA_e_o_servico_PARA(
        portao, motor, monkeypatch, sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    # o desenho saiu encostado no pe: a maquina segura a folha ali
    monkeypatch.setattr(montagem.america, "medir_o_pe",
                        lambda pdf: (2.0, 2.0, 300.0))

    r = montagem.executar(_ordem())

    assert r["feito"] is False
    assert "pinca" in r["porque"].lower()
    assert not os.path.exists(str(dia / "convite_MONTAGEM.pdf")), \
        "a montagem que nao confere ficou no disco"
    # e o original NAO saiu do portao: o servico nao andou
    assert os.path.exists(str(porta / "convite.pdf"))


def test_nao_conseguindo_MEDIR_a_pinca_o_servico_tambem_PARA(
        portao, motor, monkeypatch, sem_ghostscript):
    """
    'Nao consegui medir' nao e 'esta boa'. Sem pinca nao vai para o CTP,
    e a trava so vale se ela tambem valer quando a medida falha.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    monkeypatch.setattr(montagem.america, "medir_o_pe",
                        lambda pdf: (None, None, None))

    r = montagem.executar(_ordem())
    assert r["feito"] is False
    assert not os.path.exists(str(dia / "convite_MONTAGEM.pdf"))


def test_QUEM_MONTOU_fica_gravado_com_data(portao, motor, sem_ghostscript):
    """
    E o nome que substitui a senha: quando sair chapa errada, saber quem
    decidiu e como a regra nasce.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "convite.pdf"))
    chave = montagem.chave_arquivo(arte)

    montagem.executar(_ordem(quem="Eudson"))

    anotado = montagem.carregar_montagens()[chave]
    assert anotado["quem"] == "Eudson"
    assert anotado["quando"]
    assert anotado["montagem"] == "convite_MONTAGEM.pdf"
    assert anotado["chapa"] == "PM_52"


def test_a_MAQUINA_TROCADA_fora_da_regra_fica_gravada(portao, motor,
                                                      sem_ghostscript):
    """
    O operador disse 'geralmente', e e justamente fora do geralmente que
    a proxima regra da casa nasce - por isso a troca e registrada.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "convite.pdf"))
    chave = montagem.chave_arquivo(arte)      # antes de ele sair do portao

    montagem.executar(_ordem(chapa="SM_74",
                             maquina_trocada="a regra dava PM_52"))

    anotado = montagem.carregar_montagens()[chave]
    assert anotado["maquina_trocada"] == "a regra dava PM_52"
    assert anotado["chapa"] == "SM_74"


def test_montagem_JA_FEITA_nao_e_refeita(portao, motor, sem_ghostscript):
    """
    Refazer poria duas montagens do mesmo servico na pasta do dia, e
    alguem revisaria as duas.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    assert montagem.executar(_ordem())["feito"] is True

    # o arquivo ja saiu do portao, mas ainda assim: pedir de novo recusa
    de_novo = montagem.executar(_ordem())
    assert de_novo["feito"] is False
    assert "ja" in de_novo["porque"].lower()


def test_arquivo_que_nao_esta_na_FILA_nao_se_monta(portao, motor,
                                                   sem_ghostscript):
    dia, porta = portao
    _pdf(str(dia / "fora do portao.pdf"))
    r = montagem.executar(_ordem(arquivo="fora do portao.pdf"))
    assert r["feito"] is False
    assert "fila" in r["porque"].lower()


def test_o_que_JA_PARAVA_continua_parando(portao, motor, monkeypatch,
                                          sem_ghostscript):
    """
    Arte que so cabe deitada e arte que nao cabe em chapa nenhuma param -
    e o motor as para levantando SystemExit, que NAO e Exception e
    passaria direto por um 'except Exception:'. Escapando dali, ela
    derrubaria a linha que atende o pedido.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    def nao_cabe(origem, destino, **k):
        raise SystemExit("PAREI - nao cabe no UTIL DA CHAPA")

    de_antes = montagem._motor()

    monkeypatch.setattr(montagem, "_motor",
                        lambda: type("X", (), {
                            "Chapa": de_antes.Chapa,
                            "montar": staticmethod(nao_cabe),
                            "nome_da_montagem": staticmethod(
                                lambda o: "x_MONTAGEM.pdf")}))

    r = montagem.executar(_ordem())
    assert r["feito"] is False
    assert "nao cabe" in r["porque"].lower()
    # nada andou: o original continua no portao e nada foi registrado
    assert os.path.exists(str(porta / "convite.pdf"))
    assert montagem.carregar_montagens() == {}


def test_a_ordem_CHEGA_INTEIRA_no_motor(portao, motor, sem_ghostscript):
    """
    A grade, o vao, o tipo, o formato e a folha sao decisao de gente, e o
    motor tem de receber exatamente o que a tela coletou.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    montagem.executar(_ordem(colunas=3, linhas=2, vao=3.0, sangria=1.5,
                             formato=6, folha=2, tipo="so-frente",
                             imagens_frente=6, imagens_verso=0))

    assert motor["cols"] == 3 and motor["rows"] == 2
    assert motor["vao"] == 3.0
    assert motor["sangria"] == 1.5
    assert motor["formato"] == 6 and motor["folha"] == 2
    assert motor["tipo"] == "so-frente"
    assert (motor["chapa"].larg, motor["chapa"].alt) == (525.0, 459.0)


def test_FRENTE_E_VERSO_e_recusado_com_o_motivo(portao, motor,
                                                sem_ghostscript):
    """
    Sao DUAS chapas, uma por lado, e o nome de cada arquivo de saida e
    combinado da casa que ninguem deu. A tela oferecia esse tipo, sugeria
    ele sozinho para todo arquivo de duas paginas, e o botao FALHAVA a
    cada clique - com um recado do motor que ninguem entenderia.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    r = montagem.executar(_ordem(tipo="frente-verso"))
    assert r["feito"] is False
    assert "duas chapas" in r["porque"]
    assert "bate-vira" in r["porque"], "tem de dizer o que fazer no lugar"
    assert motor == {}, "chegou a chamar o motor para um tipo que ele recusa"


def test_duas_paginas_sugerem_BATE_VIRA_que_o_motor_sabe_montar():
    """
    As duas poem frente e verso na chapa; a diferenca e que o bate-vira
    usa UMA chapa, partida ao meio. Sugerir o que falha no clique do
    botao e pior que nao sugerir nada.
    """
    assert montagem.sugestoes_para({"paginas": 2})["tipo"] == "bate-vira"


def test_CELULA_VAZIA_e_recusada_porque_o_motor_enche_todas(portao, motor,
                                                            sem_ghostscript):
    """
    O painel avisa que sobra celula e diz que branco na chapa e decisao
    de quem monta. So que quem faria o branco seria o motor, e ele repete
    a arte em TODAS as celulas: a chapa sairia com arte onde a tela
    mostrou vazio.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    r = montagem.executar(_ordem(tipo="so-frente", imagens_frente=3,
                                 imagens_verso=0, colunas=2, linhas=2))
    assert r["feito"] is False
    assert "4 celulas" in r["porque"] and "3 imagens" in r["porque"]
    assert motor == {}


def test_o_ENCONTRO_escolhido_chega_ao_motor(portao, motor, sem_ghostscript):
    """
    Cabeca com cabeca ou pe com pe e o GIRO de cada peca na chapa, e nao
    um rotulo. Quem aprova a montagem aprova o desenho que a tela mostrou
    - e sem isto a chapa saia sempre cabeca com cabeca.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    montagem.executar(_ordem(encontro="pe"))
    assert motor["encontro"] == "pe"


def test_as_TRES_MARCAS_escolhidas_chegam_ao_motor(portao, motor,
                                                   sem_ghostscript):
    """
    As caixinhas ja existiam na tela e nao chegavam na montagem:
    desmarcar 'escala de cor' num trabalho de uma cor no preto nao fazia
    efeito nenhum.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    montagem.executar(_ordem(marca_de_corte=True, marca_de_registro=False,
                             escala_de_cor=False))
    assert motor["marca_de_corte"] is True
    assert motor["marca_de_registro"] is False
    assert motor["escala_de_cor"] is False


def test_DUAS_PESSOAS_montando_o_mesmo_arquivo_nao_se_atropelam(
        portao, motor, monkeypatch, sem_ghostscript):
    """
    O servidor existe justamente para haver duas, e montar leva SEGUNDOS.
    Sem reserva, as duas passam pelas guardas, as duas escrevem o mesmo
    destino, e a segunda tropeca ao tirar do portao um arquivo que a
    primeira ja tirou.
    """
    import threading

    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    entrou = threading.Event()
    pode_seguir = threading.Event()
    de_antes = montagem._motor()

    def devagar(origem, destino, **k):
        entrou.set()
        pode_seguir.wait(5)
        _pdf(destino, b"a montagem")
        return {}

    monkeypatch.setattr(montagem, "_motor",
                        lambda: type("X", (), {
                            "Chapa": de_antes.Chapa,
                            "montar": staticmethod(devagar),
                            "nome_da_montagem": staticmethod(
                                de_antes.nome_da_montagem)}))

    primeira = {}
    linha = threading.Thread(
        target=lambda: primeira.update(montagem.executar(_ordem())))
    linha.start()
    entrou.wait(5)

    segunda = montagem.executar(_ordem(quem="Eudson"))
    pode_seguir.set()
    linha.join(10)

    assert segunda["feito"] is False
    assert "outra pessoa" in segunda["porque"]
    assert primeira["feito"] is True, primeira.get("porque")


def test_cada_montagem_tem_a_PROPRIA_pasta_temporaria(portao, motor,
                                                       sem_ghostscript):
    """
    O motor escreve com nomes FIXOS na pasta temporaria - _p0.pdf, _m.pdf,
    _r.pdf. Duas pessoas montando arquivos DIFERENTES ao mesmo tempo (que
    e para isso que o servidor existe) escreveriam nos mesmos arquivos, e
    o pypdf le essas paginas na hora de gravar: uma chapa sairia com a
    arte da outra, ou com a grade de corte da outra.

    A reserva por arquivo nao alcanca isso - ela guarda o MESMO arquivo
    de ser montado duas vezes, e aqui os arquivos sao outros.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    montagem.executar(_ordem())

    assert motor["tmp"], "o motor foi chamado sem pasta temporaria propria"
    assert "convite" in motor["tmp"] or os.path.basename(motor["tmp"]), \
        motor["tmp"]
    # e ela some depois: montar dezenas por dia nao pode encher o disco
    assert not os.path.exists(motor["tmp"]), \
        "a pasta temporaria ficou para tras"


def test_duas_montagens_SEGUIDAS_nao_dividem_a_pasta_temporaria(
        portao, motor, sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "um.pdf"))
    _pdf(str(porta / "dois.pdf"))

    montagem.executar(_ordem(arquivo="um.pdf"))
    primeira = motor["tmp"]
    montagem.executar(_ordem(arquivo="dois.pdf"))

    assert motor["tmp"] != primeira, \
        "as duas montagens usaram a mesma pasta temporaria"


def test_bate_vira_conta_as_celulas_de_CADA_METADE(portao, motor,
                                                   sem_ghostscript):
    """
    O bate-vira parte a chapa ao meio: a metade esquerda e a frente e a
    direita e o verso. Somando os dois lados, 3 na frente e 1 no verso
    numa grade de 4 'fecha a conta' - mas a frente so tem DUAS celulas, e
    a terceira imagem nao tem onde entrar. A tela ja desenha isso certo;
    era a conta daqui que somava errado.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))

    r = montagem.executar(_ordem(tipo="bate-vira", imagens_frente=3,
                                 imagens_verso=1, colunas=2, linhas=2))
    assert r["feito"] is False
    assert "metade" in r["porque"].lower(), r["porque"]
    assert motor == {}


def test_bate_vira_com_as_duas_metades_CHEIAS_monta(portao, motor,
                                                    sem_ghostscript):
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    r = montagem.executar(_ordem(tipo="bate-vira", imagens_frente=2,
                                 imagens_verso=2, colunas=2, linhas=2))
    assert r["feito"] is True, r["porque"]


def test_registro_que_NAO_GRAVOU_nao_passa_por_montagem_feita(
        portao, motor, monkeypatch, sem_ghostscript):
    """
    A montagem esta no disco e o original ja saiu do portao. Sem o
    registro, ela fica sem dono e sem data - e ninguem sabe que ela foi
    feita. Dizer 'feito' calado esconderia justamente isso.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    monkeypatch.setattr(montagem, "anotar_montagem",
                        lambda *a, **k: None)

    r = montagem.executar(_ordem())

    assert r["atencao"], "a gravacao do registro falhou e ninguem foi avisado"
    assert "registro" in r["atencao"].lower()


def test_montagem_ANTERIOR_com_o_mesmo_nome_nao_e_jogada_fora(
        portao, motor, sem_ghostscript):
    """
    Acontece quando a AMERICA manda o arquivo corrigido com o mesmo nome.
    A antiga pode ter sido aprovada, ou estar no meio de uma revisao - e
    a mesma decisao do guardar_copia: sai de lado com a data.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    _pdf(str(dia / "convite_MONTAGEM.pdf"), b"a montagem de antes")

    r = montagem.executar(_ordem())

    assert r["feito"] is True, r["porque"]
    de_lado = [f for f in os.listdir(str(dia)) if "anterior" in f]
    assert len(de_lado) == 1, os.listdir(str(dia))
    assert b"a montagem de antes" in io.open(str(dia / de_lado[0]),
                                             "rb").read()


def test_faxina_que_falha_GRITA_e_nao_so_anota(portao, motor, monkeypatch,
                                               sem_ghostscript):
    """
    A montagem esta feita e conferida - anotar e o certo, e a licao das
    tres folhas de papel. Mas o arquivo fica no portao E some da fila
    (ja esta anotado): sem um recado alto, ele fica la sem ninguem
    olhando.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    monkeypatch.setattr(montagem.america, "chegou_inteira",
                        lambda a, b: (False, "tamanho diferente"))

    r = montagem.executar(_ordem())

    assert r["feito"] is True, "a montagem FOI feita e conferida"
    assert r["atencao"], "a faxina falhou e ninguem foi avisado"
    assert "TIRE A MAO" in r["atencao"]
    assert os.path.exists(str(porta / "convite.pdf"))


def test_nome_montado_em_OUTRO_DIA_nao_barra_o_arquivo_de_hoje(portao,
                                                               sem_ghostscript):
    """
    'CARTAZ.pdf' montado ha duas semanas nao diz nada sobre o 'CARTAZ.pdf'
    que chegou hoje. Barrando pelo nome, arquivo novo ganharia 'ja foi
    montado' e a pessoa iria procurar um defeito que nao existe.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "CARTAZ.pdf"))
    montagem.anotar_montagem(arte, {"quem": "Pedro",
                                    "montagem": "CARTAZ_MONTAGEM.pdf"},
                             chave="de outro dia")

    # a montagem daquele dia nao esta na pasta de hoje
    assert montagem.ja_montado_por_nome("CARTAZ.pdf", str(dia)) is False

    _pdf(str(dia / "CARTAZ_MONTAGEM.pdf"))
    assert montagem.ja_montado_por_nome("CARTAZ.pdf", str(dia)) is True


def test_ordem_sem_QUEM_nao_monta(portao, motor, sem_ghostscript):
    """
    O nome e o que responde de quem foi a decisao quando sair chapa
    errada - e foi ele que substituiu a senha. Montar sem nome seria
    gravar uma decisao de ninguem.
    """
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    r = montagem.executar(_ordem(quem="  "))
    assert r["feito"] is False
    assert "nome" in r["porque"].lower()


# ----------------------------------------------------------------------
# LIBERAR O QUE NAO CABE - com nome, e sem subir para o operador
# ----------------------------------------------------------------------
# Decisao fechada da equipe, e do operador CONTRA a recomendacao de
# escalar: qualquer um libera, o caso nao vai para ele, e o que segura a
# coisa e o NOME ficar gravado. Quem recebe o papel sabe que foi decisao
# de alguem - e agora sabe de quem.

@pytest.fixture
def motor_que_nao_cabe(monkeypatch, motor):
    """
    O motor devolvendo os estouros que ele mediu - e e dele que sai o
    MOTIVO, com numero, e nao de uma frase remontada aqui.
    """
    de_antes = montagem._motor()
    estouros = [
        "nao cabe no UTIL DA CHAPA: a montagem da 600.0 x 500.0 e o util "
        "e 525.0 x 399.0 (chapa 525 x 459 menos a pinca 60)",
        "nao cabe no FORMATO 4: a montagem da 600.0 x 500.0 e a area util "
        "da folha e 315 x 460 (folha 330 x 480)"]

    def montar_estourando(origem, destino, **k):
        motor.update(k)
        motor["destino"] = destino
        if not k.get("assim_mesmo"):
            raise SystemExit("PAREI - " + "; e ".join(estouros)
                             + ". Se for para tocar assim mesmo, mande de "
                               "novo com --assim-mesmo.")
        _pdf(destino, b"a montagem que estoura")
        return {"estourou": True, "estouros": estouros,
                "cabe_util": False, "cabe_formato": False}

    monkeypatch.setattr(montagem, "_motor",
                        lambda: type("X", (), {
                            "Chapa": de_antes.Chapa,
                            "montar": staticmethod(montar_estourando),
                            "nome_da_montagem": staticmethod(
                                de_antes.nome_da_montagem)}))
    return estouros


def test_sem_liberar_a_montagem_que_nao_cabe_PARA(portao, motor_que_nao_cabe,
                                                  sem_ghostscript):
    """O aviso vem com a pergunta junto, e quem responde e gente."""
    dia, porta = portao
    _pdf(str(porta / "cartaz.pdf"))

    r = montagem.executar(_ordem(arquivo="cartaz.pdf",
                                liberado_sem_caber=False))
    assert r["feito"] is False
    assert "nao cabe" in r["porque"].lower()
    assert montagem.carregar_montagens() == {}


def test_LIBERADA_a_montagem_sai_e_fica_gravada_com_NOME_E_MOTIVO(
        portao, motor_que_nao_cabe, sem_ghostscript):
    """
    O checkbox do ticket, com os dois limites estourados de uma vez. O
    motivo tem de vir com NUMERO: 'nao coube' sozinho nao ensina nada a
    quem for olhar o historico depois.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "cartaz.pdf"))
    chave = montagem.chave_arquivo(arte)

    r = montagem.executar(_ordem(arquivo="cartaz.pdf", quem="Eudson",
                                liberado_sem_caber=True))

    assert r["feito"] is True, r["porque"]
    anotado = montagem.carregar_montagens()[chave]
    assert anotado["liberado_sem_caber"] is True
    assert anotado["liberado_por"] == "Eudson"
    assert anotado["liberado_porque"] == motor_que_nao_cabe


def test_o_motivo_gravado_diz_QUAL_DOS_DOIS_limites_estourou(
        portao, motor_que_nao_cabe, sem_ghostscript):
    """
    Area util e da CHAPA - o que a gravadora alcanca, tirada a pinca.
    Formato e da FOLHA - o que a impressora pega. Sao limites diferentes
    e e facil confundir; o registro tem de dizer qual foi.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "cartaz.pdf"))
    chave = montagem.chave_arquivo(arte)

    montagem.executar(_ordem(arquivo="cartaz.pdf",
                             liberado_sem_caber=True))

    motivos = " ".join(montagem.carregar_montagens()[chave]["liberado_porque"])
    assert "UTIL DA CHAPA" in motivos
    assert "FORMATO" in motivos
    assert "525.0 x 399.0" in motivos, "sem numero nao se aprende nada"


def test_liberar_SEM_NOME_nao_monta(portao, motor_que_nao_cabe,
                                    sem_ghostscript):
    """
    E o nome que faz a liberacao ser decisao de alguem em vez de
    descuido de ninguem. Sem ele, liberar nao vale.
    """
    dia, porta = portao
    _pdf(str(porta / "cartaz.pdf"))
    r = montagem.executar(_ordem(arquivo="cartaz.pdf", quem="",
                                 liberado_sem_caber=True))
    assert r["feito"] is False
    assert "nome" in r["porque"].lower()


def test_montagem_que_CABE_nao_fica_marcada_como_liberada(portao, motor,
                                                          sem_ghostscript):
    """
    O 'pode ir' so vale quando ha o que liberar. Marcar tudo como
    liberado encheria o historico de ruido e esconderia os casos de
    verdade - que sao justamente os que ensinam a proxima regra.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "convite.pdf"))
    chave = montagem.chave_arquivo(arte)

    montagem.executar(_ordem(liberado_sem_caber=True))

    anotado = montagem.carregar_montagens()[chave]
    assert anotado["liberado_sem_caber"] is False, \
        "coube, e mesmo assim ficou marcada como liberada"
    assert anotado["liberado_por"] is None


def test_liberar_NAO_VIRA_PENDENCIA_para_o_operador(portao,
                                                    motor_que_nao_cabe,
                                                    monkeypatch,
                                                    sem_ghostscript):
    """
    Decisao do operador CONTRA a recomendacao de escalar: o caso fica
    fechado na equipe e aparece no historico, quando ELE escolher olhar.
    Pendencia e tela cheia sao para o que esta errado e precisa de alguem
    agora - e isto foi decidido por gente, de proposito.
    """
    dia, porta = portao
    _pdf(str(porta / "cartaz.pdf"))

    monkeypatch.setattr(montagem.utils, "anotar_pendencia",
                        lambda *a, **k: pytest.fail("virou pendencia"))
    gritos = []
    monkeypatch.setattr(montagem.utils, "log",
                        lambda msg, alerta=False: gritos.append(alerta))

    assert montagem.executar(_ordem(arquivo="cartaz.pdf",
                                    liberado_sem_caber=True))["feito"] is True
    assert not any(gritos), "subiu alerta no log por uma decisao de gente"


def test_a_liberacao_fica_no_LOG_DO_DIA_sem_gritar(portao,
                                                   motor_que_nao_cabe,
                                                   monkeypatch,
                                                   sem_ghostscript):
    """
    Nao gritar nao e esconder: a linha do dia continua contando o que
    houve, para quem ler o log saber sem ser interrompido.
    """
    dia, porta = portao
    _pdf(str(porta / "cartaz.pdf"))

    ditos = []
    monkeypatch.setattr(montagem.utils, "log",
                        lambda msg, alerta=False: ditos.append(msg))

    montagem.executar(_ordem(arquivo="cartaz.pdf", quem="Eudson",
                             liberado_sem_caber=True))

    liberou = [m for m in ditos if "liberou" in m.lower()]
    assert liberou, "o log do dia nao conta que alguem liberou: %r" % ditos
    assert "Eudson" in liberou[0]


# ----------------------------------------------------------------------
# A REVISAO - aprovar e mandar para a PARA CTP
# ----------------------------------------------------------------------
# A montagem gravada precisa de olho humano antes de virar chapa. O que
# muda nao e a revisao existir - e QUEM pode faze-la: era o operador
# arrastando o arquivo, passa a ser qualquer um da equipe, num clique,
# com o nome gravado.
#
# O SISTEMA NUNCA MOVE NADA POR CONTA PROPRIA. Ele move porque uma pessoa
# clicou - e e justamente esse clique que permite saber quem aprovou.

@pytest.fixture
def montada(portao, motor, sem_ghostscript):
    """Uma montagem ja feita, esperando revisao na pasta do dia."""
    dia, porta = portao
    _pdf(str(porta / "convite.pdf"))
    r = montagem.executar(_ordem())
    assert r["feito"] is True, r["porque"]
    return dia, porta, r["montagem"]


def test_a_montagem_gravada_aparece_esperando_revisao(montada):
    dia, porta, saiu = montada

    fila = montagem.esperando_revisao()
    assert [i["arquivo"] for i in fila] == ["convite_MONTAGEM.pdf"]
    # e ela chega com o que se sabe dela, para quem revisa nao ter de
    # abrir o registro na mao
    assert fila[0]["quem_montou"] == "Pedro"
    assert fila[0]["chapa"] == "PM_52"
    assert fila[0]["grade"] == "2x2"


def test_o_ORIGINAL_guardado_nao_e_confundido_com_montagem(montada):
    """
    A pasta do dia tem os dois: 'convite.pdf' (a fonte, guardada) e
    'convite_MONTAGEM.pdf'. Quem revisa revisa a MONTAGEM - mandar o
    original para a PARA CTP mandaria arte por montar para a gravadora.
    """
    dia, porta, saiu = montada
    assert os.path.exists(str(dia / "convite.pdf"))
    nomes = [i["arquivo"] for i in montagem.esperando_revisao()]
    assert "convite.pdf" not in nomes


def test_APROVAR_poe_na_PARA_CTP_e_grava_quem(montada):
    dia, porta, saiu = montada
    arte = str(dia / "convite.pdf")
    chave = montagem.chave_arquivo(arte)

    r = montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")

    assert r["feito"] is True, r["porque"]
    no_portao = str(dia / "PARA CTP" / "convite_MONTAGEM.pdf")
    assert os.path.exists(no_portao), "nao chegou na PARA CTP"

    anotado = montagem.carregar_montagens()[chave]
    assert anotado["aprovado_por"] == "Eudson"
    assert anotado["aprovado_em"]


def test_A_COPIA_DA_PASTA_DO_DIA_CONTINUA_existindo(montada):
    """
    O vigia APAGA da PARA CTP depois de gravar a chapa, e ele so pode
    fazer isso porque a copia da casa fica na pasta do dia. Movendo em
    vez de copiar, a montagem sumiria depois de virar chapa.
    """
    dia, porta, saiu = montada
    montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")

    assert os.path.exists(saiu), "a montagem sumiu da pasta do dia"
    assert (os.path.getsize(saiu)
            == os.path.getsize(str(dia / "PARA CTP" / "convite_MONTAGEM.pdf")))


def test_aprovada_ela_SAI_da_lista_de_revisao(montada):
    dia, porta, saiu = montada
    assert len(montagem.esperando_revisao()) == 1
    montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")
    assert montagem.esperando_revisao() == []


def test_o_que_JA_ESTA_na_PARA_CTP_nao_volta_a_esperar_revisao(montada):
    """
    O operador pode ter arrastado a mao, como sempre fez. Isso continua
    valendo - e o sistema nao pode pedir que ele aprove de novo.
    """
    dia, porta, saiu = montada
    (dia / "PARA CTP").mkdir(exist_ok=True)
    shutil.copy2(saiu, str(dia / "PARA CTP" / "convite_MONTAGEM.pdf"))

    assert montagem.esperando_revisao() == []


def test_aprovar_SEM_NOME_nao_move_nada(montada):
    """
    O clique e o que permite saber quem aprovou. Sem nome, aprovar seria
    mover sem responsavel - e quando sair chapa errada, saber quem viu e
    como a regra nasce.
    """
    dia, porta, saiu = montada
    r = montagem.aprovar("convite_MONTAGEM.pdf", "   ")

    assert r["feito"] is False
    assert "nome" in r["porque"].lower()
    assert not os.path.exists(str(dia / "PARA CTP" / "convite_MONTAGEM.pdf"))


def test_aprovar_o_que_NAO_ESTA_esperando_revisao_nao_move_nada(montada):
    """
    So se aprova o que esta na lista. De graca, isto tambem impede um
    nome vindo de fora de virar caminho para outra pasta.
    """
    dia, porta, saiu = montada
    _pdf(str(dia / "outra coisa.pdf"))

    for pedido in ("outra coisa.pdf", "nem existe_MONTAGEM.pdf",
                   r"..\..\segredo.pdf"):
        r = montagem.aprovar(pedido, "Eudson")
        assert r["feito"] is False, pedido

    assert not os.path.isdir(str(dia / "PARA CTP")) or \
        os.listdir(str(dia / "PARA CTP")) == []


def test_montagem_feita_A_MAO_tambem_espera_revisao(portao, sem_ghostscript):
    """
    O operador monta no Corel e salva o _MONTAGEM na pasta do dia - e
    assim que a casa sempre fez. A lista mostra o que ESTA na pasta,
    e nao so o que a FIA fez: senao a tela mentiria sobre o que falta
    revisar.
    """
    dia, porta = portao
    _pdf(str(dia / "CRISTAOS_MONTAGEM.pdf"))

    fila = montagem.esperando_revisao()
    assert [i["arquivo"] for i in fila] == ["CRISTAOS_MONTAGEM.pdf"]
    assert fila[0]["quem_montou"] is None, "ninguem montou isso pela tela"

    r = montagem.aprovar("CRISTAOS_MONTAGEM.pdf", "Pedro")
    assert r["feito"] is True, r["porque"]
    assert os.path.exists(str(dia / "PARA CTP" / "CRISTAOS_MONTAGEM.pdf"))


def test_montagem_em_CDR_tambem_pode_ser_aprovada(portao, sem_ghostscript):
    """
    A casa monta no CorelDRAW e salva o _MONTAGEM.cdr - a pasta da
    AMERICA de 10/09/2026 traz 'CRISTAOS.pdf' ao lado de
    'CRISTAOS_MONTAGEM.cdr'. O portao aceita .cdr e o vigia o publica em
    PDF; recusar aqui deixaria a montagem presa na lista PARA SEMPRE,
    porque a conferencia de chegada pede que o arquivo abra como PDF.
    """
    dia, porta = portao
    with io.open(str(dia / "CRISTAOS_MONTAGEM.cdr"), "wb") as f:
        f.write(b"o que o CorelDRAW salva, e nao e PDF")

    assert [i["arquivo"] for i in montagem.esperando_revisao()] == \
        ["CRISTAOS_MONTAGEM.cdr"]

    r = montagem.aprovar("CRISTAOS_MONTAGEM.cdr", "Pedro")
    assert r["feito"] is True, r["porque"]
    no_portao = str(dia / "PARA CTP" / "CRISTAOS_MONTAGEM.cdr")
    assert os.path.exists(no_portao)
    assert open(no_portao, "rb").read().startswith(b"o que o CorelDRAW")


def test_MEIO_CDR_no_portao_tambem_e_recusado(portao, monkeypatch,
                                              sem_ghostscript):
    """
    Nao abrindo como PDF, o .cdr se confere pelo tamanho - que e tudo o
    que da para conferir nele. Meia montagem no portao viraria chapa.
    """
    dia, porta = portao
    with io.open(str(dia / "X_MONTAGEM.cdr"), "wb") as f:
        f.write(b"conteudo inteiro")

    de_verdade = shutil.copy2
    monkeypatch.setattr(montagem.shutil, "copy2",
                        lambda a, b: (de_verdade(a, b),
                                      io.open(b, "wb").write(b"meio"))[0])

    r = montagem.aprovar("X_MONTAGEM.cdr", "Pedro")
    assert r["feito"] is False
    assert not os.path.exists(str(dia / "PARA CTP" / "X_MONTAGEM.cdr"))


def test_montagem_que_o_vigia_JA_FECHOU_nao_volta_a_esperar_revisao(
        montada):
    """
    O vigia APAGA da PARA CTP depois de gravar a chapa - a copia da casa
    fica na pasta do dia. Olhando so 'esta na PARA CTP?', a montagem
    reapareceria na lista assim que ele apagasse, e uma segunda aprovacao
    seria uma SEGUNDA CHAPA e uma SEGUNDA OS.
    """
    from finart_ctp import utils

    dia, porta, saiu = montada
    montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")
    assert montagem.esperando_revisao() == []

    # o vigia fechou: anotou no registro dele e apagou do portao
    registro = utils.carregar_registro()
    registro[utils.chave_arquivo(saiu)] = {
        "cliente": "AMERICA", "quando": "18/09/2026 10:00",
        "saidas": ["525x459_CMYK_AMERICA_convite.pdf"]}
    utils.salvar_registro(registro)
    os.remove(str(dia / "PARA CTP" / "convite_MONTAGEM.pdf"))

    assert montagem.esperando_revisao() == [], \
        "voltou para a lista depois de virar chapa"


def test_montagem_arrastada_A_MAO_e_fechada_tambem_nao_volta(portao,
                                                             sem_ghostscript):
    """
    O mesmo caso, sem a tela ter participado: o operador arrastou, o
    vigia fechou e apagou. Ela nao pode reaparecer pedindo aprovacao.
    """
    from finart_ctp import utils

    dia, porta = portao
    montada = _pdf(str(dia / "CRISTAOS_MONTAGEM.pdf"))
    registro = utils.carregar_registro()
    registro[utils.chave_arquivo(montada)] = {"cliente": "AMERICA",
                                              "quando": "antes"}
    utils.salvar_registro(registro)

    assert montagem.esperando_revisao() == []


def test_aprovacao_que_NAO_GRAVOU_nao_passa_calada(montada, monkeypatch):
    """
    O arquivo ja esta na PARA CTP e vai virar chapa. Sem o registro, ele
    vira chapa sem ninguem respondendo por ela - e era exatamente isso
    que o clique veio resolver.
    """
    dia, porta, saiu = montada

    def nao_grava(caminho, dados):
        raise OSError("disco cheio")

    monkeypatch.setattr(montagem, "_gravar_dicionario", nao_grava)

    r = montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")
    assert r["atencao"], "a gravacao falhou e ninguem foi avisado"
    assert "gravar quem aprovou" in r["atencao"]
    assert "Eudson" in r["atencao"], "sem o nome, nao da para anotar a mao"


def test_o_MESMO_NOME_montado_duas_vezes_marca_a_montagem_CERTA(
        portao, motor, sem_ghostscript):
    """
    A AMERICA manda o arquivo corrigido com o mesmo nome, e a montagem e
    refeita. Havendo duas entradas com o mesmo 'montagem', a aprovacao
    tem de cair na MAIS NOVA - que e a que esta na pasta e foi para a
    gravadora. Caindo na velha, a montagem que virou chapa fica gravada
    como nunca aprovada.
    """
    dia, porta = portao
    arte = _pdf(str(porta / "convite.pdf"), b"a primeira")
    montagem.executar(_ordem())

    # a AMERICA manda de novo, com o mesmo nome e outro conteudo
    _pdf(str(porta / "convite.pdf"), b"a segunda, corrigida")
    nova = montagem.chave_arquivo(str(porta / "convite.pdf"))
    montagem.executar(_ordem())

    montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")

    tudo = montagem.carregar_montagens()
    assert tudo[nova].get("aprovado_por") == "Eudson", \
        "a aprovacao caiu na entrada errada"


def test_a_PARA_CTP_e_criada_se_ainda_nao_existir(montada):
    """
    O portao de saida e criado por gente, como o de entrada. Mas aprovar
    sem ter onde por seria parar o serviço por causa de uma pasta.
    """
    dia, porta, saiu = montada
    assert not os.path.isdir(str(dia / "PARA CTP"))

    assert montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")["feito"] is True
    assert os.path.isdir(str(dia / "PARA CTP"))


def test_aprovar_CONFERE_que_a_copia_chegou_inteira(montada, monkeypatch):
    """
    Meia montagem na PARA CTP seria gravada pelo vigia como chapa. A
    conferencia e a mesma da casa - tamanho e abre como PDF.
    """
    dia, porta, saiu = montada
    monkeypatch.setattr(montagem.america, "chegou_inteira",
                        lambda a, b: (False, "tamanho diferente"))

    r = montagem.aprovar("convite_MONTAGEM.pdf", "Eudson")
    assert r["feito"] is False
    assert "inteira" in r["porque"].lower() or "confere" in r["porque"].lower()
    # e o que chegou pela metade nao fica la esperando o vigia
    assert not os.path.exists(str(dia / "PARA CTP" / "convite_MONTAGEM.pdf"))


def test_NINGUEM_move_para_a_PARA_CTP_sozinho():
    """
    A mudanca de pasta E a aprovacao. So o aprovar() escreve la - e ele
    so roda quando uma pessoa clica.
    """
    fonte = open(montagem.__file__, encoding="utf-8").read()
    antes, depois = fonte.split("def aprovar(", 1)

    # LER a PARA CTP e legitimo - a lista de revisao precisa saber o que
    # ja esta la. O que so o aprovar() pode fazer e ESCREVER.
    assert "shutil.copy2(" in depois
    assert "shutil.copy2(" not in antes, \
        "outra funcao copia arquivo - e a PARA CTP e o unico portao de saida"
    assert "os.makedirs(portao_saida" in depois
    for escrita in ("shutil.move(", "os.replace("):
        pedaco = depois.split("def ", 1)[0]
        assert escrita not in pedaco, \
            "%s dentro do aprovar: a copia na pasta do dia tem de ficar" \
            % escrita


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
