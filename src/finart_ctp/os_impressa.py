# -*- coding: utf-8 -*-
r"""
A folha da ORDEM DE SERVICO, para sair no verso da prova.

E o mesmo papel do F10 - Imprimir O.S. do GEREMPRE: a 1a VIA PRODUCAO.
Copiada de uma impressa de verdade, a OS 19569, campo por campo e na
mesma posicao.

POR QUE DESENHAR AQUI, e nao mandar o GEREMPRE imprimir. O relatorio vive
dentro do programa Delphi: para tira-lo de la seria preciso abrir o
programa, achar a OS e apertar F10 - uma janela na tela da maquina, no
meio do trabalho de alguem, a cada arquivo. O conteudo, por outro lado,
esta todo no banco. Entao a folha e montada aqui, com os campos lidos da
OS depois de gravada.

O logotipo saiu de dentro do proprio relatorio do GEREMPRE (o .rpf da
pasta do programa), entao e o mesmo desenho que sai na impressao deles.

NAO TEM VALOR NENHUM, e e de proposito: a via de producao nao mostra
dinheiro. Quem monta a chapa nao precisa saber o preco, e o papel anda
pela oficina.

A folha e A4 em pe, no tamanho e no sentido em que a impressora esta -
igual as folhas de prova, e sem passar pelo encaixe do Ghostscript.
"""

import os

A4_MM = (210.0, 297.0)
DPI = 150

# As medidas sairam da OS 19569 impressa, em milimetros na folha A4.
QUADRO = (10.0, 9.5, 200.0, 285.0)      # esquerda, topo, direita, base
LOGO_MM = (15.0, 19.0, 50.0)            # x, y, largura

COLUNAS_MM = {
    "especie": 12.0,
    "linhagem": 89.0,
    "montagem": 111.5,
    "laminas": 138.6,
    "cores": 158.8,
    "formato": 172.0,
}

TELEFONE = "(62) 3988-7072 / 3988-7052"

FONTES_NEGRITO = ["C:/Windows/Fonts/arialbd.ttf",
                  "C:/Windows/Fonts/calibrib.ttf"]
FONTES_NORMAL = ["C:/Windows/Fonts/arial.ttf",
                 "C:/Windows/Fonts/calibri.ttf"]

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "recursos", "logo_finart.png")


def _fonte(px, negrito=False):
    from PIL import ImageFont
    for caminho in (FONTES_NEGRITO if negrito else FONTES_NORMAL):
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, px)
            except OSError:
                pass
    return ImageFont.load_default()


def _data(d):
    return d.strftime("%d/%m/%Y") if d else ""


def _hora(h):
    return h.strftime("%H:%M:%S") if h else ""


def _inteiro(v):
    """510.00 -> '510'. A OS guarda decimal; o papel mostra inteiro."""
    if v is None:
        return "0"
    try:
        return "%.0f" % float(v)
    except (TypeError, ValueError):
        return str(v)


