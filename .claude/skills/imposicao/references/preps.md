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

**`TR` e `BV` são coisas diferentes nesta casa** — dois conjuntos
separados de modelos, com nomes distintos. A literatura chama a família
inteira de *tira e retira* e separa por eixo do giro (ver
`fundamentos.md`); aqui os dois nomes convivem, e **qual é qual ainda
não foi confirmado pelo operador**. Não invente: pergunte.

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
