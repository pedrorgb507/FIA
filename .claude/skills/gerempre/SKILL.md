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
olhando, dita com todas as letras.

**Na máquina da Finart a chave já virou**, em 09/09/2026: o
`config_local.py` aponta para `ARTE-JUNIOR` e a FIA é o funcionário 32.
Cada OS que ela abre mexe em estoque de verdade, na hora. Antes de rodar
qualquer coisa que escreva, confira em qual banco você está — o
`config_local.py` fica fora do Git, então a mesma linha de código faz
coisas diferentes em máquinas diferentes. Ver `references/producao.md`.

A cópia já pagou por si duas vezes, encontrando defeitos que teriam
zerado estoque de verdade. Os dois estão em ARMADILHAS.

## Ninguém mais está entre o cliente e o estoque

Desde 09/09/2026 o arquivo que a SOLIDA posta no Teams chega na pasta do
dia **sozinho**, e o vigia o processa sem que ninguém tenha olhado. A OS
sai dali, e com ela a baixa de chapa.

Antes havia uma pessoa no meio: alguém baixava o arquivo, o salvava e via
o que estava entrando. Esse olhar não existe mais. Ao mexer em qualquer
coisa que escreva no GEREMPRE, conte com isto — **a distância entre um
cliente clicar "enviar" e o estoque andar é hoje de segundos, sem
supervisão.**

Duas defesas nasceram disso, e nenhuma deve ser afrouxada sem conversa:

- **o aviso da rajada** — o programa não é serviço, roda enquanto a janela
  está aberta. O que o cliente postar no fim de semana entra TODO na
  segunda de manhã, no minuto em que alguém abre o programa: sete
  arquivos são sete OS e sete baixas em poucos minutos. A ponte diz o que
  vai fazer e segura, para dar tempo de Ctrl+C;
- **a guarda da regravação** — ver a armadilha 9.

## Os três estados de uma OS

```
OSSIT = 0    PENDENTE    aberta, ainda não entregue
OSSIT = 1    ENTREGUE
OSSIT = 2    CANCELADA   o gatilho DEVOLVE a chapa ao estoque
```

Lido em produção em 10/09/2026: **19.535 OS em 1 e 42 em 0** — e as 42
eram exatamente as dos últimos dez dias, ainda abertas.

**Cuidado com a conclusão fácil, que já custou caro aqui.** Olhando só a
contagem, 1 parece "o valor normal" e foi assim que ele entrou fixo no
código, com o comentário *"19.078 das 19.122 OS usam 1"*. Mas elas estão
em 1 porque **já foram entregues**: quase todo serviço acaba entregue, e
o que se está medindo é o passado, não o padrão. Inferência de
sobrevivente. A conta certa é olhar as recentes.

O preço foi a OS 19603, aberta pela FIA em 09/09/2026: saiu **ENTREGUE
com três vagas**. Foi devolvida a pendente em 10/09, com o razão
conferido dos dois lados.

**A FIA só fecha com as QUATRO vagas** — regra do operador, dita em
10/09/2026. Faltando vaga, a OS fica pendente e uma pessoa fecha à mão
quando houver necessidade. Os dois erros não custam igual: deixar
pendente o que já saiu custa uma conferida de quem fecha o dia; dar por
entregue o que não saiu põe no faturamento um serviço que ninguém
entregou, e isso só aparece quando o cliente reclama.

Quem fecha é `entregar_os()`, e ele **confere as quatro vagas por conta
própria** — é a única porta para o valor ENTREGUE, e a trava não pode
morar no chamador.

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

### Editar uma OS APAGA e REFAZ todo o movimento dela

Lido no fonte do `TR_OS_BEFO` em 10/09/2026, e é a coisa mais importante
deste arquivo. Em **todo** insert ou update de OS normal, a primeira
coisa que ele faz é:

```sql
delete from mov where movnos = new.oscod;
```

E aí reinsere as vagas. Como o `TR_MOV_AFT` devolve o saldo a cada linha
apagada, o efeito é **rebobinar e reproduzir** o estoque inteiro daquela
OS, do zero, a cada gravação.

Duas consequências que mordem:

- **um `UPDATE` numa OS antiga mexe em estoque hoje**, mesmo que você só
  quisesse corrigir o título. Não existe "editar sem mexer no estoque";
