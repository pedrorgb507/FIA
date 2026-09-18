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

# QUEM CHEGA EM .cdr - e por isso tem de ser lido SEM O PERFIL ICC.
#
# A Corel embute um perfil de 557 KB em tudo que publica, e a cobertura
# lida atraves dele NAO e a do arquivo. Medido no 'POLIPECAS -
# ETQIEUTAS' da PRIME, 14/09/2026:
#
#     com perfil   C 0,5311  M 0,5325  Y 0,5342  K 0,5144
#     sem perfil   C 0,5246  M 0,5242  Y 0,0056  K 0,5246
#
# O perfil inventa 53% de amarelo onde o arquivo tem 0,56%. Contando por
# ele sairiam QUATRO chapas; o operador gravou TRES (o arquivo dele
# chama-se '510X400_CMK_PRIME_POLIPECAS_ETQIEUTAS.ps') e a OS 19704
# baixou -3 do estoque.
#
# Isto era 'ENTREGAR_PDF_DIRETO' antes, e as duas coisas viviam juntas
# por acidente: a VOPRIX entrega o PDF inteiro E vem do Corel. A PRIME
# vem do Corel e NAO entrega - ela precisa ser montada na chapa. Entao
# as duas perguntas se separaram.
CLIENTES_QUE_VEM_DO_COREL = ("VOPRIX", "PRIME")

# QUANDO UMA TINTA E SO TRACO, E NAO CHAPA - em proporcao a mais forte.
#
# Contado das tres OS da PRIME de 14/09/2026, onde o GEREMPRE diz quantas
# chapas cada servico gastou de verdade (OS 19704: -1, -3 e -4):
#
#   VALDINO - CHAPADO     CMY 0,0005 contra K 0,9085  = 0,06%   1 chapa
#   POLIPECAS - ETQIEUTAS Y   0,0056 contra  0,5246   = 1,07%   3 chapas
#   O.S 1034 - WAN        K   0,1993 contra Y 0,5151  = 38,7%   4 chapas
#
# Era 5%, e passou a 8% em 16/09/2026. O caso foi o
# 'Pasta_44x31_4_0_Agil_Corretora_de_Seguros_Correcao' da VOPRIX, que o
# operador viu sair CMYK devendo ser MYK:
#
#   C 0,00232  M 0,04433  Y 0,04432  K 0,01481   -> C = 5,23% da mais forte
#
# 5,23% caia do lado errado de um limiar de 5% por um fio. E que aquele
# ciano NAO era cor do trabalho ficou provado de um jeito que nao depende
# de limiar nenhum:
#
#   pixels com ciano, a 300 dpi ........ 8.209
#   deles, CIANO SOZINHO ...............     0
#
# Ciano que nunca aparece sem magenta, amarelo ou preto no mesmo pixel
# nao desenha forma alguma - so enriquece tom. Descarta-lo nao tira nada
# do impresso.
#
# 10% AGORA E SO A PENEIRA GROSSA, e nao mais a decisao.
#
# Ate 16/09/2026 a proporcao decidia sozinha, com 5%. Naquele dia ela
# bateu no proprio limite: o ciano da 'Pasta Agil Corretora' da VOPRIX
# vale 5,23% da tinta mais forte e E traco; e um K de 6,45% num teste de
# arte colorida E texto de verdade. Nenhum numero separa 5,23 de 6,45 -
# a proporcao nao tem a informacao necessaria.
#
# Quem separa e a pergunta que a proporcao nao faz: ESTA TINTA APARECE
# SOZINHA EM ALGUM PIXEL? Medido na chapa da Agil, a 300 dpi:
#
#   pixels com ciano ............ 8.209
#   deles, so com ciano .........     0
#
# Tinta que nunca aparece sem outra no mesmo pixel nao desenha forma
# nenhuma - so enriquece tom. Tira-la nao muda o impresso. Ja um K de
# texto aparece sozinho em toda letra.
#
# Entao: a proporcao levanta o CANDIDATO (barato, so numero), e
# 'tinta_aparece_sozinha' CONFIRMA (uma separacao a mais, so quando ha
# candidato). Nao dando para medir, a tinta FICA - o erro seguro e chapa
# a mais na conta, nunca chapa a menos no CTP.
TINTA_QUE_E_SO_TRACO = 0.10
CLIENTES_QUE_DESCARTAM_TINTA_DE_TRACO = ("PRIME", "VOPRIX")

