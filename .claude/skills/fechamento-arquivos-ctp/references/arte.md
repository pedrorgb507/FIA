# Conferir a arte, e pôr ela na chapa

Medir a chapa é fácil: tamanho e resolução de gravação. O difícil é olhar
para **dentro** da arte — e é o que um arte-finalista faz de olho no
arquivo.

Nada do que está aqui dá erro em lugar nenhum. Uma imagem de 300 dpi
esticada numa chapa de 1000 grava lisinha e só mostra o defeito na
tiragem.

## Preflight

`preflight.conferir_arte()` devolve achados de duas gravidades:

| | |
|---|---|
| **`AVISA`** | anota no log e o serviço segue |
| **`PARA`** | não fecha a chapa sem gente olhar |

Parar por pouco emperra a gráfica; não parar queima chapa. A linha entre
os dois foi calibrada em arquivo de verdade.

### Resolução efetiva

Quantos dpi a imagem tem **no tamanho em que foi colocada** — que não é o
dpi do arquivo dela. Uma foto de 300 dpi ampliada ao dobro vira 150, e
nada no arquivo denuncia isso.

| | |
|---|---|
| `RESOLUCAO_EFETIVA_BOA` = 300 | abaixo disso, avisa |
| `RESOLUCAO_EFETIVA_MINIMA` = 200 | abaixo disso, **para** |

Os dois números são diferentes de propósito: 300 é o que o offset pede e
o que a maioria da arte boa tem — abaixo disso vale um aviso, não vale
parar serviço. Abaixo de 200 não há discussão: sai borrado.

**A SOLIDA não para por resolução** (`CLIENTES_SEM_TRAVA_DE_RESOLUCAO`).
O número de dpi sai no log como alerta, com a frase "segui assim mesmo",
e a chapa é gravada. A arte dela vem do cliente final e chega como chega:
em 09/09/2026 dois adesivos de bola de 30 cm vieram com imagem de 26 dpi
e os dois foram liberados à mão logo depois de a FIA parar. **Trava que é
liberada toda vez não protege ninguém** — só atrasa o serviço e ensina a
ignorar aviso. É a mesma razão pela qual a SOLIDA já ficava de fora das
travas de cor.

**Só a resolução.** Fonte não incorporada continua parando a SOLIDA, e
deve continuar. A mensagem é escrita e reconhecida a partir da mesma
constante (`preflight.MARCA_RESOLUCAO` / `e_de_resolucao`), para as duas
pontas não envelhecerem separadas.

**A lista cresce um de cada vez, e só quando o operador diz.** Hoje são
quatro: SOLIDA (09/09/2026), **VIVA** (10/09/2026), **FIALHO**
(14/09/2026) e **PRIME** (18/09/2026). Ficam de fora VOPRIX, EMPÓRIO e
CREATIVE.

O caso do Fialho ensina uma coisa que os outros dois não ensinavam, e
por isso vale escrita: **a OS só sai com o arquivo INTEIRO limpo.** O
`AGENDA_CADERNO 2027_ CREDI COMIGO.pdf` tem duas páginas; a 2 passou e
virou chapa, a 1 parou a 116,7 dpi. Resultado: meia agenda no CTP, **e
nenhuma OS** — porque o passo da OS é guardado por `if planos and not
problemas`. O prejuízo de uma trava que para não é só o atraso: é chapa
gravada sem cobrança, esperando alguém ler a pendência.

**E cuidado com a analogia fácil.** A VIVA entrou por 199,67 dpi — três
décimos abaixo do limite, diferença que ninguém enxerga. O Fialho entrou
por **116,7**, num pedaço de 29 × 239 mm com feitio de lombada, e nessa
resolução ele sai visivelmente mole na tiragem. Não é o mesmo caso; é a
mesma decisão, tomada por quem olhou a arte. O alerta continua saindo no
log com o número, e é ele que registra que a chapa saiu assim.

**A PRIME entrou em 18/09/2026**, e os dois casos que o operador tinha na
mão eram **elemento pequeno puxando o serviço inteiro**: 199,1 dpi num
pedaço de 27 × 27 mm (`O.S 1049 - VIA VERITATIS`) e 148,3 dpi num de
33 × 33 mm (`SEDS - LEQUE 2 IMPRESSAO1`). O primeiro é a VIVA outra vez —
nove décimos abaixo do limite.

