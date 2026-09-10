# A planta do GEREMPRE

As 16 tabelas. Metade está vazia: a Finart usa o módulo de produção e
estoque, e o financeiro do GEREMPRE está desligado. Saber disso evita
procurar dado onde não há — e avisa se um dia começarem a usar.

Os números de linha são de setembro de 2026, na cópia de teste, e servem
de ordem de grandeza, não de verdade corrente. O banco é a fonte.

Para refazer este retrato e ver o que mudou, sem escrever nada:

```
.venv\Scripts\python.exe ferramentas\varredura_gerempre.py C:\saida
```

## O tamanho de tudo

Varrido em **produção**, em 10/09/2026, com a trava de leitura do próprio
Firebird:

| | |
|---|---|
| tabelas | 16 — **9 com dado, 7 vazias** |
| colunas | 303 no total |
| **gatilhos** | **6, com 104 linhas de PSQL** |
| procedimentos | 11, todos consulta de relatório |
| geradores | 14 |
| chaves primárias | **1**, na `OSHIS`, que está vazia |
| **chaves estrangeiras** | **zero** |
| índices | 16 |
| visões | 0 |
| charset do banco | **NONE** — byte cru, por isso a conexão usa ISO8859_1 |

Vale reler esses números com calma. **A regra de negócio inteira da
empresa cabe em 104 linhas**, e só uma delas é substancial: o
`TR_OS_BEFO`. Os outros cinco gatilhos são o `+`/`−` do estoque e
propagação de nome.

E o banco **não exige quase nada**: uma chave primária numa tabela vazia,
nenhuma estrangeira. Tudo que não está nesses seis gatilhos é regra que
mora dentro do `neogerempre.exe`, compilado, sem fonte. Ver a armadilha
10 e `refazer.md`.

## Os seis gatilhos, e o que cada um faz

| gatilho | tabela | o que faz |
|---|---|---|
| `TR_OS_BEFO` | `OS` | **o coração**: total da OS, apaga-e-refaz o movimento, e o caminho de volta do cancelamento |
| `TR_MOV_BEF` | `MOV` | `chaqtd = chaqtd + movqtd` ao inserir |
| `TR_MOV_AFT` | `MOV` | `chaqtd = chaqtd - movqtd` ao apagar |
| `TR_FUN_BEF` | `FUN` | mudou o nome do funcionário? propaga para `OSNVEN`/`OSNOPER`/`OSNCONF` |
| `TR_PRO_BEF` | `PRO` | mudou o nome do serviço? propaga para `OSNESP1..4` |
| `TR_PRV_BEF` | `PRV` | mudou o nome do fornecedor? propaga para `OSNPR1..4` |

Os três últimos existem porque a `OS` guarda **código e nome** lado a
lado — dado desnormalizado de propósito, para o relatório não precisar de
junção. Quem refizer o sistema tem de decidir se mantém isso.

## Os onze procedimentos

Todos são montadores de consulta para os relatórios do Delphi, com
`EXECUTE STATEMENT` sobre texto concatenado. Nenhum guarda regra de
negócio.

```
SOMAREGISTROS · SP_CONSUMO_CHAPA · SP_ERROMAQ · SP_ESTOQUE ·
SP_ESTOQUE2 · SP_MOVIMENTACAO · SP_MOVIMENTACAO_PRODUTO ·
SP_REFACAO · SP_SERVICOPRESTADO · SP_SERVICOS · SP_SERVICOS_RESUMO
```

**Cuidado ao listar:** o nome volta cortado em 10 letras, então
`SP_ESTOQUE2` aparece como `SP_ESTOQUE` e some. É a armadilha 6.

## Em uso

