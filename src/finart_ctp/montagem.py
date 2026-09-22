# -*- coding: utf-8 -*-
r"""
A montagem da AMERICA: o que falta montar, e quem montou o que.

ESTE MODULO NAO ESCREVE NA PASTA DO CLIENTE. Ele le o portao, pergunta ao
registro e responde. Quem monta de verdade - e quem grava a montagem na
pasta do dia - vem depois, e mora aqui tambem quando chegar.

O PORTAO, e por que ele e um portao novo:

    X:\AMERICA\<Mes>\<Dia>\                <- a pasta do dia
    X:\AMERICA\<Mes>\<Dia>\PARA MONTAR\    <- o que FALTA montar
    X:\AMERICA\<Mes>\<Dia>\PARA CTP\       <- o que ja foi revisado

Os dois portoes sao irmaos e tem sentidos opostos. A 'PARA CTP' e o fim
do caminho: o que esta nela uma pessoa aprovou, e o vigia a fecha e apaga
(ver america.py). A 'PARA MONTAR' e o comeco: o que esta nela e materia
-prima, e montar e decisao de gente que sabe a regra da casa.

POR QUE NAO BASTAVA A PASTA DO DIA. Ela acumula tres coisas ao mesmo
tempo - o que chegou por montar, a montagem gravada e as copias que sobem
da 'PARA CTP' quando o vigia arruma o portao. Com uma pessoa so isso
dava, porque ela sabia de cabeca qual era qual. Com a equipe inteira
mexendo, a pasta do dia deixa de responder "o que falta?" - e essa era
justamente a pergunta que so uma pessoa sabia responder.

DUAS COISAS NAO ENTRAM NA FILA, e as duas por erro que ja custou:

  - arquivo que ainda esta CHEGANDO pela rede. Uma montagem tem
    megabytes, e medir pela metade daria formato errado - e formato
    errado escolhe a chapa errada;
  - arquivo que JA FOI MONTADO. Refazer duplica arquivo e trabalho:
    sairiam duas montagens do mesmo servico na pasta do dia, e alguem
    revisaria as duas.

O REGISTRO E UM ARQUIVO A PARTE do das chapas, e de proposito. O
_processados.json responde "esta chapa ja foi para o CTP?"; este responde
"este arquivo ja foi montado, e por quem?". Sao perguntas diferentes, e
misturadas a fila sumiria com arquivo que so passou pelo CTP - ou seja,
esconderia trabalho por fazer.
"""

import io
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timedelta
from urllib.parse import quote

from . import america, marcas, nomes, paginacao, sangria, utils
from .config import SUBPASTA_PARA_MONTAR
from .utils import arquivos_estaveis, chave_arquivo

PORTAO = SUBPASTA_PARA_MONTAR

# Onde mora o motor de imposicao - ver _motor().
FERRAMENTAS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "ferramentas")

# O QUE ENTRA NO PORTAO.
#
# PDF e o que se monta. O .CDR entra porque a AMERICA manda .cdr - e ele
# nao vira chapa direto: e PUBLICADO em PDF pelo motor da propria Corel,
# em vetor, e o PDF e que entra na fila. NAO SE RASTERIZA, ao contrario
# do .cdr da VOPRIX e do da PRIME: a AMERICA manda a imagem ja dentro do
# arquivo, e rasterizar de novo so perderia.
#
# Do WhatsApp vem de tudo junto: a mensagem em .txt, o print da conversa,
# a planilha. Nada disso se monta, e nada disso e pendencia - e so o que
# veio na mesma leva.
EXTENSOES = (".pdf", ".cdr")

REGISTRO = "_montagens.json"

# E A MEDIDA DE CADA ARQUIVO, guardada para nao se refazer.
#
# NAO E O MESMO ARQUIVO DO REGISTRO, e nao e registro de nada: e so o
# retrato do que se mediu, e pode ser apagado a qualquer momento sem
# perder nada - a proxima olhada mede de novo. O registro, esse sim,
# guarda decisao de gente.
MEDIDAS = "_medidas_montagem.json"

# QUANTAS COISAS O RETRATO GUARDA. Sobe de numero sempre que a fila passa
# a medir algo novo - subiu para 3 quando entrou a medida do corte.
#
# Sem isto, retrato tirado por uma versao anterior sobrevive a troca de
# codigo: a chave e do ARQUIVO - nome|tamanho|data -, e o arquivo nao
# mudou. Quando a sangria entrou na fila, os que ja estavam no portao
# ficariam com 'nao da para saber' para sempre - e 'nao da para saber' e
# justamente a resposta que a coluna existe para nao dar de graca.
VERSAO_DA_MEDIDA = 3

# A TRANCA DOS ARQUIVOS DESTE MODULO.
#
# Ela nasceu quando a fila virou servidor. Ate ali, quem gravava era um
# programa por vez e bastava renomear de uma vez; agora o
# ThreadingHTTPServer atende cada pedido numa LINHA, e duas pessoas
# atualizando a tela juntas sao duas linhas do MESMO processo mexendo nos
# mesmos arquivos. Sem tranca, as duas leem, as duas gravam, e a segunda
# apaga o que a primeira escreveu.
#
# E RE-ENTRANTE porque as funcoes daqui se chamam umas as outras - quem
# ja tem a tranca na mao pode pega-la de novo sem se enforcar.
#
# O QUE ELA NAO RESOLVE, e nao e para resolver: dois PROCESSOS. A tranca
# vale dentro de um; para o outro, o que vale e gravar de uma vez, por um
# temporario com nome unico. As duas coisas juntas cobrem o que ha.
_TRANCA = threading.RLock()

# Os arquivos que ESTAO SENDO MONTADOS agora, por chave. Ver executar():
# montar leva segundos, e o servidor existe justamente para haver duas
# pessoas montando ao mesmo tempo.
_MONTANDO = set()


def pastas_da_montagem():
    r"""(pasta_do_dia, pasta do PARA MONTAR) de HOJE, ou (None, None).

    A pasta do dia sai do mesmo lugar que a do outro portao - de
    america.pasta_do_dia_america -, para os dois nunca discordarem sobre
    que dia e hoje nem sobre como o mes esta escrito no servidor.

    SO HOJE, e nao uma data qualquer: o portao e a fila do dia. Quem
    precisar de um dia passado usa utils.pasta_da_data, que e quem sabe
    fazer isso - pedir outro dia aqui devolveria o de hoje calado.
    """
    dia, _ = america.pasta_do_dia_america()
    if not dia:
        return None, None
    return dia, os.path.join(dia, PORTAO)


def preparar_o_dia():
    r"""
    Garante a pasta do dia da AMERICA e os dois portoes. (portao, erro).

    E o mesmo america.garantir_pastas_do_dia que o vigia chama a cada
    volta - aqui de novo, porque o servidor da fila e OUTRO PROCESSO. Nao
    e desperdicio: nao havendo o que criar, sao tres os.path.isdir.

    POR QUE OS DOIS CHAMAM. A equipe abre a tela do PC dela, e pode abrir
    antes de alguem ligar a FIA na maquina da casa. Se so o vigia
    criasse, essa pessoa veria 'nao consegui preparar a pasta' sem haver
    defeito nenhum - so ordem de chegada. Quem chegar primeiro cria.

    O 'erro' sobe em vez de virar excecao: a tela precisa CONTAR o que
    houve, e uma pagina de erro sem motivo nao ajuda ninguem.
    """
    dia, criados, erro = america.garantir_pastas_do_dia()
    if criados:
        utils.log("MONTAGEM: preparei a pasta do dia - criei %s"
                  % ", ".join("'%s'" % c for c in criados))
    if not dia:
        return None, erro
    return os.path.join(dia, PORTAO), erro


def portao_existe(portao=None):
    """
    A pasta do portao esta la?

    E pergunta diferente de 'a fila esta vazia', e confundi-las engana
    quem esta olhando: numa manha sem portao, fila vazia e resposta
    errada - a equipe iria embora achando que nao havia trabalho.

    O QUE A AUSENCIA QUER DIZER MUDOU EM 18/09/2026. Enquanto o portao
    era criado por gente, faltar era normal. Agora quem o cria e a FIA
    - o vigia a cada volta, e a tela a cada desenho -, entao faltar so
    pode ser a FIA nao alcancando a pasta da AMERICA no servidor. A
    pergunta e a mesma; a resposta 'nao' ficou mais grave.
    """
    if portao is None:
        _, portao = pastas_da_montagem()
    return bool(portao) and os.path.isdir(portao)


def caminho_do_registro():
    return os.path.join(utils.PASTA_CONTROLE, REGISTRO)


def caminho_das_medidas():
    return os.path.join(utils.PASTA_CONTROLE, MEDIDAS)


def _ler_dicionario(caminho):
    """
    O que esta escrito naquele arquivo, ou {}. NUNCA ESTOURA.

    LE VAZIO QUANDO O ARQUIVO ESTA ESTRAGADO - JSON pela metade, da
    maquina desligada no meio de uma gravacao. O pior que acontece lendo
    vazio e uma montagem ser oferecida duas vezes, ou uma medida ser
    refeita; estourar aqui seria tela de erro para a equipe inteira.

    E ESTRAGADO INCLUI 'JSON VALIDO QUE NAO E UM DICIONARIO'. Um arquivo
    com '[]' dentro passa pelo json.load e depois estoura la na frente,
    na hora de gravar - longe daqui, com outra cara.
    """
    try:
        with io.open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def _gravar_dicionario(caminho, dados):
    """
    Grava DE UMA VEZ: escreve num temporario e renomeia por cima.

    O NOME DO TEMPORARIO LEVA O PROCESSO E A LINHA, e nao um nome fixo.
    Dois que gravem ao mesmo tempo no mesmo temporario fazem o renomeado
    sair com dois JSON emendados - e ai a leitura devolve vazio e TODA
    montagem ja feita volta para a fila, que e exatamente o trabalho
    duplicado que o registro existe para impedir.

    O PROCESSO NAO BASTAVA: desde que a fila virou servidor, duas pessoas
    atualizando a tela juntas sao duas LINHAS do mesmo processo, com o
    mesmo numero. O primeiro comentario aqui dizia que o pid resolvia -
    resolvia o caso de ontem, nao o de hoje.
    """
    os.makedirs(utils.PASTA_CONTROLE, exist_ok=True)
    tmp = "%s.%d.%d.tmp" % (caminho, os.getpid(), threading.get_ident())
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)


def carregar_montagens():
    """O que ja foi montado, por chave de arquivo."""
    return _ler_dicionario(caminho_do_registro())


def ja_montado(caminho, registro=None):
    """Este arquivo AQUI ja foi montado?

    A chave e a da casa - nome|tamanho|data -, a mesma dos outros seis
    clientes: ela reconhece 'este arquivo', e nao 'um arquivo com este
    nome'. Arquivo que a AMERICA mandou de novo, corrigido, tem tamanho
    ou data diferente e volta a ser trabalho, que e o certo.
    """
    registro = carregar_montagens() if registro is None else registro
    return chave_arquivo(caminho) in registro


