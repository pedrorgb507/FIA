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

QUEM PENSA E O CLAUDE, pela internet, com a chave da Anthropic no
config_local.py (CHAVE_DO_CLAUDE) - que nao vai para o git. Sem chave, a
tela diz isso em vez de quebrar. A voz nao passa por aqui: quem ouve e
quem fala e o navegador de quem esta usando.
"""

import datetime
import io
import json
import os

from . import config
from .utils import log

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
        return {"resposta": "Ainda nao tenho a chave da Anthropic, entao "
                            "nao consigo pensar a resposta. Peca para quem "
                            "cuida da FIA por a CHAVE_DO_CLAUDE no "
                            "config_local.py.", "erro": True}

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
