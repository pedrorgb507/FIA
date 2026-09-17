# -*- coding: utf-8 -*-
"""
O cache do pywin32, que o Windows apaga pela metade.

Em 17/09/2026 a PRIME ficou a manha inteira sem converter. O log dizia

    O.S PL DIEYME - SANTINHOS NOVO1.cdr: CorelDRAW nao converteu:
    module 'win32com.gen_py.95E23C91-...x0x27x0' has no attribute
    'CLSIDToClassMap'

e na chamada seguinte a mesma coisa com 'CLSIDToPackageMap'. Nao era o
CorelDRAW: era o pywin32. Ele guarda os involucros que gera da biblioteca
da Corel dentro do %TEMP%, e o Windows limpa o %TEMP% sozinho - naquele
dia levou os arquivos .py e deixou o __pycache__ para tras. O Python
achou a pasta, nao achou fonte nenhuma, e importou um modulo VAZIO.

O conserto e apagar o cache, que se refaz sozinho em segundos. Estes
testes provam que o programa faz isso por conta propria, porque a faxina
do %TEMP% vai acontecer de novo.
"""

import sys
import types

import pytest

from finart_ctp import corel


class _ComFalso(object):
    """Um win32com.client de mentira, para nao depender da maquina."""

    def __init__(self, falhas, erro):
        self.falhas = falhas          # quantas vezes ainda vai falhar
        self.erro = erro
        self.chamadas = 0

    def Dispatch(self, progid):
        self.chamadas += 1
        if self.falhas > 0:
            self.falhas -= 1
            raise self.erro
        return "aplicacao do CorelDRAW"


@pytest.fixture
def com_falso(monkeypatch):
    """Troca o win32com.client e a limpeza, sem tocar no cache real."""
    limpezas = []
    # o aviso vai para o _log_ctp.txt de verdade; aqui nao suja nada
    from finart_ctp import utils
    monkeypatch.setattr(utils, "log", lambda *a, **k: None)

    def montar(falhas=1, erro=None):
        erro = erro or AttributeError(
            "module 'win32com.gen_py.95E23C91-BC5A-49F3-8CD1-"
            "1FC515597048x0x27x0' has no attribute 'CLSIDToClassMap'")
        falso = _ComFalso(falhas, erro)
        modulo = types.ModuleType("win32com.client")
        modulo.Dispatch = falso.Dispatch
        monkeypatch.setitem(sys.modules, "win32com.client", modulo)
        # 'import win32com.client' pega o atributo do pacote, nao o
        # sys.modules - os dois tem de apontar para o mesmo falso
        import win32com
        monkeypatch.setattr(win32com, "client", modulo, raising=False)
        monkeypatch.setattr(corel, "limpar_cache_do_pywin32",
                            lambda: limpezas.append(1))
        return falso

    montar.limpezas = limpezas
    return montar


# ----------------------------------------------------------------------
# A SEGUNDA TENTATIVA
# ----------------------------------------------------------------------

def test_cache_quebrado_e_apagado_e_a_conversao_segue(com_falso):
    falso = com_falso(falhas=1)
    assert corel._aplicacao() == "aplicacao do CorelDRAW"
    assert falso.chamadas == 2, "tinha de tentar de novo depois de limpar"
    assert len(com_falso.limpezas) == 1


def test_o_outro_nome_do_mesmo_defeito_tambem_cura(com_falso):
    # o segundo arquivo da PRIME morreu com CLSIDToPackageMap
    falso = com_falso(falhas=1, erro=AttributeError(
        "module 'win32com.gen_py.95E23C91-...' has no attribute "
        "'CLSIDToPackageMap'"))
    assert corel._aplicacao() == "aplicacao do CorelDRAW"
    assert falso.chamadas == 2


def test_importerro_no_cache_tambem_e_tratado(com_falso):
    falso = com_falso(falhas=1, erro=ImportError("No module named gen_py"))
    assert corel._aplicacao() == "aplicacao do CorelDRAW"
    assert falso.chamadas == 2


def test_limpa_UMA_vez_so_e_nao_fica_em_laco(com_falso):
    """Corel realmente ausente nao pode virar limpeza sem fim."""
    com_falso(falhas=9)
    with pytest.raises(AttributeError):
        corel._aplicacao()
    assert len(com_falso.limpezas) == 1, "uma limpeza, uma retentativa"


def test_quando_da_certo_de_primeira_nao_mexe_no_cache(com_falso):
    falso = com_falso(falhas=0)
    assert corel._aplicacao() == "aplicacao do CorelDRAW"
    assert falso.chamadas == 1
    assert com_falso.limpezas == [], "cache bom nao se apaga"


def test_erro_de_outra_natureza_sobe_sem_apagar_cache(com_falso):
    """
    Corel fechado da erro de COM, e apagar o cache nao ajuda em nada.

    Limpar por qualquer erro custaria uma regeracao de involucros a cada
    passada do vigia com a Corel fechada - lento, e escondendo a causa.
    """
    com_falso(falhas=1, erro=RuntimeError("CorelDRAW nao esta aberto"))
    with pytest.raises(RuntimeError):
        corel._aplicacao()
    assert com_falso.limpezas == []


# ----------------------------------------------------------------------
# A LIMPEZA EM SI
# ----------------------------------------------------------------------

def test_a_limpeza_tira_os_gen_py_do_sys_modules(monkeypatch, tmp_path):
    """
    Nao basta apagar do disco: o modulo vazio ja esta importado.

    Sem tirar do sys.modules, a segunda tentativa pega o mesmo modulo sem
    atributo nenhum e o conserto nao aparece ate reiniciar o programa.
    """
    gencache = types.ModuleType("win32com.client.gencache")
    gencache.GetGeneratePath = lambda: str(tmp_path / "gen_py")
    gencache.Rebuild = lambda: None
    cliente = types.ModuleType("win32com.client")
    cliente.gencache = gencache
    monkeypatch.setitem(sys.modules, "win32com.client", cliente)
    monkeypatch.setitem(sys.modules, "win32com.client.gencache", gencache)

    sujo = tmp_path / "gen_py" / "95E23C91x0x27x0"
    sujo.mkdir(parents=True)
    (sujo / "__pycache__").mkdir()          # foi so isto que sobrou
    monkeypatch.setitem(sys.modules, "win32com.gen_py", types.ModuleType("x"))
    monkeypatch.setitem(sys.modules, "win32com.gen_py.95E23C91x0x27x0",
                        types.ModuleType("x"))

    pasta = corel.limpar_cache_do_pywin32()

    assert not sujo.exists(), "o restinho quebrado tem de sair do disco"
    assert pasta and tmp_path.name in pasta
    assert "win32com.gen_py" not in sys.modules
    assert "win32com.gen_py.95E23C91x0x27x0" not in sys.modules
