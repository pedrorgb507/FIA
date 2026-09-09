# -*- coding: utf-8 -*-
r"""
Testes da ponte do Teams.

Nenhum encosta no OneDrive nem na rede: a 'pasta sincronizada' aqui e
uma pasta comum do tmp_path, que e exatamente o que ela e na maquina de
verdade depois que o OneDrive termina de baixar.
"""

import os

import pytest

import finart_ctp.entrada_teams as T
import finart_ctp.utils as U


@pytest.fixture(autouse=True)
def fora_da_maquina(monkeypatch, tmp_path):
    """Nada de teste encosta nas pastas de verdade desta maquina."""
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl"))
    monkeypatch.setattr(T, "PASTA_CONTROLE", str(tmp_path / "_ctrl"))
    # arquivo_estavel dorme 2 segundos olhando o tamanho crescer. Na
    # maquina isso e o que impede chapa de arte pela metade; aqui os
    # arquivos ja nascem prontos.
    monkeypatch.setattr(T, "arquivo_estavel", lambda caminho: True)


@pytest.fixture
def caixa(tmp_path, monkeypatch):
    """(origem, base) - a pasta sincronizada e a pasta do cliente no V:."""
    origem = tmp_path / "teams" / "SOLIDA"
    origem.mkdir(parents=True)
    base = tmp_path / "V" / "SOLIDA Grafica"
    base.mkdir(parents=True)
    monkeypatch.setattr(T, "PASTA_TEAMS", str(tmp_path / "teams"))
    monkeypatch.setattr(T, "BASE_ENTRADA", str(base))
    return str(origem), str(base)


def por_la(pasta, nome, conteudo=b"%PDF-1.4 arte"):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def pasta_do_dia_de(base):
    return T.pasta_destino_do_dia(base)


# ----------------------------------------------------------------------
# Quais caixas existem
# ----------------------------------------------------------------------

def test_sem_pasta_teams_a_ponte_fica_desligada(monkeypatch):
    monkeypatch.setattr(T, "PASTA_TEAMS", "")
    assert T.caixas() == []
    assert T.rodada() == 0


def test_so_entra_cliente_com_pasta_criada(caixa, tmp_path, monkeypatch):
    monkeypatch.setattr(T, "BASE_ENTRADA_VOPRIX", str(tmp_path / "V" / "VOPRIX"))
    nomes = [c for c, _o, _b in T.caixas()]
    assert nomes == ["SOLIDA"]          # a pasta VOPRIX nao existe no teams


# ----------------------------------------------------------------------
# A travessia
# ----------------------------------------------------------------------

def test_arquivo_novo_atravessa(caixa):
    origem, base = caixa
    por_la(origem, "49747 - Le Creuset - panfleto.pdf")

    assert T.rodada() == 1

    destino = pasta_do_dia_de(base)
    assert os.path.isfile(
        os.path.join(destino, "49747 - Le Creuset - panfleto.pdf"))


def test_o_original_nunca_e_apagado(caixa):
    origem, _base = caixa
    ficou = por_la(origem, "grade.pdf")
    T.rodada()
    assert os.path.isfile(ficou)


def test_nao_atravessa_duas_vezes(caixa):
    origem, _base = caixa
    por_la(origem, "grade.pdf")
    assert T.rodada() == 1
    assert T.rodada() == 0              # o registro segura


def test_arte_que_nao_vira_chapa_tambem_atravessa(caixa):
    """O .cdr precisa CHEGAR na pasta para virar pendencia la."""
    origem, base = caixa
    por_la(origem, "envelope.cdr", b"CDR")
    assert T.rodada() == 1
    assert os.path.isfile(os.path.join(pasta_do_dia_de(base), "envelope.cdr"))


def test_lixo_nao_atravessa(caixa):
    origem, base = caixa
    por_la(origem, "Thumbs.db", b"lixo")
    por_la(origem, "anotacao.txt", b"lixo")
    assert T.rodada() == 0
    assert os.listdir(pasta_do_dia_de(base)) == []