O que ela ensina é o custo de deixar parado: em 17 e 18/09 os dois foram
feitos **à mão, por fora da FIA**. O VIA VERITATIS virou
`510X400_CMYK_PRIME_O.S 1049_VIA VERITATIS.ps` na pasta do JOAOZ, e a OS
19845 do LEQUE foi aberta por PEDRO RAFAEL com uma vaga só. Ou seja: a
trava não impediu nada — só tirou o serviço de dentro do sistema, onde
havia registro, e o pôs onde não há.

**E ela deixa uma armadilha atrás.** Liberar a lista não destrava o que
já parou: a entrada fica como `"status": "erro"` no `_processados.json`,
e entrada de erro é permanente. Quem quiser que um arquivo antigo volte a
ser tentado precisa **tirar a entrada e reiniciar a FIA** — e antes disso
conferir se a chapa já não saiu por outro caminho, olhando **todas** as
pastas do dia no CTP, não só a `FIA`. Foi assim que se descobriu que o
VIA VERITATIS não podia voltar.

**Por que isso é difícil de medir:** o PDF não diz em que tamanho a
imagem ficou. Ele diz "desenhe esta imagem no quadrado de 1x1" e, antes,
aplica uma transformação que estica o quadrado. Para saber o tamanho real
é preciso acompanhar a pilha de transformações — `q`, `Q`, `cm` — do
começo ao fim, inclusive entrando nos grupos (Form XObject).

`LADO_MINIMO_IMAGEM_MM` = 20: imagem menor que isso em **qualquer** lado
não entra na conta. Não é desleixo — tirinha de degradê e fiozinho de
moldura são feitos de propósito com poucos pixels esticados. Medido num
folder da Creative: uma tira de 4x210 mm a 182 dpi pararia o serviço
inteiro, e ninguém enxerga a diferença num degradê de 4 mm. Aviso que
grita por isso vira aviso ignorado.

### Traço fino

`TRACO_MINIMO_MM` = 0,05. Risco mais fino que isso some na chapa. O caso
clássico é o traço de espessura **zero**, que o desenhista nem vê na
tela: o PDF manda "a linha mais fina que o aparelho conseguir", e a 1000
dpi isso dá 0,025 mm.

O número é 0,05 e não 0,10 por um motivo medido: 0,088 mm é 0,25 pt, a
espessura padrão das **marcas de corte**. Ela aparece em quase todo
arquivo, imprime perfeitamente, e com o limite em 0,10 a FIA reclamava de
cinco arquivos em cinco. Aviso que aparece sempre não é aviso.

### Fonte

Incorporada ou não. Fonte que falta é substituída pelo RIP por outra, e o
texto **muda de forma** — some a quebra de linha que o designer ajustou,
o texto vaza da caixa. É `PARA`.

### Caixas do PDF

`TrimBox` e `BleedBox` — o que o arquivo diz do corte e da sangria.

## Onde a arte entra na chapa

Três situações, e o programa escolhe nesta ordem:

**1. A medida bate** (dentro de `TOLERANCIA_MM` = 3 mm). A chapa é do
tamanho da arte, e nada se mexe. É o caso normal.

**2. Encaixe** — só FIALHO, até `ENCAIXE_MAXIMO_MM` = 15 mm. A arte entra
centralizada na chapa mais próxima: o que sobra é **cortado** igualmente
dos dois lados, o que falta vira branco.

É corte mesmo, **não redução**: nada é redimensionado, para a arte chegar
na chapa do tamanho que foi desenhada. Por isso o limite é curto — acima
dele ninguém sabe o que pode ser cortado.

**3. Montagem** — só CREATIVE. A arte chega menor e é montada na chapa,
com pinça no pé.

## A pinça, e por que ela se mede da marca

Pinça é a faixa que a máquina precisa para segurar o papel. Ali não pode
haver desenho. Na Creative são 40 mm.

**A pinça NÃO se mede da borda do arquivo, e sim da MARCA DE CORTE.** São
coisas diferentes: no santinho da Creative a marca fica 11,9 mm para
dentro da borda. Medir do lugar errado pôs a arte 12 mm fora do lugar na
chapa, e o operador viu na hora, olhando a marca.

```
borda de baixo da arte  =  pinça - corte
```

