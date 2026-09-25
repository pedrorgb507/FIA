# -*- coding: utf-8 -*-
r"""
Falar com a FIA. A equipe pergunta, ela olha o que sabe e responde.

POR QUE ISTO EXISTE. Pedido do operador em 25/09/2026: "uma interface
na qual eu consigo falar com a FIA, e que ela responda, tenha voz para
falar". Mais gente da empresa vai usar, e ele quis que ela fosse "mais
conversada" - nao o tom seco do log.

Hoje, para saber o que a FIA fez, alguem abre o _log_ctp.txt e le linha
de maquina, ou pergunta para quem sabe ler. A pergunta que se faz de
verdade e "o 50190 saiu?", "por que deu pendencia?", "o vigia esta de
pe?" - e a resposta ja esta toda em disco. Falta quem a junte.

ELA SO LE. Nenhuma ferramenta daqui escreve: nao abre OS, nao grava
chapa, nao apaga, nao marca nada como feito. Nao e timidez - e que uma
frase ouvida errado pelo microfone nao pode virar baixa de estoque, e o
banco da Finart nao tem restauracao (CLAUDE.md, regra de 21/09/2026).
Ha teste que le esta fonte e reprova se aparecer caminho de escrita.

DOIS CEREBROS, e hoje so um esta ligado.

  - RESPOSTAS PRONTAS, sem IA. E o que roda. O operador perguntou "tem
    alguma opcao que nao preciso pagar?" e escolheu esta: entende as
    perguntas de todo dia (o que saiu, pendencia, vigia, um numero de
    servico, a fila de OS) e monta a frase com o que esta escrito nos
    arquivos. Custa zero, responde na hora e NAO TEM COMO INVENTAR - so
    repete o que o log diz. O preco e entender so o que foi ensinado;
    fora disso ela diz o que da para perguntar.

  - O CLAUDE, pela internet, com a chave da Anthropic no config_local.py
    (CHAVE_DO_CLAUDE), que nao vai para o git. Pronto e testado, mas
    desligado ate alguem por a chave - ai conversa solto.

A voz nao passa por aqui: quem ouve e quem fala e o navegador.
"""

import ctypes
import datetime
import io
import json
import os
import re

from . import config
from .utils import log, normalizar

MODELO = "claude-opus-5"

# Quantas voltas de ferramenta por pergunta. Uma pergunta de balcao
# ("o 50190 saiu?") pede duas ou tres leituras; passar muito disso e
# sinal de que ela esta rodando em circulo, e quem espera e gente em pe
# na frente da tela.
VOLTAS_MAXIMAS = 6

# O historico vem do navegador, e o navegador e de qualquer um da rede.
# Estes tetos seguram o custo de uma conversa esquecida aberta o dia todo
# e de um corpo mal formado.
MENSAGENS_MAXIMAS = 20
LETRAS_POR_MENSAGEM = 4000

# O log de um dia cheio passa de mil linhas. Mandar tudo a cada pergunta
# custa caro e afoga o que importa; a ferramenta devolve o fim, ou o que
# bate com o filtro.
LINHAS_DO_LOG = 60
LINHAS_DO_LOG_MAXIMO = 300

SISTEMA = """\
Voce e a FIA, a inteligencia artificial da Finart, uma grafica. Seu \
trabalho do dia a dia e fechar chapa: voce vigia as pastas dos clientes \
(SOLIDA, VOPRIX, FIALHO, EMPORIO, VIVA, CREATIVE, PRIME, IDEAL, AMERICA), \
confere a arte, imprime a prova, abre a ordem de servico (OS) no \
GEREMPRE e entrega a chapa no CTP.

Agora voce esta conversando com alguem da equipe da grafica, por uma \
tela no navegador. A sua resposta vai ser LIDA EM VOZ ALTA. Por isso:
- fale como uma colega de trabalho conversando, em portugues do Brasil, \
com calor e naturalidade, sem ser formal;
- nada de markdown, listas, asteriscos, tabelas ou emoji: so frases;
- seja direta. Em geral duas a cinco frases bastam. Se a pessoa pedir \
detalhe, ai sim se estenda;
- nome de arquivo longo, fale so o numero e o cliente ("o 50190 da \
SOLIDA"), a nao ser que precisem do nome inteiro;
- horario, diga como se fala ("as dez e dezenove").

O QUE VOCE PODE FAZER NESTA CONVERSA: so olhar. Voce tem ferramentas \
que leem o log do dia, as pendencias, o registro do que ja saiu, a fila \
de OS e se o vigia esta rodando. Use-as antes de responder qualquer \
coisa sobre o trabalho - nunca responda de memoria nem invente numero, \
horario ou nome de arquivo. Se a ferramenta nao trouxe, diga que nao \
achou.

O QUE VOCE NAO FAZ NESTA CONVERSA: abrir ou mudar OS, gravar ou refazer \
chapa, apagar ou mover arquivo, mexer no banco. Se pedirem, explique com \
gentileza que por aqui voce so consulta, e que isso fica com o operador \
- e diga o que ele precisaria fazer, se souber. Nunca diga que fez algo \
que nao fez.

Como ler o que as ferramentas trazem:
- no log, linha com ">>>" e alerta; "OK em 96s" quer dizer que a chapa \
foi gravada no CTP; "PENDENCIA" e algo que precisa de gente;
- "a vaga X da OS Y SUMIU" quer dizer que alguem salvou a OS por cima \
com ela aberta na tela, e o servico precisa ser lancado a mao para nao \
ficar sem cobranca;
- "_v2" no nome da chapa quer dizer que ja existia uma chapa com aquele \
nome e esta saiu ao lado, sem apagar a outra;
- no registro, status "ok" e feito pela FIA; "feito_a_mao" e feito por \
gente.
"""


