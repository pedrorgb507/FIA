# -*- coding: utf-8 -*-
r"""
A fila da montagem no navegador. CASCA FINA - nao ha regra aqui dentro.

    python run_montagem.py        (ou clique em iniciar_montagem.bat)

POR QUE ISTO EXISTE. A AMERICA manda o arquivo POR MONTAR e diz no
WhatsApp a montagem que quer. Hoje uma pessoa so le aquela mensagem,
decide chapa, arranjo e vao, e passa os parametros a FIA - e enquanto ela
nao faz isso, o servico nao anda. A frase que orienta tudo e do operador:
"o que eu quero e que a minha equipe nao dependa de mim pra dar
andamento".

Esta tela e o primeiro passo disso: a equipe abre a fila DO PC DELA e ve
o que esta esperando, JA MEDIDO, sem abrir o PDF e sem perguntar a
ninguem.

O QUE MORA AQUI E O QUE NAO MORA. Fila, medicao e registro moram no
montagem.py. Este arquivo traduz pedido em chamada e desenha a pagina -
mais nada. A regra e dura de proposito: uma conta escrita aqui deixaria a
tela e o vigia podendo discordar sobre o mesmo arquivo, e ai um dos dois
manda chapa errada. Ha teste que le esta fonte e reprova se aparecer
Ghostscript, pypdf ou leitura de marca.

PROCESSO SEPARADO DO VIGIA, e isso e decisao e nao acaso. O vigia fecha
chapa dos outros seis clientes o dia inteiro, e e ele que paga o dia.
Este servidor cair - por um pedido estranho, por a porta estar ocupada,
por alguem fechar a janela - nao pode levar aquilo junto. O vigia nem
sabe que este arquivo existe.

SOBRE A REDE. Ele atende em 0.0.0.0, que quer dizer "tambem quem vier
pela rede interna". Em 127.0.0.1 a pagina abriria so na maquina da FIA -
que e exatamente a cadeira que a equipe tem de disputar hoje. Sem senha,
escolha do operador: "senha em grafica vira papelzinho no monitor"; quem
decidiu fica gravado pelo nome que a pessoa digita.

NA PRIMEIRA VEZ, O WINDOWS VAI BARRAR. O Defender bloqueia porta que
ninguem pediu para abrir, e ai a pagina abre na maquina da FIA e nao
abre nas outras - o que parece defeito do programa e nao e. Rode uma vez,
como administrador:

    ferramentas/liberar_montagem_no_defender.ps1
"""

import html
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import montagem
# a conversa so le, e nao tem regra de montagem - ver conversa.py
from . import conversa
from .config import ENDERECO_DA_MONTAGEM, PORTA_DA_MONTAGEM
from .utils import log

ENDERECO = ENDERECO_DA_MONTAGEM
PORTA = PORTA_DA_MONTAGEM

# O PAINEL E UM ARQUIVO DA CASA, e nao uma pagina escrita aqui.
#
# Ele ja existia, ja desenha a chapa em escala, calcula sangria, vao e
# pinca, risca a grade que nao cabe, e sua conta bate com montagem real
# na terceira casa decimal. Servi-lo e o que este modulo faz; reescreve-lo
# seria jogar fora conta provada.
PAINEL = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "ferramentas",
    "painel_imposicao.html")

# Onde o servidor enfia os dados da casa. A marca esta escrita no painel,
# e ele PARA quando ela chega vazia - ver o comentario de la.
MARCA_DOS_DADOS = '<script id="dados-da-casa" type="application/json">{}</script>'


# ----------------------------------------------------------------------
# A PAGINA
# ----------------------------------------------------------------------
# E uma funcao que recebe a fila e devolve texto: da para prova-la sem
# subir socket nenhum, e e assim que ela e testada.

ESTILO = """
  * { box-sizing: border-box }
  body { font: 15px/1.5 "Segoe UI", system-ui, sans-serif; margin: 0;
         background: #f4f5f7; color: #1c1e21 }
  header { background: #1c1e21; color: #fff; padding: 18px 28px }
  header h1 { margin: 0; font-size: 20px; font-weight: 600 }
  header p { margin: 4px 0 0; font-size: 13px; color: #b9bdc4 }
  main { padding: 24px 28px; max-width: 1100px }
  table { border-collapse: collapse; width: 100%; background: #fff;
          box-shadow: 0 1px 2px rgba(0,0,0,.12) }
  th, td { padding: 11px 14px; text-align: left; border-bottom: 1px solid #e6e8eb }
  th { background: #fafbfc; font-size: 12px; text-transform: uppercase;
       letter-spacing: .04em; color: #5c6370 }
  td.arquivo { font-weight: 600 }
  td.numero { font-variant-numeric: tabular-nums; white-space: nowrap }
  .nao { color: #b23a2f; font-weight: 600 }
  .sim { color: #1f7a37 }
  .erro { color: #b23a2f; font-size: 13px }
  tr.aviso td { background: #fff8e1; border-top: 0; padding-top: 0;
                color: #7a5300; font-size: 13px; line-height: 1.45 }
  h2 { margin: 34px 0 4px; font-size: 16px; font-weight: 600 }
  h2 .quantos { background: #1c1e21; color: #fff; border-radius: 10px;
                padding: 1px 8px; font-size: 12px; vertical-align: 2px }
  p.dica { margin: 0 0 12px; color: #5c6370; font-size: 13px;
           max-width: 70ch }
  td.acao { text-align: right; white-space: nowrap }
  button.aprovar { font: inherit; font-size: 12.5px; cursor: pointer;
                   padding: 6px 12px; border-radius: 3px; color: #fff;
                   background: #1f7a37; border: 1px solid #1a6b30 }
  button.aprovar:disabled { background: #8a9099; border-color: #8a9099;
                            cursor: default }
  /* REFAZER e LIMPAR LISTA nao sao o caminho feliz: ficam discretos, de
     contorno, para ninguem apertar por engano no lugar do aprovar - que
     e o unico dos tres que grava chapa. */
  button.refazer { font: inherit; font-size: 12.5px; cursor: pointer;
                   padding: 6px 12px; border-radius: 3px; margin-right: 6px;
                   color: #1c1e21; background: #fff; border: 1px solid #c3c7cc }
  button.refazer:hover { border-color: #8a9099; background: #f7f8f9 }
  button.limpar { font: inherit; font-size: 11.5px; font-weight: 400;
                  cursor: pointer; margin-left: 10px; padding: 3px 9px;
                  border-radius: 3px; color: #575d66; background: #fff;
                  border: 1px solid #d3d7dc; vertical-align: 2px }
  button.limpar:hover { color: #1c1e21; border-color: #8a9099 }
  button.refazer:disabled, button.limpar:disabled { color: #8a9099;
                            cursor: default }
  /* CODIGO VELHO NA MEMORIA. Vermelho e no alto de tudo: quem le isto
     esta prestes a montar chapa com um programa que nao e o que a tela
     mostra, e isso nao pode passar por recado discreto. */
  .codigo-velho { background:#fdf0ee; border:1px solid #e8a49c;
                  border-left:4px solid #b3261e; border-radius:4px;
                  padding:13px 16px; margin:0 0 18px; font-size:13.5px;
                  line-height:1.55; color:#5c1a15 }
  .codigo-velho b { color:#b3261e }
  /* o botao que conserta o que a faixa reclama - a fila roda em OUTRA
     maquina, e sem ele a unica saida era caminhar ate la */
  button.reiniciar { font: inherit; font-size: 12.5px; cursor: pointer;
                     padding: 5px 12px; border-radius: 3px; color: #fff;
                     background: #b3261e; border: 1px solid #8c1d18;
                     margin: 2px 4px 2px 0 }
  button.reiniciar:hover { background: #8c1d18 }
  button.reiniciar:disabled { background: #8a9099; border-color: #8a9099;
                              cursor: default }
  .codigo-velho code { background:#f6dedb; color:#5c1a15 }
  /* a linha que pede olho: o que saiu da regra */
  tr.olho td { background: #fffdf5 }
  tr.olho td.arquivo { box-shadow: inset 3px 0 0 #d9a406 }
  a { color: #1c1e21 }
  /* a contagem do topo do historico: o que ensina, em numero */
  .tira { display: grid; gap: 1px; background: #e6e8eb; margin: 0 0 16px;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          box-shadow: 0 1px 2px rgba(0,0,0,.12) }
  .tira div { background: #fff; padding: 10px 14px }
  .tira span { display: block; color: #5c6370; font-size: 12px }
  .tira b { font-size: 20px; font-weight: 600 }
  p.erro { color: #b23a2f }
  .vazio { background: #fff; padding: 40px 28px; text-align: center;
           color: #5c6370; box-shadow: 0 1px 2px rgba(0,0,0,.12) }
  .vazio strong { display: block; font-size: 17px; color: #1c1e21;
                  margin-bottom: 6px }
  footer { padding: 0 28px 28px; color: #8a9099; font-size: 12px }
  code { background: #e9ebee; padding: 1px 5px; border-radius: 3px }
"""


