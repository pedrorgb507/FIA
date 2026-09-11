# -*- coding: utf-8 -*-
"""
Configuracao do FINART CTP.

Os valores aqui sao exemplos. Os caminhos reais de cada maquina ficam num
config_local.py ao lado deste, que nao vai para o controle de versao e
sobrescreve o que estiver aqui (veja o final do arquivo).
"""

# ----------------------------------------------------------------------
# PASTAS
# ----------------------------------------------------------------------

# Onde o cliente joga as artes. Dentro dela: MES\DIA
#   X:\ENTRADA\SETEMBRO\02
BASE_ENTRADA = r"X:\ENTRADA"

# Onde os PDFs prontos do CTP sao gravados:
#   Y:\CTP\SETEMBRO\03\FIA
# O programa acha a pasta do mes e do dia e cria a subpasta de saida
# dentro dela, do lado das pastas dos outros operadores.
BASE_CTP = r"Y:\CTP"
SUBPASTA_SAIDA = "FIA"

# Log, registro e arquivos temporarios ficam no PC. Os TIFFs da
# separacao chegam a varios GB: nao podem passar pela rede.
PASTA_CONTROLE = r"C:\CTP\_controle"

# Onde fica o que precisou de gente. Quando um arquivo da VOPRIX nao da
# para processar - grande demais, ilegivel -, o PDF que a Corel ja gerou
# e guardado aqui em vez de ser jogado fora. Assim o operador continua do
# ponto onde o programa parou (abre no Photoshop/InDesign, como sempre
# fez) sem converter o .cdr de novo, que e a parte demorada.
#
# Fica no disco local: esses arquivos passam de 500 MB e nao podem entupir
# a rede. Limpe a pasta de tempos em tempos.
PASTA_PENDENCIAS = r"C:\CTP\_pendencias"

# ----------------------------------------------------------------------
# SEGUNDO CLIENTE: VOPRIX
# ----------------------------------------------------------------------
# Mesma arvore de pastas da SOLIDA (dentro da base: MES\DIA), so que numa
# base propria. A diferenca esta no que chega e em como sai:
#
#   - a arte vem em .cdr, ja montada no tamanho da chapa. O CorelDRAW
#     desta maquina converte para PDF antes de qualquer coisa (corel.py);
#   - o nome de saida nao e por OS: e 510x400_CM_VOPRIX_Envelope_Saco.
#
# As chapas caem na MESMA pasta FIA do dia da SOLIDA - o proprio nome ja
# diz de quem e, entao nao ha o que confundir.
#
# Deixe None para o programa vigiar so a SOLIDA.
BASE_ENTRADA_VOPRIX = r"X:\VOPRIX"

# ----------------------------------------------------------------------
# TERCEIRO CLIENTE: FIALHO BRINDES
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA, base propria. O que muda e que o Fialho manda de
# tudo: PDF pronto no tamanho da chapa, PDF fora de tamanho, arquivo em
# Corel, arte que ainda precisa ser montada.
#
# PADRAO TEMPORARIO, combinado com o operador: so anda o que chega em PDF
# ja no tamanho final da chapa (510x400 ou 730x600). Qualquer outra coisa
# PARA e vira pendencia - nao se da andamento no servico. Conforme os
# casos forem aparecendo, a gente amplia.
#
# Deixe None para nao vigiar essa pasta.
BASE_ENTRADA_FIALHO = r"X:\FIALHO"

# ----------------------------------------------------------------------
# COMO O CORELDRAW DEVE PUBLICAR O PDF
# ----------------------------------------------------------------------
# O PublishToPDF nao escolhe nada sozinho: ele usa o que estiver marcado
# na janela de Publicar em PDF da maquina. E o que estava marcado era:
#
#     BitmapCompression   0      (nenhuma)
#     CompressText        False
#     DownsampleColor     False  <- com ColorResolution ja em 300, sem uso
#
# Ou seja, bitmap gravado CRU. Foi medido: um .cdr de 13 MB virou PDF de
# 1007 MB, e 1006 desses MB eram bitmap sem compactar. Nao e defeito da
# automacao - publicando pela janela da o mesmo, so que na mao o arquivo
# passa pelo Photoshop depois e ninguem ve o monstro do meio.
#
# Entao o programa passou a EXIGIR os ajustes, em vez de herdar:
#
# Sao dois ajustes, e os dois sao SEM PERDA: ZIP nos bitmaps e compressao
# nos comandos da pagina. Medido no Panfleto_M3RIN, o mesmo arquivo:
#
#     como estava        1007,5 MB
#     so ZIP               39,6 MB   <- 25x menor
#
# E o que sai e o MESMO arquivo: cobertura de tinta igual na quinta casa
# (C, M, Y e K com diferenca +0.00000) e a pagina rasterizada com
# 7.114.344 de 7.114.344 pixels identicos, diferenca maxima 0 de 255.
#
# NAO reamostramos, e isso foi decidido com numero na mesa. As imagens do
# cliente vem em ~1064 dpi no tamanho final, o que e mais do que a chapa
# grava (1000 dpi) e mais do que o offset usa (300-400). So que:
#
#   ZIP + 800 dpi   50,9 MB   MAIOR que sem reamostrar - a interpolacao
#                             inventa valores que comprimem pior
#   ZIP + 600 dpi   42,2 MB   idem
#   ZIP + 400 dpi   32,5 MB   7 MB a menos, e o QR CODE do panfleto sai
#                             borrado. Traco fino dentro do bitmap e o
#                             que quebra primeiro.
#
# Ou seja: reamostrar aqui custa qualidade e nao paga nada. A compressao
# ja faz o trabalho inteiro. Se um dia um arquivo passar do limite mesmo
# com ZIP, ai sim vale conversar sobre dpi - e olhando o QR code.
#
# Numeros do BitmapCompression, direto do CorelDRAW:
#   0 nenhuma   1 LZW   2 JPEG (com perda)   3 ZIP   4 JP2
#
# REAMOSTRAGEM: a janela de Publicar em PDF tem 'Reamostrar bitmaps para
# 300 dpi', e o ColorResolution da maquina esta em 300. Enquanto a caixa
# estiver desmarcada, nao acontece nada - mas bastava alguem marcar, ou
# um preset trocar, para TODA arte da VOPRIX sair reamostrada a 300 dpi.
# A chapa continuaria com os 1000 dpi de sempre, so que gravando uma arte
# de 300: a resolucao do arquivo mentiria e o servico ia para a maquina
# borrado. Prejuizo de tiragem inteira, e sem sintoma ate a impressao.
#
# Por isso as tres reamostragens sao DESLIGADAS na marra a cada conversao,
# em vez de herdadas. As resolucoes ficam acima do que a chapa grava, para
# que nem uma versao futura de Corel que ignore os interruptores consiga
# estragar a arte.
# A PREDEFINICAO da janela de Publicar em PDF, carregada pelo nome antes
# de qualquer ajuste. Foi o operador quem a montou e quem a mantem: e ela
# que decide cor de saida, sobreimpressao de preto, sangria e curva de
# texto. Carregar pelo nome tira isso da sorte - sem o Load, vale o que
# estiver marcado na janela da maquina naquele dia, e a janela e a mesma
# que o operador usa a mao.
#
# A FINART pede saida em CMYK (ColorMode 1). Vale conferir o que ela NAO
# faz: com ColorMode 0 (RGB) o preto cheio deste mesmo arquivo saiu como
# RGB 0.216 0.204 0.208 - cinza escuro, e sem volta. Por isso a conversao
# PARA se a predefinicao nao vier em CMYK, em vez de seguir e avisar.
#
# Deixe None para nao carregar predefinicao nenhuma.
PDF_CORELDRAW_PREDEFINICAO = "FINART"

