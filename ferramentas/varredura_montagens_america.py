# -*- coding: utf-8 -*-
r"""
AS MONTAGENS DE LIVRO DA AMERICA, DE 2026. NAO ESCREVE NADA.

    python ferramentas/varredura_montagens_america.py
    python ferramentas/varredura_montagens_america.py --meses Abril Maio
    python ferramentas/varredura_montagens_america.py --limite 40

O QUE ELA LE, E O QUE NAO LE. So a MONTAGEM, e so as MARCAS DE CORTE
dela - pedido do operador em 21/09/2026: "nao precisa ler o pdf
completo, so leia a montagem". Ler a arte inteira de oitenta livros
custaria horas de Ghostscript para responder o que as marcas respondem
em segundos.

POR QUE AS MARCAS, e nao a tinta: a marca E a linha em que a guilhotina
corta. Nao depende de a pagina ter margem branca, nem de sangria, nem de
fundo chapado. A medida por tinta ja mentiu uma vez nesta casa - nos
Canticos deu 'vao de 10 mm nas tres fronteiras' onde as marcas dizem
135|135|5|135|135. Ver ler_marcas_da_montagem.py.

A PERGUNTA QUE ELA EXISTE PARA RESPONDER: quantas paginas cabem numa
chapa, por formato de peca. E dela que sai o "escolheu formato 2, o
numero maximo de paginas ja vem preenchido" - o operador nao deve ter de
digitar o que a geometria ja sabe.

COMO SE SABE QUE UMA MONTAGEM E DE LIVRO. Pelo par de arquivos: a casa
salva a arte paginada com o nome do trabalho, e a montagem com MONTAGEM
no nome. Havendo os dois na mesma pasta, aquilo e um livro montado - e
nao uma peca solta repetida.
"""

import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = r"\\servidor\TRABALHO\AMERICA"

# Os meses de 2026 ficam na RAIZ da pasta do cliente; 2023, 2024 e 2025
# estao em subpastas de ano. Entao "este ano" e o que esta na raiz.
MESES = ("Janeiro", "Fevereiro", "MARÇO", "Abril", "Maio", "Junho",
         "JULHO", "Agosto", "Setembro")

MARCA = re.compile(r"montagem", re.I)

# Palavras que a casa usa no nome quando o trabalho e de miolo/livro.
# Nao e adivinhacao: sao as que aparecem nos proprios nomes de arquivo.
DE_LIVRO = re.compile(r"miolo|livro|livreto|revista|caderno|almanaque|"
                      r"manual|agenda|guia|cantico|apostila", re.I)


def montagens(meses=None, limite=None):
    """Os PDFs de MONTAGEM de livro, com a arte ao lado quando houver."""
    achados = []
    for mes in (meses or MESES):
        raiz = os.path.join(BASE, mes)
        if not os.path.isdir(raiz):
            continue
        for pasta, _, arquivos in os.walk(raiz):
            pdfs = [a for a in arquivos if a.lower().endswith(".pdf")]
            montados = [a for a in pdfs if MARCA.search(a)]
            for m in montados:
                if not DE_LIVRO.search(m):
                    continue
                achados.append({"mes": mes, "pasta": pasta, "montagem": m,
                                "caminho": os.path.join(pasta, m)})
                if limite and len(achados) >= limite:
                    return achados
    return achados