def anotar_montagem(caminho, o_que, chave=None):
    """
    Deixa dito que este arquivo foi montado, e por quem.

    GRAVA JUNTANDO com o que esta no disco, e nao por cima - a licao do
    salvar_registro, que ja custou uma chapa refeita quando era o vigia
    contra uma rodada avulsa. Relendo antes de gravar, o trabalho de quem
    gravou no meio nao se perde.

    LER E GRAVAR ACONTECE COM A TRANCA NA MAO. Duas pessoas montando ao
    mesmo tempo sao duas linhas deste processo, e sem a tranca as duas
    leem o mesmo registro e a segunda grava por cima da primeira - a
    decisao de alguem sobre uma chapa desapareceria sem ninguem ver.

    Sobra o caso de dois PROCESSOS, que a tranca nao alcanca: ali o que
    vale e o gravar de uma vez, e o pior que acontece e uma montagem ser
    oferecida de novo.
    """
    entrada = dict(o_que or {})
    entrada.setdefault("arquivo", os.path.basename(caminho))
    entrada.setdefault("quando", datetime.now().strftime("%d/%m/%Y %H:%M"))
    try:
        # A CHAVE PODE VIR PRONTA, e quem monta passa a dela: la o
        # original ja SAIU do portao quando se anota - e a chave se tira
        # do arquivo, que nao esta mais onde estava. Tirando-a aqui, a
        # gravacao falhava calada e a montagem ficava sem dono.
        chave = chave_arquivo(caminho) if chave is None else chave
        with _TRANCA:
            tudo = carregar_montagens()
            tudo[chave] = entrada
            _gravar_dicionario(caminho_do_registro(), tudo)
    except OSError as e:
        utils.log("MONTAGEM: nao consegui gravar o registro: %s" % e,
                  alerta=True)
        return None
    return entrada


def fila(portao=None):
    """
    Os caminhos do que esta esperando montagem, em ordem de nome.

    NAO ESCREVE NADA - nem no portao, nem na pasta do dia, nem no
    registro. E o '--olhar' da casa: conferir nao muda nada.

    Fica de fora o que ainda esta chegando pela rede e o que ja foi
    montado antes (ver o cabecalho do modulo). Portao que nao existe
    devolve lista vazia, e nao pilha de erro: quem quis so conferir nao
    merece uma tela quebrada. Dizer que ISSO E DEFEITO e trabalho de
    quem desenha a tela, com o preparar_o_dia na mao - aqui nao se
    escreve nada, e essa e a regra da funcao.

    A ORDEM E POR NOME, e nao a do sistema de arquivos: duas pessoas
    olhando a fila ao mesmo tempo precisam ver a mesma coisa na mesma
    ordem para nao pegarem as duas o mesmo servico.

    E O BARATO VEM ANTES DO CARO. O registro se le uma vez para a fila
    inteira, e a espera da rede - dois segundos - acontece uma vez para o
    que sobrou, e nao uma por arquivo. Perguntando um a um, um portao com
    vinte arquivos deixaria a tela de gente pendurada quarenta segundos.
    """
    if portao is None:
        _, portao = pastas_da_montagem()
    if not portao or not os.path.isdir(portao):
        return []

    registro = carregar_montagens()
    candidatos = []
    for nome in sorted(os.listdir(portao)):
        caminho = os.path.join(portao, nome)
        try:
            if not os.path.isfile(caminho):
                continue
            if not nome.lower().endswith(EXTENSOES):
                continue
            if ja_montado(caminho, registro):
                continue
        except OSError:
            # sumiu do portao enquanto se olhava - alguem moveu ou
            # renomeou. Nao entra na fila, e nao e erro: quem so quis
            # conferir nao merece pilha de erro na tela
            continue
        candidatos.append(caminho)

    # a ordem se preserva: quem terminou de chegar volta na ordem em que
    # entrou nesta lista
    prontos = set(arquivos_estaveis(candidatos))
    return [c for c in candidatos if c in prontos]


# ----------------------------------------------------------------------
# O QUE A TELA MOSTRA DE CADA ARQUIVO
# ----------------------------------------------------------------------
# Nenhuma delas e enfeite:
#
#   tamanho    e o que casa com a chapa e com o formato da folha;
#   cor        e ela que escolhe entre a SM 74 e a MOZP acima do F4 -
#              colorido na SM 74, preto-e-branco na MOZP;
#   paginas    para ninguem descobrir depois que era frente e verso - a
#              gravadora nao puxa multiplas paginas;
#   marca      sem marca de corte a montagem nao sabe que lado e o pe, e
#              e do pe que a pinca se mede;
#   sangria    para ninguem montar como se tivesse sangria o que nao tem.
#              Vem dos DOIS caminhos, e quando eles discordam a fila diz
#              o que cada um achou - ver sangria.py.
#
# A CONTA E A DA CASA, e isto e a decisao que sustenta a tela inteira: o
# tamanho e as tintas saem do america.medir, o mesmo que o vigia usa para
# fechar chapa. Uma segunda conta aqui deixaria a tela e o vigia podendo
# discordar sobre o mesmo arquivo - e ai um dos dois manda chapa errada.

def _o_corte(caminho, papel_l, papel_a, lida):
    """
    (largura, altura, de_onde) da PECA - o que o painel pre-preenche.

    O campo do painel e a peca, e a sangria entra num campo separado.
    Preencher a peca com a medida do PAPEL e ainda pôr a sangria medida
    no campo dela conta a sangria DUAS VEZES: a peca sai 6 mm maior do
    que o cliente pediu, e a linha de corte cai dentro do desenho.

    Tres casos, e a diferenca entre eles importa:

      TRIMBOX DECLARADA - ela e a peca. O arquivo disse onde quer ser
      cortado, e nao ha o que calcular;

      SEM TrimBox, MAS COM SANGRIA MEDIDA - a peca e o papel menos a
      sangria dos dois lados. Nao e chute: papel = peca + 2x sangria e a
      definicao de sangria;

      SEM TrimBox E SEM SANGRIA - a peca fica sendo o papel, porque e o
      que ha, e isso vem DITO. Quem monta confere a medida em vez de
      confiar nela.
    """
    corte_l, corte_a, de_onde = sangria.medida_do_corte(caminho)
    # compara CONSTANTE, e nao palavra dentro de frase: a frase e para
    # gente ler, e quem reescrevesse o texto quebraria a decisao calada
    if corte_l is None or de_onde == sangria.DA_TRIMBOX:
        return corte_l, corte_a, de_onde

    mm = lida.get("mm")
    if not lida.get("tem") or not mm:
        return corte_l, corte_a, de_onde
    return (corte_l - 2 * mm, corte_a - 2 * mm,
            "do papel menos a sangria medida (%.1f mm por lado) - o "
            "arquivo nao declara corte" % mm)


def medir_para_a_fila(caminho):
    """
    O que a tela mostra de um arquivo. Nunca estoura: o que nao deu para
    medir volta em 'erro', com o arquivo na lista do mesmo jeito.

    SOME DA FILA E PIOR QUE APARECER SEM MEDIDA. O arquivo esta no
    portao, e trabalho, e alguem tem de saber que ele existe - mesmo que
    o Ghostscript esteja fora do ar ou o PDF esteja quebrado.
    """
    medido = {"arquivo": os.path.basename(caminho), "caminho": caminho,
              "largura": None, "altura": None, "tintas": [], "cores": None,
              "peb": None, "paginas": None, "tem_marca": None,
              "marca_no_pe": None, "corte_largura": None,
              "corte_altura": None, "corte_de": None,
              "sangria": None, "sangria_mm": None,
              "sangria_declarada": None, "sangria_pela_tinta": None,
              "sangria_divergem": False, "sangria_recado": None,
              "precisa_publicar": False,
              "versao": VERSAO_DA_MEDIDA, "erro": None}

    # O .CDR NAO SE MEDE - ele nem se abre fora do CorelDRAW. Ele volta
    # dizendo que falta um passo, e NAO como erro: nao ha nada errado com
    # ele, so ainda nao ha o que medir. Quem aperta 'publicar' e gente -
    # olhar a fila nao pode abrir o CorelDRAW (ver publicar()).
    if os.path.splitext(caminho)[1].lower() == ".cdr":
        medido["precisa_publicar"] = True
        return medido

    try:
        larg, alt, tintas = america.medir(caminho)
        medido["largura"] = larg
        medido["altura"] = alt
        medido["tintas"] = sorted(tintas)
        # e o nome que a casa da a essas tintas - o MESMO que vai no nome
        # da chapa (ver nomes.cores_no_nome): 'CMYK' na ordem da escala, e
        # nao a ordem do alfabeto. A tela nao inventa a sua propria.
        medido["cores"] = nomes.cores_no_nome(tintas) or "K"
        medido["peb"] = america.e_preto_e_branco(tintas)

        import pypdf
        medido["paginas"] = len(pypdf.PdfReader(caminho).pages)

        # os quatro lados, e nao so o pe: a marca do pe e a que manda na
        # pinca, mas arte que chegou em pe tem a marca em outra borda - e
        # 'tem marca' continua sendo sim
        achadas = marcas.marcas_de_corte(caminho)
        medido["marca_no_pe"] = achadas.get("pe")
        medido["tem_marca"] = any(v is not None for v in achadas.values())

        # A SANGRIA VEM DOS DOIS CAMINHOS, e a divergencia sobe dita -
        # arquivo que declara uma coisa e mostra outra e o que engana.
        # Ver o cabecalho do sangria.py.
        lida = sangria.ler_a_sangria(caminho)
        medido["sangria"] = lida["tem"]
        # QUAL DOS DOIS NUMEROS SE MOSTRA E ESCOLHIDO LA, e nao aqui: a
        # medida declarada as vezes e um teto que inclui a area das
        # marcas de corte, e teto nao e medida. Ver o sangria.py.
        medido["sangria_mm"] = lida["mm"]
        medido["sangria_declarada"] = lida["declarada"]
        medido["sangria_pela_tinta"] = lida["pela_tinta"]
        medido["sangria_divergem"] = lida["divergem"]
        medido["sangria_recado"] = lida["recado"]

        # A MEDIDA DO CORTE E OUTRA COISA que a do papel, e e ela que o
        # painel pre-preenche: la a peca e um campo e a sangria e outro.
        # Depende do que a sangria disse, entao vem DEPOIS dela.
        (medido["corte_largura"], medido["corte_altura"],
         medido["corte_de"]) = _o_corte(caminho, larg, alt, lida)
    except Exception as e:
        medido["erro"] = str(e)[:150] or e.__class__.__name__
    return medido


