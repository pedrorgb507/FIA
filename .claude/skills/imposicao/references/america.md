# A AMÉRICA — o cliente que a FIA monta

Combinado com o operador em 10/09/2026.

## Por que ela é diferente de todos os outros

Os seis clientes que a FIA já atende **mandam o arquivo pronto**: já
montado, já imposto, no tamanho da chapa. A FIA só faz o fechamento
final — confere, abre a OS, imprime a prova e grava.

**Na AMÉRICA não.** O arquivo chega **por montar**, e quem monta é a
casa. Então o arquivo que cai na pasta do dia **não é um serviço pronto —
é matéria-prima**. Mandá-lo para o CTP como se fosse pronto seria gravar
chapa de arquivo não montado.

## Os dois portões, e quem cria a pasta

```
V:\AMERICA\<Mês>\<Dia>\               <- o arquivo chega aqui. NAO tocar.
V:\AMERICA\<Mês>\<Dia>\PARA MONTAR\   <- o que a equipe vai montar
V:\AMERICA\<Mês>\<Dia>\PARA CTP\      <- só o que está aqui vira chapa
```

**A FIA só fecha a `PARA CTP`.** O que estiver na pasta do dia, fora dela,
é arquivo esperando montagem — e esperar é o certo.

**A pasta do dia e os dois portões são criados pela FIA**, desde
18/09/2026 — pedido do operador: *"todo dia então, crie a pasta do dia e
dentro dela crie, PARA MONTAR e PARA CTP"*. Antes era combinado entre
pessoas, e a criação diária caía em cima de quem o sistema existe para
desamarrar.

Quem faz é `america.garantir_pastas_do_dia`, e **os dois processos
chamam**: o vigia a cada volta do laço e o servidor da fila a cada vez
que a tela é desenhada. Não é desperdício — sem nada a criar são três
`isdir` —, e é o que permite a equipe abrir a tela antes de alguém ligar
a FIA.

**Portão faltando virou sintoma, e não rotina.** Enquanto a pasta era
criada por gente, faltar queria dizer "ninguém preparou o dia ainda".
Agora só pode querer dizer que a FIA não está alcançando a pasta da
AMÉRICA no servidor. A tela da fila diz isso com essas palavras e **não
manda ninguém criar a pasta na mão**: criaria, o arquivo entraria, e a
montagem não teria como ser gravada de volta — quem grava é justamente
quem não está alcançando o servidor.

## O caminho, a quatro mãos

