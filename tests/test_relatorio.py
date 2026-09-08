# -*- coding: utf-8 -*-
"""
O relatorio do dia - a parte de GESTAO do oficio.

Os numeros sempre existiram no log; ninguem lia, porque estavam
misturados com o resto do dia. Um procedimento que ninguem mede vira
habito, e habito ninguem melhora.

O relatorio nao inventa nada: le o que a FIA ja escreveu.
"""

from finart_ctp import relatorio


DIA = [
    "[08/09 08:06:14] Registro: 100 arquivo(s) ja processados antes.",
    "[08/09 08:36:18] '49694 - Gaspar - colinha.pdf': 1 pagina(s)",
    "[08/09 08:36:20]    impresso em KONICA (2 folhas, so frente)",
    "[08/09 08:37:07]    OK em 46s: 49694.pdf (C+M+Y+K, 12.4 MB)",
    "[08/09 09:00:00]    OK em 20s: 510x400_CMYK_VIVA_GRADE 1.pdf (C+M+Y+K, 8.0 MB)",
    "[08/09 09:10:00]    impresso em KONICA (1 folha, so frente)",
    "[08/09 09:20:00] >>> PENDENCIA: CUPOM.pdf | pagina 2: NAO veio em "
    "quadricromia - GRAY (C 0.0000)",
    "[08/09 09:30:00] >>> PENDENCIA: OUTRO.pdf | pagina 1: NAO veio em "
    "quadricromia - GRAY (C 0.0000 M 0.1)",
    "[08/09 10:00:00] >>> PENDENCIA: arte.cdr | veio em .cdr, nao em PDF",
    "[07/09 23:00:00]    OK em 10s: 49999.pdf (C+M+Y+K, 1.0 MB)",
]


def preparar(monkeypatch, linhas=None):
    monkeypatch.setattr(relatorio, "_linhas_do_log",
                        lambda: linhas if linhas is not None else DIA)
    monkeypatch.setattr(relatorio, "_registro", lambda: {"a": 1, "b": 2})


def test_conta_as_chapas_por_cliente(monkeypatch, capsys):
    preparar(monkeypatch)
    assert relatorio.do_dia("08", "SETEMBRO") == 2
    saida = capsys.readouterr().out
    assert "SOLIDA      1 chapa(s)" in saida
    assert "VIVA        1 chapa(s)" in saida


def test_nao_mistura_o_dia_de_ontem(monkeypatch, capsys):
    """A chapa das 23h do dia 7 nao entra na conta do dia 8."""
    preparar(monkeypatch)
    relatorio.do_dia("08", "SETEMBRO")
    assert "49999" not in capsys.readouterr().out


def test_soma_as_folhas_de_prova(monkeypatch, capsys):
    preparar(monkeypatch)
    relatorio.do_dia("08", "SETEMBRO")
    assert "3 folha(s) A4" in capsys.readouterr().out


def test_agrupa_as_pendencias_pelo_motivo(monkeypatch, capsys):
    """
    Cada pendencia traz o nome do arquivo e os numeros do caso, entao
    todas sao textos unicos. Sem agrupar, a contagem nao diria nada.
    """
    preparar(monkeypatch)
    relatorio.do_dia("08", "SETEMBRO")
    saida = capsys.readouterr().out
    assert "2 x  arte fora de quadricromia" in saida
    assert "1 x  veio em Corel, nao em PDF" in saida


def test_dia_sem_nada_no_log(monkeypatch, capsys):
    preparar(monkeypatch, linhas=[])
    assert relatorio.do_dia("08", "SETEMBRO") == 0
    assert "Nao ha nada no log" in capsys.readouterr().out


def test_dia_em_que_tudo_fechou_sozinho(monkeypatch, capsys):
    preparar(monkeypatch, linhas=[
        "[08/09 08:00:00]    OK em 10s: 49111.pdf (C+M+Y+K, 5.0 MB)"])
    relatorio.do_dia("08", "SETEMBRO")
    assert "tudo que chegou fechou sozinho" in capsys.readouterr().out
