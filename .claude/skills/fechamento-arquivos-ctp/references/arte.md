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