| | quem | o quê |
|---|---|---|
| 1 | cliente | põe o arquivo em `V:\AMERICA\<Mês>\<Dia>\` |
| 2 | **operador** | passa à FIA as informações da montagem (chapa, pinça, arranjo, vão) |
| 3 | **FIA** | monta e grava `<mesmo nome>_MONTAGEM.pdf`, **na pasta do dia** |
| 4 | **operador** | **revisa** e, aprovando, move para `PARA CTP` |
| 5 | **FIA** | dali em diante é o fluxo normal: OS, prova, chapa no CTP |

O passo 4 é humano de propósito. A montagem é decisão, não conta: quem
diz que está certa é quem vai rodar.

"Será inicialmente um trabalho a quatro mãos" — palavras do operador. O
que a FIA aprender de cada montagem entra nesta skill, e a mão dela
cresce.

## A regra do nome

**`<mesmo nome do arquivo>_MONTAGEM`** — sufixo, no fim.

Não é invenção: a pasta da AMÉRICA de 10/09/2026 já trazia
`CRISTÃOS.pdf` ao lado de `CRISTÃOS_MONTAGEM.cdr`, e as OS do GEREMPRE
guardam títulos como `SANTINHO LUIS E LULA_MONTAGEM` e
`CARTAO DE RETORNO CBCO_MONTAGE`. A casa já fazia assim.

O nome de origem vai **inteiro**, sem limpeza — é ele que amarra a
montagem ao arquivo que a gerou.

## Os números da AMÉRICA, lidos do GEREMPRE

Conferidos em 10/09/2026, em leitura travada, nas OS que a casa abriu
esta semana:

Cliente **58** — `AMERICA (GRAFICA E EDITORA AMERICA LTDA)`. As chapas
são **do cliente** (`RBCHAPA = 1`), e são **três máquinas**:

| máquina | chapa | medida | preço | pinça |
|---|---|---|---|---|
| **PM 52** | 90 `PM_52` | 525 × 459 | R$ 8,00 | 60 mm |
| **MOZP** | 91 `MOZP_FT2` | 650 × 550 | R$ 12,00 | 60 mm |
| **SM 74** | 89 `SM_74` | 745 × 605 | R$ 12,00 | 62 mm |

**Os preços saíram dos usos MAIS RECENTES, não do que aparece mais
vezes.** A MOZP tem 272 lançamentos a R$ 10,00 e 112 a R$ 12,00 — mas
tudo desde agosto está em 12, então 10 é preço velho. Contar frequência
teria cobrado a menos.

### Qual máquina recebe o trabalho

Regra do operador: **até o formato 4** (maior lado ≤ 560 mm) vai na
**PM 52**; acima dele, **colorido** vai na **SM 74** e **preto-e-branco**
vai na **MOZP**.

Os 560 mm são a mesma linha que o GEREMPRE usa para separar `F4` de `F2`
na OS — agora num lugar só, `MAIOR_LADO_F4` no `config.py`.

O operador disse "geralmente". Então quando a regra não bate com o
tamanho do arquivo que chegou, **manda o arquivo** — ele já está montado
e revisado —, mas fica um aviso no log: é fora do geralmente que vale um
olho.

**Atenção:** existe também uma chapa **15**, chamada `525X459`, de dono
`0` (própria da Finart). **Não é a da AMÉRICA.** A da AMÉRICA é a 90. Usar
a 15 baixaria estoque no lugar errado.

A AMÉRICA tem outras máquinas: a `SM_74` (chapa 89, 745 × 605, R$ 12,00)
aparece nas OS de revista. Ao montar, saiba em qual delas o trabalho vai
correr — a pinça e o preço mudam.

## O nome da chapa no CTP

Lido do que já está gravado em `W:\CTP\SETEMBRO\10\`:

```
525x459_CMYK_AMERICA_Panfleto RAImundo
525x459_GREY_AMERICA_El Shaday
525x459_AMERICA_CRISTAOS
```

É o mesmo feitio dos outros clientes de formato no nome —
`<formato>_<cores>_AMERICA_<nome>`.

Cada operador tem a sua pasta dentro do dia (`FIA`, `JOAOZ`, `PEDRO`,
`eudson`); a FIA grava na dela.

### Duas páginas viram dois arquivos, numerados na frente

A montagem que o programa faz sai sempre com **uma** página. Mas o portão
aceita o que o operador puser nele, e ele monta frente e verso à mão —
foi o `PASTA PRE MEETING fv.pdf`, em 17/09/2026, que foi para o CTP com
as duas páginas dentro. A OS cobrou as 8 chapas certas (2 páginas ×
CMYK), a prova saiu com as duas, e mesmo assim só uma seria gravada: **a
gravadora não puxa múltiplas páginas.**

```
01 745x605_CMYK_AMERICA_PASTA PRE MEETING fv.pdf
02 745x605_CMYK_AMERICA_PASTA PRE MEETING fv.pdf
```

O número vai **na frente**, com dois algarismos, porque a pasta do CTP é
lida em ordem alfabética. Com uma página só, nada muda: o nome continua
limpo, sem número. A regra vale para todos os clientes e está na skill
`fechamento-arquivos-ctp`, em *"No CTP: um arquivo, uma página"*.

## O que acontece depois do portão

`ferramentas/fechar_america.py`, na ordem:

| | passo |
|---|---|
| **0** | **"já fechei este?"** — pergunta ao registro **antes de tudo** |
| 1 | **guarda cópia** na pasta do dia |
| 2 | **abre a OS** no GEREMPRE — mexe em estoque |
| 3 | **imprime a prova**, com a OS no verso — e **sem prova, nada segue**: impressora fora do ar segura o arquivo no portão, como nos outros seis clientes. Prova que *já saiu* (`JaImprimiu`) não é falha, e o fechamento continua |
| 4 | **grava a chapa no CTP** e confere que chegou inteira |
| **5** | **anota no registro** — o trabalho está feito aqui |
| 6 | **apaga da `PARA CTP`** |

### O passo 0 e o passo 5 custaram três folhas de papel

Em 10/09/2026 o portão imprimiu a **mesma prova três vezes**. O caminho:
o apagar recusou por um detalhe; o arquivo ficou no portão; o vigia
voltou cinco segundos depois e **refez tudo**, prova inclusive.

É o mesmo defeito do `02020 - CHAPA ZIMI` do EMPORIO, em outra roupa:

> **Falha depois da impressão vira laço de impressão.**
> Quem imprime tem de deixar dito que imprimiu — na hora, antes de
> fazer mais qualquer coisa.

O trabalho está **feito** quando a chapa está no CTP conferida. O apagar
que vem depois é **faxina**. Anotar só depois da faxina fazia faxina que
falha custar trabalho refeito.

E quando o portão encontra um arquivo já fechado, ele **termina a
faxina** — guarda a cópia e tira do portão — sem abrir OS, sem imprimir
e sem gravar chapa. Senão o arquivo ficaria ali para sempre, pulado em
silêncio.

O que salvou a conta naquele dia foi o `ja_esta_em_os`: as três voltas
acharam a OS 19635 e **não recobraram**. Razão intacto, saldo em 110,
uma OS só. O estrago foi papel.

O nome no CTP sai pelo protocolo da casa —
`<formato>_<cores>_AMERICA_<descrição>`, com o `finalizar()` tirando
acento. O **`_MONTAGEM` cai** aqui: ele serve para separar a montagem do
original dentro da pasta do cliente, e no CTP não há original com que
confundir. Foi assim que os operadores fizeram `CRISTÃOS.pdf` virar
`525x459_AMERICA_CRISTAOS`.

Mas o **título da OS mantém** o `_MONTAGEM` — as OS da casa guardam
`CRISTAOS_MONTAGEM` e `SANTINHO LUIS E LULA_MONTAGEM`. Os dois nomes
são diferentes de propósito.

### Sobre apagar da `PARA CTP`

Pedido do operador, e a razão dele é boa: **caixa de entrada que acumula
vira depósito**, e o servidor enche.

Mas apagar é para sempre. Então o apagar só acontece com **três coisas
provadas antes**:

1. a chapa está no CTP, do mesmo tamanho em bytes, e **abre como PDF**;
2. existe cópia na pasta do dia — e se o operador tiver **movido** em vez
   de copiado, o programa **devolve a cópia para lá antes** de apagar;
3. nada estourou nos passos anteriores.

E se a pasta do dia já tiver uma montagem **com o mesmo nome e conteúdo
diferente** — que foi o que travou tudo naquele dia —, quem manda é a do
**portão**: é a que o operador revisou. A antiga é posta de lado com a
data no nome, porque não se joga fora montagem de ninguém.

Faltando qualquer uma, **o arquivo fica**. Pesar o disco é problema;
perder montagem revisada é pior.

A `PARA CTP` é caixa de entrada; a **pasta do dia é o arquivo da casa**;
o CTP é a entrega. Cada uma com um papel.

## O que ainda não está ligado

Desde 10/09/2026 o portão é **automático**: `america.rodada()` é chamada
a cada volta do laço do vigia, logo depois da ponte do Teams.

**Ela não entra na lista de `clientes()`**, e é de propósito — o caminho
da AMÉRICA é outro. O que se vigia não é a pasta do dia, e sim a
subpasta `PARA CTP`; o arquivo que chega ali já é chapa pronta, não arte
por montar; e no fim ele é apagado, o que nenhum outro cliente faz.

A rodada **não estoura para cima**: o portão da AMÉRICA quebrando não
pode derrubar o vigia dos outros seis.

E ela espera o arquivo terminar de chegar (`arquivo_estavel`) — uma
chapa tem megabytes, e ler pela metade daria chapa cortada no CTP.

Para rodar fora do vigia, `ferramentas/fechar_america.py`, com `--olhar`
para conferir sem escrever nada.

## O .cdr no portão — 15/09/2026

*"se eu coloco o arquivo lá dentro dessa pasta no corel, você segue a
sequência que vc usa na voprix ou creative, conferir a pinça, se não
tiver pinçada, colocar do jeito certo"* — o operador.

O `.cdr` da AMÉRICA **não se rasteriza**, ao contrário do da VOPRIX e do
da PRIME: ela manda a montagem pronta, com a imagem já dentro do
arquivo. O `.cdr` só é publicado em PDF pelo motor da Corel, e esse PDF
já é a chapa.

**A PINÇA SAI DA MARCA DE CORTE, QUANDO HÁ UMA — e até 17/09/2026 não
saía.** Estava escrito aqui que "a pinça não sai da marca de corte
aqui", medido nas **oito** montagens que existiam em 15/09/2026, em que
o `marcas_de_corte` não achava marca nenhuma. A conclusão estava certa
para aquelas oito e **errada como regra**: elas já vinham no tamanho da
chapa, e numa montagem pronta a marca fica a ~60 mm da borda, fora do
alcance de 40 mm (`BORDA_MM`) do detector. Não havia marca *de se ver* —
não que não houvesse marca.

Quem chega **por montar** é outra coisa. O `Receituário Orto Saúde 2026`
chegou em 17/09/2026 com a arte de 480 × 330 e a marca de corte a
**16,5 mm** da borda do arquivo, onde o detector a acha sem esforço.
Assentando pela **borda**, a primeira linha de corte caiu a **76,4 mm**
numa PM 52 de pinça 60 — a montagem inteira subiu 16 mm, e quem mede com
a régua acha 76 onde devia achar 60.

O operador viu na hora: *"não foi pinçada com 6cm que é a pinça da chapa
menor, então está errado"*.

**A regra é a da casa inteira, e ela não tinha exceção nenhuma: a pinça
se mede até a MARCA DE CORTE.** É a mesma que custou uma chapa 12 mm fora
do lugar na CREATIVE. Quando não há marca reconhecível, vale a borda do
arquivo — que é a conta antiga, e continua certa para as oito.

A prova de que a conta nova está certa é a companhia que ela faz. As
montagens boas da AMÉRICA começam a tinta assim:

```
#1304-26-CONVITE-MEETING_MONTAGEM        pé 46,5
Flyer Semana do Cliente_MONTAGEM         pé 45,0
Arte Rifa 2025_MONTAGEM                  pé 47,3
SERRA DO BÁLSAMO - TAMPA 480             pé 47,3
IPO-563263 FOLDER -FLYER 148x210mm       pé 47,1
miolo 16x23 caderno padrão juan          pé 46,0
Porta do Céu - Livro_MONTAGEM F2         pé 45,0
```

O Receituário saía a **63,8**. Refeito pela marca, sai a **47,29** — e a
linha de corte cai em **60,00**, medida no pixel.

O que as montagens de verdade mostram, medindo a **tinta** dentro da
chapa:

```
#1304-26-CONVITE-MEETING_MONTAGEM   525x459   esq 37,5  dir 37,5  pé 46,5
Flyer Semana do Cliente_MONTAGEM    525x459   esq 35,0  dir 35,0  pé 45,0
```

Centradas ao milímetro, e a tinta começando ~15 mm **abaixo** da pinça de
60: as marcas de corte e registro vivem dentro da pinça. Daí a
`FOLGA_DAS_MARCAS` de 20 mm na conferência.

**As três decisões do `america.py`:**

| o que chega | o que a FIA faz |
|---|---|
| já no tamanho de uma chapa | não monta; **confere** a pinça pela tinta e **PARA** se estiver sem pinça |
| menor, e cabe com a pinça | monta centrada, **marca de corte** na pinça da chapa (borda do arquivo, se não houver marca) |
| só cabe **deitada** | **para e pergunta** — sem marca de corte não dá para saber que lado é o pé, e girar errado põe a arte de cabeça para baixo na máquina |
| não cabe em nenhuma | para |

→ **O portão nunca pode ficar com dois PDFs.** Montando, o PDF solto
publicado sai do portão para a pasta do dia; ficando os dois, a volta
seguinte do vigia acharia duas chapas para o mesmo serviço — duas
gravações e duas OS.

→ O `.cdr` **sai do portão e não é apagado**: ele é a fonte da montagem.
Deixado lá, seria publicado de novo a cada volta.

### Sem pinça não vai para o CTP — e agora a FIA pinça sozinha

Regra do operador, 17/09/2026, em duas metades dadas no mesmo dia:

> *"nunca um arquivo pode ir sem pinçar para o ctp"*
>
> *"quando o arquivo for pra pasta PARA CTP, e não estiver pinçado vc já
> ajusta, e sempre confere a pinça, para ver se está pinçada"*

O `conferir_a_pinca` passou por três estados nesse dia, e a sequência é
a lição: **avisava → parava → ajusta.** Avisar não parava ninguém — o
arquivo ia para o CTP do mesmo jeito. Parar era o certo **enquanto a FIA
não soubesse fazer**; sabendo, parar é só empurrar para uma pessoa o que
ela pode resolver e conferir. Parar continua sendo o fim da linha, para
quando o ajuste não couber.

**A faixa da pinça é onde a máquina segura a folha.** Desenho ali não
imprime — não é ficar feio, é chapa gravada que não serve.

#### Tinta e desenho são coisas diferentes

Esta é a parte que se erra, e eu errei antes de medir:

| | onde começa, numa chapa de pinça 60 |
|---|---|
| **a tinta** | ~47 mm — e são as **marcas** de corte e registro, que vivem dentro da pinça de propósito |
| **o desenho** | ~57 mm — e ele desce abaixo da linha de corte pela **sangria**, que a guilhotina come |

Medido:

```
Receituário Orto Saúde   pinça 60    tinta 47,3   desenho 57,3
PASTA PRE MEETING fv     pinça 62    tinta 46,8   desenho 56,8
No Auge da Loucura       pinça 60    tinta  2,0   ← esta é que não tem pinça
```

A conta antiga olhava a **primeira tinta** e perdoava 20 mm de folga,
justamente para não acusar as marcas. Era conta cega com remendo: a
mesma folga perdoava 20 mm de **desenho** invadindo a pinça. Agora se
mede o desenho, e a folga cai para os 15 mm que separam sangria
(−3 a −5,5) de montagem sem pinça (−58). Entre esses dois números não há
o que calibrar.

#### Como a medida separa os dois

`medir_o_pe()` rasteriza e conta tinta **linha a linha**: marca de corte
é risco fino, desenho é faixa larga. Medido na montagem do Receituário,
a 8 px/mm:

```
de 63,6 a 73,5 mm       4 px por linha    ← as quatro marcas
de 73,5 para cima    3438 px por linha    ← o desenho
```

Quatro contra três mil e quatrocentos: três ordens de grandeza.

**Por que na imagem, e não no PDF.** O `marcas_de_corte` lê os números
escritos no fluxo da página, e numa página **montada** esses números são
os da arte **antes** de ser deslocada — o merge escreve a translação numa
matriz, e o leitor de traços não a aplica. Na montagem do Receituário ele
devolve 16,50 mm, que é onde a marca estava dentro da arte, e não os
60,00 onde ela ficou na chapa. **Rasterizar custa segundos e não tem como
mentir.**

*(Daí também a escala sair da imagem e não do `-r` pedido: o Ghostscript
só aceita dpi inteiro, e pedir 4 px/mm vira `int(101,6) = 101`, que são
3,976. Dividir pelos 4 que se queria erra 0,6% — 1,5 mm aos 250, 2,4 aos
400. Quem pegou foi um teste sintético; num arquivo de cliente isso
passaria por folga de medição.)*

#### O ajuste, e o que ele não faz

`ajustar_a_pinca()` **desloca o conteúdo para cima** até o desenho
alcançar a pinça. Só serve para quem já chega no tamanho da chapa — quem
chega menor é assentado pelo `montar()`, que pinça pela marca de corte.

Duas travas, e nenhuma é formalidade:

- **só se couber.** Subir empurra o topo, e o que passar da borda de cima
  some sem avisar. Seria trocar um defeito visível (arte na pinça) por um
  invisível (arte cortada). Não cabendo, **para** e o arquivo fica no
  portão;
- **confere depois.** O deslocamento é uma conta; que ele tenha
  acontecido é outra coisa, e se mede no arquivo que saiu. Não conferindo,
  o arquivo é **apagado** — mandar para o CTP o que não se conferiu é pior
  que não ter tentado.

O original nunca se apaga: ele vai para a pasta do dia, como o PDF solto
das montagens.

#### E sempre confere — inclusive o que a própria FIA montou

Depois de montar, a pinça é medida no arquivo que saiu. Não é
desconfiança boba: a conta acontece numa matriz escrita no PDF, e entre
escrevê-la e ela valer há um programa inteiro. Quem mede é o Ghostscript,
que não sabe o que a FIA quis. Não conferindo, a montagem é apagada e o
serviço para.
