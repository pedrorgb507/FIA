---
name: imposicao
description: Montagem e imposicao de arquivo para a chapa - por mais de uma arte na mesma chapa, marca de corte, sangria, pinca, registro de cores, faca, dobra, caderno, paginacao, cupom, lombada, e a montagem feita no CorelDRAW pelo COM. Use sempre que aparecer montagem, montar, imposicao, impor, n-up, sangria, marca de corte, marca de registro, registro de cor, faca de corte, dobra, caderno, paginacao, encarte, cupom, aproveitamento de chapa, ou quando alguem perguntar como varias artes cabem numa chapa so.
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
| **mais de uma arte na mesma chapa** | **gente, no InDesign** | ainda não combinado |
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

Regra do operador, 10/09/2026: **arquivo todo em imagem mantém o dpi que
já tem.** Subir não cria detalhe nenhum — só peso.

O que decide não é o olho, é o arquivo: **existe um bloco `BT` (begin
text) com `Tj`/`TJ` dentro?** Havendo texto vivo, a resolução do arquivo
não quer dizer nada, porque texto não tem resolução — e aí vale
rasterizar alto, senão a letra sai serrilhada. Não havendo, o dpi das
imagens é o teto do que existe ali.

Quando é todo imagem, use o **MAIOR** dpi encontrado, não o menor: no
flyer 15×21 a maioria das imagens estava em 288 e algumas em 426 — sair
em 288 amassaria essas.

`ferramentas/montar_bate_vira.py` decide sozinho (`resolucao_do_arquivo`).

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

Centrada na largura **por exigência do vira**, não por gosto: o eixo do
giro é a linha vertical do meio, e ela tem de cair no meio da folha. Na
altura sobrava escolha, e ficou centrada no que há acima da pinça.

A ferramenta é `ferramentas/montar_bate_vira.py`.

## O que eu ainda não sei

Esta seção é o combinado desta skill: **o que estiver aqui, eu não
chuto.** Cada item sai daqui virando regra escrita quando você me
disser, e cada resposta traz um caso de verdade junto.

- ~~quanto de sobra entre uma arte e outra~~ · ~~quanto de sangria~~ ·
  ~~tamanho da marca~~ — **respondidos em 10/09/2026** pelos 2020 modelos
  do Preps desta casa: vão 5 mm, sangria 3 mm, marca de 12 mm começando
  3 mm depois do corte. Ver `references/preps.md`;
- ~~`TR` e `BV`~~ — **respondido**: são a mesma coisa, e o termo da casa
  é **bate-vira**. Como o nome não diz o eixo do giro, quem diz onde a
  pinça fica é o desenho;
- **o que fazer quando a arte chega sem sangria**;
- **marca de registro** — onde exatamente, e de que tamanho. Já se sabe
  que vai centrada no lado maior da montagem, fora do corte;
- **como se decide o aproveitamento** — cabem 6 na chapa, mas o cliente
  pediu 5: sobra branco ou muda a montagem?
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
| `references/chapas-e-pincas.md` | **a chapa e a pinca de 199 graficas - e a regra: pinca e da MAQUINA** |
| `references/preps.md` | o padrao da casa MEDIDO nos 2020 modelos do Preps |
| `references/fundamentos.md` | os estilos de vira, as tres marcas, cor de registro, os softwares |
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
