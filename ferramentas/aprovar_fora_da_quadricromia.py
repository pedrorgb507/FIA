# -*- coding: utf-8 -*-
r"""
FECHA um arquivo que parou por NAO SER QUADRICROMIA, com o seu aval.

    python ferramentas\aprovar_fora_da_quadricromia.py <arquivo> [--fechar]

Sem --fechar ele so OLHA: diz o que achou e o que faria. E de proposito -
a decisao aqui gera chapa e mexe em estoque, e ninguem deve poder
faze-la por engano de linha de comando.


POR QUE ISTO EXISTE

A VOPRIX so fecha sozinha o que vem em quadricromia. Arte de 1, 2 ou 3
cores PARA antes da chapa: a prova sai, o PDF convertido fica guardado na
_PENDENCIAS e alguem confere. Foi pedido do operador, e a razao dele e
boa - em quadricromia o caminho e sempre o mesmo, mas arte de uma cor e
onde a decisao muda de trabalho para trabalho.

A trava estava certa; o que faltava era a PORTA DE SAIDA. O
processador.processar ja aceita aprovado=True desde que a trava nasceu -
e ninguem nunca o chamou assim. Quem decidia "pode fechar" nao tinha como
dizer isso ao programa, e terminava o servico a mao, por fora, onde nao
fica registro nenhum.

Foi o caso do 'Papel_Seda_1_0_32,0x23,0_Evolve_Estetica.cdr' em
21/09/2026: o nome DIZ 1_0 - uma cor -, a arte veio com uma cor, e as
duas coisas concordavam. A trava parou assim mesmo, como manda a regra, e
ai o servico ficou esperando alguem que nao tinha botao para apertar.


O QUE ELE NAO FAZ, e e onde ele se cala de proposito

Nao decide se a arte esta certa. Ele nao sabe se uma cor era o combinado
com o cliente - quem sabe e quem olhou a prova. Ele so leva adiante a
decisao de gente, e deixa o rastro dela.

Nao pula NENHUMA outra trava. Fonte que falta continua parando, cor que
sumiu no achatamento continua parando, arquivo que nao cabe na chapa
continua parando. So o aviso do AVISAR_QUANDO_NAO_FOR_CMYK e dispensado.

Nao refaz o que ja foi feito. Achando o arquivo no registro com chapa,
para e diz - refazer daria segunda chapa e segunda OS.


ELE RODA O CAMINHO DE VERDADE, e isso precisa ser dito

Abre OS no GEREMPRE de producao, da baixa de chapa no estoque, imprime
prova e grava a chapa no CTP. Nao e ensaio. Ver a armadilha 13 da skill
do gerempre: script solto herda o config_local inteiro. Aqui isso e o
que se QUER - o arquivo existe para fazer trabalho de verdade -, e por
isso ele confirma o que vai fazer antes, e so age com --fechar.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from finart_ctp import processador                            # noqa: E402
from finart_ctp.config import PASTA_PENDENCIAS                # noqa: E402
from finart_ctp.monitor import pasta_saida_do_dia             # noqa: E402
from finart_ctp.utils import (carregar_registro,              # noqa: E402
                              chave_arquivo, impressao_digital,
                              salvar_registro)


def cliente_do_caminho(caminho):
    """
    De que cliente e este arquivo, pelo lugar em que ele esta.

    Pela PASTA, e nao pelo nome: o nome e do cliente final ('Evolve
    Estetica'), e quem paga a chapa e a grafica dona da pasta.
    """
    from finart_ctp.monitor import clientes
    caminho = os.path.abspath(caminho).upper()
    for nome, base, _ in clientes():
        if caminho.startswith(os.path.abspath(base).upper() + os.sep):
            return nome
    return None


def olhar(caminho):
    """O que ha para saber antes de decidir. Nao escreve nada."""
    caminho = os.path.abspath(caminho)
    achados = {"caminho": caminho, "existe": os.path.isfile(caminho)}
    if not achados["existe"]:
        return achados

    achados["nome"] = os.path.basename(caminho)
    achados["cliente"] = cliente_do_caminho(caminho)
    achados["mb"] = os.path.getsize(caminho) / 1048576.0

    registro = carregar_registro()
    chave = chave_arquivo(caminho)
    achados["chave"] = chave
    antiga = registro.get(chave)
    achados["no_registro"] = antiga
    achados["ja_tem_chapa"] = bool(antiga and antiga.get("saidas"))

    # o que o NOME pede, quando o cliente escreve isso no nome
    try:
        from finart_ctp.nomes import cores_pedidas_voprix
        achados["cores_no_nome"] = cores_pedidas_voprix(achados["nome"])
    except Exception:
        achados["cores_no_nome"] = None

    # o PDF que a conversao ja deixou guardado - nao se converte de novo
    guardado = os.path.join(PASTA_PENDENCIAS,
                            os.path.splitext(achados["nome"])[0] + ".pdf")
    achados["pdf_guardado"] = guardado if os.path.isfile(guardado) else None
    return achados


def contar(achados):
    """Imprime o que se achou, em portugues de gente."""
    print("")
    print("  arquivo : %s" % achados.get("nome"))
    print("  cliente : %s" % (achados.get("cliente") or "NAO SEI - ver abaixo"))
    print("  tamanho : %.1f MB" % achados.get("mb", 0))
    pedido = achados.get("cores_no_nome")
    if pedido:
        print("  o nome  : pede %d cor(es) na frente e %d no verso"
              % pedido)
    if achados.get("pdf_guardado"):
        print("  ja convertido: %s" % achados["pdf_guardado"])
    antiga = achados.get("no_registro")
    if antiga:
        print("  no registro: %s em %s"
              % (antiga.get("status"), antiga.get("quando", "?")))
        if antiga.get("saidas"):
            print("     chapas ja geradas: %s" % ", ".join(antiga["saidas"]))
        if antiga.get("motivo"):
            print("     motivo: %s" % antiga["motivo"][:120])
    print("")


def fechar(caminho, achados):
    """
    Roda o fluxo inteiro com aprovado=True e ANOTA, como o vigia anota.

    Anotar importa tanto quanto fechar: sem a entrada no registro, a
    volta seguinte do vigia veria o arquivo como novo e faria TUDO de
    novo - outra chapa, outra OS, outra prova.
    """
    saida = pasta_saida_do_dia()
    print("  gravando em: %s" % saida)
    print("")

    resultado = processador.processar(caminho, saida,
                                      cliente=achados["cliente"],
                                      aprovado=True)

    resultado["quando"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    resultado["arquivo"] = achados["nome"]
    resultado["cliente"] = achados["cliente"]
    resultado["aprovado_fora_da_quadricromia"] = True
    try:
        resultado["impressao"] = impressao_digital(caminho)
    except OSError:
        pass

    registro = carregar_registro()
    registro[achados["chave"]] = resultado
    salvar_registro(registro)
    return resultado


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    caminho = sys.argv[1]
    vai_fechar = "--fechar" in sys.argv[2:]

    achados = olhar(caminho)
    if not achados["existe"]:
        print("nao achei o arquivo: %s" % caminho)
        return 1

    contar(achados)

    if not achados["cliente"]:
        print("  PAREI: este arquivo nao esta na pasta de nenhum cliente")
        print("  vigiado. O cliente decide preco, chapa e protocolo - sem")
        print("  ele eu estaria inventando.")
        return 1

    if achados["ja_tem_chapa"]:
        print("  PAREI: este arquivo JA TEM chapa no registro.")
        print("  Refazer daria segunda chapa e segunda OS. Se a primeira")
        print("  saiu errada, quem desfaz e gente, olhando o GEREMPRE.")
        return 1

    if not vai_fechar:
        print("  Isto foi so uma OLHADA - nada foi feito.")
        print("")
        print("  Fechando, ele vai: gerar a chapa fora da quadricromia,")
        print("  ABRIR OS NO GEREMPRE DE PRODUCAO com baixa de chapa,")
        print("  imprimir a prova e gravar no CTP.")
        print("")
        print("  Decidiu? rode de novo com  --fechar")
        return 0

    print("  FECHANDO com aprovacao de gente (fora da quadricromia)...")
    resultado = fechar(caminho, achados)

    print("")
    print("  status : %s" % resultado.get("status"))
    for s in resultado.get("saidas") or []:
        print("  chapa  : %s" % s)
    if resultado.get("motivo"):
        print("  motivo : %s" % resultado["motivo"])
    return 0 if resultado.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
