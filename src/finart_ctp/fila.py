# -*- coding: utf-8 -*-
r"""
A fila de servicos esperando OS.

A OS do GEREMPRE tem quatro vagas, e os operadores enchem as quatro:
das 1.877 OS da Solida, 1.531 usam as quatro e so 97 usam uma. A FIA faz
igual - junta ate quatro do mesmo cliente e ai abre.

REGRA DA SOBRA, dada pelo operador: com uma, duas ou tres vagas, ESPERA O
DIA SEGUINTE. Nao se abre OS pela metade so porque o dia acabou; o que
sobrou entra na proxima, junto com o que chegar.

OUTRO OPERADOR PODE TER FECHADO. A OS tambem se abre a mao, e e normal
que alguem tenha lancado o servico antes da FIA chegar nele. Por isso,
antes de abrir, cada servico da fila e procurado nas OS que ja existem -
o que ja foi lancado sai da fila calado, sem virar OS repetida. Faturar
duas vezes o mesmo servico e pior do que nao faturar.

A fila fica em disco: se a FIA for desligada no meio do dia, o que ela
fechou e ainda nao lancou continua esperando.
"""

import json
import os
import re

from .config import CLIENTES_COM_OS_NO_NOME, PASTA_CONTROLE
from .gerempre import (LETRAS_NO_TITULO, MARCA_REGRAVACAO, VAGAS,
                       SemLigacao, abrir_os, conectar, ja_esta_em_os)
from .nomes import extrair_oss
from .utils import anotar_pendencia, log

ARQUIVO = "_fila_os.json"


def caminho():
    return os.path.join(PASTA_CONTROLE, ARQUIVO)


