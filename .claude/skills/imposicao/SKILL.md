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
| **mais de uma arte na mesma chapa** | **a FIA, só AMÉRICA** — bate-vira de 4 peças, **revisado por gente** antes do CTP | `references/america.md` · `ferramentas/montar_bate_vira.py` |
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
peça, sangria, vão, arranjo, tipo, cores, marcas — redesenha um diagrama
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
- **o que fazer quando a arte chega sem sangria** — o operador já disse
  o rumo: hoje o arquivo chega sangrado (2,5 mm), e mais adiante a FIA é
  que vai sangrar, PDF ou Corel. A regra de *como* ainda não existe;
- ~~marca de registro~~ — **respondido em 10/09/2026**: em pé
  (`Registro 90°.eps`), **nos dois lados**, centrada na altura, 1 mm
  depois da sangria. Escala de cor de pé, na lateral esquerda em cima, a
  3 mm. Ver "Registro e escala ficam encostados na arte";
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
| `references/america.md` | **a AMERICA: o cliente que a FIA MONTA, e o portao PARA CTP** |
| `references/chapas-e-pincas.md` | **a chapa e a pinca de 199 graficas - e a regra: pinca e da MAQUINA** |
| `references/preps.md` | o padrao da casa MEDIDO nos 2020 modelos do Preps |
| `references/fundamentos.md` | os estilos de vira, as tres marcas, cor de registro, os softwares |
| `ferramentas/painel_imposicao.html` | **o painel**: o formulário que desenha a chapa e gera a ordem |
| `ferramentas/montar_bate_vira.py` | **a montagem**: 4 peças, bate-vira, marcas, registro, escala — e a trava do portão |
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
