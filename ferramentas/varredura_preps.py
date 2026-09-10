# -*- coding: utf-8 -*-
r"""
Le os modelos de imposicao do Preps 5.0. NAO ESCREVE NADA.

Os .tpl do Preps sao PostScript de TEXTO, com o desenho todo em
comentarios estruturados '%SSi'. Ou seja: quinze anos de montagem desta
grafica estao em arquivo legivel, e da para perguntar a eles quais sao
os padroes da casa em vez de adivinhar.

    %SSiPressSheet: larg alt ... - a folha
    %SSiPrshPage:   x y larg alt ... sangE sangB sangD sangT - uma peca
    %SSiPrshMark:   folga1 folga2 comp1 comp2 tipo ... C M Y K - uma marca
    %SSiSignature:  |nome| ...

Tudo em PONTOS PostScript (1 pt = 25,4/72 mm). Conferido: 2834,6457 pt
dao 1000,0 mm; 425,19685 dao 150,0 - que e a altura da peca no modelo
'100 x 150', batendo com o nome do arquivo.

POR QUE ISTO EXISTE: as perguntas que eu ia fazer ao operador - de
quanto e a sangria, que tamanho tem a marca de corte, quanta folga ela
deixa do corte, quanto vao entre as pecas - ja estao respondidas aqui,
2020 vezes, pelas maos dele. Perguntar ao arquivo custa nada e nao
depende de memoria.
"""

import collections
import io
import os
import re
import sys

PASTA = r"C:\Program Files (x86)\Creo\Preps 5.0\Templates"
PT_MM = 25.4 / 72.0


def mm(pt):
    """Ponto PostScript -> milimetro, arredondado no centesimo."""
    return round(float(pt) * PT_MM, 2)


def numeros(resto):
    """Os campos numericos de uma linha %SSi, ignorando |nomes| e ''."""
    resto = re.sub(r"\|[^|]*\|", " ", resto)
    resto = re.sub(r"'[^']*'", " ", resto)
    return [float(n) for n in re.findall(r"-?\d+\.?\d*", resto)]


def ler(caminho):
    """{'folhas': [...], 'pecas': [...], 'marcas': [...]} de um modelo."""
    dados = {"folhas": [], "pecas": [], "marcas": [], "assinaturas": []}
    with io.open(caminho, encoding="latin-1", errors="replace") as f:
        for linha in f:
            linha = linha.rstrip("\r\n")
            if not linha.startswith("%SSi"):
                continue
            chave, _, resto = linha[4:].partition(":")
            n = numeros(resto)
            if chave == "PressSheet" and len(n) >= 2:
                dados["folhas"].append((mm(n[0]), mm(n[1])))
            elif chave == "PrshPage" and len(n) >= 11:
                dados["pecas"].append({
                    "x": mm(n[0]), "y": mm(n[1]),
                    "larg": mm(n[2]), "alt": mm(n[3]),
                    # as quatro sangrias, na ordem em que o Preps grava
                    "sangria": tuple(mm(v) for v in n[7:11]),
                })
            elif chave == "PrshMark" and len(n) >= 5:
                # duas folgas e dois comprimentos: um par e zero, o outro
                # e a marca. Qual dos dois depende de a marca ser
                # horizontal ou vertical.
                folga = max(n[0], n[1])
                comp = max(n[2], n[3])
                dados["marcas"].append({
                    "folga": mm(folga), "comp": mm(comp),
                    "tipo": int(n[4]) if len(n) > 4 else None,
                    # so e marca de TEXTO se traz |rotulo|; o '' vazio
                    # e marca comum, e foi o que zerou a conta na 1a vez
                    "texto": "|" in resto,
                })
            elif chave == "Signature":
                achado = re.search(r"\|([^|]*)\|", resto)
                if achado:
                    dados["assinaturas"].append(achado.group(1))
    return dados


