# O Preps desta casa, e o que os modelos dele contam

O operador usa o **Preps 5.0 da Creo** (`C:\Program Files (x86)\Creo\Preps 5.0`),
à mão, e ali estão **2020 modelos de imposição** — quinze anos de
montagem desta gráfica, feitos por gente, em arquivo.

**Os `.tpl` são PostScript de TEXTO.** Todo o desenho vive em
comentários estruturados, e dá para ler sem abrir o programa:

```
%SSiPressSheet: larg alt ...                        a folha
%SSiPrshPage:   x y larg alt ... sangE sangB sangD sangT   uma peça
%SSiPrshMark:   folga folga comp comp tipo ... C M Y K     uma marca
%SSiSignature:  |nome| ...
```

Tudo em **pontos PostScript** (1 pt = 25,4/72 mm). Confere: 2834,6457 pt
dão 1000,0 mm, e 425,19685 dão 150,0 — a altura da peça no modelo
`100 x 150`, batendo com o nome do arquivo.

A ferramenta que lê isso é `ferramentas/varredura_preps.py`, e ela
**não escreve nada**.

## O padrão da casa, medido

Varridos os 2020 modelos, 18.602 marcas e 18.497 peças em 10/09/2026:

| | valor | quanto manda |
|---|---|---|
| **sangria** | **3 mm** | 93,4% |
| **comprimento da marca de corte** | **12 mm** | 79,0% |
| **folga da marca até o corte** | **3 mm** | 93,7% |
| **vão entre peças, vertical** | **5 mm** | 42,8% |
| vão entre peças, horizontal | 0 mm | 50,1% |

O 0 mm no vão horizontal não é erro: é caderno. Em trabalho costurado as
páginas se encostam, porque ali não há corte — há dobra.

### A regra que amarra as três

```
folga da marca  =  sangria  =  3 mm
```

**A marca de corte começa exatamente onde a sangria acaba.** Não é
coincidência de dois números iguais: é o desenho certo. A marca não pode
cair dentro da sangria, senão some debaixo da tinta que sangra; e não
deve ficar longe dela, senão o cortador perde a referência. Encostar uma
na outra resolve as duas coisas.

Então, sabendo a sangria, a folga da marca vem junto — e vice-versa.

### O que isso confirma, e o que corrige

**Confirma:** os 12 mm de marca que o operador ditou de cabeça são
exatamente o padrão dele, 79% dos casos. O vão de 5 mm também.

**Corrige dois números**, e os dois para mais:

| o que foi dito de cabeça | o que os 2020 modelos dizem |
|---|---|
| sangria 2,5 mm ("metade do vão") | **3 mm** (93,4%; 2,5 mm aparece em 0,5%) |
| folga da marca 2 mm | **3 mm** (93,7%; 2 mm aparece em 4,0%) |

A regra "a sangria é metade do vão" descreve bem o **princípio** — o vão
existe para as duas sangrias se encontrarem. Mas na prática desta casa o
vão é 5 e a sangria é 3, então as duas sangrias **se sobrepõem 1 mm** no
meio do vão, em vez de se encostarem. E isso é normal: sangria é arte
sobrando, e ela é cortada fora de qualquer jeito.

Vale também contra o guia do Buggy (ver `fundamentos.md`), que pede no
mínimo 3 mm: **a casa está no mínimo da literatura, não abaixo dele.**

## Os estilos, pelo nome dos arquivos

| estilo | modelos | |
|---|---|---|
| (sem estilo no nome) | 688 | 34,1% |
| Saddle-Stitched | 479 | 23,7% |
| Flat Work | 440 | 21,8% |
| Perfect Bound | 183 | 9,1% |
| **TIRA E RETIRA** (`TR`) | **167** | 8,3% |
| **BATE-VIRA** (`BV`) | **63** | 3,1% |

**`TR` e `BV` são a MESMA COISA** — o operador confirmou em 10/09/2026:
"tira e retira e bate e vira são a mesma coisa, só questão de
nomenclatura, eu prefiro bate-vira". Os dois nomes convivem nos modelos
porque foram sendo escritos ao longo de anos, e não porque separem
técnicas.

**O termo desta casa é BATE-VIRA.** Use ele.

Os números concordam com o operador. Comparados os dois grupos:

| | BATE-VIRA (63) | TIRA E RETIRA (167) |
|---|---|---|
| peças por modelo | 4 · 8 · 2 | 4 · 8 · 2 |
| sangria | 3 mm | 3 mm |
| folha mais usada | 1000 × 700 | 1000 × 700 |

