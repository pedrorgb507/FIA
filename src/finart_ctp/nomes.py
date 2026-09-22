# -*- coding: utf-8 -*-
"""
Como o arquivo de saida se chama.

Nome de entrada:  "49513 - Cliente - miolo CAD2.pdf"
                   ^^^^^   ^^^^^   ^^^^^^^^^^^
                    OS    cliente   descricao

Regra: SO o numero da OS, mais nada. A descricao do arquivo de origem
("capa", "miolo CAD1") NAO entra no nome.

  510x400 mm  -> so a OS                   49572
  775x635 mm  -> OS + R1                   49576R1

  1 pagina    -> sem sufixo de pagina      49572
  2 paginas   -> F (frente) e V (verso)    49513R1 F / 49513R1 V
  3 ou mais   -> 1, 2, 3 ...               49513 1 / 49513 2 / 49513 3
"""

import os
import re
import unicodedata

from .config import (MAXIMO_DESCRICAO_EMPORIO, PALAVRAS_MATERIAL,
                     PALAVRAS_QUE_PEDEM_OLHO, PALAVRAS_SERVICO_EMPORIO,
                     PREFIXOS_DE_BACKUP)

PROIBIDOS = re.compile(r'[\/:*?"<>|]')


def sem_acento(texto):
    """'INTRODUÇÃO' -> 'INTRODUCAO'. Mantem a caixa e os espacos."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def finalizar(nome):
    """
    O acerto final de TODO nome de chapa, seja de que cliente for.

    Sem acento e sem caractere que o Windows nao aceita. Acento em nome
    de chapa e pedido de encrenca: o arquivo atravessa a rede, o RIP da
    gravadora e o InDesign, e nem todos leem UTF-8 do mesmo jeito.
    """
    nome = PROIBIDOS.sub("", sem_acento(nome))
    return re.sub(r"\s+", " ", nome).strip()


def partes_do_nome(nome):
    """('49513', 'miolo CAD2') a partir de '49513 - Cliente - miolo CAD2.pdf'."""
    base = os.path.splitext(os.path.basename(nome))[0]
    seg = [p.strip() for p in base.split(" - ")]
    prefixo = seg[0]
    descricao = seg[-1] if len(seg) > 1 else ""
    return prefixo, descricao


def extrair_os(nome):
    """Primeiro numero de OS do nome, ou None. (usado nos avisos e no log)"""
    oss = extrair_oss(nome)
    return oss[0] if oss else None


def extrair_oss(nome):
    """
    Todos os numeros de OS do inicio do nome, na ordem.

    '49581 49582 49583 - Cliente - bottons.pdf' -> ['49581','49582','49583']
    """
    prefixo, _ = partes_do_nome(nome)
    limpo = re.sub(r"OS[\s_\-]*", " ", prefixo, flags=re.IGNORECASE)
    oss = re.findall(r"\d{4,8}", limpo)
    if oss:
        return oss
    base = os.path.splitext(os.path.basename(nome))[0]
    m = re.search(r"OS[\s_\-]*(\d{3,8})", base, re.IGNORECASE)
    return [m.group(1)] if m else []


def sufixo_pagina(indice, total):
    """'' para 1 pagina, F/V para 2, 1..n para 3 ou mais."""
    if total <= 1:
        return ""
    if total == 2:
        return "F" if indice == 0 else "V"
    return str(indice + 1)


def nome_saida(nome_original, sufixo_formato, indice=0, total=1):
    """
    Nome (sem .pdf) do PDF que vai para o CTP.

    >>> nome_saida("49513 - Cliente - capa.pdf", "")
    '49513'
    >>> nome_saida("49513 - Cliente - miolo CAD2.pdf", "R1", 1, 2)
    '49513R1 V'
    """
    oss = extrair_oss(nome_original)

    nome = (" ".join(oss) if oss else "SEM_OS") + sufixo_formato
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag

    return finalizar(nome)


# ======================================================================
# VOPRIX
# ======================================================================
# Os arquivos vem em .cdr, ja montados no tamanho da chapa, e o nome
# segue outro padrao:
#
#     Envelope_Saco_23x31,5_Colegio_Unus.cdr
#     ^^^^^^^^^^^^^ ^^^^^^^ ^^^^^^^^^^^^
#       produto      medida     cliente
#
# O que vai para o CTP e o produto - o pedaco ANTES da medida - porque e
# por ele que se identifica a chapa na hora de gravar.
#
#     510x400_CM_VOPRIX_Envelope_Saco

MEDIDA = re.compile(r"^\d+(?:[.,]\d+)?(?:x\d+(?:[.,]\d+)?)+$", re.IGNORECASE)


def resumo_voprix(nome):
    """
    'Envelope_Saco_23x31,5_Colegio_Unus.cdr' -> 'Envelope_Saco'

    Tudo que vem antes da primeira medida do nome. Sem medida nenhuma,
    devolve o nome inteiro sem extensao.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    partes = base.split("_")
    for i, parte in enumerate(partes):
        if MEDIDA.match(parte):
            return "_".join(partes[:i]) or base
    return base