# O CLIQUE QUE APROVA. E o unico JavaScript desta pagina, e ele existe
# por uma razao: a mudanca de pasta E a aprovacao, e o que separa o
# clique do arrastar a mao e ficar dito QUEM clicou. Por isso a primeira
# coisa que ele faz e pedir o nome - e ele o lembra neste navegador, o
# mesmo 'fia-quem' que o painel usa, para se digitar uma vez por PC.
APROVAR_JS = """
<script>
async function _pedir(b, rota, corpo, fazendo, falhou){
  const antes = b.textContent;
  b.disabled = true; b.textContent = fazendo;
  try{
    const r = await fetch(rota, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(corpo)});
    const d = await r.json();
    if(d.feito){
      /* DEU CERTO E MESMO ASSIM PRECISA DE GENTE. A pagina recarrega
         logo em seguida, e o recado se perderia com ela - entao ele
         para na frente de quem apertou. */
      if(d.atencao) alert("ATENÇÃO\\n\\n" + d.atencao);
      /* O REFAZER manda continuar em outro lugar - o painel do arquivo
         de origem. Recarregar a fila deixaria a pessoa procurando o que
         ela acabou de mandar refazer. Sem 'ir_para' (origem que nao
         esta mais na fila), o porque explica e a fila recarrega. */
      if(d.ir_para){ location.href = d.ir_para; return; }
      if(d.porque && rota === "/refazer") alert(d.porque);
      location.reload();
      return;
    }
    alert(falhou + "\\n\\n" + d.porque);
  }catch(err){
    alert("não consegui falar com a FIA: " + err);
  }
  b.disabled = false; b.textContent = antes;
}

document.querySelectorAll("button.aprovar").forEach(b => {
  b.addEventListener("click", () => {
    /* PUBLICAR NAO PEDE NOME: nao e decisao, e um passo - o .cdr vira
       PDF e nada mais acontece. Quem decide alguma coisa e quem monta e
       quem aprova, e esses dois assinam. */
    if(b.dataset.publicar){
      _pedir(b, "/publicar", {arquivo: b.dataset.publicar},
             "Publicando… (isto abre o CorelDRAW)", "Não publiquei.");
      return;
    }
    let quem = "";
    try{ quem = localStorage.getItem("fia-quem") || ""; }catch(_){}
    quem = (prompt("Quem está aprovando esta montagem?", quem) || "").trim();
    if(!quem) return;
    try{ localStorage.setItem("fia-quem", quem); }catch(_){}
    _pedir(b, "/aprovar", {arquivo: b.dataset.arquivo, quem: quem},
           "Aprovando…", "Não aprovei.");
  });
});

/* QUEM ESTA MEXENDO - o mesmo nome dos outros botoes, guardado no
   navegador. Refazer e limpar nao gravam chapa, mas ficam registrados:
   quem tirou da lista responde por ter tirado. */
function _quem(pergunta){
  let q = "";
  try{ q = localStorage.getItem("fia-quem") || ""; }catch(_){}
  q = (prompt(pergunta, q) || "").trim();
  if(q){ try{ localStorage.setItem("fia-quem", q); }catch(_){} }
  return q;
}

document.querySelectorAll("button.refazer").forEach(b => {
  b.addEventListener("click", () => {
    const quem = _quem("Quem está mandando refazer esta montagem?");
    if(!quem) return;
    _pedir(b, "/refazer", {arquivo: b.dataset.arquivo, quem: quem},
           "Tirando da lista…", "Não consegui.");
  });
});

/* REINICIAR A FILA. O servidor sobe uma janela nova e fecha esta, entao
   a pagina fica sem resposta por alguns segundos - por isso ela nao
   recarrega na hora: espera a porta voltar e so entao volta sozinha. */
const _rein = document.getElementById("reiniciar-fila");
if(_rein){
  _rein.addEventListener("click", async () => {
    if(!confirm("Reiniciar a fila?\\n\\nA janela do servidor e trocada por "
                + "uma nova, com o codigo do disco. Quem estiver montando "
                + "agora perde o que digitou na tela.")){ return; }
    _rein.disabled = true; _rein.textContent = "Reiniciando…";
    try{
      const r = await fetch("/reiniciar", {method: "POST",
        headers: {"Content-Type": "application/json"}, body: "{}"});
      const d = await r.json();
      if(!d.feito){ alert("Nao reiniciei.\\n\\n" + d.porque);
                    _rein.disabled = false; _rein.textContent = "Reiniciar agora";
                    return; }
    }catch(err){ /* o servidor pode morrer antes de responder, e tudo bem */ }
    /* ESPERA A FILA VOLTAR, em vez de recarregar as cegas: entre o
       fechar e o abrir ha alguns segundos em que a pagina daria erro de
       conexao, e quem clicou acharia que quebrou. */
    _rein.textContent = "esperando a fila voltar…";
    let tentativas = 0;
    const olhar = setInterval(async () => {
      tentativas++;
      try{
        await fetch("/?t=" + Date.now(), {cache: "no-store"});
        clearInterval(olhar); location.reload();
      }catch(_){
        if(tentativas > 40){
          clearInterval(olhar);
          alert("A fila nao voltou sozinha. Abra o iniciar_montagem.bat "
                + "na maquina do servidor.");
        }
      }
    }, 1000);
  });
}

const _limpar = document.getElementById("limpar-revisao");
if(_limpar){
  _limpar.addEventListener("click", () => {
    /* A CONFIRMACAO DIZ O QUE **NAO** ACONTECE. O medo de quem aperta e
       perder trabalho, e e justamente o que este botao nao faz. */
    /* \\n E NAO \n: este bloco e uma string PYTHON, e um \n aqui vira
       quebra de linha DE VERDADE no meio da string JavaScript. Isso
       quebra o script inteiro - e junto com ele o botao APROVAR, que
       nao tem nada a ver com este. Foi o que aconteceu em 18/09/2026. */
    if(!confirm("Tirar todas da lista?\\n\\nIsto limpa SÓ A TELA: nenhum "
                + "arquivo é apagado, nada vai para a PARA CTP e nenhuma "
                + "chapa é gravada. As montagens continuam na pasta do dia.")){
      return;
    }
    const quem = _quem("Quem está limpando a lista?");
    if(!quem) return;
    _pedir(_limpar, "/limpar-revisao", {quem: quem},
           "Limpando…", "Não limpei.");
  });
}
</script>
"""


# ----------------------------------------------------------------------
# O ANDAMENTO DA MONTAGEM
#
# Pedido do operador, 23/09/2026: "tem como a gente criar no programa uma
# barra de porcentagem da montagem da america? que vai mostrando o
# andamento da montagem do arquivo?".
#
# O /montar e um POST que so responde no FIM, e o fim pode levar sete
# minutos numa 775x635. Ate aqui a tela escrevia "Montando..." e ficava
# muda o tempo todo - e quem acha que travou reinicia, o que ja custou
# quatro rodadas do mesmo servico.
#
# FUNCIONA PORQUE O SERVIDOR TEM LINHAS. O ThreadingHTTPServer atende o
# GET /andamento enquanto a montagem corre na linha do POST; num servidor
# de uma linha so a pergunta ficaria na fila atras da propria montagem, e
# a barra so apareceria depois de tudo pronto - inutil.
#
# QUEM DA O NUMERO E A TELA, e nao este modulo. Ela gera o id e o manda
# junto da ordem, porque o POST so responderia com um id no fim - tarde
# demais para perguntar por ele.
_ANDAMENTO = {}
_TRANCA_DO_ANDAMENTO = threading.Lock()

# Quantos andamentos guardar. Cada um tem algumas centenas de bytes, e
# eles so existem para a tela perguntar; o teto esta aqui porque este
# processo fica semanas no ar, e dicionario que so cresce e vazamento.
ANDAMENTOS_GUARDADOS = 40