- **o `MOVCOD` é queimado em cada volta.** O gerador está em 1.234.484
  para 131.502 movimentos vivos — nove em cada dez números já foram
  gastos e apagados por esse vaivém. Número de movimento não é sequência
  histórica, e não serve para contar nada.

### O caminho de volta existe no gatilho, e quase nunca correu

Quando uma OS passa a `OSSIT = 2` **ou** `OSTIPO = 4`, o mesmo gatilho
lança movimento **positivo**, com a observação
`CANCELAMENTO/REFAÇÃO OS : <n>` — devolvendo a chapa ao estoque.

Em 10/09/2026: **nenhuma OS estava em nenhum desses estados**, e só havia
6 movimentos de cancelamento em 131.502. Ou seja, é caminho real, que já
correu, e que **não tem exemplo vivo para conferir**. Mexeu nisso? Não há
dado de produção que sirva de gabarito — teste na cópia.

### O gatilho erra em silêncio quando a chapa não existe

```sql
update cha set chaqtd = chaqtd + new.movqtd
 where chacli = new.movcli and chacod = new.movcha;
```

Se não houver linha na `CHA` para aquele par **(chapa, dono)**, o
`UPDATE` não casa nada, não dá erro, e o movimento fica gravado sem que
o estoque ande. Em 10/09/2026 havia **24 movimentos assim**, de 131.502.

É o par que manda, não só o código: a mesma chapa com dono diferente é
outra linha de saldo.

## O razão

```
CHA.CHAQTD  =  SUM(MOV.MOVQTD)   daquela chapa, daquele dono
```

Conferido em **produção**, em 10/09/2026: **96 de 96 chapas batem, zero
divergência.** A chapa 98 tem 2.964 movimentos e bate no número. É a
ferramenta mais forte que existe aqui, e vale usá-la em três momentos:

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

Doze, todas cobradas em tempo, e três em estoque.

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

**6. TODO nome de metadado volta cortado em 10 letras — e isso mente.**
Não é só gerador: vale para tabela, coluna, gatilho e procedimento.
`GEN_OSCOD_ID` chega `GEN_OSCOD_` e dá "generator is not defined". Pior é
o silencioso: `SP_ESTOQUE2` chega `SP_ESTOQUE`, **idêntico** ao
`SP_ESTOQUE` de verdade, e uma varredura ingênua conclui que há dois
procedimentos com o mesmo nome em vez de dois procedimentos diferentes.
Aconteceu comigo em 10/09/2026, na primeira passada.
→ `CAST(RDB$<coluna>_NAME AS VARCHAR(31))` devolve o nome inteiro. Use
sempre, em qualquer consulta ao `RDB$`.

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

**9. Arte que volta abre OS de novo — e a proteção só cobria metade.**
A chave do registro é `nome|tamanho|data`. Arte regravada na pasta sem
mudar ganha chave nova, vale como serviço novo, e sai **outra OS com
outra baixa de chapa**. Foi o `49694 - Gaspar - colinha.pdf` em
08/09/2026: duas chapas idênticas byte a byte, 12 segundos entre as
chaves.

O conserto de então guardou um retrato do conteúdo para reconhecer a arte
de volta. Só que ele **só protege quem já o tem**: em 09/09/2026, 87 das
156 entradas eram anteriores ao retrato, e para elas a proteção não agia.
O `49695 - Radio Dente`, já gravado em 08/09, voltou pelo Teams e teria
aberto OS nova — com baixa de chapa de verdade, no estoque de verdade.

Agora, quando não dá para confirmar, o programa **para e pergunta** em vez
de chutar. Não pula por conta própria: pular arriscaria chapa faltando,
que é erro de gente, não de estoque.

→ Ao mexer no registro ou no vigia, saiba que essa guarda é o que separa
uma arte reenviada de uma segunda baixa. `SPEC-guarda-de-regravacao.md`
conta o caso inteiro.

**10. O banco não valida quase nada — quem valida é o Delphi.**
Em 303 colunas há **uma** chave primária, e ela está na `OSHIS`, que está
vazia. **Zero chaves estrangeiras.** Nenhuma restrição de verificação.

Isso quer dizer duas coisas, e as duas importam:

- o banco aceita quase tudo que você mandar. Não conte com ele para
  barrar bobagem — o `INSERT` errado entra calado;