# Palavra que nao identifica ninguem e nao conta como nome.
LIGACAO = {"E", "DE", "DA", "DO", "DAS", "DOS", "COM", "SEM", "PARA"}


def _posicoes_de_nome(partes):
    """Onde estao os pedacos que valem como nome de gente ou de empresa."""
    return [i for i, p in enumerate(partes)
            if p and not p.isdigit() and not MEDIDA.match(p)
            and p.upper() not in LIGACAO]


def partes_voprix(nome):
    """
    (CLIENTE, produto) a partir do nome do arquivo.

    >>> partes_voprix("Panfleto_15,0x21,0_4_0_M3RIN.cdr")
    ('M3RIN', 'panfleto')
    >>> partes_voprix("Envelope_Saco_23x31,5_Colegio_Unus.cdr")
    ('COLEGIO_UNUS', 'envelope_saco')

    O cliente sao os DOIS ULTIMOS nomes do arquivo - ou so o ultimo,
    quando so ha um. Numero solto nao conta (a especificacao de cores
    '4_0', a data no fim) nem palavra de ligacao.

    O produto e o que vem antes da medida. Sem medida no nome, e tudo o
    que sobra na frente do cliente.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    partes = base.split("_")

    medida = next((i for i, p in enumerate(partes) if MEDIDA.match(p)), None)
    inicio = medida + 1 if medida is not None else 0
    cauda = partes[inicio:]

    posicoes = _posicoes_de_nome(cauda)
    escolhidas = posicoes[-2:] if len(posicoes) >= 2 else posicoes[-1:]
    cliente = "_".join(cauda[i] for i in escolhidas).upper()

    if medida is not None:
        produto = "_".join(partes[:medida])
    elif escolhidas:
        produto = "_".join(partes[:inicio + escolhidas[0]])
    else:
        produto = base
    return cliente, (produto or base).lower()


def cores_pedidas_voprix(nome):
    """
    (frente, verso) que o NOME do arquivo pede, ou None quando nao diz.

    >>> cores_pedidas_voprix("Luva_Produto_24,0x9,0_4_0_Apoquel.cdr")
    (4, 0)
    >>> cores_pedidas_voprix("Stopper_CE_15,0x21,0_4_4_Apoquel.cdr")
    (4, 4)
    >>> cores_pedidas_voprix("Lamina_Tecnica_21x29,7_Cytopoint.cdr") is None
    True

    A VOPRIX escreve quantas cores o trabalho tem logo DEPOIS DA MEDIDA:
    '..._21x29,7_4_4_Fellocell'. E o cliente dizendo quantas chapas ele
    espera, e isso vale mais que qualquer conta que eu faca no arquivo.

    A ancora e a medida, e nao "dois digitos soltos em algum lugar". Sem
    ela, o '14_09' de 'Bloco_Anotacoes_10x15_Mobil_Lubexx_14_09' passaria
    por especificacao de cor - e aquele bloco e de UMA cor.
    """
    partes = os.path.splitext(os.path.basename(nome))[0].split("_")

    def par(i):
        dois = partes[i:i + 2]
        if len(dois) == 2 and all(p.isdigit() and len(p) == 1 for p in dois):
            return int(dois[0]), int(dois[1])
        return None

    # 1. logo depois da medida - o lugar certo, e sem ambiguidade nenhuma
    for i, pedaco in enumerate(partes):
        if MEDIDA.match(pedaco):
            achou = par(i + 1)
            if achou:
                return achou

    # 2. sem medida reconhecivel, vale QUALQUER par de digitos soltos.
    #
    # A medida nem sempre sai limpa: '10,5x14,8cm' traz a unidade colada
    # e 'Pasta_Bopp,43,0x31,0' traz a virgula do material. Tres dos 45
    # arquivos da VOPRIX caem assim, e todos os tres dizem 4_0.
    #
    # Data nao confunde: '14_09', '05_09', '08_09' tem DOIS algarismos em
    # cada metade, e aqui so passa digito sozinho.
    #
    # E se ainda assim errar, erra para o lado barato: este numero so
    # IMPEDE que uma tinta seja descartada - nunca inventa tinta que nao
    # esta no arquivo. O pior caso e uma chapa a mais na conta, e a casa
    # ja decidiu que isso e melhor que uma chapa a menos no CTP.
    for i in range(len(partes)):
        achou = par(i)
        if achou:
            return achou
    return None


def cores_no_nome(tintas):
    """{'M','C'} -> 'CM'. Cor especial entra depois das quatro de escala."""
    escala = [c for c in "CMYK" if c in tintas]
    especiais = [t for t in sorted(tintas) if t not in "CMYK"]
    return "".join(escala + especiais)


def nome_saida_voprix(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) do PDF que vai para o CTP.

    >>> nome_saida_voprix("Envelope_Saco_23x31,5_Colegio_Unus.cdr",
    ...                   "510x400", {"C", "M"})
    '510x400_CM_VOPRIX_COLEGIO_UNUS_envelope_saco'

    CLIENTE em maiuscula na frente, produto em minuscula atras. O cliente
    vem primeiro porque e ele que identifica o trabalho: dois 'Panfleto'
    no mesmo dia ja bateram de frente na pasta do CTP e sairam como
    'Panfleto' e 'Panfleto_v2', sem ninguem saber qual era qual.

    Com mais de uma pagina, o numero vai no fim: '... 01', '... 02'.
    """
    cliente, produto = partes_voprix(nome_original)
    miolo = "%s_%s" % (cliente, produto) if cliente else produto
    nome = "%s_%s_VOPRIX_%s" % (formato, cores_no_nome(tintas) or "K", miolo)
    if total > 1:
        nome += " %02d" % (indice + 1)
    return finalizar(nome)


