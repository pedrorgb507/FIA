# -*- coding: utf-8 -*-
"""Testes rapidos: rode com  pytest  na raiz do projeto."""

import os

import pytest

import finart_ctp.utils as U
from finart_ctp.pdf_builder import _tint_transform
from finart_ctp.processador import identificar_formato
from finart_ctp.utils import normalizar


@pytest.fixture(autouse=True)
def fora_da_maquina(monkeypatch, tmp_path):
    """Nada de teste encosta nas pastas de verdade desta maquina."""
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


def test_formato_chapa_pequena():
    assert identificar_formato(510, 400) == (1000, "")
    assert identificar_formato(400, 510) == (1000, "")      # deitado


def test_formato_chapa_grande():
    assert identificar_formato(775, 635) == (800, "R1")


def test_formato_dentro_da_tolerancia():
    assert identificar_formato(512, 398) == (1000, "")


def test_formato_fora_do_padrao():
    assert identificar_formato(300, 200) == (None, None)


def test_normalizar_mes():
    assert normalizar("MARÇO") == "MARCO"
    assert normalizar(" Marco ") == "MARCO"
    assert normalizar("Fevereiro") == "FEVEREIRO"


def test_tint_transform_uma_tinta():
    assert _tint_transform(["K"]).startswith("{")
    assert _tint_transform(["K"]).endswith("}")


def test_tint_transform_duas_tintas():
    saida = _tint_transform(["M", "K"])
    assert "roll" in saida and saida.count("pop") == 2


def test_etiqueta_por_formato():
    from finart_ctp.processador import rotulo_prova
    assert rotulo_prova(510, 400) == "SOLIDA F4"
    assert rotulo_prova(400, 510) == "SOLIDA F4"      # deitado, mesmo formato
    assert rotulo_prova(775, 635) == "SOLIDA F2"
    assert rotulo_prova(635, 775) == "SOLIDA F2"


def test_etiqueta_vazia_para_formato_desconhecido():
    from finart_ctp.processador import rotulo_prova
    assert rotulo_prova(300, 200) == ""


def test_arquivo_gigante_vira_pendencia(monkeypatch, tmp_path):
    """Nao processa, nao imprime, e avisa: e o caso do PDF de 2,2 GB."""
    import finart_ctp.processador as P

    grande = tmp_path / "49999 - Cliente - cartaz.pdf"
    grande.write_bytes(b"%PDF-1.4 nem precisa ser valido")

    monkeypatch.setattr(P, "TAMANHO_MAXIMO_MB", 0)          # tudo e gigante
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo, cliente=None: avisos.append((arq, motivo)))
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(P, "imprimir",
                        lambda *a, **k: pytest.fail("nao pode imprimir"))

    r = P.processar(str(grande), str(tmp_path / "saida"))

    assert r["status"] == "erro"
    assert "gigante" in r["motivo"]
    assert len(avisos) == 1 and "gigante" in avisos[0][1]


def test_arquivo_dentro_do_limite_nao_e_barrado(monkeypatch, tmp_path):
    import finart_ctp.processador as P

    pequeno = tmp_path / "49999 - Cliente - cartaz.pdf"
    pequeno.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "TAMANHO_MAXIMO_MB", 500)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)
    monkeypatch.setattr(P, "log", lambda *a, **k: None)

    r = P.processar(str(pequeno), str(tmp_path / "saida"))
    # passa do limite e falha adiante, na leitura do PDF - nao por tamanho
    assert "gigante" not in r["motivo"]


# ----------------------------------------------------------------------
# A ESPERA DA REDE: uma so, para a lista inteira
# ----------------------------------------------------------------------
# Perguntando um a um, uma pasta com vinte arquivos dorme quarenta
# segundos - e quem espera essa resposta e uma tela de gente.

def _sem_dormir(monkeypatch, contador):
    monkeypatch.setattr(U.time, "sleep",
                        lambda s: contador.append(s))


def test_a_espera_da_rede_e_UMA_para_a_lista_inteira(monkeypatch, tmp_path):
    dormiu = []
    _sem_dormir(monkeypatch, dormiu)
    muitos = []
    for n in range(20):
        arq = tmp_path / ("arte %02d.pdf" % n)
        arq.write_bytes(b"x" * (n + 1))
        muitos.append(str(arq))

    assert sorted(U.arquivos_estaveis(muitos)) == sorted(muitos)
    assert dormiu == [U.ESPERA_DA_REDE], \
        "vinte arquivos nao podem virar vinte esperas"


def test_quem_ainda_cresce_fica_de_fora(monkeypatch, tmp_path):
    """O arquivo cresce DURANTE a espera - e como e na rede de verdade."""
    parado = tmp_path / "parado.pdf"
    parado.write_bytes(b"x" * 100)
    crescendo = tmp_path / "crescendo.pdf"
    crescendo.write_bytes(b"x" * 100)

    def dormir_e_crescer(_):
        with open(str(crescendo), "ab") as f:
            f.write(b"mais um pedaco que chegou")

    monkeypatch.setattr(U.time, "sleep", dormir_e_crescer)
    assert U.arquivos_estaveis([str(parado), str(crescendo)]) == [str(parado)]


def test_arquivo_vazio_nao_conta_como_pronto(monkeypatch, tmp_path):
    """Zero byte e a copia que ainda nem comecou."""
    _sem_dormir(monkeypatch, [])
    vazio = tmp_path / "vazio.pdf"
    vazio.write_bytes(b"")
    assert U.arquivos_estaveis([str(vazio)]) == []


def test_arquivo_que_sumiu_no_meio_da_espera_nao_estoura(monkeypatch,
                                                         tmp_path):
    """Alguem moveu o arquivo enquanto se esperava. Nao e erro."""
    sumindo = tmp_path / "sumindo.pdf"
    sumindo.write_bytes(b"x" * 10)
    monkeypatch.setattr(U.time, "sleep", lambda s: os.remove(str(sumindo)))
    assert U.arquivos_estaveis([str(sumindo)]) == []


def test_lista_vazia_nem_espera(monkeypatch):
    dormiu = []
    _sem_dormir(monkeypatch, dormiu)
    assert U.arquivos_estaveis([]) == []
    assert dormiu == [], "sem arquivo nenhum nao ha o que esperar"


def test_arquivo_estavel_continua_respondendo_por_um_so(monkeypatch,
                                                        tmp_path):
    """
    O arquivo_estavel e o caso de um arquivo so da mesma conta - o resto
    do programa chama ele as centenas.
    """
    _sem_dormir(monkeypatch, [])
    pronto = tmp_path / "pronto.pdf"
    pronto.write_bytes(b"x" * 10)
    assert U.arquivo_estavel(str(pronto)) is True
    assert U.arquivo_estavel(str(tmp_path / "nao existe.pdf")) is False
