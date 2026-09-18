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
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import montagem
from .config import ENDERECO_DA_MONTAGEM, PORTA_DA_MONTAGEM
from .utils import log

ENDERECO = ENDERECO_DA_MONTAGEM
PORTA = PORTA_DA_MONTAGEM


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
  .vazio { background: #fff; padding: 40px 28px; text-align: center;
           color: #5c6370; box-shadow: 0 1px 2px rgba(0,0,0,.12) }
  .vazio strong { display: block; font-size: 17px; color: #1c1e21;
                  margin-bottom: 6px }
  footer { padding: 0 28px 28px; color: #8a9099; font-size: 12px }
  code { background: #e9ebee; padding: 1px 5px; border-radius: 3px }
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


def _linha(item):
    if item.get("erro"):
        return (
            '<tr><td class="arquivo">%s</td>'
            '<td colspan="5" class="erro">nao consegui medir: %s</td></tr>'
            % (html.escape(item.get("arquivo") or "?"),
               html.escape(item["erro"])))
    return (
        '<tr><td class="arquivo">%s</td>'
        '<td class="numero">%s x %s mm</td>'
        '<td>%s</td>'
        '<td class="numero">%s</td>'
        '<td>%s</td>'
        '<td>%s</td></tr>%s'
        % (html.escape(item.get("arquivo") or "?"),
           _mm(item.get("largura")), _mm(item.get("altura")),
           html.escape(_cor(item)),
           "-" if item.get("paginas") is None else item["paginas"],
           _marca(item), _sangria(item), _aviso_da_sangria(item)))


def _moldura(cabecalho, corpo, portao=None):
    return (
        "<!doctype html><html lang=pt-br><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width, initial-scale=1'>"
        "<title>Montagem AMERICA - o que falta</title>"
        "<style>%s</style></head><body>"
        "<header><h1>Montagem AMERICA</h1><p>%s</p></header>"
        "<main>%s</main>"
        "<footer>portao: <code>%s</code></footer>"
        "</body></html>"
        % (ESTILO, html.escape(cabecalho), corpo,
           html.escape(portao or "(nao achei a pasta do dia)")))


def pagina_da_fila(itens, portao=None, tem_portao=True):
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
            % html.escape(montagem.PORTAO), portao)

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

    return _moldura(quantos, corpo, portao)


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
        caminho = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if caminho in ("/", "/fila"):
                _, portao = montagem.pastas_da_montagem()
                tem = montagem.portao_existe(portao)
                self._responder(pagina_da_fila(
                    montagem.fila_medida(portao) if tem else [],
                    portao, tem_portao=tem))
            elif caminho == "/fila.json":
                _, portao = montagem.pastas_da_montagem()
                self._responder(
                    json.dumps({"portao": portao,
                                "tem_portao": montagem.portao_existe(portao),
                                "fila": montagem.fila_medida(portao)},
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
