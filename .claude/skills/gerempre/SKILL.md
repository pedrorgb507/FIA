---
name: gerempre
description: O GEREMPRE, sistema de ordem de servico e estoque da Finart, em Firebird 1.5. Use ao mexer em OS, estoque de chapa, faturamento de gravacao, preco de cliente, ou em qualquer coisa que leia ou escreva naquele banco.
---

# GEREMPRE

O programa que a Finart usa para ordem de serviço, estoque de chapa e
faturamento. Delphi antigo sobre **Firebird 1.5**, rodando no servidor
`ARTE-JUNIOR`. São 19.124 OS e 131.499 movimentos de estoque — a memória
da empresa.

A FIA abre OS ali para a gravação das chapas que fecha.

---

## A regra que vem antes de todas

**Trabalhe na cópia de teste. Nunca em produção.**

```
teste       127.0.0.1/3050:C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb
producao    ARTE-JUNIOR/3050:C:\NeoGerempre\bdados\neobdados.fdb
```

`GEREMPRE_DSN`, no `config.py`, aponta para o teste e é assim que ele vem
de fábrica. Apontar para produção é **decisão do operador**, tomada por
ele, com ele olhando. Nunca do agente, nunca "só para testar".

A cópia já pagou por si duas vezes: encontrou dois defeitos que teriam
zerado estoque de verdade. Estão descritos abaixo, em ARMADILHAS.

---

## Escrever aqui mexe em ESTOQUE

Não é anotação. A tabela `OS` tem um gatilho que movimenta inventário.

**`TR_OS_BEFO`** — antes de inserir ou alterar uma OS:

```sql
total = new.osvlu1 + new.osvlu2 + new.osvlu3 + new.osvlu4;
new.osvtot = total;

if ((new.rbchapa1 = 1) and (new.osesp1 > 0)) then
    insert into mov (...) values (..., new.osecl, new.osesp1,
                                  (new.oslan1*(new.oscor1+new.oscor11)), ...)
if ((new.rbchapapro1 = 1) and (new.osesp1 > 0)) then
    insert into mov (...) values (..., 0, new.osesp1, ...)
```

Os dois interruptores decidem **de quem sai a chapa**:

| campo | quando vale 1 | para onde vai a baixa |
|---|---|---|
| `RBCHAPA<n>` | o cliente traz a chapa | estoque **do cliente** (`movcli = OSECL`) |
| `RBCHAPAPRO<n>` | a Finart põe a chapa | estoque **da Finart** (`movcli = 0`) |

**`TR_MOV_BEF`** (antes de inserir em MOV) e **`TR_MOV_AFT`** (depois de
apagar) fecham o circuito:

```sql
update cha set chaqtd = chaqtd + new.movqtd where ...   -- ao inserir
update cha set chaqtd = chaqtd - old.movqtd where ...   -- ao apagar
```

### A invariante que serve de prova

```
CHA.CHAQTD  =  SUM(MOV.MOVQTD)  daquela chapa e daquele dono
```

Vale em **95 de 95** chapas com saldo, zero divergências — a chapa 98 tem
2.964 movimentos e bate no número. É a melhor ferramenta que existe aqui:

- **antes** de mexer, confira que bate. Se não bater, o saldo já mentia e
  o problema é outro;
- **depois** de mexer, confira de novo;
- se um saldo se perder, ele pode ser **reconstruído** pela soma dos
  próprios movimentos, sem inventar número. Foi assim que a chapa 103 foi
  devolvida a 157 depois de um erro.

---

## A planta

**Em uso**

| tabela | linhas | o que guarda |
|---|---|---|
| `OS` | 19.124 | ordem de serviço, **146 campos**, até 4 serviços |
| `MOV` | 131.499 | cada movimento de estoque de chapa |
| `CLI` | 165 | clientes — código, nome, contato, endereço |
| `CHA` | 96 | catálogo de chapas: nome, medida, preço mínimo, **saldo**, dono |
| `CAC` | 28 | permissões de acesso, por cargo |
| `PRO` | 14 | serviços: prova digital, fotolito, verniz, plástico, frete |
| `CAR` | 13 | cargos |
| `FUN` | 10 | funcionários, com usuário e senha |

