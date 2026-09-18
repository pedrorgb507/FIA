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
import threading
from datetime import datetime

from . import america, marcas, nomes, utils
from .config import SUBPASTA_PARA_MONTAR
from .utils import arquivos_estaveis, chave_arquivo

PORTAO = SUBPASTA_PARA_MONTAR

# O QUE SE MONTA. So PDF, por enquanto: a AMERICA tambem manda .cdr, e o
# caminho de publicar pela Corel ja existe (ver america.converter), mas
# ligar um ao outro e trabalho a parte - e fila que oferece o que ainda
# nao se sabe montar e fila que mente.
#
# Do WhatsApp vem de tudo junto: a mensagem em .txt, o print da conversa,
# a planilha. Nada disso se monta, e nada disso e pendencia - e so o que
# veio na mesma leva.
EXTENSOES = (".pdf",)

REGISTRO = "_montagens.json"

# E A MEDIDA DE CADA ARQUIVO, guardada para nao se refazer.
#
# NAO E O MESMO ARQUIVO DO REGISTRO, e nao e registro de nada: e so o
# retrato do que se mediu, e pode ser apagado a qualquer momento sem
# perder nada - a proxima olhada mede de novo. O registro, esse sim,
# guarda decisao de gente.
MEDIDAS = "_medidas_montagem.json"

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


def portao_existe(portao=None):
    """
    A pasta do portao esta la?

    E pergunta diferente de 'a fila esta vazia', e confundi-las engana
    quem esta olhando: a pasta do dia e nova todo dia e o portao e criado
    por gente. Numa manha em que ninguem o criou, fila vazia e resposta
    errada - a resposta certa e 'nao da para saber'.
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


def anotar_montagem(caminho, o_que):
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
        chave = chave_arquivo(caminho)
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
    montado antes (ver o cabecalho do modulo). Portao que ainda nao
    existe devolve lista vazia: ele e criado por gente, e pilha de erro
    na tela de quem so quis conferir nao ajuda ninguem.

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
# Cinco coisas, e nenhuma e enfeite:
#
#   tamanho    e o que casa com a chapa e com o formato da folha;
#   cor        e ela que escolhe entre a SM 74 e a MOZP acima do F4 -
#              colorido na SM 74, preto-e-branco na MOZP;
#   paginas    para ninguem descobrir depois que era frente e verso - a
#              gravadora nao puxa multiplas paginas;
#   marca      sem marca de corte a montagem nao sabe que lado e o pe, e
#              e do pe que a pinca se mede.
#
# A CONTA E A DA CASA, e isto e a decisao que sustenta a tela inteira: o
# tamanho e as tintas saem do america.medir, o mesmo que o vigia usa para
# fechar chapa. Uma segunda conta aqui deixaria a tela e o vigia podendo
# discordar sobre o mesmo arquivo - e ai um dos dois manda chapa errada.

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
              "marca_no_pe": None, "erro": None}
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
        if isinstance(guardado, dict) and not guardado.get("erro"):
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
