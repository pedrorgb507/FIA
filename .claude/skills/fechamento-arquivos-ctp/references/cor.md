# Cor: quantas chapas, e quais

Quantas tintas a arte usa decide três coisas ao mesmo tempo: quantas
chapas serão gravadas, o que vai no nome do arquivo e **quanto a OS
cobra**. Errar aqui não é erro de cor — é erro de estoque e de fatura.

A conta vem do `inkcov` do Ghostscript: quanto de cada tinta a página
usa, de 0 a 1. Abaixo de `LIMIAR_TINTA` (0,0001) a tinta é considerada
ausente — é sujeira de arredondamento.

## O perfil ICC — a armadilha que custou uma chapa

**Os números dentro do PDF podem estar certos e a leitura sair errada.**

Por padrão o Ghostscript gerencia cor: CMYK do arquivo → perfil de origem
→ perfil do dispositivo → CMYK de saída. Quando o arquivo traz perfil
próprio embutido, essa volta **não é identidade**. Cinza feito só de K
sai remisturado nas quatro tintas, e o K esvazia.

A Corel embute um perfil de 557 KB e o declara como `/DefaultCMYK`. Numa
pasta de verdade, medido a 1000 dpi — a resolução da chapa:

| Pasta Gyno Center | C | M | Y | K |
|---|---|---|---|---|
| como está escrito no arquivo | 0,0439 | 0,0441 | 0,0075 | **0,0515** |
| como a chapa foi gravada | 0,0945 | 0,0973 | 0,0621 | **0,0060** |

**8,6 vezes menos preto**, e o amarelo com 8 vezes mais tinta do que
devia. O logo sumiu da chapa do preto, o texto virou fantasma e o bloco
de telefone e CNPJ quase desapareceu — tudo aquilo ia imprimir montado de
CMY, fora de registro e sujo.

E dentro do PDF o preto sempre esteve certo: `0 0 0 1` para o preto
cheio, `0 0 0 0.502` para o cinza de 50%.

A prova do mecanismo: lendo o **mesmo arquivo** com o perfil, os números
voltam a ser os da chapa errada. Era a leitura, ponto.

```
-dUseFastColor=true      lê a cor como ela está escrita no arquivo
```

No código: `ghostscript.sem_perfil()`.

### Onde isto está ligado, e onde não está

| caminho | clientes | lê com perfil? |
|---|---|---|
| curto | VOPRIX | **não** — e por isso a cor chega inteira |
| longo | SOLIDA, FIALHO, EMPORIO, VIVA, CREATIVE | **sim, ainda** |

**Isto é decisão, não esquecimento.** Medido em 09/09/2026, nos arquivos
do dia:

- EMPORIO, CREATIVE e FIALHO: **não são afetados** — a leitura com e sem
  perfil dá o mesmo número. Os PDFs deles não trazem perfil embutido;
- VIVA: **é afetada**. No `GRADE 18.pdf`, M cai de 0,454 para 0,369 e Y
  de 0,437 para 0,260 quando se lê sem o perfil;
- SOLIDA: não medida (o arquivo do dia deu erro de leitura no zlib).

O operador decidiu **deixar como está e registrar o risco**: rodou assim
durante anos, ninguém reclamou, e mudar a cor de saída de cliente que
está rodando também tem risco — pede conferência de chapa antes.

**Se um dia aparecer chapa suspeita de preto lavado num desses clientes,
comece por aqui.** O teste é de um comando, e não muda nada:

```
gswin64c -q -o - -sDEVICE=inkcov ARQUIVO.pdf
gswin64c -q -dUseFastColor=true -o - -sDEVICE=inkcov ARQUIVO.pdf
```

Números diferentes = o arquivo traz perfil e a leitura o está aplicando.

**Compare sempre na mesma resolução.** Rasterizar vetor em 100 dpi e
comparar com chapa de 1000 dpi reduzida para 100 mostra diferença que não
existe. Use `-r1000` nos dois lados.

## Quadricromia e uma cor fecham sozinhas; duas ou três cores esperam

Em quadricromia o caminho é sempre o mesmo. **Uma cor também** — desde
10/09/2026, por decisão do operador: "gera o PDF normal, e ao invés de
CMYK coloca GRAY, e dá andamento normal". Só a arte de **duas ou três
tintas** continua sendo decisão de trabalho para trabalho, e quem decide
continua sendo gente.