# Modo de cor do CorelDRAW: 0 RGB, 1 CMYK, 2 tons de cinza, 3 nativo.
# Conferido nesta maquina publicando o mesmo .cdr em cada um.
COREL_CMYK = 1

# Clientes cujo PDF vai INTEIRO para o CTP, sem separacao de tintas.
#
# A separacao existe para virar IMAGEM o que so existia em vetor. Arte
# que ja chega em PDF, no tamanho da chapa e sem giro nem montagem, nao
# precisa dela - e paga caro por ela: a leitura do Ghostscript passa a
# cor pelo perfil ICC embutido e remistura o preto de K sozinho nas
# quatro tintas (ver entrega.py, com os numeros medidos).
#
# So entra aqui cliente cuja arte chega pronta. Fialho e Creative NAO
# entram: a arte deles e girada ou montada na chapa, e o caminho curto
# entrega o arquivo como ele veio.
ENTREGAR_PDF_DIRETO = ("VOPRIX",)

PDF_CORELDRAW = {
    "BitmapCompression": 3,        # pdfZIP, sem perda
    "CompressText": True,
    "DownsampleColor": False,      # nunca reamostrar bitmap colorido
    "DownsampleGray": False,       # nem em tons de cinza
    "DownsampleMono": False,       # nem traco 1 bit
    "ColorResolution": 1200,       # rede de seguranca, caso liguem
    "GrayResolution": 1200,
    "MonoResolution": 2400,
}

# ----------------------------------------------------------------------
# QUARTO CLIENTE: EMPORIO PRINT
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA, base propria. So manda PDF - nada de Corel - e o
# nome de entrada e "OS - descricao":
#
#     01995 - CHAPA CAIXA 4796.pdf
#     01965 - CHAPA - Maria Flor - Papel de Seda 45x65.pdf
#
# Entra como a SOLIDA (PDF pronto) e sai como a VOPRIX (formato, cores e
# cliente no nome). Deixe None para nao vigiar essa pasta.
BASE_ENTRADA_EMPORIO = r"X:\EMPORIO"

# ----------------------------------------------------------------------
# QUINTO CLIENTE: VIVA ACABAMENTOS
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA. Manda PDF e .cdr, mas SO O PDF ANDA - o .cdr para
# e vira pendencia, como no Fialho. Uma chapa so: 510x400.
#
# O nome de saida usa o proprio nome do arquivo como descricao, e frente
# e verso saem F e V, como na Solida:
#
#     GRADE 1637.pdf   ->  510x400_CMYK_VIVA_GRADE 1637
#     GRADE 38.pdf     ->  510x400_CMYK_VIVA_GRADE 38 F  e  ... V
#
# Deixe None para nao vigiar essa pasta.
BASE_ENTRADA_VIVA = r"X:\VIVA"

# ----------------------------------------------------------------------
# SEXTO CLIENTE: CREATIVE
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA, so PDF, e a mesma conferencia do EMPORIO: fora de
# quadricromia para, verniz para, arte de uma cor sai em GRAY.
#
# O QUE MUDA: a arte NAO vem no tamanho da chapa. Chega menor - 480x330,
# por exemplo - e e o programa que a monta na chapa de 510x400, o que
# ate hoje era feito a mao no InDesign. Duas regras, ditadas pelo
# operador e conferidas na chapa que ele fechou no dia 02:
#
#   - centralizada na largura;
#   - PINCA no pe: a borda de baixo da arte fica a PINCA_CREATIVE_MM da
#     borda de baixo da chapa.
#
# Pinca e a faixa que a maquina precisa para segurar o papel - ali nao
# pode haver desenho. Na Creative sao 4 cm.
#
# Conferido: a chapa '510x400_CMYK_CREATIVE_santinho cruvinel' fechada a
# mao trazia a arte de 480x330 com 15 mm de cada lado e 41,9 mm no pe.
# A regra dos 40 mm reproduz aquilo com menos de 2 mm de diferenca.
BASE_ENTRADA_CREATIVE = r"X:\CREATIVE"

PINCA_CREATIVE_MM = 40

