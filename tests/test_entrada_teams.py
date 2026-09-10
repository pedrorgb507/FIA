# -*- coding: utf-8 -*-
r"""
Testes da ponte do Teams.

Nenhum encosta no OneDrive nem na rede: a 'pasta sincronizada' aqui e
uma pasta comum do tmp_path, que e exatamente o que ela e na maquina de
verdade depois que o OneDrive termina de baixar.
"""

import io
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
    monkeypatch.setattr(T, "CAIXAS_TEAMS", {})
    monkeypatch.setattr(T, "CLIENTES_NO_TEAMS", ("SOLIDA",))
    # A pausa da rajada existe para dar tempo de Ctrl+C. Num teste ela
    # so faria a suite dormir.
    monkeypatch.setattr(T, "ESPERA_RAJADA", 0)
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
    caminho = os.path.join(str(pasta), nome)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def pasta_do_dia_de(base):
    return T.pasta_destino_do_dia(base)


def pendencias(tmp_path):
    try:
        with io.open(os.path.join(str(tmp_path / "_ctrl"), "_PENDENCIAS.txt"),
                     encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError):
        return ""


# ----------------------------------------------------------------------
# Quais caixas existem
# ----------------------------------------------------------------------

def test_sem_pasta_teams_a_ponte_fica_desligada(monkeypatch):
    monkeypatch.setattr(T, "PASTA_TEAMS", "")
    assert T.caixas() == []
    assert T.rodada() == 0


def test_cliente_fora_da_lista_nao_e_olhado(caixa, monkeypatch):
    """
    Quem nao manda pelo Teams nao vira aviso de pasta faltando.

    Sem isto, cinco clientes reclamariam a cada arranque e em duas
    semanas ninguem leria aviso nenhum - inclusive o que importa.
    """
    monkeypatch.setattr(T, "CLIENTES_NO_TEAMS", ("SOLIDA",))
    assert [c for c, _o, _b in T.caixas()] == ["SOLIDA"]


def test_caminho_proprio_do_cliente_ganha_do_padrao(caixa, tmp_path,
                                                    monkeypatch):
    """A porta para o dia em que o cliente sair da raiz comum."""
    propria = tmp_path / "outro lugar" / "EMPORIO"
    propria.mkdir(parents=True)
    monkeypatch.setattr(T, "CLIENTES_NO_TEAMS", ("SOLIDA", "EMPORIO"))
    monkeypatch.setattr(T, "BASE_ENTRADA_EMPORIO", str(tmp_path / "V" / "EMP"))
    monkeypatch.setattr(T, "CAIXAS_TEAMS", {"EMPORIO": str(propria)})

    caminhos = {c: o for c, o, _b in T.caixas()}
    assert caminhos["EMPORIO"] == str(propria)
    assert caminhos["SOLIDA"] == os.path.join(str(tmp_path / "teams"),
                                              "SOLIDA")


def test_caminho_proprio_funciona_sem_raiz(tmp_path, monkeypatch):
    """Cliente com caminho proprio anda mesmo com PASTA_TEAMS vazio."""
    propria = tmp_path / "so o emporio"
    propria.mkdir()
    monkeypatch.setattr(T, "PASTA_TEAMS", "")
    monkeypatch.setattr(T, "CLIENTES_NO_TEAMS", ("EMPORIO",))
    monkeypatch.setattr(T, "BASE_ENTRADA_EMPORIO", str(tmp_path / "V"))
    monkeypatch.setattr(T, "CAIXAS_TEAMS", {"EMPORIO": str(propria)})
    assert [c for c, _o, _b in T.caixas()] == ["EMPORIO"]


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
# Subpastas: o cliente organiza como quiser
# ----------------------------------------------------------------------

def test_desce_nas_subpastas(caixa):
    """Pasta postada pelo cliente nao pode sumir calada."""
    origem, base = caixa
    dentro = os.path.join(origem, "santinhos")
    os.makedirs(dentro)
    por_la(dentro, "GRADE 40.pdf")
    por_la(origem, "solto.pdf", b"outro")

    assert T.rodada() == 2

    destino = pasta_do_dia_de(base)
    assert sorted(os.listdir(destino)) == ["GRADE 40.pdf", "solto.pdf"]


def test_subpasta_achata_na_pasta_do_dia(caixa):
    """A subpasta e organizacao de quem manda, nao faz parte do servico."""
    origem, base = caixa
    fundo = os.path.join(origem, "a", "b", "c")
    os.makedirs(fundo)
    por_la(fundo, "fundo.pdf")

    T.rodada()
    assert os.path.isfile(os.path.join(pasta_do_dia_de(base), "fundo.pdf"))


def test_rotulo_diz_onde_o_arquivo_estava(caixa):
    origem, _base = caixa
    dentro = os.path.join(origem, "santinhos")
    os.makedirs(dentro)
    por_la(dentro, "GRADE 40.pdf")

    rotulos = [r for _c, r in T.arquivos_da_caixa(origem)]
    assert rotulos == [os.path.join("santinhos", "GRADE 40.pdf")]


def test_mesmo_nome_em_subpastas_diferentes_nao_se_sobrescreve(caixa,
                                                               tmp_path):
    origem, base = caixa
    um = os.path.join(origem, "manha")
    outro = os.path.join(origem, "tarde")
    os.makedirs(um)
    os.makedirs(outro)
    por_la(um, "grade.pdf", b"ARTE DA MANHA")
    por_la(outro, "grade.pdf", b"ARTE DA TARDE")

    assert T.rodada() == 2

    destino = pasta_do_dia_de(base)
    assert sorted(os.listdir(destino)) == ["grade.pdf", "grade_v2.pdf"]
    assert "versao DIFERENTE" in pendencias(tmp_path)


