# -*- coding: utf-8 -*-
"""Tudo que fala com o Ghostscript."""

import os
import shutil
import subprocess
import tempfile

from .config import GS_EXE, IMPRESSORA, PASTA_CONTROLE


def achar_ghostscript():
    """Devolve o caminho do gswin64c.exe, ou None se nao existir."""
    if GS_EXE:
        return GS_EXE
    for c in ["gswin64c", "gswin32c", "gs"]:
        p = shutil.which(c)
        if p:
            return p
    for base in [r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"]:
        if os.path.isdir(base):
            for v in sorted(os.listdir(base), reverse=True):
                exe = os.path.join(base, v, "bin", "gswin64c.exe")
                if os.path.exists(exe):
                    return exe
    return None


GS = achar_ghostscript()


# Abaixo disso a tinta e considerada ausente: sujeira de arredondamento.
LIMIAR_TINTA = 0.0001


def sem_perfil(ligado):
    """
    O argumento que manda o Ghostscript NAO passar a cor pelo perfil ICC.

    Por padrao ele color-gerencia tudo: CMYK do arquivo -> perfil de
    origem -> perfil do dispositivo -> CMYK de saida. Quando o arquivo
    traz perfil proprio embutido - a Corel embute um de 557 KB - essa
    volta NAO e identidade, e cinza feito so de K sai remisturado nas
    quatro tintas. Medido no mesmo PDF de uma pasta da VOPRIX:

        gerenciado    C 0.1019  M 0.1049  Y 0.0683  K 0.0097
        sem perfil    C 0.0464  M 0.0468  Y 0.0084  K 0.0558

    E os numeros escritos dentro do PDF sao '0 0 0 1' e '0 0 0 0.502':
    o preto sempre esteve no K.

    Quem entrega o PDF inteiro para a gravadora (entrega.py) tem de
    contar a tinta assim - senao o nome da chapa e a OS falariam de
    quatro tintas onde a gravadora vai encontrar uma.
    """
    return ["-dUseFastColor=true"] if ligado else []


def cobertura_por_pagina(pdf, sem_icc=False, so_o_corte=False):
    """
    [{"C": 0.06081, "M": 0.06079, "Y": 0.06080, "K": 0.05444}, ...]

    O inkcov cru: quanto de cada tinta a pagina usa, de 0 a 1. Uma linha
    por pagina, na ordem.

    sem_icc=True le a tinta como ela esta escrita no arquivo, sem passar
    pelo perfil embutido. Ver sem_perfil().

    so_o_corte=True mede SO O QUE FICA DENTRO DA LINHA DE CORTE.

    Regra do operador, 18/09/2026: "voce analisa somente o arquivo, as
    marcas de corte geralmente ficam nas 4 cores mesmo, mas se o arquivo
    for somente no preto, gera a OS com 1 chapa so, e o nome do arquivo
    em GRAY".

    Ele esta certo, e a diferenca decide chapa: quase todo PDF fechado
    por designer traz as marcas de corte DELE em cor de registro, que e
    C, M, Y e K a 100% - fora do corte, onde nada imprime. Contando a
    pagina inteira, arte de preto puro com marcas de registro responde
    'quatro tintas', e o trabalho sai com QUATRO chapas onde devia sair
    uma. O cliente paga quatro.

    E a mesma linha que a regra do dpi ja usava: o que vale e o que cai
    dentro do corte. Ver _OlharDentroDoCorte, na montagem.
    """
    r = subprocess.run([GS, "-q"] + sem_perfil(sem_icc)
                       + (["-dUseTrimBox"] if so_o_corte else [])
                       + ["-o", "-", "-sDEVICE=inkcov", pdf],
                       capture_output=True, text=True, timeout=3600)
    paginas = []
    for linha in r.stdout.splitlines():
        p = linha.split()
        if len(p) >= 5 and p[4] == "CMYK":
            paginas.append(dict(zip("CMYK", [float(v) for v in p[:4]])))
    return paginas


def tintas_da_cobertura(cob):
    """{'C','K'} - as tintas que a pagina usa de verdade."""
    return set(l for l in "CMYK" if cob[l] > LIMIAR_TINTA)


def tintas_por_pagina(pdf, sem_icc=True):
    """
    Lista de sets, uma por pagina: [{'M','K'}, {'K'}, ...]

    SEM O PERFIL POR PADRAO, e isso mudou em 23/09/2026. Antes o padrao
    era com o perfil, e quem chamasse sem pensar contava tinta que o
    perfil espalhou em vez da que esta escrita no arquivo - que foi o
    defeito do 'WIL BURGUE' da FIALHO, no processador. Nao ha chamador
    hoje; o padrao fica certo para o primeiro que houver.
    """
    return [tintas_da_cobertura(c)
            for c in cobertura_por_pagina(pdf, sem_icc=sem_icc)]


def sem_cor_gritante(pdf, pagina=1, dpi=72, tolerancia=96, sem_icc=False):
    """
    True se nenhum pixel da pagina tiver cor de verdade.

    E a segunda pergunta da decisao do cinza, e serve so para pegar um
    caso que a conta da cobertura nao pega: uma arte com vermelho de um
    lado e ciano do outro pode fechar C, M e Y no mesmo total e passar por
    neutra. Aqui isso reprova, porque em ALGUM pixel os canais estao longe
    um do outro.

    A folga e larga (96 de 255) de proposito. Arte cinza de verdade nao
    tem canal igualzinho pixel a pixel: a borda do texto sai com ruido de
    anti-aliasing - num arquivo real, ate 39 de diferenca em 6% dos
    pixels. Com folga apertada, arte cinza legitima seria reprovada.

    Roda em dpi baixo, que e barato e basta para essa decisao. Na duvida
    (Ghostscript reclamou, imagem nao saiu) devolve False: erra para o
    lado da quadricromia, que e o que sempre foi feito.
    """
    from PIL import Image, ImageChops
    Image.MAX_IMAGE_PIXELS = None

    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_neutro_", dir=PASTA_CONTROLE)
    try:
        alvo = os.path.join(tmp, "p.tif")
        r = subprocess.run(
            [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET"] + sem_perfil(sem_icc)
            + ["-sDEVICE=tiff32nc",
               "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
               "-r%d" % dpi, "-sOutputFile=" + alvo, pdf],
            capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.exists(alvo):
            return False
        with Image.open(alvo) as im:
            c, m, y = im.split()[:3]
        for a, b in ((c, m), (c, y), (m, y)):
            if max(ImageChops.difference(a, b).getextrema()) > tolerancia:
                return False
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def separar_cinza(pdf, dpi, pasta_tmp, pagina=1, sem_perfil=False):
    """
    Rasteriza UMA pagina em escala de cinza. Devolve o caminho do TIFF.

    E o caminho da arte de uma cor so: uma chapa no lugar das quatro.
    Diferente do tiffsep, aqui 0 e preto e 255 e branco.

    'sem_perfil' NAO E DETALHE - e a diferenca entre a chapa sair com a
    porcentagem do arquivo ou com outra. Medido em 14/09/2026, num PDF
    com seis retangulos de tom conhecido:

                        COM perfil   SEM perfil
        K puro   25%        21,6%        25,1%
        K puro   50%        41,6%        50,2%
        K puro  100%        87,5%       100,0%
        composto 25%        42,4%        50,2%
        composto 50%        70,2%       100,0%

    Ou seja: cada caso quer um caminho, e usar um so estraga o outro.

    PRETO PURO pede sem_perfil=True. A conversao entao e direta - o K vai
    para o cinza sem passar pelo perfil ICC embutido, que e quem
    escurecia o tom. Foi o que aconteceu com o '49835 - Flor Bela -
    sacola': o chapado de 100% saia com 87,5%.

    PRETO COMPOSTO pede o perfil. Sem ele as quatro tintas SOMAM - um
    composto de 50% satura em 100% -, e a chapa sai preta onde devia ter
    meio-tom.
    """
    alvo = os.path.join(pasta_tmp, "cinza.tif")
    cmd = [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=tiffgray",
           "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
           "-r%d" % dpi, "-sCompression=lzw"]
    if sem_perfil:
        cmd.append("-dUseFastColor=true")
    cmd += ["-sOutputFile=" + alvo, pdf]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(alvo):
        raise RuntimeError((r.stderr or "erro no Ghostscript")[:300])
    return alvo


def separar_tintas(pdf, dpi, pasta_tmp, pagina=1, sem_perfil_=False):
    """
    Roda o tiffsep em UMA pagina.
    Gera s(Cyan).tif, s(Magenta).tif, ... dentro de pasta_tmp.

    'sem_perfil_' faz a separacao ler a cor COMO ESTA ESCRITA no
    arquivo. Vale para quem vem do CorelDRAW, que embute um perfil ICC
    em tudo que publica - e a ida e volta por esse perfil NAO e
    identidade. Medido no 'POLIPECAS - ETQIEUTAS' da PRIME, 14/09/2026,
    o mesmo arquivo na mesma resolucao, so mudando isto:

        area de chapado    sem perfil   com perfil
            preto             265 mm2      23 mm2
            magenta           413 mm2     207 mm2
            ciano          54.030 mm2  53.824 mm2

    Ou seja: o chapado de preto quase desaparece. E o mesmo defeito que
    tirou 12,5 pontos da chapa da VOPRIX em 14/09/2026, aqui no caminho
    da quadricromia.

    Arquivo SEM perfil embutido nao muda nada com isto ligado ou
    desligado - conferido no 'GRADE 1710' da VIVA, tinta por tinta.
    """
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=tiffsep"]
        + sem_perfil(sem_perfil_) +
        ["-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-r%d" % dpi, "-sCompression=lzw",
         "-sOutputFile=" + os.path.join(pasta_tmp, "s.tif"), pdf],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "erro no Ghostscript")[:300])


def enviar_para_impressora(pdf, impressora=None, timeout=900, duplex=False):
    """
    Manda um PDF para uma impressora do Windows.

    Usa o proprio Ghostscript (device mswinpr2), entao nao depende de ter
    Acrobat instalado nem de qual programa abre PDF na maquina.

    Espere um PDF ja no tamanho E no sentido da folha: quem monta isso
    e o prova.py. Aqui nao ha encaixe nenhum, de proposito.

    FRENTE E VERSO SE PEDE, NAO SE HERDA. A Konica esta configurada em
    simplex (Duplex=1 no driver), e por muito tempo o programa supos o
    contrario: mandava arte e ordem de servico num trabalho de duas
    paginas esperando uma folha dos dois lados, e saiam duas folhas.

    O -dDuplex do Ghostscript resolve sem tocar na configuracao da
    impressora - que e compartilhada, e mudar o padrao dela mudaria a
    impressao de todo mundo. Foi conferido no papel: com -dDuplex=true um
    trabalho de duas paginas sai numa folha so.

    -dTumble=false vira pelo lado LONGO, que e como se vira uma folha de
    caderno: o verso sai de cabeca para cima.

    O pedido vai sempre, ligado ou desligado, em vez de contar com o que
    estiver marcado na impressora naquele dia.
    """
    alvo = impressora or IMPRESSORA
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dNoCancel",
         "-dDuplex=" + ("true" if duplex else "false"), "-dTumble=false",
         "-sDEVICE=mswinpr2",
         "-sOutputFile=%printer%" + alvo, pdf],
        capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "erro ao imprimir")[:300])
    return alvo


