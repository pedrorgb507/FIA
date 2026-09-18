# -*- coding: utf-8 -*-
r"""
O servidor da fila de montagem - a casca fina por cima do modulo.

DUAS COISAS ESTE ARQUIVO SEGURA, e as duas sao decisoes da spec:

  1. NADA DE REGRA DENTRO DO SERVIDOR. Fila, medicao e registro moram no
     montagem.py. O servidor traduz pedido em chamada e desenha - se um
     dia uma conta aparecer aqui, a tela e o vigia passam a poder
     discordar, e ai um dos dois manda chapa errada;

  2. ELE E PROCESSO SEPARADO DO VIGIA. O servidor cair nao pode derrubar
     o fechamento dos outros seis clientes, que e o que paga o dia.

A pagina se prova SEM SUBIR HTTP: ela e uma funcao que recebe a fila e
devolve o HTML. Quem sobe socket em teste testa o socket, nao a pagina.
"""

import os

from finart_ctp import servidor


def _item(**o):
    """Um item de fila medido, do jeito que o montagem.py devolve."""
    base = {"arquivo": "convite.pdf", "caminho": r"X:\AMERICA\09\18\convite.pdf",
            "largura": 325.0, "altura": 430.0, "tintas": ["C", "K", "M", "Y"],
            "cores": "CMYK", "peb": False, "paginas": 1, "tem_marca": True,
            "marca_no_pe": 11.9, "erro": None}
    base.update(o)
    return base


# ----------------------------------------------------------------------
# A PAGINA DA FILA
# ----------------------------------------------------------------------

def test_a_pagina_lista_o_que_esta_no_portao():
    pagina = servidor.pagina_da_fila([_item(arquivo="Flyer da Semana.pdf"),
                                      _item(arquivo="convite.pdf")])
    assert "Flyer da Semana.pdf" in pagina
    assert "convite.pdf" in pagina


def test_a_pagina_mostra_as_cinco_medidas():
    """Tamanho, cor, paginas e marca de corte - o que o ticket pediu."""
    pagina = servidor.pagina_da_fila([_item(largura=325.0, altura=430.0,
                                            paginas=2, tem_marca=True,
                                            marca_no_pe=11.9)])
    assert "325" in pagina and "430" in pagina
    assert "CMYK" in pagina
    assert "2" in pagina
    assert "11,9" in pagina or "11.9" in pagina


def test_preto_e_branco_aparece_escrito_e_nao_so_a_lista_de_tintas():
    """
    'K' nao diz nada para quem esta escolhendo maquina. 'preto e branco'
    diz - e e essa palavra que casa com a regra da casa.
    """
    pagina = servidor.pagina_da_fila([_item(tintas=["K"], cores="K",
                                            peb=True)])
    assert "preto" in pagina.lower()


def test_as_tintas_saem_na_ordem_da_ESCALA_e_nao_do_alfabeto():
    """
    A casa escreve CMYK, e e o que vai no nome da chapa. 'CKMY' - a
    ordem do alfabeto - nao e nome de cor de ninguem.
    """
    pagina = servidor.pagina_da_fila([_item()])
    assert "CMYK" in pagina
    assert "CKMY" not in pagina


def test_portao_vazio_da_PAGINA_e_nao_erro():
    """
    E o dia normal de quem ja montou tudo. Tela de erro para isso faria a
    equipe achar que o sistema quebrou.
    """
    pagina = servidor.pagina_da_fila([])
    assert "<html" in pagina.lower()
    assert "Nada esperando montagem" in pagina
    # nenhum recado de falha na tela - e dia normal, nao defeito
    assert "nao consegui" not in pagina.lower()
    assert "chame quem cuida" not in pagina.lower()


def test_arquivo_sem_medida_aparece_com_o_motivo():
    """
    O arquivo esta no portao e e trabalho. Some da tela e pior que
    aparecer sem medida.
    """
    pagina = servidor.pagina_da_fila([
        _item(largura=None, altura=None, tintas=[], peb=None, paginas=None,
              tem_marca=None, marca_no_pe=None,
              erro="o Ghostscript nao respondeu")])
    assert "convite.pdf" in pagina
    assert "Ghostscript" in pagina


def test_nome_de_arquivo_nao_vira_HTML():
    """
    Nome de arquivo e texto de fora - vem do que a AMERICA mandou pelo
    WhatsApp. Escrito cru na pagina, um '<' quebraria a tela; e quebrar a
    tela da fila e parar a equipe.
    """
    pagina = servidor.pagina_da_fila([_item(arquivo="cartaz <b>&.pdf")])
    assert "<b>" not in pagina
    assert "&lt;b&gt;" in pagina or "&#60;" in pagina


def test_portao_que_NAO_EXISTE_nao_se_parece_com_portao_vazio():
    """
    Sao duas coisas muito diferentes, e a tela confundia as duas: "a
    equipe montou tudo" e "ninguem criou a pasta ainda". A pasta do dia e
    nova todo dia e o portao e criado por gente - numa manha em que
    ninguem o criou, a fila mostraria vazio e a equipe iria embora
    achando que nao havia trabalho.
    """
    vazio = servidor.pagina_da_fila([], portao=r"X:\A\09\18\PARA MONTAR")
    sem_portao = servidor.pagina_da_fila(
        [], portao=r"X:\A\09\18\PARA MONTAR", tem_portao=False)

    assert "Nada esperando montagem" in vazio
    assert "Nada esperando montagem" not in sem_portao
    assert "PARA MONTAR" in sem_portao
    assert "nao existe" in sem_portao.lower() or \
        "nao encontrei" in sem_portao.lower()


