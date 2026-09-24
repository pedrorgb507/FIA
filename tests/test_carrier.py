# -*- coding: utf-8 -*-
"""
A CARRIER - o segundo cliente que chega por uma pasta PARA CTP.

Pedido do operador em 24/09/2026: "gostaria de acrescentar como cliente
a Carrier (...) preciso que faca o processo da america, crie uma pasta
PARA CTP, e quando jogarmos la dentro vc segue o caminho de conferir o
arquivo, a pinca, a chapa, enviar para o ctp, gerar a OS no gempre e
tirar a prova, como ja faz com america, 724x615 com 6cm de pinca, e
510X400 com pinca 3,2 cm".

O QUE MUDOU NO CODIGO, e por que nao foi copiar: o america.py tinha
'AMERICA' cravado em 1356 linhas. Duplica-lo daria dois modulos
envelhecendo separados, e cada conserto - a pinca medida da marca, a
copia guardada antes de apagar, a conferencia da chapa inteira - teria
de ser feito duas vezes. Entao o cliente virou PARAMETRO, com a AMERICA
de padrao: por isso os 68 testes que ja existiam nao mudaram uma linha.

ESTE ARQUIVO GUARDA OS DOIS LADOS: que a CARRIER responde com os numeros
dela, e que a AMERICA continua respondendo com os dela.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from finart_ctp import america                                # noqa: E402
from finart_ctp.config import (GEREMPRE_CHAPAS,               # noqa: E402
                               GEREMPRE_CLIENTES, PORTAO_AMERICA,
                               PORTAO_CARRIER, PORTOES)

COLORIDO = {"C", "M", "Y", "K"}
PEB = {"GRAY"}


# ----------------------------------------------------------------------
# As duas chapas, e as pincas que ele ditou
# ----------------------------------------------------------------------

def test_as_duas_chapas_da_carrier():
    assert america.chapa_de(510, 400, PORTAO_CARRIER) == (510, 400)
    assert america.chapa_de(724, 615, PORTAO_CARRIER) == (724, 615)


def test_as_pincas_ditadas_pelo_operador():
    """'724x615 com 6cm de pinca, e 510X400 com pinca 3,2 cm'."""
    assert america.pinca_de((510, 400), PORTAO_CARRIER) == 32.0
    assert america.pinca_de((724, 615), PORTAO_CARRIER) == 60.0


def test_a_chapa_da_AMERICA_nao_serve_a_CARRIER():
    """
    A prova de que a tabela e mesmo por cliente. A 525x459 e da AMERICA;
    pedindo-a a CARRIER, nao ha chapa - e vice-versa.
    """
    assert america.chapa_de(525, 459, PORTAO_CARRIER) is None
    assert america.chapa_de(510, 400, PORTAO_AMERICA) is None


# ----------------------------------------------------------------------
# Qual chapa recebe o trabalho
# ----------------------------------------------------------------------

def test_o_que_cabe_no_formato_4_vai_na_pequena():
    chapa, _ = america.onde_montar(300, 200, COLORIDO, PORTAO_CARRIER)
    assert chapa == (510, 400)


def test_o_que_passa_do_formato_4_vai_na_grande():
    chapa, _ = america.onde_montar(700, 500, COLORIDO, PORTAO_CARRIER)
    assert chapa == (724, 615)


def test_na_CARRIER_o_PRETO_E_BRANCO_nao_muda_de_chapa():
    """
    A AMERICA manda peb para a MOZP e colorido para a SM_74 - sao
    MAQUINAS diferentes. A CARRIER nao tem essa divisao: as chapas dela
    sao da FINART e nao carregam nome de maquina.

    Copiando a regra da AMERICA para ca sem pensar, este teste cai.
    """
    # 600x450 de proposito: cabe NAS DUAS chapas grandes da AMERICA,
    # entao a escolha ali e mesmo pela cor e nao por caber. Com 700x500
    # a MOZP nao caberia e a comparacao nao provaria nada.
    colorida, _ = america.onde_montar(600, 450, COLORIDO, PORTAO_CARRIER)
    preta, _ = america.onde_montar(600, 450, PEB, PORTAO_CARRIER)
    assert colorida == preta == (724, 615)


def test_na_AMERICA_o_PRETO_E_BRANCO_CONTINUA_mudando_de_chapa():
    """O outro lado: nada do que eu fiz mexeu na regra dela."""
    colorida, _ = america.onde_montar(600, 450, COLORIDO, PORTAO_AMERICA)
    preta, _ = america.onde_montar(600, 450, PEB, PORTAO_AMERICA)
    assert colorida == (745, 605), "colorido grande vai na SM_74"
    assert preta == (650, 550), "preto e branco grande vai na MOZP"


def test_o_que_nao_cabe_PARA_dizendo_o_cliente():
    chapa, porque = america.onde_montar(2000, 2000, COLORIDO, PORTAO_CARRIER)
    assert chapa is None
    assert "CARRIER" in porque


# ----------------------------------------------------------------------
# O dpi e o nome da chapa
# ----------------------------------------------------------------------

def test_o_dpi_e_1000_na_pequena_e_800_na_grande():
    """
    Regra da casa, nao invencao: 1000 na pequena como em todo cliente, e
    800 acima do formato 4 - chapa grande em 1000 da arquivo enorme sem
    ninguem ver diferenca.
    """
    assert america.dpi_da_america((510, 400), PORTAO_CARRIER) == 1000
    assert america.dpi_da_america((724, 615), PORTAO_CARRIER) == 800


def test_o_nome_da_chapa_segue_o_padrao_DA_CASA():
    """
    <formato>_<cores>_<CLIENTE>_<descricao>. Nao e invencao minha: e o
    que os operadores ja escrevem a mao no CTP -
    '510X400_CMYK_VOPRIX_Calendario_Mesa_LAS_01' e
    '745x605_GRAY_APARECIDA_Einstein_Env_Kraft'.
    """
    nome = america.nome_da_chapa("x/ADESIVOS BOLAS_MONTAGEM.pdf",
                                 510, 400, COLORIDO, PORTAO_CARRIER)
    assert nome == "510x400_CMYK_CARRIER_ADESIVOS BOLAS"


def test_o_nome_da_AMERICA_continua_dizendo_AMERICA():
    nome = america.nome_da_chapa("x/Flyer_MONTAGEM.pdf",
                                 525, 459, COLORIDO, PORTAO_AMERICA)
    assert nome == "525x459_CMYK_AMERICA_Flyer"


# ----------------------------------------------------------------------
# As pastas
# ----------------------------------------------------------------------

def test_a_CARRIER_tem_SO_a_PARA_CTP():
    """
    'crie uma pasta PARA CTP' - o operador. A montagem dela e feita a mao
    por eles, fora da FIA, entao a PARA MONTAR nao teria quem a enchesse
    nem quem a esvaziasse. Pasta vazia que ninguem usa vira lugar onde
    arquivo se perde.
    """
    assert america.subpastas_do_dia(PORTAO_CARRIER) == ("PARA CTP",)


def test_a_AMERICA_continua_com_as_DUAS():
    subs = america.subpastas_do_dia(PORTAO_AMERICA)
    assert "PARA CTP" in subs and "PARA MONTAR" in subs


def test_a_pasta_vem_do_config_local_e_nao_do_de_fabrica():
    """
    A ARMADILHA EM QUE EU CAI AO ESCREVER ISTO, e que o config ja
    documentava no CAIXAS_TEAMS: o descritor guarda o NOME da
    configuracao, nao o valor, porque o config_local e aplicado DEPOIS do
    bloco dos portoes. Guardando o valor, a AMERICA ficava apontando para
    a pasta de fabrica, que nao existe nesta maquina.

    Portao apontado para pasta errada NAO DA ERRO: ele so nunca acha
    arquivo nenhum, para sempre, em silencio.
    """
    import finart_ctp.config as C
    for portao in PORTOES:
        assert isinstance(portao["base"], str)
        assert portao["base"].startswith("BASE_"), (
            "o portao tem de guardar o NOME da configuracao")
        assert getattr(C, portao["base"])


# ----------------------------------------------------------------------
# O GEREMPRE
# ----------------------------------------------------------------------

def test_a_CARRIER_esta_cadastrada_no_gerempre():
    """479, 'GRAFICA CARRIER' - a unica com esse nome no cadastro."""
    assert GEREMPRE_CLIENTES["CARRIER"] == 479


def test_as_chapas_sao_DA_FINART_e_os_precos_batem_com_o_banco():
    """
    'os valores no gerempre sao as chapas da FINART, o cliente nao
    fornece, chapa pequena 20,00 e chapa grande 35,00' - o operador.

    Conferido contra as 200 OS mais recentes do cliente 479 ANTES de
    escrever, como manda a armadilha 14: item 12 a R$ 20,00 em 235 de 236
    lancamentos, item 17 a R$ 35,00 em 174 de 174, os dois com
    RBCHAPAPRO = 1.

    'propria' e o que faz a baixa sair do estoque da FINART. Trocar por
    'cliente' baixaria chapa de quem nao a forneceu - e isso nao da erro
    em lugar nenhum, so um estoque que nao fecha no fim do mes.
    """
    pequena = GEREMPRE_CHAPAS[("CARRIER", (510, 400))]
    grande = GEREMPRE_CHAPAS[("CARRIER", (724, 615))]
    assert pequena[0] == 12 and pequena[2] == 20.00
    assert pequena[3] == "propria"
    assert grande[0] == 17 and grande[2] == 35.00
    assert grande[3] == "propria"


def test_TODA_chapa_do_portao_tem_cadastro_no_gerempre():
    """
    Senao a chapa grava e a OS nao sai - foi o que aconteceu com a IDEAL,
    cujo cadastro de cliente faltava e so apareceu no SEGUNDO arquivo,
    porque completar OS que ja existe nao precisa do codigo do cliente.
    """
    for portao in PORTOES:
        cliente = portao["cliente"]
        assert cliente in GEREMPRE_CLIENTES, cliente
        for medida in portao["chapas"]:
            assert (cliente, medida) in GEREMPRE_CHAPAS, (cliente, medida)


def test_os_dois_portoes_estao_na_lista_que_o_vigia_varre():
    assert [p["cliente"] for p in PORTOES] == ["AMERICA", "CARRIER"]


def test_a_pasta_do_dia_de_CADA_portao_sai_na_base_DELE(tmp_path,
                                                        monkeypatch):
    """
    O DEFEITO MUDO DE 24/09/2026: o garantir_pastas_do_dia montava o
    caminho com BASE_AMERICA mesmo recebendo o portao da CARRIER, e
    criou a pasta da CARRIER DENTRO da AMERICA.

    E nao deu erro nenhum - ele respondeu 'ja existiam', porque a PARA
    CTP da AMERICA existe mesmo. So olhando o caminho impresso e que
    apareceu.

    Por isso este teste olha ONDE a pasta foi parar, e nao se a chamada
    deu certo.
    """
    import finart_ctp.config as C
    casa_carrier = tmp_path / "carrier"
    casa_america = tmp_path / "america"
    monkeypatch.setattr(C, "BASE_CARRIER", str(casa_carrier))
    monkeypatch.setattr(C, "BASE_AMERICA", str(casa_america))

    dia, _, erro = america.garantir_pastas_do_dia(portao=PORTAO_CARRIER)
    assert erro is None
    assert str(casa_carrier) in dia, "a CARRIER saiu fora da base dela"
    assert str(casa_america) not in dia
    assert os.path.isdir(os.path.join(dia, "PARA CTP"))
    # e a PARA MONTAR NAO se cria aqui - ela nao tem quem a use
    assert not os.path.isdir(os.path.join(dia, "PARA MONTAR"))
    # a AMERICA nem foi tocada
    assert not casa_america.exists()


# ----------------------------------------------------------------------
# A CLASSE DE ERRO QUE ESTE TRABALHO PRODUZIU
# ----------------------------------------------------------------------

def test_NENHUMA_chamada_do_modulo_esquece_o_portao():
    """
    O defeito de 24/09/2026, e ele apareceu na PROVA do cliente.

    Ao tornar o america.py multi-cliente eu passei o portao pelas
    assinaturas e esqueci CINCO chamadas internas. Elas continuaram
    valendo AMERICA, e o primeiro fechamento da CARRIER imprimiu:

        ATENCAO: pela regra (ate F4, colorido) este trabalho iria para a
                 chapa 525x459, mas o arquivo veio 510x400

    525x459 e chapa da AMERICA. O operador viu o nome errado no papel.

    QUATRO DAS CINCO ERAM MUDAS - so esta imprimia um numero. As outras
    teriam escolhido chapa, pinca e dpi do cliente errado sem dizer
    nada.

    Este teste nao guarda as cinco: guarda a CLASSE. Qualquer chamada
    nova que esqueca o portao cai aqui.
    """
    import io as _io
    import re
    import finart_ctp.america as A

    # as funcoes que dependem do cliente - todas recebem 'portao'
    com_portao = ("chapa_de", "pinca_de", "cabe_na_chapa",
                  "maquina_da_america", "onde_montar", "dpi_da_america",
                  "nome_da_chapa", "conferir_a_pinca", "ajustar_a_pinca",
                  "pe_da_montagem", "do_pdf_pronto", "subpastas_do_dia",
                  "pasta_do_dia_america", "garantir_pastas_do_dia")
    linhas = _io.open(A.__file__, encoding="utf-8").read().splitlines()
    faltando = []
    for i, linha in enumerate(linhas, start=1):
        texto = linha.strip()
        # comentario, definicao e docstring nao sao chamada
        if texto.startswith("#") or texto.startswith("def ") \
                or texto.startswith('"'):
            continue
        for nome in com_portao:
            if not re.search(r"(?<![\w.])" + nome + r"\(", linha):
                continue
            if "portao" in linha:
                break
            # a chamada pode continuar na linha seguinte
            if i < len(linhas) and "portao" in linhas[i]:
                break
            faltando.append("%d: %s" % (i, texto[:70]))
            break
    assert not faltando, (
        "estas chamadas usariam o cliente errado:\n  "
        + "\n  ".join(faltando))


def test_PERGUNTA_antes_de_anunciar_a_conversao():
    """
    O LACO DE 24/09/2026: o mesmo 'Cartao de Visitas' anunciado 23 vezes
    em tres minutos.

    O anuncio vinha ANTES da pergunta: escrevia-se "convertendo no
    CorelDRAW..." e so entao o converter_cdr descobria o arquivo aberto
    na sessao de alguem. Arquivo aberto vira 'adiado' e NAO entra no
    registro - de proposito, para ser tentado quando fecharem -, entao
    voltava a cada volta do vigia e o anuncio saia junto. O motivo e
    dito UMA vez, pelo monitor, que guarda os adiados; o anuncio e que
    nao tinha limite.

    Janela que so repete deixa de ser lida - e e nela que a FIA avisa
    quando alguma coisa custa chapa.

    LE A ORDEM NO FONTE: dirigir o _processar_pdf inteiro ate aqui daria
    um teste preso a meia duzia de passos que nao tem nada com isto. O
    que quebrou foi a ORDEM, e e a ordem que fica guardada.
    """
    import io as _io
    import finart_ctp.processador as P
    fonte = _io.open(P.__file__, encoding="utf-8").read()
    pergunta = fonte.index("if em_uso(caminho):")
    anuncio = fonte.index("convertendo no CorelDRAW")
    assert pergunta < anuncio, (
        "o anuncio voltou a vir antes da pergunta - e o laco volta com ele")


def test_em_uso_NAO_LEVANTA_quando_o_corel_nao_responde(monkeypatch):
    """
    Nao poder perguntar nao e o mesmo que estar em uso.

    Levantando aqui, um CorelDRAW fechado pararia todo .cdr da casa - e
    o caminho normal e justamente abrir o Corel quando ele nao esta
    aberto.
    """
    import finart_ctp.corel as CO

    def caiu():
        raise RuntimeError("Corel fora do ar")

    monkeypatch.setattr(CO, "_aplicacao", caiu)
    assert CO.em_uso("x.cdr") is False


# ----------------------------------------------------------------------
# O arquivo aberto no CorelDRAW nao pode virar ruido
# ----------------------------------------------------------------------

def test_o_ADIADO_que_segue_aberto_passa_CALADO():
    """
    24/09/2026: o mesmo 'Cartao de Visitas' encabecando a janela dezenas
    de vezes em poucos minutos.

    Arquivo aberto no CorelDRAW de alguem vira 'adiado' e NAO entra no
    registro - de proposito, para ser tentado quando fecharem. So que
    isso o traz de volta a cada volta do vigia, e cada volta abria um
    bloco na tela. O motivo e dito UMA vez e some no meio da repeticao.

    Agora, para quem ja esta nos adiados, pergunta-se PRIMEIRO: seguindo
    aberto, a volta termina ali - sem bloco, sem tentativa, sem linha.

    LE A ORDEM NO FONTE: a pergunta tem de vir ANTES do abrir_bloco,
    senao o cabecalho ja saiu quando se descobre que nao havia o que
    dizer.
    """
    import io as _io
    import finart_ctp.monitor as M
    fonte = _io.open(M.__file__, encoding="utf-8").read()
    pergunta = fonte.index("if chave in adiados and nome.lower()")
    bloco = fonte.index("abrir_bloco(cliente, nome)")
    assert pergunta < bloco, "o cabecalho voltou a sair antes da pergunta"


def test_quem_FECHOU_o_arquivo_volta_ao_caminho_normal():
    """
    A outra metade, e sem ela o conserto viraria um arquivo que nunca
    mais e feito: fechando o .cdr, ele SAI da lista dos adiados e a
    volta seguinte o trata como sempre.
    """
    import io as _io
    import finart_ctp.monitor as M
    fonte = _io.open(M.__file__, encoding="utf-8").read()
    trecho = fonte[fonte.index("if chave in adiados and nome.lower()"):]
    trecho = trecho[:trecho.index("abrir_bloco(cliente, nome)")]
    assert "adiados.discard(chave)" in trecho, (
        "fechando o arquivo, ele tem de sair da lista - senao nunca mais "
        "e feito")


# ----------------------------------------------------------------------
# A FIA TRANCADA CONTRA SI MESMA - 24/09/2026
# ----------------------------------------------------------------------
# O 'Cartao de Visitas' da PRIME nunca era feito. A cada volta a FIA
# dizia que ele estava "aberto no CorelDRAW" e adiava. O operador: "nao
# tem ninguem com esse arquivo aberto no corel".
#
# Nao tinha mesmo. O CorelDRAW estava com app.Visible = False - a
# sessao de automacao da PROPRIA FIA - e o documento estava ali, sem
# alteracao nenhuma, deixado por uma conversao que nao chegou a fechar
# (o vigia foi reiniciado no meio).
#
# A RAIZ ERA UMA SUPOSICAO NO NOME: o _documento_aberto respondia 'este
# arquivo esta aberto' e o docstring dele chamava aquilo de 'o documento
# DO OPERADOR'. Ele nao sabe de quem e. Quem le o nome, acredita.
# ----------------------------------------------------------------------

class _AppFalso(object):
    def __init__(self, visivel, docs):
        self.Visible = visivel
        self._docs = list(docs)

    class _Docs(object):
        def __init__(self, fora):
            self._fora = fora

        @property
        def Count(self):
            return len(self._fora._docs)

        def Item(self, i):
            return self._fora._docs[i - 1]

    @property
    def Documents(self):
        return _AppFalso._Docs(self)


class _DocFalso(object):
    def __init__(self, caminho, dirty=False, app=None):
        self.FullFileName = caminho
        self.Dirty = dirty
        self._app = app

    def Close(self):
        self._app._docs.remove(self)


def _com(visivel, dirty=False, caminho=None):
    import os as _os
    caminho = caminho or _os.path.abspath("x.cdr")
    app = _AppFalso(visivel, [])
    app._docs.append(_DocFalso(caminho, dirty, app))
    return app, caminho


def test_sessao_INVISIVEL_e_nossa_e_a_sobra_se_libera():
    """Sem gente na tela, documento aberto ali e sobra nossa."""
    import finart_ctp.corel as CO
    app, caminho = _com(visivel=False)
    assert CO._sobra_nossa(app, caminho) is True
    assert app.Documents.Count == 0, "tinha de ter fechado"


def test_sessao_VISIVEL_e_de_gente_e_NAO_se_toca():
    """
    Com o Corel aberto na tela de alguem, o arquivo e dele. Fechar seria
    tirar o trabalho da mao da pessoa.
    """
    import finart_ctp.corel as CO
    app, caminho = _com(visivel=True)
    assert CO._sobra_nossa(app, caminho) is False
    assert app.Documents.Count == 1, "nao se fecha arquivo de ninguem"


def test_documento_COM_ALTERACAO_nao_se_descarta():
    """
    Mesmo na nossa sessao. 'Dirty' quer dizer que alguma coisa foi
    mexida ali, e descartar em silencio seria jogar trabalho fora.
    """
    import finart_ctp.corel as CO
    app, caminho = _com(visivel=False, dirty=True)
    assert CO._sobra_nossa(app, caminho) is False
    assert app.Documents.Count == 1


def test_arquivo_que_NEM_ESTAVA_aberto_passa_direto():
    import finart_ctp.corel as CO
    app = _AppFalso(False, [])
    assert CO._sobra_nossa(app, "qualquer.cdr") is True


def test_nao_conseguindo_perguntar_se_ha_gente_TRATA_COMO_SE_HOUVESSE():
    """
    O erro barato e esperar; o caro e fechar o arquivo de alguem.
    """
    import finart_ctp.corel as CO

    class Mudo(object):
        @property
        def Visible(self):
            raise RuntimeError("nao respondo")

    assert CO._tem_gente_olhando(Mudo()) is True


# ----------------------------------------------------------------------
# O aviso que voltava a cada reinicio - 24/09/2026
# ----------------------------------------------------------------------

def test_o_aviso_de_arquivo_estranho_SOBREVIVE_ao_reinicio(tmp_path,
                                                           monkeypatch):
    """
    O '02040 - CHAPA - Agnus Sacola' da EMPORIO reclamou as 15:47,
    15:59, 16:17 e 16:46 - uma vez por arranque do vigia.

    O aviso SEMPRE foi 'uma vez por arquivo'. So que 'uma vez' valia
    enquanto o processo estivesse de pe: o set morria no reinicio. Num
    dia de reinicios, o mesmo arquivo reclama a cada um deles, e o
    operador le a mesma pendencia sem parar.

    Aqui se simula exatamente isso: DOIS 'arranques', cada um com o seu
    set novo em folha.
    """
    import finart_ctp.monitor as M
    import finart_ctp.utils as U
    import finart_ctp.config as C

    monkeypatch.setattr(C, "PASTA_CONTROLE", str(tmp_path))
    ditas = []
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda *a, **k: ditas.append(a[0]))

    arq = tmp_path / "arte estranha.cdr"
    arq.write_bytes(b"cdr")

    # primeiro arranque
    M.avisar_arquivo_estranho(str(arq), arq.name, "EMPORIO", (".pdf",),
                              set())
    # segundo arranque - set NOVO, como depois de reiniciar
    M.avisar_arquivo_estranho(str(arq), arq.name, "EMPORIO", (".pdf",),
                              set())

    assert len(ditas) == 1, (
        "reclamou de novo depois do reinicio: %s" % ditas)


def test_arquivo_TROCADO_por_outra_versao_reclama_de_novo(tmp_path,
                                                          monkeypatch):
    """
    A outra metade, e sem ela o conserto viraria silencio perigoso: o
    mesmo nome com conteudo NOVO e outro arquivo, e sobre esse vale
    reclamar. A chave e nome|tamanho|data, a mesma do registro.
    """
    import finart_ctp.monitor as M
    import finart_ctp.config as C

    monkeypatch.setattr(C, "PASTA_CONTROLE", str(tmp_path))
    ditas = []
    monkeypatch.setattr(M, "anotar_pendencia",
                        lambda *a, **k: ditas.append(a[0]))

    arq = tmp_path / "arte estranha.cdr"
    arq.write_bytes(b"primeira versao")
    M.avisar_arquivo_estranho(str(arq), arq.name, "EMPORIO", (".pdf",),
                              set())

    arq.write_bytes(b"uma versao bem diferente, com outro tamanho")
    M.avisar_arquivo_estranho(str(arq), arq.name, "EMPORIO", (".pdf",),
                              set())

    assert len(ditas) == 2, "versao nova tem de reclamar de novo"


def test_a_memoria_do_aviso_NAO_DERRUBA_a_varredura(tmp_path,
                                                    monkeypatch):
    """
    Isto e memoria de aviso, nao trabalho. Falhando a escrita, o pior
    que pode acontecer e reclamar de novo no proximo arranque - que e
    como era antes. Estourar seria trocar ruido por varredura parada.
    """
    import finart_ctp.utils as U
    import finart_ctp.config as C

    monkeypatch.setattr(C, "PASTA_CONTROLE",
                        str(tmp_path / "pasta que nao existe"))
    assert U.carregar_avisados() == set()
    U.guardar_avisado("x|1|2")          # nao pode estourar