# ----------------------------------------------------------------------
# AS FERRAMENTAS - todas de leitura
# ----------------------------------------------------------------------
# Leem config.PASTA_CONTROLE NA HORA, e nao numa copia feita ao importar:
# e o que deixa o teste apontar para uma pasta de mentira, e o mesmo
# cuidado que o config.py documenta sobre o config_local.

def _pasta():
    return config.PASTA_CONTROLE


def _ler_linhas(nome):
    try:
        with io.open(os.path.join(_pasta(), nome), encoding="utf-8",
                     errors="replace") as f:
            return [l.rstrip("\n") for l in f if l.strip()]
    except OSError:
        return None


def ler_log(filtro=None, linhas=LINHAS_DO_LOG):
    """O fim do log do dia - ou as linhas que tem o filtro."""
    todas = _ler_linhas("_log_ctp.txt")
    if todas is None:
        return "nao achei o log (_log_ctp.txt) na pasta de controle"
    try:
        linhas = max(1, min(LINHAS_DO_LOG_MAXIMO, int(linhas)))
    except (TypeError, ValueError):
        linhas = LINHAS_DO_LOG
    if filtro:
        f = filtro.lower()
        todas = [l for l in todas if f in l.lower()]
        if not todas:
            return "nenhuma linha do log tem '%s'" % filtro
    return "\n".join(todas[-linhas:])


def ler_pendencias(quantas=20):
    """As ultimas pendencias anotadas, a mais recente por ultimo."""
    todas = _ler_linhas("_PENDENCIAS.txt")
    if todas is None:
        return "nao achei o _PENDENCIAS.txt"
    try:
        quantas = max(1, min(100, int(quantas)))
    except (TypeError, ValueError):
        quantas = 20
    return "\n".join(todas[-quantas:]) or "nenhuma pendencia anotada"


def procurar_no_registro(texto):
    """O que o registro sabe dos arquivos cujo nome tem este texto."""
    if not texto or not str(texto).strip():
        return "diga um pedaco do nome para procurar"
    try:
        with io.open(os.path.join(_pasta(), config.REGISTRO),
                     encoding="utf-8") as f:
            registro = json.load(f)
    except (OSError, ValueError):
        return "nao consegui ler o registro (%s)" % config.REGISTRO
    t = str(texto).lower()
    achados = []
    for chave, entrada in registro.items():
        nome = entrada.get("arquivo") or chave.split("|")[0]
        if t in nome.lower():
            achados.append({k: entrada.get(k) for k in
                            ("arquivo", "status", "saidas", "motivo",
                             "quando", "impresso") if entrada.get(k)
                            not in (None, "", [])})
    if not achados:
        return "nada no registro com '%s'" % texto
    # os mais novos por ultimo, como o resto: o registro guarda na ordem
    # em que as coisas aconteceram
    return json.dumps(achados[-15:], ensure_ascii=False, indent=1)


def fila_de_os(cliente=None):
    """Quantos servicos esperam OS, por cliente - ou os de um cliente."""
    try:
        with io.open(os.path.join(_pasta(), "_fila_os.json"),
                     encoding="utf-8") as f:
            fila = json.load(f)
    except (OSError, ValueError):
        return "nao consegui ler a fila de OS"
    if cliente:
        c = str(cliente).upper()
        deste = [i.get("titulo") for i in fila
                 if str(i.get("cliente", "")).upper() == c]
        if not deste:
            return "nada da %s na fila de OS" % c
        return "%d da %s:\n%s" % (len(deste), c, "\n".join(deste[-30:]))
    conta = {}
    for i in fila:
        conta[i.get("cliente") or "?"] = conta.get(i.get("cliente") or "?", 0) + 1
    return ", ".join("%s %d" % par for par in sorted(conta.items())) or "fila vazia"


