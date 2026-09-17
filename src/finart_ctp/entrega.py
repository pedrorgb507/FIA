# -*- coding: utf-8 -*-
"""
O caminho curto: o PDF do cliente vai INTEIRO para o CTP.

O caminho longo - separar as tintas no Ghostscript e remontar o PDF -
existe porque a arte precisava virar IMAGEM para a gravadora. Quando ela
ja chega em PDF vetorial e no tamanho da chapa, esse trabalho todo nao
acrescenta nada. E nao e neutro: tira.

TIROU MESMO. Em 09/09/2026 uma pasta da VOPRIX foi gravada com o preto
no lugar errado - no arquivo do cliente o preto esta no canal K, e na
chapa ele tinha virado C, M e Y com o K vazio. Medido no mesmo PDF:

    como a FIA le hoje     C 0.1019  M 0.1049  Y 0.0683  K 0.0097
    lendo sem o perfil     C 0.0464  M 0.0468  Y 0.0084  K 0.0558

Os numeros DENTRO do PDF nunca mudaram: o preto cheio esta escrito
'0 0 0 1', o cinza de 50% '0 0 0 0.502', o de 10% '0 0 0 0.102'. O que
muda e a LEITURA. A Corel marca as cores num espaco ICC proprio
(/DefaultCMYK, 557 KB de perfil embutido no arquivo) e o Ghostscript
converte esse CMYK para o CMYK dele PASSANDO pelo perfil. Cinza feito so
de K sai remisturado nas quatro tintas, e o K esvazia.

Nao passando pelo Ghostscript nao ha o que remisturar. Com uma pagina so
- o caso da VOPRIX - o arquivo entregue e o mesmo que saiu do Corel, byte
por byte: nenhum programa nosso abre, converte ou regrava a cor.

Quem separa passa a ser a gravadora, que e quem sempre soube.
"""

import os
import shutil

# '01 <nome>' - o numero vai NA FRENTE, e nao atras.
#
# Regra do operador, 17/09/2026: "nunca mande para o ctp arquivo, pdf com
# duas paginas, se o pdf tiver duas paginas (...) crie dois arquivos, com
# numeros na frente do nome exemplo 01..02.. e por ai vai (...) sempre
# coloca no ctp 01 pagina 01 arquivo por vez.. ele nao puxa multiplas
# paginas".
#
# Na frente porque a pasta do CTP e lida em ordem alfabetica, e e assim
# que a ordem das paginas vira a ordem da fila de gravacao. Com o numero
# atras, o nome do trabalho manda na ordem e as paginas se espalham.
NUMERO_DA_PAGINA = "%02d %s"


def nome_da_pagina(base, n):
    """'01 <base>' - o numero na frente, com dois algarismos."""
    return NUMERO_DA_PAGINA % (n, base)


def _uma_pagina(origem, destino, pagina):
    """
    Uma pagina do PDF, com o documento inteiro em volta dela.

    CLONA o documento e apaga as OUTRAS paginas, em vez de montar um PDF
    novo e por a pagina dentro. Parece a mesma coisa e nao e: o PDF da
    Corel traz /OCProperties no catalogo - a ficha das CAMADAS do arquivo
    -, e quem monta documento novo deixa isso para tras. Sem a ficha, a
    camada que estava escondida (guia de corte, gabarito de verniz) fica
    com visibilidade indefinida, e a gravadora pode grava-la na chapa.
    """
    from pypdf import PdfWriter

    escritor = PdfWriter(clone_from=origem)
    for i in range(len(escritor.pages) - 1, -1, -1):
        if i != pagina - 1:
            escritor.remove_page(i)
    with open(destino, "wb") as f:
        escritor.write(f)
    return destino


def entregar(origem, destino, pagina, total):
    """
    Poe no CTP a pagina pedida do PDF do cliente. Devolve o caminho.

    Com UMA pagina e copia de arquivo - nem o pypdf encosta no conteudo.
    Nada e recomprimido, reconvertido ou regravado.

    QUEM DECIDE E O ARQUIVO, nao o 'total'. O 'total' e quantas chapas o
    plano previu; se ele disser uma e o PDF tiver duas paginas, copiar
    inteiro poria duas paginas na pasta do CTP - e a gravadora so puxa a
    primeira. Nesse caso a pagina se recorta, como no caso de muitas.
    """
    from pypdf import PdfReader

    if total == 1 and len(PdfReader(origem).pages) == 1:
        shutil.copy2(origem, destino)
        return destino
    return _uma_pagina(origem, destino, pagina)


