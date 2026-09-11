---
name: imposicao
description: Montagem e imposicao de arquivo para a chapa - por mais de uma arte na mesma chapa, marca de corte, sangria, pinca, registro de cores, faca, dobra, caderno, paginacao, cupom, lombada, bate-vira, e a montagem feita no CorelDRAW pelo COM. E o cliente AMERICA, que a FIA monta - a pasta PARA CTP, o painel de ordem de montagem, o _MONTAGEM, as maquinas PM 52, MOZP e SM 74, e o Preps. Use sempre que aparecer montagem, montar, imposicao, impor, n-up, sangria, marca de corte, marca de registro, registro de cor, escala de cor, faca de corte, dobra, caderno, paginacao, encarte, cupom, aproveitamento de chapa, AMERICA, PARA CTP, portao, painel, Preps, ou quando alguem perguntar como varias artes cabem numa chapa so.
---

# Imposição: pôr a arte na chapa

Fechar arquivo é decidir **o que** vira chapa. Impor é decidir **onde**,
dentro dela — quantas artes cabem, em que sentido, com que sobra entre
elas, e onde ficam as marcas que a oficina usa depois.

A skill `fechamento-arquivos-ctp` cobre o caminho de um arquivo até a
chapa. Esta cobre o que acontece **dentro** da chapa. Onde as duas se
tocam — pinça, marca de corte, giro — o texto de verdade está em
`fechamento-arquivos-ctp/references/arte.md`, e aqui só se aponta para
lá: duas cópias envelhecem separadas.

## O princípio

**Montagem errada não dá erro em lugar nenhum.**

É o mesmo princípio da FIA, e aqui ele morde mais fundo. Uma chapa mal
imposta grava limpa, imprime limpa, e o defeito só aparece **depois da
tiragem** — na guilhotina, que corta no lugar errado; na dobra, que não
casa; no acabamento, que descobre que faltou sangria. A essa altura já
foram chapa, papel e máquina.

Daí: **entre errar sozinha e parar para perguntar, pare.** Chutar
distância entre artes, sangria ou posição de marca não é opção.

## O que já é automático, e o que é na mão

| | quem faz | onde está escrito |
|---|---|---|
| **uma arte, centralizada, pinça no pé** | a FIA, só CREATIVE | `arte.md` |
| encaixe por corte, até 15 mm | a FIA, só FIALHO | `arte.md` |
| **mais de uma arte na mesma chapa** | **a FIA, só AMÉRICA** — grade de N peças, bate-vira ou só frente, **revisada por gente** antes do CTP | `references/america.md` · `ferramentas/montar_bate_vira.py` |
| caderno, dobra, paginação | **gente** | ainda não combinado |
| arte fora de qualquer chapa | **gente** | vira pendência |

A lista do que ainda espera gente vive em
`fechamento-arquivos-ctp/references/ainda-na-mao.md`. Quando um caso
daqui for resolvido, a regra vem para cá e sai de lá.

## O que já foi feito de montagem por programa

Um caso, em 10/09/2026: o **`MEGA MOVEIS - CUPOM1.cdr`** — uma montagem
de 12 cupons 6×2 que já vinha pronta no arquivo, e o pedido foi só pô-la
numa página de chapa 510×400 com pinça de 28 mm, **sem converter nada**.

Foi feito pelo **CorelDRAW por COM**, e o que se aprendeu ali está em
`references/corel-com.md`. São armadilhas de ferramenta, não de ofício —
mas cada uma custou uma tentativa, e a primeira delas fez o programa
mentir sobre o tamanho da arte.

O que valeu como regra de ofício, e vale além daquele arquivo:

**A pinça se mede da MARCA DE CORTE, não da borda da arte.** No cupom,
os traços de corte eram o objeto mais baixo do arquivo — 4,3 mm abaixo
do desenho. Medir do desenho poria a arte 4,3 mm fora do lugar. É a
mesma regra que a Creative já ensinou, e ela não muda de arquivo para
arquivo: `arte.md` conta o caso inteiro, com os números.

## Vocabulário desta casa

Escrito para não haver dúvida na hora de programar:

- **pinça** — a faixa que a máquina segura, no pé da chapa. Ali não pode
  haver desenho. É borda física da chapa: a chapa não se vira, quem se
  vira é a arte;
- **marca de corte** — traço curto na margem, que diz onde a guilhotina
  corta. Lida **no vetor**, nunca na imagem rasterizada;
- **chapa** — a placa de metal. Os formatos por cliente estão em
  `fechamento-arquivos-ctp/references/clientes.md`, e o preço por chapa
  no `config.py`.

## O caminho de um arquivo até a montagem

Combinado com o operador em 10/09/2026, no serviço `Flyer Semana do
Cliente_15x21`. **Nesta ordem**, e as três primeiras conferências vêm
antes de qualquer coisa ser gerada:

| | passo | o que decide |
|---|---|---|
| 1 | **preto composto no texto** | texto preto feito das quatro tintas vira **só K** |
| 2 | **sobreposição do preto** | o preto **tem** de estar em sobreposição |
| 3 | **sobreposição das outras cores** | qualquer outra cor sobrepondo **sai** |
| 4 | **converter em imagem** | 900 dpi, para nada dar pau no RIP |
| 5 | **montar** | as peças, o vão, a sangria, as marcas |