Mesma forma, mesmo padrão. São dois nomes para o mesmo trabalho.

**Consequência prática, e ela importa:** como o nome não distingue o
eixo do giro, **o nome não diz onde a pinça fica**. Quem diz é o
desenho — por onde a montagem se parte ao meio (ver `fundamentos.md`).
Ao ler um modelo antigo, olhe o arranjo, não o título.

## As folhas mais usadas

| folha | modelos |
|---|---|
| 1000 × 700 | 1801 |
| 965,2 × 635 | 181 |
| 480 × 330 · 330 × 480 | 185 |
| 660 × 480 · 480 × 660 | 95 |
| 460 × 650 · 650 × 460 | 126 |

A folha de 1000 × 700 domina — é máquina grande, e **não é a chapa de
525 × 459** de que o flyer 15×21 fala. Ao montar para uma máquina, veja
antes em qual delas o trabalho vai correr.

## Onde mais olhar, dentro do Preps

| pasta | o que tem |
|---|---|
| `Templates\` | os 2020 modelos, em 47 pastas por cliente e por tipo |
| `Marks\SmartMarks\` · `Marks\Dupmarks\` | as marcas prontas |
| `Printers\ppd\` | as máquinas: área de imagem, pinça |
| `Profiles\` | os perfis de saída |

## Uma marca, por dentro

```
%SSiPrshMark: 0.00000 8.50394 0.00000 34.01575 5 0.00000 '' 0.00000 0 100 100 100 100 ...
                      └ 3 mm            └ 12 mm      tipo            └─ C M Y K ─┘
```

Os quatro cem no fim são a **cor de registro** — 100% das quatro tintas,
como manda o ofício (ver `fundamentos.md`). O `''` é marca comum; marca
de **texto** traz um rótulo entre barras, e aceita variável do Preps:

```
%SSiPrshMark: ... |BATE-VIRA - $COMMENT| ... 100 100 100 100
```

`$COMMENT` é preenchido na hora do trabalho. É assim que o nome do
serviço vai parar na borda da chapa.


## O modelo que já faz o nosso trabalho

Procurando bate-vira com quatro peças de 150 × 210, aparecem **quatro
modelos**. Esta casa já montou este serviço. O mais próximo do que
desenhamos é o **`210 x 150 TR F4 canoa.tpl`**, com as peças deitadas:

```
folha        450 x 350 mm          peças   210 x 150, quatro
sangria      3 mm nos quatro lados
posições     x = 15 e 225          vão horizontal  0 mm
             y = 20 e 180          vão vertical   10 mm
margens      15 mm nas laterais    20 mm em cima e embaixo
marca        3 mm de folga, 12 mm de comprimento
```

Três coisas para aprender daí:

**1. A folha é 450 × 350 — que não está em tabela de formato nenhuma.**
Eles **cortam o papel para caber a montagem**, em vez de espremer a
montagem num formato de tabela. Foi o que resolveu o impasse do flyer
15×21, que estourava o Formato 4 por 5 mm.

**2. Vão zero na horizontal — é a "canoa".** As peças se encostam e
**dividem o mesmo corte**: uma guilhotinada serve as duas. Nos modelos
em pé isso aparece na sangria, que vem **assimétrica** — `(0, 5, 5, 5)`
numa peça e `(5, 5, 0, 5)` na vizinha: a borda que encosta não sangra,
porque não há para onde sangrar. Economiza papel e um corte.

**3. Os 12 mm de marca com 3 mm de folga estão lá, literalmente.**

## A biblioteca de marcas

As marcas desta casa **não são desenhadas pelo Preps: são EPS prontos**,
em `Marks\`, colocados no modelo por nome.

| arquivo | tamanho | o que é |
|---|---|---|
| `cores finart.eps` | 35,6 × 4,9 mm | **a escala de cor da Finart** — logo + CMYK |
| `cores.eps` | 175,7 × 5,6 mm | tira de cor longa |
| `Registro.eps` | 14,5 × 7,1 mm | **a marca de registro** |
| `2 Registro.eps` | 19,8 × 7,8 mm | outra medida da mesma |
| `5 Tolbar cor.eps` | 199,0 × 10,9 mm | barra de controle |
| `Marcas de Corte.eps` | 17,3 × 17,3 mm | |

Há versões `90` de cada uma — giradas para as bordas verticais.

**São exatamente os arquivos que o operador ia mandar** (`cores.pdf` e
`registro.pdf`): já estão na máquina, e é deles que se deve partir, em
vez de redesenhar de memória.

No modelo de referência elas entram assim, na folha de 450 × 350:

| elemento | onde |
|---|---|
| `Registro 90` | x 2,7 e x 440,3 — as duas pontas do eixo maior, **centrado na altura** |
| `tolbars 90` | duas, atravessando o topo (y ≈ 333) |
| `cores` | x 24,8, y 6,2 — um canto |
| texto | `CAPA TR    OP. 08  -  MQ. 02` — serviço, operador e máquina |

O texto usa variável do Preps (`$COMMENT`) em outros modelos, preenchida
na hora do trabalho.

## A PAGINAÇÃO está escrita no modelo, e eu não estava lendo

Lido em **20/09/2026**, na bancada de casa, quando o operador perguntou
como fica a montagem de um arquivo de **14 páginas**.

O `varredura_preps.py` lê sangria, marca e vão, e **pula justamente os
dois campos que um arquivo de muitas páginas precisa**:

```
%SSiPrshPage: x y larg alt GIRO FRENTE VERSO sangE sangB sangD sangT ...
                                 └──┬──┘
                        a página que cai naquele lugar
                        na FRENTE da folha e a que cai
                        no MESMO lugar no VERSO
