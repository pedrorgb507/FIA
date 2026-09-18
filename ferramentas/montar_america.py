# -*- coding: utf-8 -*-
r"""
Mostra o que esta esperando montagem no portao da AMERICA. NAO ESCREVE.

E o irmao do fechar_america.py, e o contrario dele: aquele cuida do que
uma pessoa JA revisou e vai virar chapa; este mostra o que chegou POR
MONTAR e ninguem montou ainda.

    python ferramentas/montar_america.py            <- so olha
    python ferramentas/montar_america.py --olhar    <- o mesmo, dito

Este comando nao monta nada, e nao ha bandeira que o faca montar: montar
e decisao de gente, e a equipe monta pela tela. Aqui se confere a fila -
de dentro da maquina da FIA, quando a tela nao estiver a mao, ou para
entender por que um arquivo nao aparece nela.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finart_ctp import america, montagem              # noqa: E402


def principal():
    dia, portao = montagem.pastas_da_montagem()
    if not dia:
        raise SystemExit("nao achei a pasta do dia da AMERICA em %s"
                         % america.BASE_AMERICA)
    print("pasta do dia: %s" % dia)
    print("portao:       %s" % portao)
    print()
    print(">>> SO OLHANDO: nada sera escrito <<<")
    print()

    if not os.path.isdir(portao):
        raise SystemExit(
            "a pasta '%s' nao existe ainda - crie-a na pasta do dia e ponha "
            "nela o que a AMERICA mandou por montar" % montagem.PORTAO)

    esperando = montagem.fila(portao)
    if not esperando:
        print("nada esperando montagem.")
        # NAO E O MESMO QUE PORTAO VAZIO, e a diferenca importa para quem
        # esta procurando um arquivo que "deveria estar na fila": ele pode
        # estar chegando pela rede, ou ja ter sido montado antes.
        havia = [f for f in sorted(os.listdir(portao))
                 if f.lower().endswith(montagem.EXTENSOES)]
        if havia:
            print()
            print("(ha %d arquivo(s) no portao, e nenhum e trabalho: ou "
                  "ainda esta chegando pela rede, ou ja foi montado antes)"
                  % len(havia))
            registro = montagem.carregar_montagens()
            for f in havia:
                try:
                    ja = registro.get(
                        montagem.chave_arquivo(os.path.join(portao, f)))
                except OSError:
                    # saiu do portao entre a listagem e agora
                    continue
                print("   %s - %s" % (
                    f, "montado em %s por %s" % (ja.get("quando", "antes"),
                                                 ja.get("quem", "?"))
                    if ja else "ainda chegando"))
        return

    print("esperando montagem (%d):" % len(esperando))
    for caminho in esperando:
        try:
            quanto = "%.1f MB" % (os.path.getsize(caminho) / 1048576.0)
        except OSError:
            quanto = "(saiu do portao agora)"
        print("   %s   %s" % (os.path.basename(caminho), quanto))


if __name__ == "__main__":
    principal()