**Por que o preto de texto vira só K:** preto feito das quatro tintas
precisa que as quatro casem no registro. Qualquer desvio de meio ponto
aparece como franja colorida na borda da letra — e em corpo pequeno isso
some com a legibilidade. Em uma tinta só não há o que desalinhar.

**Por que o preto tem de sobrepor:** se ele não sobrepõe, ele *recorta*
o fundo — abre um buraco branco com o formato exato da letra nas outras
três chapas. Aí qualquer desvio de registro vira um fio branco em volta
do texto. Sobrepondo, o preto é impresso **por cima** do fundo cheio, e
desvio nenhum abre branco.

**Por que as outras cores não podem sobrepor:** sobreposição só funciona
com tinta escura por cima. Uma cor clara sobrepondo não cobre o que está
embaixo — ela **mistura**, e sai uma terceira cor que ninguém pediu.
Quase sempre é sobra de configuração do arquivo, não intenção.

### Qual resolução usar

Regra do operador, 10/09/2026, em duas metades:

**1. Arquivo todo em imagem mantém o dpi que já tem.** Subir não cria
detalhe nenhum — só peso.

**Todo em imagem quer dizer DENTRO DO CORTE.** É a parte que importa da
regra: quase todo PDF fechado por designer traz as marcas de corte dele
**em vetor, fora do corte** — no flyer 15×21 são traços de 0,25 pt numa
separação chamada `All`. Contar essas marcas faria todo arquivo parecer
"tem vetor", e a regra nunca pegaria. Então a conferência olha só o que
cai dentro da área de corte, e ignora o resto.

Sendo todo imagem, use o **MAIOR** dpi encontrado, não o menor: no flyer
a maioria estava em 288 e algumas peças em 426 — sair em 288 amassaria
essas.

**2. Havendo texto, vetor ou qualquer objeto dentro do corte, o dpi vem
do TAMANHO DA CHAPA:**

| chapa | dpi |
|---|---|
| até o **formato 4** (maior lado ≤ 560 mm) | **900** |
| maior que isso | **800** |

Ali a resolução do arquivo não quer dizer nada, porque texto e vetor não
têm resolução. E chapa grande em 900 dpi dá arquivo enorme sem ninguém
ver diferença — é o mesmo raciocínio que o `config.py` já usava, gravando
a 510×400 em 1000 e a 775×635 em 800.

Os **560 mm** não foram inventados: é a mesma linha que o GEREMPRE usa
para decidir entre `F4` e `F2` na OS. As duas contas da casa concordam.

`ferramentas/montar_bate_vira.py` decide sozinho
(`resolucao_do_arquivo` e `dpi_da_chapa`).

### Converter em imagem — o que se ganha e o que não se ganha

Depois de rasterizado não há fonte que falte, transparência que achate
errado nem vetor que engasgue o RIP: há uma imagem CMYK e mais nada.

**Mas rasterizar não cria resolução.** Arte de 288 dpi virada em 900 dpi
continua com o detalhe de 288 — só ocupa mais espaço. O ganho é de
segurança, não de qualidade, e é por isso que o preflight continua
medindo a resolução do original **antes**.

E rasterize **sem o perfil ICC embutido** (`-dUseFastColor=true`). Com o
perfil, o preto se remistura nas quatro tintas — é a armadilha 1 da
skill de cor, e ela desfaz justamente o passo 1 daqui.

### O caso que fixou o padrão

`Flyer Semana do Cliente_15x21.pdf` — 2 páginas, corte 150 × 210,
**BleedBox com 3 mm exatos de sangria** (o mesmo 3 mm dos 2020 modelos
do Preps).

Os três primeiros passos **não fizeram nada nele, e por bons motivos**:

- **há UM bloco de texto, e ele é azul.** São os nomes das marcas
  (`ANNA HICKMANN`, `CAVALERA`, `CALVIN KLEIN`...), em
  `C 0,929 M 0,741 Y 0 K 0` — sem uma gota de preto. Não há preto de
  texto para converter.

  *(Na primeira passada eu disse que não havia texto nenhum, e estava
  errado: a varredura descia nos XObjects mas esquecia o fluxo da
  PRÓPRIA página, que era justamente onde o texto estava. Ao procurar
  texto num PDF, olhe os dois.)*
- **nada sobrepõe.** Todos os `ExtGState` vêm com `OP=false` e
  `op=false`;
- **os escuros não são preto.** Medidos, os pixels com K acima de 50%
  dão `C 75 M 63 Y 63 K 75` e `C 100 M 88 Y 50 K 75` — é o **azul-marinho
  da marca**, não preto neutro. Forçar K puro ali destruiria o desenho.
  O pouco que é neutro está **dentro das fotos** dos óculos, onde preto
  composto é o certo.

Fica a lição: **medir antes de aplicar a regra.** As três conferências
valem para arquivo com texto vivo; num PDF já achatado em imagem elas
não têm onde pegar, e aplicá-las na marra estragaria a arte.

A montagem que saiu:

```
chapa      525 x 459 (América, PM 52), pinça 60      -> útil 525 x 399
peça       149,96 x 209,98 de corte, deitada 209,98 x 149,96
montagem   424,97 x 304,91 de corte a corte
canto      x 50,02   y 107,04     colunas x: 50,02 e 265,00
vão 5   sangria 3   marca 12 com 3 de folga   900 dpi
```

O 900 dpi saiu **por causa daquele bloco de texto de 5,5 pt** — fosse o
arquivo todo imagem, teria saído em 426. Custou 2,3 MB a mais (6,7 contra
4,4), porque o peso está nas fotos, que já eram 288 nos dois casos.