def carregar():
    try:
        with open(caminho(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def salvar(fila):
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        tmp = caminho() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=1)
        os.replace(tmp, caminho())
    except OSError as e:
        log("Nao consegui gravar a fila de OS: %s" % e, alerta=True)


def _os_do_titulo(titulo):
    """Os numeros de OS que aparecem no titulo do servico."""
    return set(extrair_oss(titulo))


# ----------------------------------------------------------------------
# DOIS ARQUIVOS COM A MESMA OS: QUANDO PARAR E QUANDO SEGUIR
# ----------------------------------------------------------------------
# Tres casos de verdade, e a regra tem de acertar os tres:
#
#   08/09  '49728 - EDNA - COLINHAS 4MOD'
#          '49728 - EDNA - COLINHAS 4MOD 1'
#          A mesma OS e o MESMO nome, com um contador no fim. Pode ser
#          um trabalho so partido em dois arquivos, pode ser dois
#          servicos - e a diferenca e o dobro do valor. PARA E PERGUNTA.
#
#   14/09  '49854 HENRIQUE 49858 JUNIOR 49859 RICARDINHO 49860 CORI -
#           GRADE SANTINHOS'  e  '49854 - HENRIQUE CESAR - SANTINHOS'
#          Uma GRADE com quatro OS dentro, e um dos quatro sozinho. O
#          Henrique pode estar nos dois. PARA E PERGUNTA.
#
#   15/09  '49862 - MIRIA PIRES - FOLDER'
#          '49862 - MIRIA PIRES - FOLDER CORRIGIDO'
#          A mesma OS, e o nome diz o que mudou. "e diferente do arquivo
#          anterior, pois e uma correcao do cliente, um novo arquivo, e
#          tem que ser feita uma nova OS" - o operador, 15/09/2026.
#          SEGUE, e cobra os dois.
#
# O que separa o terceiro dos outros dois: ali os dois nomes carregam
# EXATAMENTE a mesma OS - nem mais nem menos - e a descricao MUDOU de
# verdade, com palavra e nao com contador.
#
# "voce precisa ler todo nome do arquivo para depois barrar" - o
# operador, no mesmo dia. E o que estas duas funcoes fazem.

# Um contador no fim do nome: ' 1', '_2', '(3)'. Marca copia ou parte,
# e nao servico diferente.
CONTADOR_NO_FIM = re.compile(r"[\s_\-]*\(?\d{1,3}\)?$")


def descricao_do_servico(titulo):
    """
    O que sobra do nome sem a OS e sem o contador do fim.

        '49728 - EDNA - COLINHAS 4MOD'            EDNACOLINHAS4MOD
        '49728 - EDNA - COLINHAS 4MOD 1'          EDNACOLINHAS4MOD
        '49862 - MIRIA PIRES - FOLDER'            MIRIAPIRESFOLDER
        '49862 - MIRIA PIRES - FOLDER CORRIGIDO'  MIRIAPIRESFOLDERCORRIGIDO

    O '4MOD' fica inteiro: o contador so sai quando e uma palavra
    sozinha de numeros no fim.
    """
    base = (titulo or "").upper()
    for numero in extrair_oss(titulo):
        base = base.replace(numero, " ")
    base = CONTADOR_NO_FIM.sub("", base.strip())
    return "".join(c for c in base if c.isalnum())


def mesma_os_na_fila(servico, fila):
    """
    O servico da fila que obriga a parar e perguntar, ou None.

    SO VALE PARA QUEM TRAZ A OS NO NOME - a SOLIDA e o EMPORIO. Nos
    outros clientes o nome nao carrega OS nenhuma, e procurar numero ali
    e procurar o que nunca esteve: 'extrair_oss' casa \\d{4,8}, entao
    'AGENDA_CADERNO 2027' e 'CAPA CADERNO _2027' viraram "a mesma OS
    2027" - que e o ANO da agenda. Aconteceu no FIALHO em 14/09/2026, e
    travou os dois arquivos. Ver CLIENTES_COM_OS_NO_NOME no config.
    """
    if servico.get("cliente") not in CLIENTES_COM_OS_NO_NOME:
        return None

    numeros = _os_do_titulo(servico["titulo"])
    if not numeros:
        return None

    minha = descricao_do_servico(servico["titulo"])
    for outro in fila:
        if outro["cliente"] != servico["cliente"]:
            continue
        if outro["titulo"] == servico["titulo"]:
            continue
        dele = _os_do_titulo(outro["titulo"])
        if not (numeros & dele):
            continue                       # nem se cruzam

        # AS OS BATEM EXATAMENTE E O NOME MUDOU? Sao dois servicos: a
        # correcao que o cliente mandou depois e gravacao nova, e se
        # cobra. Foi a regra dada em 15/09/2026.
        if numeros == dele and minha != descricao_do_servico(outro["titulo"]):
            continue

        return outro
    return None


def entrar(servico, fila=None):
    """
    Poe um servico na fila. Devolve a fila.

    servico: {'titulo', 'cliente', 'chapa': [larg, alt], 'chapas': n}

    Dois arquivos com a mesma OS param aqui e viram pendencia: cobrar um
    ou cobrar dois muda o valor, e quem decide isso e gente.
    """
    fila = carregar() if fila is None else fila
    ja = {(s["cliente"], s["titulo"]) for s in fila}
    if (servico["cliente"], servico["titulo"]) in ja:
        return fila

    irmao = mesma_os_na_fila(servico, fila)
    if irmao is not None:
        anotar_pendencia(
            servico["titulo"],
            "este arquivo e o '%s' trazem a MESMA OS. Nao lancei nenhum "
            "dos dois: sao dois servicos na OS, ou um so com as chapas "
            "somadas? Lance a mao ou me diga a regra" % irmao["titulo"][:44])
        return fila

    # LISTA NOVA, e nao append na recebida. Com append, quem chamou
    # ficava com a mesma lista de volta - o objeto era um so -, e
    # comparar o tamanho de antes com o de depois dava sempre igual.
    # Foi assim que a primeira OS da VIVA deixou de ser aberta em
    # silencio: o programa achou que a fila tinha recusado o servico.
    return fila + [servico]


# A MARCA DA REGRAVACAO mora no gerempre (importada la em cima), porque
# e ele quem precisa reservar espaco para ela ao cortar o titulo. Ela
# continua acessivel como fila.MARCA_REGRAVACAO.


def titulo_do_servico(nome, regravacao=False):
    """
    O titulo do servico: o nome do arquivo em caixa alta, sem extensao.

    INTEIRO, sem corte. Quem corta e o gerempre.titulo_da_vaga, na hora
    de gravar, e ele corta o MEIO e guarda o fim - e do fim que sai a
    diferenca entre dois servicos da mesma peca. Cortar aqui apagaria
    essa diferenca antes de qualquer um poder usa-la: a fila, a busca
    por 'ja foi lancado?' e a pendencia passariam todas a falar de um
    nome que nao existe.

    Sendo regravacao, a marca entra no fim, e la ela FICA: o
    titulo_da_vaga a reserva antes de fazer a conta das letras.
    """
    base = os.path.splitext(nome)[0].upper()
    if not regravacao:
        return base
    return "%s %s" % (base, MARCA_REGRAVACAO)


def servico_do_arquivo(nome, cliente, resultado, regravacao=False):
    """
    O servico de OS de um arquivo que acabou de fechar, ou None.

    Cobra o que SAIU, nao o que se esperava: 'chapas' vem do processador,
    uma entrada por pagina que virou chapa de verdade, com o tamanho e o
    numero de tintas. Quatro tintas gastam quatro chapas de metal, e e
    por chapa que o GEREMPRE cobra.

    Devolve None - sem cobrar - em tres casos, e os tres sao de proposito:

      - o arquivo deu problema em alguma pagina. Ele ja virou pendencia,
        e quem resolver e quem lanca. Cobrar meio arquivo e pior que nao
        cobrar;
      - nenhuma chapa saiu;
      - as paginas sairam em chapas de tamanhos DIFERENTES. Uma vaga da
        OS tem um tamanho so, e dividir um arquivo em duas vagas com
        precos diferentes e decisao de gente, nao de programa.

    O titulo e o nome do arquivo sem extensao, em caixa alta, que e como
    o GEREMPRE guarda - conferido em 330 arquivos de agosto. Sendo
    regravacao, ele leva a marca ARQUIVO NOVO no fim.
    """
    if resultado.get("status") != "ok":
        return None
    chapas = resultado.get("chapas") or []
    if not chapas:
        return None

    medidas = {tuple(c["chapa"]) for c in chapas}
    if len(medidas) > 1:
        anotar_pendencia(
            nome,
            "as paginas sairam em chapas de tamanhos diferentes (%s). Uma "
            "vaga da OS tem um tamanho so - lance a mao, que o preco de "
            "cada uma e outro"
            % " e ".join("%.0fx%.0f" % m for m in sorted(medidas)))
        return None

    larg, alt = medidas.pop()
    return {
        "titulo": titulo_do_servico(nome, regravacao),
        "cliente": cliente,
        "chapa": [larg, alt],
        "chapas": sum(c["tintas"] for c in chapas),
    }


def por_cliente(fila):
    """{cliente: [servicos]} na ordem em que entraram."""
    grupos = {}
    for servico in fila:
        grupos.setdefault(servico["cliente"], []).append(servico)
    return grupos


def _tirar(fila, saindo):
    """A fila sem estes servicos."""
    fora = {(s["cliente"], s["titulo"]) for s in saindo}
    return [s for s in fila if (s["cliente"], s["titulo"]) not in fora]


def despachar(fila=None, con=None, minimo=VAGAS):
    """
    Abre OS para quem ja juntou 'minimo' servicos. Devolve (fila, [os]).

    Antes de abrir, limpa da fila o que outro operador ja lancou a mao.
    Sem ligacao com o GEREMPRE, a fila fica como esta e ninguem perde
    nada - o servico continua esperando.
    """
    fila = carregar() if fila is None else fila
    if not fila:
        return fila, []

    proprio = con is None
    try:
        con = con or conectar()
    except SemLigacao as e:
        log("GEREMPRE fora do ar (%s). %d servico(s) seguem na fila."
            % (e, len(fila)), alerta=True)
        return fila, []

    abertas = []
    try:
        cur = con.cursor()

        # 1. o que ja foi lancado a mao sai da fila, sem alarde
        ja_feitos = [s for s in fila
                     if ja_esta_em_os(cur, s["titulo"], s["cliente"])]
        if ja_feitos:
            fila = _tirar(fila, ja_feitos)
            for s in ja_feitos:
                log("GEREMPRE: '%s' ja estava em OS - alguem lancou a mao. "
                    "Tirei da fila." % s["titulo"][:52])

        # 2. quem tem vaga cheia, vira OS
        for cliente, servicos in sorted(por_cliente(fila).items()):
            while len(servicos) >= minimo:
                lote, servicos = servicos[:VAGAS], servicos[VAGAS:]
                try:
                    numero = abrir_os(lote, con=con)
                    abertas.append(numero)
                    fila = _tirar(fila, lote)
                except Exception as e:
                    log("GEREMPRE: nao consegui abrir OS de %s: %s"
                        % (cliente, str(e)[:90]), alerta=True)
                    break
    finally:
        salvar(fila)
        if proprio:
            try:
                con.close()
            except Exception:
                pass
    return fila, abertas


def esperando(fila=None):
    """Quantos servicos de cada cliente ainda esperam vaga."""
    fila = carregar() if fila is None else fila
    return {cliente: len(servicos)
            for cliente, servicos in sorted(por_cliente(fila).items())}