# Como a tinta candidata a traco e medida: baixo o bastante para ser
# rapido, alto o bastante para o traco fino nao sumir. Medido na 'Pasta
# Agil Corretora' da VOPRIX em 16/09/2026: a 300 dpi ela da 8.209 pixels
# com ciano e ZERO so com ciano - o mesmo veredito de 150 e de 600.
DPI_DA_PROVA_DE_TRACO = 300

# Abaixo disto o pixel tem tinta. 250 de 255 deixa passar o quase-branco
# da compressao sem deixar passar tinta de verdade.
TEM_TINTA = 250


def tinta_aparece_sozinha(pdf, pagina, tinta, dpi=DPI_DA_PROVA_DE_TRACO,
                          sem_perfil_=False):
    """
    (aparece_sozinha, pixels_com_a_tinta) - ou (None, 0) se nao deu.

    A PERGUNTA QUE A PROPORCAO NAO FAZ.

    Uma tinta pode ser 5% da mais forte e ser traco, e outra pode ser 6%
    e ser o texto da peca. Nenhum limiar separa as duas, porque a
    proporcao nao sabe ONDE a tinta esta. Esta funcao sabe:

      tinta que NUNCA aparece sozinha  -> so enriquece tom de outra.
                                          Tirando-a, forma nenhuma some;
      tinta que aparece sozinha        -> desenha alguma coisa por conta
                                          propria. Tirando-a, some.

    O caso que a originou, em 16/09/2026: o ciano da 'Pasta Agil
    Corretora' da VOPRIX, 5,23% do magenta, com 8.209 pixels de ciano e
    NENHUM so de ciano. O operador ja tinha dito que o servico era MYK;
    isto foi a prova.

    DEVOLVE None QUANDO NAO CONSEGUE MEDIR, e quem chama tem de tratar
    isso como 'a tinta fica'. Chapa a mais na conta se conserta com uma
    conversa; chapa a menos no CTP so aparece na tiragem.
    """
    nome_do_canal = {"C": "Cyan", "M": "Magenta", "Y": "Yellow",
                     "K": "Black"}.get(tinta)
    if not nome_do_canal:
        return None, 0
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
    except ImportError:
        return None, 0

    pasta = tempfile.mkdtemp(prefix="traco_")
    try:
        separar_tintas(pdf, dpi, pasta, pagina, sem_perfil_=sem_perfil_)
        alvo = os.path.join(pasta, "s(%s).tif" % nome_do_canal)
        if not os.path.exists(alvo):
            return None, 0
        outros = []
        for letra, canal in (("C", "Cyan"), ("M", "Magenta"),
                             ("Y", "Yellow"), ("K", "Black")):
            if letra == tinta:
                continue
            c = os.path.join(pasta, "s(%s).tif" % canal)
            if os.path.exists(c):
                outros.append(Image.open(c).convert("L").load())
        if not outros:
            return None, 0

        im = Image.open(alvo).convert("L")
        larg, alt = im.size
        px = im.load()
        com_a_tinta = sozinha = 0
        for y in range(alt):
            for x in range(larg):
                if px[x, y] < TEM_TINTA:
                    com_a_tinta += 1
                    if all(o[x, y] > TEM_TINTA for o in outros):
                        sozinha += 1
                        if sozinha > 8:       # ja basta: ela desenha algo
                            return True, com_a_tinta
        return (sozinha > 0), com_a_tinta
    except Exception:
        return None, 0
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


