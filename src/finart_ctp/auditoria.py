# -*- coding: utf-8 -*-
r"""
Confere a resolucao das chapas ja entregues numa pasta do CTP.

    python -m finart_ctp.auditoria "W:\CTP\SETEMBRO\08\FIA"

Sem pasta, confere a do dia. E a mesma conta que a gravadora faz: tamanho
da pagina em mm contra a quantidade de pixels da imagem. Nao pergunta ao
log o que o programa achou que gerou - abre o arquivo e mede.

So mede CHAPA NOSSA: uma imagem unica cobrindo a pagina inteira. A chapa
que o operador fecha a mao sai da Corel em vetor, e vetor nao tem dpi -
quem decide a resolucao ali e o RIP da gravadora. Misturar as duas coisas
so produziria alarme falso, e alarme falso ninguem olha duas vezes.
"""

import os
import re
import sys

from .config import (FORMATOS, FORMATOS_EMPORIO, FORMATOS_FIALHO,
                     FORMATOS_VIVA)
from .utils import log

FOLGA = 0.02           # 2% - arredondamento de pixel nao e erro de gravacao
TOLERANCIA_MM = 4


def resolucoes_esperadas():
    """{(largura_mm, altura_mm): dpi} de todos os clientes juntos."""
    tabela = {}
    for formatos in (FORMATOS, FORMATOS_FIALHO, FORMATOS_EMPORIO,
                     FORMATOS_VIVA):
        for medida, (dpi, _) in formatos.items():
            tabela[medida] = dpi
    return tabela


def medir(caminho):
    """
    (largura_mm, altura_mm, dpi) da chapa, ou None se nao for chapa nossa.

    Le so o comeco do arquivo: o dicionario da imagem vem antes do fluxo,
    que numa chapa de 1000 dpi passa de 100 MB.
    """
    with open(caminho, "rb") as f:
        cabeca = f.read(8192)

    caixa = re.search(rb"/MediaBox\s*\[\s*-?[\d.]+\s+-?[\d.]+\s+"
                      rb"([\d.]+)\s+([\d.]+)\s*\]", cabeca)
    imagem = re.search(rb"/Subtype\s*/Image\s*/Width\s+(\d+)\s*/Height\s+(\d+)",
                       cabeca)
    if not caixa or not imagem:
        return None

    largura_pt, altura_pt = float(caixa.group(1)), float(caixa.group(2))
    if largura_pt <= 0:
        return None
    return (largura_pt / 72 * 25.4, altura_pt / 72 * 25.4,
            int(imagem.group(1)) / (largura_pt / 72))


def chapa_de(larg_mm, alt_mm, tabela):
    for (l, a), dpi in tabela.items():
        if (abs(larg_mm - l) <= TOLERANCIA_MM
                and abs(alt_mm - a) <= TOLERANCIA_MM):
            return (l, a), dpi
    return None, None


def auditar(pasta, mostrar_tudo=True):
    """Confere a pasta e devolve a lista de chapas fora da resolucao."""
    tabela = resolucoes_esperadas()
    problemas, medidas, de_fora = [], 0, []

    for nome in sorted(os.listdir(pasta)):
        if not nome.lower().endswith(".pdf"):
            continue
        caminho = os.path.join(pasta, nome)
        if not os.path.isfile(caminho):
            continue

        try:
            medido = medir(caminho)
        except OSError as e:
            de_fora.append((nome, "nao consegui abrir: %s" % e))
            continue

        if medido is None:
            de_fora.append((nome, "nao e chapa nossa (vetor, feita a mao)"))
            continue

        larg, alt, dpi_real = medido
        medidas += 1
        _, dpi_certo = chapa_de(larg, alt, tabela)
        if dpi_certo is None:
            de_fora.append((nome, "%.0fx%.0f mm nao e formato de chapa"
                            % (larg, alt)))
            continue

        errada = abs(dpi_real - dpi_certo) / dpi_certo > FOLGA
        if errada:
            problemas.append((nome, dpi_real, dpi_certo, larg, alt))
        if mostrar_tudo or errada:
            print("  %s %-52s %4.0f dpi (esperado %d)  %.0fx%.0f mm"
                  % ("ERRO" if errada else "OK  ", nome[:52],
                     dpi_real, dpi_certo, larg, alt))

    print()
    print("%d chapa(s) medida(s) em %s" % (medidas, pasta))
    for nome, motivo in de_fora:
        print("   - %-52s %s" % (nome[:52], motivo))

    if problemas:
        print()
        print("!" * 70)
        print("%d CHAPA(S) COM RESOLUCAO ERRADA - NAO MANDE RODAR:"
              % len(problemas))
        for nome, real, certo, l, a in problemas:
            print("   %s" % nome)
            print("      %.0f dpi, deveria ser %d  (%.0fx%.0f mm)"
                  % (real, certo, l, a))
        print("!" * 70)
    else:
        print("Todas na resolucao certa.")
    return problemas


def main():
    from .monitor import pasta_saida_do_dia
    pastas = sys.argv[1:] or [pasta_saida_do_dia()]
    ruins = 0
    for pasta in pastas:
        if not os.path.isdir(pasta):
            print("Nao achei a pasta: %s" % pasta)
            continue
        print("=" * 70)
        ruins += len(auditar(pasta))
        print()
    if ruins:
        log("AUDITORIA: %d chapa(s) com resolucao errada" % ruins, alerta=True)
    sys.exit(1 if ruins else 0)


if __name__ == "__main__":
    main()