# QUEM DEIXA A MONTAGEM NA PASTA DO DIA.
#
# "voce vai salvar de novo na pasta do dia com o mesmo nome mas
# _montagem no final... depois disso vai pegar essa montagem e continuar
# o procedimento normalmente" - o operador, 14/09/2026.
#
# E o passo que ele faz a mao. A montagem fica na pasta para ser
# conferida, E e dela que a chapa do CTP e gerada - entao o que foi para
# a gravadora e exatamente o que esta ali para olhar.
#
# A CREATIVE monta igual e NAO esta aqui: ela sempre montou sem deixar
# arquivo, e ninguem pediu para mudar.
CLIENTES_QUE_SALVAM_A_MONTAGEM = ("PRIME",)

# ----------------------------------------------------------------------
# QUEM MANDA ARTE POR MONTAR, E POR ISSO NAO LEVA TELA CHEIA
# ----------------------------------------------------------------------
# Regra do operador, 17/09/2026, sobre a FIALHO: "esse cliente tb manda
# alguns arquivos para eu montar por aqui, nem sempre ele ja manda
# montado (...) se o arquivo vier, sem estar montado, em varias paginas,
# ou em .cdr, voce so baixa pelo whatssap dentro da pasta, mais nao da
# andamento em montagem, so avisa que tem um arquivo la esperando
# analise".
#
# O programa JA nao dava andamento nesses arquivos - a regra de 14/09
# manda so andar o que chega em PDF no tamanho final da chapa. O que
# muda e o TOM: deixava de ser pendencia de tela cheia e passa a ser
# recado no log e no _PENDENCIAS.txt.
#
# Por que o tom importa. Tela cheia e para o que esta ERRADO e precisa
# de alguem agora. Arte por montar da FIALHO nao esta errada - e trabalho
# normal, esperando a vez de uma pessoa montar. Gritar por isso e o mesmo
# defeito do verniz, que abria uma tela por arquivo para dizer ao
# operador algo que ele ja sabia.
#
# SO VALE PARA ESTES DOIS SINAIS - nao e PDF, ou a pagina nao esta no
# tamanho de uma chapa do cliente. Defeito de verdade (resolucao baixa,
# OS que nao se acha, chapa que nao confere) continua gritando.
# ----------------------------------------------------------------------
# QUEM E ACHATADO EM IMAGEM DENTRO DO COREL
# ----------------------------------------------------------------------
# Regra do operador para a VOPRIX, 17/09/2026:
#
#   "estou percebendo que eles nao estao mandando os arquivos como antes,
#    convertido as imagens todas em 1 imagem, e somente os textos e
#    objetos sem converter, isso e perigoso, pode sumir algum objeto (...)
#    no corel mesmo, converta tudo em imagem 900 dpi, CMYK, gera o pdf e
#    confere as cores se estao batendo."
#
# O cliente mudou o jeito de mandar, e o jeito novo depende de fonte,
# transparencia e sobreimpressao serem lidas igual por quem grava.
# Achatado, nao ha o que interpretar: ha pixel.
#
# O PRECO: duas publicacoes por arquivo, porque o vetor e a referencia
# contra a qual a cor do achatado e conferida. Sem referencia nao ha
# conferencia, e foi conferencia que o operador pediu.
# Em 18/09/2026 o achatamento passou a POUPAR AS MARCAS - so a arte vira
# imagem, e cruz de registro, linha de corte e escala de cor ficam em
# vetor. Ver corel.separar_arte_das_marcas.
#
# O operador pediu para ligar em "VOPRIX, EMPORIO, PRIME". Foram medidos
# os tres, e so a VOPRIX entrou:
#
#   EMPORIO  nao abre no Corel. Manda so PDF - 42 arquivos no registro,
#            nenhum .cdr. Nao ha o que achatar.
#
#   PRIME    NAO ENTRA, por duas razoes independentes, medidas no
#            'O.S 1050 - SEDS FOLDER.cdr':
#
#            1. a cor nao sobrevive. O K cai de 0,2031 para 0,1564
#               (-0,0467, quase um quarto do preto) e reaparece espalhado
#               no CMY. Nao e o perfil de cor: o numero e IDENTICO com
#               UseColorProfile ligado e desligado. E a rasterizacao do
#               proprio Corel, naquele arquivo;
#
#            2. a leitura da marca de corte MUDA - pe 7,50 desaparece e
#               topo vai de 37,78 para 4,87. E a pinca da PRIME sai da
#               marca de corte. Chapa pincada pelo numero errado e
#               tiragem perdida.
#
#            A conferencia de cor barraria esses arquivos sozinha, e o
#            resultado seria a PRIME parando toda hora em pendencia. Pior
#            que nao ligar.
#
# Na VOPRIX os dois conferem, e o desvio ate DIMINUIU ao poupar as
# marcas - no Stopper_CE, de +0,0172 para +0,0097 na tinta mais afetada.
# E a marca de corte atravessa intacta: pe 29,9327 antes, 29,9327 depois.
CLIENTES_QUE_ACHATAM_NO_COREL = ("VOPRIX",)

