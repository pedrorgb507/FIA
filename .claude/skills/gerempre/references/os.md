# A OS por dentro

Cabeçalho, mais **quatro vagas de serviço**. Lido da OS 19140, que um
operador abriu à mão.

## O cabeçalho

```
OSCOD        do gerador GEN_OSCOD_ID
OSCLI        codigo do cliente        OSNCLI   nome, copiado do cadastro
OSCON        contato                  OSTEL    telefone
OSENTD       data de entrada          OSTIME   hora        OSENTG   entrega
OSECL        de qual estoque sai a chapa do cliente
OSRESP       nome de quem abriu       OSUSR_ALT  codigo dele
OSVTOT       total, calculado pelo gatilho a partir dos quatro OSVLU
```

`OSECL` fica com o código do cliente mesmo quando a chapa é própria — as
OS que os operadores abrem fazem assim, e o gatilho ignora esse campo no
caminho da chapa própria.

**Sete campos são obrigatórios**, e faltando um o banco recusa a gravação
inteira: `OSCOD`, `OSSIT`, `OSTIPO`, `OSCLI`, `OSCVEN`, `OSCOPER`,
`OSCCONF`. Os três últimos são vendedor, operador e conferente — nas
19.124 OS que existem estão todos em zero, ninguém preenche, mas não
aceitam nulo. `OSSIT` vale 1 em 19.078 delas.

## Cada vaga

```
OSTIT<n>      49348 - BASE_CALL. 2027 - LUS CONTABILIDADE
OSESP<n>      98              OSNESP<n>    SOLIDA FT4
OSMON<n>      F4              OSALT / OSLAR   510 / 400
OSLAN<n>      4               quantas CHAPAS, nao quantos arquivos
OSCOR<n>      1               cores da frente
OSCOR<n><n>   0               cores do VERSO
OSUNIT<n>     9,00            OSVLU<n>     36,00
RBCHAPA<n> / RBCHAPAPRO<n>    de quem sai a chapa
```

`OSMON` é `F4` até 560 mm de maior lado, `F2` acima disso.

## Como se conta chapa

O preço é por chapa de metal, e quadricromia gasta quatro. Então:

```
OSLAN = paginas x tintas
```

Uma página em CMYK dá 4. Uma em GRAY dá 1. Frente e verso em CMYK dá 8.
É o que a FIA já mede em cada arte, então o número vem pronto.

E o gatilho faz `movqtd = OSLAN × (OSCOR + OSCOR<n><n>)` — com as cores
da frente em 1 e as do verso em 0, o movimento sai igual ao `OSLAN`.

## As quatro vagas

Os operadores enchem as quatro: das 1.877 OS da Solida, **1.531 usam as
quatro** e só 97 usam uma. A FIA faz igual — junta até quatro do mesmo
cliente e aí abre; com uma, duas ou três, espera o dia seguinte, porque
não se abre OS pela metade só porque o dia acabou.

Uma OS é de um cliente só. Misturar faturaria um no outro.

## O título é o nome do arquivo

Em caixa alta. Conferido em 330 arquivos de agosto:

```
arquivo   49914 - Heineken - display table top.pdf
OSTIT     49914 - HEINEKEN - DISPLAY TABLE TOP
```

Vale para todos os clientes, inclusive a VOPRIX, cujos nomes vêm com
sublinhado: `TIMBRADO_21X29,7_4_0_DRA_SUZANA_NOVAIS_NEUROLOGIA_08_09`.

Cabe 50 letras, e o corte é no fim — o que faz a data sumir dos nomes
compridos da VOPRIX, que a trazem no final.

## A OS também se abre à mão

É normal outro operador lançar o serviço antes. Antes de abrir, procure o
título nas quatro vagas das OS que já existem: `ja_esta_em_os()`, em
`gerempre.py`, faz isso ignorando espaço, traço e caixa.

Faturar duas vezes a mesma chapa é pior do que não faturar.

## Dois arquivos com a mesma OS

Aconteceu: `49728 - EDNA - COLINHAS 4MOD` e `49728 - EDNA - COLINHAS 4MOD
1`. Podem ser dois serviços cobrados separados, ou um trabalho partido em
dois arquivos — e a diferença é o dobro do valor. Não há regra: o
operador decide caso a caso, então os dois param e viram pendência.
