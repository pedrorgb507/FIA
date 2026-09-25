# -*- coding: utf-8 -*-
r"""
A pendencia dita em voz alta (voz.py) - pedido do operador em 25/09/2026.

Nenhum teste aqui fala de verdade: o conftest troca o voz._dizer por um
coto, e os que precisam ver a frase sair trocam o falar por uma lista.
"""

import io
import json

from finart_ctp import utils, voz

# guardado na importacao, antes de o conftest o trocar por um coto
_DIZER_ORIGINAL = voz._dizer

SUMIU = ("a FIA lancou este servico na vaga 2 da OS 19990 em 2026, e ele "
         "NAO ESTA MAIS LA. A OS era de outro operador.")


def test_a_frase_e_a_mesma_da_conversa():
    f = voz.frase("50190 - FLAVIOS - PANFLETO", SUMIU, "SOLIDA")
    assert f.startswith("Aten\u00e7\u00e3o, pend\u00eancia da SOLIDA. O 50190:")
    assert "OS 19990 sumiu" in f and "lan\u00e7ar \u00e0 m\u00e3o" in f


def test_sem_cliente_nao_fica_buraco():
    assert voz.frase("x.pdf", "algo deu errado", None).startswith(
        "Aten\u00e7\u00e3o, pend\u00eancia. O arquivo x:")


def test_a_mesma_pendencia_so_e_dita_uma_vez_no_dia(tmp_path, monkeypatch):
    """
    24/09/2026: "voce esta me avisando pendencia dessa chapa da emporio
    sem parar". A memoria mora em disco: sobrevive ao reinicio do vigia.
    """
    ditas = []
    monkeypatch.setattr(voz, "falar", ditas.append)
    assert voz.avisar_pendencia("a.pdf", SUMIU, "SOLIDA", pasta=str(tmp_path))
    assert voz.avisar_pendencia("a.pdf", SUMIU, "SOLIDA",
                                pasta=str(tmp_path)) is None
    assert len(ditas) == 1
    # outra pendencia fala
    assert voz.avisar_pendencia("b.pdf", SUMIU, "SOLIDA", pasta=str(tmp_path))
    assert len(ditas) == 2


def test_amanha_a_mesma_pendencia_fala_de_novo(tmp_path):
    assert not voz.ja_falada("a.pdf", "m", str(tmp_path), hoje="2026-09-25")
    assert voz.ja_falada("a.pdf", "m", str(tmp_path), hoje="2026-09-25")
    assert not voz.ja_falada("a.pdf", "m", str(tmp_path), hoje="2026-09-26")
    # e a de ontem sai do arquivo: ele nao cresce para sempre
    guardado = json.load(io.open(tmp_path / voz.FALADAS, encoding="utf-8"))
    assert all(c.startswith("2026-09-26|") for c in guardado)


def test_memoria_estragada_fala_em_vez_de_quebrar(tmp_path):
    (tmp_path / voz.FALADAS).write_text("{nao e json", encoding="utf-8")
    assert voz.ja_falada("a.pdf", "m", str(tmp_path)) is False


def test_falhar_nao_derruba_quem_chamou(tmp_path, monkeypatch):
    def explode(*a):
        raise RuntimeError("sem alto-falante")
    monkeypatch.setattr(voz, "falar", explode)
    assert voz.avisar_pendencia("a.pdf", SUMIU, pasta=str(tmp_path)) is None


def test_o_texto_vai_pelo_ambiente_e_nao_pela_linha(monkeypatch):
    """Nome de cliente tem aspas e cifrao; na linha, virariam comando."""
    visto = {}

    def rodar(args, **k):
        visto["args"], visto["env"] = args, k["env"]
    monkeypatch.setattr(voz.subprocess, "run", rodar)
    texto = "o arquivo $(rm) 'x' \"y\""
    _DIZER_ORIGINAL(texto)
    assert visto["env"]["FIA_FALA"] == texto
    assert all(texto not in a for a in visto["args"])


def test_a_pendencia_chama_a_voz(monkeypatch):
    chamadas = []
    monkeypatch.setattr(utils, "VOZ_DE_PENDENCIA", True)
    monkeypatch.setattr(voz, "avisar_pendencia",
                        lambda *a, **k: chamadas.append(a))
    utils.anotar_pendencia("c.pdf", "motivo qualquer", "VIVA")
    assert chamadas == [("c.pdf", "motivo qualquer", "VIVA")]


def test_desligada_nao_fala(monkeypatch):
    chamadas = []
    monkeypatch.setattr(utils, "VOZ_DE_PENDENCIA", False)
    monkeypatch.setattr(voz, "avisar_pendencia",
                        lambda *a, **k: chamadas.append(a))
    utils.anotar_pendencia("c.pdf", "motivo qualquer", "VIVA")
    assert chamadas == []


def test_fonte_ascii():
    io.open(voz.__file__, encoding="ascii").read()
