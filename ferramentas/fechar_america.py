# -*- coding: utf-8 -*-
r"""
Fecha a mao o que estiver no portao da AMERICA. ESCREVE EM PRODUCAO.

O trabalho de verdade mora em src/finart_ctp/america.py, porque o vigia
o chama a cada volta do laco - desde 10/09/2026 o portao e AUTOMATICO.
Isto aqui e so o atalho para rodar fora do vigia: conferir sem escrever,
ou empurrar um arquivo que ficou para tras.

    python ferramentas/fechar_america.py --olhar    <- nao escreve nada
    python ferramentas/fechar_america.py            <- fecha de verdade
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finart_ctp import america                     # noqa: E402


def principal():
    so_olhar = "--olhar" in sys.argv
    dia, portao = america.pasta_do_dia_america()
    if not dia:
        raise SystemExit("nao achei a pasta do dia da AMERICA em %s"
                         % america.BASE_AMERICA)
    print("pasta do dia: %s" % dia)
    print("portao:       %s" % portao)
    if not os.path.isdir(portao):
        raise SystemExit("a pasta '%s' nao existe ainda" % america.PORTAO)

    esperando = [f for f in sorted(os.listdir(portao))
                 if f.lower().endswith(".pdf")]
    if not esperando:
        print()
        print("o portao esta vazio - nada a fechar.")
        return

    print()
    if so_olhar:
        print(">>> SO OLHANDO: nada sera escrito <<<")
        print()
    for f in esperando:
        print("=== %s ===" % f)
        relato = america.fechar(os.path.join(portao, f), dia,
                                so_olhar=so_olhar)
        for p in relato["passos"]:
            print("   %s" % p)
        print()


if __name__ == "__main__":
    principal()
