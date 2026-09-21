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
            "precisa_publicar": False, "versao": 3, "erro": None}
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
        sangria_divergem=True,
        sangria_recado="<script>alert('oi')</script>")])
    # a pagina tem script PROPRIO (o do aprovar); o que nao pode e o
    # texto do recado virar um
    assert "alert('oi')" not in pagina
    assert "&lt;script&gt;" in pagina


def test_portao_que_NAO_EXISTE_nao_se_parece_com_portao_vazio():
    """
    Sao duas coisas muito diferentes, e a tela confundia as duas: "a
    equipe montou tudo" e "a pasta nao esta la". Sem a separacao, uma
    manha sem portao mostraria fila vazia e a equipe iria embora achando
    que nao havia trabalho.
    """
    vazio = servidor.pagina_da_fila([], portao=r"X:\A\09\18\PARA MONTAR")
    sem_portao = servidor.pagina_da_fila(
        [], portao=r"X:\A\09\18\PARA MONTAR", tem_portao=False)

    assert "Nada esperando montagem" in vazio
    assert "Nada esperando montagem" not in sem_portao
    assert "PARA MONTAR" in sem_portao
    assert "nao consegui" in sem_portao.lower()


def test_portao_faltando_NAO_MANDA_MAIS_criar_a_pasta_na_mao():
    """
    O conselho da tela era "crie a pasta na pasta do dia" - e era certo
    enquanto a pasta era combinado entre gente. Desde 18/09/2026 quem a
    cria e a FIA, a cada volta do vigia e a cada vez que a tela e
    desenhada. Ai o conselho vira armadilha: a pessoa criaria a pasta, o
    arquivo entraria, e a montagem nao teria como ser gravada de volta -
    quem grava e justamente quem nao esta alcancando o servidor.
    """
    sem_portao = servidor.pagina_da_fila(
        [], portao=r"X:\A\09\18\PARA MONTAR", tem_portao=False)

    baixo = sem_portao.lower()
    assert "crie a pasta na pasta do dia" not in baixo
    assert "nao crie a pasta na mao" in baixo
    # e diz onde esta o problema, que e a rede - nao a equipe
    assert "servidor" in baixo


def test_o_motivo_do_servidor_APARECE_na_tela_e_vai_escapado():
    """
    'nao consegui' sozinho nao ajuda quem cuida da rede: o recado do
    sistema operacional e o que diz se e permissao ou se e a rede.

    E ele vem DE FORA, entao passa pelo escape como qualquer texto que
    esta tela mostre - a mesma regra do sangria_recado.
    """
    pagina = servidor.pagina_da_fila(
        [], portao=r"X:\A\09\18\PARA MONTAR", tem_portao=False,
        erro_das_pastas="[Errno 13] Permission denied: <servidor>")

    assert "Permission denied" in pagina
    assert "&lt;servidor&gt;" in pagina
    assert "<servidor>" not in pagina

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
# O BOTAO MONTA - e a casca continua fina
# ----------------------------------------------------------------------

def test_o_servidor_atende_o_pedido_de_MONTAR():
    fonte = _fonte(servidor)
    assert "def do_POST" in fonte
    assert '"/montar"' in fonte
    assert "montagem.executar(pedido)" in fonte


def test_montar_NAO_DECIDE_nada_no_servidor():
    """
    As travas - nao gravar na PARA CTP, conferir a pinca no arquivo que
    saiu, tirar o original do portao - moram no modulo, onde os testes as
    alcancam sem subir socket. O do_POST le JSON e chama.
    """
    fonte = _fonte(servidor)
    # o que se proibe e FAZER, e nao falar: o comentario que conta a
    # trava tem de poder nomear a PARA CTP
    for proibido in ("medir_o_pe(", "guardar_copia(", "anotar_montagem(",
                     '"_MONTAGEM"', "esta_pincada(", "os.remove("):
        assert proibido not in fonte, \
            "'%s' no servidor: a decisao mora no montagem.py" % proibido