# ----------------------------------------------------------------------
# A COR SOBREVIVEU AO ACHATAMENTO?
# ----------------------------------------------------------------------
# "gera o pdf e confere as cores se estao batendo, se nao perdeu na hora
# de converter e gerar o pdf" - o operador, 17/09/2026, sobre a VOPRIX.
#
# Achatar em imagem e seguro para FORMA - nao ha fonte que falte nem
# transparencia que achate errado. Mas e uma reamostragem de COR, e cor
# ja se perdeu nesta casa em silencio: em 09/09 o preto do canal K saiu
# remisturado nas quatro tintas e ninguem viu ate a chapa.
#
# Entao o achatado nao vale por si: ele tem de bater com o vetor.

# Quanto uma tinta pode mudar, em pontos de cobertura absoluta.
#
# MEDIDO nos tres .cdr da VOPRIX de 17/09/2026, achatando de verdade:
#
#     Stopper_CE     C +0,0168  M +0,0172  Y +0,0163  K -0,0040
#     Luva_Produto   C +0,0111  M -0,0007  Y +0,0107  K -0,0014
#     Luva_Simparic  C +0,0033  M +0,0119  Y +0,0033  K +0,0042
#
# O desvio e quase sempre PARA CIMA nas cores: o antisserrilhamento a 900
# dpi cria pixel de cobertura parcial em cada borda, e borda nao some no
# achatamento - aparece. O maior foi +0,0172.
#
# 0,035 e o dobro do maior desvio visto, e ainda pega o defeito que
# importa: quando o perfil ICC comeu o preto, em 09/09, o K caiu 0,046 e
# o C subiu 0,055. Entre 0,017 de ruido e 0,046 de estrago ha espaco, e
# 0,035 fica no meio dele.
FOLGA_DO_ACHATAMENTO = 0.035