# ======================================================================
# FIALHO BRINDES
# ======================================================================
# O nome de entrada nao segue padrao nenhum - e o titulo que a pessoa deu
# ao arquivo:
#
#     FORRO AGENDA unicidades  2027.pdf
#     MIOLO caderno sicoob montagen formato 48x66 9 imagem 2 chapas.pdf
#     AGENDA_CADERNO 2027_ CREDI COMIGO.pdf
#
# A chapa leva o NOME INTEIRO do arquivo, sem limite de tamanho:
#
#     510x400_FIALHO_CMYK_AGENDA_CADERNO 2027_ CREDI COMIGO
#
# ATE 14/09/2026 ERA OUTRA REGRA, e ela foi desfeita pelo operador:
# "eles estao mandando arquivos parecidos, muda o nome, entao vamos
# manter o padrao tamanho da chapa, FIALHO, cmyk, so que no final coloca
# o nome completo do arquivo, sem limites de caracteres".
#
# A regra antiga resumia o nome a uma palavra 'principal', jogando fora
# tipo de material, medida e numero - 'FORRO AGENDA unicidades 2027'
# virava so 'UNICIDADES'. A ideia era boa e o efeito foi ruim: o Fialho
# manda muitos arquivos parecidos do mesmo cliente final, e o resumo os
# colapsava no MESMO nome de chapa.
#
# Aconteceu em 14/09/2026: 'AGENDA_2027_ CREDI COMIGO capa.pdf' e
# 'AGENDA_CADERNO 2027_ CREDI COMIGO.pdf' sao dois servicos diferentes e
# os dois viravam '510x400_FIALHO_CREDI COMIGO'. Como numerar_se_preciso
# numera pelo que ja esta na pasta, a segunda leva do dia saiu como
# ' 02' e ' 03' - um servico de duas paginas com numeracao de tres
# chapas, e ninguem olhando a pasta saberia qual era qual.
#
# As cores entraram junto, para o Fialho ficar igual aos outros clientes:
# VOPRIX, EMPORIO e VIVA ja traziam as tintas no nome.