def test_o_corpo_da_ordem_tem_TETO():
    """
    O corpo vem de fora. Lendo sem limite, qualquer um na rede interna
    enche a memoria desta maquina - que e a mesma que fecha chapa dos
    outros seis clientes.
    """
    assert "64 * 1024" in _fonte(servidor)


def test_o_painel_manda_a_ordem_em_vez_de_gerar_texto():
    painel = open(servidor.PAINEL, encoding="utf-8").read()
    assert "function ordemObjeto(c)" in painel
    assert 'fetch("/montar"' in painel
    # e o texto continua existindo para quem monta a mao
    assert "function ordem(c)" in painel


# ----------------------------------------------------------------------
# O .CDR E O ARQUIVO DE VARIAS PAGINAS
# ----------------------------------------------------------------------

def test_o_CDR_aparece_com_o_botao_de_PUBLICAR():
    pagina = servidor.pagina_da_fila([_item(
        arquivo="arte.cdr", precisa_publicar=True, largura=None,
        altura=None, paginas=None, cores=None, peb=None)])
    assert "arte.cdr" in pagina
    assert 'data-publicar="arte.cdr"' in pagina
    assert "CorelDRAW" in pagina


def test_o_CDR_nao_finge_ter_medida():
    """
    Ele nem se abre fora do CorelDRAW. Mostrar '- x - mm' ao lado faria
    parecer que alguem tentou medir e nao conseguiu.
    """
    pagina = servidor.pagina_da_fila([_item(
        arquivo="arte.cdr", precisa_publicar=True, largura=None,
        altura=None, paginas=None)])
    assert "precisa ser publicado" in pagina
    assert "nao consegui medir" not in pagina


def test_o_nome_do_cdr_nao_vira_HTML_no_botao():
    pagina = servidor.pagina_da_fila([_item(
        arquivo='x" onclick="mau().cdr', precisa_publicar=True)])
    assert 'onclick="mau()' not in pagina


def test_TRES_PAGINAS_ou_mais_avisam_na_fila():
    """
    A gravadora nao puxa multiplas paginas. Duas sao frente e verso e a
    casa sabe montar; tres ou mais ninguem adivinha.
    """
    pagina = servidor.pagina_da_fila([_item(paginas=5)])
    assert "5 páginas" in pagina
    assert "não puxa múltiplas páginas" in pagina


def test_UMA_ou_DUAS_paginas_nao_enchem_a_tela_de_aviso():
    """
    Aviso que aparece sempre ninguem le - e ai o caso que importa se
    perde no meio.
    """
    for quantas in (1, 2):
        pagina = servidor.pagina_da_fila([_item(paginas=quantas)])
        assert "não puxa múltiplas páginas" not in pagina


def test_o_servidor_atende_o_pedido_de_PUBLICAR():
    fonte = _fonte(servidor)
    assert '"/publicar"' in fonte
    assert "montagem.publicar(" in fonte


def test_o_ATENCAO_para_na_frente_de_quem_apertou():
    """
    Deu certo e mesmo assim precisa de gente - o .cdr que nao saiu do
    portao, a montagem cujo registro nao gravou. A pagina recarrega logo
    em seguida, e o recado se perderia com ela.
    """
    fonte = _fonte(servidor)
    assert "if(d.atencao) alert(" in fonte
    depois = fonte.split("if(d.atencao)")[1].split("location.reload")[0]
    assert "alert" in depois, "o aviso tem de vir ANTES do recarregar"
    # e o relato do modulo chega inteiro ate a tela
    assert '"atencao": relato.get("atencao")' in fonte


def test_PUBLICAR_nao_pede_nome():
    """
    Nao e decisao, e um passo: o .cdr vira PDF e nada mais acontece. Quem
    decide alguma coisa e quem monta e quem aprova - esses dois assinam.
    """
    fonte = _fonte(servidor)
    depois = fonte.split("if(b.dataset.publicar)")[1].split("}")[0]
    assert "prompt(" not in depois