# O maior lado que ainda e "formato 4". Acima disso e formato 2.
#
# Este numero ja existia em dois lugares, escrito a mao: o GEREMPRE
# decide entre F4 e F2 na OS por ele (montar_vaga), e a montagem escolhe
# a resolucao por ele. Mora aqui agora para os dois lerem o mesmo.
MAIOR_LADO_F4 = 560

# ----------------------------------------------------------------------
# AS MAQUINAS DA AMERICA
# ----------------------------------------------------------------------
# (largura, altura): (pinca_mm, apelido). As pincas vem da lista de
# chapas e pincas que o operador mantem ha anos - ver a skill de
# imposicao, chapas-e-pincas.md.
#
# A pinca e da MAQUINA, nao do formato: seis graficas usam a mesma
# 525x459 e cada uma com a sua. Estes numeros sao os da AMERICA.
CHAPAS_AMERICA = {
    (525, 459): (60.0, "PM_52"),
    (650, 550): (60.0, "MOZP_FT2"),
    (745, 605): (62.0, "SM_74"),
}

# Qual maquina recebe um trabalho, quando e a FIA que escolhe.
#
# Regra do operador, 10/09/2026: "se for formato maior do que o formato
# 4 e o arquivo for colorido, sera para a SM_74; se for peb geralmente e
# para a MOZP; e se for menor e para a PM52".
#
# O 'formato 4' acaba em MAIOR_LADO_F4 (560 mm), a mesma linha que o
# GEREMPRE usa para separar F4 de F2 na OS.
#
# O 'geralmente' do operador esta guardado: quando a escolha da FIA nao
# bater com o tamanho do arquivo que chegou, ela AVISA e usa o tamanho
# do arquivo - quem mandou o arquivo sabe de algo que a regra nao sabe.
AMERICA_F4 = (525, 459)          # ate o formato 4
AMERICA_GRANDE_COR = (745, 605)  # maior que F4, colorido
AMERICA_GRANDE_PB = (650, 550)   # maior que F4, preto e branco

# A arte da Creative as vezes chega EM PE, e ai e girada para deitar
# antes de entrar na chapa - 'deixar da forma que sempre vem', como
# disse o operador. 90 = para a direita (horario), 270 = para a
# esquerda.
#
# Girar 90 graus nao mexe em nada do desenho: e trocar linha por
# coluna. O tamanho da arte NAO muda - nunca muda, em cliente nenhum.
# Girando, o pe da arte passa a ser outra borda do arquivo, e a pinca
# sai da marca de corte daquela borda.
# 270 = para a ESQUERDA, escolhido pelo operador. Com ele a borda da
# esquerda do arquivo desce e vira a pinca.
GIRO_CREATIVE = 270

# ----------------------------------------------------------------------
# FORMATOS ACEITOS
# ----------------------------------------------------------------------
# (largura_mm, altura_mm): (dpi, sufixo_no_nome)

FORMATOS = {
    (510, 400): (1000, ""),
    (775, 635): (800,  "R1"),
}

# O VOPRIX SO USA A 510x400. Dito pelo operador em 11/09/2026:
# "voprix nao tem chapas 775x635 somente a solida".
#
# Ate esse dia ele caia na tabela da SOLIDA por nao ter a sua, e com ela
# herdava a 775x635. Isso nao dava erro em lugar nenhum - dava coisa
# pior: a FIA FECHAVA a chapa grande do VOPRIX e depois nao conseguia
# lancar a OS, porque GEREMPRE_CHAPAS so tem a 510x400 para ele. O
# servico ia para a chapa e ficava sem cobranca ate alguem ler a
# pendencia.
#
# Com tabela propria, a medida errada para na ENTRADA - vira pendencia
# de formato antes de virar chapa, que e onde ela tem de parar.
FORMATOS_VOPRIX = {
    (510, 400): (1000, ""),
}

# O Fialho tem a propria tabela: a chapa grande dele e 730x600, que nao
# existe na Solida. O formato entra no nome, entao aqui nao ha sufixo.
FORMATOS_FIALHO = {
    (510, 400): (1000, ""),
    (730, 600): (800,  ""),
}

# A chapa grande do Emporio e outra ainda: 660x605.
FORMATOS_EMPORIO = {
    (510, 400): (1000, ""),
    (660, 605): (800,  ""),
}

# A VIVA so usa uma chapa. Qualquer outra medida vira pendencia.
FORMATOS_VIVA = {
    (510, 400): (1000, ""),
}

# A CREATIVE tambem so usa uma chapa - mas aqui a arte chega MENOR e
# e montada nela, com a pinca no pe. Ver PINCA_CREATIVE_MM.
FORMATOS_CREATIVE = {
    (510, 400): (1000, ""),
}

TOLERANCIA_MM = 3

# ENCAIXE (so FIALHO). Ate esta diferenca, arte que nao bate com nenhuma
# chapa entra CENTRALIZADA na chapa mais proxima: o que sobra e cortado
# igualmente dos dois lados, o que falta vira branco.
#
# Combinado com o operador para o caso real do 'CAPA Agenda PAULISTA
# 2027.pdf', que mede 520x400 e e chapa 510x400 - os 5 mm de cada lado
# nao tem nada. ACIMA deste limite ninguem adivinha o que pode ser
# cortado, entao vira pendencia como antes.
ENCAIXE_MAXIMO_MM = 15

# Etiqueta escrita no canto da folha de prova, fora da arte, para quem
# pega o papel saber de que chapa se trata.
ROTULOS_PROVA = {
    (510, 400): "SOLIDA F4",
    (775, 635): "SOLIDA F2",
}

# A mesma etiqueta, para as provas da VOPRIX. Uma tabela por cliente
# porque quem pega o papel precisa saber tambem de quem e a chapa.
# So a F4: o VOPRIX nao tem a chapa grande. A linha da 775x635 saiu em
# 11/09/2026 junto com FORMATOS_VOPRIX - ficando aqui ela seria etiqueta
# morta, esperando alguem devolver o formato por engano.
ROTULOS_PROVA_VOPRIX = {
    (510, 400): "VOPRIX F4",
}