### O convite que pediu SEIS, e só frente

`#1304-26-CONVITE-MEETING.pdf` — a UP Incorporadora, 11/09/2026. **Uma
página**, corte 100 × 210 exato, BleedBox 106 × 216 (3 mm do designer).
Pedido do operador: *seis imagens, só frente, vão 3, na 525 × 459.*

Foi ele que derrubou duas coisas de uma vez: o painel só oferecia 1, 2,
4, 4×1 e 8, e a `montar()` era **sempre 2×2 e sempre bate-vira** — com
uma página só ela recusava, procurando um verso que não existe.

Das quatro grades que seguram seis peças, **uma só cabe**:

| grade | montagem | |
|---|---|---|
| 1×6 | 210,0 × 615,0 | não cabe, e sai **em pé** |
| **2×3** | **423,0 × 306,0** | **cabe** |
| 3×2 | 636,0 × 203,0 | não cabe na largura |
| 6×1 | 1275,0 × 100,0 | não cabe |

A montagem que saiu:

```
chapa      525 x 459 (América, PM 52), pinça 60      -> útil 525 x 399
peça       100,04 x 210,02 de corte, deitada 210,02 x 100,04
montagem   423,04 x 306,12 de corte a corte
canto      x 50,98   y 60,00
colunas x  50,98 e 264,00      linhas y  60,00 · 163,04 · 266,08
vão 3   sangria 1,50   marca 12 com 1,5 de folga   300 dpi
```

**Três coisas para guardar deste caso:**

**1. A sangria foi RECORTADA, e é a regra funcionando.** O arquivo
chegou com os 3 mm de sempre; com vão 3 a regra pede **1,5**. As quatro
bordas saíram `recortado` — recortar não mexe no desenho, só na caixa.
Fosse o 3 fixo de antes, a linha de corte cairia 1,5 mm fora do lugar em
cada borda, e nada daria erro em lugar nenhum.

**2. Os 300 dpi não são engano, e "formato 4" não os muda.** A chapa
*é* formato 4 — e a regra do dpi pela chapa **só vale quando há texto ou
vetor dentro do corte**. Este convite não tem: **nenhuma fonte
declarada**, nenhum operador `Tj`/`TJ`/`BT` nem na página nem nos
XObjects, e quatro imagens a 300 dpi efetivos. Sendo todo imagem, ele
mantém o dpi que tem. Subir para 900 triplicaria o peso sem criar um
ponto de detalhe.

**3. A pinça foi conferida no pixel, não no relatório.** Rasterizada a
4 px/mm, a tinta da peça começa a **58,50 mm** do pé — mais 1,5 de
sangria dá o primeiro corte em **60,00**, que é a pinça da PM 52. E as
**doze marcas saíram**, inclusive as quatro verticais que descem até
46,5 — dentro da faixa da pinça, como o operador exigiu em 10/09.

### Onde a montagem se assenta

**Na largura, centrada — por exigência do vira**, não por gosto: o eixo
do giro é a linha vertical do meio, e ela tem de cair no meio da folha.

**Na altura, a borda de baixo do PDF é a borda da PINÇA, e a pinça se
mede até a MARCA DE CORTE.** Ou seja: a primeira linha de corte da
montagem cai exatamente na medida da pinça — 60 mm na PM 52. Não é a
borda da sangria nem o começo da tinta; é o corte.

É a mesma lição que a CREATIVE já tinha ensinado e que custou uma chapa
12 mm fora do lugar: **pinça não se mede da borda do arquivo.**

**As marcas de baixo SAEM, mesmo caindo na faixa da pinça.** Eu tinha
feito o contrário — recusava-as, por achar que ali nada imprime — e o
operador corrigiu: *"percebi que na parte de baixo da montagem a cruz de
corte na vertical não saiu, elas têm que sair, mas a pinça é realmente
calculada pela horizontal"*.

As duas coisas convivem: a **medida** da pinça continua sendo até a linha
de corte **horizontal** de baixo, e as marcas **verticais** que descem
dali são desenhadas do mesmo jeito. Quem grava a chapa grava a faixa
inteira, e o cortador precisa da marca nas duas pontas da linha. O único
motivo para recusar uma marca é ela cair **fora da chapa**.

### Registro e escala ficam encostados na arte

**1 mm depois de a sangria acabar** — não depois das marcas de corte.
Pedido do operador: *"pode começar logo após a sangria da imagem acabar,
pode colocar 1 mm separado, quase encostado mesmo"*. Quanto mais perto da
arte, menos papel a folha precisa ter de sobra em volta.

| | onde |
|---|---|
| **marca de registro** | **em pé, nos DOIS lados**, centrada na altura, **1 mm** depois da sangria |
| **escala de cor** | **de pé, na lateral esquerda, em cima**, **3 mm** depois da sangria |

A marca de registro usa o `Registro 90°.eps` (em pé, 6,35 × 18,70 mm).
**Dois lados importam**: com um só dá para ver desencontro de tinta, mas
não dá para ver **esquadro** — folha entrando torta desloca um lado para
um jeito e o outro para o contrário, e isso só aparece comparando as
duas pontas.

A escala de cor é a `cores finart.eps` (35,63 × 4,94 mm), **girada 90°**
e pendurada a partir do alto da montagem. Antes ficava deitada *acima*
da montagem, e ali comia altura de chapa que a arte pode querer.

