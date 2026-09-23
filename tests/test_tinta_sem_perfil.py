# -*- coding: utf-8 -*-
"""
A TINTA SE CONTA COMO ESTA ESCRITA NO ARQUIVO, e nunca pelo perfil ICC.

O caso, 23/09/2026: o 'WIL BURGUE_1 colorido.pdf' da FIALHO. Arte de
TRES tintas - MYK, sem ciano - fechada como CMYK. Nome errado no CTP,
uma chapa gravada a toa e QUATRO chapas cobradas na OS 19947 onde cabiam
tres.

O operador viu e disse o alcance: "nos proximos de QUALQUER cliente,
preciso que preste muita atencao nisso e nao erre, nao so nesse caso de
nao ter ciano, pode ser 2 cores, 1 cor, 3 cores, pode nao ter magenta,
cada um tem seu diferencial".

A CAUSA, medida no proprio arquivo - ele traz /DefaultCMYK ICCBased:

                       C          M          Y          K
    com o perfil    0.07708    0.08530    0.08542    0.07697   CKMY
    sem o perfil    0.00000    0.00863    0.00864    0.07697   KMY

O ciano e ZERO. O perfil reconstruiu o preto puro como preto rico - o C
inventado (0.07708) e o mesmo numero do K (0.07697) - e de quebra
inflou M e Y em DEZ VEZES.

E o codigo ja SABIA disso: o ghostscript.sem_perfil tem a explicacao e
os numeros desde sempre, e tres dos quatro chamadores ja passavam
sem_icc=True. So o do processador nao - ele prendia a leitura crua aos
clientes que vem do Corel, e nao havia razao para a diferenca: a chapa E
o PDF para todo cliente, e quem separa as tintas e sempre a gravadora.

ISTO NAO DA ERRO EM LUGAR NENHUM. A chapa sai, a prova sai, a OS fecha.
So aparece na maquina, quando o impressor procura a chapa de ciano que
nao tem desenho - ou nao aparece, e o cliente paga uma chapa a mais.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

import finart_ctp.processador as P                            # noqa: E402
from finart_ctp.ghostscript import tintas_da_cobertura        # noqa: E402

# Os numeros do WIL BURGUE, medidos. Ficam aqui porque e deles que o
# teste vive: mudando o limiar da tinta, e este caso que tem de continuar
# respondendo tres.
WIL_COM_PERFIL = {"C": 0.07708, "M": 0.08530, "Y": 0.08542, "K": 0.07697}
WIL_SEM_PERFIL = {"C": 0.00000, "M": 0.00863, "Y": 0.00864, "K": 0.07697}


def test_o_WIL_BURGUE_tem_TRES_tintas():
    """A medida crua, e o que ela responde."""
    assert tintas_da_cobertura(WIL_SEM_PERFIL) == {"M", "Y", "K"}


def test_com_o_perfil_ele_pareceria_ter_QUATRO():
    """O defeito, para o teste acima nao passar por acaso."""
    assert tintas_da_cobertura(WIL_COM_PERFIL) == {"C", "M", "Y", "K"}


def test_o_ciano_inventado_e_o_MESMO_numero_do_preto():
    """
    A assinatura do perfil remisturando, e o jeito mais rapido de
    reconhecer isto num arquivo novo: o C que aparece do nada vem com o
    valor do K, porque e o mesmo preto espalhado.
    """
    assert abs(WIL_COM_PERFIL["C"] - WIL_COM_PERFIL["K"]) < 0.001
    assert WIL_SEM_PERFIL["C"] == 0.0


def test_a_leitura_crua_vale_para_QUALQUER_cliente(monkeypatch):
    """
    O conserto. Antes a linha era
    'sem_icc = cliente in CLIENTES_QUE_VEM_DO_COREL', e a FIALHO - que
    nao esta nessa lista - lia com o perfil.

    Aqui se roda o processador para um cliente de CADA lado daquela
    lista e se confere COMO ele mediu.
    """
    for cliente in (P.FIALHO, P.SOLIDA, P.VOPRIX, P.VIVA, P.EMPORIO):
        pedidos = []

        def anotar(pdf, sem_icc=False, so_o_corte=False, _p=pedidos):
            _p.append(sem_icc)
            return [dict(WIL_SEM_PERFIL)]

        monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
        monkeypatch.setattr(P, "cobertura_por_pagina", anotar)
        monkeypatch.setattr(P, "sem_cor_gritante",
                            lambda pdf, pagina, sem_icc=False: False)
        monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
        monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
        try:
            P._processar_pdf("x.pdf", "teste.pdf", ".", cliente,
                             {"status": "ok", "saidas": [], "motivo": "",
                              "impresso": None}, lambda m: None, False)
        except Exception:
            # o que interessa e COMO ele pediu a medida, e isso ja
            # aconteceu antes de qualquer tropeco mais adiante
            pass
        assert pedidos, "nao mediu a cobertura em %s" % cliente
        assert pedidos[0] is True, (
            "%s leu a cobertura COM o perfil - e ai tinta que nao existe "
            "vira chapa gravada e cobrada" % cliente)


def test_a_linha_que_prendia_a_leitura_aos_clientes_do_COREL_saiu():
    """
    LE O ARQUIVO DO MODULO: o conftest troca o _os_do_arquivo por um
    coto, e o inspect devolveria o coto.

    Voltando essa linha, o defeito volta inteiro - e sem dar erro em
    lugar nenhum.
    """
    import io
    fonte = io.open(P.__file__, encoding="utf-8").read()
    # SO AS LINHAS DE CODIGO. O comentario do conserto CITA a linha
    # velha - e deve citar, e dela que se entende o caso -, e um teste
    # que casasse com o texto acusaria o proprio remedio.
    vivas = [l.split("#")[0] for l in fonte.splitlines()]
    assert not [l for l in vivas
                if "sem_icc = cliente in CLIENTES_QUE_VEM_DO_COREL" in l]
    assert [l for l in vivas if l.strip() == "sem_icc = True"]