ROTULOS_PROVA_FIALHO = {
    (510, 400): "FIALHO F4",
    (730, 600): "FIALHO F2",
}

ROTULOS_PROVA_EMPORIO = {
    (510, 400): "EMPORIO F4",
    (660, 605): "EMPORIO F2",
}

ROTULOS_PROVA_VIVA = {
    (510, 400): "VIVA F4",
}

ROTULOS_PROVA_CREATIVE = {
    (510, 400): "CREATIVE F4",
}

# ----------------------------------------------------------------------
# NOME DE SAIDA DO EMPORIO PRINT
# ----------------------------------------------------------------------
# O padrao dos operadores, lido das chapas que eles fecharam a mao:
#
#     510x400_CMYK_EMPORIO_01987_Guia
#     660x605_GRAY_EMPORIO_01965_Maria Flor
#     510x400_CMYK_EMPORIO_01995_CAIXA 4796_1   (pagina 1)
#     510x400_GRAY_EMPORIO_01995_CAIXA 4796_2   (pagina 2)
#
# A OS identifica o servico, como o cliente identifica na VOPRIX. A
# descricao vem do nome do arquivo, sem as palavras que so dizem que
# aquilo e um trabalho de chapa - a mesma ideia do nome principal do
# Fialho. VERNIZ NAO entra nesta lista de proposito: chapa de verniz
# precisa aparecer no nome.
PALAVRAS_SERVICO_EMPORIO = {
    "CHAPA", "CHAPAS", "ARTE", "ARTES", "REGRAVAR", "REGRAVA", "REGRAVACAO",
    "FORMATO", "MODELO", "MODELOS", "GRADE",
}

# Ate quantos caracteres a descricao entra no nome. Os operadores
# abreviam a mao - 'Guia', 'CXBLANT' - e isso ninguem adivinha; o teto e
# o meio termo entre o nome deles e o titulo inteiro do arquivo. O corte
# respeita a palavra: nao parte no meio.
MAXIMO_DESCRICAO_EMPORIO = 25

# Copia de seguranca que o CorelDRAW cria sozinho ao lado do arquivo do
# operador. Nao e trabalho: e backup automatico. Sem isto, cada uma delas
# viraria uma pendencia inutil na tela, todo dia.
PREFIXOS_DE_BACKUP = ("COPIA_DE_SEGURANCA_DE_", "BACKUP_OF_",
                      "COPIA DE SEGURANCA DE ", "BACKUP OF ")

# Arquivo de ARTE que o programa nao sabe tratar. Nao e lixo do
# Windows nem sobra de programa: e o trabalho de alguem, largado numa
# pasta de cliente. Ignorar em silencio e servico que ninguem lembra
# de fazer - entao vira pendencia, uma vez.
#
# Nasceu da Creative: ela ja mandou 7 arquivos .cdr em dias passados, e
# o programa so olhava .pdf naquela pasta. Cada um deles teria sumido
# da vista sem uma linha no log.
EXTENSOES_DE_ARTE = (".cdr", ".ai", ".eps", ".psd", ".indd",
                     ".tif", ".tiff", ".jpg", ".jpeg", ".png")

# ----------------------------------------------------------------------
# PREFLIGHT: a conferencia da arte por dentro
# ----------------------------------------------------------------------
# RESOLUCAO EFETIVA e quantos dpi a imagem tem NO TAMANHO EM QUE FOI
# COLOCADA - e nao o dpi do arquivo dela. Uma foto de 300 dpi ampliada
# ao dobro vira 150, e nada no arquivo denuncia isso.
#
# A chapa grava a 1000 dpi de qualquer jeito: arte ruim sai lisinha e
# so mostra o defeito na tiragem, com a chapa queimada.
#
# Os dois numeros sao diferentes de proposito. 300 dpi e o que o offset
# pede e o que a maioria da arte boa tem - abaixo disso vale um aviso,
# nao vale parar servico. Abaixo de 200 nao ha discussao: sai borrado.
RESOLUCAO_EFETIVA_MINIMA = 200        # abaixo disto, PARA
RESOLUCAO_EFETIVA_BOA = 300           # abaixo disto, so avisa

# Clientes que NAO param por baixa resolucao: o aviso sai no log, com o
# numero de dpi, e a chapa segue.
#
# Decisao do operador em 09/09/2026, sobre a SOLIDA. A arte dela vem do
# cliente final e chega como chega - em 09/09 dois adesivos de bola de
# 30 cm vieram com imagem de 26 dpi, e os dois foram fechados a mao logo
# depois de a FIA parar. Trava que e liberada toda vez nao esta
# protegendo ninguem: so atrasa o serviço e ensina a ignorar aviso.
#
# E a mesma razao pela qual a SOLIDA ja ficava de fora das travas de cor.
# Adesivo grande se olha de longe, e quem decide o que e aceitavel ali e
# quem conhece o trabalho.
#
# SO A RESOLUCAO. Fonte nao incorporada continua parando a SOLIDA, e deve
# continuar: aquilo troca a forma do texto, e ninguem ve antes da
# tiragem.
#
# A VIVA ENTROU EM 10/09/2026, pela mesma razao e com o mesmo teste no
# mundo. Naquele dia chegaram quatro grades e TRES pararam por resolucao
# - GRADE 41, 42 e 43, todas a 199,67 dpi, tres decimos abaixo do
# limite. A arte da VIVA e grade de acabamento e vem do cliente final
# como chega; parar tres de quatro e a trava atrapalhando mais do que
# protegendo.
#
# A LISTA E EXPLICITA, e cliente so entra nela quando o operador disser.
# Ele foi claro em 10/09: "somente nesses, se houver necessidade em
# outros eu te aviso".
CLIENTES_SEM_TRAVA_DE_RESOLUCAO = ("SOLIDA", "VIVA")

