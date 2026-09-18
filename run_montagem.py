# -*- coding: utf-8 -*-
"""
Ponto de entrada da FILA DA MONTAGEM da AMERICA.

Rode por aqui (ou clique duas vezes em iniciar_montagem.bat):
    python run_montagem.py

E irmao do run_ctp.py, e processo separado dele de proposito: esta tela
cair nao para o fechamento de chapa dos outros clientes, e o vigia cair
nao derruba esta tela.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from finart_ctp.servidor import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
