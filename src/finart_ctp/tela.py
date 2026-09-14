# -*- coding: utf-8 -*-
r"""
A TELA QUE CHAMA - quando a FIA precisa de gente, ela aparece.

    python -m finart_ctp.tela              abre com o que esta na fila
    python -m finart_ctp.tela --modelo     abre com exemplos, para ver

POR QUE ELA EXISTE. A pendencia sai em tres lugares, e os tres pedem que
alguem esteja olhando: a janela preta do programa, o _PENDENCIAS.txt e o
_log_ctp.txt. Quem esta na maquina de chapa, do outro lado da sala, nao
ve nenhum dos tres. Em 14/09/2026 houve dezesseis pendencias, e tres
delas eram servico que ja tinha saido gravado e ficou sem cobranca ate
alguem reparar, horas depois.

Entao a tela abre SOZINHA, EM TELA CHEIA, na hora em que o problema
acontece - e so sai quando alguem clica.

O QUE ELA NAO FAZ, de proposito:

  - NAO ACUMULA. Ela e o aviso do que esta acontecendo agora, e nao a
    lista do que esta pendente. Fechou, esvaziou. O que ficou por fazer
    continua no _PENDENCIAS.txt, que e o lugar dele;
  - nao resolve nada. Fechar so diz 'eu vi';
  - nao segura o programa. Roda em OUTRO processo - o Tk quer a linha
    principal so para ele, e uma janela travada nao pode travar o vigia
    no meio de uma chapa.
"""

import datetime
import io
import json
import os
import subprocess
import sys
import time

from .config import PASTA_CONTROLE

# A fila do que a tela tem de mostrar AGORA. Nasce quando aparece uma
# pendencia e morre quando alguem fecha a tela.
FILA = "_TELA_AGORA.json"

# Quem esta com a tela aberta. O arquivo carrega a hora, reescrita de
# tempos em tempos pela propria janela: assim uma janela que morreu de
# mau jeito nao tranca a tela para sempre.
TRANCA = "_TELA_ABERTA.lock"
BATIDA = 4.0                   # de quantos em quantos segundos ela bate
ABANDONADA = 20.0              # sem batida por tanto tempo, esta morta

OLHAR_A_FILA = 1000            # milissegundos entre uma olhada e outra

# ----------------------------------------------------------------------
# AS CORES
# ----------------------------------------------------------------------
# Fundo claro e letra escura: a sala e clara e a tela fica longe. A cor
# forte vai so na faixa de cima e na borda do cartao - e o que se ve de
# relance, do outro lado da sala.
VERMELHO = "#b3261e"
VERMELHO_ESCURO = "#8c1d18"
PAPEL = "#f7f5f3"
CARTAO = "#ffffff"
TINTA = "#1c1b1f"
TINTA_FRACA = "#5f5b57"
RISCO = "#e0dcd8"


def caminho_da_fila(pasta=None):
    return os.path.join(pasta or PASTA_CONTROLE, FILA)


def caminho_da_tranca(pasta=None):
    return os.path.join(pasta or PASTA_CONTROLE, TRANCA)


# ----------------------------------------------------------------------
# A FILA DO QUE MOSTRAR
# ----------------------------------------------------------------------

def _ler_json(caminho, vazio):
    try:
        with io.open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return vazio


def _gravar_json(caminho, dado):
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        meio = caminho + ".tmp"
        with io.open(meio, "w", encoding="utf-8") as f:
            json.dump(dado, f, ensure_ascii=False, indent=1)
        os.replace(meio, caminho)
        return True
    except OSError:
        return False


def enfileirar(arquivo, motivo, cliente=None, pasta=None, quando=None):
    """Poe mais um problema na fila da tela. Devolve a fila inteira."""
    fila = _ler_json(caminho_da_fila(pasta), [])
    if not isinstance(fila, list):
        fila = []
    quando = quando or datetime.datetime.now()
    fila.append({"quando": quando.strftime("%d/%m %H:%M"),
                 "cliente": (cliente or "").strip(),
                 "arquivo": (arquivo or "").strip(),
                 "motivo": (motivo or "").strip()})
    _gravar_json(caminho_da_fila(pasta), fila)
    return fila