def fila_medida(portao=None):
    """
    A fila com cada arquivo medido - o que a tela da equipe mostra.

    A MEDIDA SE GUARDA PARA NAO SE REFAZER. Medir tinta roda o
    Ghostscript, que custa segundos por arquivo, e a tela e atualizada a
    vontade por gente que esta escolhendo o que montar. Remedir a cada F5
    poria a equipe esperando de novo - que e o que esta fila existe para
    acabar.

    A chave do retrato e a do arquivo - nome|tamanho|data -, entao
    arquivo corrigido que a AMERICA mandou com o mesmo nome e medido de
    novo, e nao mostrado com a medida do que nao esta mais la.

    MEDIDA QUE FALHOU NAO SE GUARDA: Ghostscript fora do ar e coisa de
    momento, e guardar a falha deixaria o arquivo sem medida para sempre.

    O RETRATO FICA NO PC DA FIA, nunca na pasta do cliente - a pasta e
    compartilhada, e a regra da casa nao muda por causa de uma tela.

    A MEDICAO ACONTECE FORA DA TRANCA, e isso e de proposito. Ela custa
    segundos de Ghostscript; com a tranca na mao, a segunda pessoa que
    abrisse a tela ficaria esperando a medicao da primeira - a tela
    travaria justamente quando ha mais trabalho. So o ler e o gravar do
    retrato sao trancados, que e onde a medida se perderia.

    O preco dessa escolha: duas telas abertas no mesmo instante podem
    medir o mesmo arquivo duas vezes. Custa Ghostscript repetido uma vez,
    e nenhuma medida se perde - o contrario do que custava antes.
    """
    esperando = fila(portao)
    if not esperando:
        return []

    with _TRANCA:
        retratos = _ler_dicionario(caminho_das_medidas())

    medidos, novos = [], {}
    for caminho in esperando:
        try:
            chave = chave_arquivo(caminho)
        except OSError:
            continue                  # saiu do portao agora
        guardado = retratos.get(chave)
        if (isinstance(guardado, dict) and not guardado.get("erro")
                and guardado.get("versao") == VERSAO_DA_MEDIDA):
            # o caminho vem do disco de agora, e nao do retrato: a pasta
            # do dia muda de nome todo dia
            guardado = dict(guardado, caminho=caminho,
                            arquivo=os.path.basename(caminho))
            medidos.append(guardado)
            continue
        medido = medir_para_a_fila(caminho)
        medidos.append(medido)
        if not medido["erro"]:
            novos[chave] = medido

    if novos:
        try:
            with _TRANCA:
                # RELE ANTES DE JUNTAR: outra linha pode ter medido outros
                # arquivos enquanto esta media os seus, e o retrato dela
                # nao se joga fora
                retratos = _ler_dicionario(caminho_das_medidas())
                retratos.update(novos)
                _gravar_dicionario(caminho_das_medidas(), retratos)
        except OSError as e:
            # nao poder guardar o retrato so custa medir de novo na
            # proxima olhada - nao e motivo para a fila nao aparecer
            utils.log("MONTAGEM: nao consegui guardar as medidas: %s" % e,
                      alerta=True)
    return medidos


# ----------------------------------------------------------------------
# O .CDR: PUBLICAR PELA COREL
# ----------------------------------------------------------------------
# A AMERICA manda .cdr, e o caminho ja existe. O que ele NAO faz e
# rasterizar: ela manda a MONTAGEM com a imagem ja dentro, e o motor da
# Corel publica em PDF, em vetor. Nas outras (VOPRIX, PRIME) o .cdr e
# arte solta e vira imagem a 1000 dpi; aqui isso so perderia.
#
# PUBLICAR NAO ACONTECE SOZINHO, e essa e a decisao. A fila e uma tela
# que a equipe atualiza a vontade; publicando por conta propria, um F5
# viraria uma sessao do CorelDRAW - e dez F5, dez. O .cdr aparece na fila
# dizendo que falta publicar, e quem aperta e gente. E a mesma escolha do
# montar e do aprovar: o passo caro e o irreversivel acontecem com clique.

def _publicar_pelo_corel(cdr, destino):
    """
    O motor da Corel, isolado numa funcao para os testes o substituirem.

    Importado aqui dentro porque ele fala com o COM do Windows: quem so
    quer olhar a fila nao paga isso.
    """
    from . import corel
    return corel.publicar_pdf(cdr, destino)


# O COREL E UM SO NA MAQUINA, e duas publicacoes ao mesmo tempo disputam
# a MESMA sessao: uma fecha o documento que a outra esta publicando, e
# sobra um PDF pela metade - que ainda por cima tranca as tentativas
# seguintes, porque dali em diante 'ja existe'. A tranca do modulo nao
# serve aqui: ela protege os arquivos de registro e se pega e se solta em
# milissegundos, e isto segura por segundos.
#
# ESPERAR TEM HORA PARA ACABAR. Publicacao que emperra nao pode deixar a
# proxima pessoa pendurada na tela sem explicacao - passado o tempo, ela
# ouve que o Corel esta ocupado e tenta de novo.
_O_COREL = threading.Lock()
ESPERA_PELO_COREL = 300.0          # segundos


def publicar(arquivo, portao=None):
    """
    Publica o .cdr do portao em PDF e tira o .cdr de la.

        {"feito": bool, "pdf": nome | None, "passos": [], "porque": texto}

    O .CDR SAI DO PORTAO E NAO E APAGADO: ele e a FONTE da montagem.
    Deixa-lo la o faria aparecer na fila para sempre, ao lado do PDF que
    saiu dele - e ai a fila mostraria o mesmo servico duas vezes, e
    alguem montaria os dois. Apagar nao esta combinado com ninguem.

    ARQUIVO ABERTO NO COREL DO OPERADOR NAO SE TOCA. Regra nascida de
    erro: o CorelDRAW devolve o documento ja aberto, e fechar aquilo joga
    o trabalho dele fora. Fica para a proxima passada.
    """
    passos = []

    def parar(porque):
        return {"feito": False, "pdf": None, "passos": passos,
                "porque": porque}

    dia, portao_ = pastas_da_montagem()
    portao = portao or portao_
    if not dia:
        return parar("nao achei a pasta do dia da AMERICA")

    # SO SE PUBLICA O QUE ESTA NA FILA: o nome e procurado nela e nunca
    # juntado a um caminho.
    origem = None
    for caminho in fila(portao):
        if os.path.basename(caminho) == arquivo:
            origem = caminho
            break
    if not origem:
        return parar("'%s' nao esta na fila de montagem" % arquivo)
    if os.path.splitext(origem)[1].lower() != ".cdr":
        return parar("'%s' nao e .cdr - so o .cdr precisa ser publicado"
                     % arquivo)

    destino = os.path.splitext(origem)[0] + ".pdf"

    # UMA PUBLICACAO POR VEZ - ver _O_COREL.
    if not _O_COREL.acquire(timeout=ESPERA_PELO_COREL):
        return parar("o CorelDRAW esta ocupado com outra publicacao - ele e "
                     "um so nesta maquina. Tente de novo em instantes.")
    try:
        # A CONFERENCIA E DEPOIS DE ENTRAR, e nao antes: quem esperou na
        # porta pode estar esperando justamente a publicacao DESTE
        # arquivo terminar. Perguntando antes, os dois veriam 'nao
        # existe' e os dois publicariam.
        if os.path.exists(destino):
            # PODE SER OUTRA COISA, ou a mesma arte de uma passada
            # anterior que alguem ja mexeu. Gravar por cima apagaria
            # trabalho.
            return parar("ja existe '%s' no portao - nao gravo por cima. "
                         "Veja qual dos dois vale e tire o outro de la"
                         % os.path.basename(destino))
        _publicar_pelo_corel(origem, destino)
    except Exception as e:
        from . import corel
        if isinstance(e, corel.ArquivoEmUso):
            return parar("'%s' esta aberto no CorelDRAW - nao mexo nele de "
                         "jeito nenhum, senao o trabalho de quem esta com "
                         "ele aberto se perde. Feche e tente de novo."
                         % arquivo)
        return parar("o CorelDRAW nao publicou '%s': %s"
                     % (arquivo, str(e)[:150]))
    finally:
        _O_COREL.release()
    passos.append("publicado em PDF: %s" % os.path.basename(destino))

    # --- O .CDR SAI DO PORTAO, guardado ---
    atencao = None
    try:
        if america.guardar_o_corel(origem, dia):
            passos.append("o .cdr saiu do portao e esta guardado na pasta "
                          "do dia (nao foi apagado)")
        else:
            atencao = "nao consegui tirar '%s' do portao" % arquivo
    except Exception as e:
        atencao = ("nao consegui tirar '%s' do portao (%s)"
                   % (arquivo, str(e)[:80]))

    # FICANDO OS DOIS NO PORTAO, A FILA MOSTRA O MESMO SERVICO DUAS VEZES
    # - e alguem monta os dois: duas chapas e duas OS. O PDF saiu, entao
    # 'publicado' e verdade; o que nao pode e a faxina falhar calada.
    if atencao:
        atencao += (". O PDF foi publicado, entao o portao esta com os DOIS "
                    "agora e a fila vai mostrar o mesmo servico duas vezes. "
                    "Tire o .cdr a mao.")
        passos.append("ATENCAO: %s" % atencao)
        utils.log("MONTAGEM: %s" % atencao, alerta=True)

    utils.log("MONTAGEM: '%s' publicado em PDF pela Corel" % arquivo)
    return {"feito": True, "pdf": os.path.basename(destino),
            "passos": passos, "porque": "", "atencao": atencao}


# ----------------------------------------------------------------------
# O QUE O PAINEL RECEBE
# ----------------------------------------------------------------------
# O painel de imposicao era pagina solta, e por isso carregava uma COPIA
# da tabela de formatos e das chapas escrita em JavaScript. Era o preco
# de nao ter servidor para ler o config - e o comentario no config dizia
# "mudou aqui, muda la", que e o tipo de combinado que ninguem cumpre
# duas vezes.
#
# Servido, ele recebe as de verdade. A copia morreu, e com ela a chance
# de a tela e o vigia discordarem sobre o tamanho de uma chapa.

def chapas_da_casa():
    """
    As chapas da AMERICA como a tela as mostra, DO CONFIG.

    Da menor para a maior, porque a primeira e a que fica escolhida
    quando nao ha arquivo - e a PM 52 e a chapa do dia a dia.

    O PRECO SAI DO MESMO LUGAR QUE A OS COBRA. O painel soma o custo das
    chapas; dois lugares com preco diferente e cliente cobrado errado.

    CHAPA SEM CADASTRO NO GEREMPRE SAI COM PRECO ZERO, E GRITA NO LOG. O
    numero tem de ser algum - o painel soma e nao pode quebrar por causa
    de uma linha que falta no config -, mas zero calado seria chapa
    gravada e nao cobrada, que e o defeito que a VOPRIX ja pagou. Quem
    ler o log do dia ve.
    """
    from .config import CHAPAS_AMERICA, GEREMPRE_CHAPAS

    chapas = []
    for medida in sorted(CHAPAS_AMERICA, key=lambda m: m[0] * m[1]):
        pinca, apelido = CHAPAS_AMERICA[medida]
        cadastro = GEREMPRE_CHAPAS.get((america.CLIENTE, medida))
        if not cadastro:
            utils.log("MONTAGEM: a chapa %dx%d (%s) nao esta no cadastro de "
                      "precos do GEREMPRE - o painel vai somar R$ 0,00 por "
                      "ela. Chapa gravada sem preco nao vira faturamento."
                      % (medida[0], medida[1], apelido), alerta=True)
        chapas.append({
            "id": apelido, "l": medida[0], "a": medida[1], "pinca": pinca,
            "preco": cadastro[2] if cadastro else 0.0,
            # o apelido do config e 'PM_52'; na tela se le 'PM 52'
            "rotulo": apelido.replace("_", " "),
        })
    return chapas


def formatos_da_casa():
    """
    A tabela de formatos DO CONFIG, do jeito que a tela lê.

    As chaves saem como TEXTO porque isto atravessa JSON; em JavaScript
    tabela["4"] e tabela[4] sao a mesma coisa, entao a tela nao muda.

    Cada formato continua sendo uma LISTA de folhas: o F-04 e 33x48 OU
    24x66, e o F-06 tem tres. Achatar isso faria o painel escolher por
    conta propria, que e justamente o que ele deixou de fazer.
    """
    from .config import FORMATOS_DA_CASA

    return {str(numero): [{"total": list(total), "util": list(util)}
                          for total, util in folhas]
            for numero, folhas in FORMATOS_DA_CASA.items()}