onde `corte` é a distância da borda de baixo do arquivo até a marca. No
santinho: 40 - 12 = 28 mm entre a borda da arte e o pé da chapa, o que
deixa a marca exatamente nos 40 mm pedidos.

Confere com a chapa que o operador fechou à mão em 02/09: arte de 480x330
na chapa 510x400, 15,0 mm de cada lado e 28,0 mm no pé.

**Sem achar a marca, não monta.** Vira pendência — chutar a pinça é
mandar serviço errado.

### Como a marca se reconhece

Lida no **vetor**, nunca na imagem. Tentamos achá-la na imagem
rasterizada e não deu: em arte cheia, mancha passa por risco e risco
passa por mancha, e duas versões do detector deram números diferentes
para o mesmo arquivo. No PDF a marca é um traço com coordenada exata —
ali não há o que interpretar.

```
y =  7,1 mm do pé   lados = dir+esq   comp = 6,9    <- sangria
y = 11,9 mm do pé   lados = dir+esq   comp = 6,9    <- CORTE
y = 26,9 mm do pé   lados = esq       comp = 3,9    <- desenho, não marca
```

- traço **horizontal** curto, de 2,5 a 20 mm;
- na margem **lateral**, fora do desenho;
- nos **dois lados**, na mesma altura — é o que separa marca de desenho.

## Giro

Só a Creative, e só quando a arte chega **em pé**: girada, ela volta a
ser o que sempre chega — deitada — e cabe na 510x400.
`GIRO_CREATIVE = 270` (para a esquerda), escolhido pelo operador.

Girar 90 graus não mexe em nada do desenho: é trocar linha por coluna. O
tamanho **nunca** muda, em cliente nenhum.

Girando, o pé da chapa passa a ser **outra borda do arquivo**, e é dessa
borda que a marca de corte tem de ser lida:

| giro | borda que vira o pé |
|---|---|
| 0 | pé |
| 90 | direita |
| 180 | topo |
| 270 | esquerda |

Gire uma folha 90 graus para a direita: a borda da direita desce e vira o
pé.

A chapa **não** se vira — a pinça é uma borda física dela, a que a
máquina segura. Quem se vira é a arte.

O giro é feito pela **ficha** da página (`/Rotate`), não pelo desenho: o
Ghostscript já entrega a separação deitada e nenhum pixel é recalculado.
Girar a imagem depois de separada custaria mais de um giga de memória por
chapa.

## Trabalho que sempre precisa de olho

`PALAVRAS_QUE_PEDEM_OLHO` = `VERNIZ`. Arquivo com verniz no nome não
fecha sozinho, por mais que o resto esteja em ordem — verniz se confere
antes. Pedido do operador do EMPORIO; vale também para VIVA e CREATIVE.
Na SOLIDA sempre fechou sozinho e mudar isso pararia serviço que anda.

## A conferência final da chapa gravada

Depois de gravar, o programa **mede o arquivo pronto** e o **apaga** se
estiver fora. Não confia numa variável do meio do caminho — abre, lê o
tamanho da página e quantos pixels a imagem tem dentro dela, e divide. É
a conta que a gravadora vai fazer.

| caminho | o que se confere |
|---|---|
| longo | tamanho em mm **e dpi real** (`pdf_builder.conferir_resolucao`) |
| curto | tamanho em mm **e uma página só** (`entrega.conferir`) |

No curto não há pixel para contar — o arquivo é vetorial e a resolução
quem escolhe é a gravadora. Mas duas páginas num arquivo da pasta do CTP
são duas chapas na fila sem ninguém ter pedido, e a OS cobrou uma.

## A prova impressa

Uma folha **A4 em pé** por página da arte, a 150 dpi. A chapa é maior que
o papel, então a prova sai reduzida.

O que vai para a impressora é sempre um A4 montado por nós — nunca o
arquivo do cliente. Assim um PDF esquisito não derruba a impressão. E
arte deitada é girada aqui: o `-dFitPage` do Ghostscript quebra quando
precisa girar a página.

A etiqueta do formato (`SOLIDA F4`, `VIVA F4`) é escrita numa faixa em
branco no alto, e a arte **desce** para caber embaixo dela — o texto
nunca cai por cima do desenho.

Com OS, a folha da ordem de serviço entra **intercalada**, uma depois de
cada página da arte, tudo num trabalho só:

```
arte p1 | OS | arte p2 | OS   ->   duas folhas, arte na frente, OS no verso
```

Assim um arquivo frente e verso rende duas folhas completas, e não uma
folha de arte solta com a OS do outro lado da errada.

**Sem prova, sem chapa.** Se a impressora falhar, o arquivo fica segurado
e o programa tenta de novo — a prova é o papel que o operador leva para a
máquina. A OS que já saiu não vira duas: na passada seguinte o título é
achado nela e o número é reaproveitado.

## A pinça, cliente a cliente — 15/09/2026

A pinça é da **máquina**, não do formato: seis gráficas usam a mesma
510x400, cada uma com a sua. E de onde ela se mede **muda por cliente** —
esta é a parte que não se adivinha.

| cliente | chapa | pinça | medida a partir de |
|---|---|---|---|
| CREATIVE | 510x400 | 40 mm | **marca de corte** |
| PRIME | 510x400 | 28 mm | **marca de corte** |
| AMERICA | 525x459 · 650x550 | 60 mm | **marca de corte**, ou a borda se não houver |
| AMERICA | 745x605 | 62 mm | **marca de corte**, ou a borda se não houver |

**A AMÉRICA já foi exceção aqui, e deixou de ser em 17/09/2026.** Estava
escrito que ela se mede pela **borda**, e o motivo parecia sólido: das
oito montagens dela que existiam em 15/09/2026, nenhuma tinha marca que
o `marcas_de_corte` reconhecesse.

Estava errado como regra. Aquelas oito já vinham **no tamanho da chapa**,
e numa montagem pronta a marca fica a ~60 mm da borda — fora do alcance
de 40 mm (`BORDA_MM`) do detector. Não havia marca **de se ver**; não que
não houvesse marca. O que chega **por montar** é outra coisa, e aí a
marca está a 15 ou 20 mm da borda, onde o detector a acha sem esforço.

Custou o `Receituário Orto Saúde 2026`: marca a 16,5 mm, assentado pela
borda, linha de corte a **76,4 mm** numa chapa de pinça **60**. O
operador mediu com a régua e viu.

**A regra é uma só, para todo cliente: a pinça se mede até a marca de
corte, e só na falta dela vale a borda.** Generalizar de arquivos que
não deixavam ver a marca foi o erro — o mesmo tipo de inferência de
sobrevivente que a skill `gerempre` documenta no `OSSIT`.

**Duas marcas na PRIME.** Regra do operador: *"pode acontecer de vir com
duas marcas, você sempre deve pinçar a partir do de cima"*.

**Sem marca, não se chuta.** Quando o cliente pinça pela marca e a marca
não aparece, vira pendência — e a pendência **diz o que se viu**
(`pistas_da_marca`), porque quase sempre a marca está lá, só que fora de
alguma das regras: traço de um lado só, ou mais para dentro do que o
alcance. Chutar a pinça é mandar serviço errado para a máquina.

**E não se gira para fazer caber.** Arte que só entra na chapa deitada
para e pergunta. Sem marca de corte não dá para saber que lado é o pé, e
girar errado põe a arte de cabeça para baixo na máquina: chapa perdida e
tiragem perdida.

## A montagem fica na pasta do dia

Pedido do operador em 14/09/2026, para a PRIME: *"você vai salvar de novo
na pasta do dia com o mesmo nome mas `_montagem` no final… depois disso
vai pegar essa montagem e continuar o procedimento normalmente"*.

É o passo que ele fazia à mão, e serve para duas coisas: fica na pasta
para ser conferido, e é **dela** que a chapa do CTP sai. Assim o que foi
gravado é exatamente o que está ali para olhar — não uma segunda
montagem feita em memória.

Vai em **vetor**, não rasterizada: é leve, abre em qualquer lugar e não
perde nada.

→ O vigia **pula** os `_montagem` dos clientes que a salvam
(`CLIENTES_QUE_SALVAM_A_MONTAGEM`). Ela é saída nossa, não entrada: se
voltasse pela porta da frente, sairia uma segunda chapa e um segundo item
na OS, do mesmo serviço.

→ O mesmo cuidado vale no portão da AMÉRICA, por outro caminho: montando,
o PDF solto publicado **sai do portão**. Ficando os dois, a volta
seguinte acharia duas chapas para o mesmo serviço.