# Risco mais fino que isto some na chapa. O caso classico e o traco de
# espessura ZERO, que o desenhista nem ve na tela: o PDF manda 'a linha
# mais fina que o aparelho conseguir', e a 1000 dpi isso da 0,025 mm.
#
# O numero e 0,05 e nao 0,10 por um motivo medido: 0,088 mm e 0,25 pt,
# a espessura padrao das MARCAS DE CORTE. Ela aparece em quase todo
# arquivo que passa por aqui, imprime perfeitamente, e com o limite em
# 0,10 a FIA reclamava de cinco arquivos em cinco da Solida. Aviso que
# aparece sempre nao e aviso.
TRACO_MINIMO_MM = 0.05

# Imagem menor que isto em QUALQUER lado nao entra na conta da
# resolucao. Nao e desleixo: tirinha de degrade e fiozinho de moldura
# sao feitos de proposito com poucos pixels esticados, e sempre
# apareceriam como 'baixa resolucao'.
#
# Medido num folder de verdade da Creative: uma tira de 4 x 210 mm a
# 182 dpi pararia o servico inteiro, e ninguem enxerga a diferenca
# num degrade de 4 mm. Aviso que grita por isso vira aviso ignorado.
LADO_MINIMO_IMAGEM_MM = 20

# Trabalho que NUNCA fecha sozinho, por mais que o resto esteja em ordem.
# Pedido do operador: verniz se confere antes.
PALAVRAS_QUE_PEDEM_OLHO = {"VERNIZ"}

# ----------------------------------------------------------------------
# NOME DE SAIDA DO FIALHO
# ----------------------------------------------------------------------
# A chapa dele se chama pelo NOME PRINCIPAL do servico - quase sempre o
# cliente final:
#
#     FORRO AGENDA unicidades 2027.pdf  ->  510x400_FIALHO_UNICIDADES 01
#
# 'forro', 'miolo', 'capa' sao tipo de material, nao nome de servico. A
# lista abaixo e o que o programa joga fora ao procurar o nome principal;
# numero solto e medida (48x66) tambem caem. Se nao sobrar nada, o nome do
# arquivo inteiro vira o nome, em maiuscula e sem acento.
#
# ESTA LISTA E PARA CRESCER: toda vez que uma chapa sair com nome errado,
# a correcao costuma ser acrescentar a palavra aqui.
PALAVRAS_MATERIAL = {
    # material e tipo de peca
    "FORRO", "MIOLO", "CAPA", "PASTA", "DIVISORIA", "INTRODUCAO", "AGENDA",
    "CADERNO", "CALENDARIO", "ENVELOPE", "BLOCO", "BLOCOS", "GRADE", "DOBRA",
    "FOLHA", "FOLHAS", "ADESIVO", "CARTAO", "TAG", "ETIQUETA", "PANFLETO",
    # o que se faz com a peca
    "MONTAGEM", "MONTAGEN", "CORRECAO", "PROVA", "REGISTRO", "GABARITO",
    "FRENTE", "VERSO", "FINAL", "NOVO", "NOVA", "MODELO", "COLORIDA",
    "COLORIDO", "EMPRESARIAL", "DADOS", "PESSOAIS", "PROTOCOLO", "JANELA",
    # palavras de medida e contagem
    "FORMATO", "IMAGEM", "IMAGENS", "CHAPA", "CHAPAS", "PAGINA", "PAGINAS",
    "TAMANHO", "COPIA", "SEGURANCA",
    # ligacao
    "DE", "DA", "DO", "DAS", "DOS", "E", "COM", "SEM", "PARA", "POR", "EM",
    "A", "O", "AS", "OS", "NO", "NA",
}

# ----------------------------------------------------------------------
# OPERACAO
# ----------------------------------------------------------------------

# A pasta de entrada e compartilhada: o programa NUNCA apaga nem move
# nada de la. O controle do que ja foi feito fica no _processados.json,
# dentro da PASTA_CONTROLE, aqui no PC.
REGISTRO = "_processados.json"

# Acima disso o arquivo nao e processado: vira pendencia com aviso na
# tela. Nasceu de um .cdr de 375 MB que a Corel exportou como um PDF de
# 2,2 GB - tamanho que travava a leitura e inviabilizava a chapa.
#
# Estava em 500 MB, e o numero era conservador demais: barrou o
# '02037 - CHAPA - Caixas Filara 18 modelos.pdf' do Emporio, de 528 MB,
# que e um trabalho normal - 9 chapas de 510x400. Medido nele:
#
#     cobertura das 9 paginas    19 s
#     separar e montar 1 chapa   70 s   (15,4 MB de saida)
#
# Ou seja, o mesmo tempo dos outros trabalhos do dia - o 49729, de 62 MB,
# levou 172 s. Tamanho de arquivo diz pouco sobre o trabalho de gravar:
# quem manda e a area da chapa e o dpi, que sao sempre os mesmos.
#
# O limite continua existindo como valvula, agora onde ele de fato
# protege: o PDF de 2,2 GB da Corel ainda seria barrado. E aquela
# patologia foi consertada na origem - com ZIP obrigatorio, o mesmo
# arquivo passou de 1007 MB para 39,6 MB (ver PDF_CORELDRAW).
TAMANHO_MAXIMO_MB = 2000

# PASSO 1 DO PROCESSO: cada arte aceita sai impressa (o arquivo ORIGINAL,
# nao a chapa) antes das chapas serem geradas. A chapa e maior que o papel
# da impressora, entao a prova sai reduzida, em A4 retrato.
# Deixe IMPRIMIR_ORIGINAL = False para desligar a impressao.
# Se a impressora falhar, a chapa NAO e gerada: o arquivo fica segurado
# e o programa tenta de novo de tempos em tempos, ate a prova sair.
IMPRIMIR_ORIGINAL = True
IMPRESSORA = "NOME DA IMPRESSORA NO WINDOWS"
ESPERA_IMPRESSORA = 300        # segundos entre tentativas (5 min)