def folha(dados, dpi=DPI):
    """
    A folha A4 em pe da ORDEM DE SERVICO. Devolve uma imagem do Pillow.

    'dados' e o que gerempre.dados_da_os() devolve - lido do banco, e nao
    do que se pretendia gravar. Um campo que nao entrou sai em branco no
    papel, e alguem ve.
    """
    from PIL import Image, ImageDraw

    def px(mm):
        return int(round(mm / 25.4 * dpi))

    pagina = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")
    d = ImageDraw.Draw(pagina)

    g_titulo = _fonte(px(5.6))
    g_numero = _fonte(px(5.2))
    g_faixa = _fonte(px(4.2), True)
    g_rotulo = _fonte(px(3.6), True)
    g_texto = _fonte(px(3.2))
    g_miudo = _fonte(px(2.7))

    esq, topo, dire, base = QUADRO
    d.rectangle([px(esq), px(topo), px(dire), px(base)],
                outline="black", width=2)

    # --- cabecalho -----------------------------------------------------
    if os.path.exists(LOGO):
        try:
            logo = Image.open(LOGO).convert("RGB")
            largura = px(LOGO_MM[2])
            logo = logo.resize(
                (largura, max(1, int(logo.height * largura / logo.width))),
                Image.LANCZOS)
            pagina.paste(logo, (px(LOGO_MM[0]), px(LOGO_MM[1])))
        except OSError:
            pass

    meio_dir = px(155.0)
    d.text((meio_dir - d.textlength("ORDEM DE SERVIÇO", g_titulo) / 2, px(14)),
           "ORDEM DE SERVIÇO", fill="black", font=g_titulo)
    d.text((meio_dir - d.textlength("1ª VIA PRODUÇÃO", g_miudo) / 2, px(20)),
           "1ª VIA PRODUÇÃO", fill="black", font=g_miudo)

    numero = "N º  %s" % dados["numero"]
    d.text((meio_dir - d.textlength(numero, g_numero) / 2, px(27.5)),
           numero, fill="black", font=g_numero)

    d.text((px(72), px(33.5)), "DATA DE ENTRADA %s   -   HORA %s"
           % (_data(dados["entrada"]), _hora(dados["hora"])),
           fill="black", font=g_texto)
    d.text((px(72), px(41.5)), "PREVISÃO DE ENTREGA %s"
           % _data(dados["entrega"]), fill="black", font=g_texto)

    # --- faixa DADOS CLIENTE / MATERIAL --------------------------------
    y = px(47.0)
    d.line([px(esq), y, px(dire), y], fill="black", width=2)
    d.text((px((esq + dire) / 2)
            - d.textlength("DADOS CLIENTE / MATERIAL", g_faixa) / 2,
            y + px(1.0)), "DADOS CLIENTE / MATERIAL",
           fill="black", font=g_faixa)
    y += px(5.5)
    d.line([px(esq), y, px(dire), y], fill="black", width=2)

    def linha(rotulo, valor, yy, x=13.0, fonte=None):
        d.text((px(x), px(yy)), rotulo, fill="black", font=g_rotulo)
        recuo = d.textlength(rotulo, g_rotulo) + px(1.6)
        d.text((px(x) + recuo, px(yy) + px(0.2)), valor or "",
               fill="black", font=fonte or g_texto)

    linha("CLIENTE:", dados["cliente"], 56.5)
    linha("CONTATO:", dados["contato"] or "-", 65.0)
    linha("FONE:", dados["telefone"] or "-", 65.0, x=92.0)
    linha("VENDEDOR:", "", 73.5)
    linha("CONFERENTE:", "", 82.0)
    linha("OPERADOR:", dados.get("responsavel") or "", 90.5)

    # --- o quadro dos servicos -----------------------------------------
    y = px(105.0)
    cabecalhos = [("ESPÉCIE", "especie"), ("LINHAGEM", "linhagem"),
                  ("MONTAGEM", "montagem"), ("LÂMINAS", "laminas"),
                  ("CORES", "cores"), ("FORMATO (cm)", "formato")]
    for rotulo, chave in cabecalhos:
        d.text((px(COLUNAS_MM[chave]), y), rotulo, fill="black", font=g_texto)

    y = px(113.0)
    ALTURA_VAGA = 18.6
    por_vaga = {i["vaga"]: i for i in dados["itens"]}
    for vaga in range(1, 5):
        item = por_vaga.get(vaga)
        topo_vaga = y + px(ALTURA_VAGA * (vaga - 1))

        especie = item["material"] if item else ""
        montagem = item["montagem"] if item else ""
        laminas = _inteiro(item["quantas"]) if item else "0"
        cores = ("%s x %s" % (item["frente"], item["verso"])) if item \
            else "0 x 0"
        formato = ("%s  x  %s" % (_inteiro(item["alt"]), _inteiro(item["lar"]))) \
            if item else "0 x   0"

        d.text((px(COLUNAS_MM["especie"]), topo_vaga), especie,
               fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["montagem"]), topo_vaga), montagem,
               fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["laminas"] + 16.0)
                - d.textlength(laminas, g_texto), topo_vaga), laminas,
               fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["cores"] + 10.0)
                - d.textlength(cores, g_texto), topo_vaga), cores,
               fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["formato"] + 16.0)
                - d.textlength(formato, g_texto), topo_vaga), formato,
               fill="black", font=g_texto)

        d.text((px(COLUNAS_MM["especie"]), topo_vaga + px(5.6)), "Título:",
               fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["especie"] + 11.0), topo_vaga + px(5.6)),
               item["titulo"] if item else "", fill="black", font=g_texto)
        d.text((px(COLUNAS_MM["montagem"] + 17.0), topo_vaga + px(5.6)),
               "Obs.:", fill="black", font=g_texto)
        if item and item["obs"]:
            d.text((px(COLUNAS_MM["montagem"] + 26.0), topo_vaga + px(5.6)),
                   item["obs"], fill="black", font=g_texto)

    # --- faixa MATERIAIS RECEBIDOS -------------------------------------
    y = px(183.0)
    d.line([px(esq), y, px(dire), y], fill="black", width=2)
    d.text((px((esq + dire) / 2)
            - d.textlength("MATERIAIS RECEBIDOS", g_faixa) / 2, y + px(1.0)),
           "MATERIAIS RECEBIDOS", fill="black", font=g_faixa)
    y += px(5.5)
    d.line([px(esq), y, px(dire), y], fill="black", width=2)

    for rotulo, x in (("DISQUETES:", 13.0), ("PEN-DRIVE:", 56.0),
                      ("PRINTS:", 99.0), ("ZIP:", 134.0),
                      ("IMPRESSO:", 160.0)):
        linha(rotulo, "0", 192.0, x=x)
    for rotulo, x in (("DVD:", 13.0), ("CD:", 40.0), ("E-MAIL:", 68.0),
                      ("FTP:", 102.0)):
        linha(rotulo, "0", 201.0, x=x)

    d.text((px(13.0), px(210.0)), "OBSERVAÇÕES:", fill="black", font=g_rotulo)
    d.text((px(13.0), px(234.0)), "MOTIVO:", fill="black", font=g_rotulo)
    return pagina


def folha_da_os(numero, con=None, dpi=DPI):
    """A folha da OS de numero 'numero', ou None se ela nao existir."""
    from .gerempre import dados_da_os
    dados = dados_da_os(numero, con=con)
    if not dados:
        return None
    return folha(dados, dpi=dpi)
