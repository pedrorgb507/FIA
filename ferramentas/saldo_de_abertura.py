# -*- coding: utf-8 -*-
r"""
Zeramento do movimento anterior a 06/06/2024, com SALDO DE ABERTURA.

A tabela OS so lembra de 06/06/2024 para ca. A MOV lembra de 02/04/2015,
e as 105.848 linhas anteriores ao corte apontam, TODAS, para OS que nao
existe mais - conferido: 105.848 de 105.848. Como historia, nao ligam em
nada. Como estoque, carregam saldo: a chapa 88 da PRIME tem +44 ali, de
chapas que o cliente entregou em maio de 2024.

Entao nao se apaga e pronto. Para cada par (chapa, dono):

    1. soma-se tudo o que ha antes do corte;
    2. apagam-se essas linhas;
    3. lanca-se UMA linha com essa soma, em 05/06/2024.

O gatilho faz o resto sozinho, e o resultado e neutro:

    TR_MOV_AFTER  ao apagar:  chaqtd = chaqtd - old.movqtd
    TR_MOV_BEFORE ao inserir: chaqtd = chaqtd + new.movqtd

Apagar tira a soma; inserir devolve a mesma soma. NENHUM saldo muda.

TUDO NUMA TRANSACAO SO. No fim, cada linha da CHA e comparada com o
retrato tirado antes, e o razao e refeito dos dois lados. Um numero
diferente que seja, e rollback - nada e gravado.
"""

import datetime
import io
import os
import sys
import time

# O src sai DAQUI, e nao de um caminho escrito a mao: a pasta do
# projeto ja mudou de nome uma vez (era PROJETO AUTOMATIZACAO
# SOLIDA) e mudou de novo em 24/09/2026. Caminho absoluto numa
# ferramenta quebra calado no dia da mudanca.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from finart_ctp import gerempre as G

CORTE = datetime.date(2024, 6, 6)
DIA_DA_ABERTURA = datetime.date(2024, 6, 5)
OBS = "SALDO ANTERIOR ATE 05/06/2024"
FUNCIONARIO = 32                      # FINART (FIA)
SEM_OS = 0


def retrato(cur):
    """{(chapa, dono): saldo} de TODAS as chapas, vivas ou nao."""
    cur.execute("SELECT CHACOD, CHACLI, CHAQTD FROM CHA")
    return {(a, b): (c or 0) for a, b, c in cur.fetchall()}


def razao(cur):
    """{(chapa, dono): soma dos movimentos}."""
    cur.execute("SELECT MOVCHA, MOVCLI, SUM(MOVQTD) FROM MOV "
                "GROUP BY MOVCHA, MOVCLI")
    return {(a, b): (c or 0) for a, b, c in cur.fetchall()}


def main():
    con = G.conectar()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM MOV WHERE MOVDIA IS NULL")
    sem_data = cur.fetchone()[0]
    print("linhas de MOV sem data: %d (ficam onde estao)" % sem_data)

    antes = retrato(cur)
    razao_antes = razao(cur)
    ruins = [k for k, v in antes.items() if v != razao_antes.get(k, 0)]
    print("razao ANTES: %d chapas, %d divergencia(s)" % (len(antes), len(ruins)))
    if ruins:
        print("PAREI: o razao ja nao batia antes de eu mexer: %s" % ruins[:8])
        con.close()
        return 1

    cur.execute("SELECT MOVCHA, MOVCLI, SUM(MOVQTD), COUNT(*) FROM MOV "
                "WHERE MOVDIA < ? GROUP BY MOVCHA, MOVCLI", (CORTE,))
    aberturas = [(cha, cli, int(soma or 0), n) for cha, cli, soma, n
                 in cur.fetchall()]
    total_linhas = sum(n for _, _, _, n in aberturas)

    print("\n== SALDOS DE ABERTURA a lancar em %s ==" % DIA_DA_ABERTURA)
    print("   %-6s %-6s %10s %10s" % ("chapa", "dono", "linhas", "saldo"))
    for cha, cli, soma, n in sorted(aberturas):
        print("   %-6s %-6s %10d %+10d" % (cha, cli, n, soma))
    print("   %d pares, %d linhas antigas viram %d linhas"
          % (len(aberturas), total_linhas, len(aberturas)))

    print("\n== apagando ==", flush=True)
    t = time.time()
    cur.execute("DELETE FROM MOV WHERE MOVDIA < ?", (CORTE,))
    print("   apagadas em %.1fs" % (time.time() - t), flush=True)

    print("== lancando as aberturas ==", flush=True)
    t = time.time()
    for cha, cli, soma, _ in aberturas:
        entrada = soma if soma > 0 else 0
        saida = -soma if soma < 0 else 0
        cur.execute(
            "INSERT INTO MOV (MOVCOD, MOVDIA, MOVCLI, MOVCHA, MOVQTD, "
            "MOVENT, MOVSDA, MOVNOS, MOVOBS, MOVFUN) VALUES "
            "(GEN_ID(GEN_MOVCOD_ID, 1), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (DIA_DA_ABERTURA, cli, cha, soma, entrada, saida, SEM_OS, OBS,
             FUNCIONARIO))
    print("   %d lancadas em %.1fs" % (len(aberturas), time.time() - t),
          flush=True)

    print("\n== conferencia, antes de gravar ==")
    depois = retrato(cur)
    razao_depois = razao(cur)

    mudaram = [(k, antes[k], depois.get(k)) for k in antes
               if depois.get(k) != antes[k]]
    sumiram = [k for k in antes if k not in depois]
    novos = [k for k in depois if k not in antes]
    desencontro = [k for k, v in depois.items() if v != razao_depois.get(k, 0)]

    print("   saldos que mudaram : %d" % len(mudaram))
    print("   chapas que sumiram : %d" % len(sumiram))
    print("   chapas novas       : %d" % len(novos))
    print("   razao fora         : %d" % len(desencontro))
    cur.execute("SELECT COUNT(*) FROM MOV")
    print("   MOV agora          : %s linhas" % cur.fetchone()[0])

    if mudaram or sumiram or novos or desencontro:
        for k, a, d in mudaram[:12]:
            print("      chapa %s dono %s: %s -> %s" % (k[0], k[1], a, d))
        for k in desencontro[:12]:
            print("      razao chapa %s dono %s: CHA %s, MOV %s"
                  % (k[0], k[1], depois.get(k), razao_depois.get(k)))
        con.rollback()
        print("\n   ROLLBACK. Nada foi gravado.")
        con.close()
        return 1

    con.commit()
    print("\n   tudo bate. GRAVADO.")

    depois_do_commit = retrato(cur)
    iguais = sum(1 for k in antes if depois_do_commit.get(k) == antes[k])
    print("   relido do banco: %d de %d saldos identicos aos de antes"
          % (iguais, len(antes)))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
