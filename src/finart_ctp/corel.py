# -*- coding: utf-8 -*-
"""
Conversao de .cdr para PDF, usando o proprio CorelDRAW.

Por que a Corel e nao um conversor de terceiros: quem exporta e o motor
da propria Corel, entao cor especial, sobreimpressao, sangria e fonte
saem como no arquivo. Um conversor livre sai "parecido", e parecido nao
serve para gravar chapa.

CUIDADO - a automacao NAO abre uma instancia nova: ela se conecta a
sessao do CorelDRAW que estiver aberta na maquina, a do operador. Duas
regras nasceram de erro cometido:

  1. nunca mexer em Visible (ja escondemos a janela de alguem)
  2. nunca fechar documento que nao fomos nos que abrimos

A regra 2 e a mais importante. O OpenDocument de um arquivo JA ABERTO
devolve o documento do operador; fechar aquilo joga fora o trabalho dele
sem perguntar. Por isso, arquivo aberto na sessao nao e convertido: fica
para a proxima passada, quando a pessoa tiver fechado.

O operador vai ver o arquivo piscar na tela durante a conversao. E o
preco combinado de dividir a maquina.
"""

import os

from .config import (COREL_CMYK, PDF_CORELDRAW, PDF_CORELDRAW_PREDEFINICAO)

PROGID = "CorelDRAW.Application"


class ArquivoEmUso(Exception):
    """O .cdr esta aberto no CorelDRAW do operador."""


def limpar_cache_do_pywin32():
    """
    Joga fora os involucros que o pywin32 gerou, para ele refaze-los.

    E operacao barata e sem perda: aquilo e cache, e se reconstroi na
    proxima chamada em poucos segundos.
    """
    import importlib
    import shutil
    import sys
    from win32com.client import gencache

    pasta = gencache.GetGeneratePath()
    shutil.rmtree(pasta, ignore_errors=True)
    os.makedirs(pasta, exist_ok=True)
    for modulo in [m for m in list(sys.modules)
                   if m.startswith("win32com.gen_py")]:
        del sys.modules[modulo]
    importlib.invalidate_caches()
    try:
        gencache.Rebuild()
    except Exception:
        pass
    return pasta


def _aplicacao():
    """
    A sessao do CorelDRAW da maquina. Abre uma se nao houver nenhuma.

    TENTA DUAS VEZES, e a segunda depois de limpar o cache do pywin32.

    O pywin32 guarda os involucros que gera da biblioteca do CorelDRAW
    numa pasta dentro do %TEMP% - e %TEMP% e justamente o que o Windows
    limpa sozinho. Em 17/09/2026 a faxina levou os arquivos .py e deixou
    o __pycache__ para tras: o Python passou a importar um modulo VAZIO,
    e toda conversao morria com

        module 'win32com.gen_py.95E23C91-...' has no attribute
        'CLSIDToClassMap'      (e, na chamada seguinte, CLSIDToPackageMap)

    A PRIME ficou a manha inteira sem converter por causa disso, e o
    aviso nao ajudava ninguem a entender o que fazer.

    Nao adianta so avisar melhor: o conserto e apagar o cache, e isso o
    programa faz sozinho. Note que vale ate para o Dispatch simples -
    havendo involucro gerado, ele e usado, e um involucro quebrado
    envenena tambem a ligacao tardia.
    """
    import win32com.client
    try:
        return win32com.client.Dispatch(PROGID)
    except (AttributeError, ImportError) as e:
        from .utils import log
        log("O cache do pywin32 estava quebrado (%s). Apaguei e vou "
            "tentar de novo - ele se refaz sozinho." % str(e)[:90],
            alerta=True)
        limpar_cache_do_pywin32()
        return win32com.client.Dispatch(PROGID)


def disponivel():
    """True se der para falar com o CorelDRAW nesta maquina."""
    try:
        _aplicacao()
        return True
    except Exception:
        return False