def estilo(nome):
    """O feitio do trabalho, lido do nome do arquivo."""
    n = nome.upper()
    if "BATE-VIRA" in n or re.search(r"\bBV\b", n):
        return "BATE-VIRA"
    if re.search(r"\bTR\b", n) or "TIRA E RETIRA" in n:
        return "TIRA E RETIRA"
    if "PERFECT" in n:
        return "Perfect Bound"
    if "SADDLE" in n:
        return "Saddle-Stitched"
    if "FLAT" in n:
        return "Flat Work"
    return "(sem estilo no nome)"


def vaos(pecas):
    """Os vaos entre pecas vizinhas, na horizontal e na vertical."""
    achados = []
    for eixo, pos, tam in (("h", "x", "larg"), ("v", "y", "alt")):
        # agrupa pelas pecas que compartilham a outra coordenada
        outro = "y" if eixo == "h" else "x"
        linhas = collections.defaultdict(list)
        for p in pecas:
            linhas[round(p[outro], 1)].append(p)
        for grupo in linhas.values():
            grupo.sort(key=lambda p: p[pos])
            for a, b in zip(grupo, grupo[1:]):
                folga = round(b[pos] - (a[pos] + a[tam]), 2)
                if 0 <= folga < 60:
                    achados.append((eixo, folga))
    return achados


def principal():
    if not os.path.isdir(PASTA):
        raise SystemExit("nao achei a pasta de modelos: %s" % PASTA)

    arquivos = []
    for raiz, _, nomes in os.walk(PASTA):
        for nome in nomes:
            if nome.lower().endswith(".tpl"):
                arquivos.append(os.path.join(raiz, nome))
    print("modelos encontrados: %d" % len(arquivos))
    print()

    estilos = collections.Counter()
    folhas = collections.Counter()
    sangrias = collections.Counter()
    comprimentos = collections.Counter()
    folgas_marca = collections.Counter()
    vao_h = collections.Counter()
    vao_v = collections.Counter()
    tintas_marca = collections.Counter()
    quebrados = 0

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        estilos[estilo(nome)] += 1
        try:
            d = ler(caminho)
        except Exception:
            quebrados += 1
            continue
        for f in d["folhas"]:
            folhas[f] += 1
        for p in d["pecas"]:
            s = set(p["sangria"])
            if len(s) == 1:                      # sangria igual nos 4 lados
                sangrias[s.pop()] += 1
        for m in d["marcas"]:
            if m["comp"] > 0 and not m["texto"]:
                comprimentos[m["comp"]] += 1
                folgas_marca[m["folga"]] += 1
        for eixo, folga in vaos(d["pecas"]):
            (vao_h if eixo == "h" else vao_v)[folga] += 1

    def mostrar(titulo, contador, quantos=12, unidade="mm"):
        print("== %s ==" % titulo)
        total = sum(contador.values())
        for valor, n in contador.most_common(quantos):
            if isinstance(valor, tuple):
                texto = "%g x %g" % valor
            else:
                texto = "%g %s" % (valor, unidade)
            print("   %-22s %6d   %5.1f%%" % (texto, n, 100.0 * n / total))
        print("   (%d ao todo, %d valores diferentes)"
              % (total, len(contador)))
        print()

    print("== estilo, pelo nome do arquivo ==")
    for e, n in estilos.most_common():
        print("   %-24s %5d   %5.1f%%" % (e, n, 100.0 * n / len(arquivos)))
    print()

    mostrar("folhas de impressao", folhas)
    mostrar("SANGRIA por peca", sangrias)
    mostrar("COMPRIMENTO da marca", comprimentos)
    mostrar("FOLGA da marca ate o corte", folgas_marca)
    mostrar("VAO entre pecas - horizontal", vao_h)
    mostrar("VAO entre pecas - vertical", vao_v)

    if quebrados:
        print("modelos que nao consegui ler: %d" % quebrados)


if __name__ == "__main__":
    principal()