# E a tinta PERDER um terco de si mesma nao passa, por menor que seja.
#
# Numero absoluto sozinho e cego para tinta fraca: o K do Stopper e
# 0,0421, e ele poderia cair para 0,010 - perdendo 76% - sem chegar perto
# dos 0,035. Seria exatamente o defeito do perfil ICC, em miniatura, e
# passaria batido.
SOBRA_MINIMA = 0.66            # o que tem de restar da tinta original
PERDA_QUE_IMPORTA = 0.005      # abaixo disto e ruido, nao perda


# E a tinta que SOME nao tem folga nenhuma.
#
# Uma cor que existia no vetor e zerou no achatado e objeto perdido -
# exatamente o que o operador temia. Abaixo disto a tinta nao existe.
TINTA_QUE_SUMIU = 0.0005


def cor_sobreviveu(antes, depois):
    """
    (bate, recado) comparando a cobertura do vetor com a do achatado.

    'antes' e 'depois' sao dicionarios {C, M, Y, K} da mesma pagina, os
    dois lidos do MESMO jeito - com ou sem perfil, mas iguais entre si.
    Comparar um lido com perfil contra outro lido sem ele acusaria
    diferenca que e da leitura, nao do arquivo.
    """
    sumiram = []
    mudaram = []
    for t in "CMYK":
        a, d = antes.get(t, 0.0), depois.get(t, 0.0)
        if a > TINTA_QUE_SUMIU and d <= TINTA_QUE_SUMIU:
            sumiram.append("%s (tinha %.4f, ficou %.4f)" % (t, a, d))
        elif (d < a * SOBRA_MINIMA and (a - d) > PERDA_QUE_IMPORTA):
            sumiram.append("%s (tinha %.4f, ficou %.4f - perdeu %.0f%%)"
                           % (t, a, d, 100.0 * (a - d) / a))
        elif abs(a - d) > FOLGA_DO_ACHATAMENTO:
            mudaram.append("%s %.4f -> %.4f (%+.4f)" % (t, a, d, d - a))

    if sumiram:
        return False, ("TINTA PERDIDA no achatamento: %s. Isso e objeto "
                       "que sumiu, nao arredondamento"
                       % ", ".join(sumiram))
    if mudaram:
        return False, ("a cor mudou demais no achatamento: %s (a folga e "
                       "%.2f)" % (", ".join(mudaram), FOLGA_DO_ACHATAMENTO))
    return True, ("cor conferida: " + ", ".join(
        "%s %.4f" % (t, depois.get(t, 0.0)) for t in "CMYK"))