```

Quem lê isso agora é `ferramentas/ler_paginacao_preps.py`, e ele também
**não escreve nada**.

### A prova de que a leitura está certa

`%SSiSignature: |nome| N ...` diz quantas páginas o caderno segura.
Então a conferência é: as páginas do caderno têm de dar **1..N, cada uma
uma vez**. Nos modelos de exemplo do Preps, **72 de 100 cadernos
fecham** — e os 28 que não fecham são repetição de propósito, como o
`2 up cover`, que põe **duas** capas iguais na mesma folha.

**O ZERO não é página: é "deste lado não vai nada".** Contá-lo fazia o
modelo do calendário parecer repetir a página 0 oito vezes. Era leitura
minha errada, não defeito do modelo.

### O 16 páginas, por dentro

```
|16 page SW|   16 páginas em 8 lugares    folha 1000 x 650

   x     y     peça        giro   frente  verso
   35    333   210 x 297   180    1       2
   245   333   210 x 297   180    16      15
   545   333   210 x 297   180    13      14
   755   333   210 x 297   180    4       3
   35    20    210 x 297     0    8       7
   245   20    210 x 297     0    9       10
   545   20    210 x 297     0    12      11
   755   20    210 x 297     0    5       6
```

**A página 1 divide o lugar com a 2**, a 16 com a 15, a 8 com a 7. Um
lugar é um pedaço de papel, e papel tem dois lados: a montagem do verso
não é uma segunda conta, é **a outra metade da mesma**.

E a fileira de baixo sai a **0°** enquanto a de cima sai a **180°** —
cabeça com cabeça, que é onde a dobra passa.

### `SW` e `WT` são as duas máquinas que a casa já conhece

| no modelo | o que é | quantas chapas |
|---|---|---|
| **`WT`** — work and turn | o **bate-vira** desta casa | **uma** |
| **`SW`** — sheetwise | **frente e verso** | **duas** |

São os mesmos dois nomes da tabela de `fundamentos.md`, e agora com os
números do Preps atrás.

### O giro é um par de bits, e não um ângulo

O campo vale 4, 5, 6 ou 7. Medido:

| campo | peça |
|---|---|
| **7** | **0°** — do jeito que o arquivo é |
| **5** | **180°** |
| **6** | **90°** |
| **4** | **−90°** |

A prova é geométrica, e está dentro do próprio modelo: no `8 page SW` as
peças **só cabem** na folha de 650 × 500 se as de campo 4 e 6 ocuparem
**297 mm de largura** — que é a *altura* da página A4, ou seja, deitada.
Lidas como se estivessem em pé, sobraria um vão de 103 mm entre elas,
que não existe em montagem nenhuma.

### O CALENDÁRIO tem modelo próprio, e ele não é caderno

`Calendar.tpl`, folha 635 × 482,6, oito folhas de 304,8 × 228,6:

```
   x       y       giro   frente  verso
   9,52    241,30    0     0      2
   320,67  241,30  180     0      3
   9,52    238,12  180     1      0
   320,67  238,12    0     4      0
   ...