**Vazias** — o módulo financeiro do GEREMPRE está desligado na Finart.
Saber disso evita procurar dado onde não há, e avisa se um dia começarem
a usar:

`CHE` cheques · `CTA` contas · `FIN` financeiro · `EST` estoque (outra
tabela, não usada) · `MAQ` máquinas · `OSHIS` histórico da OS · `PRV`
fornecedores · `BKP` só o registro do último backup

**Geradores de número** (é daqui que sai o próximo código, como o próprio
programa faz): `GEN_OSCOD_ID`, `GEN_MOVCOD_ID`, `GEN_FUNCOD_ID`,
`GEN_CLICOD_ID`, `GEN_CHACOD_ID` e mais oito.

---

## A OS por dentro

Cabeçalho, mais **quatro vagas de serviço**. Foi lido da OS 19140, aberta
à mão por um operador:

```
cabecalho   OSCOD (do gerador)   OSCLI + OSNCLI   OSCON, OSTEL
            OSENTD, OSTIME, OSENTG
            OSECL = de qual estoque sai a chapa do cliente
            OSRESP = nome de quem abriu    OSUSR_ALT = codigo dele

vaga <n>    OSTIT<n>    49348 - BASE_CALL. 2027 - LUS CONTABILIDADE
            OSESP<n>    98        OSNESP<n>   SOLIDA FT4
            OSMON<n>    F4        OSALT/OSLAR   510 / 400
            OSLAN<n>    4         quantas CHAPAS, nao quantos arquivos
            OSCOR<n>    1         cores da frente
            OSCOR<n><n> 0         cores do VERSO
            OSUNIT<n>   9,00      OSVLU<n>   36,00
            RBCHAPA<n> / RBCHAPAPRO<n>
```

**Campos obrigatórios** — o banco recusa a gravação inteira se faltar um:
`OSCOD`, `OSSIT`, `OSTIPO`, `OSCLI`, `OSCVEN`, `OSCOPER`, `OSCCONF`. Os
três últimos são vendedor, operador e conferente; nas 19.124 OS que
existem estão todos em **zero** — ninguém preenche, mas não aceitam nulo.

**Quantas chapas.** O preço é por chapa de metal, e quadricromia gasta
quatro. Então `OSLAN = páginas × tintas`, que é o que a FIA já mede em
cada arte: CMYK numa página dá 4, GRAY dá 1, frente e verso em CMYK dá 8.

**Os operadores enchem as quatro vagas.** Das 1.877 OS da Solida, 1.531
usam as quatro e só 97 usam uma. A FIA faz igual: junta até quatro do
mesmo cliente e aí abre; com uma, duas ou três, espera o dia seguinte.

**A OS também se abre à mão.** É normal outro operador lançar o serviço
antes. Antes de abrir, procure o título nas quatro vagas das OS que já
existem — faturar duas vezes a mesma chapa é pior do que não faturar.

**O título é o nome do arquivo em caixa alta.** Conferido em 330 arquivos
de agosto: `49914 - Heineken - display.pdf` vira
`49914 - HEINEKEN - DISPLAY`.

---

## As armadilhas

Sete. Todas custaram tempo, e duas custaram estoque.

**1. Conta com nulo dá nulo — e apaga saldo.**
`movqtd = oslan × (oscor + oscor<n><n>)`. Sem preencher as cores do
verso, a quantidade sai nula; `chaqtd = chaqtd + null` deixa **o estoque
da chapa nulo**. Aconteceu com as chapas 98 e 103. O mesmo vale para
`osvtot = osvlu1+2+3+4`: numa OS de um serviço só, as três vagas vazias
iam nulas e o total da OS saía nulo.
→ **Zere as quatro vagas antes de preencher.**

**2. `STARTING WITH` distingue maiúscula de minúscula.**
O GEREMPRE guarda o título em caixa alta. Procurar `48915 - Heineken` não
acha `48915 - HEINEKEN`. Pior: títulos que começam com número casavam por
acaso, escondendo o defeito.
→ Use `UPPER(OSTIT<n>) STARTING WITH ?` com o texto já em maiúscula.

