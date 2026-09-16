# -*- coding: utf-8 -*-
r"""
TR_OS_SEM_NULO - deixa a OS voltar a gravar com campo de gente em branco.

O Firebird 1.5 nao cobrava os NOT NULL da OS no caminho que o Delphi usa.
O 2.0 cobra. Na manha de 16/09/2026, a manha seguinte a mudanca de
maquina, a grafica parou: toda gravacao de OS com o Vendedor em branco
morria com

    SQLCODE -625  validation error for column OSCVEN, value "*** null ***"

e a estacao mostrava so 'unknown ISC error 336397210', porque falta o
firebird.msg do lado do cliente. Entrou 1 OS no dia, contra 32 a 41 de
um dia normal.

Este gatilho troca nulo por zero nos campos onde zero JA E o valor de
todas as 19.749 OS que existem - ele nao inventa dado, reproduz o que o
banco ja tem.

O QUE ELE NAO TOCA, de proposito:

  OSCOD   - OS sem numero tem de falhar alto. Pior: o TR_OS_BEFORE faz
            'delete from mov where movnos = new.oscod', e um zero ali
            apagaria as 94 linhas de SALDO ANTERIOR, que moram em
            MOVNOS = 0. Seria o estoque inteiro pelos ares.
  OSCLI   - OS sem cliente nao e OS. Que continue recusando.

Posicao 0, como o TR_OS_BEFORE: a ordem entre os dois nao importa, porque
a validacao do NOT NULL so acontece depois que TODOS os BEFORE rodaram.

Desfazer: DROP TRIGGER TR_OS_SEM_NULO;
"""

import datetime
import sys

sys.path.insert(0, r"C:\PROJETO FECHAMENTO CHAPA\src")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from finart_ctp import gerempre as G

FONTE = """
CREATE TRIGGER TR_OS_SEM_NULO FOR OS
ACTIVE BEFORE INSERT OR UPDATE POSITION 0
AS
BEGIN
  IF (NEW.OSCVEN IS NULL)  THEN NEW.OSCVEN  = 0;
  IF (NEW.OSCOPER IS NULL) THEN NEW.OSCOPER = 0;
  IF (NEW.OSCCONF IS NULL) THEN NEW.OSCCONF = 0;
  IF (NEW.OSSIT IS NULL)   THEN NEW.OSSIT   = 0;
  IF (NEW.OSTIPO IS NULL)  THEN NEW.OSTIPO  = 0;
END
"""

BASE = dict(OSENTD=datetime.date(2026, 9, 16), OSECL=116, OSCLI=116,
            OSSIT=0, OSTIPO=0, OSRESP="ENSAIO", OSUSR_ALT=32,
            OSCVEN=0, OSCOPER=0, OSCCONF=0,
            OSTIT1="ENSAIO DO GATILHO", OSLAN1=1, OSCOR1=1, OSCOR11=0,
            OSESP1=11, OSUNIT1=35, OSVLU1=35, RBCHAPA1=0, RBCHAPAPRO1=1)
for _i in (2, 3, 4):
    BASE.update({"OSVLU%d" % _i: 0, "OSLAN%d" % _i: 0, "OSCOR%d" % _i: 0,
                 "OSCOR%d%d" % (_i, _i): 0, "OSESP%d" % _i: 0,
                 "RBCHAPA%d" % _i: 0, "RBCHAPAPRO%d" % _i: 0})


def razao(cur):
    cur.execute("SELECT CHACOD, CHACLI, CHAQTD FROM CHA")
    s = {(a, b): (c or 0) for a, b, c in cur.fetchall()}
    cur.execute("SELECT MOVCHA, MOVCLI, SUM(MOVQTD) FROM MOV "
                "GROUP BY MOVCHA, MOVCLI")
    m = {(a, b): (c or 0) for a, b, c in cur.fetchall()}
    return s, [k for k, q in s.items() if q != m.get(k, 0)]


def tentar(con, cur, rotulo, extra, ver=None):
    campos = dict(BASE)
    campos.update(extra)
    cur.execute("SELECT GEN_ID(GEN_OSCOD_ID, 0) FROM RDB$DATABASE")
    campos["OSCOD"] = cur.fetchone()[0] + 900000
    try:
        cur.execute("INSERT INTO OS (%s) VALUES (%s)"
                    % (", ".join(campos), ", ".join("?" * len(campos))),
                    list(campos.values()))
        extra_txt = ""
        if ver:
            cur.execute("SELECT %s FROM OS WHERE OSCOD = ?"
                        % ", ".join(ver), (campos["OSCOD"],))
            extra_txt = "  gravou %s" % dict(zip(ver, cur.fetchone()))
        cur.execute("SELECT MOVCHA, MOVCLI, MOVQTD FROM MOV WHERE MOVNOS = ?",
                    (campos["OSCOD"],))
        print("   %-38s PASSOU  mov %s%s"
              % (rotulo, cur.fetchall(), extra_txt))
    except Exception as e:
        m = str(e).replace("\n", " ")
        i = m.find("validation error")
        print("   %-38s RECUSOU %s" % (rotulo, m[i:i + 58] if i > 0 else m[:58]))
    finally:
        con.rollback()


def main():
    con = G.conectar()
    cur = con.cursor()

    antes, ruins = razao(cur)
    print("razao antes: %d chapas, %d divergencia(s)" % (len(antes), len(ruins)))
    if ruins:
        print("PAREI: o razao ja nao batia."); con.close(); return 1

    print("\n== antes do gatilho ==")
    tentar(con, cur, "vendedor em branco", {"OSCVEN": None})

    print("\n== criando o gatilho ==")
    cur.execute(FONTE)
    con.commit()
    cur.execute("SELECT CAST(RDB$TRIGGER_NAME AS VARCHAR(31)), "
                "RDB$TRIGGER_TYPE, RDB$TRIGGER_SEQUENCE, RDB$TRIGGER_INACTIVE "
                "FROM RDB$TRIGGERS WHERE RDB$RELATION_NAME = 'OS' "
                "ORDER BY RDB$TRIGGER_SEQUENCE")
    for L in cur.fetchall():
        print("   %-24s tipo %s posicao %s inativo %s" % L)

    print("\n== depois do gatilho ==")
    tentar(con, cur, "vendedor em branco", {"OSCVEN": None},
           ver=["OSCVEN", "OSCOPER", "OSCCONF"])
    tentar(con, cur, "operador e conferente em branco",
           {"OSCOPER": None, "OSCCONF": None}, ver=["OSCOPER", "OSCCONF"])
    tentar(con, cur, "situacao e tipo em branco",
           {"OSSIT": None, "OSTIPO": None}, ver=["OSSIT", "OSTIPO"])
    tentar(con, cur, "tudo preenchido (como a FIA grava)", {},
           ver=["OSCVEN", "OSSIT"])
    print("   -- e o que deve CONTINUAR recusando --")
    tentar(con, cur, "cliente em branco", {"OSCLI": None})

    depois, ruins = razao(cur)
    mudou = [k for k in antes if depois.get(k) != antes[k]]
    print("\nrazao depois: %d chapas, %d divergencia(s), %d saldo(s) mudado(s)"
          % (len(depois), len(ruins), len(mudou)))
    cur.execute("SELECT COUNT(*) FROM MOV WHERE MOVNOS = 0")
    print("linhas de SALDO ANTERIOR intactas: %s" % cur.fetchone()[0])
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