```

**Cada lugar tem UM lado em branco**, e os lugares vêm **aos pares, quase
no mesmo y** (241,30 e 238,12 — 3,18 mm de diferença) e **girados 180°
um do outro**. São duas folhas do calendário **cabeça com cabeça**: a
que imprime na frente e a que imprime no verso ocupam o mesmo pedaço de
papel, e os 3,18 mm entre elas são o que a guilhotina come.

Não há dobra nenhuma, e não há ordem de caderno: é **folha solta**, que
depois vira bloco no espiral ou no wire-o.

### Corte e empilha — o outro caminho de muitas páginas

`Cut and Stack A4.tpl`, duas páginas na folha:

```
   x     giro   frente  verso
   0       0     3      4
   210     0     1      2
```

Cada lugar é uma **pilha**, não uma página: o da direita leva a primeira
metade do documento, o da esquerda leva a segunda. Corta-se a folha ao
meio e **empilha-se uma metade sobre a outra** — e o bloco sai em ordem,
sem dobra nenhuma.

É por isso que os números pulam de dois em dois: com 2 lugares e 4
páginas, cada lugar come 2. Com 4 lugares e 40 páginas, cada um come 10.

**Esta é a lógica que serve a um calendário, a um bloco e a um talão** —
e é diferente da do caderno, onde a página 1 anda junto com a última.

### O que continua em aberto

Isto **descreve** o que o Preps faz; não decide o que a casa faz. A
ordem das páginas numa montagem da FIA continua sendo pergunta de
`SKILL.md` — *"caderno e paginação"* —, e por dois motivos que os
modelos não respondem: **quantas faces o serviço tem** (um lado só ou os
dois) e **como ele é encadernado** (espiral, grampo, lombada). Sem essas
duas, a mesma arte de 14 páginas tem montagens diferentes e todas
parecem certas na tela.

### A FOLHA diz como ela vira, e quanto sobra no pé

```
%SSiPressSheet: larg alt ? margem VIRA PINÇA ? sobra
```

**O 5º campo é o estilo de vira**, e a separação é limpa nos 100
cadernos — nenhum caso cai do lado errado:

| campo | cadernos | o que o nome deles diz |
|---|---|---|
| **0** | 67 | 30 dizem `SW`/`duplex`, **nenhum** diz WT ou simplex → **frente e verso** |
| **1** | 11 | 8 dizem `WT`, **nenhum** diz outra coisa → **bate-vira** |
| **3** | 22 | 13 dizem `simplex`/`1-up`, **nenhum** outro → **só frente** |

São **os mesmos três tipos de vira do painel da FIA**, e chegamos neles
por outro caminho — o operador ditando, não o Preps. As duas contas da
casa concordam de novo.

**E o 6º campo é a PINÇA** — o que resolve *"Um número a confirmar"*,
aqui embaixo, que estava aberto desde 10/09/2026. Nos 100 cadernos ele
só aparece em medida de pinça:

```
101,6 mm (4 polegadas)   62 cadernos   <- o padrao dos modelos em polegada
 60,0 mm                 15            <- os tutoriais em milimetro
 63,5 mm (2,5 pol)       10
