# -*- coding: utf-8 -*-
r"""
O ESTOQUE DE CHAPAS DO CLIENTE, numa folha, todo dia.

    python -m finart_ctp.estoque              a SOLIDA, e abre na tela
    python -m finart_ctp.estoque VIVA         outro cliente
    python -m finart_ctp.estoque --nao-abrir  so grava

PARA QUE SERVE. A chapa e do cliente: ele manda um lote, a Finart grava
e o saldo cai. Quando o saldo acaba, a gravacao para - e quem descobre
e o operador, na hora em que o servico ja esta na fila. O GEREMPRE
guarda o numero certo, mas mostra um saldo por vez, numa tela, sem
dizer quanto tempo ele ainda dura.

Esta folha responde a pergunta que importa: **quantos dias ainda tem**.

COMO O ARQUIVO ANDA DURANTE O DIA. Um por dia, sempre com o mesmo nome,
reescrito por cima. A FIA olha uma SENTINELA a cada volta do laco - uma
consulta so, 0,14 s - e so redesenha quando o movimento do cliente
mudou. Assim a folha acompanha tambem o que os operadores lancam no
Delphi, que e a maior parte: em 14/09/2026, das cinco OS da SOLIDA,
quatro foram abertas a mao.

    sentinela   COUNT(*), MAX(MOVCOD), SUM(MOVQTD) do dono
                muda em qualquer insercao, remocao ou correcao - e o
                TR_OS_BEFO apaga e refaz TODO o movimento de uma OS a
                cada gravacao, entao contar so o MAX deixaria passar
                uma OS que encolheu.

NAO EXISTE 'ESTOQUE MINIMO' NESTE BANCO. O campo CHAMIN parece ser isso
pelo nome e NAO E: ele guarda o PRECO. Conferido em 14/09/2026 - chapa
98 tem CHAMIN 9 e todas as 843 OS dela cobram 9,00; a 103 tem 13 e as
157 cobram 13,00; FIALHO 10 e 15, VIVA 8,50. Sao os mesmos numeros da
tabela GEREMPRE_CHAPAS. Ler CHAMIN como minimo faria a folha dizer
'175 de minimo 9, tudo bem' na vespera de acabar.

Por isso a folga e medida em DIAS, pelo consumo de verdade: a media do
que saiu nos ultimos dias COM MOVIMENTO (dia util, nao dia de
calendario - contar sabado e domingo esticaria a conta em dois setimos).

SO LE. Nenhuma linha daqui escreve no GEREMPRE.
"""

import datetime
import os
import sys

from .config import GEREMPRE_CLIENTES, PASTA_CONTROLE
from .os_impressa import A4_MM, DPI, LOGO, _fonte
from .utils import agora_util, log

CLIENTE_PADRAO = "SOLIDA"

# Quantos dias COM MOVIMENTO entram na media de consumo. Vinte cobrem
# cerca de um mes de trabalho e ainda acompanham a subida de servico -
# a SOLIDA saiu de 25 por dia em agosto para 40 em setembro.
DIAS_DA_MEDIA = 20

# Quantos dias de folga acendem o alerta. Tres dias e o tempo que o
# cliente leva para mandar mais - decidido olhando as entradas: elas
# chegam em lotes de 50, 100 e 200, a cada cinco a dez dias.
POUCO_DIA = 3.0

ARQUIVO = "ESTOQUE %s.pdf"      # um por cliente, reescrito por cima

MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
SEMANA = ("segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
          "sexta-feira", "sabado", "domingo")


def _n(v):
    """Decimal do Firebird -> numero de Python. Nulo vira zero."""
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _texto(v):
    return (v or "").strip()


# ----------------------------------------------------------------------
# O QUE SE LE DO BANCO
# ----------------------------------------------------------------------

def sentinela(dono, con):
    """
    A impressao digital do movimento deste cliente, numa consulta so.

    Muda a qualquer insercao, remocao ou correcao. E o que permite
    olhar o estoque a cada volta do laco sem pesar: 0,14 s contra 0,37 s
    da folha inteira.
    """
    cur = con.cursor()
    cur.execute("SELECT COUNT(*), MAX(MOVCOD), SUM(MOVQTD) FROM MOV "
                "WHERE MOVCLI = ?", (dono,))
    linha = cur.fetchone() or (0, 0, 0)
    return (int(_n(linha[0])), int(_n(linha[1])), _n(linha[2]))