def entregar_no_ctp(origem, pasta, base, ext=".pdf"):
    """
    Poe o PDF no CTP, UM ARQUIVO POR PAGINA. Devolve os caminhos, em ordem.

    A GRAVADORA NAO PUXA MULTIPLAS PAGINAS. Um PDF de duas paginas na
    pasta do CTP nao vira duas chapas: vira uma chapa e uma pagina
    esquecida, e ninguem ve, porque o arquivo ESTA la e tem o nome certo.

    Aconteceu em 17/09/2026 com o 'PASTA PRE MEETING fv.pdf' da AMERICA -
    frente e verso montados a mao pelo operador, num arquivo so. A OS
    cobrou as 8 chapas certas (2 paginas x CMYK), a prova saiu com as
    duas, e para o CTP foi um arquivo de duas paginas. O operador partiu
    a mao e ditou a regra.

    Com UMA pagina, e copia de arquivo - nem o pypdf encosta no conteudo,
    e o arquivo entregue e byte por byte o que o cliente mandou.
    """
    from pypdf import PdfReader

    os.makedirs(pasta, exist_ok=True)
    total = len(PdfReader(origem).pages)
    if total <= 1:
        destino = os.path.join(pasta, base + ext)
        shutil.copy2(origem, destino)
        return [destino]

    saidas = []
    for n in range(1, total + 1):
        destino = os.path.join(pasta, nome_da_pagina(base, n) + ext)
        _uma_pagina(origem, destino, n)
        saidas.append(destino)
    return saidas


def chegou_por_pagina(saidas, paginas):
    """
    Confere o que foi partido: devolve (True, '') ou (False, porque).

    Aqui o tamanho em bytes nao serve de prova - cada pedaco e menor que
    o original, de proposito. O que prova e a CONTA e a forma: um arquivo
    por pagina, cada um abrindo com UMA pagina so.
    """
    from pypdf import PdfReader

    if len(saidas) != paginas:
        return False, ("sairam %d arquivos para %d paginas"
                       % (len(saidas), paginas))
    for caminho in saidas:
        nome = os.path.basename(caminho)
        if not os.path.exists(caminho):
            return False, "'%s' nao esta no CTP" % nome
        try:
            quantas = len(PdfReader(caminho).pages)
        except Exception as e:
            return False, "'%s' nao abre como PDF: %s" % (nome, str(e)[:50])
        if quantas != 1:
            return False, ("'%s' ficou com %d paginas, e chapa e uma so"
                           % (nome, quantas))
    return True, ""


def conferir(caminho, larg_mm, alt_mm, folga=1.0):
    """
    Mede o que foi entregue. Devolve o que esta errado, ou ''.

    A chapa RASTERIZADA se confere em dpi, contando pixels
    (pdf_builder.conferir_resolucao). Aqui nao ha pixel para contar: o
    arquivo e vetorial e a resolucao quem escolhe e a gravadora. O que da
    para conferir - e precisa - e o tamanho da pagina e que exista UMA so.

    Duas paginas num arquivo da pasta do CTP viram duas chapas na fila
    sem ninguem ter pedido, e a OS cobrou uma.
    """
    from pypdf import PdfReader

    leitor = PdfReader(caminho)
    if len(leitor.pages) != 1:
        return ("o arquivo entregue ficou com %d paginas, e chapa e uma so"
                % len(leitor.pages))

    pagina = leitor.pages[0]
    caixa = pagina.mediabox
    larg = float(caixa.width) / 72 * 25.4
    alt = float(caixa.height) / 72 * 25.4
    if ((pagina.get("/Rotate") or 0) % 360) in (90, 270):
        larg, alt = alt, larg

    for real, pedido, lado in ((larg, larg_mm, "largura"),
                               (alt, alt_mm, "altura")):
        if abs(real - pedido) > folga:
            return ("a pagina entregue tem %.1f mm de %s em vez de %.0f"
                    % (real, lado, pedido))
    return ""
