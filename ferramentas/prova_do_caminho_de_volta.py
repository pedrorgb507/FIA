# -*- coding: utf-8 -*-
r"""Prova, NA PRODUCAO, que uma OS da FIA se desfaz e o estoque volta.

ISTO ESCREVE NO BANCO DA EMPRESA. Abre uma OS de mentira com UMA chapa
propria (a 12, estoque da Finart), confere que o estoque desceu, apaga,
e confere que voltou ao numero exato de antes. Por isso nao roda sem a
palavra na linha de comando:

    python ferramentas/prova_do_caminho_de_volta.py SIM-EU-QUERO

O que fica: um buraco na numeracao das OS. E normal - o proprio programa
deixa buracos quando um operador desiste no meio - e GEN_OSCOD_ID nao
recua.

Foi rodado uma vez, em 09/09/2026, e passou: estoque exatamente onde
estava. Fica guardado porque testar o caminho de volta DEPOIS de precisar
dele nao vale nada - e porque e daqui que se copia o jeito certo de
desfazer, se um dia a FIA abrir uma OS que nao devia:

    DELETE FROM MOV WHERE MOVNOS = <numero>     -- primeiro os movimentos
    DELETE FROM OS  WHERE OSCOD  = <numero>     -- depois a OS

Nessa ordem, e conferindo o saldo da chapa antes e depois. O gatilho
TR_MOV_AFT devolve a quantidade ao estoque ao apagar o movimento; apagar
a OS primeiro deixaria movimento orfao e o razao torto.
"""
import sys

sys.path.insert(0, r"C:\PROJETO FECHAMENTO CHAPA\src")

from finart_ctp import gerempre
from finart_ctp.config import GEREMPRE_DSN

CHAPA = 12          # 510X400 - 0,15, chapa propria da Finart
DONO = 0            # estoque da Finart
TITULO = "TESTE DA FIA 09/09 - PODE IGNORAR"


def p(t=""):
    sys.stdout.buffer.write((t + "\n").encode("utf-8", "replace"))


def saldo_e_razao(cur):
    cur.execute("SELECT CHAQTD FROM CHA WHERE CHACOD = ?", (CHAPA,))
    saldo = cur.fetchone()[0]
    cur.execute("SELECT SUM(MOVQTD) FROM MOV WHERE MOVCHA = ? AND MOVCLI = ?",
                (CHAPA, DONO))
    return saldo, (cur.fetchone()[0] or 0)


if "SIM-EU-QUERO" not in sys.argv:
    p("Este script ABRE UMA OS DE VERDADE e mexe no estoque, so para")
    p("provar que da para desfazer. Se e isso mesmo que voce quer:")
    p("")
    p("    python ferramentas/prova_do_caminho_de_volta.py SIM-EU-QUERO")
    sys.exit(1)

p("banco: %s" % GEREMPRE_DSN)
if "NeoGerempre" not in GEREMPRE_DSN:
    p("isto nao e a producao. Nada a provar aqui.")
    sys.exit(1)

con = gerempre.conectar()
cur = con.cursor()

antes, razao_antes = saldo_e_razao(cur)
p("chapa %d antes:  saldo %s, soma dos movimentos %s   %s"
  % (CHAPA, antes, razao_antes, "batendo" if antes == razao_antes else "TORTO"))
if antes != razao_antes:
    p("o razao ja nao batia antes de eu chegar. Nao mexo.")
    con.close()
    sys.exit(1)

# --- 1. abre ----------------------------------------------------------
servico = {"titulo": TITULO, "cliente": "VOPRIX", "chapa": [510, 400],
           "chapas": 1}
numero = gerempre.abrir_os([servico], con=con)
p("abri a OS %s, com 1 chapa" % numero)

depois, razao_depois = saldo_e_razao(cur)
cur.execute("SELECT MOVCOD, MOVQTD, MOVCLI FROM MOV WHERE MOVNOS = ?",
            (numero,))
movimentos = cur.fetchall()
p("   movimentos gerados: %s"
  % ", ".join("MOVCOD %s qtd %s cliente %s" % m for m in movimentos))
p("   saldo agora: %s  (era %s, andou %s)" % (depois, antes, depois - antes))
if depois != antes - 1:
    p("   o estoque NAO desceu 1. Vou apagar assim mesmo e conferir.")

# --- 2. apaga ---------------------------------------------------------
cur.execute("DELETE FROM MOV WHERE MOVNOS = ?", (numero,))
apagados = cur.rowcount
cur.execute("DELETE FROM OS WHERE OSCOD = ?", (numero,))
con.commit()
p("apaguei %d movimento(s) e a OS %s" % (apagados, numero))

# --- 3. confere numa ligacao nova -------------------------------------
con.close()
con2 = gerempre.conectar()
c2 = con2.cursor()
final, razao_final = saldo_e_razao(c2)
c2.execute("SELECT COUNT(*) FROM OS WHERE OSCOD = ?", (numero,))
sobrou_os = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM MOV WHERE MOVNOS = ?", (numero,))
sobrou_mov = c2.fetchone()[0]

p()
p("depois de desfazer:")
p("   a OS %s existe? %s" % (numero, "SIM - PROBLEMA" if sobrou_os else "nao"))
p("   sobrou movimento dela? %s" % ("SIM - PROBLEMA" if sobrou_mov else "nao"))
p("   saldo da chapa %d: %s   (era %s antes de tudo)" % (CHAPA, final, antes))
p("   soma dos movimentos: %s" % razao_final)
p()
if final == antes and razao_final == razao_antes and not sobrou_os \
        and not sobrou_mov:
    p("O CAMINHO DE VOLTA FUNCIONA. Estoque exatamente onde estava.")
else:
    p("ALGO NAO VOLTOU. Confira a mao antes de seguir.")
p("fica so um buraco na numeracao, no numero %s - e normal." % numero)
con2.close()