`AVISAR_QUANDO_NAO_FOR_CMYK` — só para **VOPRIX, EMPORIO, VIVA e
CREATIVE** — deixa passar quadricromia e o caso `cinza` (a arte de uma
cor, ver seção abaixo). O que **não fecha** é a página com duas ou três
tintas, ou uma tinta que não é neutra (um spot color sozinho, por
exemplo): vira pendência com a cobertura de cada tinta na tela, para
alguém conferir. A prova sai do mesmo jeito, e o PDF já convertido fica
guardado na `PASTA_PENDENCIAS`, para o trabalho da Corel não se perder.

**Antes disso** a trava parava as duas coisas juntas — uma cor e duas ou
três — e a arte de uma cor desses quatro clientes ficava pendente até
alguém aprovar à mão. Isso mudou; duas ou três cores continua igual.

**SOLIDA e FIALHO ficam fora das duas travas desde sempre** — nem a de
quadricromia nem a do cinza fazem sentido pra eles: arte de uma cor
deles já fechava sozinha antes de 10/09/2026, pela própria cobertura (ela
já chega como uma tinta só, sem o artifício do preto composto). Mudar
isso pararia serviço que hoje anda. No Fialho a razão é outra também: a
arte dele chega pronta, no tamanho da chapa, e o que decide o que anda
ali é o formato, não a cor. **A FIALHO nem roda a conferência do preto
composto** (`sem_cor_gritante`) — um teste garante isso, porque rodá-la
ali seria trabalho à toa.

**O que isso muda na conta:** se a frente sai em CMYK (4 chapas) e o
verso em GRAY (1 chapa), a OS agora fecha o arquivo inteiro e lança
**5 chapas** — antes o verso ficava pendente e segurava o arquivo
inteiro (nenhuma OS nascia, mesmo a frente já tendo saído pronta).
`quantas_chapas()` (em `gerempre.py`) já somava por tinta de cada
página; o que faltava era a página de uma cor não travar mais o
caminho até ali.

## Arte de uma cor: uma chapa, não quatro

Arte de uma cor às vezes não chega como preto puro: vem **composta**, com
C, M, Y e K juntos. Gravar isso como quadricromia dá quatro chapas onde o
trabalho pede uma; e pegar só o canal K dá chapa lavada, porque o preto
está espalhado.

O certo é rasterizar a página em cinza — `/DeviceGray`, uma chapa só — e
escrever `GRAY` no nome, que é o que os operadores escrevem à mão.

Duas perguntas decidem, e as duas precisam passar:

1. **a cobertura das três cores bate?** Num arquivo real: C 0,06081,
   M 0,06079, Y 0,06080 — iguais até a quarta casa. Arte colorida nunca
   faz isso, porque cada canal tem o seu total. Preto puro (CMY zerados)
   também conta como uma cor;
2. **existe cor gritante em algum pixel?** Rasteriza em 72 dpi e confere.
   Pega o caso que a conta acima não pega: vermelho de um lado e ciano do
   outro pode fechar os totais e passar por neutro sem ser.

A folga da segunda é larga — 96 de 255 — de propósito: arte cinza de
verdade não tem canal igualzinho pixel a pixel, a borda do texto sai com
ruído de anti-aliasing (num arquivo real, até 39 de diferença em 6% dos
pixels). Com folga apertada, arte cinza legítima seria reprovada.

> **Cuidado com a explicação antiga.** Este trecho já disse que "a Corel
> exporta o preto composto", e era falso: a Corel escreve `0 0 0 1`. Quem
> compunha o preto era a leitura com perfil. Onde a leitura é sem perfil,
> arte K-only aparece como K-only de verdade.

**No caminho curto, arte de uma cor com quatro tintas não passa.** A
gravadora não tem como adivinhar que aquilo é uma chapa só — gravaria
quatro, e a OS cobrou uma. Volta pelo caminho longo, que junta tudo num
cinza. Arte de uma cor com **uma** tinta passa: a gravadora acha aquela
tinta e grava a mesma chapa que a gente contou. É o que
`processador.cabe_no_curto()` decide.

## Cor especial

O `tiffsep` devolve uma separação por tinta, com o nome que o arquivo
declara. As quatro de escala viram C, M, Y e K; qualquer outra é
**cor especial** — Pantone, verniz — e entra no log com aviso e no nome
da chapa depois das quatro de escala.

Separação vazia é descartada: tinta que a cobertura não viu não vira
chapa.

## A conta que vira OS

O que a OS cobra vem do que **realmente saiu**, não do que se esperava
sair:

```
chapas do serviço = soma das tintas de cada página
```

Uma página em quadricromia gasta quatro chapas de metal; uma em GRAY,
uma. No caminho curto a conta tem de ser a que **a gravadora** vai fazer,
e é por isso que a tinta ali se conta sem o perfil.

