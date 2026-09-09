# A planta do GEREMPRE

As 16 tabelas. Metade está vazia: a Finart usa o módulo de produção e
estoque, e o financeiro do GEREMPRE está desligado. Saber disso evita
procurar dado onde não há — e avisa se um dia começarem a usar.

Os números de linha são de setembro de 2026, na cópia de teste, e servem
de ordem de grandeza, não de verdade corrente. O banco é a fonte.

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

`GEN_OSCOD_ID` · `GEN_MOVCOD_ID` · `GEN_CLICOD_ID` · `GEN_FUNCOD_ID` ·
`GEN_CHACOD_ID` · e mais oito, um por tabela.

Ler com incremento zero é seguro e serve para conferir onde a numeração
está sem gastar um número.

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