CLIENTES_QUE_MANDAM_ARTE_POR_MONTAR = ("FIALHO",)

# E onde a arte JA MONTADA dele espera.
#
# "quando o arquivo vier pelo whattsapp ja montado, no tamanho das chapas
# dele e pincado, coloca na pasta PARA CTP, e de dentro dessa pasta vc
# envia pro ctp, mais dessa vez, SEM DELETAR o arquivo la de dentro, ja
# que esse arquivo so vai ter uma copia."
#
# O vigia ja varre as subpastas da pasta do dia, entao o que cai aqui e
# fechado sem nada de novo no caminho - e o fluxo comum nunca apaga a
# entrada, que e justamente o que ele pediu. A pasta e criada sozinha
# para que haja onde soltar o arquivo, e serve de combinado entre quem
# baixa e quem fecha: aqui dentro e o que ja esta pronto.
#
# NAO E A 'PARA CTP' DA AMERICA, que e outra coisa: la o arquivo e
# APAGADO depois de gravado, porque a copia da casa fica na pasta do dia.
# Aqui nao ha segunda copia.
CLIENTES_COM_PORTAO_QUE_NAO_APAGA = ("FIALHO",)
SUBPASTA_PARA_CTP = "PARA CTP"

# E O PORTAO DO OUTRO LADO, o da AMERICA: o que ainda FALTA montar.
#
# Os dois portoes moram na mesma pasta do dia e tem sentidos opostos. Na
# 'PARA CTP' esta o que uma pessoa ja revisou e vai virar chapa; na 'PARA
# MONTAR' esta o que chegou por montar e ninguem montou ainda.
#
# Por que ele existe: a pasta do dia da AMERICA acumula tres coisas - o
# que chegou por montar, a montagem gravada e as copias que sobem da
# 'PARA CTP'. Com uma pessoa so isso dava, porque ela sabia de cabeca
# qual era qual; com a equipe inteira mexendo, vira "qual desses e o que
# falta?". O portao se le sozinho: o que esta nele e o que falta.
#
# O nome mora aqui, e nao no modulo, pelo mesmo motivo do BASE_AMERICA:
# nome de pasta de cliente e ajuste da casa, e a tela e o vigia tem de
# ler o MESMO.
SUBPASTA_PARA_MONTAR = "PARA MONTAR"

# ----------------------------------------------------------------------
# O SERVIDOR DA MONTAGEM
# ----------------------------------------------------------------------
# A fila da montagem abre no navegador, e a equipe a abre DO PC DELA.
# Essa e a parte que tira a dependencia de verdade: enquanto a tela morar
# na maquina da FIA, quem quiser montar tem de disputar aquela cadeira.
#
# ENDERECO 0.0.0.0 e a decisao, e ela e deliberada: significa 'atenda
# tambem quem vier pela rede', e nao so o proprio computador. Em
# 127.0.0.1 a pagina abriria so na maquina da FIA - que e exatamente o
# problema que este sistema existe para resolver.
#
# SEM SENHA, escolha do operador: "senha em grafica vira papelzinho no
# monitor". Quem decidiu fica gravado pelo NOME que a pessoa digita, e e
# isso que responde de quem foi a decisao. A rede e interna.
#
# A PORTA nao e porta de coisa conhecida - nao e 80, 8080 nem 3050 (que e
# o Firebird do GEREMPRE) - para nao disputar lugar com nada que ja roda
# nesta maquina.
ENDERECO_DA_MONTAGEM = "0.0.0.0"
PORTA_DA_MONTAGEM = 8787

