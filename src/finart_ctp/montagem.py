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
from datetime import datetime

from . import america, utils
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


def caminho_do_registro():
    return os.path.join(utils.PASTA_CONTROLE, REGISTRO)


def carregar_montagens():
    """
    O que ja foi montado, por chave de arquivo. Vazio quando nao ha nada.

    LE VAZIO TAMBEM QUANDO O ARQUIVO ESTA ESTRAGADO - JSON pela metade,
    da maquina desligada no meio de uma gravacao. O pior que acontece
    lendo vazio e uma montagem ser oferecida duas vezes; estourar aqui
    seria tela de erro para a equipe inteira, que e pior.

    E ESTRAGADO INCLUI 'JSON VALIDO QUE NAO E UM DICIONARIO'. Um arquivo
    com '[]' dentro passa pelo json.load e depois estoura la na frente,
    na hora de gravar - longe daqui, com outra cara.
    """
    try:
        with io.open(caminho_do_registro(), encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


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

    E O ARQUIVO NUNCA FICA PELA METADE: escreve-se num temporario e ele
    e RENOMEADO por cima, que o sistema faz de uma vez. O temporario tem
    o numero do processo no nome, e nao um nome fixo: dois programas
    gravando ao mesmo tempo - a equipe monta de PCs diferentes, e o
    servidor atende mais de um pedido - escreveriam no MESMO temporario e
    o renomeado sairia com dois JSON emendados. Ai carregar_montagens le
    vazio, e TODA montagem ja feita volta para a fila, que e exatamente o
    trabalho duplicado que este registro existe para impedir.

    O que a releitura NAO fecha: se dois gravarem no mesmo instante, o
    segundo pode ter lido antes de o primeiro renomear, e ai a entrada do
    primeiro se perde. O arquivo continua valido e o pior que acontece e
    uma montagem ser oferecida de novo - uma trava de verdade so vale a
    pena quando alguem vir isso acontecer.
    """
    entrada = dict(o_que or {})
    entrada.setdefault("arquivo", os.path.basename(caminho))
    entrada.setdefault("quando", datetime.now().strftime("%d/%m/%Y %H:%M"))
    try:
        os.makedirs(utils.PASTA_CONTROLE, exist_ok=True)
        tudo = carregar_montagens()
        tudo[chave_arquivo(caminho)] = entrada
        tmp = "%s.%d.tmp" % (caminho_do_registro(), os.getpid())
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump(tudo, f, ensure_ascii=False, indent=1)
        os.replace(tmp, caminho_do_registro())
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