def chapas_vivas(dono, con):
    """
    As chapas ATIVAS do cliente: [(cod, nome, medida, saldo, preco)].

    CHAINA = 1 e chapa desativada no cadastro. A SOLIDA tem oito
    cadastradas e so duas em uso; as seis paradas carregam saldo antigo
    (a 25 tem 8.662) que nao existe em prateleira nenhuma. Somar aquilo
    daria um estoque de mentira.
    """
    cur = con.cursor()
    cur.execute("SELECT CHACOD, CHANOM, CHAALT, CHALAR, CHAQTD, CHAMIN "
                "FROM CHA WHERE CHACLI = ? AND CHAINA = 0 "
                "ORDER BY CHAQTD DESC", (dono,))
    vivas = []
    for cod, nome, alt, lar, qtd, preco in cur.fetchall():
        vivas.append({"cod": cod, "nome": _texto(nome),
                      "medida": (int(_n(alt)), int(_n(lar))),
                      "saldo": _n(qtd), "preco": _n(preco)})
    return vivas


def paradas(dono, con):
    """(quantas, saldo_somado) das chapas desativadas que ainda tem saldo."""
    cur = con.cursor()
    cur.execute("SELECT COUNT(*), SUM(CHAQTD) FROM CHA "
                "WHERE CHACLI = ? AND CHAINA = 1 AND CHAQTD > 0", (dono,))
    linha = cur.fetchone() or (0, 0)
    return int(_n(linha[0])), _n(linha[1])


def por_dia(dono, con, desde):
    """
    {codigo_da_chapa: [(dia, saiu, entrou)]} do periodo, em ordem.

    Usa MOVSDA e MOVENT, e nao o sinal de MOVQTD: os dois campos ja
    separam entrada de saida, e um dia com as duas coisas (14/09 teve)
    ficaria irreconhecivel somando o liquido.
    """
    cur = con.cursor()
    cur.execute("SELECT MOVCHA, MOVDIA, SUM(MOVSDA), SUM(MOVENT) FROM MOV "
                "WHERE MOVCLI = ? AND MOVDIA >= ? "
                "GROUP BY MOVCHA, MOVDIA ORDER BY MOVCHA, MOVDIA",
                (dono, desde))
    dias = {}
    for cha, dia, saiu, entrou in cur.fetchall():
        dias.setdefault(cha, []).append((dia, _n(saiu), _n(entrou)))
    return dias


def do_dia(dono, con, dia):
    """
    O movimento de um dia: [(hora, os, quem, chapa, entrou, saiu, obs)].

    A hora nao esta na MOV - MOVDIA e so data. Ela vem do OSTIME da OS
    que gerou o movimento; lancamento a mao (entrada de chapa nova) nao
    tem OS, e fica sem hora.
    """
    cur = con.cursor()
    cur.execute("SELECT MOVCHA, MOVNCH, MOVENT, MOVSDA, MOVNOS, MOVNFU, "
                "MOVOBS FROM MOV WHERE MOVCLI = ? AND MOVDIA = ? "
                "ORDER BY MOVCOD", (dono, dia))
    linhas = cur.fetchall()

    horas = {}
    numeros = sorted({int(_n(l[4])) for l in linhas if l[4]})
    for numero in numeros:
        cur.execute("SELECT OSTIME FROM OS WHERE OSCOD = ?", (numero,))
        achou = cur.fetchone()
        if achou and achou[0]:
            horas[numero] = achou[0]

    feito = []
    for cha, nome, entrou, saiu, numero, quem, obs in linhas:
        numero = int(_n(numero)) or None
        feito.append({"chapa": cha, "nome": _texto(nome),
                      "entrou": _n(entrou), "saiu": _n(saiu),
                      "os": numero, "quem": _texto(quem),
                      "hora": horas.get(numero), "obs": _texto(obs)})
    return feito


def razao(dono, con):
    """
    {codigo: (saldo_da_CHA, soma_da_MOV)} - a conferencia de sempre.

    CHA.CHAQTD tem de ser a soma dos MOV daquela chapa e daquele dono.
    Em 10/09/2026 as 96 chapas do banco batiam, todas. Quando parar de
    bater, o numero desta folha deixou de valer, e quem le precisa
    saber disso ANTES de decidir comprar chapa.
    """
    cur = con.cursor()
    cur.execute("SELECT CHACOD, CHAQTD FROM CHA WHERE CHACLI = ?", (dono,))
    saldos = {c: _n(q) for c, q in cur.fetchall()}
    cur.execute("SELECT MOVCHA, SUM(MOVQTD) FROM MOV WHERE MOVCLI = ? "
                "GROUP BY MOVCHA", (dono,))
    somas = {c: _n(s) for c, s in cur.fetchall()}
    return {c: (saldos[c], somas.get(c, 0.0)) for c in saldos}