Página em chapas de tamanhos diferentes no mesmo arquivo não vira serviço
cobrável sozinho: vira pendência. Ver a skill `gerempre`.

## A pergunta certa, feita à fonte certa — 15/09/2026

Esta seção é o resumo do que custou mais caro nesta skill. São **duas
perguntas diferentes**, e confundi-las gerou três chapas erradas em
quatro dias.

```
1. "isto vale UMA chapa?"          -> pagina_de_uma_cor
2. "em QUE CANAL a tinta está?"    -> preto_so_no_K
```

A primeira decide quantas chapas a OS cobra. A segunda decide **como a
chapa é gerada**, e é ela que se engana com o perfil.

**A segunda pergunta só pode ser feita ao arquivo — nunca ao perfil.**
Lida com o perfil embutido, ela responde errado, e responde errado de
dois jeitos diferentes conforme a arte:

| | com o perfil | sem o perfil | o que acontecia |
|---|---|---|---|
| **chapado** (`Flor Bela`) | C=M=Y=K=0,3867 | C=M=Y=0 · K=0,3867 | os quatro **iguais** — passava por preto composto, e a detecção funcionava **por acidente** |
| **meio-tom** (`GRADE 3386` verso) | C 0,1393 M 0,1435 Y 0,1435 K 0,0634 | C=M=Y=0,001 · **K 0,4131** | os canais **desiguais** — não passava por nada, e saíram quatro chapas |

No chapado a conta do perfil é linear e espalha o preto por igual; no
meio-tom ela é não linear. Foi por isso que o caso da SOLIDA funcionou e
o da VIVA não, e foi por isso que o conserto de 14/09 — feito olhando só
o chapado — não bastou.

→ Hoje `preto_so_no_K` roda **sempre** sobre a leitura crua, antes de
qualquer outra pergunta. Custa uma passada a mais do `inkcov` por
arquivo, **mais barata** que a com perfil: 0,9 s contra 2,3 s no próprio
`GRADE 3386`, porque não há conversão de cor a fazer.

→ O preto **composto** continua decidido pela leitura com perfil, e
continua preso a `CLIENTES_QUE_JUNTAM_PRETO_COMPOSTO`. Ali as quatro
tintas estão escritas dentro do arquivo, e fundir quatro chapas numa é
decisão bem mais delicada do que reconhecer preto que já é preto.

### O preto puro não tem lista de cliente

Regra do operador, 14/09/2026: *"todos os arquivos que vierem somente no
canal do preto faça assim, de todos os clientes"*.

Arte inteira no K é um **fato do arquivo**, não do cliente: seja quem for
que mandou, ela vale uma chapa e tem de sair com a porcentagem que
entrou. Por isso a porta do preto puro é a única das duas que não olha
quem mandou.

## Conferir a chapa de uma cor

A chapa de uma cor é a única que tem conferência de **tinta** — as outras
conferem medida e resolução. Ela compara o antes e o depois e **apaga a
chapa** se a porcentagem mudou.

Duas coisas que essa conferência aprendeu do jeito difícil:

**O máximo sempre dá 100%, e não prova nada.** As marcas de registro da
Corel são 100% das quatro tintas e atravessam o perfil intactas. A
conferência passava alegremente enquanto a arte saía com 87% de preto
onde o arquivo tinha 100%. Some o **chapado**: quantos mm² estão em 100%
de tinta. O perfil derrete essa área, e é ela que denuncia.

**Em 300 dpi, não em 60.** Vetor rasterizado em dpi baixo infla o traço
fino: a mesma arte dá 0,45 de razão em 60 dpi e passa folgado em 300.
Uma chapa correta chegou a ser recusada por causa disso.

**E jamais leia a origem pelo mesmo perfil que estraga a chapa.** Esse
foi o erro que me fez declarar *"a chapa está boa"* para uma chapa que
não estava: eu comparei a doença contra ela mesma. `-dUseFastColor=true`
dos dois lados, sempre.

### O que uma conferência boa parece

```
tinta antes  7,30%  (max 100,00%, chapado 159 mm2)
tinta depois 7,28%  (max 100,00%, chapado 160 mm2)
```

O máximo continua em 100% e o chapado não encolheu: o preto que era 100%
saiu 100%. Foi assim que o verso do `GRADE 3386` foi refeito — de
`/DeviceN` com quatro tintas para `/DeviceGray`, na mesma resolução
(20079 x 15748 px), de 4,9 MB para 1,5 MB, e a OS de 8 chapas para 5.