def sugestoes_para(medido):
    """
    {"chapa":, "cor":, "tipo":} - o que a regra da casa SUGERE.

    SUGERE, e nao decide. O operador disse "geralmente", e quem manda e a
    mensagem que a AMERICA mandou pelo WhatsApp - trocar e um clique, e a
    troca fica registrada.

    O QUE NAO FOI MEDIDO NAO GANHA SUGESTAO. Arquivo que nao deu para
    medir com uma chapa escolhida seria a tela chutando maquina.
    """
    larg, alt = medido.get("largura"), medido.get("altura")
    tintas = set(medido.get("tintas") or [])

    chapa = None
    if larg and alt:
        # A REGRA E A DO america.py, e nao uma copia dela: e a mesma
        # funcao que o vigia usa para conferir chapa que ja chegou
        # montada. Duas regras de maquina na casa e duas verdades.
        medida = america.maquina_da_america(max(larg, alt), tintas)
        chapa = dict(chapas_de_id())[medida]

    # A COR SO SE SUGERE QUANDO HA FICHA CERTA. O painel tem tres -
    # CMYK (4 chapas), preto e branco (1) e duas cores (2) -, e trabalho
    # de TRES tintas nao tem nenhuma: sugerir CMYK cobraria uma chapa a
    # mais, sugerir 'duas cores' cobraria uma a menos, e a tela ainda
    # estaria mostrando 'colorido (CMK)' ao lado, contradizendo a si
    # mesma. Sem ficha certa, quem escolhe e gente.
    cor = None
    if medido.get("peb"):
        cor = "PB"
    elif medido.get("peb") is False:
        cor = {2: "2", 4: "CMYK"}.get(len(tintas))

    # PAGINA NAO TEM CAMPO NO PAINEL, e o tipo e o unico lugar onde essa
    # medida muda uma decisao: uma pagina nao tem verso, e duas tem frente
    # e verso. Tres ou mais nao se adivinha - e o caso que o ticket 09 vai
    # perguntar em vez de chutar.
    #
    # DUAS PAGINAS SUGEREM BATE-VIRA, E NAO 'FRENTE E VERSO'. As duas
    # poem frente e verso na chapa; a diferenca e que o bate-vira usa UMA
    # chapa, partida ao meio, e e o que a casa faz - e e o que o motor
    # sabe montar. Sugerir 'frente e verso' era oferecer um caminho que
    # falhava no clique do botao.
    tipo = {1: "so-frente", 2: "bate-vira"}.get(medido.get("paginas"))

    return {"chapa": chapa, "cor": cor, "tipo": tipo}


def chapas_de_id():
    """[((l, a), apelido)] - para traduzir medida em id de chapa."""
    from .config import CHAPAS_AMERICA
    return [(medida, CHAPAS_AMERICA[medida][1]) for medida in CHAPAS_AMERICA]


# ----------------------------------------------------------------------
# O BOTAO MONTA DE VERDADE
# ----------------------------------------------------------------------
# A ORDEM E O CONTRATO. Tudo que a tela coleta cabe num objeto, e uma
# funcao recebe esse objeto e faz o trabalho. E o que permite haver um
# seam so: se prova o que a funcao FAZ com a ordem, e nao que uma funcao
# chamou outra.
#
#   ordem = {arquivo, chapa, imagens_frente, imagens_verso,
#            colunas, linhas, vao, sangria, formato, folha, tipo,
#            quem, maquina_trocada, liberado_sem_caber}

def _motor():
    """
    O motor de imposicao da casa - quem assenta a grade na chapa.

    ELE JA EXISTE, e reescreve-lo seria jogar fora conta provada: ele poe
    a peca deitada em cada celula, gira a metade do verso no bate-vira,
    desenha as marcas de corte e de registro com os EPS da propria casa,
    poe a escala de cor, e tem prova propria que confere o PIXEL de cada
    celula (test_imposicao_grade.py).

    ELE MORA EM ferramentas/, E ISSO E DIVIDA CONHECIDA. Src nao devia
    importar de ferramentas - o certo e ele mudar de casa, como o
    sangrar.py mudou. Nao mudou junto com este ticket de proposito: sao
    mil linhas do caminho mais caro da casa, e move-las no mesmo commit
    que liga o botao juntaria dois riscos que nao precisam andar juntos.
    O servidor ja alcanca ferramentas/ para ler o painel.

    IMPORTADO AQUI DENTRO, e nao no topo: ele carrega o pypdf e fala com
    o Ghostscript, e quem so quer olhar a fila nao precisa pagar isso.
    """
    import sys
    if FERRAMENTAS not in sys.path:
        sys.path.insert(0, FERRAMENTAS)
    import montar_bate_vira
    return montar_bate_vira


def _chapa_da_ordem(apelido):
    """
    A chapa com este apelido, do CONFIG, na forma que o motor recebe.

    A MEDIDA SAI DO CONFIG e nao do motor - e a mesma fonte que serve o
    painel. Do motor vem so o TIPO, que e a forma que ele sabe ler; se a
    medida viesse de la, a tela e a montagem poderiam discordar sobre o
    tamanho da chapa, que e o defeito que esta spec veio acabar.
    """
    for c in chapas_da_casa():
        if c["id"] == apelido:
            return _motor().Chapa(float(c["l"]), float(c["a"]),
                                  float(c["pinca"]))
    return None