def _documento_aberto(app, caminho):
    """O documento do operador, se este arquivo ja estiver aberto."""
    alvo = os.path.normcase(os.path.abspath(caminho))
    try:
        total = app.Documents.Count
    except Exception:
        return None
    for i in range(1, total + 1):
        try:
            doc = app.Documents.Item(i)
            if os.path.normcase(doc.FullFileName) == alvo:
                return doc
        except Exception:
            continue
    return None


def carregar_predefinicao(doc, nome=PDF_CORELDRAW_PREDEFINICAO):
    """
    Carrega pelo NOME a predefinicao da janela de Publicar em PDF.

    Sem isto vale o que estiver marcado na janela naquele dia - e a
    janela e a mesma que o operador usa a mao. Predefinicao se pede, nao
    se herda, pela mesma razao que frente e verso se pede na impressora.

    Depois de carregar, CONFERE a cor de saida. Nao e formalidade: com a
    predefinicao em RGB, o preto cheio deste mesmo arquivo sai como
    RGB 0.216 0.204 0.208 - cinza escuro - e nenhuma etapa adiante
    desfaz isso. Fora do CMYK a conversao PARA.
    """
    if not nome:
        return
    ajustes = doc.PDFSettings
    try:
        ajustes.Load(nome)
    except Exception as e:
        raise RuntimeError(
            "o CorelDRAW nao achou a predefinicao de PDF '%s' (%s). Nao "
            "converto: sem ela vale o que estiver marcado na janela, e "
            "ninguem sabe o que esta marcado" % (nome, str(e)[:80]))

    modo = getattr(ajustes, "ColorMode", None)
    if modo != COREL_CMYK:
        raise RuntimeError(
            "a predefinicao '%s' esta saindo em modo de cor %s, e nao em "
            "CMYK (%d). Nao converto: chapa se grava em CMYK e o que sair "
            "fora dele nao volta" % (nome, modo, COREL_CMYK))


def ajustar_pdf(doc):
    """
    Exige do CorelDRAW os ajustes do PDF_CORELDRAW, em vez de herdar.

    O PublishToPDF usa o que estiver marcado na janela de Publicar em PDF
    da maquina - e o que estava marcado gravava bitmap CRU: um .cdr de
    13 MB virou PDF de 1007 MB, sendo 1006 MB de imagem sem compactar.

    Devolve o que NAO deu para ajustar, para o chamador avisar. Versao de
    Corel diferente pode nao ter alguma dessas propriedades, e isso nao e
    motivo para deixar de converter.
    """
    ajustes = doc.PDFSettings
    faltaram = []
    for nome, valor in PDF_CORELDRAW.items():
        try:
            setattr(ajustes, nome, valor)
            conferido = getattr(ajustes, nome)
            # nao basta mandar: tem versao de Corel que aceita a atribuicao
            # e continua com o valor antigo
            if conferido != valor:
                faltaram.append("%s (pedi %s, ficou %s)"
                                % (nome, valor, conferido))
        except Exception:
            faltaram.append(nome)
    return faltaram


# ----------------------------------------------------------------------
# ACHATAR TUDO EM IMAGEM, DENTRO DO COREL
# ----------------------------------------------------------------------
# Pedido do operador para a VOPRIX, 17/09/2026:
#
#   "estou percebendo que eles nao estao mandando os arquivos como antes,
#    convertido as imagens todas em 1 imagem, e somente os textos e
#    objetos sem converter, isso e perigoso, pode sumir algum objeto, dar
#    problema. Vamos colocar o protocolo dela entao o seguinte: no corel
#    mesmo, converta tudo em imagem 900 dpi, CMYK, gera o pdf e confere
#    as cores se estao batendo, se nao perdeu na hora de converter."
#
# O risco que ele descreve e real e conhecido: texto e vetor que
# atravessam o PDF dependem de fonte, transparencia e sobreimpressao
# serem interpretados igual por quem grava. Achatado em imagem, nao ha
# fonte que falte nem transparencia que achate errado - ha pixel, e mais
# nada. E o mesmo raciocinio do passo 4 da montagem da AMERICA.
#
# DUAS TRAVAS, e a primeira e a que importa:
#
# 1. O ORIGINAL NUNCA E ABERTO. O .cdr e COPIADO para uma pasta
#    temporaria, e quem e achatado e a copia. Se alguma coisa der errado
#    - o Corel salvar sozinho, a maquina cair no meio - o arquivo do
#    cliente continua vetorial, intacto. Achatar e irreversivel: um .cdr
#    salvo como bitmap perde o texto para sempre, e nao ha desfazer no
#    dia seguinte.
#
# 2. O documento e fechado com Dirty = False. Sem isso o Corel pode
#    perguntar se quer salvar - e uma pergunta numa automacao e uma
#    janela parada esperando alguem que nao esta olhando.

