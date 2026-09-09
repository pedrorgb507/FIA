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

from finart_ctp import gerempre, processador


@pytest.fixture(autouse=True)
def gerempre_desligado(monkeypatch):
    """O GEREMPRE nao existe, a menos que o teste peca um."""
    def recusar(*a, **k):
        raise gerempre.SemLigacao(
            "os testes nao falam com o GEREMPRE de verdade "
            "(veja tests/conftest.py)")

    monkeypatch.setattr(gerempre, "conectar", recusar)
    monkeypatch.setattr(processador, "_os_do_arquivo",
                        lambda nome, cliente, planos: None)


_PASSO_DA_OS = processador._os_do_arquivo      # guardado antes de qualquer
#                                                patch, na importacao


@pytest.fixture
def com_os(monkeypatch):
    """Devolve o passo da OS de verdade, para quem quiser exercita-lo."""
    monkeypatch.setattr(processador, "_os_do_arquivo", _PASSO_DA_OS)
    return _PASSO_DA_OS
