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

from .config import PASTA_CONTROLE
from .gerempre import VAGAS, SemLigacao, abrir_os, conectar, ja_esta_em_os
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


def mesma_os_na_fila(servico, fila):
    """
    O servico da fila que ja usa o mesmo numero de OS, ou None.

    Aconteceu em 08/09: dois arquivos, '49728 - EDNA - COLINHAS 4MOD' e
    '49728 - EDNA - COLINHAS 4MOD 1', com a MESMA OS 49728. Podem ser
    dois servicos que se cobram separados, ou um trabalho so partido em
    dois arquivos - e a diferenca e o dobro do valor.

    O operador decidiu que nao ha regra: depende do caso. Entao a FIA
    para e pergunta, em vez de escolher o lado errado calada.
    """
    numeros = _os_do_titulo(servico["titulo"])
    if not numeros:
        return None
    for outro in fila:
        if outro["cliente"] != servico["cliente"]:
            continue
        if outro["titulo"] == servico["titulo"]:
            continue
        if numeros & _os_do_titulo(outro["titulo"]):
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


def servico_do_arquivo(nome, cliente, resultado):
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
    o GEREMPRE guarda - conferido em 330 arquivos de agosto.
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
        "titulo": os.path.splitext(nome)[0].upper(),
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
