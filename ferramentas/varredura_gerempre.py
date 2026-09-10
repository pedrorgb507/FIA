# -*- coding: utf-8 -*-
r"""
A planta do GEREMPRE, tirada do proprio banco. LEITURA SO.

Roda assim, e nao escreve nada:

    .venv\Scripts\python.exe ferramentas\varredura_gerempre.py C:\saida

A trava nao e disciplina minha: e o READ_COMMITED_RO do proprio Firebird,
que faz o SERVIDOR recusar escrita com SQLCODE -817. Antes de qualquer
leitura, o programa TENTA escrever de proposito - com um UPDATE que casa
uma linha, que e a unica forma de provar a trava (ver armadilha 7 da
skill) - e para na hora se a escrita passar.

Serve para duas coisas:

  - refazer a varredura de 10/09/2026 e ver O QUE MUDOU. A planta em
    references/banco.md e um retrato daquele dia, e retrato envelhece;
  - descobrir a planta de novo, se algum dia a documentacao se perder.

Despeja em arquivos, e nao na tela: sao 303 colunas e 104 linhas de PSQL.
"""

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from finart_ctp.config import (GEREMPRE_CLIENTE_DLL, GEREMPRE_DSN,
                               GEREMPRE_SENHA, GEREMPRE_USUARIO)

# O RDB$ guarda nome de metadado num campo que volta CORTADO EM 10 LETRAS
# por este cliente - 'GEN_OSCOD_ID' chega 'GEN_OSCOD_', e 'SP_ESTOQUE2'
# chega 'SP_ESTOQUE', igual ao 'SP_ESTOQUE' de verdade. O CAST devolve o
# nome inteiro. Sem ele, a varredura mente sem avisar.
NOME = "CAST(%s AS VARCHAR(31))"

TIPO = {7: "SMALLINT", 8: "INTEGER", 10: "FLOAT", 12: "DATE", 13: "TIME",
        14: "CHAR", 16: "BIGINT", 27: "DOUBLE", 35: "TIMESTAMP",
        37: "VARCHAR", 261: "BLOB", 40: "CSTRING", 45: "BLOB_ID"}

QUANDO = {1: "BEFORE INSERT", 2: "AFTER INSERT", 3: "BEFORE UPDATE",
          4: "AFTER UPDATE", 5: "BEFORE DELETE", 6: "AFTER DELETE",
          17: "BEFORE INSERT/UPDATE", 113: "BEFORE INSERT/UPDATE/DELETE"}