def esvaziar(pasta=None):
    _gravar_json(caminho_da_fila(pasta), [])


def por_arquivo(fila):
    """
    A fila agrupada por ARQUIVO, na ordem em que os arquivos chegaram.

    Um .cdr de tres paginas sem marca de corte lanca quatro pendencias
    no mesmo segundo - uma por pagina, mais a do PDF guardado -, e
    quatro cartoes iguais empurram para fora da tela tudo o que veio
    depois. E UM arquivo com quatro coisas a dizer.
    """
    ordem = []
    juntas = {}
    for p in fila:
        nome = p.get("arquivo", "")
        cartao = juntas.get(nome)
        if cartao is None:
            cartao = {"quando": p.get("quando", ""),
                      "cliente": p.get("cliente", ""),
                      "arquivo": nome, "motivos": [], "quantos": {}}
            juntas[nome] = cartao
            ordem.append(nome)
        cartao["quando"] = p.get("quando", "") or cartao["quando"]
        cartao["cliente"] = cartao["cliente"] or p.get("cliente", "")
        motivo = p.get("motivo", "")
        if motivo in cartao["quantos"]:
            cartao["quantos"][motivo] += 1
        else:
            cartao["quantos"][motivo] = 1
            cartao["motivos"].append(motivo)

    cartoes = []
    for nome in ordem:
        c = juntas[nome]
        cartoes.append({"quando": c["quando"], "cliente": c["cliente"],
                        "arquivo": c["arquivo"],
                        "motivos": [(c["quantos"][m], m)
                                    for m in c["motivos"]]})
    return cartoes


# ----------------------------------------------------------------------
# A TRANCA - uma tela de cada vez
# ----------------------------------------------------------------------

def ha_tela_aberta(pasta=None, agora=None):
    """
    Ja ha uma janela no ar?

    Vale pela BATIDA, e nao pela existencia do arquivo: uma janela que
    morreu de mau jeito deixaria a tranca para tras e nenhuma pendencia
    voltaria a abrir a tela - calada, que e o pior defeito possivel
    numa coisa que existe para avisar.
    """
    marca = _ler_json(caminho_da_tranca(pasta), None)
    if not isinstance(marca, dict):
        return False
    agora = agora if agora is not None else time.time()
    return (agora - float(marca.get("batida") or 0)) < ABANDONADA


def trancar(pasta=None, agora=None):
    _gravar_json(caminho_da_tranca(pasta),
                 {"batida": agora if agora is not None else time.time(),
                  "processo": os.getpid()})


def destrancar(pasta=None):
    try:
        os.remove(caminho_da_tranca(pasta))
    except OSError:
        pass


def chamar(arquivo, motivo, cliente=None, pasta=None):
    """
    Poe o problema na fila e sobe a tela, se ainda nao houver uma.

    Havendo, nao sobe outra: a que esta no ar olha a fila sozinha e
    acrescenta o cartao. Duas janelas em tela cheia, uma por cima da
    outra, seriam duas para fechar.

    NUNCA levanta. Uma janela que nao abre nao pode parar o programa
    que grava chapa.
    """
    try:
        enfileirar(arquivo, motivo, cliente, pasta)
        if ha_tela_aberta(pasta):
            return False
        executavel = sys.executable
        sem_console = executavel.replace("python.exe", "pythonw.exe")
        if os.path.exists(sem_console):
            executavel = sem_console
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.Popen([executavel, "-m", "finart_ctp.tela"], cwd=raiz,
                         close_fds=True)
        return True
    except Exception:
        return False


# ----------------------------------------------------------------------
# A TELA
# ----------------------------------------------------------------------

def _fonte(tamanho, negrito=False):
    return ("Segoe UI", tamanho, "bold" if negrito else "normal")