DPI_DO_ACHATADO = 900
CDR_IMAGE_CMYK = 5                 # cdrImageMode.cdrImageCMYK
CDR_ANTISERRILHAMENTO = 1          # cdrAntiAliasingType.cdrNormalAntiAliasing


# ----------------------------------------------------------------------
# A MARCA NAO VIRA PIXEL - so a arte
# ----------------------------------------------------------------------
# Pedido do operador em 18/09/2026, depois de ver funcionar num ensaio:
# "converta em imagem, mas nao converta as cruz de corte nem de registro,
# somente o que for da arte".
#
# Tres coisas nao podem ser rasterizadas numa chapa ja montada:
#
#   - a LINHA DE CORTE e lida pela guilhotina, e traco fino a 900 dpi
#     vira borda cinza de meio pixel;
#   - a CRUZ DE REGISTRO existe para casar as quatro chapas. Ela usa a
#     COR DE REGISTRO, que imprime em todas - virando imagem CMYK, ela
#     deixa de ser cor de registro e passa a ser quatro objetos
#     separados, um por chapa. Seria justamente o desencontro que ela
#     existe para denunciar;
#   - a ESCALA DE COR e referencia de densidade; reamostrada, deixa de
#     medir o que devia.
#
# A separacao sai da COR DE REGISTRO, e isso nao e convencao nossa: e o
# que a cor de registro significa. Toda marca a usa, nenhuma arte usa.
#
# QUEM NAO TEM MARCA NENHUMA CAI NO CASO ANTIGO sozinho: nao achando cor
# de registro em parte alguma, tudo e arte e tudo vira imagem - que era
# o comportamento antes de 18/09.

MM_POR_POLEGADA = 25.4       # o Corel devolve medida em polegada


def _e_registro(cor):
    """
    A cor e a COR DE REGISTRO?

    Lida pelo texto que o Corel devolve - 'REGCOLOR,USER,...'. O
    ToString e o que ha de estavel aqui: a constante de tipo muda de
    nome entre versoes, e o prefixo nao.
    """
    try:
        return cor.ToString().upper().startswith("REGCOLOR")
    except Exception:
        return False


def usa_registro(forma):
    """A PROPRIA forma e desenhada em cor de registro?"""
    try:
        f = forma.Fill
        if f.Type == 1 and _e_registro(f.UniformColor):
            return True
    except Exception:
        pass
    try:
        o = forma.Outline
        if o.Width is not None and _e_registro(o.Color):
            return True
    except Exception:
        pass
    return False


def tem_registro_dentro(forma, fundo=0):
    """Ela, ou qualquer descendente dela, usa cor de registro?"""
    if usa_registro(forma):
        return True
    if fundo > 6:
        return False
    try:
        filhos = forma.Shapes
        total = filhos.Count
    except Exception:
        return False
    for i in range(1, total + 1):
        try:
            if tem_registro_dentro(filhos.Item(i), fundo + 1):
                return True
        except Exception:
            continue
    return False


def escolher(forma, marcas, arte, fundo=0):
    """Separa em duas listas: o que fica em vetor e o que vira imagem."""
    if usa_registro(forma):
        marcas.append(forma)
        return
    if tem_registro_dentro(forma):
        try:
            filhos = forma.Shapes
            total = filhos.Count
        except Exception:
            total = 0
        if total and fundo < 6:
            for i in range(1, total + 1):
                escolher(filhos.Item(i), marcas, arte, fundo + 1)
            return
        marcas.append(forma)
        return
    arte.append(forma)


