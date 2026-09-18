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
            "marca_no_pe": 11.9,
            "corte_largura": 100.0, "corte_altura": 150.0,
            "corte_de": "da TrimBox declarada no arquivo",
            "sangria": True, "sangria_mm": 3.0,
            "sangria_declarada": 3.0, "sangria_pela_tinta": 2.8,
            "sangria_divergem": False, "sangria_recado": "as duas concordam",
            "versao": 3, "erro": None}
    base.update(o)
    return base


# ----------------------------------------------------------------------
# A PAGINA DA FILA
# ----------------------------------------------------------------------

def test_o_item_de_mentira_tem_a_MESMA_forma_que_o_de_verdade():
    """
    Todo teste daqui desenha a pagina a partir do _item(). Ele ficando
    para tras do que a fila mede de verdade, a tela passaria a ser
    provada com uma forma que nao existe - e um campo novo poderia sair
    quebrado sem um unico teste vermelho.
    """
    from finart_ctp import montagem
    de_verdade = montagem.medir_para_a_fila(__file__)   # nao e PDF: cai em erro
    assert set(_item()) == set(de_verdade), \
        "o _item() e a fila divergiram: %s" % (
            set(_item()) ^ set(de_verdade))


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


def test_a_pagina_diz_se_o_arquivo_JA_VEIO_SANGRADO():
    """
    Para ninguem montar como se tivesse sangria o que nao tem - e o
    contrario, mandar sangrar o que ja esta sangrado.
    """
    sangrado = servidor.pagina_da_fila([_item(sangria=True, sangria_mm=3.0)])
    assert "sangria" in sangrado.lower()
    assert "3,0" in sangrado or "3.0" in sangrado

    pelado = servidor.pagina_da_fila([_item(sangria=False, sangria_mm=0.0)])
    assert "nao" in pelado.lower()


def test_sangria_que_NAO_SE_SABE_nao_aparece_como_sem_sangria():
    """
    Arquivo que nao declara TrimBox e nao tem marca de corte: nao da para
    medir. Mostrar 'nao' ali faria alguem montar confiando numa resposta
    que ninguem deu.
    """
    pagina = servidor.pagina_da_fila([_item(
        sangria=None, sangria_mm=None, sangria_declarada=None,
        sangria_pela_tinta=None,
        sangria_recado="nao da para saber: o arquivo nao declara TrimBox")])
    assert "nao da para saber" in pagina or "nao sei" in pagina.lower()


def test_as_duas_leituras_DISCORDANDO_a_tela_diz_o_que_cada_uma_achou():
    """
    O caso que engana. A tela nao pode resumir isso a um 'sim' ou a um
    'nao' - os dois numeros tem de aparecer, porque quem decide e gente.
    """
    pagina = servidor.pagina_da_fila([_item(
        sangria=None, sangria_declarada=3.0, sangria_pela_tinta=0.0,
        sangria_divergem=True,
        sangria_recado="AS DUAS LEITURAS DISCORDAM, e arquivo que declara "
                       "uma coisa e mostra outra e o que engana: o arquivo "
                       "DECLARA 3.0 mm de sangria, e na TINTA o desenho "
                       "para na linha de corte")])
    assert "DISCORDAM" in pagina
    assert "3.0" in pagina or "3,0" in pagina
    assert "declara" in pagina.lower() and "tinta" in pagina.lower()


def test_o_recado_da_sangria_tambem_escapa_HTML():
    """Texto que vai para a tela passa pelo escape, todo ele."""
    pagina = servidor.pagina_da_fila([_item(
        sangria_divergem=True, sangria_recado="<script>x</script>")])
    assert "<script>" not in pagina


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


def test_o_nome_na_fila_LEVA_ao_painel_daquele_arquivo():
    """
    E o caminho inteiro do sistema numa frase: a pessoa ve o que esta
    esperando, escolhe um, e cai no painel ja preenchido.
    """
    pagina = servidor.pagina_da_fila([_item(arquivo="Flyer & cia.pdf")])
    assert 'href="/painel?arquivo=Flyer%20%26%20cia.pdf"' in pagina


def test_arquivo_SEM_MEDIDA_tambem_leva_ao_painel():
    """
    Ele esta no portao e e trabalho. O painel serve para montar a mao o
    que a FIA nao conseguiu medir.
    """
    pagina = servidor.pagina_da_fila([_item(erro="o Ghostscript caiu")])
    assert 'href="/painel?arquivo=convite.pdf"' in pagina