def geometria(caminho):
    """
    {colunas, linhas, peca, vaos} de uma montagem, pelas marcas.

    Devolve None quando nao deu para ler - montagem sem marca, PDF que
    nao abre, Ghostscript engasgado. Nao estoura: uma pasta de cliente
    tem de tudo, e parar na primeira esquisitice nao varre nada.
    """
    import shutil
    import tempfile
    from ler_marcas_da_montagem import contar, ler

    # O GHOSTSCRIPT NAO LE PDF POR CAMINHO DE REDE. E armadilha conhecida
    # desta casa, e ela nao da erro claro: ele devolve "Unrecoverable
    # error" e quem ve conclui que o PDF esta quebrado. Os arquivos da
    # AMERICA moram todos no \servidor, entao cada um vem para o disco
    # local antes de ser lido, e sai depois.
    pasta = tempfile.mkdtemp(prefix="montagem_")
    local = os.path.join(pasta, "m.pdf")
    try:
        shutil.copy2(caminho, local)
        lido = ler(local, pagina=1)
    except Exception:
        return None
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    if not lido or not lido.get("passos_x") or not lido.get("passos_y"):
        return None
    # O ler() devolve 'passos_x'/'passos_y', e nao 'colunas'/'linhas' - a
    # primeira versao desta varredura perguntou pelos nomes errados,
    # recebeu vazio e culpou o Ghostscript. Lida direto, a mesma
    # montagem respondia na hora.
    pc, vc = contar(lido["passos_x"])
    pl, vl = contar(lido["passos_y"])
    return {"chapa": lido["chapa"],
            "passos_x": lido["passos_x"], "passos_y": lido["passos_y"],
            "peca": (pc, pl), "vaos": (vc, vl),
            "colunas": len(lido["passos_x"]), "linhas": len(lido["passos_y"])}


def _peca_e_vaos(passos):
    """(medida da peca, [vaos]) a partir dos passos entre marcas."""
    if not passos:
        return None, []
    # A PECA E O PASSO QUE MAIS SE REPETE, e o vao e o que sobra. Numa
    # montagem de caderno os passos sao 135,135,5,135,135: a peca
    # aparece quatro vezes e o vao uma. Tirar a media misturaria os dois.
    conta = collections.Counter(round(p, 1) for p in passos)
    peca = conta.most_common(1)[0][0]
    vaos = [p for p in passos if abs(p - peca) > 1.0]
    return peca, vaos


def principal():
    meses = None
    limite = None
    if "--meses" in sys.argv:
        i = sys.argv.index("--meses")
        meses = [a for a in sys.argv[i + 1:] if not a.startswith("--")]
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])

    lista = montagens(meses, limite)
    print("montagens de livro achadas: %d" % len(lista))
    print("")

    linhas_ok = 0
    registros = []
    por_grade = collections.Counter()
    por_peca = collections.Counter()
    for m in lista:
        g = geometria(m["caminho"])
        if not g:
            print("   -- %-58s (nao consegui ler as marcas)"
                  % m["montagem"][:58])
            continue
        linhas_ok += 1
        pc, pl = g["peca"]
        nc, nr = g["colunas"], g["linhas"]
        por_grade["%dx%d" % (nc, nr)] += 1
        if pc and pl:
            por_peca["%.0f x %.0f" % (pc, pl)] += 1
        print("   %-46s %dx%d  peca %.0f x %.0f  chapa %.0f x %.0f"
              % (m["montagem"][:46], nc, nr, pc or 0, pl or 0,
                 g["chapa"][0], g["chapa"][1]))
        print("      colunas %s"
              % " | ".join("%.0f" % p for p in g["passos_x"]))
        print("      linhas  %s"
              % " | ".join("%.0f" % p for p in g["passos_y"]))
        registros.append(dict(g, arquivo=m["montagem"], mes=m["mes"]))

    print("")
    print("=" * 66)
    print("  LIDAS: %d de %d" % (linhas_ok, len(lista)))
    for titulo, conta in (("grade", por_grade), ("peca (mm)", por_peca)):
        print("")
        print("  por %s:" % titulo)
        for chave, q in conta.most_common(12):
            print("     %-16s %4d" % (chave, q))

    # O DESENHO DO VAO e o que distingue caderno de folha solta, e e a
    # razao desta varredura existir. 'encostadas' quer dizer vao zero
    # entre vizinhas - dobra, nao corte.
    print("")
    print("  o desenho do vao, por eixo:")
    for eixo, campo in (("colunas", "passos_x"), ("linhas", "passos_y")):
        desenho = collections.Counter()
        for r in registros:
            pc = r["peca"][0 if campo == "passos_x" else 1]
            marca = "".join("=" if abs(p - pc) <= 1.5 else "|"
                            for p in r[campo])
            desenho[marca] += 1
        print("     %s:" % eixo)
        for d, q in desenho.most_common(8):
            print("        %-14s %4d    (= peca encostada, | vao)" % (d, q))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