# A VOPRIX so fecha sozinha o que vem em quadricromia. Arte de 1, 2 ou 3
# cores - ou em escala de cinza - PARA antes de gerar a chapa: a prova sai
# do mesmo jeito, o PDF convertido fica guardado na PASTA_PENDENCIAS e o
# aviso aparece na tela, com a cobertura de cada tinta, para alguem
# conferir. Quem manda fechar depois e gente.
#
# Pedido do operador: em quadricromia o caminho e sempre o mesmo, mas arte
# de uma cor ou de duas e onde a decisao muda de trabalho para trabalho.
AVISAR_QUANDO_NAO_FOR_CMYK = True

# Arquivo que aparece na pasta mas nao termina de chegar - 0 byte, ou
# crescendo sem parar - e pulado a cada varredura, calado. Depois deste
# tempo o programa avisa, uma vez so.
#
# Nasceu de caso real: em 08/09/2026 um PDF de 4 OS foi salvo com 0 byte
# e ficou 3 minutos parado na pasta. O programa fez certo em nao tocar
# nele, mas ninguem soube - o operador so viu que a chapa nao saiu.
AVISAR_ARQUIVO_PARADO = 120        # segundos (2 min)

# Se voce vira a noite, a pasta do dia so troca depois desta hora.
HORA_VIRADA = 0

# Segundos entre uma varredura e outra da pasta.
INTERVALO = 5

# Caminho fixo do Ghostscript. Deixe None para procurar sozinho.
GS_EXE = None

# Nomes dos meses, na ordem. Serve para achar a pasta do mes mesmo que ela
# esteja escrita diferente na rede (MARCO / MARÇO / Marco / marco).
MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

# ----------------------------------------------------------------------
# TABELAS DE TINTA (nao mexer)
# ----------------------------------------------------------------------

NOMES_TINTA = {"Cyan": "C", "Magenta": "M", "Yellow": "Y", "Black": "K"}
CMYK_PDF = {"C": "/Cyan", "M": "/Magenta", "Y": "/Yellow", "K": "/Black"}

# ----------------------------------------------------------------------
# GEREMPRE - a OS da empresa
# ----------------------------------------------------------------------
# O GEREMPRE e o programa que a Finart usa para ordem de servico,
# estoque e faturamento. Banco Firebird 1.5.
#
# ATENCAO: escrever aqui MEXE EM ESTOQUE. O gatilho TR_OS_BEFO lanca
# movimento na tabela MOV quando a OS marca chapa. Por isso o padrao
# aponta para a COPIA DE TESTE, e so muda para o banco de verdade com
# decisao consciente, no config_local.py.
GEREMPRE_DSN = r"127.0.0.1/3050:C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb"
GEREMPRE_CLIENTE_DLL = r"C:\GEREMPRE FIA TESTE\_firebird15\fbclient64.dll"
GEREMPRE_USUARIO = "sysdba"
GEREMPRE_SENHA = "masterkey"
# O nome que vai em OSRESP e aparece na OS e no protocolo. Mudado em
# 10/09/2026 a pedido do operador: 'FIA' sozinho nao dizia a quem
# pertencia o servico para quem lesse o papel de fora da casa.
#
# O cadastro na FUN (funcionario 32) foi mudado junto, no mesmo dia -
# senao a OS diria uma coisa e o programa Delphi outra. Cabe: a coluna
# tem 50 letras nas duas tabelas.
GEREMPRE_RESPONSAVEL = "FINART (FIA)"

# O funcionario FIA no cadastro do GEREMPRE (CADASTRO / FUNCIONARIO).
# E por ele que se sabe, olhando a OS, que foi a FIA quem abriu: o
# codigo vai em OSUSR_ALT e o nome em OSRESP, como o programa faz com
# WILKER (24), JOAOZIMAR (27) e os outros.
GEREMPRE_FUNCIONARIO = 32          # cargo 5, OPERADOR DE BUREAU

# Codigo da Finart no cadastro de clientes, para a chapa propria.
GEREMPRE_CLIENTE_FIA = 0

# Cada cliente da FIA e o codigo dele no cadastro do GEREMPRE.
#
# Cuidado com os homonimos: ha dois cadastros de VIVA, e o trabalho de
# chapa vai no 511 (VIVA GRAFICA - CHAPAS). O 129 (VIVA ACABAMENTOS) nao
# teve nenhuma OS de chapa em 2026.
GEREMPRE_CLIENTES = {
    "SOLIDA": 161,
    "VOPRIX": 420,
    "FIALHO": 114,
    "EMPORIO": 508,
    "VIVA": 511,
    "CREATIVE": 268,
    # AMERICA (GRAFICA E EDITORA AMERICA LTDA). Ela NAO e varrida pelo
    # vigia: nao ha BASE_ENTRADA_AMERICA, de proposito. O arquivo dela
    # chega POR MONTAR, e so entra no fluxo depois que o operador o move
    # para a pasta 'PARA CTP' - ver a skill de imposicao, america.md.
    "AMERICA": 58,
}