# ----------------------------------------------------------------------
# A CONTA DA FOLGA
# ----------------------------------------------------------------------

def media_por_dia_util(historico):
    """
    Quanto sai por dia de trabalho, pelos ultimos DIAS_DA_MEDIA dias
    que tiveram movimento.

    Dia sem movimento nao entra: feriado e domingo puxariam a media
    para baixo e a folga para cima, que e o erro que custa caro.
    """
    com_saida = [saiu for _, saiu, _ in historico if saiu > 0]
    if not com_saida:
        return 0.0
    ultimos = com_saida[-DIAS_DA_MEDIA:]
    return sum(ultimos) / float(len(ultimos))


def dias_de_folga(saldo, media):
    """Quantos dias uteis o saldo ainda cobre. None quando nao ha consumo."""
    if media <= 0:
        return None
    return saldo / media


def data_do_fim(dias, de=None):
    """
    Em que dia o saldo acaba, pulando sabado e domingo.

    Contar em dias de calendario adiantaria o susto em dois setimos - e
    um estoque que 'dura cinco dias' numa sexta-feira dura ate a sexta
    seguinte, nao ate a quarta.
    """
    if dias is None:
        return None
    de = de or agora_util().date()
    inteiros = int(dias)
    quando = de
    andados = 0
    while andados < inteiros:
        quando += datetime.timedelta(days=1)
        if quando.weekday() < 5:
            andados += 1
    return quando


# ----------------------------------------------------------------------
# O LEVANTAMENTO
# ----------------------------------------------------------------------

def levantar(cliente=CLIENTE_PADRAO, con=None, dia=None):
    """
    Tudo o que a folha mostra, lido do banco numa ligacao so.

    Devolve None quando o cliente nao esta no cadastro da FIA.
    """
    from .gerempre import conectar

    dono = GEREMPRE_CLIENTES.get(cliente)
    if dono is None:
        return None

    proprio = con is None
    con = con or conectar()
    try:
        dia = dia or agora_util().date()
        desde = dia - datetime.timedelta(days=90)

        vivas = chapas_vivas(dono, con)
        historico = por_dia(dono, con, desde)
        conferencia = razao(dono, con)
        movimento = do_dia(dono, con, dia)
        quantas_paradas, saldo_parado = paradas(dono, con)

        for chapa in vivas:
            passado = historico.get(chapa["cod"], [])
            chapa["historico"] = passado
            chapa["media"] = media_por_dia_util(passado)
            chapa["folga"] = dias_de_folga(chapa["saldo"], chapa["media"])
            chapa["acaba"] = data_do_fim(chapa["folga"], dia)
            chapa["entrou_hoje"] = sum(m["entrou"] for m in movimento
                                       if m["chapa"] == chapa["cod"])
            chapa["saiu_hoje"] = sum(m["saiu"] for m in movimento
                                     if m["chapa"] == chapa["cod"])
            cha, mov = conferencia.get(chapa["cod"], (0.0, 0.0))
            chapa["razao_bate"] = abs(cha - mov) < 0.001

        return {"cliente": cliente, "dono": dono, "dia": dia,
                "chapas": vivas, "movimento": movimento,
                "paradas": (quantas_paradas, saldo_parado),
                "quando": agora_util(),
                "sentinela": sentinela(dono, con)}
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


# ----------------------------------------------------------------------
# A FOLHA
# ----------------------------------------------------------------------

MARGEM = 14.0
CINZA = (120, 120, 120)
PRETO = (20, 20, 20)
ALERTA = (190, 30, 30)
BARRA = (160, 175, 190)
BARRA_HOJE = (70, 100, 140)
RISCO = (200, 200, 200)


def _dia_por_extenso(d):
    return "%s, %d de %s de %d" % (SEMANA[d.weekday()], d.day,
                                   MESES[d.month - 1], d.year)


def _dinheiro(v):
    """9.0 -> 'R$ 9,00'. Virgula, como o resto dos papeis da casa."""
    return ("R$ %.2f" % v).replace(".", ",")


