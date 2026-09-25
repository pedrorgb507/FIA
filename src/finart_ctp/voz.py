# -*- coding: utf-8 -*-
r"""
A FIA FALA A PENDENCIA EM VOZ ALTA, no alto-falante desta maquina.

Pedido do operador em 25/09/2026: "eu quero q ela avise quando tiver
pendencias tambem, fale em voz alta no computador".

A tela cheia (tela.py) ja chama quem esta perto. A voz alcanca quem
NAO esta olhando: a maquina de chapa fica do outro lado da sala, e uma
janela so e vista por quem vira a cabeca. Ouvir nao pede isso.

QUEM FALA E O WINDOWS, e nao o navegador: a voz "Microsoft Maria"
(pt-BR) vem instalada, funciona sem internet e sem pagina aberta. Medido
nesta maquina em 25/09/2026 - e a unica pt-BR do System.Speech aqui.

O QUE ELA DIZ e a mesma frase curta da conversa (conversa.py): "o
50190 da SOLIDA: a vaga dele na OS 19990 sumiu...". Uma so maneira de
contar a mesma pendencia, na tela de conversa e no alto-falante.

TRES CUIDADOS, e cada um tem o seu caso:

  - FALA EM OUTRO PROCESSO, numa fila propria. O vigia esta no meio de
    uma chapa quando a pendencia nasce; esperar a frase terminar - ou
    ver o PowerShell falhar - nao pode segurar nada. Tudo aqui engole o
    proprio erro, como a tela;

  - UMA DE CADA VEZ. Pendencia vem em rajada (o 50190 de 25/09 gerou
    tres em dez minutos), e tres vozes ao mesmo tempo nao se entendem;

  - A MESMA PENDENCIA NAO SE REPETE NO DIA. Em 24/09 o operador
    reclamou "voce esta me avisando pendencia dessa chapa da emporio sem
    parar" - era a tela, a cada reinicio. A memoria mora em disco pelo
    mesmo motivo que a do aviso de arquivo estranho: o vigia reinicia
    varias vezes num dia ruim, e ouvir a mesma frase a cada arranque e
    o que faz alguem desligar o som.
"""

import datetime
import io
import json
import os
import queue
import subprocess
import threading

from . import config

# A memoria do que ja foi dito. So guarda o dia de hoje: amanha a mesma
# pendencia, se ainda estiver la, merece ser dita de novo.
FALADAS = "_pendencias_faladas.json"

# Quanto uma frase pode demorar. A mais longa das pendencias conhecidas
# leva uns 15 s na voz da Maria; passar muito disso e o PowerShell
# preso, e a fila nao pode ficar parada atras dele.
PRAZO_DA_FALA = 60

# Sem janela: o processo de fala nao pode piscar um console na frente de
# quem esta trabalhando.
SEM_JANELA = 0x08000000

# O texto vai pela VARIAVEL DE AMBIENTE, e nao pela linha de comando:
# nome de arquivo de cliente tem aspas, apostrofo e cifrao, e qualquer
# um deles quebraria a linha - ou pior, viraria comando.
FALAR_PS = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "try { $v = $s.GetInstalledVoices() | Where-Object { "
    "$_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | "
    "Select-Object -First 1; "
    "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) } } catch { }; "
    "$s.Volume = 100; $s.Speak($env:FIA_FALA)"
)


def frase(arquivo, motivo, cliente=None):
    """A pendencia contada em uma frase para ouvir."""
    from .conversa import _apelido, _com_acento, _motivo_falado
    de_quem = " da %s" % cliente if cliente else ""
    return _com_acento("Atencao, pendencia%s. %s: %s." % (
        de_quem, _apelido(arquivo)[0].upper() + _apelido(arquivo)[1:],
        _motivo_falado(motivo)))


def _caminho(pasta=None):
    return os.path.join(pasta or config.PASTA_CONTROLE, FALADAS)


def _chave(arquivo, motivo, hoje):
    return "%s|%s|%s" % (hoje, arquivo, (motivo or "")[:80])


def ja_falada(arquivo, motivo, pasta=None, hoje=None):
    """
    True se esta pendencia ja foi dita hoje; se nao, anota e diz False.

    Nunca estoura: falhando a leitura ou a escrita, o pior e falar de
    novo - que e o que acontecia antes de haver memoria.
    """
    hoje = hoje or datetime.date.today().isoformat()
    chave = _chave(arquivo, motivo, hoje)
    try:
        with io.open(_caminho(pasta), encoding="utf-8") as f:
            ditas = [c for c in json.load(f) if c.startswith(hoje + "|")]
    except Exception:
        ditas = []
    if chave in ditas:
        return True
    try:
        with io.open(_caminho(pasta), "w", encoding="utf-8") as f:
            f.write(json.dumps(ditas + [chave], ensure_ascii=False, indent=1))
    except Exception:
        pass
    return False


# A fila e a linha que a esvazia. A linha nasce na primeira fala e e
# 'daemon': o vigia pode sair sem esperar frase nenhuma terminar.
_fila = queue.Queue()
_linha = None
_trava = threading.Lock()


def _dizer(texto):
    """Fala e espera terminar. So a linha da fila chama isto."""
    ambiente = dict(os.environ, FIA_FALA=texto)
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-Command", FALAR_PS],
                       env=ambiente, creationflags=SEM_JANELA,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=PRAZO_DA_FALA)
    except Exception:
        pass


def _esvaziar():
    while True:
        texto = _fila.get()
        try:
            _dizer(texto)
        finally:
            _fila.task_done()


def falar(texto):
    """Poe a frase na fila. Volta na hora; a fala acontece por tras."""
    global _linha
    with _trava:
        if _linha is None or not _linha.is_alive():
            _linha = threading.Thread(target=_esvaziar, name="voz-da-fia",
                                      daemon=True)
            _linha.start()
    _fila.put(texto)


def avisar_pendencia(arquivo, motivo, cliente=None, pasta=None):
    """
    Fala a pendencia, se ainda nao foi dita hoje. Devolve o que disse,
    ou None. Nunca estoura: e aviso, e aviso nao derruba chapa.
    """
    try:
        if ja_falada(arquivo, motivo, pasta):
            return None
        texto = frase(arquivo, motivo, cliente)
        falar(texto)
        return texto
    except Exception:
        return None
