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

import shutil


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
    """
    if total == 1:
        shutil.copy2(origem, destino)
        return destino
    return _uma_pagina(origem, destino, pagina)


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