def test_arquivo_so_na_nuvem_espera(caixa, monkeypatch):
    origem, base = caixa
    por_la(origem, "pesado.pdf")
    monkeypatch.setattr(T, "so_na_nuvem", lambda caminho: True)
    assert T.rodada() == 0
    assert os.listdir(pasta_do_dia_de(base)) == []


# ----------------------------------------------------------------------
# Quando ja ha um arquivo com o mesmo nome na pasta do dia
# ----------------------------------------------------------------------

def test_igual_ao_que_ja_estava_nao_copia_de_novo(caixa):
    """O caso de hoje: alguem ja tinha salvo a mao antes da ponte existir."""
    origem, base = caixa
    destino = pasta_do_dia_de(base)
    por_la(destino, "49747.pdf", b"%PDF-1.4 arte")
    por_la(origem, "49747.pdf", b"%PDF-1.4 arte")

    assert T.rodada() == 0
    assert sorted(os.listdir(destino)) == ["49747.pdf"]


def test_versao_diferente_nao_sobrescreve(caixa):
    origem, base = caixa
    destino = pasta_do_dia_de(base)
    por_la(destino, "49747.pdf", b"%PDF-1.4 arte VELHA")
    por_la(origem, "49747.pdf", b"%PDF-1.4 arte CORRIGIDA")

    assert T.rodada() == 1

    with open(os.path.join(destino, "49747.pdf"), "rb") as f:
        assert f.read() == b"%PDF-1.4 arte VELHA"      # intacta
    with open(os.path.join(destino, "49747_v2.pdf"), "rb") as f:
        assert f.read() == b"%PDF-1.4 arte CORRIGIDA"


def test_versao_diferente_vira_pendencia(caixa, tmp_path):
    origem, base = caixa
    destino = pasta_do_dia_de(base)
    por_la(destino, "49747.pdf", b"VELHA")
    por_la(origem, "49747.pdf", b"NOVA")
    T.rodada()

    assert U.pendencias_abertas(), "a troca de versao tem de chamar gente"


# ----------------------------------------------------------------------
# Detalhes que ja quebraram coisa parecida antes
# ----------------------------------------------------------------------

def test_nao_deixa_arquivo_pela_metade(caixa):
    """
    O monitor.py varre a mesma pasta a cada poucos segundos. Se a copia
    aparecesse com o nome final antes de terminar, ele gravaria chapa de
    arte incompleta.
    """
    origem, base = caixa
    por_la(origem, "grade.pdf")
    T.rodada()
    destino = pasta_do_dia_de(base)
    assert not [n for n in os.listdir(destino) if n.startswith("~")]


def test_parcial_some_quando_a_copia_falha(caixa, monkeypatch):
    origem, base = caixa
    por_la(origem, "grade.pdf")

    def falhar(*a, **k):
        raise OSError("o OneDrive nao conseguiu baixar")

    monkeypatch.setattr(T.shutil, "copy2", falhar)
    assert T.rodada() == 0

    destino = pasta_do_dia_de(base)
    assert os.listdir(destino) == []


def test_cria_a_pasta_do_dia_se_nao_existir(caixa):
    """Arquivo que chega as 7h precisa ter onde cair."""
    origem, base = caixa
    por_la(origem, "grade.pdf")
    T.rodada()
    esperado = os.path.join(base, U.localizar_pasta_mes(base), U.pasta_do_dia())
    assert os.path.isdir(esperado)


def test_destino_livre_mantem_a_extensao(tmp_path):
    pasta = str(tmp_path)
    assert T.destino_livre(pasta, "a.pdf") == os.path.join(pasta, "a.pdf")
    por_la(pasta, "a.pdf")
    assert T.destino_livre(pasta, "a.pdf") == os.path.join(pasta, "a_v2.pdf")
    por_la(pasta, "a_v2.pdf")
    assert T.destino_livre(pasta, "a.pdf") == os.path.join(pasta, "a_v3.pdf")


def test_o_temporario_da_ponte_nao_atravessa(caixa):
    """Nome comecado por '~' e sobra, dos dois lados da ponte."""
    origem, base = caixa
    por_la(origem, "~grade.pdf.parcial", b"metade")
    assert T.rodada() == 0
    assert os.listdir(pasta_do_dia_de(base)) == []