# (cliente, (maior_lado, menor_lado)) -> (codigo, nome, preco, tipo)
#
# Levantado das OS de 2026, uma a uma - nao e tabela de preco de gaveta,
# e o que foi cobrado de verdade:
#
#   SOLIDA   cod 98   1194 OS   R$  9,00
#   SOLIDA   cod 103   424 OS   R$ 13,00
#   FIALHO   cod 95    164 OS   R$ 10,00
#   FIALHO   cod 96     22 OS   R$ 15,00
#   EMPORIO  cod 101   282 OS   R$ 10,00
#   VIVA     cod 93    160 OS   R$  8,50
#   VOPRIX   cod 12    817 OS   R$ 20,00   (chapa propria)
#   CREATIVE cod 12    202 OS   R$ 20,00   (chapa propria)
#
# O operador lembrava R$ 15,00 na chapa propria pequena; as 1019 OS de
# 2026 dizem 20,00, sem uma excecao, e ele confirmou 20,00.
GEREMPRE_CHAPAS = {
    # cliente traz a chapa: cobramos a gravacao
    ("SOLIDA", (510, 400)): (98, "SOLIDA FT4", 9.00, "cliente"),
    ("SOLIDA", (775, 635)): (103, "SOLIDA 775X635 - 780E", 13.00, "cliente"),
    ("FIALHO", (510, 400)): (95, "FIALHO CHAPA FT4", 10.00, "cliente"),
    ("FIALHO", (730, 600)): (96, "FIALHO CHAPA FT2", 15.00, "cliente"),
    ("EMPORIO", (510, 400)): (101, "510 X 400 - EMPORIO FT4", 10.00,
                              "cliente"),
    ("VIVA", (510, 400)): (93, "CHAPA VIVA - FT4", 8.50, "cliente"),

    # AS TRES MAQUINAS DA AMERICA. Precos lidos do proprio GEREMPRE em
    # 10/09/2026, dos usos MAIS RECENTES de cada chapa - e nao do que
    # aparece mais vezes na historia: a MOZP tem 272 lancamentos a
    # R$ 10,00 e 112 a R$ 12,00, mas tudo desde agosto esta em 12, entao
    # 10 e preco velho. Contar frequencia teria cobrado a menos.
    ("AMERICA", (525, 459)): (90, "PM_52", 8.00, "cliente"),
    ("AMERICA", (650, 550)): (91, "MOZP_FT2", 12.00, "cliente"),
    ("AMERICA", (745, 605)): (89, "SM_74", 12.00, "cliente"),
    # CUIDADO, tres vezes:
    #  - ha uma chapa 15 chamada '525X459' de dono 0 (propria da Finart)
    #    que NAO e a da AMERICA. Usar a 15 baixaria estoque alheio;
    #  - ha codigos VELHOS para as mesmas maquinas (67 'PM 52', 76
    #    'MOZP', 10 'SM 74'). Os que a casa usa hoje sao 89, 90 e 91;
    #  - o resto do cadastro da AMERICA (BOPP, VERNIZ, FOTOLITO,
    #    COMUNICACAO VISUAL) e acabamento, nao e chapa de CTP.

    # chapa propria: chapa + gravacao
    ("VOPRIX", (510, 400)): (12, "510X400 - 0,15", 20.00, "propria"),
    ("CREATIVE", (510, 400)): (12, "510X400 - 0,15", 20.00, "propria"),
    ("EMPORIO", (660, 605)): (18, "660X605 - 0,30", 35.00, "propria"),
}
# FALTA CADASTRAR, e por isso vira pendencia em vez de chute:
# A VOPRIX usa SO a chapa pequena - confirmado pelo operador. Uma arte
# dela em 775x635 nao deveria existir; se aparecer, vira pendencia em
# vez de OS com preco chutado.

# Onde a folha da OS e gravada como PDF enquanto o servico anda.
#
# O operador pediu que o PDF da ordem de servico EXISTA em disco durante
# o processo - da para abrir e conferir o que esta indo no verso da
# prova -, e que suma depois, para a pasta nao encher de uma OS por
# arquivo fechado, todo dia.
#
# Deixe None para nao gravar nada: a impressao usa a folha que ja esta
# na memoria, e nao este arquivo.
# Ate quantos dias para tras a FIA procura um servico que ja foi lancado
# a mao. Alem disso, e outro servico com o mesmo nome.
#
# A VIVA reaproveita nome de grade: o 'GRADE 40' de 09/09/2026 casou com
# o 'GRADE 40' da MESMA cliente de 21/08/2024, e a prova saiu com o
# numero de uma OS de dois anos atras impresso no verso. O arquivo chega
# na pasta do dia e e fechado no mesmo dia ou no seguinte - um mes e
# folga de sobra.
GEREMPRE_JANELA_DIAS = 30

PASTA_PDF_OS = r"C:\GEREMPRE FIA TESTE\PDF de OS"

# ----------------------------------------------------------------------
# ENTRADA PELO TEAMS
# ----------------------------------------------------------------------
# Raiz das pastas que o OneDrive sincroniza do SharePoint do time.
# Dentro dela, UMA pasta por cliente, com o NOME DO CLIENTE:
#
#   ...\Finart Digital\CTP\SOLIDA
#   ...\Finart Digital\CTP\VOPRIX
#
# O que o cliente postar no canal dele cai nessa pasta sozinho, pelo
# OneDrive, e a ponte (entrada_teams.py) leva para a pasta do dia dele
# no V:. Dali em diante e o caminho de sempre.
#
# Vazio DESLIGA a ponte, sem barulho: o programa segue vigiando o V:
# como sempre fez. Foi feito assim para poder subir o codigo em maquina
# que ainda nao tem o OneDrive configurado.
PASTA_TEAMS = r""

# Onde a ponte anota o que ja trouxe, para nao trazer o mesmo arquivo
# duas vezes. Fica ao lado do registro das chapas, em PASTA_CONTROLE.
REGISTRO_TEAMS = "_trazidos_do_teams.json"

# Quem manda arquivo pelo Teams. Os outros continuam chegando no V: do
# jeito de sempre - a ponte nem olha para eles.
#
# Esta lista precisa ser EXPLICITA, e nao 'todo cliente que tiver pasta
# la'. E ela que da sentido ao aviso de pasta sumida: sem ela, cliente
# que nunca esteve no Teams reclamaria de pasta faltando a cada
# arranque, cinco avisos por dia, e em duas semanas ninguem mais leria
# aviso nenhum - inclusive o do cliente que esta mesmo parado.
CLIENTES_NO_TEAMS = ("SOLIDA",)