def _comecar_o_andamento(ident, arquivo):
    """Abre a ficha deste trabalho. Devolve o proprio id, ou None."""
    if not ident:
        return None
    with _TRANCA_DO_ANDAMENTO:
        # O MAIS VELHO SAI, e so os TERMINADOS. Jogar fora um que ainda
        # corre deixaria a tela daquela pessoa sem resposta no meio da
        # montagem dela - e duas pessoas montando ao mesmo tempo e para
        # isso que este servidor existe.
        if len(_ANDAMENTO) >= ANDAMENTOS_GUARDADOS:
            velhos = sorted((v.get("comecou", 0), k)
                            for k, v in _ANDAMENTO.items()
                            if v.get("terminou"))
            for _, k in velhos[:max(1, len(velhos) // 2)]:
                _ANDAMENTO.pop(k, None)
        _ANDAMENTO[ident] = {"arquivo": arquivo, "passo": "recebi o pedido",
                             "feitos": 0, "total": 1, "indefinido": True,
                             "saiu": [], "comecou": time.time(),
                             "terminou": None, "feito": None}
    return ident


def _anotar_o_andamento(ident):
    """O 'avisar' que o motor chama a cada passo. Ver montar_bate_vira."""
    def avisar(d):
        with _TRANCA_DO_ANDAMENTO:
            ficha = _ANDAMENTO.get(ident)
            if ficha is None:
                return
            passo = d.get("passo") or ""
            # A LISTA DO QUE JA SAIU e o que a tela mostra embaixo da
            # barra. Passo repetido nao entra duas vezes: no livro o
            # mesmo texto volta a cada caderno.
            if ficha["passo"] and ficha["passo"] != passo:
                if not ficha["saiu"] or ficha["saiu"][-1] != ficha["passo"]:
                    ficha["saiu"].append(ficha["passo"])
                del ficha["saiu"][:-12]
            ficha["passo"] = passo
            # NUNCA PARA TRAS. A barra voltando e o sinal mais rapido de
            # que alguem contou errado, e quem monta acredita nela.
            fracao = (float(d.get("feitos") or 0)
                      / float(d.get("total") or 1))
            antes = ficha["feitos"] / float(ficha["total"] or 1)
            if fracao >= antes:
                # NUNCA CHEIA ENQUANTO CORRE, nem que o motor diga que
                # acabou. Ele acaba antes do trabalho: depois de gravar,
                # o executar ainda confere a pinca no arquivo que saiu -
                # e essa conferencia REPROVA e APAGA a montagem quando
                # nao bate. Mostrar 100% ali manda a pessoa buscar um
                # arquivo que pode nao existir.
                #
                # Quem fecha a barra e _acabar_o_andamento, e so ele.
                ficha["total"] = float(d.get("total") or 1)
                ficha["feitos"] = min(float(d.get("feitos") or 0),
                                      ficha["total"] * 0.99)
            ficha["indefinido"] = bool(d.get("indefinido"))
    return avisar


def _acabar_o_andamento(ident, feito, porque=""):
    with _TRANCA_DO_ANDAMENTO:
        ficha = _ANDAMENTO.get(ident)
        if ficha is None:
            return
        if ficha["passo"]:
            ficha["saiu"].append(ficha["passo"])
        ficha.update(terminou=time.time(), feito=bool(feito),
                     indefinido=False, porque=porque,
                     passo="pronto" if feito else "parei")
        if feito:
            # SO CHEGA A 100% TENDO TERMINADO. Barra cheia com a
            # montagem correndo e a mentira mais facil de contar aqui.
            ficha["feitos"] = ficha["total"]


def andamento(ident):
    """O que a tela pergunta uma vez por segundo."""
    with _TRANCA_DO_ANDAMENTO:
        ficha = _ANDAMENTO.get(ident)
        if ficha is None:
            return {"achei": False}
        d = dict(ficha)
    d["achei"] = True
    d["segundos"] = int((d.get("terminou") or time.time()) - d["comecou"])
    return d


def _mm(valor):
    return "-" if valor is None else ("%.0f" % valor)


def _cor(item):
    """
    O que se le na coluna da cor - e e ela que escolhe a maquina.

    A palavra vem escrita, e nao so a lista de tintas: 'K' nao diz nada
    para quem esta escolhendo maquina, e 'preto e branco' casa com a
    regra da casa - acima do formato 4, colorido na SM 74 e
    preto-e-branco na MOZP.
    """
    if item.get("peb") is None:
        return "-"
    cores = item.get("cores") or "".join(item.get("tintas") or []) or "?"
    return ("preto e branco (%s)" % cores if item["peb"]
            else "colorido (%s)" % cores)


def _marca(item):
    if item.get("tem_marca") is None:
        return '<span class="nao">-</span>'
    if not item["tem_marca"]:
        return '<span class="nao">nao achei</span>'
    no_pe = item.get("marca_no_pe")
    if no_pe is None:
        return '<span class="sim">sim</span>'
    return '<span class="sim">sim, a %s mm do pe</span>' % _numero(no_pe)


def _numero(valor):
    """3.0 -> '3,0'. Virgula, que e como a casa escreve medida."""
    return ("%.1f" % valor).replace(".", ",")


def _sangria(item):
    """
    A coluna da sangria - e ela tem TRES respostas, nao duas.

    'nao da para saber' NAO PODE PARECER 'nao tem'. Arquivo que nao
    declara TrimBox e nao tem marca de corte nao foi medido por ninguem;
    mostrar 'nao' ali faria alguem montar confiando numa resposta que
    ninguem deu - e sangria e coisa que se descobre no papel cortado.
    """
    if item.get("sangria") is None:
        return '<span class="nao">nao da para saber</span>'
    if not item["sangria"]:
        return '<span class="nao">nao veio sangrada</span>'
    mm = item.get("sangria_mm")
    return ('<span class="sim">sim%s</span>'
            % ("" if mm is None else ", %s mm" % _numero(mm)))


def _aviso_da_sangria(item):
    """
    A linha do recado, quando as duas leituras discordam.

    Ela ocupa a largura da tabela de proposito: e aviso, nao coluna. E
    aparece SO na divergencia - aviso que aparece sempre ninguem le.
    """
    if not item.get("sangria_divergem") or not item.get("sangria_recado"):
        return ""
    return ('<tr class="aviso"><td></td><td colspan="5">%s</td></tr>'
            % html.escape(item["sangria_recado"]))


def _para_montar(item):
    """
    O nome do arquivo, clicavel: leva ao painel DAQUELE arquivo.

    E o caminho inteiro do sistema numa frase - a pessoa ve o que esta
    esperando, escolhe um, e cai no painel ja preenchido. Antes disso ela
    tinha de abrir o PDF, medir na mao e digitar tudo de novo.
    """
    nome = item.get("arquivo") or "?"
    return ('<a href="/painel?arquivo=%s">%s</a>'
            % (urllib.parse.quote(nome, safe=""), html.escape(nome)))


def _aviso_das_paginas(item):
    """
    A linha do recado quando o arquivo tem mais de uma pagina.

    A GRAVADORA NAO PUXA MULTIPLAS PAGINAS, e ja houve arquivo que foi
    para o CTP com duas dentro: a OS cobrou as chapas certas, a prova
    saiu com as duas, e mesmo assim so uma seria gravada. Duas sao a
    frente e o verso, e isso a casa sabe montar.

    ---------------------------------------------------------------
    LIVRO DEIXOU DE SER 'NINGUEM ADIVINHA', EM 21/09/2026.

    Ate aqui esta linha dizia, para QUALQUER arquivo de tres paginas ou
    mais: "eu nao escolho quais montar. Separe as que vao para a chapa,
    ou monte uma de cada vez". Era verdade quando foi escrita, e deixou
    de ser no mesmo dia em que o painel aprendeu a fechar livro - ele
    ganhou os campos de paginas, sobra, repeticao e cadernos, e o motor
    ganhou o montar_livro.

    O operador viu as duas telas discordarem e mandou alinhar: a fila
    recusava o que o painel ja fazia. Uma tela que manda separar o
    arquivo a mao, quando ha um caminho pronto ao lado, faz a pessoa
    trabalhar duas horas para nada - e pior, ensina que a ferramenta nao
    serve.

    O QUE DECIDE E O MULTIPLO DE 4, e nao o numero de paginas. Todo
    caderno nasce de uma folha dobrada, e folha dobrada da 4, 8, 12, 16
    paginas - sempre multiplo de 4. Livro cujo total nao e multiplo de 4
    nao fecha em caderno nenhum, e ai o recado antigo continua certo.

    A SOBRA NAO REPROVA. O 'Miolo Sapientia Crucis' tem 228 paginas:
    nao fecha em caderno de 16 (sobram 4) nem de 8, e fecha em 57 de 4.
    Isso nao e defeito - e a conversa que o painel existe para ter, no
    campo 'paginas sem caderno'. Quem decide o que fazer com a sobra e
    gente, e agora ela tem onde decidir.
    """
    quantas = item.get("paginas")
    if not quantas or quantas < 3:
        return ""

    if quantas % 4 == 0:
        nome = item.get("arquivo") or ""
        return ('<tr class="aviso"><td></td><td colspan="5">%d páginas — '
                'múltiplo de 4, então fecha em caderno. '
                '<a href="/painel?arquivo=%s">Monte como livro</a>: '
                'escolha o processo, o tamanho do caderno e o que fazer '
                'com a sobra.</td></tr>'
                % (quantas, urllib.parse.quote(nome, safe="")))

    return ('<tr class="aviso"><td></td><td colspan="5">%d páginas — não é '
            'múltiplo de 4, então não fecha em caderno, e a gravadora não '
            'puxa múltiplas páginas. Separe as que vão para a chapa, ou '
            'monte uma de cada vez.</td></tr>' % quantas)


def _linha_do_cdr(item):
    """
    O .cdr no portao: ele nao se mede, e precisa ser publicado antes.

    O BOTAO EXISTE PORQUE A FILA NAO PUBLICA SOZINHA. Ela e uma tela que
    a equipe atualiza a vontade, e publicar por conta propria faria cada
    F5 abrir uma sessao do CorelDRAW.
    """
    nome = item.get("arquivo") or "?"
    return (
        '<tr><td class="arquivo">%s</td>'
        '<td colspan="4">arquivo do CorelDRAW — precisa ser publicado em '
        'PDF antes de montar</td>'
        '<td class="acao"><button class="aprovar" data-publicar="%s">'
        'Publicar em PDF</button></td></tr>'
        % (html.escape(nome), html.escape(nome)))


def _linha(item):
    if item.get("precisa_publicar"):
        return _linha_do_cdr(item)
    if item.get("erro"):
        # ARQUIVO SEM MEDIDA CONTINUA CLICAVEL: ele esta no portao, e
        # trabalho, e o painel serve para montar a mao o que a FIA nao
        # conseguiu medir.
        return (
            '<tr><td class="arquivo">%s</td>'
            '<td colspan="5" class="erro">nao consegui medir: %s</td></tr>'
            % (_para_montar(item), html.escape(item["erro"])))
    return (
        '<tr><td class="arquivo">%s</td>'
        '<td class="numero">%s x %s mm</td>'
        '<td>%s</td>'
        '<td class="numero">%s</td>'
        '<td>%s</td>'
        '<td>%s</td></tr>%s'
        % (_para_montar(item),
           _mm(item.get("largura")), _mm(item.get("altura")),
           html.escape(_cor(item)),
           "-" if item.get("paginas") is None else item["paginas"],
           _marca(item), _sangria(item),
           _aviso_das_paginas(item) + _aviso_da_sangria(item)))


RETRATO_DO_ARRANQUE = None


def _guardar_o_retrato():
    """
    A data dos .py como estavam quando ESTA janela subiu.

    Chamado uma vez, no main(). O vigia ja faz isso para a janela preta
    dele (monitor.avisar_se_o_programa_mudou); aqui a mesma pergunta
    precisa de outra RESPOSTA, porque quem usa a fila esta no navegador
    de OUTRA maquina e nunca ve janela preta nenhuma.
    """
    global RETRATO_DO_ARRANQUE
    from .monitor import retrato_do_programa
    RETRATO_DO_ARRANQUE = retrato_do_programa()


def codigo_que_mudou():
    """
    Quais .py mudaram no disco depois que esta janela subiu.

    O QUE ISTO PEGA, e custou uma montagem em 21/09/2026: o eudson-pc
    puxou o codigo novo e NAO reiniciou o run_montagem. O painel ficou
    novo - o HTML e lido do disco a cada pedido - e o motor ficou VELHO,
    porque modulo Python se le uma vez, ao subir.

    Foi o pior dos dois mundos: a tela mostrava o seletor de giro novo,
    o operador escolheu 0 graus, e o motor - sem saber o que era giro -
    deitou a peca assim mesmo. A tela prometeu 425 x 310 e o motor
    respondeu 205 x 640 'nao cabe'. Nada disso parecia codigo velho,
    porque a metade que se ve estava nova.
    """
    if RETRATO_DO_ARRANQUE is None:
        return []
    from .monitor import retrato_do_programa
    agora = retrato_do_programa()
    return sorted(n for n, quando in agora.items()
                  if RETRATO_DO_ARRANQUE.get(n) != quando)


def reiniciar_a_fila():
    """
    Sobe uma janela nova desta fila e fecha esta. {"feito", "porque"}.

    Pedido do operador em 21/09/2026, olhando a faixa de codigo antigo:
    *"eu quero que saia esse mensagem daqui, me guie passo a passo como
    fazer ou entao veja se consegue fazer automaticamente"*.

    POR QUE UM BOTAO, E NAO SOZINHO. Reiniciar sozinho ao ver o disco
    mudar e tentador e tem um custo escondido: quem estiver com o painel
    aberto, no meio de uma montagem, perde a janela sem ter pedido. E o
    vigia nao se reinicia de proposito - rodando pelo F5 do VS Code, um
    processo novo se soltaria do depurador e a janela ficaria muda.
    Clicando, a pessoa sabe o que vai acontecer e escolhe a hora.

    POR QUE ISSO EXISTE. A fila roda em OUTRA maquina - o servidor da
    casa -, e quem usa esta no navegador do PC dele. Sem o botao, a unica
    saida era alguem caminhar ate la para fechar uma janela preta, e
    tres manhas desta semana se perderam nisso.

    O FILHO NASCE ANTES DE O PAI MORRER, e por isso ele espera a porta:
    por um instante os dois existem e a porta ainda esta presa aqui. E
    ele nasce SOLTO - novo grupo de processos -, senao morreria junto
    com este.
    """
    try:
        ambiente = dict(os.environ)
        # quanto o filho espera a porta do pai ser liberada
        ambiente["FIA_ESPERAR_PORTA"] = "20"
        raiz = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        alvo = os.path.join(raiz, "run_montagem.py")
        if not os.path.isfile(alvo):
            return {"feito": False,
                    "porque": "nao achei o run_montagem.py em %s" % raiz}

        solto = 0
        if os.name == "nt":
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            solto = 0x00000008 | 0x00000200
        subprocess.Popen([sys.executable, alvo], cwd=raiz, env=ambiente,
                         creationflags=solto, close_fds=True)
    except Exception as e:
        return {"feito": False,
                "porque": "nao consegui subir a janela nova: %s" % str(e)[:160]}

    def morrer():
        # o respiro e para a RESPOSTA chegar ao navegador: fechando aqui
        # mesmo, quem clicou veria a conexao cair e nao saberia se deu
        # certo
        time.sleep(1.5)
        log("MONTAGEM: reiniciada a pedido da tela", alerta=True)
        os._exit(0)

    threading.Thread(target=morrer, daemon=True).start()
    return {"feito": True,
            "porque": "subindo a janela nova - esta pagina volta sozinha"}


def _faixa_do_codigo_velho():
    """A faixa vermelha no alto, quando o disco esta na frente da memoria."""
    mudaram = codigo_que_mudou()
    if not mudaram:
        return ""
    return (
        '<div class="codigo-velho"><b>ESTA TELA ESTÁ RODANDO CÓDIGO '
        'ANTIGO.</b> O programa mudou no disco depois que esta janela '
        'subiu, e o Python só lê o código uma vez — a página que você vê '
        'já é a nova, mas quem monta ainda é a versão de antes. '
        '<button class="reiniciar" id="reiniciar-fila">Reiniciar agora</button>'
        ' — ou pare o <code>iniciar_montagem.bat</code> e suba de novo, '
        'na máquina do servidor. Mudou: <code>%s</code></div>'
        % html.escape(", ".join(mudaram)))


def _moldura(cabecalho, corpo, portao=None, depois=""):
    return (
        "<!doctype html><html lang=pt-br><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width, initial-scale=1'>"
        "<title>Montagem AMERICA - o que falta</title>"
        "<style>%s</style></head><body>"
        "<header><h1>Montagem AMERICA</h1><p>%s</p></header>"
        "<main>%s%s%s</main>"
        "<footer>portao: <code>%s</code> · "
        '<a href="/historico">histórico da semana</a> · '
        '<a href="/conversa">falar com a FIA</a></footer>'
        "%s</body></html>"
        % (ESTILO, html.escape(cabecalho), _faixa_do_codigo_velho(),
           corpo, depois,
           html.escape(portao or "(nao achei a pasta do dia)"),
           APROVAR_JS if depois else ""))


def _linha_de_revisao(item):
    """Uma montagem esperando olho humano."""
    de_onde = []
    if item.get("quem_montou"):
        de_onde.append("montada por %s" % item["quem_montou"])
    if item.get("quando"):
        de_onde.append(item["quando"])
    if item.get("chapa"):
        de_onde.append("%s, grade %s" % (item["chapa"],
                                         item.get("grade") or "?"))
    if not de_onde:
        # montagem feita a mao no Corel, como a casa sempre fez
        de_onde.append("montada fora da tela")

    avisos = []
    if item.get("maquina_trocada"):
        avisos.append(item["maquina_trocada"])
    if item.get("liberado_sem_caber"):
        # QUEM REVISA PRECISA VER ISTO ANTES DE APROVAR: e o caso em que
        # alguem ja disse 'pode ir' sabendo que nao cabia.
        avisos.append("LIBERADA SEM CABER por %s: %s"
                      % (item.get("liberado_por") or "?",
                         "; e ".join(item.get("liberado_porque") or [])))

    # REFAZER fica AO LADO de aprovar, e nao escondido: a montagem que
    # saiu errada e tao comum quanto a que saiu certa - o CHECK-LIST de
    # 18/09/2026 saiu em uma cor sendo colorido -, e sem este botao a
    # unica saida era aprovar o errado ou deixar entulhando a lista.
    return (
        '<tr><td class="arquivo">%s</td><td>%s</td>'
        '<td class="acao">'
        '<button class="refazer" data-arquivo="%s">Refazer</button>'
        '<button class="aprovar" data-arquivo="%s">'
        'Aprovar e mandar para a PARA CTP</button></td></tr>%s'
        % (html.escape(item.get("arquivo") or "?"),
           html.escape(" · ".join(de_onde)),
           html.escape(item.get("arquivo") or ""),
           html.escape(item.get("arquivo") or ""),
           ('<tr class="aviso"><td></td><td colspan="2">%s</td></tr>'
            % html.escape(" — ".join(avisos))) if avisos else ""))


def _bloco_da_revisao(itens):
    """
    A segunda metade da tela: o que ja foi montado e espera olho humano.

    FICA NA MESMA PAGINA da fila de propósito. Sao as duas metades da
    mesma pergunta - o que falta fazer hoje -, e quem abre a tela quer
    ver as duas sem procurar.
    """
    if not itens:
        return ('<h2>Esperando revisão</h2><div class="vazio">'
                '<strong>Nada esperando revisão.</strong>'
                'O que for montado aparece aqui para alguém conferir '
                'antes de virar chapa.</div>')
    # LIMPAR LISTA fica no cabecalho, longe dos botoes de cada linha.
    # Ele NAO apaga nada - nem arquivo, nem montagem, nem chapa: so tira
    # da tela. Pedido do operador em 18/09/2026, "limpar lista que limpa
    # somente na pagina, nao deleta nada".
    return (
        '<h2>Esperando revisão <span class="quantos">%d</span>'
        '<button class="limpar" id="limpar-revisao" title="Tira todas da '
        'tela. Não apaga arquivo, não manda nada para a PARA CTP.">'
        'Limpar lista</button></h2>'
        '<p class="dica">Abra a montagem na pasta do dia, confira, e só '
        'então aprove. A mudança de pasta <b>é</b> o aprovado — dali em '
        'diante a FIA abre a OS, imprime a prova e grava a chapa.</p>'
        '<table><thead><tr><th>montagem</th><th>de onde veio</th>'
        '<th></th></tr></thead><tbody>%s</tbody></table>'
        % (len(itens), "".join(_linha_de_revisao(i) for i in itens)))


def pagina_da_fila(itens, portao=None, tem_portao=True, revisao=None,
                   erro_das_pastas=None):
    """
    O HTML da fila. Recebe a fila medida e devolve texto.

    'tem_portao' separa duas coisas que a tela confundia, e a confusao
    custaria uma manha: 'a equipe montou tudo' e 'a pasta nao esta la'.
    Sem essa separacao, uma manha sem portao mostrava fila vazia e a
    equipe iria embora achando que nao havia trabalho.

    O QUE O PORTAO FALTANDO QUER DIZER MUDOU EM 18/09/2026, e o recado
    mudou junto. Enquanto a pasta era criada por gente, faltar era
    normal: ninguem tinha preparado o dia ainda, e a tela pedia que
    alguem a criasse. Agora quem cria e a FIA, a cada volta do vigia e a
    cada vez que esta tela e desenhada - entao faltar so pode ser uma de
    duas coisas, e as duas sao defeito: o servidor esta fora do ar, ou a
    pasta da AMERICA esta so-leitura para nos.

    Mandar a equipe criar a pasta na mao agora seria conselho errado:
    ela criaria a pasta, o arquivo entraria, e a MONTAGEM gravada nao
    teria como voltar - quem grava e a FIA, que e justamente quem nao
    esta alcancando o servidor.
    """
    if not tem_portao:
        porque = ('<p class="erro">O servidor disse: %s</p>'
                  % html.escape(erro_das_pastas)) if erro_das_pastas else ""
        return _moldura(
            "nao consegui preparar a pasta do dia",
            '<div class="vazio"><strong>A pasta "%s" nao esta na pasta do '
            'dia, e eu nao consegui cria-la.</strong>Ela e criada sozinha, '
            'toda manha - faltar quer dizer que nao estou alcancando a '
            'pasta da AMERICA no servidor.%s'
            '<p class="erro">Nao crie a pasta na mao: o arquivo entraria, '
            'mas a montagem nao teria como ser gravada de volta. Chame '
            'quem cuida da rede.</p></div>'
            % (html.escape(montagem.PORTAO), porque), portao,
            _bloco_da_revisao(revisao or []))

    if itens:
        corpo = (
            "<table><thead><tr><th>arquivo</th><th>tamanho</th>"
            "<th>cor</th><th>paginas</th><th>marca de corte</th>"
            "<th>sangria</th>"
            "</tr></thead><tbody>%s</tbody></table>"
            % "".join(_linha(i) for i in itens))
        quantos = "%d arquivo%s esperando montagem" % (
            len(itens), "s" if len(itens) > 1 else "")
    else:
        # PORTAO VAZIO NAO E ERRO: e o dia normal de quem ja montou tudo.
        # Tela de erro aqui faria a equipe achar que o sistema quebrou.
        corpo = ('<div class="vazio"><strong>Nada esperando montagem.</strong>'
                 'O que a AMERICA mandar por montar aparece aqui, ja medido.'
                 '</div>')
        quantos = "a fila esta vazia"

    return _moldura(quantos, corpo, portao, _bloco_da_revisao(revisao or []))


def _linha_do_historico(linha):
    """Uma montagem no historico, com o que precisa de olho destacado."""
    quem = linha.get("quem") or "—"
    # O NOME DE QUEM APROVOU VEM DE FORA, digitado no navegador de quem
    # clicou - e vai para a tela de TODO MUNDO. Passou daqui cru uma vez;
    # um nome com '<' dentro viraria marcacao viva no historico.
    aprovou = (html.escape(linha["aprovado_por"])
               if linha.get("aprovado_por")
               else '<span class="nao">ainda não aprovada</span>')

    avisos = []
    if linha.get("maquina_trocada"):
        # ONDE A REGRA DA CASA NAO COBRE A REALIDADE - e e dai que sai a
        # proxima regra. E o que o operador vem procurar aqui.
        avisos.append('<b>máquina trocada fora da regra:</b> %s'
                      % html.escape(linha["maquina_trocada"]))
    if linha.get("liberado_sem_caber"):
        avisos.append('<b>liberada sem caber por %s:</b> %s'
                      % (html.escape(linha.get("liberado_por") or "?"),
                         html.escape("; e ".join(
                             linha.get("liberado_porque") or []))))

    return (
        '<tr%s><td class="numero">%s</td><td class="arquivo">%s</td>'
        '<td>%s</td><td>%s</td><td>%s</td></tr>%s'
        % (' class="olho"' if avisos else "",
           html.escape(linha.get("quando") or "—"),
           html.escape(linha.get("montagem") or linha.get("arquivo") or "?"),
           html.escape("%s %s" % (linha.get("chapa") or "—",
                                  linha.get("grade") or "")),
           html.escape(quem), aprovou,
           ('<tr class="aviso"><td></td><td colspan="4">%s</td></tr>'
            % " — ".join(avisos)) if avisos else ""))


def pagina_do_historico(linhas, dia=None, dias=7, data_nao_entendida=None):
    """
    A tela onde o operador ESCOLHE olhar.

    O TOPO CONTA OS DOIS CASOS QUE ENSINAM, e nao o total de montagens:
    maquina trocada fora da regra e montagem liberada sem caber. Uma
    tela que so diz 'foram 34 montagens' nao serve para o que ela existe.
    """
    trocadas = [x for x in linhas if x.get("maquina_trocada")]
    liberadas = [x for x in linhas if x.get("liberado_sem_caber")]
    sem_aprovar = [x for x in linhas if not x.get("aprovado_por")]

    # A FRASE CONCORDA. 'os últimos 1 dias' e 'nada montado em o dia' sao
    # o tique mais reconhecivel de tela gerada, e esta e a tela que o
    # operador abre quando quer ENTENDER alguma coisa.
    # DATA QUE NAO SE ENTENDEU NAO VIRA SILENCIO. Pedindo
    # '?dia=18-09-2026' a tela caia para a semana e continuava se
    # chamando 'o dia 18-09-2026': a pessoa leria uma semana inteira
    # achando que era um dia.
    nao_entendi = (
        '<p class="dica erro">Não entendi a data <b>%s</b> — escreva como a '
        'casa escreve, <code>18/09/2026</code>. Enquanto isso, o que está '
        'abaixo é o período de sempre.</p>'
        % html.escape(data_nao_entendida)) if data_nao_entendida else ""

    if dia:
        periodo, periodo_em = "o dia %s" % dia, "no dia %s" % dia
    elif dias == 1:
        periodo, periodo_em = "o último dia", "no último dia"
    else:
        periodo = "os últimos %d dias" % dias
        periodo_em = "nos últimos %d dias" % dias
    if linhas:
        corpo = (
            '<div class="tira">%s</div>'
            '<table><thead><tr><th>quando</th><th>montagem</th>'
            '<th>chapa</th><th>montou</th><th>aprovou</th></tr></thead>'
            '<tbody>%s</tbody></table>'
            % ("".join('<div><span>%s</span><b>%d</b></div>' % (rotulo, n)
                       for rotulo, n in (
                           ("montagens", len(linhas)),
                           ("máquina trocada fora da regra", len(trocadas)),
                           ("liberadas sem caber", len(liberadas)),
                           ("ainda não aprovadas", len(sem_aprovar)))),
               "".join(_linha_do_historico(x) for x in linhas)))
    else:
        corpo = ('<div class="vazio"><strong>Nada montado %s.</strong>'
                 'Cada montagem que a equipe fizer aparece aqui — quem '
                 'montou, quem aprovou, e o que saiu da regra.</div>'
                 % html.escape(periodo_em))

    return (
        "<!doctype html><html lang=pt-br><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width, initial-scale=1'>"
        "<title>Montagem AMERICA - historico</title>"
        "<style>%s</style></head><body>"
        "<header><h1>Histórico da montagem</h1><p>%s</p></header>"
        "<main>"
        '<p class="dica">O que está <b>destacado</b> é o que ensina: '
        'máquina trocada fora da regra é onde a regra da casa não cobre a '
        'realidade, e montagem liberada sem caber é o caso que ninguém '
        'previu. <a href="/">← a fila</a></p>'
        '<p class="dica">Ver: <a href="/historico?dias=1">hoje</a> · '
        '<a href="/historico?dias=7">a semana</a> · '
        '<a href="/historico?dias=30">o mês</a> · ou um dia só, com '
        '<code>/historico?dia=18/09/2026</code></p>'
        "%s%s</main>"
        "<footer>esta tela só lê — nada aqui apaga registro nenhum</footer>"
        "</body></html>"
        % (ESTILO, html.escape(periodo), nao_entendi, corpo))


def _json_para_dentro_do_html(dados):
    """
    O JSON escapado para viver dentro de um <script> do HTML.

    O '<' vira \\u003c, e isso NAO e zelo teorico: o nome do arquivo vem
    do que a AMERICA mandou pelo WhatsApp, e um nome com '</script>'
    dentro fecharia o bloco no meio e o resto viraria HTML. O JSON
    continua valido - \\u003c e a mesma letra para quem le.
    """
    return (json.dumps(dados, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def pagina_do_painel(dados):
    """
    O painel da casa com as tabelas do config enfiadas dentro.

    O ARQUIVO E LIDO A CADA PEDIDO, de proposito: quem mexe no painel ve
    o resultado no F5, sem reiniciar o servidor. Ele muda a mao, com o
    provador ao lado, e esperar reinicio a cada tentativa seria atrito
    onde nao precisa haver.
    """
    pagina = io.open(PAINEL, encoding="utf-8").read()
    if MARCA_DOS_DADOS not in pagina:
        # O PAINEL MUDOU DE FORMA. Melhor parar aqui do que servir uma
        # pagina que vai trabalhar com tabela vazia.
        raise RuntimeError(
            "nao achei onde por os dados da casa no painel_imposicao.html "
            "- a marca '<script id=\"dados-da-casa\"' mudou?")
    dentro = ('<script id="dados-da-casa" type="application/json">%s</script>'
              % _json_para_dentro_do_html(dados))
    return pagina.replace(MARCA_DOS_DADOS, dentro)


# ----------------------------------------------------------------------
# FALAR COM A FIA
# ----------------------------------------------------------------------
# Quem pensa e o conversa.py; aqui so a pagina. A voz e do navegador:
# o reconhecimento de fala do Chrome/Edge ouve, e o speechSynthesis fala.
#
# O MICROFONE SO ABRE EM ENDERECO SEGURO. O navegador libera o microfone
# em https ou em localhost - e esta tela e http pela rede interna. Na
# maquina da FIA funciona; nas outras, a pessoa digita e a FIA fala do
# mesmo jeito. A pagina diz isso em vez de ficar com um botao morto.

PAGINA_DA_CONVERSA = """<!doctype html><html lang=pt-br><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Falar com a FIA</title>
<style>
  :root { --fundo:#f4f5f7; --tinta:#1c1e21; --fraco:#5c6370; --cartao:#fff;
          --fia:#e8f0fb; --eu:#1c1e21; --eu-tinta:#fff; --acento:#1f5fbf;
          --vermelho:#b23a2f; --linha:#e6e8eb }
  @media (prefers-color-scheme: dark) {
    :root { --fundo:#15171a; --tinta:#e7e9ec; --fraco:#9aa1ab; --cartao:#1f2226;
            --fia:#1d2a3b; --eu:#e7e9ec; --eu-tinta:#15171a; --acento:#6ea3ef;
            --vermelho:#e0776c; --linha:#2c3036 } }
  * { box-sizing:border-box }
  body { margin:0; font:16px/1.5 "Segoe UI", system-ui, sans-serif;
         background:var(--fundo); color:var(--tinta); display:flex;
         flex-direction:column; height:100vh; height:100dvh }
  header { padding:14px 20px; border-bottom:1px solid var(--linha);
           display:flex; align-items:center; gap:12px; flex-wrap:wrap }
  header h1 { margin:0; font-size:19px; font-weight:600; flex:1 }
  header label { font-size:14px; color:var(--fraco); cursor:pointer }
  header a { font-size:14px; color:var(--acento) }
  #conversa { flex:1; overflow-y:auto; padding:20px; display:flex;
              flex-direction:column; gap:12px; max-width:820px; width:100%;
              margin:0 auto }
  .bolha { max-width:85%; padding:10px 14px; border-radius:14px;
           white-space:pre-wrap; overflow-wrap:anywhere }
  .fia { background:var(--fia); align-self:flex-start;
         border-bottom-left-radius:4px }
  .eu { background:var(--eu); color:var(--eu-tinta); align-self:flex-end;
        border-bottom-right-radius:4px }
  .erro { color:var(--vermelho) }
  .pensando { color:var(--fraco); font-style:italic }
  form { display:flex; gap:8px; padding:12px 20px 18px; max-width:820px;
         width:100%; margin:0 auto }
  input { flex:1; min-width:0; font:inherit; padding:12px 14px;
          border-radius:24px; border:1px solid var(--linha);
          background:var(--cartao); color:var(--tinta) }
  button { font:inherit; border:0; border-radius:24px; padding:0 18px;
           cursor:pointer; background:var(--acento); color:#fff; min-height:46px }
  button:disabled { opacity:.5; cursor:default }
  #mic { width:46px; padding:0; font-size:20px }
  #mic.ouvindo { background:var(--vermelho) }
  #aviso { font-size:13px; color:var(--fraco); text-align:center;
           padding:0 20px; margin:0 }
</style></head><body>
<header><h1>Falar com a FIA</h1>
  <label><input type=checkbox id=voz checked> ela responde falando</label>
  <a href="/">fila da montagem</a></header>
<div id=conversa aria-live=polite></div>
<p id=aviso></p>
<form id=form><button type=button id=mic title="falar" aria-label="falar">&#127908;</button>
  <input id=texto autocomplete=off placeholder="Pergunte alguma coisa...">
  <button id=enviar>Enviar</button></form>
<script>
(function () {
  var historico = [], ocupado = false;
  var caixa = document.getElementById("conversa"),
      texto = document.getElementById("texto"),
      enviar = document.getElementById("enviar"),
      mic = document.getElementById("mic"),
      voz = document.getElementById("voz"),
      aviso = document.getElementById("aviso");

  try { voz.checked = localStorage.getItem("fia-voz") !== "nao"; } catch (e) {}
  voz.onchange = function () {
    try { localStorage.setItem("fia-voz", voz.checked ? "sim" : "nao"); } catch (e) {}
    if (!voz.checked) speechSynthesis.cancel();
  };

  function bolha(classe, t) {
    var d = document.createElement("div");
    d.className = "bolha " + classe;
    d.textContent = t;
    caixa.appendChild(d);
    caixa.scrollTop = caixa.scrollHeight;
    return d;
  }

  // A VOZ. Prefere uma voz brasileira 'natural' (as do Edge soam gente);
  // nao havendo, qualquer pt-BR; nao havendo, a padrao.
  function escolherVoz() {
    var vs = speechSynthesis.getVoices();
    var br = vs.filter(function (v) { return /pt[-_]BR/i.test(v.lang); });
    return br.filter(function (v) { return /natural|online/i.test(v.name); })[0]
        || br[0] || null;
  }
  function falar(t) {
    if (!voz.checked || !window.speechSynthesis) return;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(t);
    u.lang = "pt-BR";
    var v = escolherVoz();
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }
  if (window.speechSynthesis) speechSynthesis.onvoiceschanged = function () {};

  function perguntar(t) {
    t = (t || "").trim();
    if (!t || ocupado) return;
    ocupado = true; enviar.disabled = true;
    bolha("eu", t);
    historico.push({papel: "eu", texto: t});
    var espera = bolha("fia pensando", "olhando...");
    fetch("/conversa", {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({historico: historico})})
    .then(function (r) { return r.json(); })
    .then(function (d) {
      espera.className = "bolha fia" + (d.erro ? " erro" : "");
      espera.textContent = d.resposta;
      // RESPOSTA DE ERRO NAO ENTRA NO HISTORICO: ela nao e fala da FIA
      // sobre o trabalho, e a pergunta seguinte a leria como se fosse
      if (!d.erro) historico.push({papel: "fia", texto: d.resposta});
      else historico.pop();
      falar(d.resposta);
    })
    .catch(function () {
      espera.className = "bolha fia erro";
      espera.textContent = "Nao consegui falar com o servidor da FIA.";
      historico.pop();
    })
    .then(function () { ocupado = false; enviar.disabled = false; texto.focus(); });
  }

  document.getElementById("form").onsubmit = function (e) {
    e.preventDefault();
    var t = texto.value; texto.value = "";
    perguntar(t);
  };

  // O OUVIDO.
  var Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Rec) {
    mic.disabled = true;
    aviso.textContent = "Este navegador nao ouve voz - use o Chrome ou o Edge. Digitar funciona.";
  } else if (!window.isSecureContext) {
    mic.disabled = true;
    aviso.textContent = "O microfone so abre na maquina da FIA (o navegador bloqueia em endereco da rede). Digite, que ela responde falando.";
  } else {
    var rec = new Rec(), ouvindo = false;
    rec.lang = "pt-BR"; rec.interimResults = true; rec.continuous = false;
    rec.onresult = function (e) {
      var t = "";
      for (var i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
      texto.value = t;
      if (e.results[e.results.length - 1].isFinal) { texto.value = ""; perguntar(t); }
    };
    rec.onend = function () { ouvindo = false; mic.classList.remove("ouvindo"); };
    rec.onerror = function (e) {
      if (e.error === "not-allowed") aviso.textContent = "O navegador nao deixou usar o microfone.";
    };
    mic.onclick = function () {
      if (ouvindo) { rec.stop(); return; }
      if (window.speechSynthesis) speechSynthesis.cancel();
      ouvindo = true; mic.classList.add("ouvindo"); rec.start();
    };
  }

  bolha("fia", "Oi! Sou a FIA. Pode me perguntar o que saiu hoje, o que deu pendencia, se o vigia esta rodando...");
  texto.focus();
})();
</script></body></html>"""


def pagina_nao_achei():
    """
    Endereco que nao existe.

    NAO SE MOSTRA A FILA VAZIA AQUI, e era o que se fazia: endereco
    digitado errado abria 'Nada esperando montagem' com o rodape dizendo
    que nao achou a pasta do dia. O 404 nao aparece no navegador, e quem
    leu aquilo concluiria que nao ha trabalho.
    """
    return _moldura(
        "este endereco nao existe",
        '<div class="vazio"><strong>Nao achei esta pagina.</strong>'
        'A fila da montagem fica em <a href="/">/</a> - e dali que se ve '
        'o que esta esperando.</div>')


# ----------------------------------------------------------------------
# O SERVIDOR
# ----------------------------------------------------------------------

class Fila(BaseHTTPRequestHandler):
    server_version = "FinartMontagem/1.0"

    def _responder(self, corpo, tipo="text/html; charset=utf-8", codigo=200):
        dados = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        # a fila muda enquanto a equipe trabalha: pagina guardada em cache
        # mostraria trabalho que outra pessoa ja pegou
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        partido = urllib.parse.urlsplit(self.path)
        caminho = partido.path.rstrip("/") or "/"
        pedido = urllib.parse.parse_qs(partido.query)
        try:
            if caminho == "/andamento":
                # A BARRA. Pergunta barata de proposito: so le um
                # dicionario na memoria, sem tocar em disco nem em rede.
                # A tela chama isto uma vez por segundo, e pode haver
                # mais de uma tela aberta.
                self._responder(
                    json.dumps(andamento((pedido.get("id") or [""])[0]),
                               ensure_ascii=False),
                    tipo="application/json; charset=utf-8")
            elif caminho == "/painel":
                # o nome vem de fora, e NAO e juntado a caminho nenhum: o
                # modulo o procura na fila, e so acha o que esta esperando
                # montagem. Ver montagem.dados_do_painel.
                nome = (pedido.get("arquivo") or [None])[0]
                self._responder(pagina_do_painel(
                    montagem.dados_do_painel(nome)))
            elif caminho in ("/", "/fila"):
                # PREPARA ANTES DE OLHAR: cria a pasta do dia e os dois
                # portoes se ainda nao existirem. Ver montagem.preparar_o_dia
                # - o vigia faz o mesmo, e quem chegar primeiro cria.
                portao, erro = montagem.preparar_o_dia()
                tem = montagem.portao_existe(portao)
                self._responder(pagina_da_fila(
                    montagem.fila_medida(portao) if tem else [],
                    portao, tem_portao=tem, erro_das_pastas=erro,
                    revisao=montagem.esperando_revisao()))
            elif caminho == "/historico":
                # O QUE SE PEDE VEM DO ENDERECO, e o endereco e digitado
                # por gente. O modulo ja aperta a janela; aqui se descobre
                # o que ele APERTOU, para a tela nao se rotular com um
                # periodo que nao e o que ela esta mostrando.
                pedida = (pedido.get("dia") or [None])[0]
                dia = pedida if montagem.entende_a_data(pedida) else None
                try:
                    dias = int((pedido.get("dias") or [7])[0])
                except (TypeError, ValueError):
                    dias = 7
                dias = max(montagem.MENOS_DIAS,
                           min(montagem.MAIS_DIAS, dias))
                self._responder(pagina_do_historico(
                    montagem.historico(dias=dias, dia=dia), dia=dia,
                    dias=dias,
                    data_nao_entendida=pedida if (pedida and not dia)
                    else None))
            elif caminho == "/conversa":
                self._responder(PAGINA_DA_CONVERSA)
            elif caminho == "/fila.json":
                portao, erro = montagem.preparar_o_dia()
                self._responder(
                    json.dumps({"portao": portao,
                                "tem_portao": montagem.portao_existe(portao),
                                "erro_das_pastas": erro,
                                "fila": montagem.fila_medida(portao),
                                "revisao": montagem.esperando_revisao()},
                               ensure_ascii=False, indent=1),
                    tipo="application/json; charset=utf-8")
            else:
                self._responder(pagina_nao_achei(), codigo=404)
        except Exception as e:
            # UM PEDIDO ESTRANHO NAO DERRUBA A TELA DA EQUIPE. O
            # ThreadingHTTPServer sobreviveria de qualquer jeito, mas quem
            # esta olhando veria a aba morrer sem explicacao.
            log("MONTAGEM: erro atendendo '%s' (%s)"
                % (self.path, str(e)[:120]), alerta=True)
            try:
                self._responder(
                    "<!doctype html><meta charset=utf-8><p>Nao consegui "
                    "montar esta pagina: %s</p><p>Atualize. Continuando, "
                    "chame quem cuida da FIA.</p>" % html.escape(str(e)[:200]),
                    codigo=500)
            except Exception:
                pass

    def do_POST(self):
        """
        O botao de montar. A tela manda a ORDEM e recebe o relato.

        NADA DE REGRA AQUI: o que este metodo faz e ler o JSON e chamar
        montagem.executar. As travas - nao gravar na PARA CTP, conferir a
        pinca no arquivo que saiu, tirar o original do portao - moram no
        modulo, onde os testes as alcancam sem subir socket.
        """
        caminho = urllib.parse.urlsplit(self.path).path.rstrip("/") or "/"
        if caminho == "/conversa":
            self._conversar()
            return
        if caminho not in ("/montar", "/aprovar", "/publicar",
                           "/refazer", "/limpar-revisao", "/reiniciar"):
            self._responder(json.dumps({"feito": False,
                                        "porque": "nao conheco este pedido"}),
                            tipo="application/json; charset=utf-8",
                            codigo=404)
            return
        try:
            quantos = int(self.headers.get("Content-Length") or 0)
            # UM TETO, porque o corpo vem de fora: a ordem tem algumas
            # dezenas de bytes, e ler sem limite deixa qualquer um encher
            # a memoria desta maquina.
            # NEGATIVO TAMBEM NAO PASSA: rfile.read(-1) le ate o fim, e o
            # teto que este bloco existe para ter deixaria de existir por
            # um cabecalho escrito a mao.
            if quantos < 0 or quantos > 64 * 1024:
                raise ValueError("ordem de tamanho invalido")
            pedido = json.loads(self.rfile.read(quantos).decode("utf-8"))
            if not isinstance(pedido, dict):
                raise ValueError("o pedido tem de ser um objeto")
            if caminho == "/aprovar":
                relato = montagem.aprovar(pedido.get("arquivo"),
                                          pedido.get("quem"))
            elif caminho == "/publicar":
                relato = montagem.publicar(pedido.get("arquivo"))
            elif caminho == "/refazer":
                relato = montagem.refazer(pedido.get("arquivo"),
                                          pedido.get("quem"))
            elif caminho == "/limpar-revisao":
                relato = montagem.limpar_revisao(pedido.get("quem"))
            elif caminho == "/reiniciar":
                # a unica rota que nao passa pelo montagem.py: ela
                # mexe nESTE processo, e nao na pasta do dia
                relato = reiniciar_a_fila()
            else:
                # O ID VEM DA TELA - ver _comecar_o_andamento. Nao vindo,
                # a montagem corre igual e so nao ha barra: o andamento e
                # enfeite, e um pedido antigo (ou um teste) nao pode
                # deixar de montar por falta dele.
                ident = _comecar_o_andamento(pedido.get("id"),
                                             pedido.get("arquivo"))
                relato = None
                try:
                    relato = montagem.executar(
                        pedido,
                        avisar=_anotar_o_andamento(ident) if ident else None)
                finally:
                    # NO finally, e nao depois: o executar levanta em
                    # alguns caminhos, e uma ficha que nunca termina
                    # deixa a barra girando para sempre na tela de quem
                    # ja levou a recusa. Levantando, relato fica None - e
                    # e isso mesmo que a ficha deve dizer.
                    if ident:
                        _acabar_o_andamento(ident,
                                            (relato or {}).get("feito"),
                                            (relato or {}).get("porque", ""))
        except Exception as e:
            log("MONTAGEM: erro em '%s' (%s)" % (caminho, str(e)[:150]),
                alerta=True)
            relato = {"feito": False, "passos": [],
                      "porque": "nao consegui ler o pedido: %s" % str(e)[:200]}
        # o caminho da montagem nao interessa a tela, e o relato do motor
        # tem objetos que nao viram JSON
        magro = {"feito": relato.get("feito", False),
                 "passos": relato.get("passos") or [],
                 "porque": relato.get("porque") or "",
                 "atencao": relato.get("atencao"),
                 # o refazer diz POR ONDE recomecar; sem isso a tela
                 # limparia a linha e deixaria a pessoa procurando
                 "ir_para": relato.get("ir_para"),
                 "pdf": relato.get("pdf"),
                 "montagem": (os.path.basename(relato["montagem"])
                              if relato.get("montagem") else None)}
        self._responder(json.dumps(magro, ensure_ascii=False),
                        tipo="application/json; charset=utf-8",
                        codigo=200 if magro["feito"] else 409)

    def _conversar(self):
        """
        Uma pergunta para a FIA. Fora do do_POST da montagem de proposito:
        o relato de la tem outro formato, e a conversa nao toca em nada
        do montagem.py.

        A resposta demora alguns segundos - o Claude pensa e le arquivo.
        O ThreadingHTTPServer atende cada pedido na sua linha, entao a
        fila da montagem nao espera por isso.
        """
        try:
            quantos = int(self.headers.get("Content-Length") or 0)
            # o historico cresce com a conversa, mas o conversa.py so usa
            # as ultimas mensagens, podadas; 256 KB sobra
            if quantos < 0 or quantos > 256 * 1024:
                raise ValueError("pedido de tamanho invalido")
            pedido = json.loads(self.rfile.read(quantos).decode("utf-8"))
            if not isinstance(pedido, dict):
                raise ValueError("o pedido tem de ser um objeto")
            resposta = conversa.responder(pedido.get("historico"))
        except Exception as e:
            resposta = {"resposta": "Nao entendi o pedido: %s" % str(e)[:150],
                        "erro": True}
        self._responder(json.dumps(resposta, ensure_ascii=False),
                        tipo="application/json; charset=utf-8")

    def log_message(self, formato, *args):
        # o padrao escreve no stderr, uma linha por pedido - inclusive
        # pelos do favicon. O log da casa e o log do dia, e enche-lo com
        # isso esconderia o que importa
        pass


def _enderecos_para_a_equipe():
    """Como a equipe chega nesta tela, do PC dela."""
    nomes = []
    try:
        maquina = socket.gethostname()
        nomes.append("http://%s:%d/" % (maquina, PORTA))
        nomes.append("http://%s:%d/" % (socket.gethostbyname(maquina), PORTA))
    except OSError:
        pass
    nomes.append("http://localhost:%d/   (nesta maquina)" % PORTA)
    return nomes


def esta_na_maquina_certa():
    """
    (pode_subir, recado). So o SERVIDOR_DA_MONTAGEM sobe a fila.

    Dois servidores no ar nao se anunciam um ao outro: cada um atende
    quem digitar o endereco dele, e os dois escrevem no MESMO registro,
    na MESMA pasta de rede. Montagem feita num, revisao procurada no
    outro - e foi o que aconteceu duas vezes nesta semana.

    E o VS Code sobe a fila sozinho ao abrir a pasta. Basta alguem abrir
    o projeto em outra maquina para nascer um segundo servidor sem
    ninguem pedir; por isso isto e trava, e nao combinado.

    O FIA_MONTAGEM_AQUI=1 destranca, para quem precisar levantar a fila
    fora do servidor de proposito - mudar de maquina, testar, socorrer
    um dia em que o servidor esta fora. Quem usa sabe que esta fazendo
    o segundo.
    """
    from .config import SERVIDOR_DA_MONTAGEM
    if not SERVIDOR_DA_MONTAGEM:
        return True, ""
    if os.environ.get("FIA_MONTAGEM_AQUI") == "1":
        return True, ("ATENCAO: subindo a fila FORA do servidor (%s), "
                      "porque FIA_MONTAGEM_AQUI=1. Havendo outro no ar, "
                      "sao DOIS mexendo na mesma pasta."
                      % SERVIDOR_DA_MONTAGEM)
    aqui = (os.environ.get("COMPUTERNAME") or "").strip().upper()
    if aqui == SERVIDOR_DA_MONTAGEM.strip().upper():
        return True, ""
    return False, (
        "A fila da montagem roda em UMA maquina so, e esta e a '%s'.\n"
        "   Esta aqui e a '%s', entao nao subo: dois servidores escrevem\n"
        "   no mesmo registro e na mesma pasta, e ninguem sabe qual vale.\n"
        "\n"
        "   Para usar a fila, abra   http://%s:%d/\n"
        "   ou o atalho 'MONTAGEM AMERICA - abrir aqui.html', no X:.\n"
        "\n"
        "   Se for mesmo para levantar uma aqui, ponha FIA_MONTAGEM_AQUI=1\n"
        "   no ambiente - mas saiba que serao dois."
        % (SERVIDOR_DA_MONTAGEM, aqui or "(sem nome)",
           SERVIDOR_DA_MONTAGEM, PORTA))


def main():
    pode, recado = esta_na_maquina_certa()
    if not pode:
        print("")
        print(recado)
        return 2
    if recado:
        print("")
        print(recado)
        log(recado.splitlines()[0], alerta=True)

    # O RETRATO VEM ANTES DE ABRIR A PORTA: dali em diante, qualquer .py
    # que mudar no disco esta na frente do que esta na memoria desta
    # janela, e a tela passa a dizer isso a quem for montar.
    _guardar_o_retrato()

    # ESPERAR A PORTA, quando quem subiu foi o proprio reinicio.
    #
    # O servidor que se reinicia lanca o filho e SO ENTAO se fecha - e
    # por um instante os dois existem, com a porta ainda presa pelo pai.
    # Sem esta espera o filho morre na largada dizendo 'porta ocupada',
    # e a fila fica fora do ar justamente por causa do botao que devia
    # consertar.
    espera = int(os.environ.get("FIA_ESPERAR_PORTA") or 0)
    servidor, ultimo = None, None
    ate = time.time() + espera
    while True:
        try:
            servidor = ThreadingHTTPServer((ENDERECO, PORTA), Fila)
            break
        except OSError as e:
            ultimo = e
            if time.time() >= ate:
                break
            time.sleep(0.4)

    if servidor is None:
        # PORTA OCUPADA e o caso comum: alguem abriu duas vezes. Dizer
        # qual e o erro poupa o susto de achar que o programa quebrou.
        print("")
        print("Nao consegui abrir a porta %d: %s" % (PORTA, ultimo))
        print("Ja ha um servidor da montagem rodando nesta maquina? "
              "Feche o outro, ou troque a PORTA_DA_MONTAGEM no "
              "config_local.py.")
        return 1

    log("MONTAGEM: fila no ar na porta %d" % PORTA)
    print("")
    print("  A FILA DA MONTAGEM ESTA NO AR. Abra do seu PC:")
    for onde in _enderecos_para_a_equipe():
        print("     %s" % onde)
    print("")
    print("  Nao abrindo de outro PC, o Windows esta barrando a porta.")
    print("  Rode uma vez, como administrador:")
    print("     ferramentas%sliberar_montagem_no_defender.ps1" % os.sep)
    print("")
    print("  Para parar: Ctrl+C.")
    print("")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("")
        log("MONTAGEM: fila fora do ar (parada por quem estava aqui)")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
