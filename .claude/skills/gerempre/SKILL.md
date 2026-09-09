---
name: gerempre
description: Escrever no GEREMPRE mexe em ESTOQUE - e o banco de ordem de servico e inventario da Finart, em Firebird 1.5. Use sempre que aparecer OS, ordem de servico, baixa de chapa, faturamento de gravacao, preco de cliente, o programa neogerempre, ou qualquer consulta aquele banco, inclusive leitura - e ali que moram as armadilhas.
---

# GEREMPRE

Ordem de serviço, estoque de chapa e faturamento da Finart. Delphi antigo
sobre Firebird 1.5, no servidor `ARTE-JUNIOR`. 19 mil OS, 131 mil
movimentos de estoque: a memória da empresa.

A FIA abre OS ali para a gravação das chapas que fecha.

## Trabalhe na cópia de teste

```
teste       127.0.0.1/3050:C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb
producao    ARTE-JUNIOR/3050:C:\NeoGerempre\bdados\neobdados.fdb
```

`GEREMPRE_DSN`, no `config.py`, aponta para o teste, e é assim que ele vem
de fábrica. Apontar para produção é decisão do operador — dele, com ele
olhando, dita com todas as letras. Ver `references/producao.md` quando
essa hora chegar.

A cópia já pagou por si duas vezes, encontrando defeitos que teriam
zerado estoque de verdade. Os dois estão em ARMADILHAS.

## Escrever mexe em estoque

A tabela `OS` tem um gatilho, `TR_OS_BEFO`, que lança movimento de
inventário assim que a OS entra. Dois interruptores decidem de quem sai a
chapa:

| campo | quando vale 1 | a baixa vai para |
|---|---|---|
| `RBCHAPA<n>` | o cliente traz a chapa | estoque **do cliente** (`movcli = OSECL`) |
| `RBCHAPAPRO<n>` | a Finart põe a chapa | estoque **da Finart** (`movcli = 0`) |

Os gatilhos da `MOV` fecham o circuito — `chaqtd + movqtd` ao inserir,
`chaqtd - movqtd` ao apagar.

Trocar os dois interruptores dá baixa no cliente errado, ou deixa de dar
baixa na Finart. Confira contra uma OS que um operador abriu à mão para o
mesmo cliente: os campos têm de sair iguais, menos o título e quem abriu.

## O razão

```
CHA.CHAQTD  =  SUM(MOV.MOVQTD)   daquela chapa, daquele dono
```

Vale em 95 de 95 chapas com saldo — a chapa 98 tem 2.964 movimentos e
bate no número. É a ferramenta mais forte que existe aqui, e vale usá-la
em três momentos:

- **antes** de mexer: se o razão já não bate, o saldo mentia antes de
  você chegar, e o problema é outro;
- **depois** de mexer: o saldo tem de ter andado exatamente o que a OS
  pedia, nem mais nem menos;
- **para reparar**: um saldo perdido se reconstrói pela soma dos próprios
  movimentos, sem inventar número. Foi assim que a chapa 103 voltou a 157
  depois de um erro.

Mexeu no banco e não conferiu o razão dos dois lados? O trabalho não
acabou.

## Armadilhas

Oito, todas cobradas em tempo, e duas em estoque.

**1. Conta com nulo dá nulo, e nulo apaga saldo.**
`movqtd = oslan × (oscor + oscor<n><n>)`. Sem preencher as cores do
verso, a quantidade sai nula; `chaqtd + null` deixa o estoque da chapa
**nulo**. Aconteceu com as chapas 98 e 103. O mesmo vale para
`osvtot = osvlu1+2+3+4`: numa OS de um serviço só, as três vagas vazias
iam nulas e o total da OS saía nulo.
→ Preencha as quatro vagas com zero antes de pôr conteúdo em qualquer
uma.

**2. `STARTING WITH` distingue maiúscula.**
O GEREMPRE guarda título em caixa alta, então `48915 - Heineken` não acha
`48915 - HEINEKEN`. Pior: títulos que começam com número casavam por
acaso, escondendo o defeito.
→ `UPPER(OSTIT<n>) STARTING WITH ?`, com o texto já em maiúscula.

**3. `OSTIT` cabe 50 letras, e o Firebird não corta sozinho.**
Passar disso derruba a gravação inteira com erro de truncamento.
→ Corte em 50 antes de gravar.

**4. Firebird 1.5 é de 2004.**
Sem `TRIM`, sem várias funções de texto. Escreva SQL da época e faça o
resto em Python.

**5. `fbclient` de 32 bits não fala com Python de 64.**
Dá `WinError 193`. O cliente que funciona está em
`C:\GEREMPRE FIA TESTE\_firebird15\fbclient64.dll` — é de uma versão nova
do Firebird e conversa bem com o servidor 1.5.

**6. Nome de metadado volta cortado em 10 letras.**
`GEN_OSCOD_ID` chega como `GEN_OSCOD_`, e usar assim dá "generator is not
defined". O padrão é `GEN_<X>COD_ID`; para o nome exato, leia a fonte de
um gatilho que o use.

**7. Ler produção com trava de verdade — e testar a trava direito.**
`isolation_level=fdb.ISOLATION_LEVEL_READ_COMMITED_RO` faz o próprio
Firebird recusar escrita, com SQLCODE -817, e não depende de você lembrar
de não escrever. Mas o teste da trava precisa de um `UPDATE` que **case
uma linha**: com `WHERE` que não acha nada, o Firebird devolve sucesso sem
tentar escrever, e o teste passa sem provar coisa alguma. Serve
`UPDATE CHA SET CHAQTD = CHAQTD WHERE CHACOD = 98` — casa uma linha, não
muda valor, e a `CHA` não tem gatilho.

**8. A tabela `FUN` guarda senha em texto puro.**
Quem abre aquele banco lê a senha de todo mundo. Senha mora no
`config_local.py`, fora do Git, e em lugar nenhum além dele. Precisando
de usuário novo, peça a uma pessoa que crie pela tela do programa — o
cadastro feito por gente é o que vale.

## Onde está o resto

| | |
|---|---|
| `references/banco.md` | a planta: as 16 tabelas, o que cada uma guarda, os geradores |
| `references/os.md` | a OS campo a campo: as quatro vagas, o que é obrigatório, como se conta chapa |
| `references/producao.md` | o portão da virada para o banco de verdade |
| `src/finart_ctp/gerempre.py` | conectar, montar vaga, abrir OS, procurar se já foi lançado |
| `src/finart_ctp/fila.py` | a fila que junta quatro serviços e despacha |
| `src/finart_ctp/config.py` | **preços, códigos de cliente e de chapa** |
| `tests/test_gerempre.py` · `tests/test_fila.py` | 36 testes, inclusive os dois defeitos de estoque |

Os preços ficam no `config.py` e não aqui: mudam, e duas cópias
envelhecem separadas. Saíram das OS de 2026, uma a uma, e o comentário de
lá conta de onde veio cada número.

## O princípio

O mesmo da FIA: entre errar sozinha e parar para perguntar, pare.

Aqui vale dobrado. Erro de chapa aparece na prova; erro de estoque só
aparece no inventário, meses depois, quando ninguém lembra mais o que
aconteceu.