# Quem pode ter o PRETO COMPOSTO juntado numa chapa so.
#
# Preto PURO - arte inteira no canal do K - nao consulta esta lista: vale
# para todo cliente, porque e um fato do arquivo. "todos os arquivos que
# vierem somente no canal do preto faca assim, de todos os clientes",
# 14/09/2026.
#
# O COMPOSTO e outra coisa: o arquivo tem C, M, Y e K escritos dentro
# dele e somos nos que decidimos, pela cobertura, que aquilo era para ser
# uma chapa so. Errar ali funde quatro chapas numa, entao anda por
# cliente conhecido. A FIALHO esta fora - ela manda quadricromia de
# verdade, e as capas de agenda de 14/09/2026 medem C 0,42 M 0,35
# Y 0,42 K 0,41: nada perto de preto.
#
# A PRIME entrou em 16/09/2026, a pedido do operador: "voce mandou alguns
# pretos em 4 cores, mas tem que ser so preto, como e a regra da voprix".
# O caso foi o 'PREF INHUMAS - FICHA REFERENCIA', e a medicao mostra que
# nao era marca de registro - era arte mesmo:
#
#   Black    16.979 px   x  41..469 mm   y 63..372    a arte inteira
#   Cyan      4.800 px   x 261..459 mm   y 80..364  ┐ identicas, no mesmo
#   Magenta   4.800 px   x 261..459 mm   y 80..364  ├ lugar: preto
#   Yellow    4.800 px   x 261..459 mm   y 80..364  ┘ composto na metade
#                                                     direita da montagem
#
# Contagem igual e caixa igual nas tres e a assinatura do composto. Uma
# das duas pecas da montagem vinha em K puro e a outra em CMYK.
CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO = ("SOLIDA", "VOPRIX", "EMPORIO",
                                      "VIVA", "CREATIVE", "PRIME")