# ----------------------------------------------------------------------
# A REVISAO NA TELA
# ----------------------------------------------------------------------

def _revisao(**o):
    base = {"arquivo": "convite_MONTAGEM.pdf", "caminho": r"X:\A\convite.pdf",
            "quem_montou": "Pedro", "quando": "18/09/2026 09:12",
            "chapa": "PM_52", "grade": "2x2", "tipo": "bate-vira",
            "de": "convite.pdf", "maquina_trocada": None,
            "liberado_sem_caber": False, "liberado_por": None,
            "liberado_porque": []}
    base.update(o)
    return base


def test_a_tela_mostra_as_DUAS_metades_do_dia():
    """
    O que falta montar e o que falta revisar sao as duas metades da mesma
    pergunta. Quem abre a tela quer ver as duas sem procurar.
    """
    pagina = servidor.pagina_da_fila([_item()], revisao=[_revisao()])
    assert "convite.pdf" in pagina
    assert "Esperando revisão" in pagina
    assert "convite_MONTAGEM.pdf" in pagina


def test_cada_montagem_tem_o_BOTAO_de_aprovar():
    pagina = servidor.pagina_da_fila([], revisao=[_revisao()])
    assert 'data-arquivo="convite_MONTAGEM.pdf"' in pagina
    assert "PARA CTP" in pagina


def test_a_tela_diz_QUEM_MONTOU_antes_de_alguem_aprovar():
    """Quem revisa precisa saber de quem e o trabalho que esta olhando."""
    pagina = servidor.pagina_da_fila([], revisao=[_revisao()])
    assert "Pedro" in pagina and "PM_52" in pagina


def test_montagem_LIBERADA_SEM_CABER_grita_para_quem_vai_aprovar():
    """
    E o caso em que alguem ja disse 'pode ir' sabendo que nao cabia.
    Quem revisa tem de ver isso ANTES de aprovar - depois vira chapa.
    """
    pagina = servidor.pagina_da_fila([], revisao=[_revisao(
        liberado_sem_caber=True, liberado_por="Eudson",
        liberado_porque=["nao cabe no UTIL DA CHAPA: 805.0 x 300.0"])])
    assert "LIBERADA SEM CABER" in pagina
    assert "Eudson" in pagina
    assert "805.0" in pagina


def test_a_MAQUINA_TROCADA_tambem_aparece_para_quem_revisa():
    pagina = servidor.pagina_da_fila([], revisao=[_revisao(
        maquina_trocada="a regra da casa sugeriu PM_52")])
    assert "sugeriu PM_52" in pagina


def test_montagem_feita_FORA_DA_TELA_aparece_dizendo_isso():
    """O operador monta no Corel, como sempre fez - e ela precisa de olho
    humano do mesmo jeito."""
    pagina = servidor.pagina_da_fila([], revisao=[_revisao(
        quem_montou=None, quando=None, chapa=None, grade=None)])
    assert "montada fora da tela" in pagina


def test_nada_esperando_revisao_nao_e_erro():
    pagina = servidor.pagina_da_fila([_item()], revisao=[])
    assert "Nada esperando revisão" in pagina
    assert "nao consegui" not in pagina.lower()


def test_o_nome_da_montagem_nao_vira_HTML_no_botao():
    pagina = servidor.pagina_da_fila([], revisao=[_revisao(
        arquivo='x" onclick="mau()_MONTAGEM.pdf')])
    assert 'onclick="mau()' not in pagina


def test_o_servidor_atende_o_pedido_de_APROVAR():
    fonte = _fonte(servidor)
    assert '"/aprovar"' in fonte
    assert "montagem.aprovar(" in fonte