**Cuidado com o nome das duas coisas.** O operador chama a escala de
cores de *"registro de cores"*, e eu troquei uma pela outra: mexi na
marca de registro quando o pedido era da escala. Ele desfez —
*"a marca de registro está perfeito do jeito que tinha colocado a vez
anterior... altere a de cores"*. **Marca de registro** é a cruz que casa
as chapas; **escala de cor** é a tira com o logo e os quadrados de C, M,
Y e K. Na dúvida, pergunte qual das duas.

O `Registro 90°.eps` da casa mede **6,35 × 18,70 mm** — estreito e alto,
que é o feitio certo para borda vertical. A `cores finart.eps` mede
**35,63 × 4,94 mm**.

A ferramenta é `ferramentas/montar_bate_vira.py`.

## O painel de ordem de montagem

`ferramentas/painel_imposicao.html`, feito em 10/09/2026 a pedido do
operador, para ele passar os parâmetros sem digitar. A ideia que o
sustenta: **o formulário é a chapa.** Cada escolha — cliente, chapa,
peça, sangria, vão, **quantidade**, tipo, cores, marcas — redesenha um diagrama
em escala, com a pinça hachurada no pé, as peças já giradas para o
bate-vira, as marcas em cor de registro, o registro nos dois lados e a
escala de pé na lateral, mais o veredito de cabe/não cabe com os
números. É a conferência que eu faço à mão, na tela dele, antes de
existir arquivo. A conta bate com a montagem real (425,00 × 305,00 contra
424,97 × 304,91 — a diferença é o corte do arquivo ser 149,96, não 150).

O que ele **não** faz, e por quê:

- **não me chama sozinho.** É página local; o botão gera a ordem em texto
  para o operador copiar e mandar. Disparar direto precisaria de um
  programa escutando, e isso é outra conversa;
- **não move arquivo.** A montagem sai na **pasta do dia** com
  `_MONTAGEM`; quem a põe na `PARA CTP` é o operador, depois de revisar.
  Isso é **trava em `montar()`**, não promessa: escrever no portão pularia
  a revisão, e a mudança de pasta *é* o "aprovado";
- **não usa abas**, embora o operador tenha pedido abas. Aba esconde, e
  aqui toda escolha muda o desenho — esconder faria decidir sem ver a
  consequência. Ficaram blocos que cascateiam. Ele aceitou; se quiser
  aba mesmo, é rápido.

Os números do painel (chapas, pinças, marcas) são os mesmos do
`config.py`. Mudou lá, muda aqui — são duas cópias, e é o preço de ser
uma página sem servidor.

### TUDO É DIGITADO, e o painel só avisa

Duas conversas com o operador, no mesmo dia 11/09/2026, e a segunda
desfez metade do que a primeira tinha feito — o que é sinal de que a
primeira estava mandando demais.

**A primeira:** *"preciso que deixe o campo editável com a quantidade de
imposição que eu quero colocar"*. Até ali o arranjo eram **cinco botões
fixos** — 1, 2, 4, 4×1 e 8 — e o número que derrubou a lista foi o
**6**: o convite 100 × 210 da UP Incorporadora, só frente, na 525 × 459.
Não havia onde pedir seis.

**A segunda:** *"deixa editável o número de imagens pra colocar frente e
o número verso, a montagem deixa editável também... então a montagem é
livre, me avise somente se não couber dentro do formato, área útil"*.

O que ficou:

| campo | |
|---|---|
| **imagens frente** e **imagens verso** | dois números, separados. No bate-vira eles somam — as duas metades dividem a mesma chapa; em frente e verso são duas chapas, cada uma com a sua conta |
| **colunas × linhas** | a montagem, digitada. O painel **não a corrige** |
| **formato** | o segundo limite, e ele é outro — ver abaixo |

**O painel deixou de escolher.** Ele lê, desenha e avisa. As grades
continuam aparecendo, agora como **sugestão num clique**, ordenadas
pela que cabe, sai deitada e não deixa célula vazia — mas nenhuma é
imposta, e a que não cabe sai **riscada** com o motivo.

**O que ele avisa, e o que trava.** Só dois avisos trancam o botão, e
mesmo esses só até o operador responder:

- **não cabe na área útil** — a chapa menos a pinça;
- **não cabe no formato** — a folha que entra na máquina.

Aparece um **"Dar andamento assim mesmo"** junto do aviso; marcado, o
botão destranca e a ordem sai com `ATENÇÃO: esta montagem NÃO CABE (...)
e foi liberada à mão` escrito nela — quem receber o papel precisa saber
que foi decisão de alguém, e não descuido de ninguém. **A marca cai a
cada mudança:** um "pode ir" dado para uma montagem não vale para a
seguinte.

O resto é recado, e não tranca nada: célula vazia (desenhada
**tracejada**, no canto longe da pinça), imagem que não entra na grade,
colunas ímpares num bate-vira.

E o que os números **arrastam junto**: a sangria. Ela é metade do vão, e
o "peça sozinha, 2,5" só vale com **uma** célula — mudar a grade muda a
sangria, não só o desenho.

### Os dois limites são DIFERENTES, e é fácil confundir

**Área útil** é da **chapa**: o que a gravadora alcança, o que sobra
tirada a pinça. **Formato** é da **folha**: o que a impressora pega.

Uma montagem pode caber numa e não na outra, e por isso o aviso diz
**qual dos dois** estourou. Medido: 425 × 100 numa PM 52 cabe folgado na
área útil (525 × 399) e **não cabe no formato 32**, cuja área útil é
105 × 150.