def vigia_rodando():
    """
    O vigia esta de pe? Responde pelo _rodando.lock.

    SO LE O QUE ESTA ANOTADO A PARTIR DO SEGUNDO BYTE, como o
    utils.quem_esta_rodando. NUNCA se tenta pegar a trava para 'ver se
    esta livre': conseguindo, esta conversa passaria a segura-la, e o
    vigia que subisse depois se recusaria a rodar achando que ja ha outro.
    """
    caminho = os.path.join(_pasta(), "_rodando.lock")
    try:
        with open(caminho, "rb") as f:
            f.seek(1)
            anotado = f.read(80).decode("utf-8", "ignore").strip()
    except OSError:
        return "nao achei sinal do vigia (_rodando.lock)"
    ultima = (_ler_linhas("_log_ctp.txt") or ["(log vazio)"])[-1]
    return ("o vigia anotou: %s. Ultima linha do log: %s"
            % (anotado or "(nada)", ultima))


FERRAMENTAS = {
    "ler_log": ler_log,
    "ler_pendencias": ler_pendencias,
    "procurar_no_registro": procurar_no_registro,
    "fila_de_os": fila_de_os,
    "vigia_rodando": vigia_rodando,
}

DESCRICOES = [
    {"name": "ler_log",
     "description": "Le o log do vigia do CTP (_log_ctp.txt): o que foi "
                    "fechado, gravado, impresso, lancado em OS, e os "
                    "alertas. Sem filtro devolve o fim do log; com filtro "
                    "(numero do servico, cliente, palavra) devolve as "
                    "linhas que o contem. Cada linha comeca com [dd/mm "
                    "hh:mm:ss].",
     "input_schema": {"type": "object", "properties": {
         "filtro": {"type": "string",
                    "description": "texto a procurar, sem diferenca de "
                                   "maiuscula. Ex.: '50190', 'SOLIDA', "
                                   "'PENDENCIA', '25/09'"},
         "linhas": {"type": "integer",
                    "description": "quantas linhas do fim (padrao 60, "
                                   "maximo 300)"}},
         "required": []}},
    {"name": "ler_pendencias",
     "description": "Le as ultimas pendencias - o que a FIA nao conseguiu "
                    "resolver sozinha e precisa de gente.",
     "input_schema": {"type": "object", "properties": {
         "quantas": {"type": "integer", "description": "padrao 20"}},
         "required": []}},
    {"name": "procurar_no_registro",
     "description": "Procura no registro do que ja foi processado os "
                    "arquivos cujo nome tem o texto: status, chapas que "
                    "sairam, quando, se foi impresso.",
     "input_schema": {"type": "object", "properties": {
         "texto": {"type": "string",
                   "description": "pedaco do nome do arquivo, ex.: '50190'"}},
         "required": ["texto"]}},
    {"name": "fila_de_os",
     "description": "A fila de servicos lembrados para OS, contada por "
                    "cliente - ou a lista de um cliente.",
     "input_schema": {"type": "object", "properties": {
         "cliente": {"type": "string", "description": "ex.: 'SOLIDA'"}},
         "required": []}},
    {"name": "vigia_rodando",
     "description": "Diz se o vigia do CTP esta rodando, desde quando, e a "
                    "ultima coisa que ele escreveu no log.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
]


def usar_ferramenta(nome, entrada):
    """Chama a ferramenta pelo nome. Erro vira texto, nunca derruba."""
    funcao = FERRAMENTAS.get(nome)
    if funcao is None:
        return "nao conheco a ferramenta '%s'" % nome, True
    try:
        return str(funcao(**(entrada or {}))), False
    except Exception as e:
        return "a ferramenta falhou: %s" % str(e)[:200], True


# ----------------------------------------------------------------------
# A CONVERSA
# ----------------------------------------------------------------------

def chave():
    """A chave da Anthropic: do config_local, ou do ambiente."""
    return (getattr(config, "CHAVE_DO_CLAUDE", None)
            or os.environ.get("ANTHROPIC_API_KEY") or None)


def _mensagens(historico):
    """
    O historico do navegador vira mensagens do Claude - so texto.

    O navegador guarda a conversa, e nao este servidor: a tela e de
    varias pessoas ao mesmo tempo, e cada aba tem a sua. O que chega e
    podado aqui, porque chega de fora.
    """
    msgs = []
    for item in (historico or [])[-MENSAGENS_MAXIMAS:]:
        if not isinstance(item, dict):
            continue
        papel = "assistant" if item.get("papel") == "fia" else "user"
        texto = str(item.get("texto") or "").strip()[:LETRAS_POR_MENSAGEM]
        if not texto:
            continue
        if msgs and msgs[-1]["role"] == papel:
            msgs[-1]["content"] += "\n" + texto
        else:
            msgs.append({"role": papel, "content": texto})
    # a conversa tem de comecar e terminar com a pessoa falando
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    while msgs and msgs[-1]["role"] != "user":
        msgs.pop()
    return msgs


def _cliente():
    import anthropic
    return anthropic.Anthropic(api_key=chave(), timeout=90.0, max_retries=2)


def responder(historico, cliente=None, agora=None):
    """
    Recebe a conversa, devolve {"resposta": texto, "erro": bool}.

    'cliente' e para o teste por um Claude de mentira no lugar.
    """
    msgs = _mensagens(historico)
    if not msgs:
        return {"resposta": "Nao ouvi nenhuma pergunta.", "erro": True}
    if cliente is None and not chave():
        # sem chave, as respostas prontas: so a ultima fala importa, elas
        # nao lembram da conversa
        return {"resposta": responder_sem_ia(msgs[-1]["content"], agora),
                "erro": False}

    # A HORA VAI NA PERGUNTA, e nao no SISTEMA: o texto do sistema fica
    # igual o dia todo e o Claude o guarda em cache; um relogio ali
    # mudaria a cada pedido e jogaria o cache fora.
    agora = agora or datetime.datetime.now()
    msgs[-1]["content"] = ("(agora sao %s)\n%s"
                           % (agora.strftime("%d/%m/%Y %H:%M"),
                              msgs[-1]["content"]))

    cliente = cliente or _cliente()
    try:
        for _ in range(VOLTAS_MAXIMAS):
            r = cliente.beta.messages.create(
                model=MODELO,
                max_tokens=4000,
                system=[{"type": "text", "text": SISTEMA,
                         "cache_control": {"type": "ephemeral"}}],
                tools=DESCRICOES,
                messages=msgs,
                # conversa de balcao: rapidez vale mais que pensar fundo
                output_config={"effort": "medium"},
                # se o modelo recusar, o proprio servidor da Anthropic
                # tenta outro - sem isto a pessoa ouviria silencio
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if r.stop_reason == "refusal":
                return {"resposta": "Desculpa, essa eu nao consigo "
                                    "responder.", "erro": True}
            if r.stop_reason != "tool_use":
                texto = " ".join(b.text for b in r.content
                                 if b.type == "text").strip()
                return {"resposta": texto or "Fiquei sem resposta.",
                        "erro": not texto}
            msgs.append({"role": "assistant", "content": r.content})
            resultados = []
            for b in r.content:
                if b.type != "tool_use":
                    continue
                saida, falhou = usar_ferramenta(b.name, b.input)
                resultados.append({"type": "tool_result",
                                   "tool_use_id": b.id,
                                   "content": saida, "is_error": falhou})
            msgs.append({"role": "user", "content": resultados})
        return {"resposta": "Procurei, procurei e nao cheguei numa "
                            "resposta. Tenta perguntar de outro jeito?",
                "erro": True}
    except Exception as e:
        # sem internet, chave errada, Anthropic fora: a tela explica, o
        # servidor da montagem segue de pe
        log("CONVERSA: nao consegui falar com o Claude (%s)" % str(e)[:150],
            alerta=True)
        return {"resposta": "Nao consegui pensar agora - perdi o contato "
                            "com o servidor da Anthropic. Tenta de novo "
                            "daqui a pouco.", "erro": True}


# ----------------------------------------------------------------------
# RESPOSTAS PRONTAS - o cerebro sem IA
# ----------------------------------------------------------------------
# Cada pergunta de todo dia tem a sua funcao, que le o arquivo e monta a
# frase. A frase e para ser OUVIDA: nada de nome de arquivo inteiro,
# nada de linha de log crua - "o 50190", "as 10:19".
#
# ESCOLHER A RESPOSTA E POR PALAVRA, e a ordem importa: numero de servico
# vem primeiro, porque "o 50190 saiu?" tem 'saiu' e nao e a pergunta do
# dia inteiro.

CLIENTES = ("SOLIDA", "VOPRIX", "FIALHO", "EMPORIO", "VIVA", "CREATIVE",
            "PRIME", "IDEAL", "AMERICA", "CARRIER")

AJUDA = ("Por enquanto eu entendo estas perguntas: o que saiu hoje, se "
         "tem pendencia, se o vigia esta rodando, como esta a fila de OS "
         "de um cliente, e o numero de um servico, tipo: o 50190 saiu?")

# Quantas pendencias ler em voz alta. Mais que isso ninguem guarda de
# ouvido; o resto fica dito como numero.
PENDENCIAS_FALADAS = 3


def _texto_simples(t):
    """Minusculo e sem acento, para procurar palavra."""
    return normalizar(t or "").lower()


def _hoje(agora):
    return agora.strftime("%d/%m")


def _hora_do_log(linha):
    """'[25/09 10:18:54] ...' -> '10:18'."""
    m = re.match(r"\[\d\d/\d\d (\d\d:\d\d)", linha or "")
    return m.group(1) if m else None


def _log_de_hoje(agora):
    return [l for l in (_ler_linhas("_log_ctp.txt") or [])
            if l.startswith("[%s " % _hoje(agora))]


def _cliente_na_pergunta(t):
    for c in CLIENTES:
        if re.search(r"\b%s\b" % c.lower(), t):
            return c
    return None


def _apelido(arquivo):
    """Como se fala o nome de um arquivo: 'o 50190', ou o comeco do nome."""
    nome = os.path.splitext(os.path.basename(str(arquivo or "")))[0]
    m = re.match(r"\s*(?:OS\s*)?(\d{4,6})\b", nome, re.I)
    if m:
        return "o %s" % m.group(1)
    return "o arquivo %s" % nome.strip()[:40]


def _juntar(itens):
    if len(itens) == 1:
        return itens[0]
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _motivo_falado(motivo):
    """
    O motivo da pendencia em uma frase que se entende de ouvido.

    Os casos conhecidos tem frase propria; o resto vai o comeco do texto
    como esta - melhor cru que errado.
    """
    m = motivo or ""
    da_os = re.search(r"da OS (\d+)", m)
    if "NAO ESTA MAIS LA" in m:
        return ("a vaga dele na OS %s sumiu, alguem salvou a OS por cima. "
                "Precisa lancar a mao, senao fica sem cobranca"
                % (da_os.group(1) if da_os else ""))
    if "saiu como _v2" in m:
        return ("ja existia uma chapa com esse nome, e a nova saiu ao "
                "lado, como v2")
    if "falar com o GEREMPRE" in m:
        return ("o GEREMPRE estava fora do ar, e a OS nao foi aberta. "
                "Precisa lancar a mao")
    if "nao e chapa" in m:
        return "o tamanho da pagina nao bate com nenhuma chapa"
    if "CorelDRAW nao converteu" in m:
        return "o CorelDRAW nao conseguiu converter o arquivo"
    if "MESMA OS" in m:
        return ("tem dois arquivos com a mesma OS, e nao sei se sao um "
                "servico so ou dois. Nao lancei nenhum")
    if "so manda .pdf" in m:
        return "chegou um arquivo que este cliente nao costuma mandar"
    if "ilegivel" in m:
        return "o PDF veio estragado, nao consegui ler"
    curto = m.split(". ")[0].strip()
    return curto[:140] + ("..." if len(curto) > 140 else "")


def _partes_da_pendencia(linha):
    """'25/09 10:33 | SOLIDA | arquivo | motivo' - o cliente e opcional."""
    partes = [p.strip() for p in linha.split(" | ")]
    hora = partes[0][6:11] if len(partes[0]) >= 11 else ""
    if len(partes) >= 4:
        return hora, partes[1], partes[2], " | ".join(partes[3:])
    if len(partes) == 3:
        return hora, None, partes[1], partes[2]
    return hora, None, "", partes[-1]


def _pendencias_de_hoje(agora):
    return [l for l in (_ler_linhas("_PENDENCIAS.txt") or [])
            if l.startswith(_hoje(agora) + " ")]


def resposta_pendencias(agora, cliente=None):
    linhas = _pendencias_de_hoje(agora)
    if cliente:
        linhas = [l for l in linhas if cliente in l.upper()]
    de_quem = " da %s" % cliente if cliente else ""
    if not linhas:
        return "Hoje nao tem nenhuma pendencia%s. Tudo tranquilo!" % de_quem
    n = len(linhas)
    frases = ["Hoje tem %d pendencia%s%s." % (n, "s" if n > 1 else "",
                                              de_quem)]
    # A MESMA PENDENCIA SE REPETE: o 50190 de 25/09/2026 perdeu a vaga
    # duas vezes na mesma OS, e ouvir a mesma frase duas vezes seguidas
    # so gasta a paciencia de quem esta ouvindo. Fala-se a mais nova.
    ditas, faladas = set(), 0
    for linha in reversed(linhas):
        hora, cli, arquivo, motivo = _partes_da_pendencia(linha)
        quem = _apelido(arquivo) + (" da %s" % cli if cli else "")
        o_que = _motivo_falado(motivo)
        if (quem, o_que) in ditas:
            continue
        ditas.add((quem, o_que))
        frases.append("As %s, %s: %s." % (hora, quem, o_que))
        faladas += 1
        if faladas == PENDENCIAS_FALADAS:
            break
    if n > len(ditas) and faladas == PENDENCIAS_FALADAS:
        frases.append("Tem mais no arquivo de pendencias.")
    return " ".join(frases)


def _processo_vivo(pid):
    """
    True, False, ou None quando nao da para saber.

    Pergunta ao Windows se o processo existe, SEM tocar na trava - ver o
    vigia_rodando, la em cima, sobre por que nunca se pega a trava.
    """
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
    except (AttributeError, OSError):
        return None                          # fora do Windows
    h = k.OpenProcess(0x1000, False, int(pid))   # so consulta
    if not h:
        # 87 = parametro invalido: o processo nao existe mais. Outro
        # erro (acesso negado) nao diz nada sobre ele estar vivo.
        return False if ctypes.get_last_error() == 87 else None
    try:
        codigo = ctypes.c_ulong()
        if not k.GetExitCodeProcess(h, ctypes.byref(codigo)):
            return None
        return codigo.value == 259           # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def resposta_vigia(agora):
    try:
        with open(os.path.join(_pasta(), "_rodando.lock"), "rb") as f:
            f.seek(1)
            anotado = f.read(80).decode("utf-8", "ignore")
    except OSError:
        return ("Nao achei sinal do vigia por aqui. Ou ele nunca subiu "
                "nesta maquina, ou a pasta de controle mudou de lugar.")
    m = re.search(r"processo (\d+), desde (\d\d/\d\d) (\d\d:\d\d)", anotado)
    if not m:
        return "Nao consegui ler o que o vigia anotou."
    pid, dia, hora = m.groups()
    quando = ("as %s" % hora if dia == _hoje(agora)
              else "as %s do dia %s" % (hora, dia))
    ultima = _hora_do_log((_ler_linhas("_log_ctp.txt") or [""])[-1])
    depois = (" A ultima anotacao dele no log foi as %s." % ultima
              if ultima else "")
    vivo = _processo_vivo(pid)
    if vivo is False:
        return ("Nao, o vigia esta parado. Ele tinha subido %s, mas o "
                "processo nao existe mais. Precisa subir de novo pelo VS "
                "Code.%s" % (quando, depois))
    if vivo is None:
        return ("O vigia subiu %s, mas daqui eu nao consigo confirmar se "
                "ele continua de pe.%s" % (quando, depois))
    return "Sim, o vigia esta rodando desde %s.%s" % (quando, depois)


def resposta_saiu_hoje(agora, cliente=None):
    hoje = _log_de_hoje(agora)
    chapas = [m.group(1) for m in
              (re.search(r"OK em \d+s: (.+?) \(", l) for l in hoje) if m]
    arquivos = []
    for l in hoje:
        m = re.match(r"\[[^\]]+\] '(.+)': \d+ pagina", l)
        if m and m.group(1) not in arquivos:
            arquivos.append(m.group(1))
    if not chapas:
        return "Hoje ainda nao saiu nenhuma chapa."
    frase = ("Hoje ja %s %d chapa%s, de %d arquivo%s."
             % ("sairam" if len(chapas) > 1 else "saiu",
                len(chapas), "s" if len(chapas) > 1 else "",
                len(arquivos), "s" if len(arquivos) != 1 else ""))
    ultimos = []
    for a in reversed(arquivos):
        if _apelido(a) not in ultimos:
            ultimos.append(_apelido(a))
        if len(ultimos) == 3:
            break
    if ultimos:
        frase += " %s %s." % ("O ultimo foi" if len(ultimos) == 1
                              else "Os ultimos foram", _juntar(ultimos))
    if cliente:
        frase += " Separar por cliente eu ainda nao sei."
    return frase


def resposta_fila(cliente=None):
    try:
        with io.open(os.path.join(_pasta(), "_fila_os.json"),
                     encoding="utf-8") as f:
            fila = json.load(f)
    except (OSError, ValueError):
        return "Nao consegui ler a fila de OS agora."
    if cliente:
        deste = [i for i in fila
                 if str(i.get("cliente", "")).upper() == cliente]
        if not deste:
            return "A %s nao tem nenhum servico esperando OS." % cliente
        n = len(deste)
        recentes = []
        for i in reversed(deste):
            if _apelido(i.get("titulo")) not in recentes:
                recentes.append(_apelido(i.get("titulo")))
            if len(recentes) == 3:
                break
        if n == 1:
            return ("A %s tem um servico na fila, esperando OS: %s."
                    % (cliente, recentes[0]))
        return ("A %s tem %d servicos na fila, esperando OS. %s: %s."
                % (cliente, n, "O mais recente" if len(recentes) == 1
                   else "Os mais recentes", _juntar(recentes)))
    if not fila:
        return "A fila de OS esta vazia."
    conta = {}
    for i in fila:
        c = i.get("cliente") or "sem cliente"
        conta[c] = conta.get(c, 0) + 1
    return ("Na fila, esperando OS, tem: %s."
            % _juntar(["%s com %d" % par for par in sorted(conta.items())]))


def _quando_falado(quando, agora):
    """'25/09/2026 10:19:05' -> 'hoje as 10:19' ou 'dia 24/09 as 17:02'."""
    m = re.match(r"(\d\d/\d\d)/\d{4} (\d\d:\d\d)", quando or "")
    if not m:
        return ""
    dia, hora = m.groups()
    return ("hoje as %s" % hora if dia == _hoje(agora)
            else "dia %s as %s" % (dia, hora))


def resposta_servico(numero, agora):
    try:
        with io.open(os.path.join(_pasta(), config.REGISTRO),
                     encoding="utf-8") as f:
            registro = json.load(f)
    except (OSError, ValueError):
        registro = {}
    padrao = re.compile(r"(?<!\d)%s(?!\d)" % numero)
    achados = [e for k, e in registro.items()
               if padrao.search(e.get("arquivo") or k.split("|")[0])]

    frases = []
    if achados:
        # o registro guarda na ordem em que aconteceu: o ultimo e o de agora
        e = achados[-1]
        quando = _quando_falado(e.get("quando"), agora)
        onde = ", " + quando if quando else ""
        saidas = e.get("saidas") or []
        if e.get("status") == "ok":
            if len(saidas) == 1:
                # '50190_v2' dito com o sublinhado nao se entende
                chapa = (" e gerou a chapa %s"
                         % os.path.splitext(os.path.basename(saidas[0]))[0]
                         .replace("_", " "))
            elif saidas:
                chapa = " e gerou %d chapas" % len(saidas)
            else:
                chapa = ""
            frases.append("O %s saiu sim%s%s." % (numero, onde, chapa))
        elif e.get("status") == "feito_a_mao":
            frases.append("O %s foi feito a mao, fora de mim." % numero)
        else:
            porque = _motivo_falado(e.get("motivo")) if e.get("motivo") else ""
            frases.append("O %s passou por mim%s, mas nao saiu%s." % (
                numero, onde, ": " + porque if porque else ""))
        if len(achados) > 1:
            frases.append("Ele passou %d vezes por mim." % len(achados))
    else:
        no_log = [l for l in (_ler_linhas("_log_ctp.txt") or [])
                  if padrao.search(l)]
        if not no_log:
            return ("Nao achei nada do %s, nem no registro nem no log. Pode "
                    "ser que ainda nao tenha chegado na pasta." % numero)
        frases.append("O %s ainda nao esta no registro, mas aparece no "
                      "log. A ultima vez foi as %s."
                      % (numero, _hora_do_log(no_log[-1]) or "?"))

    pend = [l for l in _pendencias_de_hoje(agora) if padrao.search(l)]
    if pend:
        hora, _, _, motivo = _partes_da_pendencia(pend[-1])
        frases.append("Atencao, tem pendencia dele hoje, as %s: %s."
                      % (hora, _motivo_falado(motivo)))
    return " ".join(frases)


def resposta_os(numero):
    linhas = [l for l in (_ler_linhas("_log_ctp.txt") or [])
              if re.search(r"\bOS %s\b" % numero, l)]
    if not linhas:
        return "Nao achei a OS %s no log." % numero
    n = len(linhas)
    frase = "A OS %s aparece %d vez%s no log, a ultima as %s." % (
        numero, n, "es" if n > 1 else "",
        _hora_do_log(linhas[-1]) or "?")
    m = re.search(r"com '([^']+)'", " ".join(linhas))
    if m:
        frase += " Eu lancei nela %s." % _apelido(m.group(1))
    if any("SUMIU" in l for l in linhas):
        frase += (" E atencao: uma vaga que eu lancei nela sumiu depois, "
                  "alguem salvou a OS por cima. Precisa lancar a mao.")
    return frase


# OS ACENTOS ENTRAM NA SAIDA. O codigo da casa e ASCII, mas a frase e
# para ser ouvida: a voz do navegador le "nao" como "nau", e na tela fica
# com cara de erro. Entao as frases sao escritas sem acento e esta tabela
# os poe no fim. As palavras que mudam de sentido com acento (o 'esta'
# demonstrativo, o 'e' de ligar frase) foram evitadas nas frases de
# proposito, e aqui so aparece a forma que as frases usam.
#
# Escritos com \u para o fonte seguir ASCII: \u00e3 e o 'a' com til,
# \u00e1 com agudo, \u00ea com circunflexo, \u00e7 o cedilha.
ACENTOS = {
    "nao": "n\u00e3o", "estao": "est\u00e3o", "esta": "est\u00e1",
    "ja": "j\u00e1", "so": "s\u00f3", "sao": "s\u00e3o",
    "entao": "ent\u00e3o", "tambem": "tamb\u00e9m",
    "pendencia": "pend\u00eancia", "pendencias": "pend\u00eancias",
    "servico": "servi\u00e7o", "servicos": "servi\u00e7os",
    "ultima": "\u00faltima", "ultimo": "\u00faltimo",
    "ultimos": "\u00faltimos", "anotacao": "anota\u00e7\u00e3o",
    "atencao": "aten\u00e7\u00e3o", "alguem": "algu\u00e9m",
    "lancar": "lan\u00e7ar", "lancado": "lan\u00e7ado",
    "sairam": "sa\u00edram", "pagina": "p\u00e1gina",
    "maquina": "m\u00e1quina", "cobranca": "cobran\u00e7a",
    "voce": "voc\u00ea", "numero": "n\u00famero", "pe": "p\u00e9",
    "senao": "sen\u00e3o",
}
FRASES_COM_CRASE = (("a mao", "\u00e0 m\u00e3o"),
                    ("e so chamar", "\u00e9 s\u00f3 chamar"))


def _com_acento(texto):
    for de, para in FRASES_COM_CRASE:
        texto = texto.replace(de, para)
    # 'as 10:19' vira '\u00e0s 10:19' - menos depois de 'desde', onde a crase
    # esta errada ("desde as 11:47")
    texto = re.sub(r"(?<!desde )\b([Aa])s (?=\d\d:\d\d)",
                   lambda m: ("\u00c0" if m.group(1) == "A"
                              else "\u00e0") + "s ",
                   texto)

    def trocar(m):
        palavra = m.group(0)
        certo = ACENTOS.get(palavra.lower())
        if not certo:
            return palavra
        return certo[0].upper() + certo[1:] if palavra[0].isupper() else certo
    return re.sub(r"[A-Za-z]+", trocar, texto)


def responder_sem_ia(pergunta, agora=None):
    """Escolhe a resposta pronta pela palavra. Nunca levanta."""
    return _com_acento(_escolher(pergunta, agora or datetime.datetime.now()))


def _escolher(pergunta, agora):
    t = _texto_simples(pergunta)
    cliente = _cliente_na_pergunta(t)
    try:
        m = re.search(r"\bos\s*(?:n[ro]?\.?\s*)?(\d{4,6})\b", t)
        if m:
            return resposta_os(m.group(1))
        m = re.search(r"(?<!\d)(\d{4,6})(?!\d)", t)
        if m:
            return resposta_servico(m.group(1), agora)
        if re.search(r"vigia|rodando|ligad|funcionando|\bno ar\b|de pe", t):
            return resposta_vigia(agora)
        if re.search(r"pendenc|problema|erro|deu ruim", t):
            return resposta_pendencias(agora, cliente)
        if re.search(r"fila|esperando os|abrir os", t):
            return resposta_fila(cliente)
        if re.search(r"saiu|sairam|gravou|gravad|chapa|hoje|quant", t):
            return resposta_saiu_hoje(agora, cliente)
        if re.search(r"obrigad|valeu", t):
            return "De nada! Precisando, e so chamar."
        if re.search(r"\b(oi|ola|bom dia|boa tarde|boa noite|e ai)\b", t):
            return "Oi! Tudo bem? " + AJUDA
        if cliente:
            return resposta_fila(cliente)
    except Exception as e:
        log("CONVERSA: resposta pronta falhou em '%s' (%s)"
            % (str(pergunta)[:60], str(e)[:120]), alerta=True)
        return "Tive um problema para ler isso agora. Tenta de novo?"
    return "Hum, essa eu ainda nao sei responder. " + AJUDA