def limpo(texto):
    """
    'INTRODUÇÃO  unicidades' -> 'INTRODUCAO UNICIDADES'.

    Nasceu para o resumo do FIALHO, que foi aposentado em 14/09/2026, e
    FICOU porque o EMPORIO e o reconhecedor de backup do Corel dependem
    dele - comparar palavra por palavra so funciona com tudo na mesma
    caixa e sem acento.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    so_util = re.sub(r"[^A-Za-z0-9 ]+", " ", sem_acento)
    return re.sub(r"\s+", " ", so_util).strip().upper()


# O que separa o nome do numero da pagina, na FIALHO.
#
# Era um ESPACO ('...TOCANTINS 01') e virou sublinhado em 17/09/2026:
# "cada pagina, num pdf diferente, diferenciando no final do nome com
# _01, _02 e assim por diante" - o operador.
#
# Quem LE aceita os dois (ver numerar_se_preciso e proxima_sequencia).
# Tem de aceitar: as chapas gravadas antes da mudanca estao na pasta do
# dia com espaco, e a numeracao da FIALHO se faz olhando a pasta - um
# leitor estreito recomecaria do 01 e gravaria por cima do que ja saiu.
SEPARADOR_DA_SEQUENCIA = "_"


def nome_saida_fialho(nome_original, formato, tintas, sequencia=None):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_fialho("FORRO AGENDA unicidades  2027.pdf", "510x400",
    ...                   set("CMYK"))
    '510x400_FIALHO_CMYK_FORRO AGENDA unicidades 2027'
    >>> nome_saida_fialho("MIOLO caderno sicoob.pdf", "730x600", {"K"}, 12)
    '730x600_FIALHO_K_MIOLO caderno sicoob_12'

    O nome do arquivo vai INTEIRO, como a pessoa escreveu - so caem o
    acento e o que o Windows nao aceita, no finalizar, que e o mesmo
    acerto de todo cliente. Sem limite de letras: quem corta perde
    justamente o pedaco que distingue dois arquivos parecidos, que e o
    defeito que esta regra veio consertar.

    Sem sequencia, sem numero: chapa sozinha nao precisa ser numerada. O
    numero e do DIA e do trabalho, nao do arquivo. Quem conta e o
    processador, olhando a pasta de saida.
    """
    inteiro = os.path.splitext(os.path.basename(nome_original))[0].strip()
    nome = "%s_FIALHO_%s_%s" % (formato, cores_no_nome(tintas) or "K",
                                inteiro)
    if sequencia is not None:
        nome += "%s%02d" % (SEPARADOR_DA_SEQUENCIA, sequencia)
    return finalizar(nome)


# ======================================================================
# EMPORIO PRINT
# ======================================================================
# Entra como a SOLIDA - PDF pronto, com a OS na frente - e sai como a
# VOPRIX, com formato, cores e cliente no nome:
#
#     01995 - CHAPA CAIXA 4796.pdf
#       ->  510x400_CMYK_EMPORIO_01995_CAIXA 4796_1
#           510x400_GRAY_EMPORIO_01995_CAIXA 4796_2
#
# Quem identifica o servico e a OS. A descricao vem junto, limpa das
# palavras que so dizem que aquilo e um trabalho de chapa.