| tabela | linhas | o que guarda |
|---|---|---|
| `OS` | 19.124 | ordem de serviço. 146 campos, até quatro serviços. Ver `os.md` |
| `MOV` | 131.499 | cada movimento de estoque de chapa |
| `CLI` | 165 | clientes: código, nome, contato, endereço, dados de faturamento |
| `CHA` | 96 | catálogo de chapas: nome, medida, preço mínimo, **saldo**, dono |
| `CAC` | 28 | permissões de acesso, por cargo |
| `PRO` | 14 | serviços: prova digital, fotolito, verniz, plástico, BOPP, frete |
| `CAR` | 13 | cargos: recepcionista, vendedor, operador de bureau... |
| `FUN` | 10 | funcionários, com usuário e senha em texto puro |

## Vazias

`CHE` cheques · `CTA` contas · `FIN` financeiro · `EST` estoque (outra
tabela, não usada) · `MAQ` máquinas · `OSHIS` histórico da OS · `PRV`
fornecedores · `BKP` uma linha só, o registro do último backup

## A CHA, por dentro

É o catálogo e o saldo ao mesmo tempo — por isso o razão se mede nela.

| campo | |
|---|---|
| `CHACOD` | o código, que a OS referencia em `OSESP<n>` |
| `CHANOM` | `SOLIDA FT4`, `510X400 - 0,15` |
| `CHAALT` / `CHALAR` | a medida, em mm |
| `CHAMIN` | preço mínimo — referência, não o preço praticado |
| `CHAQTD` | **o saldo**, mantido pelos gatilhos da MOV |
| `CHACLI` | o dono. Vazio quer dizer chapa da Finart |

Chapa com dono é chapa que o cliente traz e a Finart guarda. Os códigos
que a FIA usa estão em `config.py`, em `GEREMPRE_CHAPAS`.

## A MOV, por dentro

| campo | |
|---|---|
| `MOVCHA` | qual chapa |
| `MOVCLI` | de quem é o estoque. **Zero é a Finart** |
| `MOVQTD` | negativo na saída, positivo na entrada |
| `MOVSDA` / `MOVENT` | a mesma quantidade, positiva, em saída ou entrada |
| `MOVNOS` | a OS que gerou o movimento |
| `MOVFUN` | o funcionário |

Os gatilhos: `TR_MOV_BEF` faz `chaqtd = chaqtd + new.movqtd` ao inserir,
e `TR_MOV_AFT` faz `chaqtd = chaqtd - old.movqtd` ao apagar. É por isso
que apagar uma OS devolve o estoque — e por isso que um `movqtd` nulo
apaga o saldo.

## Os geradores

O próximo código sai daqui, do mesmo lugar de onde o programa tira:

```sql
SELECT GEN_ID(GEN_OSCOD_ID, 1) FROM RDB$DATABASE   -- avanca e devolve
SELECT GEN_ID(GEN_OSCOD_ID, 0) FROM RDB$DATABASE   -- so le, nao avanca
```

Ler com incremento zero é seguro e serve para conferir onde a numeração
está sem gastar um número. Em 10/09/2026, em produção:

| gerador | valor | |
|---|---|---|
| `GEN_OSCOD_ID` | 19.604 | a próxima OS |
| `GEN_MOVCOD_ID` | **1.234.484** | para 131.502 movimentos vivos |
| `GEN_CLICOD_ID` | 528 | para 166 clientes |
| `GEN_CHACOD_ID` | 103 | |
| `GEN_FUNCOD_ID` | 32 | a FIA é o último |
| `GEN_PROCOD_ID` | 14 | |
| `GEN_CARCOD_ID` | 13 | |
| `GEN_CHECOD_ID` · `GEN_CTACOD_ID` · `GEN_ESTCOD_ID` · `GEN_FINCOD_ID` · `GEN_MAQCOD_ID` · `GEN_PRVCOD_ID` | 0 | os módulos desligados |
| `OS_ORDEM` | 0 | |

**O `GEN_MOVCOD_ID` conta uma história:** 1,23 milhão de números gastos
para 131 mil movimentos que sobreviveram. Nove em cada dez foram criados
e apagados pelo apaga-e-refaz do `TR_OS_BEFO`, que roda a cada gravação
de OS. `MOVCOD` não é sequência histórica e não serve para contar nada.

