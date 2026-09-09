# -*- coding: utf-8 -*-
r"""
A OS no GEREMPRE: abrir ordem de servico para a gravacao das chapas.

O GEREMPRE e o programa da empresa, em Firebird 1.5. Nada aqui toca o
banco de producao enquanto GEREMPRE_DSN apontar para a copia de teste -
e e assim que ele vem de fabrica.

COMO UMA OS E MONTADA. Ela tem CABECALHO e ate QUATRO VAGAS de servico.
Foi lido da OS 19140, aberta a mao por um operador:

    cabecalho   OSCOD (do gerador GEN_OSCOD_ID)   OSCLI + OSNCLI
                OSENTD, OSTIME, OSENTG            OSECL = estoque de quem
    vaga <n>    OSTIT<n>    49348 - BASE_CALL. 2027 - LUS CONTABILIDADE
                OSESP<n>    98        OSNESP<n>  SOLIDA FT4
                OSMON<n>    F4        OSALT/OSLAR  510 / 400
                OSLAN<n>    4         quantas CHAPAS, nao quantos arquivos
                OSUNIT<n>   9,00      OSVLU<n>   36,00
                RBCHAPA<n>  1

CUIDADO - ESCREVER AQUI MEXE EM ESTOQUE. O gatilho TR_OS_BEFO da tabela
OS nao e decoracao: quando RBCHAPA<n>=1 ele LANCA MOVIMENTO na tabela
MOV, dando baixa de chapa. Ou seja, abrir OS nao e anotar: e movimentar o
que a empresa tem e o que ela fatura.

    RBCHAPA<n>    = 1  ->  baixa no estoque DO CLIENTE  (ele traz a chapa)
    RBCHAPAPRO<n> = 1  ->  baixa no estoque DA FINART   (chapa propria)

QUANTAS CHAPAS. O preco e por chapa de metal, e um trabalho em
quadricromia gasta quatro. Entao OSLAN = paginas x tintas, que e
exatamente o que a FIA ja mede em cada arte.
"""

import datetime

from .config import (GEREMPRE_CHAPAS, GEREMPRE_CLIENTES, GEREMPRE_DSN,
                     GEREMPRE_FUNCIONARIO, GEREMPRE_RESPONSAVEL,
                     GEREMPRE_SENHA, GEREMPRE_USUARIO)
from .utils import log

VAGAS = 4                      # a OS tem quatro lugares de servico

# Quanto cabe no titulo da vaga. E o tamanho da coluna OSTIT<n> no
# banco, e o Firebird nao corta sozinho: passar disso derruba a
# gravacao inteira com erro de truncamento. O operador escolheu cortar
# no fim, que e o que ja acontece hoje quando alguem digita demais.
LETRAS_NO_TITULO = 50
CLIENTE = "cliente"            # a chapa e do cliente
PROPRIA = "propria"            # a chapa e da Finart


class SemLigacao(Exception):
    """Nao deu para falar com o GEREMPRE."""


def conectar():
    """
    Abre a ligacao com o banco. Levanta SemLigacao se nao der.

    Quem chama fecha. Nunca deixamos conexao pendurada: o Firebird 1.5
    do GEREMPRE e o mesmo que os operadores usam o dia inteiro.
    """
    if not GEREMPRE_DSN:
        raise SemLigacao("GEREMPRE_DSN nao esta configurado")
    try:
        import fdb
    except ImportError:
        raise SemLigacao("falta a biblioteca fdb (pip install fdb)")

    from .config import GEREMPRE_CLIENTE_DLL
    try:
        if GEREMPRE_CLIENTE_DLL:
            fdb.load_api(GEREMPRE_CLIENTE_DLL)
        return fdb.connect(dsn=GEREMPRE_DSN, user=GEREMPRE_USUARIO,
                           password=GEREMPRE_SENHA, charset="ISO8859_1")
    except Exception as e:
        raise SemLigacao(str(e)[:120])


def chapa_do_servico(cliente, larg_mm, alt_mm):
    """
    (codigo_da_chapa, nome, preco, tipo) para este cliente e formato.

    None quando nao ha combinacao cadastrada - e ai o servico vira
    pendencia em vez de OS com preco chutado.
    """
    medida = tuple(sorted((int(round(larg_mm)), int(round(alt_mm))),
                          reverse=True))
    return GEREMPRE_CHAPAS.get((cliente, medida))