### A tabela de formatos

Passada pelo operador em 11/09/2026, em centímetro, e guardada em
**milímetro** — que é a unidade de todo o resto. Vive em
`config.py` (`FORMATOS_DA_CASA`, com `cabe_no_formato()`) e tem uma
cópia em JavaScript no painel, que não tem servidor para ler de lá.

Cada formato tem **área total** (a folha) e **área útil** (o que
imprime). **Quem manda na conferência é a útil** — a folha inteira não
imprime.

**Um número pode ter mais de uma folha, e não é erro de digitação.** O
**F-04 é 33×48 OU 24×66**; o **F-06 tem três**. São maneiras diferentes
de cortar a folha grande, todas chamadas pelo mesmo número. Por isso
cada entrada é uma **lista**, e o painel **pergunta qual** quando há mais
de uma — em vez de pegar a primeira.

**A folha entra nos dois sentidos.** A tabela escreve largura × altura,
mas 33×48 é a mesma folha virada, e a montagem sai sempre deitada.
Conferir num sentido só acusaria "não cabe" no que cabe: o convite dá
423 × 306 e o útil do F-04 é 315 × 460 — **só serve virado**. Se a casa
exigir um sentido só (por causa da pinça, ou da fibra do papel), isso
muda, e é uma linha.

**Por que a tabela não saiu do GEREMPRE**, embora ele tenha o campo: fui
procurar lá primeiro, e o `OSMON` é **texto livre** — `F4`, `FT 4`,
`FT4`, `F4 GER`, `F4 IRREG`, cinquenta e tantas grafias —, e o
`OSLAR/OSALT` ao lado dele ora está em milímetro, ora em centímetro, e
ora é a medida da **chapa** em vez da folha: nas OS recentes o F4 mais
repetido é `400×510`, que é chapa. Uma tabela tirada dali sairia errada e
ninguém veria.

### Provar o painel sem runtime de JavaScript

Esta máquina não tem node. Balanço de chaves e "a página abre" não
provam regra nenhuma, e eu estava fazendo mudança grande no escuro.

O que funciona: **uma cópia da página com um script a mais no fim**, que
preenche os campos, chama o laço e escreve no DOM o que o painel
respondeu — e o **Edge sem tela** (`--headless=new --dump-dom`) devolve
o resultado. A cópia sai do arquivo de verdade, lido na hora: se o
painel mudar e a regra quebrar, isso quebra junto.

Oito casos passam por lá — o convite, o bate-vira de sempre, os dois
limites estourando um de cada vez, colunas ímpares, imagem sobrando,
peça sozinha, e o formato de três folhas. Foi assim que apareceram
`4 imagemns`, `1 imagem em 1 células` e o `3 imagens em 6 células` que
não dizia **por chapa** — três defeitos de texto que o balanço de chaves
nunca acharia.

## Sangria inventada, quando a arte chega pelada

Respondido em 11/09/2026, com gabarito medido. `ferramentas/sangrar.py`.

**A regra que quase todo mundo quebra: sangria não é ampliar a arte.**
Esticar 150×210 até 156×216 faz tudo crescer 4% — o texto, a
logomarca, o corte. O impresso deixa de ter o tamanho que foi pedido.
Sangria se **acrescenta por fora**; o corte continua do tamanho que era,
e o que cresceu é só o que a guilhotina come.

Dá para inventar ou não **depende do que há na borda**, e cada uma das
quatro bordas se decide sozinha — uma arte pode ter as quatro
diferentes:

| na borda | o que se faz | vale? |
|---|---|---|
| acaba em branco | enche de branco | nada a inventar, o papel já é branco |
| cor chapada | estende a cor | **exato** — ninguém distingue do original |
| foto, textura que continua | espelha a faixa para fora | é chute, mas plausível: a continuação de uma textura é mais textura |
| um fio, moldura ou letra **parada** na linha de corte | **para e chama gente** | espelhar duplicaria o traço, e a duplicata sai no impresso |

O último caso é o que importa: **não invento traço.** Ou volta para o
designer, ou alguém decide na mão.

### Como se mediu — e qual é a medida certa

O gabarito foi o `Flyer Semana do Cliente_15x21`, que tem 3 mm de
sangria feita por gente (trim 149,94×209,97, bleed 155,94×215,97).
Rasterizei no BleedBox, **joguei a sangria do designer fora** — isso
fabrica exatamente o arquivo "chegou pelado", e alinhado ao pixel — e
mandei reinventar.

**Comparar a cor com a do designer engana.** Na borda direita do verso
deu 9,7 de erro médio, e eu quase tomei por defeito: o designer tinha
desenhado na sangria um verde que **nem existe dentro do corte**. Ou
seja, a divergência inteira estava em tinta que a guilhotina come.

A medida que vale é outra, porque é o defeito que **aparece**: a
guilhotina entrar 1 mm torta e encontrar **papel** em vez de tinta.
Então a pergunta é *onde o designer pôs tinta na sangria, a FIA pôs
tinta também?* — **fiapo branco em 0,000% das oito bordas** das duas
páginas. E o detector pegou moldura de 2 mm **e** fio de 0,5 mm nas
quatro bordas, sem disparar à toa numa foto em degradê.

Isso está preso em `tests/test_sangrar.py`. A arte de cliente não vai
para o git, então os casos sintéticos guardam as regras e o teste do
flyer pula quando o arquivo não está na máquina.