PDF_CORELDRAW = {
    # O PRETO TEM DE SOBREPOR. Regra do operador, 18/09/2026: "sempre o
    # preto fique sobreposto, quando ele for 100% nao pode vazar nas
    # outras cores".
    #
    # Sem isto o preto RECORTA o que esta embaixo: abre um buraco com o
    # formato exato da letra nas outras tres chapas, e qualquer desvio de
    # registro vira um fio branco em volta do texto. Nada da erro em
    # lugar nenhum - so aparece na tiragem.
    #
    # Medido no 'Timbrado Traumat' do dia, um texto preto sobre azul
    # chapado (C 171, Y 48 de 255):
    #
    #     sem Overprints   dentro do preto C=0 M=0 Y=0, e o anel em volta
    #                      com 100% de cor -> buraco perfeito no azul
    #
    # ISTO SOZINHO NAO RESOLVE, e saber por que poupa a proxima tarde.
    # 'Overprints' PRESERVA a sobreposicao que os objetos do .cdr ja
    # tem; nao cria nenhuma. Ligado, o PDF do Timbrado saiu IDENTICO, e
    # marcar Shape.OverprintFill nos objetos tambem nao adiantou: o
    # PublishToPDF do Corel 27 nao exporta aquilo.
    #
    # Fica ligado porque e o certo para quem CHEGA com sobreposicao
    # marcada pelo designer - ai ha o que preservar. Quem cria a do
    # preto cheio e sobreposicao.py, no PDF.
    "Overprints": True,
    # 'acima de 95%' e o que o Corel desta casa ja usava, e e o corte que
    # sobreposicao.py le. O operador falou em 100%; 95 pega o 100 e mais
    # a franja de antisserrilhamento, que e o que se quer.
    "OverprintBlackLimit": 95,
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

# ----------------------------------------------------------------------
# SETIMO CLIENTE: PRIME (Prime Graf)
# ----------------------------------------------------------------------
# Arvore MES\DIA como todos, arquivo em .cdr como a VOPRIX, e montagem
# na chapa com PINCA como a CREATIVE - as duas coisas juntas pela
# primeira vez.
#
# TUDO ABAIXO FOI MEDIDO nos arquivos de 14/09/2026, e nao combinado de
# cabeca. O 'POLIPECAS - ETQIEUTAS' existe em duas versoes na pasta: a
# copia de seguranca do Corel, de antes do operador trabalhar, e o
# arquivo salvo depois. As duas juntas mostram o servico inteiro:
#
#   COMO CHEGA    pagina 330 x 320 mm, arte de 317,3 x 299,6 mm,
#                 marca de corte a 17,5 mm do pe da pagina
#   COMO SAI      pagina 510 x 400 (a chapa), a MESMA arte de
#                 317,3 x 299,6 - nada redimensionado -, 96,4 mm de
#                 cada lado e a MARCA a 28,0 mm do pe da chapa
#
# Aplicando a conta que a CREATIVE ja usa: esquerda (510-330)/2 = 90,0 e
# base = 28 - 17,5 = 10,5. Isso poe a tinta a 96,3 mm da esquerda e a
# 73,6 mm do topo; medido no arquivo do operador: 96,4 e 73,3. A
# diferenca e de 0,3 mm.
BASE_ENTRADA_PRIME = r"X:\PRIME"

# A AMERICA tem pasta, mas NAO tem BASE_ENTRADA_ no nome, de proposito: o
# vigia monta a lista dele com os BASE_ENTRADA_* nomeados um a um, e a
# AMERICA nao e varrida. O arquivo dela chega POR MONTAR e so entra no
# fluxo quando o operador o move para a 'PARA CTP'.
#
# Ate 16/09/2026 este caminho estava FIXO dentro do america.py, e por
# isso escapou da troca de letra mapeada por caminho de rede (armadilha
# 27 da skill gerempre): numa sessao de administrador o V: nao existe, e
# so a AMERICA teria quebrado, calada. Caminho de cliente mora no
# config, como os outros seis.
BASE_AMERICA = r"X:\AMERICA"

# 2,8 cm, ditado pelo operador e conferido acima: a marca de corte fica
# a 28,0 mm do pe da chapa.
PINCA_PRIME_MM = 28

# DUAS MARCAS: VALE A DE CIMA.
#
# "pode acontecer de vir com duas marcas, voce sempre deve pincar a
# partir do de cima" - o operador. O 'O.S 1034 - WAN SEMANA DO CLIENTE'
# de 14/09/2026 e esse caso, e esta escrito no arquivo:
#
#     y = 8,00 mm do pe    esquerda e direita, 4,02 mm   <- a sangria
#     y = 9,96 mm do pe    esquerda e direita, 4,02 mm   <- o CORTE
#
# Nao ha regra nova a escrever: marcas.py ja devolve a mais de DENTRO
# (max das que aparecem nos dois lados), que e justamente a de cima.
# Conferido nesse arquivo - devolve 9,9.

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

# A PRIME e o mesmo caso da CREATIVE - arte menor, montada na chapa com
# pinca -, e so uma chapa. Ver PINCA_PRIME_MM.
FORMATOS_PRIME = {
    (510, 400): (1000, ""),
}

# QUAIS CLIENTES TRAZEM O NUMERO DA OS NO NOME DO ARQUIVO
#
# So dois: a SOLIDA ('49713 - Lucas Calil - panfleto') e o EMPORIO
# ('02047 - CHAPAS - PANFLETOS 3 MODELOS'). Nos outros o nome nao carrega
# OS nenhuma - o VOPRIX traz o formato, o FIALHO o resumo da arte, a VIVA
# o numero da grade.
#
# Isto existe por causa de 14/09/2026. A regra "dois arquivos com a MESMA
# OS param e viram pendencia" procurava o numero em QUALQUER nome, e
# 'extrair_oss' casa \d{4,8} no comeco. Dois arquivos do FIALHO -
# 'AGENDA_CADERNO 2027_ CREDI COMIGO' e 'CAPA CADERNO _2027_ TOCANTINS' -
# foram dados como da mesma OS por causa do 2027, que e o ANO da agenda.
#
# O operador desfez: "sao dois arquivos diferentes, cada arquivo com sua
# OS diferente, separados". E de fato: no FIALHO a OS nem vem no nome, e
# procurar numero ali e procurar o que nunca esteve.
#
# Cliente entra nesta lista quando a casa mudar a convencao dele, e nao
# antes: incluir por engano faz voltar o falso positivo; excluir por
# engano deixa passar dois servicos da mesma OS, que e o dobro do valor.
CLIENTES_COM_OS_NO_NOME = ("SOLIDA", "EMPORIO")

TOLERANCIA_MM = 3

# ATE ONDE A DIFERENCA E SO ARREDONDAMENTO DE PDF.
#
# Acima disso a arte NAO tem a medida da chapa, e entra centralizada na
# chapa cadastrada em vez de virar uma chapa daquele tamanho torto.
#
# O numero saiu do registro de 162 chapas ja fechadas, em 14/09/2026:
#
#     161 delas desviam 0,0006 mm   - arredondamento, e nada mais
#       1 delas desvia  1,0083 mm   - 509,764 x 398,992, do EMPORIO
#
# Mil e setecentas vezes de distancia entre as duas populacoes. 0,1 mm
# fica no meio, e vale lembrar que a 1000 dpi um pixel tem 0,0254 mm:
# abaixo de 0,1 mm a diferenca nao chega a quatro pixels.
ARREDONDAMENTO_MM = 0.1

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

ROTULOS_PROVA_PRIME = {
    (510, 400): "PRIME F4",
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
# O FIALHO ENTROU EM 14/09/2026, a pedido do operador: "pode quebrar
# essa barreira tb na fialho, como fizemos com a viva".
#
# O caso foi o 'AGENDA_CADERNO 2027_ CREDI COMIGO.pdf', de duas paginas.
# A pagina 2 passou; a 1 parou por uma imagem de 116,7 dpi num pedaco de
# 29 x 239 mm. Sem OS, porque a OS so sai com o arquivo INTEIRO limpo -
# entao meia agenda foi para o CTP e a cobranca nao saiu.
#
# ATENCAO, e isto esta escrito aqui porque nao e igual aos outros dois:
# 116,7 dpi NAO e caso de fronteira. A VIVA entrou por 199,67 - tres
# decimos abaixo do limite, diferenca que ninguem enxerga. Aqui sao 116
# num elemento estreito e alto, feitio de lombada, e nessa resolucao ele
# SAI VISIVELMENTE MOLE na tiragem. Quem olhou a arte foi o operador, e
# a decisao e dele; o aviso continua saindo no log, com o numero.
#
# A PRIME ENTROU EM 18/09/2026, a pedido do operador: "tire essa trava
# da prime de nao lancar a OS com baixa resolucao, e pra lancar do mesmo
# jeito".
#
# Os dois casos que ele tinha na mao, e os dois sao ELEMENTO PEQUENO
# puxando o servico inteiro para baixo:
#
#   O.S 1049 - VIA VERITATIS - FOLDER   199,1 dpi num pedaco de 27 x 27 mm
#   SEDS - LEQUE 2 IMPRESSAO1           148,3 dpi num pedaco de 33 x 33 mm
#
# O primeiro e o caso da VIVA outra vez: 199,1 contra um limite de 200 -
# nove decimos, diferenca que ninguem enxerga e que ninguem deixaria de
# fechar.
#
# O QUE SE PERDE, dito por inteiro: a arte da PRIME chega montada e vai
# para chapa de 1000 dpi, onde imagem mole sai lisinha e so mostra o
# defeito na tiragem, com a chapa ja queimada. Daqui em diante quem olha
# isso e gente. O numero continua saindo no log, com os dpi e o tamanho
# do pedaco - e e por ele que se descobre depois.
#
# E ISSO NAO E SO SOBRE A CHAPA, e por isso ele pediu assim: a OS so sai
# com o arquivo INTEIRO limpo. Parando por resolucao, a chapa gravada e
# a cobranca nao - que foi o que aconteceu com a agenda do FIALHO em
# 14/09. O prejuizo da trava nao era atraso: era servico entregue sem
# faturar.
#
# A LISTA E EXPLICITA, e cliente so entra nela quando o operador disser.
# Ele foi claro em 10/09: "somente nesses, se houver necessidade em
# outros eu te aviso".
CLIENTES_SEM_TRAVA_DE_RESOLUCAO = ("SOLIDA", "VIVA", "FIALHO", "PRIME")

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

# ----------------------------------------------------------------------
# A TELA QUE CHAMA
# ----------------------------------------------------------------------
# Toda pendencia abre uma janela EM TELA CHEIA, na hora, por cima de
# tudo - ver tela.py. Quem esta na maquina de chapa nao ve a janela
# preta do programa nem o _PENDENCIAS.txt.
#
# Desligue aqui se um dia a tela atrapalhar mais do que ajuda; a
# pendencia continua indo para o log e para o arquivo, como sempre foi.
TELA_DE_PENDENCIA = True

# ----------------------------------------------------------------------
# A FOLHA DE ESTOQUE DE CHAPAS
# ----------------------------------------------------------------------
# A chapa e do cliente, e quando ela acaba a gravacao para. A FIA
# mantem uma folha em PDF na PASTA_CONTROLE, um arquivo por cliente,
# reescrito por cima - ver estoque.py.
#
# Por que so a SOLIDA, por enquanto: e dela o movimento diario que
# justifica acompanhar (duas chapas vivas, ~64 saindo por dia util,
# reposicao a cada cinco ou dez dias). Acrescentar outro cliente e
# botar o nome aqui.
CLIENTES_COM_FOLHA_DE_ESTOQUE = ("SOLIDA",)

# De quanto em quanto tempo a FIA PERGUNTA ao GEREMPRE se o movimento
# do cliente mudou.
#
# A pergunta e uma consulta so - COUNT, MAX e SUM da MOV daquele dono,
# 0,14 s - e a folha so e redesenhada quando a resposta muda. Mesmo
# assim ela nao vai no ritmo do laco: a 5 segundos seriam 17 mil
# consultas por dia num Firebird 1.5 de 2004 que os operadores usam o
# dia inteiro. A um minuto, sao 480, e a folha ainda acompanha cada
# lancamento - inclusive os que os operadores fazem no Delphi, que sao
# a maior parte.
ESTOQUE_DE_QUANTO_EM_QUANTO = 60   # segundos

# ----------------------------------------------------------------------
# OS DOIS RELATORIOS QUE VAO PARA O CLIENTE
# ----------------------------------------------------------------------
# Regra do operador, 14/09/2026: "se eu te pedir um relatorio atual,
# voce gera na hora e salva na PASTA DA SOLIDA, com o nome relatorio
# atual e o horario; se eu nao te pedir, segue a rotina: quando der
# meia noite o dia se encerra e voce salva o relatorio dentro da pasta
# do dia com nome RELATORIO CHAPAS SOLIDA (data), assim quando eu
# chegar cedo eu envio manualmente para eles acompanharem".
#
# Sao dois papeis diferentes:
#
#   ATUAL       tirado no meio do dia, a pedido. Vai na RAIZ da pasta
#               do cliente, com data e hora no nome - sem a data, o
#               pedido de amanha escreveria por cima do de hoje;
#   DO DIA      o fechamento, um por dia, dentro da pasta daquele dia.
#               E o que o cliente recebe.
#
# A pasta e a MESMA que o vigia varre. Por isso o nome dos dois comeca
# com 'RELATORIO ': o vigia pula quem comeca assim, senao ele pegaria o
# proprio relatorio como se fosse arte e tentaria gravar chapa dele.
RELATORIO_ATUAL = "RELATORIO ATUAL %s %s.pdf"        # data, hora
RELATORIO_DO_DIA = "RELATORIO CHAPAS %s (%s).pdf"    # cliente, data

# Onde mora a pasta de cada cliente que tem relatorio de estoque.
#
# Guarda o NOME da configuracao, e nao o valor. Escrito
# {"SOLIDA": BASE_ENTRADA}, este dicionario congelaria o 'X:\ENTRADA'
# de fabrica: o config_local so e aplicado no FIM deste arquivo, e a
# esta altura o BASE_ENTRADA ainda e o padrao. O relatorio iria parar
# numa pasta que nao existe, calado.
#
# Foi medido, e nao suposto: a primeira versao desta linha derivava o
# valor e devolvia 'X:\ENTRADA' com o BASE_ENTRADA ja valendo
# 'V:\SOLIDA Grafica'. E a mesma razao do CAIXAS_TEAMS, mais acima.
PASTA_DO_CLIENTE = {"SOLIDA": "BASE_ENTRADA"}

# Quantos dias para tras a FIA procura dia por fechar, ao subir.
#
# O programa nao e servico: ele roda enquanto a janela esta aberta. Se
# a maquina estiver desligada a meia-noite, ninguem fecha o dia - e o
# operador chega cedo e nao acha o relatorio. Entao, ao subir, ela
# olha para tras e fecha o que ficou. Sete dias cobrem um fim de
# semana prolongado.
DIAS_PARA_FECHAR_ATRASADO = 7

# De que dia em diante a FIA fecha o dia. 'AAAA-MM-DD', ou vazio para
# nao ter limite.
#
# Sem isto, a rotina nasceria olhando os sete dias anteriores e
# despejaria de uma vez cinco relatorios retroativos na pasta do
# cliente - papeis que ninguem pediu, com data de uma semana atras, na
# pasta que o cliente abre. A rotina comeca no dia em que foi ligada.
#
# Querendo um dia antigo, e uma linha de comando:
#     python -m finart_ctp.estoque --fechar 11/09
FECHAMENTO_A_PARTIR_DE = "2026-09-14"

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
    # PRIME. O nome no cadastro nao ajuda a achar - esta como
    # 'PRIME (POR DENT. DO ESPORTE EVENT.ESPORTIVOS LTDA' -, e procurar
    # por 'PRIME' tambem traz 'R3 SU-PRIME-NTOS'. O 502 foi confirmado
    # pelas OS: 176 em 2026, entre elas a 19704 de 14/09/2026, com
    # 'VALDINO - CHAPADO' e 'POLIPECAS - ETQIEUTAS'.
    "PRIME": 502,
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
    # PRIME cod 88, R$ 10,00 - lido das OS de 2026: 410 itens a 10,00,
    # 400x510, sem uma excecao. A chapa e do CLIENTE (os 1093
    # lancamentos sao todos com dono 502).
    ("PRIME", (510, 400)): (88, "510X400 - PRIME F4", 10.00, "cliente"),

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

# A PONTE DO TEAMS ESTA LIGADA?
#
# Nao, desde 14/09/2026. Nao por defeito - ela funcionava - e sim porque
# o trabalho dela passou para outro lugar: "tenho um projeto que vai
# pegar do teams e salvar na pasta, e voce vai pegar da pasta e iniciar o
# processo, um nao atropela o outro" - o operador.
#
# A divisao ficou limpa, e vale escrever por que ela e melhor: um
# programa so escreve na pasta do dia e um programa so le. Dois
# baixadores gravando o mesmo arquivo na mesma pasta se atropelam por
# tempo - meio arquivo na pasta, nome igual com conteudo diferente, a
# pendencia de 'versao DIFERENTE' disparando a toa. Com um de cada lado,
# nada disso pode acontecer.
#
# O CODIGO DA PONTE FICA. Ele esta inteiro e testado, e a religacao e
# esta linha - nao ha nada para reescrever se um dia o outro projeto
# sair do ar. CAIXAS_TEAMS continua apontando para a pasta sincronizada,
# no config_local.
PONTE_DO_TEAMS_LIGADA = False

# A PONTE DO TEAMS FALA NO TERMINAL?
#
# Nao. Pedido do operador, 14/09/2026: "quando a solida mandar algo no
# canal do teams, nao precisa avisar no terminal, ja estou com outro
# projeto que esta fazendo a automacao de baixar pra mim".
#
# Cala SO A ROTINA: arquivo que chegou, arquivo que ainda esta na nuvem,
# arquivo que ja estava la igualzinho. Nada disso e decisao de ninguem -
# e so a ponte contando o que fez.
#
# CONTINUA FALANDO o que da errado, e isso nao e teimosia: arquivo que
# NAO atravessou parece, de fora, arquivo que o cliente nao mandou. Se
# emudecesse tambem aqui, um servico poderia ficar parado a tarde
# inteira sem ninguem saber que existia. Continuam ditos:
#
#   - nao consegui trazer (quase sempre OneDrive sem internet);
#   - chegou versao DIFERENTE com nome igual - essa vira pendencia;
#   - o OneDrive nao esta rodando, ou a pasta do time sumiu;
#   - a rajada: quando muita coisa espera junta, a ponte diz o que vai
#     entrar e da alguns segundos de Ctrl+C. Ali nao se trata de avisar
#     que chegou arquivo, e sim de que MUITA OS esta para ser aberta.
TEAMS_FALA_NO_TERMINAL = False

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
# ESTA TABELA TINHA UMA COPIA no painel_imposicao.html, em JavaScript, e
# o comentario aqui dizia "mudou aqui, muda la". Era o preco de a pagina
# nao ter servidor para ler daqui - e e o tipo de combinado que ninguem
# cumpre duas vezes: uma folha escrita em dois lugares e uma medida
# errada esperando a hora.
#
# A COPIA MORREU EM 18/09/2026. O painel e servido pelo servidor da
# montagem, que injeta esta tabela e as chapas (ver montagem.formatos_da_casa
# e chapas_da_casa). Aqui e o unico lugar onde ela existe, e o painel nem
# abre mais sem receber - ele para e diz por onde entrar, em vez de
# trabalhar com tabela de mentira.
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