def executar(ordem):
    """
    Faz a montagem que a tela pediu. Devolve o relato do que aconteceu:

        {"feito": bool, "montagem": caminho | None,
         "passos": [texto], "porque": texto}

    A ORDEM DOS PASSOS E A PROPRIA REGRA, e cada trava aqui veio de erro
    pago:

      1. NUNCA GRAVA NA 'PARA CTP'. A montagem sai na pasta do DIA, e
         quem a move para o portao e gente, DEPOIS de revisar - e essa
         mudanca de pasta que significa 'aprovado'. Escrever no portao
         faria o vigia mandar para o CTP uma montagem que ninguem olhou.
         A trava mora tambem dentro do motor, e e boa que more nos dois;

      2. A PINCA SE CONFERE NO ARQUIVO QUE SAIU, e nao na conta que se
         fez: entre escrever a matriz de deslocamento no PDF e ela valer
         ha um programa inteiro. Nao conferindo - ou nao dando para medir
         -, a montagem e APAGADA e o servico para. 'Nao consegui medir'
         nao e 'esta boa';

      3. O PORTAO NUNCA FICA COM DOIS PDFS DO MESMO SERVICO. Montada a
         peca, o original SAI do portao - guardado na pasta do dia, nunca
         apagado, porque ele e a fonte da montagem. Ficando os dois, a
         volta seguinte do vigia acharia duas chapas: duas gravacoes e
         duas OS.

    E O QUE JA PARAVA CONTINUA PARANDO: arte que so cabe deitada e arte
    que nao cabe em chapa nenhuma. O motor para levantando SystemExit -
    que NAO e Exception e passaria direto por um 'except Exception' -,
    entao ela e pega por nome aqui.
    """
    passos = []

    def parar(porque):
        return {"feito": False, "montagem": None, "passos": passos,
                "porque": porque}

    quem = (ordem.get("quem") or "").strip()
    if not quem:
        return parar("nao monto sem o nome de quem esta montando: e ele que "
                     "responde pela decisao quando sair chapa errada")

    # FRENTE E VERSO DEIXOU DE SER RECUSA - 22/09/2026.
    #
    # Aqui havia uma parada que dizia: "sao duas chapas, uma por lado, e
    # o NOME de cada arquivo de saida e combinado da casa que ninguem me
    # deu". Ela estava certa enquanto durou - inventar convencao de nome
    # de arquivo e exatamente o que nao se faz aqui.
    #
    # O que ela nao sabia e que a saida ja tinha sido achada em 21/09,
    # para o livro: a saida nao era descobrir o nome, era NAO PRECISAR
    # DELE. Um arquivo so, uma chapa por pagina, e o entregar_no_ctp()
    # recorta uma por arquivo na hora de entregar.
    #
    # O operador viu o botao Montar falhar com a montagem inteira pronta
    # na tela e mandou: "vamos arrumar essa informacao para ele salvar a
    # montagem completa".

    # CELULA VAZIA: o motor enche TODAS. O painel avisa que sobra celula
    # e diz que branco na chapa e decisao de quem monta - mas quem faz o
    # branco seria o motor, e ele nao sabe: ele repete a arte em cada
    # celula. Montar assim poria arte onde a tela prometeu branco.
    #
    # E NO BATE-VIRA A CONTA E POR METADE, e nao pela soma. Ele parte a
    # chapa ao meio - esquerda e a frente, direita e o verso -, entao
    # 3 na frente e 1 no verso numa grade de 4 'fecha a conta' somando e
    # mesmo assim deixa a terceira imagem da frente sem onde entrar: a
    # metade dela so tem duas celulas.
    colunas = int(ordem.get("colunas") or 1)
    linhas = int(ordem.get("linhas") or 1)
    celulas = colunas * linhas
    frente = int(ordem.get("imagens_frente") or 0)
    verso = int(ordem.get("imagens_verso") or 0)

    if (ordem.get("tipo") or "") == "bate-vira":
        metade = (colunas // 2) * linhas
        if (frente or verso) and (frente != metade or verso != celulas - metade):
            return parar(
                "no bate-vira cada METADE da chapa tem a sua conta: a "
                "frente cabe em %d celulas e o verso em %d, e foram "
                "pedidas %d e %d. Eu encho todas as celulas, entao a "
                "chapa sairia com arte onde a tela mostrou vazio."
                % (metade, celulas - metade, frente, verso))
    elif frente and frente != celulas:
        return parar(
            "a grade tem %d celulas e foram pedidas %d imagens: eu encho "
            "TODAS as celulas, entao a chapa sairia com arte onde a tela "
            "mostrou vazio. Ajuste a grade, ou peca %d imagens."
            % (celulas, frente, celulas))

    dia, portao = pastas_da_montagem()
    if not dia:
        return parar("nao achei a pasta do dia da AMERICA")

    # SO SE MONTA O QUE ESTA ESPERANDO MONTAGEM. E a mesma porta do
    # painel: o nome e procurado NA FILA e nunca juntado a um caminho.
    origem = None
    for caminho in fila(portao):
        if os.path.basename(caminho) == ordem.get("arquivo"):
            origem = caminho
            break
    if not origem:
        if ordem.get("arquivo") and ja_montado_por_nome(ordem["arquivo"], dia):
            return parar("'%s' ja foi montado - nao refaco. Refazer poria "
                         "duas montagens do mesmo servico na pasta do dia"
                         % ordem["arquivo"])
        return parar("'%s' nao esta na fila de montagem - so se monta o que "
                     "esta no portao %s" % (ordem.get("arquivo"), PORTAO))

    if ja_montado(origem):
        return parar("'%s' ja foi montado - nao refaco"
                     % os.path.basename(origem))

    # A CHAVE SE TIRA AGORA, com o arquivo ainda no portao: la na frente
    # ele ja saiu, e chave_arquivo precisa do arquivo no lugar.
    chave = chave_arquivo(origem)

    # DUAS PESSOAS APERTANDO O BOTAO NO MESMO ARQUIVO. O servidor existe
    # justamente para haver duas, e montar leva SEGUNDOS: as duas passam
    # pelas guardas acima, as duas escrevem o mesmo destino, e a segunda
    # ainda tropeca ao tirar do portao um arquivo que a primeira ja tirou.
    #
    # A marca e de memoria e nao de disco: um servidor so atende a fila, e
    # trava em disco para isso seria mais coisa para dar errado do que o
    # problema que ela resolve.
    with _TRANCA:
        if chave in _MONTANDO:
            return parar("'%s' esta sendo montado agora por outra pessoa - "
                         "espere ela terminar" % os.path.basename(origem))
        _MONTANDO.add(chave)
    try:
        return _montar_de_fato(ordem, origem, chave, dia, passos, parar)
    finally:
        with _TRANCA:
            _MONTANDO.discard(chave)


def _montar_de_fato(ordem, origem, chave, dia, passos, parar):
    """O trabalho, com o arquivo ja reservado. Ver executar()."""
    quem = ordem["quem"].strip()

    chapa = _chapa_da_ordem(ordem.get("chapa"))
    if chapa is None:
        return parar("nao conheco a chapa '%s' da AMERICA"
                     % ordem.get("chapa"))

    motor = _motor()
    destino = os.path.join(dia, motor.nome_da_montagem(origem))

    # JA HA UMA MONTAGEM COM ESTE NOME? Ela nao se joga fora. Acontece
    # quando a AMERICA manda o arquivo corrigido com o mesmo nome: a
    # chave muda e a montagem e refeita, mas a antiga pode ter sido
    # aprovada e movida - e pode estar no meio de uma revisao. E a mesma
    # decisao do guardar_copia: a anterior sai de lado com a data.
    if os.path.exists(destino):
        base, ext = os.path.splitext(destino)
        selo = datetime.now().strftime("%Y%m%d_%H%M%S")
        de_lado = "%s (anterior %s)%s" % (base, selo, ext)
        try:
            shutil.move(destino, de_lado)
            passos.append("ja havia uma montagem com este nome - a antiga "
                          "foi posta de lado: %s" % os.path.basename(de_lado))
        except OSError as e:
            return parar("ja existe '%s' na pasta do dia e nao consegui "
                         "por de lado (%s) - nao gravo por cima de montagem "
                         "de ninguem" % (os.path.basename(destino),
                                         str(e)[:60]))

    passos.append("montando '%s' na %s, grade %sx%s"
                  % (os.path.basename(origem), ordem.get("chapa"),
                     ordem.get("colunas"), ordem.get("linhas")))

    # --- 1. a montagem, na PASTA DO DIA ---
    #
    # CADA MONTAGEM NA SUA PASTA TEMPORARIA. O motor escreve la com nomes
    # FIXOS - _p0.pdf, _m.pdf, _r.pdf -, e ele nasceu para rodar um de
    # cada vez, na linha de comando. Agora quem o chama e um servidor com
    # LINHAS: duas pessoas montando arquivos DIFERENTES ao mesmo tempo -
    # que e para isso que o servidor existe - escreveriam nos mesmos
    # arquivos, e o pypdf le essas paginas na hora de gravar. Uma chapa
    # sairia com a arte da outra, ou com a grade de corte da outra, e
    # ninguem veria antes da maquina.
    #
    # A reserva por arquivo nao alcanca isto: ela guarda o MESMO arquivo
    # de ser montado duas vezes, e aqui os arquivos sao outros.
    tmp = tempfile.mkdtemp(prefix="montagem_")
    try:
        # LIVRO OU FOLHA SOLTA, e quem diz e o PROCESSO da ordem.
        #
        # Canoa e lombada tem caderno, e caderno tem mais de uma chapa:
        # a saida e um PDF de VARIAS paginas, uma chapa por pagina, e
        # quem separa uma por arquivo e a entrega no CTP. Folha solta
        # continua como sempre foi - uma chapa, uma pagina.
        #
        # Regra do operador, 21/09/2026: "preciso que na montagem
        # consiga montar multiplas paginas, para ir caderno frente e
        # verso, ai quando colocar PARA CTP, la sim, voce separa as
        # paginas por chapa".
        processo = e_livro(ordem)
        if processo:
            # OS CADERNOS VEM DA TELA, prontos. O painel deixa o
            # montador somar caderno por caderno, cada um com a SUA
            # vira e as suas paginas - e a casa mistura mesmo. Recalcular
            # aqui um tamanho unico jogaria a escolha dele fora.
            livro = ordem.get("livro") or {}
            # A CHAPA DE CADA CADERNO, traduzida aqui.
            #
            # A tela manda o APELIDO ('MOZP_FT2'), e a medida sai do
            # config - a mesma fonte que serve o painel. Vindo a medida
            # da tela, ela e a montagem poderiam discordar sobre o
            # tamanho da chapa, que e o defeito que _chapa_da_ordem veio
            # acabar.
            #
            # O ultimo caderno quase nunca tem o tamanho dos outros - o
            # Sapientia fechou 14 de 16 e um de 4 -, e caderno pequeno
            # nao precisa da chapa grande. Regra do operador,
            # 22/09/2026.
            for c in (livro.get("cadernos") or []):
                if c.get("chapa"):
                    c["chapa"] = _chapa_da_ordem(c["chapa"])
            relato = motor.montar_livro(
                origem, destino, chapa=chapa, tmp=tmp,
                cadernos=livro.get("cadernos") or None,
                paginas=int(livro.get("paginas")
                            or ordem.get("paginas_do_livro") or 0),
                por_caderno=int(ordem.get("paginas_por_caderno") or 0),
                processo=processo,
                vira=ordem.get("vira") or paginacao.FRENTE_E_VERSO,
                vao=float(ordem.get("vao") or 0),
                sangria=ordem.get("sangria"),
                formato=ordem.get("formato"), folha=ordem.get("folha") or 0,
                assim_mesmo=bool(ordem.get("liberado_sem_caber")),
                extra=ordem.get("etiqueta") or "",
                marca_de_corte=ordem.get("marca_de_corte", True),
                marca_de_registro=ordem.get("marca_de_registro", True),
                escala_de_cor=ordem.get("escala_de_cor", True),
                # CONVERTER EM IMAGEM E ESCOLHA POR MONTAGEM, e o
                # padrao do livro e NAO converter - regra do operador,
                # 21/09/2026: "no caso do livro as paginas nao serao
                # convertidas em imagem, pq geralmente sao mais textos e
                # fotos que nao dao problema". Quando ele quiser
                # converter, a tela manda dizendo.
                em_imagem=bool(livro.get("em_imagem")))
            relato.setdefault("montagem", destino)
            return _relato_do_livro(relato, destino, ordem)

        # FOLHA SOLTA EM FRENTE E VERSO: duas chapas, num PDF so - o
        # mesmo desenho do livro, sem dobra nenhuma. Ver
        # motor.montar_frente_e_verso.
        if (ordem.get("tipo") or "") == "frente-verso":
            relato = motor.montar_frente_e_verso(
                origem, destino, chapa=chapa, tmp=tmp,
                cols=int(ordem.get("colunas") or 1),
                rows=int(ordem.get("linhas") or 1),
                vao=float(ordem.get("vao") or 0),
                sangria=ordem.get("sangria"),
                formato=ordem.get("formato"), folha=ordem.get("folha") or 0,
                assim_mesmo=bool(ordem.get("liberado_sem_caber")),
                encontro=ordem.get("encontro") or "cabeca",
                giro=int(ordem.get("giro", -90)),
                marca_de_corte=ordem.get("marca_de_corte", True),
                marca_de_registro=ordem.get("marca_de_registro", True),
                escala_de_cor=ordem.get("escala_de_cor", True))
            relato.setdefault("montagem", destino)
            return _relato_do_livro(relato, destino, ordem)

        relato = motor.montar(
            origem, destino, chapa=chapa, tmp=tmp,
            cols=int(ordem.get("colunas") or 1),
            rows=int(ordem.get("linhas") or 1),
            vao=float(ordem.get("vao") or 0),
            sangria=ordem.get("sangria"),
            tipo=ordem.get("tipo") or "bate-vira",
            formato=ordem.get("formato"), folha=ordem.get("folha") or 0,
            assim_mesmo=bool(ordem.get("liberado_sem_caber")),
            # O ENCONTRO E O GIRO DE CADA PECA, e quem aprova a montagem
            # aprova o DESENHO que a tela mostrou. Sem isto a chapa saia
            # sempre cabeca-com-cabeca, mesmo com pe-com-pe escolhido.
            encontro=ordem.get("encontro") or "cabeca",
            # O GIRO DA PECA NA CELULA - e o que diz se ela entra EM PE
            # ou DEITADA. Sem ele aqui, a tela mostraria a peca em pe e o
            # motor a deitaria assim mesmo: a chapa sairia diferente do
            # desenho que a pessoa acabou de aprovar. -90 e o que a casa
            # ja fazia, entao ordem antiga sem o campo nao muda de nada.
            giro=int(ordem.get("giro", -90)),
            marca_de_corte=ordem.get("marca_de_corte", True),
            marca_de_registro=ordem.get("marca_de_registro", True),
            escala_de_cor=ordem.get("escala_de_cor", True))
    except SystemExit as e:
        # o motor para assim: arte que nao cabe, grade impossivel, bate-
        # vira com colunas impares. Nao e falha nossa - e ele fazendo o
        # que tem de fazer, e o recado dele e para gente ler.
        return parar(str(e))
    except Exception as e:
        return parar("nao consegui montar: %s" % str(e)[:200])
    finally:
        # O motor ja gravou o destino aqui - o pypdf materializa tudo no
        # write -, entao o temporario nao faz falta a ninguem. Deixa-lo
        # encheria o disco de quem monta dezenas por dia.
        shutil.rmtree(tmp, ignore_errors=True)

    passos.append("montagem gravada: %s" % os.path.basename(destino))

    # --- 2. A PINCA, NO ARQUIVO QUE SAIU ---
    _, pe_arte, _ = america.medir_o_pe(destino)
    if pe_arte is None or not america.esta_pincada(pe_arte, chapa.pinca):
        try:
            os.remove(destino)
        except OSError:
            pass
        return parar(
            "PARO: montei e conferi, e %s. A montagem foi apagada e o "
            "arquivo continua no portao - remonte."
            % ("nao consegui medir a pinca no arquivo que saiu"
               if pe_arte is None else
               "o desenho ficou a %.0f mm do pe em vez dos %.0f da pinca"
               % (pe_arte, chapa.pinca)))
    passos.append("pinca conferida no arquivo que saiu: o desenho comeca a "
                  "%.1f mm do pe (pinca %.0f)" % (pe_arte, chapa.pinca))

    # --- 2b. FOI LIBERADA SEM CABER? ---
    #
    # O QUE MARCA NAO E O PEDIDO, E O QUE ACONTECEU. A tela manda
    # 'liberado_sem_caber' junto com a ordem, mas quem sabe se a montagem
    # estourou de verdade e o motor, que mediu. Marcando pelo pedido, uma
    # montagem que cabia sairia no historico como liberada - e o
    # historico existe justamente para separar os casos que ensinam dos
    # que nao ensinam nada.
    estourou = bool((relato or {}).get("estourou"))
    motivos = list((relato or {}).get("estouros") or []) if estourou else []
    if estourou:
        # DECISAO FECHADA DA EQUIPE, e do operador contra a recomendacao
        # de escalar: nao vira pendencia e nao grita. A linha do dia
        # conta o que houve, e o historico guarda o nome - ele escolhe
        # quando olhar, em vez de ser interrompido.
        passos.append("LIBERADA SEM CABER por %s: %s"
                      % (quem, "; e ".join(motivos)))
        utils.log("MONTAGEM: %s liberou sem caber '%s' - %s"
                  % (quem, os.path.basename(origem), "; e ".join(motivos)))

    # --- 3. O ORIGINAL SAI DO PORTAO, guardado ---
    #
    # E SO DEPOIS DE A MONTAGEM ESTAR CONFERIDA. Tirando antes, uma
    # montagem que nao conferisse deixaria o servico sem arquivo no
    # portao e sem montagem - o trabalho sumiria no meio.
    atencao = None
    try:
        guardada, o_que_fiz = america.guardar_copia(origem, dia)
        ok, porque = america.chegou_inteira(origem, guardada)
        if not ok:
            atencao = ("a montagem esta feita e conferida, mas NAO consegui "
                       "tirar '%s' do portao (%s). TIRE A MAO: ele nao vai "
                       "mais aparecer na fila - ja esta anotado como montado "
                       "- e ficar la nao adianta nada"
                       % (os.path.basename(origem), porque))
        else:
            os.remove(origem)
            passos.append("o original saiu do portao e esta guardado na "
                          "pasta do dia (nao foi apagado)")
    except Exception as e:
        atencao = ("a montagem esta feita e conferida, mas NAO consegui "
                   "tirar '%s' do portao (%s). Tire a mao."
                   % (os.path.basename(origem), str(e)[:80]))
    if atencao:
        # ALTO, e nao so uma linha nos passos: o arquivo some da fila
        # (ja esta anotado) e fica no portao sem ninguem olhando. O
        # trabalho FOI feito - anotar e o certo, e a licao das tres
        # folhas de papel -, mas a faxina que falhou precisa de gente.
        passos.append("ATENCAO: %s" % atencao)
        utils.log("MONTAGEM: %s" % atencao, alerta=True)

    # --- 4. QUEM MONTOU, ANTES DE MAIS NADA DAR ERRADO ---
    #
    # A licao das tres folhas de papel: o trabalho esta FEITO aqui, e o
    # que vem depois e faxina. Quem faz deixa dito que fez, na hora.
    anotado = anotar_montagem(origem, {
        "quem": quem, "chapa": ordem.get("chapa"),
        "montagem": os.path.basename(destino),
        "grade": "%sx%s" % (ordem.get("colunas"), ordem.get("linhas")),
        "tipo": ordem.get("tipo"), "vao": ordem.get("vao"),
        "sangria": ordem.get("sangria"), "formato": ordem.get("formato"),
        "imagens_frente": ordem.get("imagens_frente"),
        "imagens_verso": ordem.get("imagens_verso"),
        "maquina_trocada": ordem.get("maquina_trocada"),
        # quem liberou e POR QUE nao cabia - os dois, ou nenhum
        "liberado_sem_caber": estourou,
        "liberado_por": quem if estourou else None,
        "liberado_porque": motivos,
        "pe_conferido": round(pe_arte, 2),
    }, chave=chave)

    # O REGISTRO PODE NAO TER GRAVADO - disco cheio, pasta sem permissao.
    # A montagem esta no disco e o original ja saiu do portao: sem o
    # registro ela fica SEM DONO e SEM DATA, e ninguem sabe que ela foi
    # feita. Dizer 'feito' calado esconderia justamente isso.
    if anotado is None:
        atencao = ("a montagem esta feita e conferida, mas NAO consegui "
                   "gravar o registro: ela fica sem dono e sem data, e nao "
                   "vai aparecer no historico. Veja o log e anote a mao "
                   "quem montou '%s'." % os.path.basename(destino))
        passos.append("ATENCAO: %s" % atencao)
        utils.log("MONTAGEM: %s" % atencao, alerta=True)
    else:
        passos.append("anotado: montado por %s" % quem)

    utils.log("MONTAGEM: %s montou '%s' na %s (%sx%s) - %s"
              % (quem, os.path.basename(origem), ordem.get("chapa"),
                 ordem.get("colunas"), ordem.get("linhas"),
                 os.path.basename(destino)))

    return {"feito": True, "montagem": destino, "passos": passos,
            "porque": "", "atencao": atencao, "relato": relato}


def e_livro(ordem):
    """
    O processo, se esta ordem for de LIVRO; '' se for folha solta.

    Quem decide e o PROCESSO, e nao o tipo de vira: canoa e lombada tem
    caderno, e caderno tem mais de uma chapa - a saida e um PDF de
    varias paginas. Folha solta continua uma chapa, uma pagina.

    Esta separada de proposito. Ela vive dentro do executar(), que antes
    dela confere arquivo, reserva e portao - e um teste que quisesse
    provar so a escolha teria de montar a pasta do dia inteira para
    chegar ate aqui.

    O NOME PASSA PELA TRADUCAO, e nao se compara cru. A tela diz
    'hotmelt'; o paginacao diz 'lombada'. Comparando direto, hotmelt nao
    era nem canoa nem lombada e a ordem inteira caia no caminho da folha
    solta - que respondia falando de BATE-VIRA, coisa que o operador nem
    tinha escolhido. Ver paginacao.processo_que_e.
    """
    processo = paginacao.processo_que_e(ordem.get("processo"))
    return processo if processo in (paginacao.CANOA, paginacao.LOMBADA) else ""


def _relato_do_livro(relato, destino, ordem):
    """
    O que a tela recebe quando o que saiu foi um LIVRO.

    Mesma forma do relato de uma chapa - 'feito', 'passos', 'porque' -,
    porque quem desenha a tela nao tem de saber a diferenca. O que muda
    e o que os passos CONTAM: um livro sai com varias chapas, e quem vai
    grava-las precisa ler a lista antes de aprovar.

    A ORDEM DAS PAGINAS E A FILA DA GRAVACAO, e por isso ela aparece
    escrita: a pasta do CTP e lida em ordem alfabetica e o numero vai na
    frente do nome, entao caderno 1 frente, caderno 1 verso, caderno 2
    frente... e a sequencia em que as chapas saem. Trocar duas e um
    livro com o miolo fora de ordem, e isso so aparece depois de dobrado.
    """
    chapas = relato.get("chapas") or []
    passos = [
        "%s - %d caderno(s) de %s pagina(s), %s"
        % (relato.get("processo", "livro"), relato.get("cadernos", 0),
           relato.get("por_caderno", "?"), relato.get("vira", "?")),
        "saiu UM PDF com %d pagina(s): uma chapa por pagina"
        % relato.get("paginas_no_pdf", len(chapas)),
    ]
    for c in chapas:
        paginas = [n for n in (c.get("paginas_do_livro") or []) if n]
        passos.append("   %-24s paginas %s"
                      % (c.get("etiqueta", "?"),
                         ", ".join(str(n) for n in paginas)))

    # O QUE AINDA PEDE OLHO, e nao e pouco: a fuga da canoa (o creep)
    # nao e compensada por ninguem aqui - ver a skill de imposicao. Com
    # mais de um caderno, a margem interna das paginas do miolo some se
    # ninguem olhar.
    atencao = None
    if relato.get("processo") == paginacao.CANOA and \
            (relato.get("cadernos") or 0) > 1:
        atencao = ("canoa de %d cadernos: a FUGA (creep) nao e compensada "
                   "aqui. Confira a margem interna das paginas do miolo "
                   "antes de aprovar." % relato["cadernos"])

    return {"feito": True, "montagem": destino, "passos": passos,
            "porque": "", "atencao": atencao, "relato": relato}


# ----------------------------------------------------------------------
# A REVISAO - aprovar e mandar para a PARA CTP
# ----------------------------------------------------------------------
# A MUDANCA DE PASTA E A APROVACAO, e por isso ela nao acontece sozinha.
# O sistema move porque uma pessoa clicou, e e justamente esse clique que
# permite saber quem aprovou - quando sair chapa errada, saber quem viu e
# como a regra nasce.
#
# O QUE MUDA NAO E A REVISAO EXISTIR, e QUEM pode faze-la: era o operador
# arrastando o arquivo, passa a ser qualquer um da equipe.
#
# DALI EM DIANTE E O FLUXO QUE JA EXISTE. O vigia acha a montagem na
# 'PARA CTP', abre a OS, imprime a prova, grava a chapa no CTP e apaga do
# portao - e nao precisa saber que ela veio daqui.

SUFIXO_MONTAGEM = "_MONTAGEM"


def _montagens_da_pasta(dia):
    """Os nomes dos arquivos *_MONTAGEM da pasta do dia, em ordem."""
    try:
        nomes = sorted(os.listdir(dia))
    except OSError:
        return []
    achadas = []
    for nome in nomes:
        base, ext = os.path.splitext(nome)
        if not base.upper().endswith(SUFIXO_MONTAGEM):
            continue
        if not ext.lower().endswith((".pdf", ".cdr")):
            continue
        if os.path.isfile(os.path.join(dia, nome)):
            achadas.append(nome)
    return achadas


def _entrada_da_montagem(nome, registro=None):
    """
    (chave, entrada) do registro para esta montagem, ou (None, {}).

    VALE A MAIS NOVA quando ha mais de uma. Acontece quando a AMERICA
    manda o arquivo corrigido com o mesmo nome: a montagem e refeita e
    nascem duas entradas com o mesmo 'montagem'. A que esta na pasta - e
    a que vai para a gravadora - e a ultima; marcando a velha, a montagem
    que virou chapa ficaria gravada como nunca aprovada.

    ESTA FUNCAO EXISTE PARA A LISTA E A APROVACAO NAO DISCORDAREM: uma
    pegava a ultima e a outra a primeira, e a conta so nao batia
    justamente no caso em que ha duas.
    """
    registro = carregar_montagens() if registro is None else registro
    achado = (None, {})
    for chave, entrada in registro.items():
        if entrada.get("montagem") == nome:
            achado = (chave, entrada)
    return achado


def _chegou_inteira(origem, destino):
    """
    (ok, porque) - a copia no portao de saida e a mesma que saiu daqui?

    PDF SE CONFERE ABRINDO, que e a prova mais forte que ha, e e a
    conferencia da casa. O .CDR NAO ABRE COMO PDF - e o que o CorelDRAW
    salva -, e para ele o tamanho e tudo o que da para conferir. Usando a
    conferencia de PDF nele, a montagem em .cdr seria recusada SEMPRE e
    ficaria presa na lista de revisao para sempre.
    """
    if os.path.splitext(destino)[1].lower() == ".pdf":
        return america.chegou_inteira(origem, destino)
    if not os.path.exists(destino):
        return False, "nao esta no portao"
    if os.path.getsize(destino) != os.path.getsize(origem):
        return False, "tamanho diferente do original"
    return True, ""


def esperando_revisao(dia=None):
    """
    As montagens da pasta do dia que ainda nao foram aprovadas.

    OLHA A PASTA, e nao so o registro. O operador monta no CorelDRAW e
    salva o _MONTAGEM na pasta do dia - e assim que a casa sempre fez, e
    continua valendo. Listando so o que a FIA fez, a tela mentiria sobre
    o que falta revisar. O que o registro sabe entra junto, quando
    souber: quem montou, em que chapa, se foi liberada sem caber.

    SAI DA LISTA O QUE JA FOI APROVADO - pelo registro, ou por ja estar
    na 'PARA CTP'. A segunda pergunta importa porque o operador pode ter
    arrastado a mao, como sempre fez, e pedir que ele aprove de novo
    seria a tela nao enxergar o que ele acabou de fazer.
    """
    if dia is None:
        dia, _ = pastas_da_montagem()
    if not dia:
        return []

    from .config import SUBPASTA_PARA_CTP
    ja_no_portao = set()
    try:
        ja_no_portao = set(os.listdir(os.path.join(dia, SUBPASTA_PARA_CTP)))
    except OSError:
        pass

    # os dois registros se leem UMA vez para a lista inteira
    registro = carregar_montagens()
    # E O DO FECHAMENTO TAMBEM. O vigia APAGA da 'PARA CTP' depois de
    # gravar a chapa - a copia da casa fica na pasta do dia -, entao
    # olhar so 'esta na PARA CTP?' faria a montagem REAPARECER na lista
    # assim que ele apagasse. Uma segunda aprovacao seria uma SEGUNDA
    # CHAPA e uma SEGUNDA OS, que e o prejuizo que o portao inteiro
    # existe para nao ter.
    ja_virou_chapa = utils.carregar_registro()

    esperando = []
    for nome in _montagens_da_pasta(dia):
        _, anotada = _entrada_da_montagem(nome, registro)
        # DISPENSADA E DIFERENTE DE APROVADA, e os dois campos existem
        # separados de proposito. Aprovar poe a montagem na 'PARA CTP' e
        # ela vira chapa; dispensar so a tira da tela - o arquivo fica na
        # pasta do dia, intocado, e nenhuma chapa e gravada.
        #
        # Gravar 'aprovado_por' para limpar a lista seria registrar uma
        # aprovacao que ninguem deu, e esse registro e justamente quem
        # responde por cada chapa que saiu.
        if (anotada.get("aprovado_por") or anotada.get("dispensada_por")
                or nome in ja_no_portao):
            continue
        try:
            if chave_arquivo(os.path.join(dia, nome)) in ja_virou_chapa:
                continue
        except OSError:
            continue        # sumiu da pasta enquanto se olhava
        esperando.append({
            "arquivo": nome,
            "caminho": os.path.join(dia, nome),
            "quem_montou": anotada.get("quem"),
            "quando": anotada.get("quando"),
            "chapa": anotada.get("chapa"),
            "grade": anotada.get("grade"),
            "tipo": anotada.get("tipo"),
            "de": anotada.get("arquivo"),
            "maquina_trocada": anotada.get("maquina_trocada"),
            "liberado_sem_caber": anotada.get("liberado_sem_caber") or False,
            "liberado_por": anotada.get("liberado_por"),
            "liberado_porque": anotada.get("liberado_porque") or [],
        })
    return esperando


def dispensar(arquivo, quem, porque=None, dia=None):
    """
    Tira uma montagem da lista de revisao SEM aprovar nada.

        {"feito": bool, "porque": texto}

    Aprovar copia para a 'PARA CTP' e a montagem vira chapa. Dispensar
    nao mexe em arquivo nenhum: o _MONTAGEM continua na pasta do dia,
    como estava, e so some da tela.

    Existe porque a lista acumula - montagem refeita, arte que o cliente
    trocou, teste que ficou - e sem isto a unica forma de limpar seria
    marcar 'aprovado_por' num trabalho que ninguem aprovou. Esse campo e
    quem responde por cada chapa que saiu; enche-lo de mentira custaria
    a proxima vez que alguem perguntasse quem mandou gravar.

    Fica gravado QUEM dispensou e QUANDO, pelo mesmo motivo.
    """
    if dia is None:
        dia, _ = pastas_da_montagem()
    if not dia:
        return {"feito": False, "porque": "nao achei a pasta do dia"}

    caminho = os.path.join(dia, arquivo)
    if not os.path.exists(caminho):
        return {"feito": False,
                "porque": "'%s' nao esta na pasta do dia" % arquivo}

    chave, _ = _entrada_da_montagem(arquivo)
    quando = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        if chave:
            with _TRANCA:
                tudo = carregar_montagens()
                tudo[chave] = dict(tudo.get(chave) or {},
                                   dispensada_por=quem, dispensada_em=quando,
                                   dispensada_porque=porque)
                _gravar_dicionario(caminho_do_registro(), tudo)
        else:
            anotar_montagem(caminho,
                            {"montagem": arquivo, "quem": None,
                             "dispensada_por": quem, "dispensada_em": quando,
                             "dispensada_porque": porque,
                             "montada_fora_da_tela": True})
    except OSError as e:
        return {"feito": False, "porque": "nao consegui gravar: %s" % e}
    return {"feito": True,
            "porque": "'%s' saiu da lista - o arquivo continua na pasta"
                      % arquivo}


def limpar_revisao(quem, porque=None, dia=None):
    """
    Dispensa TUDO que esta esperando revisao. Devolve quantos sairam.

        {"feito": bool, "quantos": int, "porque": texto}

    Pedido do operador em 18/09/2026: um botao de "limpar lista que
    limpa somente na pagina, nao deleta nada". E isso: nenhum arquivo e
    tocado, nada vai para a 'PARA CTP', nenhuma chapa e gravada. So a
    tela fica limpa - e quem limpou fica registrado.
    """
    itens = esperando_revisao(dia)
    if not itens:
        return {"feito": True, "quantos": 0,
                "porque": "a lista ja estava vazia"}
    fora, sobraram = 0, []
    for i in itens:
        r = dispensar(i["arquivo"], quem, porque=porque, dia=dia)
        if r["feito"]:
            fora += 1
        else:
            sobraram.append("%s (%s)" % (i["arquivo"], r["porque"]))
    return {"feito": not sobraram, "quantos": fora,
            "porque": ("%d sairam da lista; os arquivos continuam na pasta"
                       % fora) if not sobraram
                      else "sairam %d, mas nao consegui: %s"
                           % (fora, "; ".join(sobraram))}


def refazer(arquivo, quem, dia=None):
    """
    Tira uma montagem errada da lista e devolve por onde recomeca-la.

        {"feito": bool, "porque": texto, "ir_para": rota ou None}

    Pedido do operador em 18/09/2026, depois do CHECK-LIST: *"ela era
    colorida, e eu disse que era 1 cor"*. A montagem saiu com a cor
    errada e nao ha o que revisar nela - o que falta e monta-la de novo.

    NAO APAGA A MONTAGEM ERRADA. Ela continua na pasta do dia: e o que
    se olha quando alguem pergunta o que foi feito, e a nova sai com o
    mesmo nome por cima quando for gerada. Aqui so se tira da lista.

    O 'ir_para' aponta o painel do arquivo de ORIGEM. Ele so existe se a
    origem ainda estiver na fila - o painel nao monta o que nao esta
    esperando montagem, e essa trava fica de pe. Nao estando, isto
    avisa em vez de inventar um caminho.
    """
    alvo = None
    for i in esperando_revisao(dia):
        if i["arquivo"] == arquivo:
            alvo = i
            break
    if alvo is None:
        return {"feito": False, "ir_para": None,
                "porque": "'%s' nao esta esperando revisao" % arquivo}

    r = dispensar(arquivo, quem, porque="refazer: montagem a corrigir",
                  dia=dia)
    if not r["feito"]:
        return {"feito": False, "ir_para": None, "porque": r["porque"]}

    de = alvo.get("de")
    if de and any(i["arquivo"] == de for i in fila_medida()):
        return {"feito": True, "ir_para": "/painel?arquivo=" + quote(de),
                "porque": "saiu da lista - monte '%s' de novo" % de}

    # SEM ORIGEM NA FILA nao ha painel para abrir, e isso e comum: a
    # montagem pode ter sido feita a mao no Corel, ou o original ja ter
    # saido do portao. Dizer a verdade vale mais do que um botao que
    # leva a lugar nenhum.
    return {"feito": True, "ir_para": None,
            "porque": ("saiu da lista. O arquivo de origem%s nao esta "
                       "esperando montagem - ponha-o na 'PARA MONTAR' "
                       "para montar de novo")
                      % ((" ('%s')" % de) if de else "")}


def aprovar(arquivo, quem, dia=None):
    """
    Poe a montagem na 'PARA CTP' e grava quem aprovou.

        {"feito": bool, "porque": texto, "passos": [texto]}

    COPIA, E NAO MOVE, e isso nao e detalhe: o vigia APAGA da 'PARA CTP'
    depois de gravar a chapa, e ele so pode fazer isso porque a copia da
    casa fica na pasta do dia. Movendo, a montagem sumiria justamente
    depois de virar chapa - e ela e o que se olha quando alguem pergunta
    o que foi para a gravadora.

    O NOME E OBRIGATORIO. Sem ele, aprovar seria mover sem responsavel, e
    era exatamente isso que a mudanca de pasta a mao ja fazia. O clique
    so vale mais que o arrastar porque fica dito quem clicou.
    """
    passos = []

    def parar(porque):
        return {"feito": False, "passos": passos, "porque": porque}

    quem = (quem or "").strip()
    if not quem:
        return parar("nao aprovo sem o nome de quem esta aprovando: quando "
                     "sair chapa errada, saber quem viu e como a regra nasce")

    if dia is None:
        dia, _ = pastas_da_montagem()
    if not dia:
        return parar("nao achei a pasta do dia da AMERICA")

    # SO SE APROVA O QUE ESTA ESPERANDO REVISAO. E a mesma porta do
    # montar: o nome e procurado NA LISTA e nunca juntado a um caminho.
    escolhida = None
    for item in esperando_revisao(dia):
        if item["arquivo"] == arquivo:
            escolhida = item
            break
    if not escolhida:
        return parar("'%s' nao esta esperando revisao - so se aprova o que "
                     "esta na lista" % arquivo)

    from .config import SUBPASTA_PARA_CTP
    portao_saida = os.path.join(dia, SUBPASTA_PARA_CTP)
    destino = os.path.join(portao_saida, arquivo)
    try:
        os.makedirs(portao_saida, exist_ok=True)
        shutil.copy2(escolhida["caminho"], destino)
    except OSError as e:
        return parar("nao consegui por na %s: %s"
                     % (SUBPASTA_PARA_CTP, str(e)[:120]))

    # CHEGOU INTEIRA? Meia montagem no portao seria gravada como chapa
    # pelo vigia. PDF se confere abrindo; .cdr, pelo tamanho.
    ok, porque = _chegou_inteira(escolhida["caminho"], destino)
    if not ok:
        try:
            os.remove(destino)
        except OSError:
            pass
        return parar("a copia nao chegou inteira na %s (%s) - tirei de la, "
                     "porque o vigia gravaria isso como chapa"
                     % (SUBPASTA_PARA_CTP, porque))

    passos.append("%s foi para a %s" % (arquivo, SUBPASTA_PARA_CTP))

    # --- QUEM APROVOU ---
    #
    # A entrada e a da montagem, quando ela existe. Montagem feita a mao
    # no Corel nao tem entrada nenhuma - e ai nasce uma, porque o nome de
    # quem aprovou vale do mesmo jeito.
    chave, _ = _entrada_da_montagem(arquivo)
    quando = datetime.now().strftime("%d/%m/%Y %H:%M")
    anotado = None
    if chave:
        try:
            with _TRANCA:
                tudo = carregar_montagens()
                tudo[chave] = dict(tudo.get(chave) or {},
                                   aprovado_por=quem, aprovado_em=quando)
                _gravar_dicionario(caminho_do_registro(), tudo)
            anotado = True
        except OSError:
            anotado = None
    else:
        anotado = anotar_montagem(escolhida["caminho"],
                                  {"montagem": arquivo, "quem": None,
                                   "aprovado_por": quem, "aprovado_em": quando,
                                   "montada_fora_da_tela": True})

    # A GRAVACAO PODE TER FALHADO, e dizer 'aprovada' calado esconderia
    # justamente o que o clique veio resolver: o arquivo JA ESTA na
    # 'PARA CTP' e vai virar chapa, e sem o registro ele vira chapa sem
    # ninguem respondendo por ela. E a mesma decisao do montar.
    atencao = None
    if not anotado:
        atencao = ("'%s' esta na %s e vai virar chapa, mas NAO consegui "
                   "gravar quem aprovou. Anote a mao que foi %s - senao ela "
                   "vira chapa sem ninguem respondendo por ela."
                   % (arquivo, SUBPASTA_PARA_CTP, quem))
        passos.append("ATENCAO: %s" % atencao)
        utils.log("MONTAGEM: %s" % atencao, alerta=True)
    else:
        passos.append("aprovada por %s" % quem)

    utils.log("MONTAGEM: %s aprovou '%s' e mandou para a %s"
              % (quem, arquivo, SUBPASTA_PARA_CTP))
    return {"feito": True, "passos": passos, "porque": "",
            "atencao": atencao}


# ----------------------------------------------------------------------
# O HISTORICO - onde o operador ESCOLHE olhar
# ----------------------------------------------------------------------
# Ele tirou o caso dificil do caminho dele: liberar montagem que nao cabe
# e decisao fechada da equipe e nao sobe para ele. Em troca, precisa de um
# lugar onde ESCOLHE olhar, em vez de ser interrompido.
#
# E NAO E BUROCRACIA. Maquina trocada fora da regra e onde a regra da casa
# nao cobre a realidade - e e dai que sai a proxima regra. Montagem
# liberada sem caber e o caso que ninguem previu.
#
# ESTA TELA SO LE. Um botao que apaga, no lugar onde se procura o que deu
# errado, e o jeito mais rapido de perder o que ensina.

FORMATO_DA_DATA = "%d/%m/%Y %H:%M"


def _quando_foi(entrada):
    """
    O 'quando' da entrada como data, ou None.

    A DATA SE ORDENA COMO DATA, e nao como texto. O 'quando' e escrito
    dd/mm/aaaa porque e para gente ler; ordenado como texto, 09/10 viria
    antes de 17/09 e o historico mostraria o mes errado no topo sem
    ninguem entender por que.

    Devolve None para o que nao da para ler - registro escrito a mao, ou
    de uma versao anterior. Essas entradas NAO somem da tela: sao
    justamente as que alguem tem de ver.
    """
    try:
        return datetime.strptime(entrada.get("quando") or "",
                                 FORMATO_DA_DATA)
    except (ValueError, TypeError):
        return None


# A JANELA QUE SE PODE PEDIR. O numero vem do endereco que a pessoa
# digita: 0 listaria o registro inteiro sob o rotulo 'os ultimos 0 dias',
# um negativo poria o corte no FUTURO e esconderia tudo, e um numero
# grande demais estoura o timedelta e derruba a pagina.
MENOS_DIAS, MAIS_DIAS = 1, 3650


def entende_a_data(texto):
    """A data escrita como a casa escreve - '18/09/2026' -, ou None."""
    try:
        return datetime.strptime((texto or "").strip(), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def historico(dias=7, dia=None):
    """
    As montagens do periodo, DA MAIS NOVA PARA A MAIS VELHA.

    'dia' pede um dia so, escrito como a casa escreve - '18/09/2026'.
    Sem ele, valem os ultimos 'dias' dias.

    OS DIAS SAO DE CALENDARIO, e nao de relogio: 'os ultimos 7 dias' e
    hoje mais os seis anteriores, contados do comeco do dia. Com corte
    rolando de 24 em 24 horas, quem abrisse a tela as 16:00 nao veria a
    manha de ontem - e ninguem entende uma lista que muda de conteudo
    conforme a hora.

    NAO PRECISA DA PASTA DO DIA: le o registro, que fica no PC da FIA.
    O operador olha o historico com o V: fora do ar e continua vendo o
    que a equipe decidiu.

    ENTRADA SEM DATA LEGIVEL ENTRA NA LISTA, no fim. Sumir com ela seria
    esconder justamente o que precisa de olho.
    """
    so_este_dia = entende_a_data(dia) if dia else None

    corte = None
    if so_este_dia is None:
        try:
            dias = int(dias)
        except (TypeError, ValueError):
            dias = 7
        dias = max(MENOS_DIAS, min(MAIS_DIAS, dias))
        comeco_de_hoje = datetime.now().replace(hour=0, minute=0, second=0,
                                                microsecond=0)
        corte = comeco_de_hoje - timedelta(days=dias - 1)

    linhas = []
    for entrada in carregar_montagens().values():
        quando = _quando_foi(entrada)
        if so_este_dia is not None:
            if quando is None or quando.date() != so_este_dia:
                continue
        elif corte is not None and quando is not None and quando < corte:
            continue
        linhas.append({
            "arquivo": entrada.get("arquivo"),
            "montagem": entrada.get("montagem"),
            "quando": entrada.get("quando"),
            "quem": entrada.get("quem"),
            "chapa": entrada.get("chapa"),
            "grade": entrada.get("grade"),
            "tipo": entrada.get("tipo"),
            "aprovado_por": entrada.get("aprovado_por"),
            "aprovado_em": entrada.get("aprovado_em"),
            "maquina_trocada": entrada.get("maquina_trocada"),
            "liberado_sem_caber": entrada.get("liberado_sem_caber") or False,
            "liberado_por": entrada.get("liberado_por"),
            "liberado_porque": entrada.get("liberado_porque") or [],
            "_quando": quando,
        })

    # sem data vai para o FIM: nao da para saber quando foi, e por isso
    # mesmo ela nao pode empurrar o que se sabe para baixo
    linhas.sort(key=lambda linha: (linha["_quando"] is not None,
                                   linha["_quando"] or datetime.min),
                reverse=True)
    for linha in linhas:
        linha.pop("_quando", None)
    return linhas


def ja_montado_por_nome(nome, pasta_dia):
    """
    Este NOME ja foi montado, e a montagem dele esta na pasta do dia?

    Serve para uma coisa so: dizer 'ja foi montado' em vez de 'nao esta
    na fila' quando alguem aperta o botao duas vezes. O arquivo ja saiu
    do portao na primeira, entao pela chave nao se acha mais - e 'nao
    esta na fila' mandaria a pessoa procurar um defeito que nao existe.

    A MONTAGEM TEM DE ESTAR NA PASTA DO DIA, e nao basta o nome estar no
    registro: 'CARTAZ.pdf' montado ha duas semanas nao diz nada sobre o
    'CARTAZ.pdf' que chegou hoje. Sem esta conferencia, arquivo novo que
    so ainda nao terminou de chegar ganharia 'ja foi montado - nao
    refaco', e a pessoa iria procurar um defeito que nao existe.
    """
    for e in carregar_montagens().values():
        if e.get("arquivo") != nome:
            continue
        saiu = e.get("montagem")
        if saiu and os.path.exists(os.path.join(pasta_dia, saiu)):
            return True
    return False


def dados_do_painel(arquivo=None, portao=None):
    """
    Tudo que o painel precisa saber: as tabelas da casa e o arquivo.

    'arquivo' e o NOME que a fila mostrou. Ele e procurado NA FILA, e
    nunca juntado a um caminho: so se monta o que esta esperando
    montagem, e de graca isso tambem impede um nome vindo de fora de
    virar caminho para outra pasta.

    Sem arquivo - ou com um que nao esta na fila - as tabelas vem do
    mesmo jeito: o painel continua servindo para conferir uma montagem no
    vazio, que e como ele nasceu.
    """
    escolhido = None
    medida = fila_medida(portao)
    if arquivo:
        for item in medida:
            if item["arquivo"] == arquivo:
                escolhido = dict(item, sugestao=sugestoes_para(item))
                break
    elif len(medida) == 1:
        # UM SO ESPERANDO: e esse, e nao ha o que perguntar.
        #
        # Pedido do operador em 22/09/2026: "quero que vc ja coloque
        # automaticamente a quantidade de paginas que o arquivo ja tem,
        # eu estou tendo que preencher".
        #
        # A fila ja media as paginas e o painel ja as usava - so que o
        # painel aberto SEM o nome na URL nao tinha arquivo nenhum, e ai
        # tudo comecava em zero. Quem clica no nome, na fila, sempre
        # teve; quem digita /painel, nao.
        #
        # COM UM SO NAO HA AMBIGUIDADE. Com dois ou mais continua
        # perguntando - escolher arquivo no lugar de alguem e como sai
        # chapa do servico errado, e o nome nem aparece na tela para a
        # pessoa desconfiar.
        escolhido = dict(medida[0], sugestao=sugestoes_para(medida[0]))

    return {
        "clientes": {america.CLIENTE: {"nome": "América",
                                       "chapas": chapas_da_casa()}},
        "formatos": formatos_da_casa(),
        "arquivo": escolhido,
        # AS DOBRAS QUE A CASA TEM, para a tela poder FECHAR UM LIVRO
        # sozinha sem inventar caderno nenhum.
        #
        # Vai daqui e nao de uma copia em JavaScript: o catalogo e lido
        # de modelo do Preps, cresce quando o operador manda um modelo
        # novo, e uma segunda lista envelheceria calada - a tela
        # ofereceria um caderno que o motor recusa, ou deixaria de
        # oferecer um que ele ja sabe dobrar.
        "dobras": dobras_da_casa(),
    }


def dobras_da_casa():
    """
    [{paginas, vira, colunas, linhas, chapas, em_pe}] - o que sabemos dobrar.

    So entra o que tem ORDEM DAS PAGINAS e ONDE DOBRA. O caderno de 8 em
    frente e verso tem a primeira e nao a segunda - os quatro tutoriais
    do Preps discordam -, entao ele fica de fora: oferecer na tela o que
    o motor recusa e fazer o operador montar o livro duas vezes.
    """
    saida = []
    for por_caderno, vira, repeticao in paginacao.arranjos_conhecidos():
        desenho = paginacao.arranjo(por_caderno, vira, repeticao)
        try:
            paginacao.vaos_do_arranjo(por_caderno, vira, repeticao)
        except paginacao.NaoSeiPaginar:
            continue
        colunas, linhas = desenho["grade"]
        giros = {abs(int(g)) % 180 for _, _, g, _, _ in desenho["celulas"]}
        saida.append({
            "paginas": por_caderno, "vira": vira,
            "repeticao": repeticao,
            "colunas": colunas, "linhas": linhas,
            "chapas": paginacao.chapas_do_caderno(vira),
            # a PECA em pe ou deitada, que e o que muda o tamanho da
            # montagem na chapa
            "em_pe": giros == {0},
        })
    return sorted(saida, key=lambda d: (-d["paginas"], d["vira"],
                                        d["repeticao"]))