### A saída NUNCA rasteriza — e foi aí que eu errei primeiro

A primeira versão pintava pixel: rasterizava, espelhava a faixa e
gravava um PDF de imagem RGB. Funcionava e estava errada, e o operador
viu na hora: **"nunca pode ser rgb pra saida"**.

O motivo é o mesmo que mata o vetor. Um PDF do designer está em CMYK —
cada objeto diz quanto tem de ciano, magenta, amarelo e preto, e é isso
que vira as quatro chapas. Rasterizar joga tudo para RGB, que é tela e
não papel; para voltar a CMYK alguém tem de **re-separar**, sem saber o
que era antes. Um preto que era só **K** vira as quatro tintas, e o
texto preto sai com quatro chapas empilhadas — qualquer desregistro
borra. Um Pantone vira a mistura mais parecida. Ou seja: resolvia a
sangria e estragava a cor. Pelo mesmo caminho o vetor deixa de ter
contorno e passa a ter pixel.

**A sangria é feita de transformação, não de pixel.** A própria página
é colocada NOVE vezes na página nova — o miolo, quatro espelhos nas
bordas e quatro nos cantos. Um espelho é só uma matriz com **-1 na
diagonal**, com a dobradiça caindo exatamente na linha de corte; por
isso a tinta encosta na linha sem degrau e sem folga. Antes de copiar,
a página é **recortada no próprio corte**, para que sobra de sangria
parcial ou marca esquecida não entre de carona.

Assim vetor continua vetor, CMYK continua CMYK, Pantone continua
Pantone, e imagem continua na resolução que tinha. **Serve igual para
arte vetorial e para arte que é uma foto só** — é a mesma
transformação, porque ela não olha o que há dentro da página.

O rasterizador continua no arquivo, mas só para **olhar**: é pela
imagem que se decide o que há em cada borda. Olhar em RGB não custa
nada — a decisão sai a mesma, e o arquivo que sai não passou por lá.

Medido: CMYK 25 operadores na entrada, 225 na saída (25 × 9
colocações), **RGB zero**; as imagens continuam imagens, o miolo sai com
erro 0,000 de 255, e o TrimBox fica a 3,00 mm de cada borda.

### Sangria de papel não se desenha

Quando as quatro bordas acabam em branco **e** nada é pintado fora do
corte, não há o que espelhar: só se abre a caixa em volta do desenho,
sem tocar no conteúdo.

Isso não é economia, é conserto. O cupom da MEGA MÓVEIS tem 23 MB de
desenho comprimidos em 6,98 MB. Reescrever a página para colar branco
em volta regravava o stream **cru**: o arquivo ia de 8,7 para **23,9 MB**
em 36 segundos, para não mudar um pixel. Com o atalho: 8,75 MB em 2,9 s.
No caminho dos espelhos, que reescreve mesmo, o conteúdo é comprimido
de volta.

### Quem chama: a montagem, sozinha

Respondido em 11/09/2026 — *"preciso que ela sangre sozinha, e eu vou
conferindo"*. `montar_bate_vira._garantir_sangria()` roda **antes de
qualquer medida**.

O buraco que isso fecha já existia e era silencioso. A montagem faz
`corte_l = sang_l - 2 * SANGRIA`, supondo que a peça **já** vem
sangrada. Numa arte pelada essa conta marca a linha de corte **3 mm
dentro do desenho**: as marcas saem no lugar errado e o cliente recebe
o impresso com a borda comida. Nada dava erro em lugar nenhum.

A prova: o flyer 15×21 **pelado**, montado do zero, sai em
**424,97 × 304,91 mm, margem 50,02, primeiro corte em 60** — os mesmos
números, ao centésimo, da montagem feita com o arquivo do designer já
sangrado, e os mesmos da chapa que rodou em 10/09. Erro médio entre as
duas chapas inteiras: **0,041 de 255**.

Quem já vem sangrado não é tocado — sangrar duas vezes engordaria a
peça em 6 mm e erraria o corte do mesmo jeito, para o outro lado.

**Quando uma borda pede olho, ela NÃO para.** A sangria sai espelhada e
o aviso sobe no relatório da montagem, dizendo qual página e qual
borda. É o certo aqui porque **o olho humano já é obrigatório nesta
estrada**: a montagem nunca vai sozinha para a `PARA CTP` — há uma
trava no código — e só o operador a move, depois de revisar. Não
faltava o olho; faltava ele saber **onde** olhar.

## A REGRA DA SANGRIA

Estabelecida pelo operador em 11/09/2026, e e uma regra, nao um numero:

> *"a sangria nao precisa ser 3mm, ela pode ficar estabelecida metade do
> vao que estiver no meio - se o vao for 5mm ela fica 2,5mm, se o vao no
> meio for 3mm ela fica 1,5mm; e se a montagem for somente com 1 imagem,
> ela fica com sangria para todos os lados de 2,5mm como padrao."*

| situacao | sangria |
|---|---|
| vao 5 mm | **2,5 mm** |
| vao 3 mm | **1,5 mm** |
| vao 8 mm | **4 mm** |
| uma peca sozinha | **2,5 mm** (o padrao da casa) |

**Por que metade.** A guilhotina corta **duas vezes** no vao — uma na
borda de cada peca — e a tira do meio e refugo. Cada peca sangra para
dentro desse refugo, e metade do vao e a **maior sangria que cabe sem
uma peca invadir a metade da outra**: as duas se encontram no meio da
tira e param ali.