# ----------------------------------------------------------------------
# O PAINEL SERVIDO - e a copia em JavaScript que morreu
# ----------------------------------------------------------------------

def test_o_painel_recebe_as_tabelas_da_casa():
    from finart_ctp import montagem

    dados = montagem.dados_do_painel(None)
    pagina = servidor.pagina_do_painel(dados)
    assert "525" in pagina and "459" in pagina        # a PM 52
    assert '"total": [330, 480]' in pagina or "330" in pagina


def test_a_COPIA_em_javascript_deixou_de_existir():
    """
    O checkbox do ticket, e a razao de o painel ter virado servido. A
    tabela estava escrita em dois lugares e o comentario no config dizia
    'mudou aqui, muda la' - combinado que ninguem cumpre duas vezes.
    """
    painel = open(servidor.PAINEL, encoding="utf-8").read()
    assert "const FORMATOS_DA_CASA = FIA_DADOS.formatos" in painel
    assert "const CLIENTES = FIA_DADOS.clientes" in painel
    # nenhuma medida de chapa nem de folha escrita a mao no JavaScript
    for copiado in ("l:525", "l:650", "l:745", "util:[315,460]",
                    "total:[330,480]", 'pinca:60'):
        assert copiado not in painel, \
            "'%s' continua escrito no painel - a copia nao morreu" % copiado


def test_o_painel_PARA_quando_abre_sem_os_dados():
    """
    Aberto direto do disco ele nao tem as tabelas. Trabalhar com tabela
    vazia seria pior que nao abrir: ele diria 'cabe' sobre uma chapa que
    nao existe.
    """
    painel = open(servidor.PAINEL, encoding="utf-8").read()
    assert "if(!FIA_DADOS.clientes || !FIA_DADOS.formatos)" in painel
    assert "iniciar_montagem.bat" in painel


def test_servir_o_painel_com_a_marca_mudada_PARA_em_vez_de_servir_vazio():
    """
    Se alguem mexer no painel e tirar o lugar dos dados, o servidor tem
    de parar - servir a pagina assim a faria trabalhar com tabela vazia,
    e ninguem veria.
    """
    import pytest
    original = servidor.MARCA_DOS_DADOS
    try:
        servidor.MARCA_DOS_DADOS = '<script id="nao-existe-mais"></script>'
        with pytest.raises(RuntimeError, match="dados da casa"):
            servidor.pagina_do_painel({"clientes": {}, "formatos": {}})
    finally:
        servidor.MARCA_DOS_DADOS = original


def test_nome_de_arquivo_nao_escapa_do_bloco_de_dados():
    """
    O nome vem do que a AMERICA mandou pelo WhatsApp. Um '</script>'
    dentro dele fecharia o bloco no meio, e o resto do JSON viraria HTML.
    """
    pagina = servidor.pagina_do_painel({
        "clientes": {}, "formatos": {},
        "arquivo": {"arquivo": "x</script><b>oi</b>.pdf"}})
    assert "</script><b>oi</b>" not in pagina
    assert "\\u003c/script" in pagina


def test_o_painel_traz_o_arquivo_que_a_fila_mandou():
    pagina = servidor.pagina_do_painel({
        "clientes": {}, "formatos": {},
        "arquivo": {"arquivo": "convite.pdf", "corte_largura": 100.0,
                    "corte_altura": 150.0,
                    "sugestao": {"chapa": "PM_52", "cor": "CMYK",
                                 "tipo": "frente-verso"}}})
    assert "convite.pdf" in pagina
    assert "PM_52" in pagina


def test_o_painel_preenche_os_campos_do_que_foi_medido():
    """
    A conta de quem preenche mora no painel, e o que se confere aqui e
    que ela EXISTE e usa a medida do CORTE - nao a do papel.
    """
    painel = open(servidor.PAINEL, encoding="utf-8").read()
    assert "function preencherDoArquivo()" in painel
    assert "preencherDoArquivo();" in painel
    assert "pl_.value = a.corte_largura" in painel
    assert "pa_.value = a.corte_altura" in painel
    # e a sugestao entra por ID, nunca por posicao
    assert "acha(e.cliente.chapas, s.chapa)" in painel


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