def test_o_clique_de_aprovar_PEDE_O_NOME():
    """
    O que separa o clique do arrastar a mao e ficar dito quem clicou.
    Sem nome, aprovar seria mover sem responsavel.
    """
    fonte = _fonte(servidor)
    assert "prompt(" in fonte
    assert "fia-quem" in fonte, "o nome tem de ser o mesmo que o painel usa"
    assert "if(!quem) return;" in fonte


# ----------------------------------------------------------------------
# A TELA DE HISTORICO
# ----------------------------------------------------------------------

def _linha(**o):
    base = {"arquivo": "convite.pdf", "montagem": "convite_MONTAGEM.pdf",
            "quando": "18/09/2026 09:12", "quem": "Pedro", "chapa": "PM_52",
            "grade": "2x2", "tipo": "bate-vira", "aprovado_por": "Eudson",
            "aprovado_em": "18/09/2026 10:15", "maquina_trocada": None,
            "liberado_sem_caber": False, "liberado_por": None,
            "liberado_porque": []}
    base.update(o)
    return base


def test_o_historico_lista_quem_montou_e_quem_aprovou():
    pagina = servidor.pagina_do_historico([_linha()])
    assert "convite_MONTAGEM.pdf" in pagina
    assert "Pedro" in pagina and "Eudson" in pagina
    assert "18/09/2026 09:12" in pagina


def test_o_TOPO_conta_os_casos_que_ENSINAM_e_nao_so_o_total():
    """
    Uma tela que so diz 'foram 34 montagens' nao serve para o que ela
    existe: o operador vem aqui procurar onde a regra da casa nao cobriu
    a realidade.
    """
    pagina = servidor.pagina_do_historico([
        _linha(),
        _linha(arquivo="a.pdf", maquina_trocada="a regra sugeriu PM_52"),
        _linha(arquivo="b.pdf", liberado_sem_caber=True,
               liberado_por="Eudson", liberado_porque=["nao cabe no UTIL"]),
    ])
    assert "máquina trocada fora da regra" in pagina
    assert "liberadas sem caber" in pagina
    assert "ainda não aprovadas" in pagina


def test_a_MAQUINA_TROCADA_aparece_destacada_com_o_motivo():
    pagina = servidor.pagina_do_historico([_linha(
        maquina_trocada="a regra da casa sugeriu PM_52 e foi montado na "
                        "SM_74")])
    assert 'class="olho"' in pagina, "a linha nao ficou destacada"
    assert "sugeriu PM_52" in pagina


def test_a_LIBERADA_SEM_CABER_aparece_com_o_limite_que_estourou():
    pagina = servidor.pagina_do_historico([_linha(
        liberado_sem_caber=True, liberado_por="Eudson",
        liberado_porque=["nao cabe no UTIL DA CHAPA: 805.0 x 300.0"])])
    assert 'class="olho"' in pagina
    assert "liberada sem caber por Eudson" in pagina
    assert "805.0" in pagina


def test_a_montagem_normal_NAO_fica_destacada():
    """
    Destaque que aparece sempre ninguem le - e ai o caso que importa se
    perde no meio.
    """
    assert 'class="olho"' not in servidor.pagina_do_historico([_linha()])


def test_a_que_AINDA_NAO_FOI_APROVADA_e_dita_na_tela():
    pagina = servidor.pagina_do_historico([_linha(aprovado_por=None,
                                                  aprovado_em=None)])
    assert "ainda não aprovada" in pagina


def test_a_tela_diz_de_que_PERIODO_esta_falando():
    """Sem isso, 'nada montado' pode ser o dia calmo ou o filtro errado."""
    assert "últimos 7 dias" in servidor.pagina_do_historico([_linha()])
    assert "o dia 18/09/2026" in servidor.pagina_do_historico(
        [], dia="18/09/2026")