def quantas_chapas(paginas_com_tintas):
    """
    Quantas chapas de METAL o trabalho gasta.

    O preco e por chapa, e quadricromia gasta quatro. Recebe uma lista
    com o conjunto de tintas de cada pagina:

        [{'C','M','Y','K'}]            -> 4
        [{'GRAY'}]                     -> 1
        [{'C','M','Y','K'}, {'GRAY'}]  -> 5
    """
    return sum(max(1, len(tintas)) for tintas in paginas_com_tintas)


def _cadastro_do_cliente(cur, codigo):
    """Nome e contato do cliente, como o GEREMPRE os copia para a OS."""
    cur.execute("SELECT CLINOM, CLICON, CLITEL FROM CLI WHERE CLICOD = ?",
                (codigo,))
    linha = cur.fetchone()
    if not linha:
        return None, None, None
    return tuple((c or "").strip() if isinstance(c, str) else c
                 for c in linha)


def _so_letras_e_numeros(texto):
    """'49713 - Lucas Calil' -> '49713LUCASCALIL'. Para comparar titulo."""
    return "".join(c for c in (texto or "").upper() if c.isalnum())


def ja_esta_em_os(cur, titulo):
    """
    O numero da OS em que este servico ja foi lancado, ou None.

    A OS tambem se abre A MAO, e e normal que outro operador tenha
    lancado o servico antes da FIA chegar nele. Faturar duas vezes o
    mesmo servico e pior do que nao faturar.

    Procura nas QUATRO vagas. O titulo no GEREMPRE e o proprio nome do
    arquivo em maiuscula - foi conferido em 330 arquivos de agosto -, mas
    a comparacao ignora espaco, traco e caixa, porque quem digita varia.
    """
    alvo = _so_letras_e_numeros(titulo)
    if not alvo:
        return None

    # O GEREMPRE guarda o titulo em CAIXA ALTA, e o STARTING WITH do
    # Firebird distingue maiuscula de minuscula: procurar por
    # '48915 - Heineken' nao acha '48915 - HEINEKEN'. Custou uma busca em
    # branco antes de aparecer, porque os titulos que comecam com numero
    # casavam por acaso.
    comeco = titulo[:20].upper()
    for vaga in range(1, VAGAS + 1):
        # o STARTING WITH so aproxima; a comparacao exata e feita aqui,
        # ignorando espaco, traco e caixa - quem digita varia
        cur.execute("SELECT OSCOD, OSTIT%d FROM OS "
                    "WHERE UPPER(OSTIT%d) STARTING WITH ?" % (vaga, vaga),
                    (comeco,))
        for numero, achado in cur.fetchall():
            if _so_letras_e_numeros(achado) == alvo:
                return numero
    return None


def _proximo_numero(cur):
    """O proximo numero de OS, do mesmo gerador que o GEREMPRE usa."""
    cur.execute("SELECT GEN_ID(GEN_OSCOD_ID, 1) FROM RDB$DATABASE")
    return cur.fetchone()[0]


def montar_vaga(servico):
    """
    Os campos de UMA vaga, a partir de um servico da FIA.

    servico: {'titulo', 'cliente', 'chapa': (larg, alt), 'chapas': n}
    """
    achado = chapa_do_servico(servico["cliente"], *servico["chapa"])
    if not achado:
        return None
    codigo, nome, preco, tipo = achado
    larg, alt = servico["chapa"]
    quantas = servico["chapas"]
    return {
        "OSTIT": servico["titulo"][:LETRAS_NO_TITULO],
        "OSESP": codigo,
        "OSNESP": nome,
        "OSMON": "F4" if max(larg, alt) <= 560 else "F2",
        "OSALT": int(round(max(larg, alt))),
        "OSLAR": int(round(min(larg, alt))),
        "OSLAN": quantas,
        "OSCOR": 1,
        "OSUNIT": preco,
        "OSVLU": round(preco * quantas, 2),
        "RBCHAPA": 1 if tipo == CLIENTE else 0,
        "RBCHAPAPRO": 1 if tipo == PROPRIA else 0,
    }