def texto(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("iso8859-1", "replace")
    if hasattr(v, "read"):
        return v.read().decode("iso8859-1", "replace")
    return str(v)


def abrir_travado():
    """Conexao que o SERVIDOR recusa escrever, e a prova disso."""
    import fdb
    if GEREMPRE_CLIENTE_DLL:
        fdb.load_api(GEREMPRE_CLIENTE_DLL)
    con = fdb.connect(dsn=GEREMPRE_DSN, user=GEREMPRE_USUARIO,
                      password=GEREMPRE_SENHA, charset="ISO8859_1",
                      isolation_level=fdb.ISOLATION_LEVEL_READ_COMMITED_RO)
    cur = con.cursor()
    try:
        # casa UMA linha de proposito: WHERE que nao acha nada devolve
        # sucesso sem tentar escrever, e o teste passaria sem provar nada
        cur.execute("UPDATE CHA SET CHAQTD = CHAQTD WHERE CHACOD = 98")
    except Exception as e:
        if "-817" in str(e) or "read-only" in str(e).lower():
            return con, cur
        raise SystemExit("escrita recusada por outro motivo: %s" % str(e)[:90])
    raise SystemExit("A TRAVA NAO PEGOU - o banco aceitou escrita. Parei.")


def main(saida):
    os.makedirs(saida, exist_ok=True)
    con, cur = abrir_travado()
    print("ligado em %s" % GEREMPRE_DSN)
    print("trava confirmada: o servidor recusou a escrita (-817)")

    def guardar(nome, linhas):
        io.open(os.path.join(saida, nome), "w",
                encoding="utf-8").write("\n".join(linhas))

    # ---- tabelas e contagem ----
    cur.execute("SELECT %s, RDB$VIEW_BLR FROM RDB$RELATIONS "
                "WHERE RDB$SYSTEM_FLAG = 0 OR RDB$SYSTEM_FLAG IS NULL "
                "ORDER BY 1" % (NOME % "RDB$RELATION_NAME"))
    tabelas, visoes = [], []
    for nome, view in cur.fetchall():
        (visoes if view is not None else tabelas).append(texto(nome).strip())

    linhas = {}
    for t in tabelas:
        cur.execute("SELECT COUNT(*) FROM %s" % t)
        linhas[t] = cur.fetchone()[0]

    # ---- colunas ----
    col, total_col = [], 0
    for t in tabelas + visoes:
        cur.execute("""SELECT %s, f.RDB$FIELD_TYPE, f.RDB$FIELD_LENGTH,
                              f.RDB$FIELD_SCALE, rf.RDB$NULL_FLAG
                       FROM RDB$RELATION_FIELDS rf
                       JOIN RDB$FIELDS f
                         ON f.RDB$FIELD_NAME = rf.RDB$FIELD_SOURCE
                       WHERE rf.RDB$RELATION_NAME = ?
                       ORDER BY rf.RDB$FIELD_POSITION"""
                    % (NOME % "rf.RDB$FIELD_NAME"), (t,))
        cs = cur.fetchall()
        total_col += len(cs)
        col.append("=== %s (%d colunas, %s linhas) ===" %
                   (t, len(cs), linhas.get(t, "-")))
        for c in cs:
            tp = TIPO.get(c[1], "tipo%s" % c[1])
            if tp in ("VARCHAR", "CHAR"):
                tp = "%s(%s)" % (tp, c[2])
            elif c[3]:
                tp = "%s(escala %d)" % (tp, c[3])
            col.append("    %-18s %-16s %s" % (texto(c[0]).strip(), tp,
                                               "NOT NULL" if c[4] else ""))
        col.append("")
    guardar("colunas.txt", col)

    # ---- gatilhos: a regra de negocio mora aqui ----
    cur.execute("""SELECT %s, %s, RDB$TRIGGER_TYPE, RDB$TRIGGER_INACTIVE,
                          RDB$TRIGGER_SOURCE
                   FROM RDB$TRIGGERS
                   WHERE RDB$SYSTEM_FLAG = 0 OR RDB$SYSTEM_FLAG IS NULL
                   ORDER BY 2, RDB$TRIGGER_SEQUENCE"""
                % (NOME % "RDB$TRIGGER_NAME", NOME % "RDB$RELATION_NAME"))
    gat, n_gat, n_psql = [], 0, 0
    for g in cur.fetchall():
        fonte = texto(g[4])
        n_gat += 1
        n_psql += len([l for l in fonte.splitlines() if l.strip()])
        gat.append("=== %s [%s] %s %s ===" %
                   (texto(g[0]).strip(), texto(g[1]).strip(),
                    QUANDO.get(g[2], "tipo %s" % g[2]),
                    "DESLIGADO" if g[3] else "ATIVO"))
        gat.append(fonte)
        gat.append("")
    guardar("gatilhos.txt", gat)

    # ---- procedimentos ----
    cur.execute("SELECT %s, RDB$PROCEDURE_SOURCE FROM RDB$PROCEDURES "
                "ORDER BY 1" % (NOME % "RDB$PROCEDURE_NAME"))
    proc, n_proc = [], 0
    for p in cur.fetchall():
        n_proc += 1
        proc.append("=== %s ===" % texto(p[0]).strip())
        proc.append(texto(p[1]))
        proc.append("")
    guardar("procedimentos.txt", proc)

    # ---- geradores, com o valor atual (incremento zero nao gasta numero) ----
    cur.execute("SELECT %s FROM RDB$GENERATORS "
                "WHERE RDB$SYSTEM_FLAG = 0 OR RDB$SYSTEM_FLAG IS NULL "
                "ORDER BY 1" % (NOME % "RDB$GENERATOR_NAME"))
    ger = []
    for (g,) in cur.fetchall():
        nome = texto(g).strip()
        try:
            cur.execute("SELECT GEN_ID(%s, 0) FROM RDB$DATABASE" % nome)
            ger.append("%-22s %s" % (nome, cur.fetchone()[0]))
        except Exception:
            ger.append("%-22s ?" % nome)
    guardar("geradores.txt", ger)

    # ---- o razao, que e o juiz de tudo ----
    cur.execute("""SELECT c.CHACOD, c.CHACLI, %s, c.CHAQTD,
                          (SELECT SUM(m.MOVQTD) FROM MOV m
                           WHERE m.MOVCHA = c.CHACOD
                             AND m.MOVCLI = c.CHACLI)
                   FROM CHA c""" % (NOME % "c.CHANOM"))
    bate, fora, razao = 0, [], []
    for cod, cli, nom, qtd, soma in cur.fetchall():
        if (qtd or 0) == (soma or 0):
            bate += 1
        else:
            fora.append((cod, cli, texto(nom).strip(), qtd, soma))
    razao.append("chapas que batem: %d | DIVERGENTES: %d" % (bate, len(fora)))
    for d in fora:
        razao.append("   chapa %s dono %s %-22s saldo=%s soma=%s" % d)
    guardar("razao.txt", razao)

    resumo = [
        "TABELAS: %d (%d com dado)" %
        (len(tabelas), len([t for t in tabelas if linhas.get(t)])),
        "COLUNAS: %d" % total_col,
        "GATILHOS: %d (%d linhas de PSQL)" % (n_gat, n_psql),
        "PROCEDIMENTOS: %d" % n_proc,
        "GERADORES: %d" % len(ger),
        "RAZAO: %d batem, %d divergentes" % (bate, len(fora)),
        "",
        "linhas por tabela:",
    ]
    for t in sorted(tabelas, key=lambda x: -linhas.get(x, 0)):
        resumo.append("   %-10s %9s" % (t, linhas.get(t)))
    guardar("resumo.txt", resumo)
    print("\n".join(resumo))
    print("\narquivos em %s" % saida)
    con.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("uso: varredura_gerempre.py <pasta de saida>")
    main(sys.argv[1])