def mostrar(cartoes, pasta=None, ao_fechar=None, seguir=True):
    """
    Poe a tela CHEIA na frente de tudo. So volta quando alguem a fecha.

    'seguir' faz a janela reler a fila enquanto esta aberta: pendencia
    que aparecer agora entra nela em vez de abrir uma segunda janela.
    """
    import tkinter as tk

    janela = tk.Tk()
    janela.title("FINART CTP - precisa de voce")
    janela.configure(bg=PAPEL)
    janela.attributes("-fullscreen", True)
    janela.attributes("-topmost", True)
    janela.lift()
    try:
        janela.focus_force()
    except tk.TclError:
        pass

    estado = {"cartoes": list(cartoes), "vivo": True}

    def fechar(_evento=None):
        if not estado["vivo"]:
            return
        estado["vivo"] = False
        if ao_fechar:
            try:
                ao_fechar()
            except Exception:
                pass
        janela.destroy()

    # Esc fecha tambem. Numa janela em tela cheia isso nao e conforto: e
    # a saida de emergencia se o botao nao aparecer por qualquer motivo.
    janela.bind("<Escape>", fechar)
    janela.protocol("WM_DELETE_WINDOW", fechar)

    # --- a faixa de cima ------------------------------------------------
    faixa = tk.Frame(janela, bg=VERMELHO)
    faixa.pack(fill="x")
    titulo = tk.Label(faixa, text="", bg=VERMELHO, fg="white",
                      font=_fonte(34, True), anchor="w", padx=40)
    titulo.pack(fill="x", pady=(24, 2))
    tk.Label(faixa,
             text="a chapa nao para por causa disto - mas o lancamento, sim",
             bg=VERMELHO, fg="#f3d6d3", font=_fonte(14), anchor="w",
             padx=42).pack(fill="x", pady=(0, 24))

    # --- a lista, com rolagem -------------------------------------------
    meio = tk.Frame(janela, bg=PAPEL)
    meio.pack(fill="both", expand=True)

    tela = tk.Canvas(meio, bg=PAPEL, highlightthickness=0)
    barra = tk.Scrollbar(meio, orient="vertical", command=tela.yview)
    dentro = tk.Frame(tela, bg=PAPEL)

    dentro.bind("<Configure>",
                lambda e: tela.configure(scrollregion=tela.bbox("all")))
    quadro = tela.create_window((0, 0), window=dentro, anchor="nw")
    tela.bind("<Configure>",
              lambda e: tela.itemconfigure(quadro, width=e.width))
    tela.configure(yscrollcommand=barra.set)
    tela.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    janela.bind_all("<MouseWheel>",
                    lambda e: tela.yview_scroll(-1 * (e.delta // 120),
                                                "units"))

    def desenhar():
        for filho in dentro.winfo_children():
            filho.destroy()
        quantos = len(estado["cartoes"])
        titulo.configure(
            text="1 COISA PRECISA DE VOCE" if quantos == 1
            else "%d COISAS PRECISAM DE VOCE" % quantos)
        for c in estado["cartoes"]:
            _cartao(tk, dentro, c)
        if not estado["cartoes"]:
            tk.Label(dentro, text="nada em aberto", bg=PAPEL,
                     fg=TINTA_FRACA, font=_fonte(18), pady=60).pack()

    desenhar()

    # --- o botao --------------------------------------------------------
    pe = tk.Frame(janela, bg=PAPEL)
    pe.pack(fill="x")
    tk.Frame(pe, bg=RISCO, height=1).pack(fill="x")
    caixa = tk.Frame(pe, bg=PAPEL, pady=20)
    caixa.pack()
    botao = tk.Button(caixa, text="JA VI  -  FECHAR", command=fechar,
                      font=_fonte(22, True), bg=VERMELHO, fg="white",
                      activebackground=VERMELHO_ESCURO,
                      activeforeground="white", relief="flat",
                      padx=60, pady=18, cursor="hand2", borderwidth=0)
    botao.pack()
    tk.Label(caixa,
             text="fechar nao resolve: so diz que voce viu. "
                  "O que esta aqui continua esperando no _PENDENCIAS.txt.",
             bg=PAPEL, fg=TINTA_FRACA, font=_fonte(11)).pack(pady=(8, 0))
    botao.focus_set()

    # --- a batida e a fila ----------------------------------------------
    if seguir:
        def bater():
            if not estado["vivo"]:
                return
            trancar(pasta)
            novos = por_arquivo(_ler_json(caminho_da_fila(pasta), []))
            if novos and novos != estado["cartoes"]:
                estado["cartoes"] = novos
                desenhar()
            janela.after(OLHAR_A_FILA, bater)

        trancar(pasta)
        janela.after(OLHAR_A_FILA, bater)

    janela.mainloop()


def _cartao(tk, pai, c):
    """Um ARQUIVO, numa caixa branca, com tudo o que ele tem a dizer."""
    fora = tk.Frame(pai, bg=PAPEL, padx=36, pady=8)
    fora.pack(fill="x")

    caixa = tk.Frame(fora, bg=CARTAO, highlightthickness=0)
    caixa.pack(fill="x")
    tk.Frame(caixa, bg=VERMELHO, width=8).pack(side="left", fill="y")

    corpo = tk.Frame(caixa, bg=CARTAO, padx=24, pady=16)
    corpo.pack(side="left", fill="both", expand=True)

    linha = tk.Frame(corpo, bg=CARTAO)
    linha.pack(fill="x")
    tk.Label(linha, text=c["quando"], bg=CARTAO, fg=TINTA_FRACA,
             font=_fonte(13, True)).pack(side="left")
    if c["cliente"]:
        tk.Label(linha, text=" %s " % c["cliente"], bg="#eceae7", fg=TINTA,
                 font=_fonte(12, True), padx=9,
                 pady=1).pack(side="left", padx=(16, 0))

    tk.Label(corpo, text=c["arquivo"], bg=CARTAO, fg=TINTA,
             font=_fonte(19, True), anchor="w", justify="left",
             wraplength=1500).pack(fill="x", pady=(7, 4))

    for quantas, motivo in c["motivos"]:
        if len(c["motivos"]) > 1:
            motivo = "-  %s" % motivo
        if quantas > 1:
            motivo = "%s   (repetiu %d vezes)" % (motivo, quantas)
        tk.Label(corpo, text=motivo, bg=CARTAO, fg=TINTA_FRACA,
                 font=_fonte(14), anchor="w", justify="left",
                 wraplength=1480).pack(fill="x", pady=1)


# ----------------------------------------------------------------------

def _exemplos():
    """Pendencias de verdade de 14/09/2026, para ver como a tela fica."""
    agora = datetime.datetime.now().strftime("%d/%m %H:%M")
    return [
        {"quando": agora, "cliente": "VOPRIX",
         "arquivo": "ENVELOPE_SACO_23X31,5_4_0_RAPHAEL _BRANDAO_MACHADO_"
                    "COLEGIO_VOOLIVRE",
         "motivos": [(1, "a FIA lancou este servico na vaga 3 da OS 19703 "
                         "as 19:20, e ele NAO ESTA MAIS LA. O servico ja "
                         "saiu: precisa ser lancado A MAO, ou a gravacao "
                         "fica sem cobranca.")]},
        {"quando": agora, "cliente": "PRIME",
         "arquivo": "O.S 1035 - MPGO CARTAZES.cdr",
         "motivos": [(1, "pagina 1: nao achei a marca de corte (lado pe), e "
                         "e dela que sai a pinca. Nao montei a chapa"),
                     (1, "pagina 2: nao achei a marca de corte (lado pe)"),
                     (1, "PDF convertido guardado em "
                         "C:/Finart/_PENDENCIAS/O.S 1035 - MPGO "
                         "CARTAZES.pdf")]},
        {"quando": agora, "cliente": "SOLIDA",
         "arquivo": "49854 HENRIQUE 49858 JUNIOR - GRADE SANTINHOS",
         "motivos": [(10, "este arquivo e o '49854 - HENRIQUE CESAR - "
                          "SANTINHOS' trazem a MESMA OS. Nao lancei nenhum "
                          "dos dois: sao dois servicos na OS, ou um so com "
                          "as chapas somadas? Lance a mao ou me diga a "
                          "regra.")]},
    ]


def main():
    if "--modelo" in sys.argv:
        mostrar(_exemplos(), seguir=False)
        return

    cartoes = por_arquivo(_ler_json(caminho_da_fila(), []))
    if not cartoes:
        return

    def acabou():
        esvaziar()
        destrancar()

    try:
        mostrar(cartoes, ao_fechar=acabou)
    finally:
        destrancar()


if __name__ == "__main__":
    main()