def test_a_FRASE_CONCORDA_em_numero_e_preposicao():
    """
    'os últimos 1 dias' e 'nada montado em o dia' sao o tique mais
    reconhecivel de tela gerada - e esta e a tela que o operador abre
    quando quer ENTENDER alguma coisa.
    """
    um_dia = servidor.pagina_do_historico([_linha()], dias=1)
    assert "1 dias" not in um_dia, "concordancia: %r" % um_dia[:400]
    assert "último dia" in um_dia

    vazio_no_dia = servidor.pagina_do_historico([], dia="18/09/2026")
    assert "em o dia" not in vazio_no_dia
    assert "Nada montado no dia 18/09/2026" in vazio_no_dia

    vazio_na_semana = servidor.pagina_do_historico([], dias=7)
    assert "Nada montado nos últimos 7 dias" in vazio_na_semana


def test_periodo_VAZIO_nao_e_erro():
    pagina = servidor.pagina_do_historico([], dias=30)
    assert "Nada montado" in pagina
    assert "nao consegui" not in pagina.lower()


def test_da_para_pedir_UM_DIA_pela_tela():
    pagina = servidor.pagina_do_historico([_linha()])
    assert "/historico?dias=1" in pagina
    assert "/historico?dia=" in pagina


def test_o_historico_e_a_fila_se_ALCANCAM():
    """
    Duas telas do mesmo trabalho. Quem esta numa tem de chegar na outra
    sem digitar endereco.
    """
    assert '<a href="/">' in servidor.pagina_do_historico([_linha()])
    assert "/historico" in servidor.pagina_da_fila([], revisao=[])


def test_o_texto_do_historico_tambem_escapa_HTML():
    pagina = servidor.pagina_do_historico([_linha(
        montagem="x<b>&.pdf", quem="<script>alert(1)</script>",
        maquina_trocada="a <b>regra</b>")])
    # o TEXTO pode aparecer; o que nao pode e ele virar marcacao viva
    assert "<b>&.pdf" not in pagina
    assert "<script>alert(1)" not in pagina
    assert "a <b>regra</b>" not in pagina
    assert "&lt;script&gt;alert(1)" in pagina


def test_o_nome_de_quem_APROVOU_tambem_escapa():
    """
    Ele vem de fora - digitado no navegador de quem clicou em aprovar -
    e vai para a tela de TODO MUNDO. Passou daqui cru uma vez.
    """
    pagina = servidor.pagina_do_historico([_linha(
        aprovado_por="<script>alert(1)</script>")])
    assert "<script>alert(1)" not in pagina
    assert "&lt;script&gt;alert(1)" in pagina


def test_a_contagem_do_topo_tem_ESTILO():
    """
    A tira e a razao de a tela existir - o que ensina, em numero. Sem
    regra no estilo ela sai como blocos empilhados, e o que era para
    saltar aos olhos vira paragrafo.
    """
    pagina = servidor.pagina_do_historico([_linha()])
    assert 'class="tira"' in pagina
    assert ".tira {" in pagina or ".tira{" in pagina


def test_data_que_NAO_SE_ENTENDEU_nao_vira_silencio():
    """
    Pedindo '?dia=18-09-2026' a tela caia para a semana e continuava se
    chamando 'o dia 18-09-2026': a pessoa leria uma semana inteira
    achando que era um dia.
    """
    pagina = servidor.pagina_do_historico(
        [_linha()], dia=None, dias=7, data_nao_entendida="18-09-2026")
    assert "Não entendi a data" in pagina
    assert "18-09-2026" in pagina
    assert "o dia 18-09-2026" not in pagina
    assert "últimos 7 dias" in pagina


def test_a_janela_pedida_pelo_endereco_e_APERTADA():
    """
    O numero vem do endereco, que e digitado por gente: 0 listaria o
    registro inteiro sob 'os ultimos 0 dias', um negativo poria o corte
    no FUTURO e esconderia tudo, e um numero grande demais estoura o
    timedelta e derruba a pagina.
    """
    from finart_ctp import montagem

    assert montagem.MENOS_DIAS == 1
    for pedido in (0, -1, 10 ** 9, "nao e numero"):
        # nao estoura, e nao devolve o registro inteiro sem corte
        assert isinstance(montagem.historico(dias=pedido), list), pedido