## A OS por dentro: 146 campos, 116 vivos

Em 19.575 ordens, **30 campos nunca receberam um valor**:

```
OSNOPER  OSNCONF  OSPOS1..4  OSNEG1..4  OSPRO1..4  OSPRVL1..4
OSNPR1..4  OSLIN4  OSOBS2  OSEOBS  OSFFAX  OSFREP  OSTMP
OSEND_CON  OSRESPID
```

Repare que os campos de **fornecedor** (`OSPRO`, `OSPRVL`, `OSNPR`) estão
todos mortos — combina com a `PRV` vazia e com o `TR_PRV_BEF` que nunca
teve o que propagar. Um sistema novo não precisa deles.

## A história não fecha para trás

| | |
|---|---|
| `MOV` | movimento desde **02/04/2015** |
| `OS` | ordem desde **06/06/2024** |
| OS distintas citadas na `MOV` | 58.129 |
| OS que existem | 19.575 |
| **movimentos apontando para OS ausente** | **102.168 de 131.502 — 78%** |

A `OS` foi expurgada em algum momento e a numeração reiniciou. Portanto:
**`MOVNOS` não liga para trás.** Relatório que junte `MOV` com `OS` perde
quatro quintos da história sem avisar. Para somar estoque, use a própria
`MOV`.

## Quem guarda BLOB

Só campos de observação, e quase todos em tabela vazia. Nas que têm dado:
`CAR.CAROBS` (13 linhas), `FUN.FUNOBS` (10) e `PRO.PROOBS` (14). Trinta e
sete linhas no total — para migração, é nada.

## O U: não é o banco vivo

O programa mora em `\\servidor\NeoGerempre`, mapeado como `U:`, e dentro
dele há um `bdados\neobdados.fdb` — **parado em 24/08/2026**, quando a
empresa mudou o banco de máquina. O Firebird de `servidor` continua no ar
servindo essa cópia velha, então ela abre normalmente e não avisa nada.

O banco vivo é o de `ARTE-JUNIOR`, e quem diz isso é o próprio
`U:\config.txt`, que é o arquivo que o `neogerempre.exe` lê ao abrir:

```
Database=ARTE-JUNIOR/3050:C:\NeoGerempre\bdados\neobdados.fdb
```

Como se distingue, em dez segundos: as OS por dia. O de ARTE-JUNIOR
recebe trabalho todo dia útil; o do U: parou no dia 24 de agosto, no meio
do expediente.

```sql
SELECT OSENTD, COUNT(*) FROM OS WHERE OSENTD >= '2026-08-20'
  GROUP BY OSENTD ORDER BY OSENTD
```

Na dúvida sobre caminho, `U:\config.txt` e `U:\config2.txt` são a fonte —
é de lá que o programa dos operadores tira o dele, e é por isso que todo
mundo enxerga o banco certo mesmo abrindo o exe do compartilhamento.

## Como olhar o banco sem estragar nada

```python
import sys; sys.path.insert(0, "src")
from finart_ctp import gerempre
con = gerempre.conectar()      # levanta SemLigacao se nao der
cur = con.cursor()
```

Servidor, caminho, usuário e senha ficam no `config.py`, seção GEREMPRE,
e podem ser trocados por máquina no `config_local.py`.

O servidor de teste sobe assim, e às vezes precisa disso quando começa a
recusar conexão sem motivo aparente:

```
C:\GEREMPRE FIA TESTE\FIREBIRD\Firebird_1_5\bin\fbserver.exe -a
```

A cópia do programa Delphi também aponta para o teste: `config.txt` e
`config2.txt`, dentro de `C:\GEREMPRE FIA TESTE`. Os originais, que
apontavam para produção, estão guardados ao lado com `.ANTES_DA_FIA` no
nome. Quem abrir aquele executável vê dado de teste, e é essa a intenção.
