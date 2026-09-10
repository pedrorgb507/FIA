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

## Um número a confirmar

Naquele modelo, a folha entra na chapa com um deslocamento de **50 mm**
(`%SSiPressSheet: ... 141.73230 ...`). Se isso for a pinça, são 50 e não
os 60 mm que o operador falou para o flyer — pode ser máquina diferente,
pode ser leitura minha errada do campo. **Não use esse 50 sem
confirmar.**