def medida(forma):
    return ("%.1f x %.1f mm em (%.1f, %.1f)"
            % (forma.SizeWidth * MM, forma.SizeHeight * MM,
               forma.PositionX * MM, forma.PositionY * MM))


def _por_atras_das_marcas(imagem, marcas, pagina):
    """
    Poe a imagem atras de TODAS as marcas. True se conseguiu.

    NAO DEDUZ A ORDEM DAS CAMADAS - experimenta e confere. Duas
    suposicoes minhas cairam aqui em 18/09/2026:

      - que OrderToBack bastasse. Ele so ordena dentro da camada, e o
        arquivo da CAIPORA tem DUAS camadas imprimiveis, as duas
        chamadas 'Camada 1';
      - que Layers.Item(1) fosse a de baixo. Mudar para ela e mandar
        para o fundo deixou a imagem na frente de 13 marcas.

    Entao: tenta o caminho barato (so o fundo da camada atual) e, nao
    dando, muda para cada camada imprimivel e tenta de novo. Entre uma
    tentativa e outra quem responde e o Corel, pelo OrderIsInFrontOf -
    o nome da camada nao diz quem cobre quem.
    """
    def conseguiu():
        return not any(_esta_na_frente(imagem, m) for m in marcas)

    try:
        imagem.OrderToBack()
    except Exception:
        pass
    if conseguiu():
        return True

    for j in range(1, pagina.Layers.Count + 1):
        try:
            camada = pagina.Layers.Item(j)
            if not camada.Printable:
                continue
            imagem.MoveToLayer(camada)
            imagem.OrderToBack()
        except Exception:
            continue
        if conseguiu():
            return True
    return False


def _esta_na_frente(forma, outra):
    """
    A forma esta desenhada POR CIMA da outra?

    Pergunta ao Corel em vez de deduzir da camada: 'Camada 1' pode
    existir duas vezes no mesmo arquivo, e ai o nome nao diz nada sobre
    quem cobre quem.
    """
    try:
        return bool(forma.OrderIsInFrontOf(outra))
    except Exception:
        return False


def camada_mais_de_baixo(pagina):
    """
    A camada imprimivel que fica por baixo de todas, ou None.

    As 'Linhas-guia' e companhia nao contam: nao imprimem, e por elas o
    desenho passaria a ficar atras de nada.
    """
    for j in range(1, pagina.Layers.Count + 1):
        camada = pagina.Layers.Item(j)
        try:
            if camada.Printable:
                return camada
        except Exception:
            continue
    return None


def separar_arte_das_marcas(pagina):
    """([formas de arte], [formas de marca]) de uma pagina."""
    marcas, arte = [], []
    for j in range(1, pagina.Layers.Count + 1):
        camada = pagina.Layers.Item(j)
        if not camada.Printable:
            continue
        for k in range(1, camada.Shapes.Count + 1):
            escolher(camada.Shapes.Item(k), marcas, arte)
    return arte, marcas


