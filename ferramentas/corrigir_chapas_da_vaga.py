# -*- coding: utf-8 -*-
r"""
CORRIGE QUANTAS CHAPAS uma vaga da OS cobra. NAO E ROTINA.

    python ferramentas\corrigir_chapas_da_vaga.py <OS> <vaga> <chapas>
    python ferramentas\corrigir_chapas_da_vaga.py <OS> <vaga> <chapas> --gravar

Sem --gravar ele so OLHA: mostra a OS, o razao e o que faria.


POR QUE ISTO EXISTE

Em 21/09/2026 dois arquivos da AMERICA sairam em CMYK sendo de preto
puro - as cruzes de corte, coloridas e DENTRO do corte, contavam como
tinta. A OS 19860 cobrou 4 chapas em cada uma das vagas 3 e 4, onde devia
cobrar 1. A causa foi consertada no america.medir(); isto aqui conserta
o que ja tinha sido cobrado.

Nao havia como fazer isso pelo programa: a FIA sabe ABRIR e COMPLETAR
uma OS, e nao CORRIGIR uma. Quem corrigia era gente, pelo Delphi.


O QUE ELE ESCREVE, e e pouco de proposito

Tres campos da vaga, os mesmos que o montar_vaga escreve:

    OSLAN<n>   quantas chapas
    OSVLU<n>   o valor da vaga = preco unitario x chapas
    OSVTOT     o total da OS, somado das quatro vagas

Nao mexe no titulo, na chapa, no dono nem no tipo. Se a chapa estiver
errada, isso e outro conserto e nao e este.


O QUE ACONTECE NO BANCO, e nao e pouco

O UPDATE dispara o TR_OS_BEFO, que APAGA todos os movimentos desta OS e
os REFAZ a partir das quatro vagas. Ou seja: o estoque inteiro da OS e
rebobinado e reproduzido. As vagas que nao se toca saem iguais; a que se
corrige sai com a quantidade nova.

Por isso ele confere o RAZAO dos dois lados - antes e depois - e diz de
quanto o saldo andou. Saldo que ande diferente do esperado e sinal de
que outra coisa aconteceu junto, e ai a conferencia salva.


O QUE ELE RECUSA

OS ENTREGUE (OSSIT = 1) ou CANCELADA (OSSIT = 2). Numa entregue o
protocolo ja saiu e o faturamento ja correu; numa cancelada o gatilho
toma o outro caminho, o que DEVOLVE estoque. Corrigir qualquer das duas
por aqui mexeria em coisa que ja fechou - quem faz isso e gente,
olhando.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from finart_ctp import gerempre                              # noqa: E402

VAGAS = 4


def _um_valor(cur, sql, args=()):
    gerempre.perguntar(cur, sql, args)
    linha = cur.fetchone()
    return linha[0] if linha else None


def razao(cur, chapa, dono):
    """(saldo na CHA, soma da MOV) daquele par chapa/dono."""
    saldo = _um_valor(cur, "SELECT CHAQTD FROM CHA WHERE CHACOD = ? "
                           "AND CHACLI = ?", (chapa, dono))
    soma = _um_valor(cur, "SELECT SUM(MOVQTD) FROM MOV WHERE MOVCHA = ? "
                          "AND MOVCLI = ?", (chapa, dono))
    return saldo, soma


def ler_os(cur, numero):
    """O que importa da OS, vaga a vaga."""
    campos = ["OSCOD", "OSSIT", "OSCLI", "OSVTOT"]
    for n in range(1, VAGAS + 1):
        campos += ["OSTIT%d" % n, "OSESP%d" % n, "OSLAN%d" % n,
                   "OSUNIT%d" % n, "OSVLU%d" % n]
    gerempre.perguntar(cur, "SELECT %s FROM OS WHERE OSCOD = ?"
                       % ", ".join(campos), (numero,))
    linha = cur.fetchone()
    if not linha:
        return None
    dados = dict(zip(campos, linha))
    dados["vagas"] = [
        {"n": n, "titulo": dados["OSTIT%d" % n], "item": dados["OSESP%d" % n],
         "chapas": dados["OSLAN%d" % n], "unit": dados["OSUNIT%d" % n],
         "valor": dados["OSVLU%d" % n]}
        for n in range(1, VAGAS + 1) if dados["OSESP%d" % n]]
    return dados


def mostrar(dados):
    print("")
    print("  OS %s   cliente %s   situacao %s   TOTAL R$ %s"
          % (dados["OSCOD"], dados["OSCLI"], dados["OSSIT"], dados["OSVTOT"]))
    for v in dados["vagas"]:
        print("     vaga %d  %-44s  %s chapa(s) x R$ %s = R$ %s"
              % (v["n"], (v["titulo"] or "")[:44], v["chapas"], v["unit"],
                 v["valor"]))


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    numero, vaga, chapas = (int(sys.argv[1]), int(sys.argv[2]),
                            int(sys.argv[3]))
    gravar = "--gravar" in sys.argv[4:]

    if not 1 <= vaga <= VAGAS:
        print("a vaga vai de 1 a %d" % VAGAS)
        return 1
    if chapas < 1:
        print("chapas tem de ser 1 ou mais - tirar uma vaga e outro conserto")
        return 1

    with gerempre.conectar() as con:
        cur = con.cursor()
        antes = ler_os(cur, numero)
        if not antes:
            print("a OS %s nao existe" % numero)
            return 1
        mostrar(antes)

        if int(antes["OSSIT"] or 0) != 0:
            print("")
            print("  PAREI: a OS nao esta PENDENTE (situacao %s)."
                  % antes["OSSIT"])
            print("  Entregue ja teve protocolo e faturamento; cancelada usa")
            print("  o caminho do gatilho que DEVOLVE estoque. As duas sao")
            print("  conserto de gente, olhando.")
            return 1

        alvo = [v for v in antes["vagas"] if v["n"] == vaga]
        if not alvo:
            print("")
            print("  PAREI: a vaga %d esta vazia." % vaga)
            return 1
        alvo = alvo[0]
        item, unit = alvo["item"], float(alvo["unit"] or 0)
        saldo_antes, soma_antes = razao(cur, item, antes["OSCLI"])

        print("")
        print("  RAZAO da chapa %s, dono %s" % (item, antes["OSCLI"]))
        print("     saldo na CHA: %s     soma da MOV: %s     bate: %s"
              % (saldo_antes, soma_antes,
                 saldo_antes is not None and soma_antes is not None
                 and float(saldo_antes) == float(soma_antes)))

        de = int(alvo["chapas"] or 0)
        anda = de - chapas
        novo_valor = round(unit * chapas, 2)
        total = round(sum(float(v["valor"] or 0) for v in antes["vagas"]
                          if v["n"] != vaga) + novo_valor, 2)

        print("")
        print("  O QUE EU FARIA na vaga %d:" % vaga)
        print("     chapas  %s  ->  %s" % (de, chapas))
        print("     valor   R$ %s  ->  R$ %s" % (alvo["valor"], novo_valor))
        print("     TOTAL   R$ %s  ->  R$ %s" % (antes["OSVTOT"], total))
        print("     o estoque da chapa %s deve SUBIR %d" % (item, anda))

        if not gravar:
            print("")
            print("  Isto foi so uma OLHADA - nada foi gravado.")
            print("  Decidiu? rode de novo com  --gravar")
            return 0

        # O UPDATE dispara o TR_OS_BEFO: ele APAGA os movimentos desta OS
        # e os refaz a partir das quatro vagas. E por isso que o razao e
        # conferido dos dois lados.
        cur.execute("UPDATE OS SET OSLAN%d = ?, OSVLU%d = ?, OSVTOT = ? "
                    "WHERE OSCOD = ?" % (vaga, vaga),
                    (chapas, novo_valor, total, numero))
        con.commit()

        depois = ler_os(cur, numero)
        saldo_depois, soma_depois = razao(cur, item, antes["OSCLI"])
        mostrar(depois)
        print("")
        print("  RAZAO depois: saldo %s, soma %s, bate: %s"
              % (saldo_depois, soma_depois,
                 saldo_depois is not None and soma_depois is not None
                 and float(saldo_depois) == float(soma_depois)))
        andou = float(saldo_depois) - float(saldo_antes)
        print("  o saldo andou %+d, e eu esperava %+d  ->  %s"
              % (andou, anda, "confere" if andou == anda else "NAO CONFERE"))
        if andou != anda:
            print("")
            print("  OLHE ISSO. Saldo que anda diferente do esperado quer")
            print("  dizer que outra coisa mexeu nesta OS junto.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
