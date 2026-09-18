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
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import montagem
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
</script>
"""


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
    frente e o verso, e isso a casa sabe montar; TRES OU MAIS ninguem
    adivinha - a tela mostra e pergunta.
    """
    quantas = item.get("paginas")
    if not quantas or quantas < 3:
        return ""
    return ('<tr class="aviso"><td></td><td colspan="5">%d páginas — a '
            'gravadora não puxa múltiplas páginas, e eu não escolho quais '
            'montar. Separe as que vão para a chapa, ou monte uma de cada '
            'vez.</td></tr>' % quantas)


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


def _moldura(cabecalho, corpo, portao=None, depois=""):
    return (
        "<!doctype html><html lang=pt-br><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width, initial-scale=1'>"
        "<title>Montagem AMERICA - o que falta</title>"
        "<style>%s</style></head><body>"
        "<header><h1>Montagem AMERICA</h1><p>%s</p></header>"
        "<main>%s%s</main>"
        "<footer>portao: <code>%s</code> · "
        '<a href="/historico">histórico da semana</a></footer>'
        "%s</body></html>"
        % (ESTILO, html.escape(cabecalho), corpo, depois,
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

    return (
        '<tr><td class="arquivo">%s</td><td>%s</td>'
        '<td class="acao"><button class="aprovar" data-arquivo="%s">'
        'Aprovar e mandar para a PARA CTP</button></td></tr>%s'
        % (html.escape(item.get("arquivo") or "?"),
           html.escape(" · ".join(de_onde)),
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
    return (
        '<h2>Esperando revisão <span class="quantos">%d</span></h2>'
        '<p class="dica">Abra a montagem na pasta do dia, confira, e só '
        'então aprove. A mudança de pasta <b>é</b> o aprovado — dali em '
        'diante a FIA abre a OS, imprime a prova e grava a chapa.</p>'
        '<table><thead><tr><th>montagem</th><th>de onde veio</th>'
        '<th></th></tr></thead><tbody>%s</tbody></table>'
        % (len(itens), "".join(_linha_de_revisao(i) for i in itens)))


def pagina_da_fila(itens, portao=None, tem_portao=True, revisao=None):
    """
    O HTML da fila. Recebe a fila medida e devolve texto.

    'tem_portao' separa duas coisas que a tela confundia, e a confusao
    custaria uma manha: 'a equipe montou tudo' e 'ninguem criou a pasta
    ainda'. A pasta do dia e nova todo dia e o portao e criado por gente
    - numa manha em que ninguem o criou, a fila mostrava vazio e a equipe
    iria embora achando que nao havia trabalho.
    """
    if not tem_portao:
        return _moldura(
            "a pasta do portao ainda nao existe hoje",
            '<div class="vazio"><strong>A pasta "%s" nao existe na pasta '
            'do dia.</strong>Ninguem a criou ainda - e ela nao se cria '
            'sozinha. Crie a pasta na pasta do dia da AMERICA e ponha nela '
            'o que veio por montar.<p class="erro">Enquanto ela nao '
            'existir, nao da para saber se ha trabalho esperando.</p></div>'
            % html.escape(montagem.PORTAO), portao,
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
            if caminho == "/painel":
                # o nome vem de fora, e NAO e juntado a caminho nenhum: o
                # modulo o procura na fila, e so acha o que esta esperando
                # montagem. Ver montagem.dados_do_painel.
                nome = (pedido.get("arquivo") or [None])[0]
                self._responder(pagina_do_painel(
                    montagem.dados_do_painel(nome)))
            elif caminho in ("/", "/fila"):
                _, portao = montagem.pastas_da_montagem()
                tem = montagem.portao_existe(portao)
                self._responder(pagina_da_fila(
                    montagem.fila_medida(portao) if tem else [],
                    portao, tem_portao=tem,
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
            elif caminho == "/fila.json":
                _, portao = montagem.pastas_da_montagem()
                self._responder(
                    json.dumps({"portao": portao,
                                "tem_portao": montagem.portao_existe(portao),
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
        if caminho not in ("/montar", "/aprovar", "/publicar"):
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
            else:
                relato = montagem.executar(pedido)
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
                 "pdf": relato.get("pdf"),
                 "montagem": (os.path.basename(relato["montagem"])
                              if relato.get("montagem") else None)}
        self._responder(json.dumps(magro, ensure_ascii=False),
                        tipo="application/json; charset=utf-8",
                        codigo=200 if magro["feito"] else 409)

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


def main():
    try:
        servidor = ThreadingHTTPServer((ENDERECO, PORTA), Fila)
    except OSError as e:
        # PORTA OCUPADA e o caso comum: alguem abriu duas vezes. Dizer
        # qual e o erro poupa o susto de achar que o programa quebrou.
        print("")
        print("Nao consegui abrir a porta %d: %s" % (PORTA, e))
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
