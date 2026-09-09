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

## Quadricromia fecha sozinha; o resto espera

Em quadricromia o caminho é sempre o mesmo. Fora dela a decisão muda de
trabalho para trabalho, e quem decide é gente.

`AVISAR_QUANDO_NAO_FOR_CMYK` — só para **VOPRIX, EMPORIO, VIVA e
CREATIVE**,
página que não use as quatro tintas **não fecha**: vira pendência com a
cobertura de cada tinta na tela, para alguém conferir. A prova sai do
mesmo jeito, e o PDF já convertido fica guardado na `PASTA_PENDENCIAS`,
para o trabalho da Corel não se perder.

**SOLIDA e FIALHO ficam fora das duas travas** — nem a de quadricromia
nem a do cinza. Arte de uma cor deles sempre fechou sozinha, e mudar isso
pararia serviço que hoje anda. No Fialho a razão é outra: a arte dele
chega pronta, no tamanho da chapa, e o que decide o que anda ali é o
formato, não a cor.

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