def _folga_em_texto(chapa):
    """'dura 5 dias uteis - ate 18/09', ou por que nao da para dizer."""
    if chapa["folga"] is None:
        return "sem consumo para calcular"
    dias = int(chapa["folga"])
    if dias < 1:
        return "ACABA HOJE"
    return "dura %d dia%s de trabalho - ate %s" % (
        dias, "" if dias == 1 else "s", chapa["acaba"].strftime("%d/%m"))


def folha(dados, dpi=DPI):
    """A folha A4 em pe do estoque. Devolve uma imagem do Pillow."""
    from PIL import Image, ImageDraw

    def px(mm):
        return int(round(mm / 25.4 * dpi))

    pagina = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")
    d = ImageDraw.Draw(pagina)

    g_titulo = _fonte(px(6.0), True)
    g_cliente = _fonte(px(9.0), True)
    g_secao = _fonte(px(3.8), True)
    g_nome = _fonte(px(4.2), True)
    g_numero = _fonte(px(13.0), True)
    g_texto = _fonte(px(3.2))
    g_miudo = _fonte(px(2.6))

    dire = A4_MM[0] - MARGEM

    # --- cabecalho ------------------------------------------------------
    if os.path.exists(LOGO):
        try:
            logo = Image.open(LOGO).convert("RGBA")
            larg = px(40.0)
            alt = int(logo.height * larg / float(logo.width))
            pagina.paste(logo.resize((larg, alt), Image.LANCZOS),
                         (px(MARGEM), px(13.0)), logo.resize((larg, alt),
                                                             Image.LANCZOS))
        except OSError:
            pass

    d.text((px(dire), px(12.0)), "ESTOQUE DE CHAPAS", font=g_titulo,
           fill=CINZA, anchor="ra")
    d.text((px(dire), px(18.0)), dados["cliente"], font=g_cliente,
           fill=PRETO, anchor="ra")
    d.text((px(dire), px(31.0)), _dia_por_extenso(dados["dia"]),
           font=g_texto, fill=CINZA, anchor="ra")
    d.text((px(dire), px(35.5)),
           "atualizado as %s" % dados["quando"].strftime("%H:%M"),
           font=g_texto, fill=CINZA, anchor="ra")
    d.line([(px(MARGEM), px(42.0)), (px(dire), px(42.0))], fill=RISCO,
           width=max(1, px(0.3)))

    # --- os cartoes de cada chapa ---------------------------------------
    y = 50.0
    d.text((px(MARGEM), px(y)), "O QUE TEM AGORA", font=g_secao, fill=PRETO)
    y += 7.0

    chapas = dados["chapas"]
    if not chapas:
        d.text((px(MARGEM), px(y)), "nenhuma chapa ativa no cadastro",
               font=g_texto, fill=CINZA)
        y += 10.0

    largura = (dire - MARGEM - 6.0) / 2.0 if len(chapas) > 1 else \
        (dire - MARGEM)
    alto = 52.0
    for i, chapa in enumerate(chapas[:4]):
        coluna = i % 2
        linha = i // 2
        x = MARGEM + coluna * (largura + 6.0)
        topo = y + linha * (alto + 6.0)
        pouco = chapa["folga"] is not None and chapa["folga"] <= POUCO_DIA
        d.rectangle([px(x), px(topo), px(x + largura), px(topo + alto)],
                    outline=(ALERTA if pouco else RISCO),
                    width=max(1, px(0.4 if pouco else 0.25)))

        d.text((px(x + 5.0), px(topo + 4.5)), chapa["nome"][:26],
               font=g_nome, fill=PRETO)
        d.text((px(x + 5.0), px(topo + 10.0)),
               "%d x %d mm   %s a gravacao"
               % (chapa["medida"][0], chapa["medida"][1],
                  _dinheiro(chapa["preco"])),
               font=g_miudo, fill=CINZA)

        d.text((px(x + 5.0), px(topo + 16.0)), "%.0f" % chapa["saldo"],
               font=g_numero, fill=(ALERTA if pouco else PRETO))
        d.text((px(x + 5.0), px(topo + 32.0)), "chapas em estoque",
               font=g_miudo, fill=CINZA)

        d.text((px(x + largura - 5.0), px(topo + 17.0)),
               "hoje  +%.0f  -%.0f"
               % (chapa["entrou_hoje"], chapa["saiu_hoje"]),
               font=g_texto, fill=PRETO, anchor="ra")
        d.text((px(x + largura - 5.0), px(topo + 22.0)),
               "sai ~%.0f por dia util" % chapa["media"],
               font=g_texto, fill=CINZA, anchor="ra")
        d.text((px(x + largura - 5.0), px(topo + 27.0)),
               _folga_em_texto(chapa), font=g_texto,
               fill=(ALERTA if pouco else CINZA), anchor="ra")

        # a barrinha dos ultimos dias, dentro do proprio cartao
        recentes = [h for h in chapa["historico"] if h[1] > 0][-20:]
        if recentes:
            maior = max(h[1] for h in recentes)
            base = topo + alto - 6.0
            altura = 12.0
            passo = (largura - 10.0) / float(len(recentes))
            for j, (quando, saiu, _e) in enumerate(recentes):
                h = altura * (saiu / maior) if maior else 0
                bx = x + 5.0 + j * passo
                cor = BARRA_HOJE if quando == dados["dia"] else BARRA
                d.rectangle([px(bx), px(base - h),
                             px(bx + passo * 0.68), px(base)], fill=cor)
            d.text((px(x + 5.0), px(base + 0.8)),
                   "o que saiu nos ultimos %d dias de trabalho"
                   % len(recentes), font=g_miudo, fill=CINZA)

    y += ((len(chapas[:4]) + 1) // 2) * (alto + 6.0) + 6.0

    # --- o movimento do dia ---------------------------------------------
    d.text((px(MARGEM), px(y)), "O QUE ANDOU HOJE", font=g_secao, fill=PRETO)
    y += 6.5

    movimento = dados["movimento"]
    if not movimento:
        d.text((px(MARGEM), px(y)), "nada ainda", font=g_texto, fill=CINZA)
        y += 6.0
    for m in movimento[:22]:
        hora = m["hora"].strftime("%H:%M") if m["hora"] else "  -  "
        onde = "OS %s" % m["os"] if m["os"] else "entrada"
        sinal = "+%.0f" % m["entrou"] if m["entrou"] else "-%.0f" % m["saiu"]
        d.text((px(MARGEM), px(y)), hora, font=g_texto, fill=CINZA)
        d.text((px(MARGEM + 14.0), px(y)), onde, font=g_texto, fill=PRETO)
        d.text((px(MARGEM + 36.0), px(y)), m["quem"][:22], font=g_texto,
               fill=CINZA)
        d.text((px(MARGEM + 84.0), px(y)), m["nome"][:26], font=g_texto,
               fill=CINZA)
        d.text((px(MARGEM + 140.0), px(y)), sinal, font=g_texto,
               fill=(PRETO if m["saiu"] else (30, 110, 60)), anchor="ra")
        y += 5.0
    if len(movimento) > 22:
        d.text((px(MARGEM), px(y)), "e mais %d lancamento(s)"
               % (len(movimento) - 22), font=g_miudo, fill=CINZA)
        y += 5.0

    entrou = sum(m["entrou"] for m in movimento)
    saiu = sum(m["saiu"] for m in movimento)
    y += 1.0
    d.line([(px(MARGEM), px(y)), (px(dire), px(y))], fill=RISCO,
           width=max(1, px(0.25)))
    y += 2.0
    d.text((px(MARGEM), px(y)),
           "no dia:  entraram %.0f   sairam %.0f" % (entrou, saiu),
           font=g_texto, fill=PRETO)

    # --- rodape ----------------------------------------------------------
    base = A4_MM[1] - 16.0
    d.line([(px(MARGEM), px(base - 4.0)), (px(dire), px(base - 4.0))],
           fill=RISCO, width=max(1, px(0.25)))

    torto = [c for c in dados["chapas"] if not c["razao_bate"]]
    if torto:
        d.text((px(MARGEM), px(base)),
               "ATENCAO: o saldo de %s NAO bate com a soma dos movimentos. "
               "O numero acima nao vale." % ", ".join(c["nome"] for c in torto),
               font=g_texto, fill=ALERTA)
    else:
        d.text((px(MARGEM), px(base)),
               "o saldo confere com a soma dos movimentos, chapa por chapa",
               font=g_miudo, fill=CINZA)

    quantas, parado = dados["paradas"]
    if quantas:
        d.text((px(MARGEM), px(base + 4.0)),
               "ha %d chapa(s) desativada(s) no cadastro carregando %.0f de "
               "saldo antigo - nao entram nesta conta" % (quantas, parado),
               font=g_miudo, fill=CINZA)

    d.text((px(dire), px(base + 8.0)),
           "FINART (FIA) - lido do GEREMPRE, sem escrever nada",
           font=g_miudo, fill=CINZA, anchor="ra")
    return pagina


# ----------------------------------------------------------------------
# GRAVAR, ABRIR E ACOMPANHAR
# ----------------------------------------------------------------------

def caminho_da_folha(cliente=CLIENTE_PADRAO, pasta=None):
    return os.path.join(pasta or PASTA_CONTROLE, ARQUIVO % cliente)


def gravar(dados, pasta=None, dpi=DPI):
    """
    Grava a folha por cima da de ontem e devolve o caminho, ou None.

    UM arquivo por cliente, e nao um por dia: quem acompanha estoque
    quer o numero de agora, e uma pasta com trinta PDFs por mes seria
    mais um lugar onde procurar. O passado esta todo no GEREMPRE.
    """
    caminho = caminho_da_folha(dados["cliente"], pasta)
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        # grava ao lado e troca: se a folha estiver aberta na tela de
        # alguem, escrever direto por cima falharia no meio e deixaria
        # um PDF quebrado.
        meio = caminho + ".tmp"
        folha(dados, dpi=dpi).save(meio, "PDF", resolution=dpi)
        os.replace(meio, caminho)
        return caminho
    except (OSError, ValueError) as e:
        log("Nao consegui gravar a folha de estoque: %s" % e, alerta=True)
        return None


def abrir(caminho):
    """Poe a folha na tela, com o leitor de PDF do Windows."""
    if not caminho:
        return False
    try:
        os.startfile(caminho)       # so existe no Windows, e e onde ela roda
        return True
    except (OSError, AttributeError) as e:
        log("Nao consegui abrir a folha de estoque: %s" % e)
        return False


_ULTIMA = {}                        # cliente -> sentinela ja desenhada


def esquecer():
    """Zera a memoria da sentinela. Para os testes e para o arranque."""
    _ULTIMA.clear()


def acompanhar(cliente=CLIENTE_PADRAO, con=None, pasta=None):
    """
    Redesenha a folha SE o movimento do cliente mudou. Devolve o
    caminho quando redesenhou, e None quando nao havia o que fazer.

    E isto que a FIA chama a cada volta do laco. O custo normal e uma
    consulta - 0,14 s - e nao a folha inteira, que leva 0,37 s.
    """
    from .gerempre import conectar, SemLigacao

    dono = GEREMPRE_CLIENTES.get(cliente)
    if dono is None:
        return None

    proprio = con is None
    try:
        con = con or conectar()
    except SemLigacao:
        return None                 # sem banco nao se inventa estoque
    try:
        agora = sentinela(dono, con)
        primeira = cliente not in _ULTIMA
        if not primeira and agora == _ULTIMA[cliente]:
            return None
        dados = levantar(cliente, con=con)
        if not dados:
            return None
        _ULTIMA[cliente] = dados["sentinela"]
        caminho = gravar(dados, pasta=pasta)
        if caminho and not primeira:
            log("Estoque da %s: o movimento mudou, refiz a folha" % cliente)
        return caminho
    finally:
        if proprio:
            try:
                con.close()
            except Exception:
                pass


def main():
    argumentos = [a for a in sys.argv[1:] if not a.startswith("-")]
    cliente = (argumentos[0].upper() if argumentos else CLIENTE_PADRAO)
    if cliente not in GEREMPRE_CLIENTES:
        raise SystemExit("nao conheco o cliente %r. Conheco: %s"
                         % (cliente, ", ".join(sorted(GEREMPRE_CLIENTES))))

    dados = levantar(cliente)
    if not dados:
        raise SystemExit("nao consegui levantar o estoque da %s" % cliente)

    print("ESTOQUE DA %s em %s" % (cliente, dados["dia"].strftime("%d/%m/%Y")))
    for chapa in dados["chapas"]:
        print("   %-26s %6.0f chapas   sai ~%.0f/dia   %s"
              % (chapa["nome"], chapa["saldo"], chapa["media"],
                 _folga_em_texto(chapa)))
    caminho = gravar(dados)
    print()
    print("folha: %s" % caminho)
    if "--nao-abrir" not in sys.argv:
        abrir(caminho)


if __name__ == "__main__":
    main()