def test_pagina_desconhecida_nao_finge_que_a_fila_esta_vazia():
    """
    Endereco digitado errado mostrava 'Nada esperando montagem' com o
    rodape dizendo que nao achou a pasta do dia. O 404 nao aparece no
    navegador, e a pessoa concluiria que nao ha trabalho.
    """
    pagina = servidor.pagina_nao_achei()
    assert "Nada esperando montagem" not in pagina
    assert "<html" in pagina.lower()
    assert "/" in pagina


def test_a_pagina_diz_de_que_pasta_esta_falando():
    """
    Quem abre de outro PC nao ve a pasta. Sem o caminho na tela, nao da
    para saber se a fila e do dia certo.
    """
    pagina = servidor.pagina_da_fila([], portao=r"X:\AMERICA\SETEMBRO\18\PARA MONTAR")
    assert "PARA MONTAR" in pagina


# ----------------------------------------------------------------------
# CASCA FINA: a regra nao mora aqui
# ----------------------------------------------------------------------

def _fonte(modulo):
    return open(modulo.__file__, encoding="utf-8").read()


def test_o_servidor_nao_mede_nada_por_conta_propria():
    """
    A medicao e a da casa, chamada pelo montagem.py. O servidor que
    importasse o Ghostscript ou o pypdf estaria comecando uma segunda
    conta - e duas contas na casa e o defeito que esta spec veio acabar.
    """
    fonte = _fonte(servidor).lower()
    for proibido in ("import pypdf", "from pypdf", "import ghostscript",
                     "from .ghostscript", "from .marcas", "import marcas",
                     "cobertura_por_pagina(", "marcas_de_corte(",
                     "pdfreader("):
        assert proibido not in fonte, \
            "'%s' no servidor: a conta tem de ficar no modulo" % proibido


def test_o_servidor_so_conhece_o_modulo_da_montagem():
    """
    A casca fina chama UMA porta de entrada. Importando america, corel ou
    processador direto, ela comecaria a ter caminho proprio - e a regra
    deixaria de morar num lugar so.
    """
    fonte = _fonte(servidor)
    for proibido in ("from . import america", "from . import processador",
                     "from . import corel", "from . import gerempre",
                     "from .america import", "from .processador import"):
        assert proibido not in fonte, proibido
    assert "from . import montagem" in fonte


def test_o_servidor_nao_escreve_na_pasta_do_cliente():
    """A pasta e compartilhada, e a regra da casa vale para a tela também."""
    fonte = _fonte(servidor)
    for proibido in ("shutil.move", "shutil.copy", "os.remove", "os.rmdir"):
        assert proibido not in fonte


# ----------------------------------------------------------------------
# PROCESSO SEPARADO DO VIGIA
# ----------------------------------------------------------------------

def test_o_vigia_nao_sobe_o_servidor():
    """
    O servidor cair nao pode derrubar o fechamento dos outros seis
    clientes - e o jeito mais simples de garantir isso e o vigia nao
    saber que ele existe.
    """
    from finart_ctp import monitor
    fonte = _fonte(monitor)
    # o que importa e IMPORTACAO: o vigia nao carrega nem chama nada
    # desta tela. ('servidor' solto aparece no caminho \\servidor\ das
    # mensagens dele, e isso nao acopla nada.)
    for proibido in ("import servidor", "from .servidor", "from . import "
                     "servidor", "import montagem", "from .montagem",
                     "from . import montagem", "ThreadingHTTPServer",
                     "http.server"):
        assert proibido not in fonte, \
            "o vigia passou a saber da tela por '%s'" % proibido


def test_o_servidor_sobe_sozinho_por_um_main():
    assert callable(servidor.main)
    assert '__main__' in _fonte(servidor)


def test_o_servidor_atende_a_rede_e_nao_so_a_propria_maquina():
    """
    E a decisao que tira a dependencia: a equipe abre a fila do PC DELA.
    Em 127.0.0.1 a pagina abriria so na maquina da FIA, que e justamente
    a cadeira que todo mundo tem de disputar hoje.
    """
    from finart_ctp import config
    assert config.ENDERECO_DA_MONTAGEM == "0.0.0.0"
    assert servidor.ENDERECO == config.ENDERECO_DA_MONTAGEM
    assert servidor.PORTA == config.PORTA_DA_MONTAGEM


def test_o_arranque_existe_e_e_separado_do_vigia():
    """
    O operador liga o que precisa por atalho, e nao por linha de comando
    - e o mesmo par iniciar_ctp.bat / run_ctp.py que o vigia ja tem.
    Duas janelas, e cada uma cuida da sua vida.
    """
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    bat = os.path.join(raiz, "iniciar_montagem.bat")
    assert os.path.exists(bat), "falta o atalho de arranque"
    assert "run_montagem.py" in open(bat, encoding="latin-1").read()

    entrada = os.path.join(raiz, "run_montagem.py")
    assert os.path.exists(entrada)
    fonte = open(entrada, encoding="utf-8").read()
    assert "finart_ctp.servidor" in fonte
    # e o arranque do vigia continua nao sabendo desta tela
    assert "servidor" not in open(os.path.join(raiz, "run_ctp.py"),
                                  encoding="utf-8").read()