def test_a_tela_de_historico_NAO_ESCREVE_nada():
    """
    E tela de olhar. Um botao que apaga no lugar onde se procura o que
    deu errado e o jeito mais rapido de perder o que ensina.
    """
    fonte = _fonte(servidor)
    corpo = fonte.split("def pagina_do_historico(")[1].split("\ndef ")[0]
    for escrita in ("montagem.aprovar", "montagem.executar", "os.remove",
                    "<form", "<button"):
        assert escrita not in corpo, "o historico tem %s" % escrita


def test_o_servidor_atende_o_HISTORICO():
    fonte = _fonte(servidor)
    assert '"/historico"' in fonte
    assert "montagem.historico(" in fonte
    # e nunca por POST: nao ha o que mandar para uma tela de olhar
    depois_do_post = fonte.split("def do_POST")[1]
    assert "/historico" not in depois_do_post


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


# --------------------------------------------------------------------------
# O SCRIPT DA PAGINA TEM DE SER JAVASCRIPT VALIDO
# --------------------------------------------------------------------------
#
# 18/09/2026: escrevi "\n" dentro do confirm do 'Limpar lista'. Aquele
# bloco e uma string PYTHON, entao o \n virou quebra de linha DE VERDADE
# no meio de uma string JavaScript - e string aberta quebra o script
# inteiro.
#
# O que o operador viu nao foi o botao novo falhando: foi o APROVAR, que
# nao tem nada a ver com aquilo, parar de responder. Erro de sintaxe em
# <script> nao aparece na tela; ele so faz TODOS os botoes da pagina
# emudecerem de uma vez.

def _script_da_pagina(html_):
    import re
    achados = re.findall(r"<script>(.*?)</script>", html_, re.S)
    assert achados, "a pagina perdeu o <script>"
    return "\n".join(achados)


def _linhas_com_string_aberta(js):
    """
    As linhas cuja contagem de aspas duplas e IMPAR.

    E o sintoma exato do defeito: uma string que abre e nao fecha na
    mesma linha, porque um \\n virou quebra de linha de verdade.
    """
    ruins = []
    for n, linha in enumerate(js.splitlines(), 1):
        sem_escape = linha.replace('\\"', "").replace("\\'", "")
        if sem_escape.lstrip().startswith(("//", "/*", "*")):
            continue
        if sem_escape.count('"') % 2:
            ruins.append((n, linha))
    return ruins


def test_a_CONFERENCIA_pega_uma_string_aberta():
    """
    O teste que prova o teste. Sem isto, os de baixo passariam mesmo
    cegos - e foi justamente um defeito silencioso que eles existem
    para pegar.
    """
    bom = 'if(!confirm("uma pergunta\\\\ncom quebra")){ return; }'
    assert _linhas_com_string_aberta(bom) == []

    # o defeito: a quebra de linha DE VERDADE no meio da string
    ruim = 'if(!confirm("uma pergunta\ncom quebra")){ return; }'
    assert len(_linhas_com_string_aberta(ruim)) == 2, \
        "a conferencia nao viu a string aberta"


def test_nenhuma_string_do_script_fica_ABERTA():
    """
    Uma aspa que abre e nao fecha na mesma linha e o sintoma exato do
    defeito: o \n virou quebra de linha dentro da string.
    """
    js = _script_da_pagina(servidor.pagina_da_fila([], None, tem_portao=True,
                                                   revisao=[]))
    ruins = _linhas_com_string_aberta(js)
    assert not ruins, "string aberta no script da fila: %s" % ruins


