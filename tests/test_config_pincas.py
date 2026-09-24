# -*- coding: utf-8 -*-
"""
As pincas ditadas pelo operador, presas por teste.

Nao ha logica aqui para conferir - ha NUMERO, e numero ditado se perde
calado. Um teste que falha ao mudar a constante e o que faz alguem
parar e perguntar "o operador mandou mudar isto?".
"""
from finart_ctp.config import (PINCA_CREATIVE_MM, PINCA_EMPORIO_MM,
                               PINCA_IDEAL_MM, PINCA_PRIME_MM)
from finart_ctp.processador import (CREATIVE, EMPORIO, IDEAL, PRIME,
                                    pinca_do_cliente)


def test_as_pincas_ditadas():
    assert PINCA_CREATIVE_MM == 40      # GTO 52
    assert PINCA_PRIME_MM == 28
    assert PINCA_IDEAL_MM == 35         # GTO e ADAST, 22/09/2026
    assert PINCA_EMPORIO_MM == 28       # 24/09/2026, era 30


def test_a_EMPORIO_esta_registrada_mas_a_FIA_nao_a_APLICA():
    """
    E os dois lados importam.

    O numero existe - o operador ditou em 24/09/2026 e ele tem de estar
    escrito onde se procura. Mas a FIA NAO monta arte da EMPORIO: a arte
    dela chega ja no tamanho da chapa (39 das 40 chapas ja fechadas
    vieram em 510x400 exatos), e so se pinca quem chega menor.

    Ligar a EMPORIO ao pinca_do_cliente por engano faria a FIA comecar a
    montar arte que hoje passa direto - mudanca de comportamento em
    producao que ninguem pediu. Se um dia ele pedir, e aqui que este
    teste muda, de proposito.
    """
    assert pinca_do_cliente(EMPORIO) == 0
    assert pinca_do_cliente(CREATIVE) == PINCA_CREATIVE_MM
    assert pinca_do_cliente(PRIME) == PINCA_PRIME_MM
    assert pinca_do_cliente(IDEAL) == PINCA_IDEAL_MM
