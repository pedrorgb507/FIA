# -*- coding: utf-8 -*-
r"""
A trava: NENHUM teste fala com o GEREMPRE de verdade.

Isto nao e zelo excessivo. Em 09/09/2026 a bateria de testes abriu
QUATRO ORDENS DE SERVICO NA PRODUCAO e baixou chapa em quatro estoques -
UNIRV BLOCOS, TAG BALADA, VERNIZ e SICOOB, todas com nome de arquivo de
teste. Foram desfeitas no mesmo dia e o estoque voltou ao numero exato,
mas o susto foi real.

Como aconteceu: os testes chamam _processar_pdf com arquivos de mentira,
e o passo da OS agora mora dentro dele. Enquanto havia um defeito na
fila, esse passo parava antes de chegar ao banco - e a suite parecia
inofensiva. Consertado o defeito, ela passou a escrever no banco da
empresa. Ou seja: a seguranca era um acidente, e acidente nao segura
estoque.

Agora conectar() levanta SemLigacao em qualquer teste. O programa ja sabe
lidar com isso - e o caminho de 'GEREMPRE fora do ar', que faz a chapa
sair e o lancamento ficar para a mao -, entao os testes exercitam um
caminho de verdade em vez de um banco de verdade.

Sao duas camadas, e de proposito:

  1. conectar() levanta SemLigacao. E a trava dura: nao ha como um teste
     alcancar o banco, nem por caminho que ninguem previu;
  2. o passo da OS devolve None. Sem isto, todo teste de arte teria de
     conviver com a pendencia de 'GEREMPRE fora do ar' - um aviso certo,
     que atrapalha quem esta falando de cor e de formato.

Quem quiser exercitar o passo da OS pede 'com_os', que devolve o de
verdade - continuando sem banco, entao ele so anda ate a SemLigacao:

    def test_algo(com_os):
        ...
"""

import pytest

from finart_ctp import gerempre, processador, prova, utils


@pytest.fixture(autouse=True)
def pasta_de_controle_de_mentira(monkeypatch, tmp_path):
    """
    Nenhum teste escreve na PASTA_CONTROLE de verdade - nem no log.

    Descoberto em 11/09/2026 lendo o log de producao: as 08:05 havia
    dezenas de linhas 'GEREMPRE: abri a OS 19150 para SOLIDA' e 'OS 19605
    ENTREGUE'. Nao era a FIA - era a SUITE, rodada as 08:00. O log() de
    utils grava em <PASTA_CONTROLE>\_log_ctp.txt, e nada o redirecionava.
    O registro (_processados.json) e a fila passam pela mesma pasta.

    Log de teste no log de producao e pior que ruido: o operador le
    'abri a OS 19150' e vai procurar uma OS que nao existe.
    """
    monkeypatch.setattr(utils, "PASTA_CONTROLE", str(tmp_path / "_controle"))


@pytest.fixture(autouse=True)
def livro_de_impressao_de_mentira(monkeypatch, tmp_path):
    """
    Nenhum teste escreve no livro de impressao DE VERDADE.

    A trava de copia unica (prova.imprimir) guarda o que ja saiu num
    arquivo na PASTA_CONTROLE. Sem isolar, dois problemas juntos:

      1. os testes sujam o livro da maquina com nomes de mentira;
      2. pior - o PRIMEIRO teste que imprime anota, e os SEGUINTES batem
         na trava e quebram. Foi o que aconteceu ao escrever a trava:
         tres testes de prova cairam de uma vez, todos usando o mesmo
         'qualquer.pdf'.

    Cada teste ganha um livro proprio, vazio.
    """
    monkeypatch.setattr(prova, "PASTA_CONTROLE", str(tmp_path / "_livro"))


@pytest.fixture(autouse=True)
def gerempre_desligado(monkeypatch):
    """O GEREMPRE nao existe, a menos que o teste peca um."""
    def recusar(*a, **k):
        raise gerempre.SemLigacao(
            "os testes nao falam com o GEREMPRE de verdade "
            "(veja tests/conftest.py)")

    monkeypatch.setattr(gerempre, "conectar", recusar)
    # (numero, fechou_a_quarta) - o segundo diz se ESTE arquivo encheu a
    # ultima vaga, que e o sinal para dar a OS por entregue depois da
    # prova. Sem OS, nada fecha.
    monkeypatch.setattr(processador, "_os_do_arquivo",
                        lambda nome, cliente, planos: (None, False))


_PASSO_DA_OS = processador._os_do_arquivo      # guardado antes de qualquer
#                                                patch, na importacao


@pytest.fixture
def com_os(monkeypatch):
    """Devolve o passo da OS de verdade, para quem quiser exercita-lo."""
    monkeypatch.setattr(processador, "_os_do_arquivo", _PASSO_DA_OS)
    return _PASSO_DA_OS