# Caminho PROPRIO de um cliente, quando ele nao mora sob PASTA_TEAMS:
#
#   CAIXAS_TEAMS = {"EMPORIO": r"C:\Users\...\Emporio - Documentos"}
#
# Hoje so a SOLIDA anda pelo Teams, e um canal PADRAO serve. No dia em
# que entrar um segundo cliente, canal padrao deixa de servir: ele e
# visivel a TODO o time, e dois clientes concorrentes veriam a arte e as
# OS um do outro. A saida sera canal privado ou link de solicitacao - e
# os dois ganham site proprio no SharePoint, fora da raiz.
#
# Este dicionario e a porta para esse dia: uma linha por cliente, sem
# reescrever a ponte. Caminho explicito, nunca derivado de PASTA_TEAMS -
# se fosse derivado aqui, o config_local trocaria a raiz depois e este
# valor ficaria para tras, apontando para o lugar errado em silencio.
CAIXAS_TEAMS = {}

# Pasta que a ponte NUNCA abre, mesmo descendo nas subpastas. E onde se
# envelhece arquivo velho pelo SharePoint sem a ponte trazer tudo de
# volta - o registro seguraria, mas registro se perde quando a maquina
# troca, e ai viria um ano de arquivo de uma vez.
PASTAS_IGNORADAS_TEAMS = ("Arquivado",)

# A RAJADA DA SEGUNDA-FEIRA
# -------------------------
# O programa nao e servico: roda enquanto a janela esta aberta. Cliente
# posta sabado e domingo; segunda de manha tudo entra junto - e cada
# arquivo abre OS no GEREMPRE de PRODUCAO, com baixa de chapa de
# verdade, e cospe prova na Konica.
#
# A partir de RAJADA arquivos esperando, a ponte diz o que vai fazer e
# segura ESPERA_RAJADA segundos antes do primeiro. Da tempo de Ctrl+C se
# algo estiver obviamente errado.
#
# Nao ha confirmacao obrigatoria de proposito: botao de confirmar vira
# reflexo depois de duas semanas, e ai protege menos que nada.
RAJADA = 3
ESPERA_RAJADA = 30

# ----------------------------------------------------------------------
# Ajustes desta maquina, fora do controle de versao.
# ----------------------------------------------------------------------
# Fica no FIM do arquivo de proposito: o que vem depois sobrescreve o que
# veio antes. Quando esta importacao morava no meio, tudo que estivesse
# abaixo dela - o bloco GEREMPRE inteiro - voltava ao valor de fabrica
# sem avisar. Um GEREMPRE_DSN apontado para producao seria trocado pelo
# de teste em silencio, e a FIA escreveria no banco errado achando que
# estava no certo.

try:
    from .config_local import *          # noqa: F401,F403,E402  # isort: skip
except ImportError:
    pass


# ----------------------------------------------------------------------
# A TABELA DE FORMATOS DA CASA
# ----------------------------------------------------------------------
# Passada pelo operador em 11/09/2026, em centimetro, e guardada aqui em
# MILIMETRO - que e a unidade de todo o resto.
#
# Cada formato tem a AREA TOTAL (a folha) e a AREA UTIL (o que se pode
# imprimir nela). Quem manda na conferencia da montagem e a UTIL: a
# folha inteira nao imprime.
#
# UM NUMERO PODE TER MAIS DE UMA FOLHA, e nao e erro de digitacao: o
# F-04 e 33x48 OU 24x66, e o F-06 tem tres. Sao maneiras diferentes de
# cortar a folha grande, todas chamadas pelo mesmo numero. Por isso cada
# entrada e uma LISTA, e quem escolhe qual delas e o operador.
#
# NAO SAIU DO GEREMPRE de proposito: la o campo OSMON e texto livre
# ('F4', 'FT 4', 'FT4', 'F4 GER'...) e a medida ao lado ora e milimetro,
# ora centimetro, ora e a CHAPA em vez da folha.
#
# ESTA TABELA TEM UMA COPIA no painel_imposicao.html, em JavaScript - a
# pagina nao tem servidor para ler daqui. Mudou aqui, muda la.
FORMATOS_DA_CASA = {
    1:  [((660, 960), (640, 900))],
    2:  [((480, 660), (460, 640))],
    3:  [((320, 660), (305, 640))],
    4:  [((330, 480), (315, 460)), ((240, 660), (230, 640))],
    5:  [((320, 340), (305, 325))],
    6:  [((240, 420), (220, 410)), ((320, 330), (305, 320)),
         ((220, 480), (205, 460))],
    7:  [((220, 370), (205, 355))],
    8:  [((240, 330), (220, 315)), ((165, 480), (150, 460))],
    9:  [((220, 320), (210, 310))],
    10: [((190, 330), (180, 315)), ((220, 260), (205, 250))],
    11: [((210, 250), (195, 235))],
    12: [((220, 240), (205, 225)), ((160, 330), (155, 320))],
    14: [((234, 192), (220, 180))],
    15: [((190, 220), (180, 205))],
    16: [((165, 240), (155, 225))],
    18: [((160, 220), (150, 205))],
    20: [((165, 192), (155, 180))],
    22: [((130, 220), (120, 210))],
    24: [((120, 220), (110, 200)), ((165, 160), (155, 150))],
    25: [((130, 190), (120, 180))],
    30: [((110, 192), (100, 180))],
    32: [((120, 165), (105, 150))],
}


def cabe_no_formato(larg, alt, formato, folha=0):
    """
    A montagem (larg x alt, em mm) cabe na area util deste formato?

    Devolve (cabe, sentido) - ou (None, None) quando o formato nao esta
    na tabela. NAO SEI e diferente de NAO CABE, e quem chama precisa
    poder ver a diferenca.

    A FOLHA ENTRA NOS DOIS SENTIDOS: a tabela escreve cada formato como
    largura x altura, mas 33x48 e a mesma folha que 48x33, e a montagem
    sai sempre DEITADA. Conferir num sentido so acusaria 'nao cabe' em
    montagem que cabe: o convite de 11/09 da 423 x 306 e o util do F-04
    e 315 x 460, que so serve virado.
    """
    folhas = FORMATOS_DA_CASA.get(formato)
    if not folhas:
        return None, None
    a, b = folhas[min(folha, len(folhas) - 1)][1]
    if larg <= a and alt <= b:
        return True, (a, b)
    if larg <= b and alt <= a:
        return True, (b, a)
    return False, None