# ----------------------------------------------------------------------
# A pasta que a ponte nunca abre
# ----------------------------------------------------------------------

def test_arquivado_nao_atravessa(caixa):
    origem, base = caixa
    velho = os.path.join(origem, "Arquivado", "2025")
    os.makedirs(velho)
    por_la(velho, "antigo.pdf")
    por_la(origem, "novo.pdf", b"novo")

    assert T.rodada() == 1
    assert os.listdir(pasta_do_dia_de(base)) == ["novo.pdf"]


def test_arquivado_nao_depende_de_maiuscula(caixa):
    origem, base = caixa
    os.makedirs(os.path.join(origem, "ARQUIVADO"))
    por_la(os.path.join(origem, "ARQUIVADO"), "antigo.pdf")

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


def test_versao_diferente_vira_pendencia_com_o_nome_do_cliente(caixa,
                                                               tmp_path):
    origem, base = caixa
    destino = pasta_do_dia_de(base)
    por_la(destino, "49747.pdf", b"VELHA")
    por_la(origem, "49747.pdf", b"NOVA")
    T.rodada()

    texto = pendencias(tmp_path)
    assert "versao DIFERENTE" in texto
    assert "SOLIDA" in texto, "a pendencia tem de dizer a QUEM responder"


# ----------------------------------------------------------------------
# A rajada da segunda-feira
# ----------------------------------------------------------------------

def test_pendentes_olha_sem_tocar(caixa):
    origem, base = caixa
    por_la(origem, "um.pdf", b"um")
    por_la(origem, "dois.pdf", b"dois")

    fila = T.pendentes({})
    assert [c for c, _p, _r in fila] == ["SOLIDA", "SOLIDA"]
    assert os.listdir(pasta_do_dia_de(base)) == [], "nao podia ter trazido"


def test_rajada_nao_avisa_por_pouca_coisa(caixa, monkeypatch):
    origem, _base = caixa
    monkeypatch.setattr(T, "RAJADA", 3)
    por_la(origem, "um.pdf", b"um")
    assert T.anunciar_rajada({}) == 1


def test_rajada_avisa_quando_muita_coisa_esperou(caixa, monkeypatch, capsys):
    origem, _base = caixa
    monkeypatch.setattr(T, "RAJADA", 3)
    for n in range(4):
        por_la(origem, "arquivo%d.pdf" % n, b"conteudo %d" % n)

    assert T.anunciar_rajada({}) == 4

    tela = capsys.readouterr().out
    assert "4 arquivos esperando" in tela
    assert "arquivo0.pdf" in tela, "tem de DIZER quais, nao so quantos"
    assert "GEREMPRE" in tela, "tem de dizer o que vai acontecer"


def test_rajada_nao_conta_o_que_ja_atravessou(caixa, monkeypatch):
    origem, _base = caixa
    monkeypatch.setattr(T, "RAJADA", 1)
    por_la(origem, "um.pdf", b"um")
    T.rodada()
    assert T.anunciar_rajada(T.carregar_trazidos()) == 0


# ----------------------------------------------------------------------
# A ponte nao emudece
# ----------------------------------------------------------------------

def test_pasta_que_sumiu_grita_no_log(caixa, capsys):
    origem, _base = caixa
    os.rmdir(origem)                    # o OneDrive parou, ou deslogou

    assert T.rodada() == 0

    tela = capsys.readouterr().out
    assert "sumiu" in tela
    assert "SOLIDA" in tela


def test_pasta_que_sumiu_so_grita_uma_vez(caixa, capsys):
    origem, _base = caixa
    os.rmdir(origem)
    avisados = set()

    T.rodada(avisados=avisados)
    capsys.readouterr()
    T.rodada({}, avisados)

    assert "sumiu" not in capsys.readouterr().out


def test_arranque_reclama_da_pasta_que_nao_existe(caixa, capsys, monkeypatch):
    origem, _base = caixa
    os.rmdir(origem)
    monkeypatch.setattr(T, "onedrive_de_pe", lambda: True)

    T.conferir_no_arranque()

    tela = capsys.readouterr().out
    assert "NAO existe" in tela
    assert "Sincronize" in tela


def test_arranque_reclama_do_onedrive_parado(caixa, capsys, monkeypatch):
    monkeypatch.setattr(T, "onedrive_de_pe", lambda: False)
    T.conferir_no_arranque()
    assert "OneDrive NAO esta rodando" in capsys.readouterr().out


def test_arranque_cala_quando_nao_da_para_saber(caixa, capsys, monkeypatch):
    """Alarme falso ensina o operador a ignorar alarme."""
    monkeypatch.setattr(T, "onedrive_de_pe", lambda: None)
    T.conferir_no_arranque()
    assert "OneDrive NAO esta rodando" not in capsys.readouterr().out


def test_onedrive_indeciso_quando_nao_da_para_perguntar(monkeypatch):
    def explodir(*a, **k):
        raise OSError("tasklist nao existe aqui")

    monkeypatch.setattr(T.subprocess, "run", explodir)
    assert T.onedrive_de_pe() is None


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