def publicar_pdf_achatado(cdr, destino, dpi=DPI_DO_ACHATADO):
    """
    Achata o .cdr inteiro em UMA imagem CMYK e publica em PDF.

    Devolve o caminho do PDF. O arquivo de origem nao e tocado: quem e
    aberto e achatado e uma COPIA.
    """
    import shutil
    import tempfile

    cdr = os.path.abspath(cdr)
    destino = os.path.abspath(destino)
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    app = _aplicacao()
    if _documento_aberto(app, cdr) is not None:
        raise ArquivoEmUso("'%s' esta aberto no CorelDRAW"
                           % os.path.basename(cdr))

    pasta = tempfile.mkdtemp(prefix="achatar_")
    copia = os.path.join(pasta, os.path.basename(cdr))
    shutil.copy2(cdr, copia)

    doc = app.OpenDocument(copia)
    try:
        carregar_predefinicao(doc)
        faltaram = ajustar_pdf(doc)
        criticos = [f for f in faltaram if f.startswith("Downsample")]
        if criticos:
            raise RuntimeError(
                "o CorelDRAW nao aceitou desligar a reamostragem (%s)"
                % ", ".join(criticos))

        # PAGINA A PAGINA. Um ConvertToBitmapEx no documento inteiro
        # juntaria paginas diferentes numa imagem so.
        achatadas = 0
        for i in range(1, doc.Pages.Count + 1):
            pagina = doc.Pages.Item(i)
            # Activate(), e nao 'doc.ActivePage = pagina': ActivePage e
            # so de leitura no Corel 27, e a atribuicao estoura com
            # AttributeError sem dizer que o problema e esse.
            pagina.Activate()
            arte, marcas = separar_arte_das_marcas(pagina)
            if not arte:
                continue
            fundo = camada_mais_de_baixo(pagina)

            # DE UMA VEZ SO, num ShapeRange. Forma a forma sairia uma
            # imagem por forma - e ha arquivo com 978 formas de arte.
            faixa = app.CreateShapeRange()
            for f in arte:
                faixa.Add(f)
            imagem = faixa.ConvertToBitmapEx(
                CDR_IMAGE_CMYK,     # Mode: CMYK
                False,              # Dithered
                True,               # Transparent - ver o bloco abaixo
                dpi,                # Resolution
                CDR_ANTISERRILHAMENTO,
                True,               # UseColorProfile - o mesmo da tela
                False,              # AlwaysOverprintBlack
                95)                 # OverprintBlackLimit

            # E A IMAGEM VAI PARA TRAS DE TODAS AS MARCAS.
            #
            # O bitmap nasce NO TOPO da pilha, e a caixa dele e um
            # retangulo OPACO: cobre o que estiver embaixo, mesmo onde
            # nao ha desenho. Em 18/09/2026 isso comeu as cruzes de
            # registro, as marcas de corte dos cantos, a escala de cor e
            # o texto da OS no pe do
            # '510x400_CMYK_VOPRIX_CAIPORA_TABACOS_caixa_palheiro'.
            # Guardar a marca em vetor nao adianta se depois se pinta por
            # cima dela.
            #
            # E NAO BASTA UM OrderToBack. Duas coisas, perguntadas ao
            # proprio Corel em vez de supostas:
            #
            #   - ele so ordena DENTRO DA CAMADA, e aquele arquivo tem
            #     DUAS camadas imprimiveis, ambas chamadas 'Camada 1';
            #     depois do OrderToBack a imagem continuava na frente da
            #     barra de cor, que estava na outra;
            #   - o OrderBackOf resolve, mas de UMA forma por vez: posta
            #     atras da primeira marca, ela seguia na frente da
            #     segunda.
            #
            # Entao empurra-se para tras de cada marca que ainda estiver
            # por baixo, ate nao haver nenhuma - e no fim CONFERE. Se
            # sobrar uma, nao se entrega: chapa com a marca de corte
            # coberta e chapa que a guilhotina nao sabe cortar.
            # O FUNDO DA IMAGEM E TRANSPARENTE, e e isso que salva as
            # marcas.
            #
            # 18/09/2026: o operador recebeu a chapa da CAIPORA com as
            # cruzes de registro, as marcas de corte dos cantos, a escala
            # de cor e o texto da OS COBERTOS. As marcas estavam la, em
            # vetor, intactas - e invisiveis, porque o bitmap e um
            # RETANGULO e o retangulo era opaco. A caixa dele vai de
            # ponta a ponta da arte e passa por cima de tudo que mora
            # dentro dela.
            #
            # DUAS TENTATIVAS MINHAS FALHARAM antes disto, e valem ficar
            # escritas para ninguem repetir:
            #
            #   OrderToBack()  - so ordena DENTRO da camada, e aquele
            #     arquivo tem DUAS camadas imprimiveis, ambas chamadas
            #     'Camada 1'. Perguntado ao Corel depois de mandar para o
            #     fundo: a imagem continuava na frente da barra;
            #
            #   MoveToLayer + OrderToBack em cada camada - tambem nao.
            #     Nenhuma posicao na pilha resolve, porque parte das
            #     marcas esta ANINHADA dentro de grupos e a comparacao de
            #     ordem com elas nao responde o que eu supunha.
            #
            # O conserto nao era ordenar: era nao ter fundo. Medido na
            # faixa dos 30 mm do pe da chapa, contra o mesmo arquivo
            # publicado em vetor:
            #
            #     opaco .......... 137 de 974 pixels de tinta    14%
            #     TRANSPARENTE ... 978 de 974                   100%
            #
            # E o branco da arte continua branco: numa chapa, branco e
            # ausencia de tinta, que e o que transparente quer dizer.
            #
            # O OrderToBack fica assim mesmo, por ordem: arte atras,
            # marca na frente. Nao depende mais dele para funcionar.
            try:
                imagem.OrderToBack()
            except Exception:
                pass
            achatadas += 1
            if marcas:
                from .utils import log
                log("   p%d: %d forma(s) viraram UMA imagem de %d dpi; "
                    "%d marca(s) ficaram em vetor"
                    % (i, len(arte), dpi, len(marcas)))
        if not achatadas:
            raise RuntimeError("o arquivo nao tem nada desenhado")

        doc.PublishToPDF(destino)
    finally:
        try:
            doc.Dirty = False       # nao perguntar se quer salvar
        except Exception:
            pass
        try:
            doc.Close()
        except Exception:
            pass
        shutil.rmtree(pasta, ignore_errors=True)

    if not os.path.exists(destino):
        raise RuntimeError("CorelDRAW nao gerou o PDF achatado de '%s'"
                           % os.path.basename(cdr))
    return destino


