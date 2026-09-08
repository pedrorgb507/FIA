# -*- coding: utf-8 -*-
r"""
O que a FIA fez hoje.

    python -m finart_ctp.relatorio
    python -m finart_ctp.relatorio 07 08          (dias especificos)

Nao inventa numero nenhum: le o registro e o log que ela ja escreve. Ate
agora esses dados existiam e ninguem lia - a informacao estava toda no
_log_ctp.txt, misturada com o resto do dia.

E a parte de GESTAO do oficio. Um POP que ninguem mede vira habito, e
habito ninguem melhora. As tres perguntas que o relatorio responde:

    quanto saiu       chapas por cliente
    quanto parou      pendencias, agrupadas pelo motivo
    quanto custou     papel de prova e tempo de maquina
"""

import collections
import json
import os
import re
import sys

from .config import PASTA_CONTROLE, REGISTRO
from .utils import agora_util, nome_do_mes, pasta_do_dia

HORA = re.compile(r"^\[(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})\] (.*)$")


def _linhas_do_log():
    try:
        with open(os.path.join(PASTA_CONTROLE, "_log_ctp.txt"),
                  encoding="utf-8") as f:
            return f.read().splitlines()
    except OSError:
        return []


def _do_dia(linhas, dia):
    """As linhas do log daquele dia, com (hora_em_segundos, texto)."""
    achadas = []
    for linha in linhas:
        m = HORA.match(linha)
        if m and m.group(1) == dia:
            segundos = (int(m.group(3)) * 3600 + int(m.group(4)) * 60
                        + int(m.group(5)))
            achadas.append((segundos, m.group(6)))
    return achadas


def _registro():
    try:
        with open(os.path.join(PASTA_CONTROLE, REGISTRO),
                  encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _resumir_motivo(texto):
    """
    Agrupa pendencias pelo que ELAS SAO, nao pelo texto exato.

    Sem isto cada pendencia seria unica - todas trazem o nome do arquivo
    e os numeros do caso - e a contagem nao diria nada.
    """
    baixo = texto.lower()
    for pedaco, rotulo in (
            ("nao veio em quadricromia", "arte fora de quadricromia"),
            ("marca de corte", "sem marca de corte reconhecivel"),
            ("nao e chapa", "medida que nao e chapa do cliente"),
            ("verniz", "verniz - confere antes"),
            ("nao em pdf", "veio em Corel, nao em PDF"),
            ("nao sei tratar", "tipo de arquivo que ela nao trata"),
            ("fonte nao incorporada", "fonte nao incorporada"),
            ("borrada na tiragem", "imagem de baixa resolucao"),
            ("vazio (0 byte)", "arquivo vazio"),
            ("mudando de tamanho", "arquivo ainda chegando"),
            ("arquivo gigante", "arquivo acima do limite"),
            ("ja tinha o nome", "nome repetido - virou MODELO ou _v2"),
            ("ja existe", "nome repetido - virou MODELO ou _v2"),
            ("numero de os no nome", "sem numero de OS no nome"),
            ("aberto no coreldraw", "aberto no CorelDRAW de alguem"),
            ("impressora", "impressora fora do ar"),
    ):
        if pedaco in baixo:
            return rotulo
    return texto[:60]


def do_dia(dia=None, mes=None):
    """Imprime o relatorio de um dia. Devolve o total de chapas."""
    dia = dia or pasta_do_dia()
    mes = mes or nome_do_mes()
    linhas = _do_dia(_linhas_do_log(), dia)

    print("=" * 68)
    print("O QUE A FIA FEZ EM %s/%s" % (dia, mes))
    print("=" * 68)

    if not linhas:
        print("Nao ha nada no log deste dia.")
        return 0

    # --- chapas, por cliente -------------------------------------------
    chapas = collections.Counter()
    tempo = collections.Counter()
    megas = 0.0
    for _, texto in linhas:
        m = re.match(r"OK em (\d+)s: (.+?) \((.+?), ([\d.]+) MB\)",
                     texto.strip())
        if not m:
            continue
        nome = m.group(2)
        dono = "SOLIDA"
        for cliente in ("VOPRIX", "FIALHO", "EMPORIO", "VIVA", "CREATIVE"):
            if cliente in nome.upper():
                dono = cliente
                break
        chapas[dono] += 1
        tempo[dono] += int(m.group(1))
        megas += float(m.group(4))

    print()
    print("CHAPAS ENTREGUES")
    if not chapas:
        print("   nenhuma")
    for dono, quantas in chapas.most_common():
        print("   %-9s %3d chapa(s)   %5.1f min de maquina"
              % (dono, quantas, tempo[dono] / 60.0))
    if chapas:
        print("   %-9s %3d            %5.1f min   |  %.1f GB gravados"
              % ("TOTAL", sum(chapas.values()), sum(tempo.values()) / 60.0,
                 megas / 1024))

    # --- provas impressas ----------------------------------------------
    folhas = 0
    for _, texto in linhas:
        m = re.search(r"impresso em .+ \((\d+) folha", texto)
        if m:
            folhas += int(m.group(1))
    print()
    print("PROVAS IMPRESSAS")
    print("   %d folha(s) A4" % folhas)

    # --- o que parou ---------------------------------------------------
    motivos = collections.Counter()
    quais = collections.defaultdict(set)
    for _, texto in linhas:
        if not texto.startswith(">>> PENDENCIA: "):
            continue
        corpo = texto[len(">>> PENDENCIA: "):]
        arquivo, _, motivo = corpo.partition(" | ")
        rotulo = _resumir_motivo(motivo)
        motivos[rotulo] += 1
        quais[rotulo].add(arquivo)

    print()
    print("O QUE PAROU E ESPEROU GENTE")
    if not motivos:
        print("   nada - tudo que chegou fechou sozinho")
    for motivo, quantas in motivos.most_common():
        print("   %2d x  %s" % (quantas, motivo))
        for arquivo in sorted(quais[motivo])[:3]:
            print("         %s" % arquivo[:58])
        if len(quais[motivo]) > 3:
            print("         e mais %d" % (len(quais[motivo]) - 3))

    # --- o dia -----------------------------------------------------------
    print()
    print("O DIA")
    print("   da %02d:%02d as %02d:%02d"
          % (linhas[0][0] // 3600, linhas[0][0] % 3600 // 60,
             linhas[-1][0] // 3600, linhas[-1][0] % 3600 // 60))
    reinicios = sum(1 for _, t in linhas if t.startswith("Registro: "))
    if reinicios:
        print("   %d vez(es) que a FIA subiu" % reinicios)

    registro = _registro()
    print("   %d arquivo(s) no registro, desde o comeco" % len(registro))
    return sum(chapas.values())


def main():
    dias = sys.argv[1:] or [pasta_do_dia()]
    for dia in dias:
        do_dia(dia)
        print()
    print("(hoje e %s)" % agora_util().strftime("%d/%m/%Y"))


if __name__ == "__main__":
    main()