- toda regra que não está nas 104 linhas dos seis gatilhos mora **dentro
  do `neogerempre.exe`**, compilado, sem fonte. Não há como lê-la: só
  observando o programa funcionar.

**11. 78% do movimento aponta para OS que não existe mais.**
`102.168 de 131.502`, em 10/09/2026. A `MOV` tem movimento desde
02/04/2015; a `OS` só guarda desde 06/06/2024, e a numeração já
reiniciou — a `MOV` cita 58.129 OS distintas, e existem 19.575.

Então: **`MOVNOS` não é ligação confiável para trás.** Relatório que
junte `MOV` com `OS` perde quatro quintos da história sem avisar. Para
somar estoque, use a própria `MOV`; a `OS` só serve para o período que
ela ainda cobre.

**12. Renomear um funcionário pode reescrever estoque.**
O `TR_FUN_BEF` propaga o nome novo para dentro da `OS`:

```sql
update os set osnven  = new.funnom where oscven  = old.funcod;
update os set osnoper = new.funnom where oscoper = old.funcod;
update os set osnconf = new.funnom where oscconf = old.funcod;
```

E **cada linha de OS que ele tocar dispara o `TR_OS_BEFO`**, que apaga e
refaz todos os movimentos daquela OS. Um `UPDATE` no cadastro de uma
pessoa pode acabar mexendo no inventário de centenas de OS.

Hoje é inofensivo por acidente: `OSCVEN`, `OSCOPER` e `OSCCONF` estão em
zero nas 19.577 OS, então o `WHERE` não casa nada. Mas isso é sorte, não
proteção — no dia em que alguém começar a preencher vendedor, a conta
muda.

→ Antes de renomear alguém, conte quantas OS os três campos alcançam. Se
não for zero, faça na cópia primeiro e confira o razão dos dois lados.

Foi assim que a FIA virou **FINART (FIA)** em 10/09/2026 — funcionário
32, cadastro na `FUN` e `GEREMPRE_RESPONSAVEL` mudados no mesmo dia,
porque deixar só um faria a OS dizer uma coisa e o Delphi outra.

## Onde está o resto

| | |
|---|---|
| skill `fechamento-arquivos-ctp` | de onde vem a OS: como a chapa é fechada e quantas o serviço gasta |
| `references/banco.md` | a planta: as 16 tabelas, os 6 gatilhos, os geradores, o que está morto |
| `references/os.md` | a OS campo a campo: as quatro vagas, o que é obrigatório, como se conta chapa |
| `references/producao.md` | o portão da virada para o banco de verdade |
| `references/refazer.md` | dá para fazer um sistema próprio? o que se perde, e como não perder |
| `ferramentas/varredura_gerempre.py` | refaz a planta a partir do banco, sem escrever nada |
| `src/finart_ctp/gerempre.py` | conectar, montar vaga, abrir OS, procurar se já foi lançado |
| `src/finart_ctp/fila.py` | a fila que junta quatro serviços e despacha |
| `src/finart_ctp/entrada_teams.py` | a ponte que trouxe o cliente para perto do estoque |
| `src/finart_ctp/os_impressa.py` | a folha do F10 - 1ª via de produção, no verso da prova |
| `src/finart_ctp/protocolo.py` | o protocolo do F12 - duas vias, valores e o estoque |
| `src/finart_ctp/config.py` | **preços, códigos de cliente e de chapa** |
| `SPEC-guarda-de-regravacao.md` | a armadilha 9 por inteiro, com os dois acidentes |
| `tests/test_gerempre.py` · `tests/test_fila.py` · `tests/test_fila_do_arquivo.py` | 58 testes, inclusive os dois defeitos de estoque |
| `tests/test_protocolo.py` | o papel do cliente, caso a caso |
| `tests/test_registro.py` | a guarda da armadilha 9, caso a caso |

Os preços ficam no `config.py` e não aqui: mudam, e duas cópias
envelhecem separadas. Saíram das OS de 2026, uma a uma, e o comentário de
lá conta de onde veio cada número.

## O princípio

O mesmo da FIA: entre errar sozinha e parar para perguntar, pare.

Aqui vale dobrado. Erro de chapa aparece na prova; erro de estoque só
aparece no inventário, meses depois, quando ninguém lembra mais o que
aconteceu.