def dados_da_os(numero, con=None):
    """
    Tudo que a folha da ORDEM DE SERVICO precisa, lido do banco.

    Le a OS de volta depois de gravada, em vez de reaproveitar o que foi
    montado na memoria: assim a folha impressa mostra o que EXISTE no
    GEREMPRE. Se um campo nao entrou, aparece em branco no papel, e
    alguem ve.
    """
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT * FROM OS WHERE OSCOD = ?", (numero,))
        linha = cur.fetchone()
        if not linha:
            return None
        d = dict(zip([c[0] for c in cur.description], linha))

        def texto(campo):
            v = d.get(campo)
            return v.strip() if isinstance(v, str) else v

        itens = []
        for i in range(1, VAGAS + 1):
            if not d.get("OSESP%d" % i):
                continue
            itens.append({
                "vaga": i,
                "material": texto("OSNESP%d" % i) or "",
                "codigo": d.get("OSESP%d" % i),
                "alt": d.get("OSALT%d" % i),
                "lar": d.get("OSLAR%d" % i),
                "montagem": texto("OSMON%d" % i) or "",
                "frente": d.get("OSCOR%d" % i) or 0,
                "verso": d.get("OSCOR%d%d" % (i, i)) or 0,
                "quantas": d.get("OSLAN%d" % i) or 0,
                "titulo": texto("OSTIT%d" % i) or "",
                "obs": texto("OSOBS%d" % i) or "",
                "unitario": d.get("OSUNIT%d" % i),
                "total": d.get("OSVLU%d" % i),
            })

        endereco = " - ".join(p for p in (
            texto("OSEND_END"), texto("OSEND_BAI"), texto("OSEND_CID")) if p)
        return {
            "numero": d["OSCOD"],
            "entrada": d.get("OSENTD"),
            "hora": d.get("OSTIME"),
            "entrega": d.get("OSENTG"),
            "cliente": texto("OSNCLI") or "",
            "contato": texto("OSCON") or "",
            "telefone": texto("OSTEL") or "",
            "celular": texto("OSCEL") or "",
            "endereco": endereco,
            "responsavel": texto("OSRESP") or "",
            "total_geral": d.get("OSVTOT"),
            "itens": itens,
        }
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def _vagas_ocupadas(cur, numero):
    """Quais vagas da OS ja tem servico. [1, 2] quer dizer duas cheias."""
    cur.execute("SELECT OSESP1, OSESP2, OSESP3, OSESP4 FROM OS "
                "WHERE OSCOD = ?", (numero,))
    linha = cur.fetchone()
    if not linha:
        return None
    return [i for i, esp in enumerate(linha, start=1) if esp]


def os_com_vaga_livre(cur, cliente, quando=None):
    """
    A OS de hoje deste cliente que a FIA abriu e ainda tem vaga, ou None.

    Os operadores enchem as quatro vagas, e agora a FIA faz igual - so
    que sem esperar: abre na primeira arte e vai completando conforme as
    outras fecham. Assim cada arquivo ja sai com o numero da OS impresso
    no verso da prova, que e o que o operador precisa na mao.

    SO OS QUE A FIA ABRIU. Completar uma OS envolve UPDATE, e o gatilho
    TR_OS_BEFO, no UPDATE, apaga TODOS os movimentos da OS e refaz os
    quatro do zero. Numa OS da FIA isso e seguro, porque ela nasce com
    as quatro vagas zeradas. Numa OS aberta a mao pelo programa Delphi,
    uma vaga vazia pode estar NULA - e conta com nulo da nulo, que
    apagaria o saldo da chapa. Alem disso, mexer na OS de outra pessoa
    nao e nosso lugar.
    """
    codigo = GEREMPRE_CLIENTES.get(cliente)
    if not codigo:
        return None
    hoje = (quando or datetime.datetime.now()).date()
    # OSSIT 2 e cancelada, OSTIPO 4 e refacao: nas duas o gatilho toma
    # outro caminho, que devolve estoque. Nao se completa uma dessas.
    cur.execute("SELECT OSCOD FROM OS WHERE OSCLI = ? AND OSENTD = ? "
                "AND OSUSR_ALT = ? AND OSSIT = 1 AND OSTIPO = 0 "
                "AND (OSESP4 = 0 OR OSESP4 IS NULL) "
                "ORDER BY OSCOD DESC",
                (codigo, hoje, GEREMPRE_FUNCIONARIO))
    for (numero,) in cur.fetchall():
        ocupadas = _vagas_ocupadas(cur, numero)
        if ocupadas is not None and len(ocupadas) < VAGAS:
            return numero
    return None