def test_o_script_TEM_os_tres_botoes_ligados():
    """Se o script quebrar, isto continua passando - por isso o de cima."""
    js = _script_da_pagina(servidor.pagina_da_fila([], None, tem_portao=True,
                                                   revisao=[]))
    assert "button.aprovar" in js
    assert "button.refazer" in js
    assert "limpar-revisao" in js


def test_o_bloco_da_revisao_com_itens_tambem_fica_valido():
    """A pagina com lista cheia e outra string - e ela tem os data-arquivo."""
    itens = [{"arquivo": "x_MONTAGEM.pdf", "quem_montou": "Pedro",
              "quando": "18/09/2026 16:00", "chapa": "PM 52", "grade": "2x1"}]
    html_ = servidor.pagina_da_fila([], None, tem_portao=True, revisao=itens)
    assert not _linhas_com_string_aberta(_script_da_pagina(html_))
    assert 'data-arquivo="x_MONTAGEM.pdf"' in html_


# --------------------------------------------------------------------------
# A TELA AVISA QUANDO O CODIGO NA MEMORIA JA NAO E O DO DISCO
# --------------------------------------------------------------------------
#
# 21/09/2026, o CONVITE CREDENCIAMENTO da AMERICA. O eudson-pc puxou o
# codigo novo e NAO reiniciou o run_montagem. Deu no pior dos dois
# mundos:
#
#   o painel ficou NOVO   - o HTML e lido do disco a cada pedido
#   o motor ficou VELHO   - modulo Python se le uma vez, ao subir
#
# O operador viu o seletor de giro novo, escolheu 0 graus, e o motor -
# que nao sabia o que era giro - deitou a peca assim mesmo. A tela
# prometeu 425 x 310 "Cabe" e o motor respondeu 205 x 640 "nao cabe".
#
# Nada daquilo parecia codigo velho, porque a metade que se VE estava
# nova. O vigia ja avisava disso na janela preta dele; aqui nao servia,
# porque quem usa a fila esta no navegador de OUTRA maquina e nunca ve
# janela preta nenhuma.

def test_sem_mudanca_no_disco_a_faixa_NAO_aparece(monkeypatch):
    monkeypatch.setattr(servidor, "RETRATO_DO_ARRANQUE", None)
    from finart_ctp import monitor
    agora = monitor.retrato_do_programa()
    monkeypatch.setattr(servidor, "RETRATO_DO_ARRANQUE", agora)
    assert servidor.codigo_que_mudou() == []
    assert "RODANDO CÓDIGO" not in servidor.pagina_da_fila(
        [], None, tem_portao=True, revisao=[])


def test_UM_PY_MUDADO_poe_a_faixa_na_tela(monkeypatch):
    from finart_ctp import monitor
    antes = dict(monitor.retrato_do_programa())
    # o disco andou: um arquivo com data diferente da que esta guardada
    algum = sorted(antes)[0]
    antes[algum] = antes[algum] - 60
    monkeypatch.setattr(servidor, "RETRATO_DO_ARRANQUE", antes)

    assert servidor.codigo_que_mudou() == [algum]
    pagina = servidor.pagina_da_fila([], None, tem_portao=True, revisao=[])
    assert "RODANDO CÓDIGO" in pagina
    assert algum in pagina, "a faixa tem de dizer QUAL arquivo mudou"
    assert "suba de novo" in pagina


def test_sem_retrato_guardado_nao_inventa_aviso(monkeypatch):
    """
    Quem importa o modulo sem passar pelo main() - os proprios testes -
    nao tem retrato. Sem ele a pergunta nao tem resposta, e calar e
    melhor do que acusar mudanca que ninguem sabe se houve.
    """
    monkeypatch.setattr(servidor, "RETRATO_DO_ARRANQUE", None)
    assert servidor.codigo_que_mudou() == []
    assert "RODANDO CÓDIGO" not in servidor.pagina_da_fila(
        [], None, tem_portao=True, revisao=[])