102,0 mm                  6
```

Os **60 mm** dos modelos métricos são exatamente a pinça da **PM 52** da
AMÉRICA. O `50` de que a dúvida falava era um modelo antigo da casa com
outra máquina — não uma leitura errada do campo.

## A MARCA NÃO TEM POSIÇÃO: TEM ÂNCORA

Esta é a ideia do Preps que a FIA ainda não tem, e é a que muda o
programa. Lida nos 53 SmartMarks (`Marks\SmartMarks\*.smk`, texto puro).

Uma marca se declara assim:

```
name: |PressSheet_Bottom|
refentity:  2        <- em QUE coisa ela se pendura
refanchor:  7        <- em QUAL PONTO daquela coisa
markanchor: 9        <- qual ponto DA MARCA encosta ali
smartoffsetx/y       <- e quanto se afasta dali
sigstart / sigmod    <- e em quais cadernos ela aparece
```

A FIA calcula a posição de cada marca em milímetro absoluto. O Preps
**não calcula**: ele diz *"esta marca mora no canto de baixo à esquerda
da sangria da imposição, e é o canto de cima à direita dela que encosta
lá"*. Mudou a montagem, a marca vai junto, sem ninguém recalcular nada.

### As coisas em que uma marca se pendura (`refentity`)

Lidas pelo nome dos 53 arquivos, e todas conferem:

| | |
|---|---|
| **2** | a **folha** (`PressSheet_*`) |
| **4** | a **sangria da imposição** (`ImpBleed_*`, e todas as de registro) |
| **5 · 6 · 7 · 8** | as margens **de cima · de baixo · esquerda · direita** |
| **9 · 10 · 11 · 12** | os quatro **cantos** das margens |
| **13** | o **vão vertical** (entre colunas) |
| **14** | o **vão horizontal** (entre linhas) |

### Os nove pontos (`refanchor` e `markanchor`)

Dão a volta pela borda, começando em cima à esquerda:

```
1 --- 2 --- 3
|           |
8     9     4          9 = o centro
|           |
7 --- 6 --- 5
```

A prova está nas próprias linhas: `PressSheet_Left` vai do ponto **1 ao
7** (canto de cima à esquerda até o de baixo à esquerda), `PressSheet_Top`
vai do **1 ao 3**, `PressSheet_Bottom` do **7 ao 5**. Uma régua é dois
âncoras, não uma coordenada.

E o `markanchor` é o que faz a marca ficar **por fora**: o `Reg_TopLeft`
pendura no ponto **1** da sangria o ponto **5** da marca — o canto de
baixo à direita dela. Encostando canto com canto oposto, a marca cai
inteira para fora do desenho, sem uma conta de subtração sequer.

### Os tipos de marca

O número depois de `%SSiSmartMarkStart:` diz o que a marca é:

| tipo | |
|---|---|
| 1 | **slugline** — a tarja de texto do serviço |
| 2 | **registro** — um EPS colocado por nome |
| 4 · 5 | **colação** de lombada · de canoa |
| 6 | marca de **dobra** |
| 7 | **régua** (dois âncoras) — 38 dos 53 |
| 9 | **escala de cor** |
| 10 | **marca de corte** |

### A marca sabe em que caderno está

Dois campos que a FIA não tem e vai precisar quando montar caderno:

- **`sigstart` / `sigmod`** — em quais cadernos a marca sai. É assim que
  se põe algo "a cada dois cadernos", ou só no primeiro;
- **`stepsize` / `collstart` / `collsize`** (nas marcas de colação) — o
  **degrau**. A marca de colação anda um passo a cada caderno, e é o que
  faz aparecer a escadinha na lombada que denuncia caderno fora de
  ordem. No exemplo, passo de **6,35 mm**.

O `INFO.SMG` do grupo diz a regra em inglês, e ela é de ofício:

> *"The Perfect Bound collation mark will appear only on a perfect bound
> signature between the highest and lowest numbered pages. The
> Saddle-Stitch collation mark will only appear on a saddle-stitch
> signature, at the head of the low page."*

Ou seja: **a marca conhece o estilo de encadernação**, e se recusa a sair
no estilo errado.

### E estes números saíram dos MODELOS DE EXEMPLO, não dos 2020 da casa

Medido na bancada, e o aviso é o número: nesta máquina o Preps tem
**58 modelos** numa pasta só, `Sample Templates` — os que vêm com o
programa. Os **2020 da casa**, em 47 pastas por cliente, estão na
máquina da gráfica, e é neles que se deve conferir se a casa faz assim
também. O leitor roda igual lá.

## ~~Um número a confirmar~~ — CONFIRMADO em 20/09/2026

Estava escrito aqui: *"naquele modelo, a folha entra na chapa com um
deslocamento de 50 mm (`%SSiPressSheet: ... 141.73230 ...`). Se isso for
a pinça, são 50 e não os 60 do flyer — pode ser máquina diferente, pode
ser leitura minha errada do campo. Não use esse 50 sem confirmar."*

**Era a pinça, e a leitura estava certa.** Medido nos 100 cadernos dos
modelos de exemplo, aquele campo só aparece em medida de pinça — 101,6
(4 polegadas), 60, 63,5, 102 —, e os 60 dos modelos métricos são
exatamente a pinça da PM 52. Ver *"A FOLHA diz como ela vira"*, aqui em
cima.

Então os **50 mm** são de outra **máquina**, como a primeira leitura
suspeitava. Continua valendo o que a casa já sabia e está em
`chapas-e-pincas.md`: **a pinça é da máquina, não do formato.**