def resumo_emporio(nome):
    """
    '01995 - CHAPA CAIXA 4796.pdf' -> 'CAIXA 4796'

    Tudo depois da OS, sem as palavras de servico e sem os tracos. Se
    nao sobrar nada, devolve vazio - ai o nome fica so com a OS, que ja
    identifica o trabalho.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    oss = extrair_oss(nome)
    if oss:
        # tira a OS e o que vier antes dela
        corte = base.find(oss[-1])
        if corte >= 0:
            base = base[corte + len(oss[-1]):]

    base = re.sub(r"[_\-]+", " ", base)
    palavras = [p for p in base.split(" ") if p]
    ficam = [p for p in palavras
             if limpo(p) not in PALAVRAS_SERVICO_EMPORIO]
    return encurtar(re.sub(r"\s+", " ", " ".join(ficam)).strip(),
                    MAXIMO_DESCRICAO_EMPORIO)


def encurtar(texto, teto):
    """
    Corta o texto no teto SEM partir palavra.

    'Guia do Comprador com canhoto de entrega' em 25 vira 'Guia do
    Comprador com' - e nao 'Guia do Comprador com can', que nao quer
    dizer nada em nome de chapa.
    """
    if len(texto) <= teto:
        return texto
    corte = texto[:teto + 1]
    espaco = corte.rfind(" ")
    return (corte[:espaco] if espaco > 0 else texto[:teto]).strip()


def palavra_que_pede_olho(nome):
    """
    QUAL palavra do nome pede conferencia humana, ou None.

    >>> palavra_que_pede_olho("01929 - CHAPA VERNIZ - Caixas.pdf")
    'VERNIZ'
    >>> palavra_que_pede_olho("Mascara_Folder_29,7x15_Chapadeira.cdr")
    'MASCARA'

    Existe para a MENSAGEM nao mentir. Enquanto a lista tinha uma
    palavra so, a pendencia podia dizer "o nome diz VERNIZ" de cor;
    com MASCARA dentro dela, em 21/09/2026, esse texto passaria a
    acusar VERNIZ num arquivo onde a palavra nem aparece - e quem
    fosse conferir procuraria o que nao esta escrito.

    Casando mais de uma (o caso real e o
    'Mascara_Verniz Local_...Leharmony.cdr', que tem as duas),
    devolve a PRIMEIRA na ordem do nome - a que a pessoa le antes.
    """
    for palavra in limpo(nome).split(" "):
        if palavra in PALAVRAS_QUE_PEDEM_OLHO:
            return palavra
    return None


def pede_olho(nome):
    """True quando o nome do arquivo pede conferencia humana."""
    return palavra_que_pede_olho(nome) is not None


def nome_saida_emporio(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_emporio("01995 - CHAPA CAIXA 4796.pdf", "510x400",
    ...                    set("CMYK"), 0, 2)
    '510x400_CMYK_EMPORIO_01995_CAIXA 4796_1'

    Com mais de uma pagina, o numero vai no fim depois de um _, que e
    como os operadores ja escrevem.
    """
    oss = extrair_oss(nome_original)
    partes = [formato, cores_no_nome(tintas) or "K", "EMPORIO",
              " ".join(oss) if oss else "SEM_OS"]
    descricao = resumo_emporio(nome_original)
    if descricao:
        partes.append(descricao)

    nome = "_".join(partes)
    if total > 1:
        nome += "_%d" % (indice + 1)
    return finalizar(nome)


# ======================================================================
# VIVA ACABAMENTOS
# ======================================================================
# A descricao e o proprio nome do arquivo, e frente/verso saem F e V,
# como na Solida. Foi lido das chapas que os operadores fecharam a mao:
#
#     GRADE 1637.pdf  ->  510x400_CMYK_VIVA_GRADE 1637
#     GRADE 38.pdf    ->  510x400_CMYK_VIVA_GRADE 38 F  e  ... V