def publicar_pdf(cdr, destino):
    """
    Abre o .cdr e publica em PDF. Devolve o caminho do PDF.

    Levanta ArquivoEmUso se o arquivo estiver aberto na sessao do
    operador: nesse caso nao mexemos nele de jeito nenhum.
    """
    cdr = os.path.abspath(cdr)
    destino = os.path.abspath(destino)
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    app = _aplicacao()
    if _documento_aberto(app, cdr) is not None:
        raise ArquivoEmUso("'%s' esta aberto no CorelDRAW"
                           % os.path.basename(cdr))

    doc = app.OpenDocument(cdr)
    try:
        # A ORDEM IMPORTA. A predefinicao vem primeiro, e e ela que manda
        # em cor, sobreimpressao e sangria - o que o operador ajustou.
        # Os ajustes do PDF_CORELDRAW vem DEPOIS, por cima, e sao dois
        # tipos de coisa que a predefinicao nao tem por que carregar:
        #
        #   compressao SEM PERDA - a FINART guarda bitmap cru. Neste
        #   mesmo arquivo deu 1,2 MB contra 0,6 MB com ZIP, e ja houve
        #   .cdr de 13 MB virar PDF de 1007 MB. Agora esse PDF atravessa
        #   a rede ate o CTP, entao o peso conta em dobro. Foi medido que
        #   o arquivo sai IGUAL: mesma cobertura de tinta na quinta casa;
        #
        #   reamostragem DESLIGADA - rede de seguranca. A FINART ja vem
        #   com as tres desligadas; forcar aqui e o que impede que uma
        #   edicao futura na janela do operador reamostre a arte para
        #   300 dpi sem ninguem perceber.
        carregar_predefinicao(doc)
        faltaram = ajustar_pdf(doc)
        # Compressao que nao pegou custa espaco em disco. Reamostragem que
        # nao pegou custa a TIRAGEM: sai arte de 300 dpi gravada numa chapa
        # de 1000, borrada, e ninguem ve antes de imprimir. Essa nao passa.
        criticos = [f for f in faltaram if f.startswith("Downsample")]
        if criticos:
            raise RuntimeError(
                "o CorelDRAW nao aceitou desligar a reamostragem (%s). "
                "Nao converto: a arte sairia em 300 dpi sem aviso"
                % ", ".join(criticos))
        doc.PublishToPDF(destino)
    finally:
        try:
            doc.Close()          # fechamos apenas o que nos abrimos
        except Exception:
            pass

    if not os.path.exists(destino):
        raise RuntimeError("CorelDRAW nao gerou o PDF de '%s'"
                           % os.path.basename(cdr))
    return destino