**Cuidado com a explicacao facil, que eu escrevi errado antes de medir.**
Cheguei a registrar que os 3 mm fixos num vao de 5 punham *"tinta da
outra peca"* na sangria da vizinha. Nao punham: a sobreposicao de 1 mm
caia inteira no refugo, entre as duas linhas de corte, e nunca chegava
ao impresso. O 3 fixo **nao estragava nada**. O que a regra da e outra
coisa — cada peca passa a ser dona exata da sua metade, e a sangria
deixa de ser um numero solto para virar **consequencia do vao**: se o
vao muda, ela muda junto, sem ninguem ter de lembrar.

Quem provou que eu estava errado foi a medicao: varri o vao da montagem
e contei branco. Com 2,5 aparecem 2 px brancos (0,25 mm) no centro
exato da tira — refugo, que vai fora. Com 3, nenhum, porque as duas
sangrias se cobriam. Nao era defeito; era desperdicio.

**A conta mora em um lugar so**, `sangrar.regra_da_sangria(vao, pecas)`,
e o painel tem a mesma em JavaScript, com um comentario dizendo que as
duas andam juntas.

**A folga da marca acompanha a sangria.** A marca de corte comeca onde a
tinta acaba. Nos 2020 modelos do Preps as duas eram 3 — sao o mesmo
numero, e continuam sendo: quando a sangria muda, a folga muda junto.

### O que a montagem faz com o arquivo que chega

`montar_bate_vira._ajustar_sangria()` poe a peca **exatamente** na
medida da regra, venha ela como vier. Tres casos, e nenhum para o
servico:

| como chegou | o que faco |
|---|---|
| **pelada** | invento a sangria inteira, espelhando |
| **com menos** | invento **so o que falta**, a partir da borda da sangria que ela ja tem — o desenho do designer fica |
| **com mais** | **recorto**, e recortar nao mexe no desenho, so na caixa |

O terceiro e o comum hoje: os arquivos chegam com 3 mm e a regra, com
vao 5, pede 2,5.

Isso tambem **resolveu** frente e verso com sangrias diferentes, que eu
antes parava. Parar era fraqueza minha: os dois cortam na mesma grade,
entao basta levar os dois a mesma medida — um e recortado, o outro
ganha o que falta, e a grade serve aos dois.

Medido no flyer: 3,00 → 2,50 recorta e o miolo sai com erro **0,0000**
de 255; 2,00 → 2,50 cria so meio milimetro e os 2 mm do designer
sobrevivem. A montagem com a regra da peça de corte **149,94 × 209,97**
— o TrimBox exato do arquivo, mais preciso que os 149,96 × 209,98 que a
conta do 3 fixo dava.

### A frente e o verso podem vir em DOIS arquivos

Regra do operador, 11/09/2026: *"quando eu colocar dois arquivos lá
provavelmente será frente e verso"*. É como a CARTA de setembro chega —
`CARTA_FRENTE_SETEMBRO_(1)_(2).pdf` e
`CARTA_VERSO_SETEMBRO_opcao_2_(2).pdf`, um arquivo de uma página cada.

Até esse dia a montagem só aceitava **um** arquivo de duas páginas: com
dois arquivos ela lia a página 2 de um arquivo que só tinha uma.

**A ordem manda, e não o nome.** O primeiro é a frente, o segundo é o
verso. Não adivinho pelo nome do arquivo — o `opcao_2` no nome do verso
da CARTA é a prova de que nome de arquivo de cliente não é lugar de
procurar regra. No painel a lista é visível e mexível (↑ e ✕) justamente
por isso.

Provado: os dois arquivos da CARTA, montados na MOZP, dão peça
210,02 × 296,98, montagem 598,95 × 425,04, primeiro corte em 60. A4 em
2×2 dá 599 × 425 — **não cabe na PM 52** (útil 525 × 399), precisa da MOZP
ou da SM 74.

### A sangria é a do ARQUIVO, e mede-se pelo BleedBox

Duas coisas que eu errei no mesmo dia, e as duas eram silenciosas.

**A caixa.** `ja_tem_sangria` media MediaBox contra TrimBox. O
CARTA_FRENTE tem MediaBox 233,28 × 320,28 e corte 210 × 297: por aí
dariam 11,64 mm de sangria. Mas o BleedBox é 216 × 303 — a sangria é
**3 mm**, e os outros 8,64 são a **área das marcas de corte**, que não
sangram nada. O erro pior é o outro sentido: um arquivo **com marcas e
sem sangria** passaria por sangrado, e a montagem cortaria 3 mm dentro
do desenho. E quem rasteriza a peça já usa `-dUseBleedBox`: medir por
outra caixa seria medir uma coisa e cortar outra.

**O valor.** `corte_l = sang_l - 2 * SANGRIA` usava os 3 mm da casa. O
**folder do Sesc chega com 2,5** — corte 400 × 300 dentro de um BleedBox
de 405 × 305. Com 3 fixo a linha de corte sairia em 399 × 299: 1 mm de
erro em cada medida, sem nada dar erro. Agora quem manda é o arquivo;
`SANGRIA = 3.0` continua sendo o padrão da casa, e só vale para a
sangria que a **FIA cria**.

E se a frente e o verso chegarem com sangrias **diferentes**, para: os
dois cortam na mesma grade, e não há escolha que conserte os dois.