def nome_saida_viva(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_viva("GRADE 1637.pdf", "510x400", set("CMYK"))
    '510x400_CMYK_VIVA_GRADE 1637'
    >>> nome_saida_viva("GRADE 38.pdf", "510x400", set("CMYK"), 1, 2)
    '510x400_CMYK_VIVA_GRADE 38 V'

    A descricao sai do arquivo como esta escrita - so o acento cai, no
    finalizar. Duas paginas viram F e V; tres ou mais, 1, 2, 3.
    """
    descricao = os.path.splitext(os.path.basename(nome_original))[0].strip()
    nome = "%s_%s_VIVA_%s" % (formato, cores_no_nome(tintas) or "K", descricao)
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag
    return finalizar(nome)


# ======================================================================
# IDEAL GRAFICA
# ======================================================================
# COMO A VIVA, por ordem do operador em 22/09/2026: "a forma que vc esta
# nomeando o arquivo da IDEAL nao e a correta quando voce envia para o
# ctp (...) o padrao pode seguir como da VIVA".
#
# ATE ENTAO ELA CAIA NO PADRAO DA SOLIDA, e nao por decisao: o
# nome_da_chapa nao tinha ramo para a IDEAL, entao ela escorregava para
# o nome_saida() do fim, que extrai a OS do nome e devolve so o numero.
# As chapas sairam '116530.pdf' e '116546_v2.pdf'.
#
# E EU DOCUMENTEI O ERRO COMO SE FOSSE A REGRA. Na skill eu tinha
# escrito, por suposicao, que ela sairia '510x400_CMYK_IDEAL_...';
# vi sair '116530', achei que a suposicao e que estava errada, e
# "corrigi" a skill para o comportamento. O operador desfez: a suposicao
# estava certa, quem estava errado era o codigo.
#
# A LICAO, que vale alem deste cliente: o que o programa FAZ nao e a
# regra da casa. Ver o programa fazer X e escrever "a regra e X" troca
# um defeito por documentacao que o defende. Quem decide nome de chapa e
# quem grava.
#
# A DESCRICAO E O NOME DO ARQUIVO INTEIRO, como na VIVA - inclusive o
# 'OS 116530 - ' da frente. Nao invento corte: o EMPORIO separa a OS da
# descricao, e se a casa quiser isso aqui e outra conversa, com a
# palavra dele.


def nome_saida_ideal(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_ideal("OS 116530 - caixinha brasa express 26.pdf",
    ...                  "510x400", set("CMYK"))
    '510x400_CMYK_IDEAL_OS 116530 - caixinha brasa express 26'
    >>> nome_saida_ideal("OS 116546- Goias cesta basica.pdf",
    ...                  "510x400", set("CMYK"), 1, 2)
    '510x400_CMYK_IDEAL_OS 116546- Goias cesta basica V'

    Duas paginas viram F e V; tres ou mais, 1, 2, 3 - como na VIVA e na
    SOLIDA.
    """
    descricao = os.path.splitext(os.path.basename(nome_original))[0].strip()
    nome = "%s_%s_IDEAL_%s" % (formato, cores_no_nome(tintas) or "K",
                               descricao)
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag
    return finalizar(nome)


MARCA_DE_MONTAGEM = "_montagem"


def e_verniz(nome):
    """
    True para arquivo de VERNIZ ou de MASCARA - que vira FOTOLITO,
    nao chapa.

    Regra do operador, 17/09/2026, em duas conversas. Primeiro so a
    VIVA: "quando o arquivo chegar com nome de verniz*.*, pode
    desconsiderar; nao precisa fazer nada, nem precisa avisar - so
    deixar parado na pasta". Depois, de todos: "vamos colocar a trava
    entao em todos os arquivos que tiver o nome de verniz, de todos os
    clientes... pois serao feitos fotolitos e nao chapas, e voce ainda
    nao tem essa habilidade".

    O REGISTRO CONCORDA COM A REGRA, e foi o que me convenceu de que ela
    vale para o nome inteiro e nao so para o comeco. Dos 11 arquivos com
    'verniz' no nome desde 02/09/2026, **todos os 11 geraram ZERO
    chapas**:

        6 da VIVA     'verniz 17xx.cdr'            erro (.cdr)
        4 da VOPRIX   'Mascara_Verniz Local...'    erro - e aqui a
                      palavra esta no MEIO do nome
        1 do EMPORIO  '01929 - CHAPA VERNIZ - ...' feito_a_mao

    Casa por PALAVRA, e nao por pedaco: 'Mascara_Verniz' conta,
    'VERNIZADO' nao contaria. E a mesma conta do 'pede_olho', que ate
    hoje mandava parar e perguntar nesses casos - a palavra e a mesma, e
    o que mudou foi a resposta: de 'confira antes' para 'nao e comigo'.

    MASCARA ENTROU EM 21/09/2026, pela mesma porta e pelo mesmo motivo.
    O operador: "aconteceu na pasta da voprix, MASCARA, siga a mesma
    regra para quando o nome for verniz, o nome MASCARA tb e para uma
    mascara de verniz, entao pode desconsiderar quando cair um arquivo
    com esse nome".

    E o registro concordou de novo: dos 5 arquivos com 'Mascara' no
    nome desde 09/09/2026, **os 5 geraram ZERO chapas** - os cinco
    viraram pendencia de TAMANHO (478x328, 660x480, 297x420), que e
    medida de PECA e nunca de chapa. Mascara se faz no tamanho do
    trabalho. No CTP inteiro nao ha uma chapa com 'mascara' no nome.

    Tres deles ja traziam 'Verniz' junto - e sao justamente os que
    aparecem aqui em cima, na conta do verniz. Os dois que escaparam
    sao os que custaram pendencia: o 'Mascara_Pasta_Bolsa_46x31_
    Cruvinel...' em 15/09 e o 'Mascara_Folder_29,7x15_4_4_Chapadeira'
    em 21/09, este ultimo o que provocou o pedido.

    SILENCIO AQUI E O PEDIDO, e nao descuido. Em toda a outra parte
    desta casa pular arquivo calado e defeito - a armadilha 19 do
    fechamento existe para isso. A diferenca: aqui o operador SABE que o
    arquivo esta ali e sabe o que fazer com ele. O aviso nao lhe dizia
    nada de novo, e era ele que vinha abrindo uma tela cheia por
    arquivo, todo dia.

    → O dia em que a FIA mandar para fotolito, esta funcao deixa de ser
    'ignore' e passa a ser 'mande para o outro caminho'.
    """
    return pede_olho(nome)


# O comeco do nome dos relatorios que a FIA deixa na pasta do cliente.
#
# Sao dois - 'RELATORIO ATUAL <data> <hora>.pdf' na raiz e 'RELATORIO
# CHAPAS <cliente> (<data>).pdf' dentro da pasta do dia - e os dois
# ficam em pasta que o vigia varre.
MARCA_DE_RELATORIO = "RELATORIO "


def e_relatorio(nome):
    """
    True para o relatorio de estoque que a propria FIA guardou ali.

    O vigia tem de pular esses, e pelo mesmo motivo da montagem: e
    SAIDA, nao entrada. O relatorio do dia mora dentro da pasta do dia
    do cliente - a mesma pasta de onde a arte vem -, e sem esta trava a
    FIA o leria como arte na volta seguinte, gravaria uma chapa do
    proprio relatorio e ainda abriria OS cobrando por ela.

    Nao ha risco de pegar arte do cliente por engano: nenhum dos 295
    arquivos ja processados comeca com 'RELATORIO'.
    """
    base = os.path.basename(nome or "").upper()
    return base.startswith(MARCA_DE_RELATORIO)


def e_montagem(nome):
    """
    True para 'VALDINO - CHAPADO_montagem.pdf' - arquivo que a FIA
    mesma deixou na pasta do dia.

    O vigia tem de pular esses. A montagem e SAIDA, nao entrada: se ela
    voltasse pela porta da frente sairia uma segunda chapa e um segundo
    item na OS, do mesmo servico. Ver salvar_montagem.

    Pega tambem a montagem que o operador fez a mao, que e como o
    'O.S 1034 - WAN SEMANA DO CLIENTE_montagem.cdr' de 14/09/2026 - e
    nao ha perda nisso: quem anda e o arquivo original, e a FIA refaz a
    montagem dele.

    Depois da marca so pode vir o sufixo de pagina, e SEPARADO POR
    ESPACO ('..._montagem F.pdf', '..._montagem 02.pdf'). Sem o espaco
    nao conta: '525x459_CMYK_AMERICA_Arte Rifa 2025_MONTAGEM02.pdf' e
    nome de chapa da AMERICA, e nao a nossa montagem.

    Pular arquivo por engano e pior do que fazer duas vezes: ninguem
    percebe. Por isso a regra e apertada, e quem chama ainda pergunta se
    o cliente e daqueles que salvam montagem.
    """
    base = os.path.splitext(os.path.basename(nome or ""))[0]
    corte = base.lower().rfind(MARCA_DE_MONTAGEM)
    if corte < 0:
        return False
    sobra = base[corte + len(MARCA_DE_MONTAGEM):]
    if not sobra:
        return True
    if sobra[0] != " ":
        return False
    resto = sobra.strip()
    return resto.upper() in ("F", "V") or resto.isdigit()


def e_backup_do_corel(nome):
    """
    True quando o arquivo e copia de seguranca que o CorelDRAW cria.

    'Copia_de_seguranca_de_verniz 1705.cdr' nao e trabalho: e backup
    automatico, ao lado do arquivo do operador. Sem isto, cada uma delas
    viraria uma pendencia inutil na tela, todo dia.
    """
    limpo_nome = limpo(os.path.basename(nome))
    return limpo_nome.startswith(tuple(PREFIXOS_DE_BACKUP))


# ======================================================================
# CREATIVE
# ======================================================================
# Mesmo nome da VIVA - formato, cores, cliente e o nome do arquivo - lido
# da chapa que o operador fechou a mao em 02/09:
#
#     santinho cruvinel.pdf -> 510x400_CMYK_CREATIVE_santinho cruvinel
#
# O que muda na Creative nao esta no nome: e que a arte chega menor que a
# chapa e o programa a monta nela, com a pinca no pe (processador.py).


def nome_saida_prime(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_prime("POLIPECAS - ETQIEUTAS.cdr", "510x400",
    ...                  {"C", "M", "K"})
    '510x400_CMK_PRIME_POLIPECAS - ETQIEUTAS'

    Mesma forma da CREATIVE e da VIVA - formato, cores, cliente e o nome
    do arquivo INTEIRO. Lido das chapas que os operadores fecharam a mao:

        510X400_CMK_PRIME_POLIPECAS_ETQIEUTAS
        510X400_GRAY_PRIME_VALDINO_CHAPADO
        510X400_CMYK_PRIME_O.S 1034 - WAN SEMANA DO CLIENTE

    O nome INTEIRO importa aqui mais do que nos outros: a PRIME manda o
    numero da O.S DELA na frente ('O.S 1034 - ...'), e dois servicos
    diferentes podem trazer o mesmo numero. "nao pode ler somente o
    primeiro nome, ou o numero da OS, para pensar que e o mesmo servico:
    tem que ler todo o nome e comparar" - o operador, 14/09/2026.

    O formato no nome e o da CHAPA, nao o da arte: a arte chega menor e
    e montada na 510x400.
    """
    descricao = os.path.splitext(os.path.basename(nome_original))[0].strip()
    nome = "%s_%s_PRIME_%s" % (formato, cores_no_nome(tintas) or "K",
                               descricao)
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag
    return finalizar(nome)


def nome_saida_creative(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_creative("santinho cruvinel.pdf", "510x400", set("CMYK"))
    '510x400_CMYK_CREATIVE_santinho cruvinel'

    O formato no nome e o da CHAPA, nao o da arte: quem grava precisa
    saber o que vai para a maquina, e o que vai e uma 510x400.
    """
    descricao = os.path.splitext(os.path.basename(nome_original))[0].strip()
    nome = "%s_%s_CREATIVE_%s" % (formato, cores_no_nome(tintas) or "K",
                                  descricao)
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag
    return finalizar(nome)


def veio_do_portao(caminho):
    """
    True se o arquivo esta DENTRO da subpasta 'PARA CTP'.

    E a assinatura de quem montou: a mesma arte que PARA na pasta do dia
    - um .cdr solto ali e arte por montar, esperando gente - dentro da
    PARA CTP e montagem PRONTA, feita e revisada. Nao ha campo, nem
    marca no arquivo, nem tela para clicar: a pasta e o combinado.

    Olha SO a pasta que contem o arquivo, e nao o caminho inteiro. Uma
    'PARA CTP' la em cima na arvore do cliente nao pode aprovar tudo o
    que estiver embaixo dela.
    """
    import os
    from .config import SUBPASTA_PARA_CTP
    pai = os.path.basename(os.path.dirname(os.path.abspath(caminho)))
    return pai.upper() == SUBPASTA_PARA_CTP.upper()
