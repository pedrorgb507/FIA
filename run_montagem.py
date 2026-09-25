# -*- coding: utf-8 -*-
"""
Ponto de entrada da FILA DA MONTAGEM da AMERICA.

Rode por aqui (ou clique duas vezes em iniciar_montagem.bat):
    python run_montagem.py

E irmao do run_ctp.py, e processo separado dele de proposito: esta tela
cair nao para o fechamento de chapa dos outros clientes, e o vigia cair
nao derruba esta tela.

ESTE ARQUIVO E UM SUPERVISOR, desde 25/09/2026. Ele roda a fila como
FILHA e, quando ela sai pedindo reinicio (o botao "Reiniciar agora" da
tela), sobe outra no MESMO terminal.

Antes o proprio servidor lancava o substituto, solto, e se matava. No
Windows um processo solto ganha janela propria: toda vez que alguem
apertava o botao, abria uma janela preta de python no meio da tela do
EUDSON-PC, fora do VS Code. O operador: "eu ja disse varias vezes que
quero que avise no terminal do vs code". Com o supervisor o filho herda
o terminal de quem o chamou - o da tarefa do VS Code, ou o do .bat.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# O codigo de saida com que a fila pede para ser subida de novo. Tem de
# ser o mesmo do servidor.REINICIAR - ha teste conferindo. Nao se importa
# de la para o supervisor nao carregar o programa inteiro so por um numero.
REINICIAR = 3

# Marca que distingue a filha do supervisor, no mesmo arquivo.
FILHA = "FIA_MONTAGEM_FILHA"


def supervisionar(rodar=subprocess.call):
    """Roda a fila e a sobe de novo enquanto ela pedir. Devolve o codigo."""
    ambiente = dict(os.environ)
    ambiente[FILHA] = "1"
    while True:
        try:
            codigo = rodar([sys.executable, os.path.abspath(__file__)],
                           env=ambiente)
        except KeyboardInterrupt:
            # Ctrl+C no terminal chega aos dois; a filha fecha sozinha
            return 0
        if codigo != REINICIAR:
            return codigo
        print("")
        print("  Reiniciando a fila da montagem, a pedido da tela...")
        print("")
        # a porta da anterior pode levar um instante para soltar - ver
        # servidor.main, ESPERAR A PORTA
        ambiente["FIA_ESPERAR_PORTA"] = "20"


if __name__ == "__main__":
    if os.environ.get(FILHA):
        from finart_ctp.servidor import main
        sys.exit(main())
    sys.exit(supervisionar())