### O que ela ainda não faz

- **só a montagem a chama.** O caminho da chapa única (SOLIDA, VOPRIX)
  não passa por aqui, e nem deveria sem decisão: acrescentar 6 mm mudaria
  o tamanho da peça e bateria de frente com as travas de formato;
- **o PDF sangrado não volta para o designer** — ele existe para ser
  montado. Quem quiser devolver tem de olhar as bordas espelhadas
  primeiro;
- **na mão, quando se quiser só a sangria**:
  `python ferramentas/sangrar.py arquivo.pdf [mm]`. Ele se recusa a
  mexer no que já chega sangrado.

## O que eu ainda não sei

Esta seção é o combinado desta skill: **o que estiver aqui, eu não
chuto.** Cada item sai daqui virando regra escrita quando você me
disser, e cada resposta traz um caso de verdade junto.

- ~~quanto de sobra entre uma arte e outra~~ · ~~quanto de sangria~~ ·
  ~~tamanho da marca~~ — **respondidos em 10/09/2026** pelos 2020 modelos
  do Preps desta casa: vão 5 mm, marca de 12 mm. A **sangria deixou de
  ser um número em 11/09/2026** e virou regra — metade do vão, 2,5 na
  peça sozinha — e a folga da marca a acompanha. Ver "A REGRA DA
  SANGRIA" e `references/preps.md`;
- ~~`TR` e `BV`~~ — **respondido**: são a mesma coisa, e o termo da casa
  é **bate-vira**. Como o nome não diz o eixo do giro, quem diz onde a
  pinça fica é o desenho;
- ~~o que fazer quando a arte chega sem sangria~~ — **respondido em
  11/09/2026**: `ferramentas/sangrar.py`, chamado sozinho pela montagem.
  Sem rasterizar, sem sair do CMYK, e avisando quando há fio na linha de
  corte. Ver "Sangria inventada" aqui em cima;
- ~~marca de registro~~ — **respondido em 10/09/2026**: em pé
  (`Registro 90°.eps`), **nos dois lados**, centrada na altura, 1 mm
  depois da sangria. Escala de cor de pé, na lateral esquerda em cima, a
  3 mm. Ver "Registro e escala ficam encostados na arte";
- **como se decide o aproveitamento** — cabem 6 na chapa, mas o cliente
  pediu 5: sobra branco ou muda a montagem? O painel **mostra** a célula
  vazia (tracejada, no canto mais longe da pinça) e diz que a decisão é
  do operador — mostrar não é decidir, e esta continua aberta;
- **frente e verso na ferramenta** — são DUAS chapas, uma por lado. A
  conta é a mesma da grade que já existe; o que falta é o **nome de cada
  arquivo de saída**, que é convenção da casa. A `montar()` recusa em voz
  alta em vez de inventar sufixo.
- **caderno e paginação** — a ordem das páginas na chapa, que depende da
  dobra e do número de folhas;
- **faca de corte** — se vem no arquivo do cliente, em que camada, e se
  entra na chapa ou fica de fora;
- **giro por aproveitamento** — girar uma arte 180° para encaixar mais
  na chapa é comum em algumas casas e proibido em outras (por causa da
  direção da fibra do papel). Aqui, não sei qual é.

## Onde está o resto

| | |
|---|---|
| skill `fechamento-arquivos-ctp` | o caminho do arquivo até a chapa |
| `fechamento-arquivos-ctp/references/arte.md` | **pinça, marca de corte, giro** — o texto de verdade |
| `fechamento-arquivos-ctp/references/clientes.md` | os formatos de chapa de cada cliente |
| `fechamento-arquivos-ctp/references/ainda-na-mao.md` | a lista do que ainda espera gente |
| skill `gerempre` | quantas chapas o serviço gasta, e quanto custa |
| `references/america.md` | **a AMERICA: o cliente que a FIA MONTA, e o portao PARA CTP** |
| `references/chapas-e-pincas.md` | **a chapa e a pinca de 199 graficas - e a regra: pinca e da MAQUINA** |
| `references/preps.md` | o padrao da casa MEDIDO nos 2020 modelos do Preps |
| `references/fundamentos.md` | os estilos de vira, as tres marcas, cor de registro, os softwares |
| `ferramentas/painel_imposicao.html` | **o painel**: o formulário que desenha a chapa e gera a ordem |
| `ferramentas/montar_bate_vira.py` | **a montagem**: a grade de N peças, bate-vira ou só frente, marcas, registro, escala — e a trava do portão |
| `src/finart_ctp/america.py` | **o fechamento depois do portão**: cópia, OS, prova, CTP, apagar — com memória |
| `ferramentas/varredura_preps.py` | le os modelos do Preps, sem escrever nada |
| `ferramentas/ler_chapas_e_pincas.py` | le a lista de chapas e pincas, sem escrever nada |
| `references/corel-com.md` | mexer no CorelDRAW por programa, e as armadilhas |
| `src/finart_ctp/corel.py` | o que já existe de CorelDRAW no programa |

## Como esta skill cresce

Ela nasceu vazia de propósito, em 10/09/2026, a pedido do operador: "tudo
que a gente implementar sobre montagem, marca de corte, sangria,
imposição e registro de cores, você vai alimentando essa skill".

Então: **toda vez que uma regra de montagem for combinada, ela entra
aqui** — com o caso de verdade que a originou, os números medidos, e o
que custou descobrir. Regra sem caso vira lenda; caso sem número não se
programa.
