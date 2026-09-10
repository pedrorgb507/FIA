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
aceitam nulo.

**`OSSIT` não é sempre 1.** Ele vale 1 na esmagadora maioria porque **1 é
ENTREGUE**, e quase todo serviço acaba entregue — a contagem mede o
passado, não o padrão. Uma OS nova nasce em **0**, pendente. A skill tem
a história inteira, e ela custou uma OS.

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

Os operadores enchem as quatro: das 2.183 OS da Solida, **72% usam as
quatro**. A FIA faz igual, e **sem esperar**: abre na primeira arte do
dia e vai completando conforme as outras fecham — assim cada arquivo já
sai com o número da OS impresso no verso da prova, que é o que o operador
precisa na mão.

**Mas quatro vagas é norma da SOLIDA, não de todo mundo.** Medido em
10/09/2026, sobre as OS entregues:

| cliente | o que a maioria usa |
|---|---|
| SOLIDA | 4 vagas (72%) |
| VIVA | **3 vagas** (58%) |
| VOPRIX · EMPORIO · CREATIVE · FIALHO | **1 vaga** (37% a 48%) |

Por isso a OS só é dada por ENTREGUE com as quatro cheias, e o resto fica
pendente para uma pessoa fechar: aplicar "espere as quatro" a quem
normalmente usa uma deixaria a OS aberta para sempre.

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

## Os papéis que saem de uma OS

Dois, e o GEREMPRE imprime os dois de dentro do exe Delphi. A FIA
desenha os dois aqui, pela mesma razão: tirar de lá exigiria abrir o
programa e apertar tecla, uma janela na tela no meio do trabalho de
alguém. O conteúdo está todo no banco.

| tecla | papel | quem desenha | mostra dinheiro? |
|---|---|---|---|
| **F10** | 1ª via de produção, no verso da prova | `os_impressa.py` | **não** — o papel anda pela oficina |
| **F12** | protocolo de entrega, o cliente assina | `protocolo.py` | **sim** — é o recibo |

Os dois foram copiados de impressos de verdade, campo por campo: a folha
do F10 da OS 19569, e o protocolo da OS 19605, impresso pelo operador em
10/09/2026.

### O protocolo, por dentro

- **duas vias na mesma folha**, a segunda 467 unidades abaixo — a do
  cliente e a da casa, para destacar;
- os **quatro blocos de produto saem sempre**, cheios ou vazios; vaga
  vazia mostra os rótulos e `0,00`;
- **o ESTOQUE embaixo**, listando só as chapas que **aquela OS** usou,
  com o saldo de agora: *"você gastou isto, sobrou aquilo"*;
- **VENDEDOR sai vazio** — é o vendedor que atendeu, e a FIA não vende.

Três coisas que só o papel de verdade revelou, e que a leitura do
relatório sozinha não teria dado:

**O número na frente do PRODUTO é a QUANTIDADE de chapas (`OSLAN`), e
não a vaga.** No primeiro modelo lido — a OS 16577, da ZAP — a vaga 1
gastava 1 chapa, e os dois números calhavam de ser iguais. A OS 19605
desfez a dúvida: as quatro vagas começam com `4 -`, porque cada uma
gasta quatro chapas de metal.

**O ENDEREÇO vem da tabela `CLI`, não da OS.** A OS tem campos próprios —
`OSEND_END`, `OSEND_BAI`, `OSEND_CID` — e eles estão **vazios nas 19.577
que existem**. Ninguém preenche. O feitio do papel deles é
`endereço - bairro - cidade - CEP: nnn - TEL: nnn`.

**A grade não é enfeite.** A primeira versão do protocolo saiu com o
texto todo no lugar certo e sem uma linha sequer — e o operador não
reconheceu como sendo o papel dele.

### Como se lê um relatório do GEREMPRE

Os `.rpf` da pasta do programa são relatórios **já renderizados**, no
formato `RLGraphicStorage` do ReportBuilder. Dão as posições exatas sem
precisar abrir o Delphi:

```
[x:int32][y:int32][2 bytes][tamanho:int32][texto]
```

e o retângulo da célula fica **36 bytes antes** do tamanho, como quatro
`int32`: esquerda, topo, direita, base. As coordenadas estão em 96 dpi —
210 mm dão 794 unidades.

Foi de `U:\ZAP PROT ENTREGA.rpf` que saíram os 104 campos do protocolo, e
foi do `.rpf` do F10 que saiu o logotipo da Finart.

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