def completar_os(numero, servico, con=None):
    """
    Poe o servico na proxima vaga livre de uma OS que ja existe.

    Devolve o numero da vaga usada.

    O UPDATE dispara o TR_OS_BEFO, que APAGA todos os movimentos desta
    OS e os refaz a partir das quatro vagas. Por isso completar nao
    cobra o item 1 duas vezes: ele e apagado e recriado igual, e o novo
    item entra junto. Foi lido na fonte do gatilho, nao suposto.
    """
    vaga = montar_vaga(servico)
    if vaga is None:
        raise ValueError("nao sei que chapa usar para %s %.0fx%.0f"
                         % (servico["cliente"], servico["chapa"][0],
                            servico["chapa"][1]))
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        ocupadas = _vagas_ocupadas(cur, numero)
        if ocupadas is None:
            raise ValueError("a OS %s nao existe" % numero)
        livres = [i for i in range(1, VAGAS + 1) if i not in ocupadas]
        if not livres:
            raise ValueError("a OS %s ja tem as quatro vagas cheias"
                             % numero)
        n = livres[0]

        campos = {"%s%d" % (chave, n): valor for chave, valor in vaga.items()}
        # OSCOR<n><n> - as cores do VERSO. Zero, e nunca nulo: o gatilho
        # faz oslan * (oscor + oscor<n><n>), e nulo apaga o saldo.
        campos["OSCOR%d%d" % (n, n)] = 0
        nomes = sorted(campos)
        cur.execute("UPDATE OS SET %s WHERE OSCOD = ?"
                    % ", ".join("%s = ?" % c for c in nomes),
                    [campos[c] for c in nomes] + [numero])
        con.commit()
        log("GEREMPRE: completei a OS %s na vaga %d com '%s'"
            % (numero, n, servico["titulo"][:40]))
        return n
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def os_do_servico(servico, con=None, quando=None):
    """
    A OS deste servico: acha, completa ou abre. Devolve (numero, vaga).

    Tres caminhos, nesta ordem:

      1. o servico JA ESTA numa OS - outro operador lancou a mao, ou a
         propria FIA lancou antes e o arquivo voltou. Devolve aquela OS
         e nao cobra de novo. Faturar duas vezes e pior que nao faturar;
      2. ha uma OS de hoje, deste cliente, aberta pela FIA e com vaga -
         entra nela;
      3. nao ha - abre uma nova, com o servico na primeira vaga.

    O caminho 1 e o que segura a repeticao quando um arquivo passa duas
    vezes pelo programa: a prova sai com o mesmo numero, e o estoque nao
    anda de novo.
    """
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        numero = ja_esta_em_os(cur, servico["titulo"])
        if numero:
            ocupadas = _vagas_ocupadas(cur, numero) or []
            return numero, (ocupadas[-1] if ocupadas else 1)

        numero = os_com_vaga_livre(cur, servico["cliente"], quando)
        if numero:
            return numero, completar_os(numero, servico, con=con)

        numero = abrir_os([servico], quando=quando, con=con)
        return numero, 1
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def abrir_os(servicos, quando=None, con=None):
    """
    Abre UMA OS com ate quatro servicos. Devolve o numero da OS.

    Todos os servicos tem de ser do mesmo cliente - a OS e por cliente.
    Grava tudo numa transacao so: ou entra a OS inteira, ou nao entra
    nada. Meia OS lancaria estoque pela metade.
    """
    if not servicos:
        raise ValueError("nenhum servico para lancar")
    if len(servicos) > VAGAS:
        raise ValueError("a OS tem %d vagas, vieram %d servicos"
                         % (VAGAS, len(servicos)))
    clientes = {s["cliente"] for s in servicos}
    if len(clientes) > 1:
        raise ValueError("uma OS e de um cliente so, vieram: %s"
                         % ", ".join(sorted(clientes)))

    cliente = servicos[0]["cliente"]
    codigo = GEREMPRE_CLIENTES.get(cliente)
    if not codigo:
        raise ValueError("cliente %s nao esta ligado a nenhum codigo do "
                         "GEREMPRE" % cliente)

    vagas = []
    for servico in servicos:
        vaga = montar_vaga(servico)
        if vaga is None:
            raise ValueError("nao sei que chapa usar para %s %.0fx%.0f"
                             % (cliente, servico["chapa"][0],
                                servico["chapa"][1]))
        vagas.append(vaga)

    quando = quando or datetime.datetime.now()
    proprio = con is None
    con = con or conectar()
    try:
        cur = con.cursor()
        numero = _proximo_numero(cur)
        nome, contato, telefone = _cadastro_do_cliente(cur, codigo)

        campos = {
            "OSCOD": numero,
            "OSENTD": quando.date(),
            "OSTIME": quando.time().replace(microsecond=0),
            "OSENTG": quando.date(),
            "OSCLI": codigo,
            "OSNCLI": nome,
            "OSCON": contato,
            "OSTEL": telefone,
            # de que estoque sai a chapa do cliente
            "OSECL": codigo,
            "OSNECLI": nome,
            # O banco exige sete campos: OSCOD, OSSIT, OSTIPO, OSCLI,
            # OSCVEN, OSCOPER e OSCCONF. Os tres ultimos sao vendedor,
            # operador e conferente, e nas 19.122 OS que existem eles
            # estao em ZERO - ninguem preenche. Deixar de fora derruba a
            # gravacao inteira com 'validation error'.
            "OSSIT": 1,          # 19.078 das 19.122 OS usam 1
            "OSTIPO": 0,
            "OSCVEN": 0,
            "OSCOPER": 0,
            "OSCCONF": 0,
            "OSORD": 1,
            "OSRESP": GEREMPRE_RESPONSAVEL,
            # quem abriu: o codigo vai no movimento de estoque pelo
            # gatilho (MOVFUN), e o nome fica visivel na propria OS
            "OSUSR_ALT": GEREMPRE_FUNCIONARIO,
        }
        # ZERO EM TODAS AS QUATRO VAGAS, ANTES DE PREENCHER. Em SQL,
        # qualquer conta com nulo da nulo, e o gatilho faz duas contas
        # que passam por aqui. As duas foram vistas quebrando no banco de
        # teste, e as duas estragam em silencio:
        #
        #   total = osvlu1 + osvlu2 + osvlu3 + osvlu4
        #       numa OS de um servico so, as tres vagas vazias eram nulas
        #       e o TOTAL DA OS saia nulo.
        #
        #   movqtd = oslan<n> * (oscor<n> + oscor<n><n>)
        #       oscor<n><n> e o numero de cores do VERSO. Sem preencher,
        #       a quantidade do movimento saia nula - e o gatilho da MOV
        #       faz 'chaqtd = chaqtd + movqtd', entao o ESTOQUE DA CHAPA
        #       virava nulo. Aconteceu com as chapas 98 e 103 na copia.
        for i in range(1, VAGAS + 1):
            campos["OSVLU%d" % i] = 0
            campos["OSLAN%d" % i] = 0
            campos["OSCOR%d" % i] = 0
            campos["OSCOR%d%d" % (i, i)] = 0      # cores do verso
            campos["OSESP%d" % i] = 0
            campos["RBCHAPA%d" % i] = 0
            campos["RBCHAPAPRO%d" % i] = 0

        for i, vaga in enumerate(vagas, start=1):
            for chave, valor in vaga.items():
                campos["%s%d" % (chave, i)] = valor

        nomes = sorted(campos)
        cur.execute("INSERT INTO OS (%s) VALUES (%s)"
                    % (", ".join(nomes), ", ".join(["?"] * len(nomes))),
                    [campos[n] for n in nomes])
        con.commit()
        log("GEREMPRE: abri a OS %s para %s com %d servico(s)"
            % (numero, cliente, len(vagas)))
        return numero
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass
