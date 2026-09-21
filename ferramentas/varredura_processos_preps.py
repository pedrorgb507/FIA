# -*- coding: utf-8 -*-
r"""
O QUE OS 1773 MODELOS DO PREPS DIZEM SOBRE OS TRES PROCESSOS.

    python ferramentas/varredura_processos_preps.py
    python ferramentas/varredura_processos_preps.py --america
    python ferramentas/varredura_processos_preps.py --dobras

NAO ESCREVE NADA. Le os .tpl e conta.

POR QUE ELA EXISTE. O operador nomeou os tres processos da AMERICA em
20/09/2026 - folha solta, canoa e lombada - e a skill ficou com quatro
perguntas de pe, todas da mesma familia: o que MUDA entre canoa e
lombada, alem do encaixe dos cadernos.

Os modelos respondem sozinhos, porque a casa escreve o processo NO NOME
DO ARQUIVO, em ingles do Preps:

    Flat Work        folha solta
    Saddle-Stiched   canoa     (e as grafias Saddle-Stitched, Sithce...)
    Perfect Bound    lombada, hot-melt

Nao fui eu que inventei essa classificacao, e por isso ela vale: sao
quinze anos de montagem desta grafica, arquivada por quem monta.

O QUE SE PERGUNTA A ELES, e cada pergunta e uma linha aberta na skill:

  1. a DOBRA muda entre canoa e lombada? A skill afirma que nao, com
     base em DOIS tutoriais de 16 paginas. Dois nao e amostra;
  2. quantas colunas e linhas a casa usa em caderno? So havia dois e
     quatro medidos, e nenhuma montagem de mais de duas linhas;
  3. a peca DEITADA em caderno existe? Estava implementada e nao
     medida em arquivo nenhum;
  4. quantas paginas por caderno a casa usa em cada processo? E dai
     sai o "formato 2 ja vem com o maximo que cabe".
"""

import collections
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ler_paginacao_preps import PASTA, conferir, ler        # noqa: E402

# A CASA ESCREVE O PROCESSO NO NOME, e escreve errado de varios jeitos.
# 'Saddle-Stiched', 'Saddle-Sithce', 'Saddle Stitched' - quinze anos de
# gente digitando. O reconhecimento e por pedaco, e nao por nome exato.
PROCESSOS = (
    ("canoa",   re.compile(r"sadd|stich|stitch|sithce", re.I)),
    ("lombada", re.compile(r"perfect|bound|hot.?melt", re.I)),
    ("solta",   re.compile(r"flat.?work", re.I)),
)


def processo_do_nome(nome):
    for rotulo, padrao in PROCESSOS:
        if padrao.search(nome):
            return rotulo
    return "sem nome de processo"


def e_da_america(nome):
    return re.search(r"america|américa", nome, re.I) is not None


def grade(lugares):
    """(colunas, linhas) contando posicoes distintas de x e de y."""
    if not lugares:
        return (0, 0)
    xs = sorted(set(round(p["x"], 1) for p in lugares))
    ys = sorted(set(round(p["y"], 1) for p in lugares))
    return (len(xs), len(ys))


# O QUE O ler_paginacao_preps DEVOLVE E TEXTO, e nao um dicionario.
# A primeira versao desta varredura perguntava p["giro"].get("deitada") a
# uma string - nunca dava verdadeiro - e eu quase escrevi na skill que a
# casa NUNCA deita peca em caderno, com 0 de 2439 de amostra. Zero
# redondo demais e sinal de contador quebrado, nao de regra da casa.
DEITADAS = ("90", "-90")


def deitada(lugares):
    """Alguma peca entra DEITADA neste caderno?"""
    return any(p.get("giro") in DEITADAS for p in lugares)


def giros_deste(lugares):
    """Quantas pecas em cada giro."""
    import collections as _c
    return _c.Counter(p.get("giro") for p in lugares)


def assinatura_da_dobra(caderno):
    """
    A DOBRA, como uma chave comparavel: as paginas em ordem de lugar.

    O lugar e ordenado por (y, x) - de baixo para cima, da esquerda para
    a direita -, que e como se le uma folha posta na mesa. Duas dobras
    iguais dao a mesma chave, venham de que processo vierem.

    NORMALIZADO PELO TAMANHO: so faz sentido comparar caderno de 16 com
    caderno de 16.
    """
    lugares = sorted(caderno["lugares"],
                     key=lambda p: (round(p["y"], 1), round(p["x"], 1)))
    return tuple((p["frente"], p["verso"]) for p in lugares)


def varrer(so_america=False):
    achados = []
    for nome in sorted(os.listdir(PASTA)):
        if not nome.lower().endswith(".tpl"):
            continue
        if so_america and not e_da_america(nome):
            continue
        try:
            cadernos = ler(os.path.join(PASTA, nome))
        except Exception:
            continue
        for c in cadernos:
            if not c["lugares"]:
                continue
            bate, _ = conferir(c)
            achados.append({
                "arquivo": nome,
                "processo": processo_do_nome(nome),
                "america": e_da_america(nome),
                "paginas": c["paginas"],
                "folha": c["folha"],
                "grade": grade(c["lugares"]),
                "deitada": deitada(c["lugares"]),
                "giros": giros_deste(c["lugares"]),
                "lugares": len(c["lugares"]),
                "bate": bate,
                "dobra": assinatura_da_dobra(c),
                "pinca": c.get("pinca"),
            })
    return achados


def _tabela(titulo, contagem, total=None):
    print("")
    print("== %s" % titulo)
    total = total or sum(contagem.values())
    for chave, quantos in sorted(contagem.items(),
                                 key=lambda kv: -kv[1])[:14]:
        print("   %-28s %5d   %5.1f%%"
              % (chave, quantos, 100.0 * quantos / max(1, total)))


def relatorio(achados, rotulo):
    print("")
    print("=" * 70)
    print("  %s - %d caderno(s) em %d modelo(s)"
          % (rotulo, len(achados),
             len(set(a["arquivo"] for a in achados))))
    print("=" * 70)

    _tabela("por processo",
            collections.Counter(a["processo"] for a in achados))

    for proc in ("canoa", "lombada", "solta"):
        destes = [a for a in achados if a["processo"] == proc]
        if not destes:
            continue
        print("")
        print("-- %s ------------------------------------------" % proc.upper())
        _tabela("  paginas por caderno",
                collections.Counter(a["paginas"] for a in destes))
        _tabela("  grade (colunas x linhas)",
                collections.Counter("%dx%d" % a["grade"] for a in destes))
        quantas = sum(1 for a in destes if a["deitada"])
        print("")
        print("   caderno com ALGUMA peca deitada: %d de %d  (%.1f%%)"
              % (quantas, len(destes), 100.0 * quantas / len(destes)))
        giros = collections.Counter()
        for a in destes:
            giros.update(a["giros"])
        total_pecas = sum(giros.values())
        print("   os giros, peca por peca (%d pecas):" % total_pecas)
        for g, q in sorted(giros.items(), key=lambda kv: -kv[1]):
            print("      giro %-5s %6d   %5.1f%%"
                  % (g, q, 100.0 * q / max(1, total_pecas)))
        ruins = [a for a in destes if a["bate"] is False]
        print("   cadernos cuja paginacao NAO fecha 1..N: %d" % len(ruins))


def comparar_dobras(achados):
    """
    A PERGUNTA QUE A SKILL DEIXOU ABERTA: a dobra muda entre canoa e
    lombada?

    Compara, para cada numero de paginas, as dobras vistas em cada
    processo. Sendo a mesma dobra nos dois, a skill esta certa e passa a
    ter amostra em vez de dois tutoriais.
    """
    print("")
    print("=" * 70)
    print("  A DOBRA MUDA ENTRE CANOA E LOMBADA?")
    print("=" * 70)

    por = collections.defaultdict(lambda: collections.defaultdict(set))
    for a in achados:
        if a["processo"] in ("canoa", "lombada") and a["bate"]:
            por[a["paginas"]][a["processo"]].add(a["dobra"])

    for paginas in sorted(por):
        canoa = por[paginas].get("canoa", set())
        lomb = por[paginas].get("lombada", set())
        if not canoa or not lomb:
            continue
        comuns = canoa & lomb
        print("")
        print("   %d paginas:  canoa tem %d dobra(s) distinta(s), "
              "lombada tem %d" % (paginas, len(canoa), len(lomb)))
        print("      dobras em COMUM: %d" % len(comuns))
        so_canoa, so_lomb = canoa - lomb, lomb - canoa
        if so_canoa:
            print("      so na canoa   : %d" % len(so_canoa))
        if so_lomb:
            print("      so na lombada : %d" % len(so_lomb))
        if comuns and not so_canoa and not so_lomb:
            print("      -> IDENTICAS. A dobra nao distingue os dois.")


def principal():
    so_america = "--america" in sys.argv
    achados = varrer()
    relatorio(achados, "TODOS OS MODELOS")
    if so_america or "--dobras" not in sys.argv:
        da_casa = [a for a in achados if a["america"]]
        if da_casa:
            relatorio(da_casa, "SO OS DA AMERICA")
    comparar_dobras(achados)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