**3. `OSTIT` cabe 50 letras e o Firebird não corta sozinho.**
Passar disso derruba a gravação inteira com erro de truncamento.
→ Corte em 50 antes de gravar.

**4. `TRIM` não existe no Firebird 1.5.**
Nem várias outras funções de texto. Escreva SQL de 2004 e faça o resto em
Python.

**5. `fbclient` de 32 bits não fala com Python de 64.**
Dá `WinError 193`. O cliente de 64 bits que funciona está em
`C:\GEREMPRE FIA TESTE\_firebird15\fbclient64.dll` — é de uma versão nova
do Firebird e conversa bem com o servidor 1.5.

**6. Nome de metadado volta cortado em 10 letras.**
`GEN_OSCOD_ID` chega como `GEN_OSCOD_`, e usar assim dá "generator is not
defined". O padrão dos nomes é `GEN_<X>COD_ID` — leia da fonte de um
gatilho quando precisar do nome exato.

**7. A tabela `FUN` guarda senha em TEXTO PURO.**
Quem abre o banco lê a senha de todo mundo. **Não copie senha para
arquivo nenhum, log nenhum, nem para esta skill.** Se precisar criar
usuário, prefira que uma pessoa crie pela tela do programa.

---

## Como se conecta

```python
from finart_ctp import gerempre
con = gerempre.conectar()      # levanta SemLigacao se nao der
```

Servidor, caminho, usuário e senha estão em `config.py`, na seção
GEREMPRE, e podem ser trocados por máquina no `config_local.py`. **Não
repita credencial aqui.**

O servidor de teste sobe assim, e às vezes precisa disso quando começa a
recusar conexão sem motivo:

```
C:\GEREMPRE FIA TESTE\FIREBIRD\Firebird_1_5\bin\fbserver.exe -a
```

A cópia do programa também aponta para o teste: `config.txt` e
`config2.txt` dentro de `C:\GEREMPRE FIA TESTE`. Os originais, que
apontavam para produção, estão guardados ao lado com `.ANTES_DA_FIA` no
nome.

---

## Onde está o código

| | |
|---|---|
| `src/finart_ctp/gerempre.py` | conectar, montar vaga, abrir OS, procurar se já foi lançado |
| `src/finart_ctp/fila.py` | a fila que junta quatro serviços e despacha |
| `src/finart_ctp/config.py` | **preços, códigos de cliente e de chapa** — a fonte da verdade |
| `tests/test_gerempre.py` | 19 testes, inclusive os dois defeitos de estoque |
| `tests/test_fila.py` | 17 testes da fila |

Os preços não estão nesta skill de propósito: mudam, e duas fontes de
verdade envelhecem separadas. Eles foram levantados das OS de 2026, uma a
uma, e o comentário no `config.py` conta de onde saiu cada número.

---

## Antes de apontar para PRODUÇÃO

Isto é um portão, não uma receita. **A decisão é do operador.**

```
[ ] o razao bate em todas as chapas, antes de comecar
[ ] a FIA existe no cadastro de funcionarios da producao,
    criada por uma pessoa, com senha que nao seja 0000
[ ] os codigos de cliente e os precos foram conferidos contra
    a producao, e nao contra a copia de 24/08
[ ] o operador acompanhou as primeiras OS, uma a uma
[ ] existe caminho de volta: como apagar uma OS errada e
    devolver o estoque, testado antes de precisar
[ ] o operador disse, com todas as letras, para virar a chave
```

Se qualquer linha estiver em branco, continue no teste. Uma OS que falta
dá trabalho; uma OS errada mexe no que a empresa tem e no que ela fatura.

---

## O princípio

O mesmo da FIA: **entre errar sozinha e parar para perguntar, pare.**

Aqui vale dobrado. Um erro de chapa se vê na prova; um erro de estoque só
aparece no inventário, meses depois, quando ninguém lembra mais o que
aconteceu.
