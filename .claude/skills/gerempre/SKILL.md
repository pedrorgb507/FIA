---
name: gerempre
description: Escrever no GEREMPRE mexe em ESTOQUE - e o banco de ordem de servico e inventario da Finart, em Firebird 1.5 (arquivo ODS 10.3). Use sempre que aparecer OS, ordem de servico, baixa de chapa, faturamento de gravacao, preco de cliente, o programa neogerempre, backup ou mudanca de servidor do banco, ou qualquer consulta aquele banco, inclusive leitura - e ali que moram as armadilhas.
---

# GEREMPRE

Ordem de serviço, estoque de chapa e faturamento da Finart. Delphi antigo
sobre Firebird 1.5. Mudou de máquina duas vezes em dois dias — da
`ARTE-JUNIOR` para o `SERVIDOR` em 15/09/2026, e de lá para o
`EUDSON-PC` em 16/09, quando o Firebird 2.0 do servidor recusou o SQL do
próprio programa (armadilha 26). 19 mil OS, 25 mil movimentos de
estoque: a memória da empresa. Onde ele está **hoje**, e por quê, em
`references/servidor.md`.

A FIA abre OS ali para a gravação das chapas que fecha.

## Trabalhe na cópia de teste

```
teste       127.0.0.1/3050:C:\GEREMPRE FIA TESTE\bdados\neobdados.fdb
producao    SERVIDOR/3050:C:\NeoGerempre\bdados\neobdados.fdb
```

`GEREMPRE_DSN`, no `config.py`, aponta para o teste, e é assim que ele vem
de fábrica. Apontar para produção é decisão do operador — dele, com ele
olhando, dita com todas as letras.

**Na máquina da Finart a chave já virou**, em 09/09/2026: o
`config_local.py` aponta para produção e a FIA é o funcionário 32.
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

## "O GEREMPRE caiu" — qual dos dois caiu?

São **duas coisas com o mesmo nome**, e confundi-las já custou dois
diagnósticos errados na mesma semana:

- o **banco** — o servidor Firebird no SERVIDOR;
- o **programa** — o `neogerempre.exe` em Delphi, na máquina de quem
  está usando.

Quando alguém diz que caiu, o que caiu pode ser qualquer um dos dois, e
o remédio é oposto. **Meça antes de dizer.** Três conferências, em
ordem, e todas de leitura:

**1. Abra o banco, não a porta.** `telnet 3050` abrindo não quer dizer
nada — foi assim que eu disse *"não é o banco, é a rede"* e estava
errado. Abra uma ligação de verdade e faça uma consulta:

```python
con = fdb.connect(dsn=..., isolation_level=fdb.ISOLATION_LEVEL_READ_COMMITED_RO)
cur.execute("SELECT MAX(OSCOD) FROM OS")
```

Abrindo em décimos de segundo, **o banco está no ar** — e o problema é
do outro. Faça **meia dúzia seguidas**: queda intermitente aparece aí, e
uma só não distingue "no ar" de "no ar neste instante".

**2. O log de eventos do Windows, na máquina de quem reclamou.**

```powershell
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'} |
  Where-Object { $_.Message -match "neogerempre" }
```

Um crash do Delphi aparece como **duas** entradas com segundos de
diferença, e é uma queda só:

```
11:41:39  neogerempre.exe  KERNELBASE.dll  0x0eedfade   <- exceção Delphi não tratada
11:41:47  neogerempre.exe  ntdll.dll       0xc0000409   <- estouro, já durante a queda
```

**`0x0eedfade` é o código de exceção do Delphi.** Ele diz *"o programa
levantou um erro que ninguém tratou"* — e não diz qual. Sozinho, ele não
leva a lugar nenhum: o que leva é **o que a pessoa estava fazendo na
tela**, porque a exceção vem de uma ação. Pergunte.

**3. Conte as quedas, antes de chamar de recorrente.** Em 23/09/2026 o
programa caiu e a palavra foi *"caiu novamente"* — mas no log de 14 dias
havia **duas** entradas, e as duas eram daquela mesma queda. O
*"novamente"* era a lembrança da parada da manhã, que fora **do banco**.
Coisa diferente, mesmo nome.

E antes de culpar a FIA: veja a hora da última escrita dela no
`_log_ctp.txt`. Naquele dia foi a OS 19940, **doze minutos antes** da
queda — e ela fala com o banco pelo `fdb`, não pelo Delphi.

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

Vinte e tres, todas cobradas em tempo, e quatro em estoque.

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

**11. O movimento não ligava na OS — e isso foi consertado em
15/09/2026, com saldo de abertura.**

Era a armadilha mais cara de contornar. A `MOV` guardava movimento desde
02/04/2015; a `OS` só lembra de 06/06/2024, e a numeração já reiniciou.
Resultado medido: **106.619 das 131.594 linhas — 81% — apontavam para OS
que não existe mais.** Juntar `MOV` com `OS` perdia quatro quintos da
história sem avisar.

O corte foi feito. Das 105.848 linhas anteriores a 06/06/2024,
**105.848 eram órfãs — todas, sem exceção**: nenhuma podia ser rastreada
até um serviço. Elas foram apagadas e substituídas por **94 linhas de
saldo de abertura**, uma por par (chapa, dono), datadas de 05/06/2024.

```
MOV   131.594  ->  25.840 linhas      órfãs  81%  ->  3,3%
```

**Nenhum saldo mudou** — as 96 linhas da `CHA` saíram idênticas. O método
inteiro, e por que apagar sem compensar teria falsificado o estoque da
PRIME, está em `references/banco.md`.

→ Hoje `MOVNOS` **é** ligação confiável, com duas exceções: as 94 linhas
de abertura (`MOVNOS = 0`, observação `SALDO ANTERIOR ATE 05/06/2024`) e
uns 3% de órfãs legítimas do período novo. Para somar estoque continue
usando a própria `MOV` — ela é a fonte, e o razão prova isso.

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

**13. A trava dos testes só protege quem passa por ela.**
Em 09/09/2026 a bateria de testes abriu **quatro OS na produção de
verdade** e baixou quatro estoques, sem que ninguém mandasse. A causa:
os testes chamam `_processar_pdf` com arquivo de mentira, e o passo da
OS mora dentro dele; enquanto havia um defeito em outro lugar, esse passo
parava antes de chegar ao banco e a suíte parecia inofensiva. Consertado
o defeito, ela passou a escrever no banco de verdade — a segurança era um
acidente.

O conserto está em `tests/conftest.py`: um `autouse fixture` troca
`gerempre.conectar` por uma função que sempre levanta `SemLigacao`, e
troca `processador._os_do_arquivo` por um coto que devolve `(None,
False)`. **Isso só protege quem roda por `pytest`.** Um script solto —
`python algo.py` fora da suíte, para depurar um caso — importa
`finart_ctp.config`, que aplica o `config_local.py` por cima, e esse
arquivo aponta para o servidor de verdade (hoje o `SERVIDOR`) e para a
pasta de controle de verdade (`C:\Finart\_ctp_ia`). Nenhuma das duas
travas do `conftest` está lá.

Aconteceu de novo assim em 10/09/2026, depurando esta mesma armadilha:
um script solto chamou `_processar_pdf` de ponta a ponta para conferir a
conta de chapas, e o passo da OS rodou de verdade — leu o GEREMPRE de
produção (achou a OS já lançada, não cobrou de novo, sem dano) e **gravou
uma entrada de teste na fila real do dia**, `C:\Finart\_ctp_ia\_fila_os.json`.
Foi achada e tirada à mão, uma entrada, conferida pelo tamanho da chapa
sem ruído de ponto flutuante (as de verdade vêm de PDF medido; a de
teste tinha `510, 400` redondos).

→ Para depurar um caminho que passa por `_os_do_arquivo`, rode dentro do
`pytest` (a suíte já existe, ou escreva um teste novo) e use a fixture
`com_os` se precisar do passo de verdade — ela ainda não fala com o
banco, só reativa a chamada. **Nunca** um script solto: ele herda o
`config_local.py` inteiro, sem avisar.

**14. Cliente novo se cadastra lendo as OS dele — e o preço é o do uso
MAIS RECENTE, não o mais frequente.**
A AMÉRICA entrou em 10/09/2026 sem ninguém ditar número: cliente `58`, e
as chapas saíram das OS que a casa já tinha aberto para ela — `90
PM_52` 525×459 a R$ 8,00, `91 MOZP_FT2` 650×550 a R$ 12,00, `89 SM_74`
745×605 a R$ 12,00, todas com `RBCHAPA = 1` (chapa do cliente). Contar
frequência teria cobrado a MOZP a R$ 10,00 — são 272 lançamentos a 10
contra 112 a 12 —, mas **tudo desde agosto está em 12**. Preço velho
aparece mais vezes justamente porque é velho.

Três armadilhas no cadastro dela, e valem para qualquer cliente:

- há uma chapa **15** chamada `525X459` com `CHACLI = 0` — é **própria
  da Finart**, não da AMÉRICA. Mesma medida, dono errado: usá-la
  baixaria estoque alheio. **`CHA.CHACLI` diz de quem é a chapa; o nome
  não diz.**
- há **códigos velhos** para as mesmas máquinas (`67 PM 52`, `76 MOZP`,
  `10 SM 74`). Os que a casa usa hoje são os que aparecem nas OS mais
  recentes;
- o resto do cadastro dela — BOPP, VERNIZ, FOTOLITO, COMUNICAÇÃO VISUAL
  — é **acabamento**, não chapa de CTP. Medida `33x48` em centímetro
  denuncia: chapa é em milímetro.

→ Antes de cadastrar chapa de cliente novo em `GEREMPRE_CHAPAS`, leia as
últimas OS **dele** ordenadas por `OSCOD DESC`, e confira o dono em
`CHA`. O caso inteiro está em `imposicao/references/america.md`.

**15. `OSUSR_ALT` é quem ALTEROU POR ÚLTIMO, não quem abriu — e por isso
o filtro da FIA erra dos dois lados.**

Medido em produção, 11/09/2026. Entre as 54 OS pendentes há
`OSUSR_ALT 27` com `OSRESP 'FINART (FIA)'`, e `OSUSR_ALT 1` com
`OSRESP 'JOAOZIMAR'`: o código e o nome **discordam**. A FIA grava
sempre os dois juntos (`OSRESP = FINART (FIA)`, `OSUSR_ALT = 32`), então
um par desses só pode ter sido desfeito depois.

E foi: o `_log_ctp.txt` mostra `abri a OS 19642` e `abri a OS 19650` pela
própria FIA, em 11/09 — e hoje as duas estão com `OSUSR_ALT = 27`.
Alguém as abriu no Delphi e salvou; o campo passou a ser dele. *USR_ALT*
é **usuário da alteração**, e o nome já dizia.

O `os_com_vaga_livre` filtra por `OSUSR_ALT = 32` acreditando que aquilo
quer dizer "OS que a FIA abriu". Erra nos dois sentidos:

- **OS da FIA que um operador tocou** deixa de ser encontrada, e a FIA
  abre **outra OS para o mesmo cliente no mesmo dia** — chapa a mais e
  faturamento dobrado;
- **OS de outro** que a FIA tenha tocado passaria a parecer dela.

→ Para saber quem abriu, o campo confiável é **`OSRESP`** (é o que a FIA
escreve e o que o Delphi mostra), ou melhor ainda o próprio
`_log_ctp.txt`, que registra cada `abri a OS <n>`.

**16. O medo do nulo nas OS alheias não tem base no dado — o perigo é
outro.**

O `os_com_vaga_livre` recusa completar OS de outro operador com este
motivo escrito: *"numa OS aberta à mão pelo Delphi, uma vaga vazia pode
estar NULA - e conta com nulo dá nulo, que apagaria o saldo"*. Era
suposição. Contado em produção, 11/09/2026, nos campos que o gatilho
multiplica (`OSLAN`, `OSCOR`, `OSCOR<n><n>`, `OSVLU`, `OSESP`, as quatro
vagas):

```
todas as OS                            19.627    com nulo: 0
pendentes                                  54    com nulo: 0
pendentes de outros operadores             48    com nulo: 0
```

**Zero, em todas.** O Delphi preenche as vagas vazias com zero.

O perigo real é outro, e é de **gente, não de banco**: o Delphi guarda a
OS inteira na memória da tela. Se a FIA puser o item 2 enquanto alguém
está com ela aberta, essa pessoa salva **o que está vendo** — sem o item
novo — e o `TR_OS_BEFO` apaga e refaz todos os movimentos a partir do que
foi salvo. O item some, o estoque volta junto, e **ninguém vê erro
nenhum**.

**E não dá para detectar pela trava.** Sondei em produção com
`SELECT ... FOR UPDATE WITH LOCK` numa transação `NOWAIT`, uma OS por
vez, tudo em rollback: **as 300 OS mais recentes estavam livres**,
inclusive com uma delas aberta na tela de outra máquina. O Delphi **não
tranca a linha** enquanto a OS está aberta.

→ Como não dá para evitar nem para detectar na hora, o remédio é
**perceber depois** — ver a seção a seguir.

**17. `CHAMIN` parece "estoque mínimo" e é o PREÇO.**

Medido em produção, 14/09/2026. A chapa 98 tem `CHAMIN = 9` e as **843
OS** dela cobram 9,00, sem exceção; a 103 tem 13 e as 157 cobram 13,00.
FIALHO 10 e 15, VIVA 8,50 — os mesmos números de `GEREMPRE_CHAPAS`.

**Não existe estoque mínimo neste banco.** Ler `CHAMIN` como mínimo faria
um relatório dizer *"175 de mínimo 9, tudo bem"* na véspera de acabar —
e a SOLIDA gasta ~39 por dia útil, ou seja 175 são quatro dias.

→ Folga de estoque se mede em **dias**, pelo consumo de verdade
(`MOVSDA` dos últimos dias COM movimento; dia parado não entra na média).
`estoque.py` faz essa conta.

**18. `CHAINA = 1` é chapa desativada, e o saldo dela é fantasma.**

A SOLIDA tem oito chapas cadastradas e **duas em uso**. As seis paradas
carregam **15.267** de saldo — a 25 sozinha tem 8.662 — que não existe em
prateleira nenhuma. Somar o cadastro inteiro dá um estoque de mentira
que nunca acaba.

→ Filtre `CHAINA = 0`, e diga em algum lugar quanto ficou de fora: senão
a soma do GEREMPRE nunca bate com o relatório, e é o relatório que vai
parecer errado.

**19. Ligar pelo NOME do servidor custava 84 segundos. Por IP, 6
milésimos.**

Medido várias vezes na máquina da Finart, 14/09/2026:

```
resolver 'ARTE-JUNIOR' no Windows .....   0,017 s
TCP puro até 192.168.15.27:3050 .......   0,001 s
fdb.connect pelo NOME .................  84,203 s
fdb.connect pelo IP ...................   0,006 s
```

Não é DNS nem rede: é o cliente Firebird tentando outro caminho antes de
cair no TCP, e esperando esgotar. O preço era pago em **toda** ligação —
no log de 14/09, 86 e 87 segundos entre a chapa ficar pronta e a OS
sair.

*(A medida é de quando o banco morava na `ARTE-JUNIOR`. O defeito é do
cliente Firebird, não daquela máquina, e a defesa continua valendo com o
`SERVIDOR`: em 15/09/2026, já no servidor novo, a ligação leva 0,126 s.)*

`gerempre.conectar()` resolve o nome e liga pelo IP, caindo de volta no
nome se o IP falhar. O `GEREMPRE_DSN` continua escrito com o **nome**, de
propósito: IP fixo na configuração pararia a FIA calada no dia em que o
servidor trocasse de número.

→ Qualquer ferramenta nova que abra o banco por conta própria deve usar
`gerempre.conectar()`, e não um `fdb.connect` solto com o DSN do
`config_local.py` — senão volta a pagar os 84 segundos.

**20. Dois serviços da mesma peça viram UM SÓ no corte das 50 letras.**

14/09/2026, VOPRIX, mesmo dia:

```
Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Colegio_Voolivre
Envelope_Saco_23x31,5_4_0_Raphael _Brandao_Machado_Nelore_Bemach
```

As **50 primeiras letras são iguais**. A FIA lançou o Voolivre às 19:20 e,
às 19:23, casou o Nelore com o título cortado do outro: *"já está
lançado, não cobrei de novo"*. A gravação do Nelore saiu **sem cobrança**.

Dois remedios, os dois em `gerempre.py`:

- **`titulo_da_vaga`** — nome que não cabe vai PARTIDO: começo, `..` e as
  últimas PALAVRAS. `ENVELOPE_SACO_23X31,5_4_0_RAPHAEL..NELORE_BEMACH`.
  **Sempre** que passa de 50, nunca só quando há colisão à vista: um
  título que dependesse do que já está na OS mudaria conforme a hora do
  dia, e a FIA deixaria de reconhecer o que ela mesma lançou;
- **`ja_esta_em_os`** — bater só com as 50 primeiras letras **não é mais
  prova**. Vale quando o cliente põe a nossa OS na frente do nome
  (`CLIENTES_COM_OS_NO_NOME`: SOLIDA e EMPORIO), porque ali o começo
  carrega o número do serviço. Nos outros é **dúvida**, e ela vai na lista
  `duvidas` para quem chamou parar e perguntar.

Contado no registro: dos 295 arquivos fechados, **24 passam de 50
letras** — 12 VOPRIX (nome sem número nenhum) e 10 EMPORIO (número na
frente). E nas OS desde 01/06/2026, **12,6% dos títulos** chegaram ao
limite da coluna, com 46 títulos cheios repetidos no mesmo cliente.

→ Na dúvida entre cobrar em dobro e dar a gravação, **pare**. As 50
letras que o banco guarda não dizem qual dos dois é, e quem tem o
arquivo na mão resolve em dez segundos.

### Título igual em OUTRO DIA é OUTRO serviço — 23/09/2026

A regra acima, *"na dúvida entre cobrar em dobro e dar a gravação,
pare"*, continua valendo para a **dúvida**. Mas o **encontro certo** virou
outra coisa, e quem mudou foi o operador.

O caso: o `VALDINO - CHAPADO` da VIVA casou com a **OS 19704, de dias
atrás**, e a FIA escreveu no log *"JA ESTAVA na OS 19704 — não cobrei de
novo"*. Ele viu:

> *"essa OS é de dias atrás, o cliente pode muito bem pedir um serviço
> com o mesmo nome, e se você não colocar na OS, saímos no prejuízo pois
> não vai ser cobrado (...) quando for assim você deve colocar em uma
> nova OS (...) nos próximos você não pode não lançar"*

**Estava escrito no código exatamente o contrário** — *"faturar duas
vezes é pior do que não faturar"* —, e essa frase era a leitura de quem
escreveu, não dele. Ela só vale enquanto o nome identifica o serviço, e
**não vale**: a gráfica repete nome o tempo todo, e o mesmo cliente pede
o mesmo serviço de novo. A janela de `GEREMPRE_JANELA_DIAS = 30` estava
sendo lida como *"lançado há pouco"* quando ela só diz *"a empresa já
usou este nome"*.

**Como ficou:**

| a OS que casou é | a FIA |
|---|---|
| **de hoje** | não lança — alguém acabou de lançar à mão, e lançar de novo é cobrar duas vezes |
| **de outro dia** | **lança e cobra**, e escreve no log o número e a data da antiga |

O `ja_esta_em_os` passou a devolver a **data** de cada OS que casou (o
parâmetro `encontradas`), porque sem ela quem chama não distingue *"alguém
acabou de lançar"* de *"a empresa já usou este nome"*. Quem decide é o
`os_do_servico`.

**O recado no log não é formalidade** — é a única coisa que sobrou no
lugar da trava, e é por ele que uma pessoa descobre uma cobrança em dobro
de verdade. Por isso ele traz o número e a data da OS antiga, e há teste
exigindo os dois.

**Por que isto é caro dos dois lados, e por que ele escolheu este:**
chapa gravada sem cobrança **não dá erro em lugar nenhum** — a chapa sai,
a prova sai, o cliente recebe, e a falta só aparece no fechamento do mês,
se aparecer. Cobrança em dobro, ao contrário, o cliente reclama. Entre um
erro que alguém percebe e um que ninguém percebe, ele prefere o primeiro.

**21. O relatório de estoque do GEREMPRE conta pelos MOVIMENTOS, e casa
a chapa pelo NOME.**

Ele é um procedimento no próprio banco (`SP_ESTOQUE` / `SP_ESTOQUE2`,
código idêntico):

```
ESTOQUE ATUAL = SUM(movqtd) anterior a datai  +  entradas  -  saídas
casando  mov.movnch = cha.chanom     (o NOME, não o código)
```

A FIA lê `CHA.CHAQTD` pelo **código**. São dois caminhos independentes
para o mesmo número — e por isso comparar vale: chapa renomeada, nome
repetido, ou movimento gravado sem o saldo andar aparecem aí e em lugar
nenhum mais.

Conferido em produção em 14/09/2026, quatro dias (14, 11, 10 e 08/09):
os oito números bateram. `estoque.py` faz essa comparação em toda folha,
e diz na folha quando **não** conseguiu fazê-la — dar por conferido o que
não foi é o único jeito de a conferência piorar as coisas.

→ Com `datai = dataf = o dia`, o procedimento devolve o saldo no FIM
daquele dia: serve para conferir relatório retroativo, e a lista sai
trinta vezes menor (28 linhas contra 171).

→ **Refeito em 16/09/2026, já no Firebird 1.5 do EUDSON-PC**, e continua
batendo: `SP_ESTOQUE` devolve 76 e 48, `CHA.CHAQTD` pelo código devolve
os mesmos 76 e 48, `conferi_o_gerempre: True`. Onde cada um dos três
artefatos é gravado — e por que procurar o fechamento na raiz da pasta
do cliente não o encontra — está em `references/servidor.md`.

**22. Há UMA PÁGINA CORROMPIDA neste banco, e ela já quebrou um
procedimento.**

Descoberto em 14/09/2026:

```
SELECT ... FROM RDB$PROCEDURE_PARAMETERS
  → SQLCODE -902, "database file appears corrupt"
     "page 73787 is of wrong type (expected 5, found 8)"
```

O efeito visível: **`SP_ESTOQUE` não pode mais ser chamado** — a engine
não lê os parâmetros dele e responde *"procedure SP_ESTOQUE does not
return any values"*. O mesmo vale para `SP_MOVIMENTACAO` e
`SP_MOVIMENTACAO_PRODUTO`. Já `SP_ESTOQUE2`, `SP_CONSUMO_CHAPA` e
`SOMAREGISTROS` respondem normalmente.

**As tabelas de dados estão inteiras** — `MOV`, `OS`, `CHA` e as demais
`RDB$` leem sem erro. O estrago, até onde se mediu, está na página que
guarda parâmetros de procedimento.

→ Não tente consertar por conta própria. `gfix -mend` e um
backup/restore com `gbak` são escrita em produção e exigem o banco fora
do ar, com todo mundo desconectado — é decisão de quem cuida do
servidor. Código que precise de procedimento do banco deve tentar mais
de um nome e seguir sem ele quando nenhum responder.

→ **Ela sobreviveu à mudança de máquina**, em 15/09/2026: o arquivo foi
copiado para o SERVIDOR e o Firebird 2.0 dá o mesmo erro, na mesma
página. A corrupção está no arquivo, não no servidor.

→ **E ela é a razão de o backup ser cópia a frio.** Como o `gbak` não
roda, a única cópia íntegra possível é a do arquivo com o serviço
parado. A rotina existe desde 15/09/2026 —
`references/servidor.md`. Até aquele dia **não havia backup nenhum**.

**23. A tabela `OS` tem UM único índice, no `OSCOD`. Tudo o mais é
varredura.**

Medido em 15/09/2026:

```
OS    OS_IDX1   [OSCOD]                 ← só isto
MOV   MOV_IDX1  [MOVCOD]
      MOV_IDX2  [MOVCLI]
      MOV_IDX3  [MOVCHA, MOVCLI]
CHA   CHA_IDX1  [CHACOD]
CLI   CLI_IDX1  [CLICOD]
```

Consulta na `OS` por qualquer coisa que não seja `OSCOD` vira
`PLAN (OS NATURAL)`: as 19.686 linhas, **186 ms**. Por `OSCOD`, 19 ms.
Na `MOV` o índice ajuda mas não salva — `MOVCLI = 161` casa 30.428
linhas e leva 155 a 225 ms de qualquer jeito.

**Isso desmente a otimização óbvia.** Preparar o SQL uma vez em vez de a
cada execução dá 40× num `SELECT 1 FROM RDB$DATABASE` (19 ms → 0,5 ms) e
**quase nada** nas consultas de verdade: 22,7 s → 19,9 s numa busca
real. Onde se lê tabela, o custo é ler a tabela.

O que rendeu foi outra coisa: o `ja_esta_em_os` fazia **quatro**
consultas, uma por vaga — quatro varreduras, 855 ms por serviço. Passou
a trazer as quatro vagas numa consulta só: **168 ms**, cinco vezes. O
`UPPER(...) STARTING WITH` saiu junto e ficou mais correto de quebra
(ver armadilha 2).

→ Consulta nova na `OS`: ou por `OSCOD`, ou aceite os 186 ms e traga
**tudo** o que precisa numa vez. Nunca uma consulta por vaga.

→ Um índice em `OS(OSENTD)` levaria isso a ~1 ms — e é **DDL em
produção**, escrevendo nas tabelas de sistema de um banco que tem página
corrompida e não tem backup (armadilha 22). Não antes de resolver o
backup, e nunca sem o operador.

**24. A chapa que não está na pasta NÃO FOI GRAVADA — e essa ausência é
a prova que decide se o serviço se cobra.**

15/09/2026. Varrendo o que ficara sem OS, achei quatro gravações a
lançar. Uma delas, o `49854 - HENRIQUE CESAR - SANTINHOS` da SOLIDA,
tinha até uma pendência da própria FIA dizendo *"o serviço já saiu: ele
precisa ser lançado à mão, ou a gravação fica sem cobrança"*. Lancei. A
OS 19735 baixou 4 chapas.

Estava errado, e a prova estava a um `dir` de distância: o
`W:\CTP\...\FIA\49854.pdf` **não existia**, embora o log dissesse
`OK em 331s: 49854.pdf (54.2 MB)`. Os outros dezessete arquivos daquele
dia continuavam lá — só aquele sumira. Uma pessoa o apagara de
propósito, e na mesma hora **trocou a vaga 2 da OS 19708** pela grade
`49854 HENRIQUE 49858 JUNIOR...` (`OSUSR_ALT = 31`, gente, não a FIA
que é 32). Ela estava respondendo à pergunta que a FIA fizera 20 minutos
antes: são dois serviços ou um só? **Um só.**

→ Antes de cobrar gravação atrasada, **procure a chapa na pasta do dia**.
Arquivo apagado é decisão de gente, e decisão de gente vale mais que
registro de máquina.

→ E há um defeito de verdade embaixo disso: o `conferir_completadas` não
sabe distinguir *"alguém salvou por cima sem querer"* (armadilha 16) de
*"alguém tirou de propósito"*. As duas aparecem iguais — a vaga sumiu —
e ele sempre escreve a primeira. A frase dele é afirmativa demais para o
que ele sabe.

*(Neste caso a chapa acabou sendo gravada no dia seguinte, e a OS 19735
ficou boa por acidente. O acidente não desfaz o erro de método.)*

**25. A fila de OS nunca é despachada — ela só cresce.**

`fila.despachar()` existe, está testado, e **não tem um único chamador**.
O lançamento de verdade acontece arquivo a arquivo, dentro do
`_os_do_arquivo`. Então o `_fila_os.json` acumula: em 15/09/2026 tinha
**101 serviços, 97 já lançados**, mais uma entrada `TESTE` sobrevivente
da armadilha 13.

Hoje é inofensivo, porque ninguém despacha. Mas no dia em que alguém
ligar o `despachar`, ele limpa a fila com `ja_esta_em_os` — que **não
reconhece** título cortado pelo Delphi nem título digitado à mão por um
operador. Medido naquele dia: das 8 entradas que ele não reconheceria,
**3 já estavam em OS**. Com 5 serviços da VOPRIX na fila e o mínimo em
4, ele abriria uma OS cobrando de novo o `CUBO_PDV` (19636), o
`ENGQUER` (19695) e o `NELORE` (19703).

→ Ligar o `despachar` exige limpar a fila antes, à mão, conferindo cada
entrada contra o banco. Não é ligar um interruptor.

**26. O `neogerempre.exe` manda um INSERT com coluna repetida. O Firebird
1.5 aceita; o 2.0 recusa — e isso parou a gráfica por uma manhã.**

16/09/2026, o dia depois de o banco sair da ARTE-JUNIOR para o SERVIDOR.
Toda gravação de OS pelo Delphi morria, e a tela mostrava só

```
unknown ISC error 336397210
unknown ISC error 336397208
```

Entrou **1 OS no dia**, contra 32 a 41 de um dia normal — e a única foi
a da FIA.

**Esses dois números são a mensagem que o cliente não soube ler.**
Decifrados nos cabeçalhos de mensagem do Firebird moderno
(`include/firebird/impl/msg/sqlerr.h`), `código = 0x14000000 |
(facility << 16) | número`:

```
336397210 = SQLERR 922  "Column @1 cannot be repeated in @2 statement"  SQLCODE -206
336397208 = SQLERR 920  "At line @1, column @2"
```

Reproduzido contra o banco:

```
Column OS.OSCOD cannot be repeated in INSERT statement
At line 1, column 31
```

É erro **de preparação**, antes de executar. Por isso o `firebird.log`
do servidor não registrava nada, por isso o número da OS era queimado
(o programa já o tinha pegado do gerador), e por isso nenhum gatilho
podia ajudar — a instrução nunca chega a rodar.

→ **O SQL está compilado dentro do `neogerempre.exe`.** Não há como
arrumá-lo. Quem tem de ceder é o servidor: **Firebird 1.5**. Ensaiado
numa cópia do backup antes de decidir — o 1.5 abre o arquivo que o 2.0
usou (ODS 10.3, sem restore) e aceita a coluna repetida.

→ **Não é o cliente velho.** Foi a primeira hipótese e está errada:
o `isql` do Firebird **1.5** lê e grava no servidor **2.0** sem erro, e
a falha se reproduz com cliente moderno.

→ **E houve um achado real que NÃO era a causa.** Procurando, encontrei
que a `OS` tem sete colunas NOT NULL — `OSCOD`, `OSSIT`, `OSTIPO`,
`OSCLI`, `OSCVEN`, `OSCOPER`, `OSCCONF` — e que mandar nulo em `OSCVEN`
(o Vendedor, que o operador deixa em branco) dá
`SQLCODE -625 validation error`. Reproduzi, criei o `TR_OS_SEM_NULO`
para isso, e **a gráfica continuou parada.** Achado verdadeiro, causa
falsa. A lição: *reproduzir* um erro parecido não prova que ele é **o**
erro — a prova é o erro que a tela mostra, traduzido.

→ **Por que ninguém conseguia ler o erro:** falta `firebird.msg` ao lado
do `fbclient.dll` e do `gds32.dll`. Sem ele o cliente Firebird não
traduz **nenhum** erro — tudo vira `unknown ISC error <número>`, e o
número não diz nada. Pus uma cópia em `\\servidor\NeoGerempre\`, mas as
estações carregam o `gds32.dll` de outro lugar; falta descobrir de onde.

→ **O conserto foi o `TR_OS_SEM_NULO`**, criado em 16/09/2026: um
`BEFORE INSERT OR UPDATE` que troca nulo por zero em `OSCVEN`,
`OSCOPER`, `OSCCONF`, `OSSIT` e `OSTIPO`. Zero é o que as 19.749 OS
existentes já têm nesses campos — ele não inventa dado, reproduz o que o
banco tem. Desfaz-se com `DROP TRIGGER TR_OS_SEM_NULO`.

→ **E ele NÃO toca em `OSCOD` nem em `OSCLI`, de propósito.** OS sem
cliente não é OS. E `OSCOD` é pior: o `TR_OS_BEFORE` faz
`delete from mov where movnos = new.oscod`, e um zero ali apagaria as 94
linhas de `SALDO ANTERIOR`, que moram justamente em `MOVNOS = 0` — o
estoque inteiro pelos ares. Conferido: não existe OS com `OSCOD = 0`, a
menor é 2.

→ A lição maior: **mudar a versão do servidor muda o que o banco
aceita.** O que se testou antes da mudança foi ler e escrever pelo
código da FIA, que preenche todos os campos e escreve SQL limpo. O
programa dos operadores faz diferente, e foi ele que quebrou. Da próxima
vez, teste **pelo caminho de quem usa**, não pelo de quem programa.

**27. Sessão de administrador não enxerga letra mapeada — e a FIA sobe
muda.**

16/09/2026. O VS Code foi aberto como administrador para instalar o
serviço do Firebird. No F5 seguinte a FIA não escreveu nada: sem
"Vigiando", sem os sete "OK", sem uma linha no log.

Não era defeito dela. **Mapeamento de letra pertence à sessão do
usuário**: o UAC dá ao processo elevado outro token, e o `V:` e o `W:`
que a pessoa mapeou como usuário comum **não existem** para ele.

```
V:  NAO EXISTE   ->  BASE_ENTRADA  V:\SOLIDA Grafica    nao alcanco
W:  NAO EXISTE   ->  BASE_CTP      W:\CTP               nao alcanco
```

→ **O conserto foi trocar letra por caminho de rede inteiro** no
`config_local.py`: `\\servidor\TRABALHO\SOLIDA Grafica`,
`\\servidor\@clientes\CTP`. Caminho de rede não pertence a sessão
nenhuma — vale elevado ou não — e ainda sobrevive ao mapeamento que não
reconecta no logon.

→ A outra saída seria `EnableLinkedConnections = 1` em
`HKLM\...\Policies\System`, que é a solução oficial da Microsoft. Ela
**exige reiniciar a máquina** — e naquele dia a máquina era o servidor
do banco. Caminho de rede não pede reinício.

→ O perigo real veio depois: para "fazer a FIA aparecer", o
`sys.exit(1)` que barra a subida sem pasta alcançável chegou a ser
removido do `monitor.py`. Sem ele a FIA sobe **vigiando o nada, em
silêncio** — o mesmo defeito da armadilha 19 do fechamento. A parada foi
restaurada, agora dizendo em voz alta que letra mapeada some em sessão
elevada.

**28. O Firebird trava sem morrer — e o Guardian não cobre isso.**

16/09/2026, 12:50. O GEREMPRE parou pela segunda vez em dois dias. A tela
do cliente dizia

```
Unable to complete network request to host "EUDSON-PC".
Nenhuma conexão pôde ser feita porque a máquina de destino as recusou
ativamente.  Error Code: -902
```

"Recusou ativamente" é `WSAECONNREFUSED`. Mas o serviço estava
**Running**, o processo vivo e respondendo, 14 threads, 274 handles. E o
`netstat` mostrava o quadro que explica tudo:

```
TCP  0.0.0.0:3050            LISTENING     21680
TCP  192.168.15.134:3050  ->  ...15.27      ESTABLISHED   21680   (x3)
TCP  192.168.15.134:3050  ->  ...15.34      ESTABLISHED   21680   (x2)
```

**Soquete de escuta aberto, cinco conexões antigas vivas, e toda conexão
nova recusada — inclusive de 127.0.0.1.** O processo segurava tudo e não
aceitava mais nada: a fila de espera do soquete enche e o Windows passa a
recusar.

O que fechou o diagnóstico foi o **carimbo de hora do `.fdb`**: parado em
12:50:46, mais de uma hora sem uma escrita. Servidor que atende não
deixa o arquivo intocado por uma hora. Só restava reiniciar.

→ **O `firebird.log` do servidor não registrou nada.** Travou calado. Não
espere que ele conte; pergunte ao `netstat` e ao carimbo do arquivo.

→ **O Guardian não resolve.** Ele ressuscita processo que **morre**, não
processo que **trava**. Eram dois casos em dois dias — 15/09 o 2.0 caindo
com erro interno, 16/09 o 1.5 travando — e o Guardian não teria pegado o
segundo.

→ **O conserto foi um vigia próprio**, em `ferramentas/vigia_firebird.ps1`,
tarefa de minuto em minuto como SISTEMA. Ele não pergunta se o processo
existe; pergunta se o **banco atende**, e em dois níveis, porque **porta
aberta não é banco vivo**: abre a 3050 e, abrindo, faz uma consulta de
verdade com prazo de 20 s. Duas falhas seguidas e ele reinicia, no
máximo três vezes por hora. Detalhes em `references/servidor.md`.

## A OS DE CHAPA NÃO SE MISTURA COM A DE ACABAMENTO

Regra do operador, **21/09/2026**: *"se a OS estiver preenchida com algum
item de acabamento gráfico, ou outro item que não seja de chapas, não use
essa OS (...) crie uma nova, ou utilize alguma que esteja aberta somente
com chapas"*.

A OS tem quatro vagas e cada vaga guarda um **item**, pelo código em
`OSESP<n>`. Chapa é item; acabamento também. Contado nas 400 OS mais
recentes da AMÉRICA:

```
 90  PM_52                306 vagas   <- chapa
 89  SM_74                128         <- chapa
 91  MOZP_FT2              52         <- chapa
  6  BOPP FOSCO            44
 10  COMUNICACAO VISUAL    31
  8  VERNIZ LOCAL          13
  2  FOTOLITO              12
  4  PLASTICO BRILHO       10
  7  BOPP BRILHO            3
```

**Quase um quinto das vagas dela não é chapa.** São serviços de outra
natureza, com outro preço e outro caminho na oficina.

**Uma vaga de acabamento derruba a OS inteira**, e não só aquela vaga:
`so_tem_chapa()` exige que **todas** as ocupadas sejam chapa. Não havendo OS limpa, abre-se uma nova — que é o que ele pediu.

### Vale para TODOS os clientes — 23/09/2026

Ele estendeu a regra: *"vamos colocar uma regra no gerempre, em todos os
clientes (...) se a OS estiver com algum item de acabamento, ou
comunicação visual, algum item que não for chapas, não acrescente mais
nenhum item aquela OS, abra uma nova OS"*.

A lista `CLIENTES_QUE_NAO_MISTURAM_OS` **saiu do `config.py`** — ela
existia para fazer a regra valer só na AMÉRICA, e não há mais o que
escolher. Não procure por ela: não há portão.

**O que custa**, medido nas 300 OS mais recentes de cada um dos nove
clientes: **42 OS misturam, em 2.263** — 42 números de OS a mais.

```
AMERICA 12    FIALHO 12    IDEAL 8    EMPORIO 7
CREATIVE 2    VOPRIX 1     PRIME, SOLIDA e VIVA: ZERO
```

### Quem é chapa: o campo do GATILHO, não o nosso cadastro

Até 23/09 os códigos vinham de `GEREMPRE_CHAPAS` daquele cliente, e o
argumento parecia bom — *"chapa nova cadastrada passa a valer sozinha,
e não há segunda lista para envelhecer"*. **Era errado, e do jeito que
não dá erro:** o `config` conhece só as chapas que a FIA usa, e o
operador usa outras à mão.

Medido em produção em 23/09, as OS que aquele critério acusaria de *"ter
item que não é chapa"*:

```
          pelo config        pelo campo do gatilho
IDEAL     216 de 300    <-   8 de 300
EMPORIO   138 de 300    <-   7 de 300
AMERICA    67 de 300    <-  12 de 300
```

Os "itens estranhos" da IDEAL eram `510X400 - 0,15`, `SM 74`,
`720X557 - 0,30` — **chapas**, só que cadastradas com outro código. Pelo
`config`, a FIA abriria OS nova em quase toda entrega dela. E repare na
AMÉRICA: a regra que já estava no ar mordia **seis vezes mais** do que o
número escrito ao lado dela no `config`.

Agora quem decide são **`RBCHAPA<n>` e `RBCHAPAPRO<n>`** — os campos que
o próprio `TR_OS_BEFO` usa para tirar a chapa do estoque do cliente ou do
da Finart. **Os dois em zero quer dizer que aquela vaga não move estoque
nenhum**, e isso é a definição de serviço. Não é interpretação nossa: é a
conta que o banco já faz.

Os dois têm de ser lidos. Ler só o `RBCHAPA` acusaria de acabamento toda
OS de quem usa chapa da Finart — IDEAL e CREATIVE trabalham assim.

Visto por dentro, na OS 19917 da AMÉRICA:

```
vaga 1   item 89   rbcha=1 rbpro=0   CAPA GOTAS DE SABEDORIA_MONTAGEM
vaga 2   item  2   rbcha=0 rbpro=0   CAPA GOTAS DE SABEDORIA MASCARA
```

**E acabamento não é item da `CHA`.** Procurei lá primeiro e o cadastro
inteiro dos nossos nove clientes são chapas, com medida em milímetro —
BOPP, verniz e comunicação visual não aparecem. Quem quiser classificar
pelo nome do item na `CHA` vai procurar o que não está lá.

**Duas respostas que parecem detalhe e não são:**

| | |
|---|---|
| **OS vazia responde SIM** | não há item estranho nela, e ela é exatamente uma das que ele mandou usar. Responder não faria a FIA abrir OS nova tendo uma limpa na frente |
| **não conseguindo ler, responde NÃO** | no escuro, abrir OS nova custa um número; escrever numa OS de acabamento custa a separação que a regra existe para manter |

**O efeito medido, nas 6 OS pendentes da AMÉRICA em 21/09/2026:**

```
19867   1/4   COMUNICACAO VISUAL          *** MUDOU: antes serviria, agora é pulada
19860   1/4   só chapa                    serve, como antes
19854   3/4   só chapa                    serve, como antes
19834   4/4   BOPP + VERNIZ + 2 chapas    nenhum - já estava cheia
19833   4/4   BOPP + 3 chapas             nenhum - já estava cheia
19832   4/4   BOPP + 3 chapas             nenhum - já estava cheia
```

Ou seja: **uma OS de seis muda de comportamento hoje.** As outras três
mistas já eram puladas por estarem cheias — mas repare nelas: a FIA
**já pôs chapa dentro de OS com BOPP**, três vezes. É isso que a regra
para daqui em diante.

*(A lista de clientes que existia aqui — `CLIENTES_QUE_NAO_MISTURAM_OS`
— saiu em 23/09/2026, quando ele mandou a regra valer para todos. Os
números que ela trazia, medidos pelo cadastro do `config`, eram os
errados de qualquer forma: ver acima.)*

## A vaga de qualquer operador, e a conferência que vem atrás

Decisão do operador em 11/09/2026: *"de qualquer um"*. A FIA passou a
completar a OS de **qualquer** operador que tenha vaga aberta para o
cliente naquele dia, e o filtro de dono saiu de `os_com_vaga_livre`
inteiro — com ele morreu o defeito do `OSUSR_ALT` da armadilha 15, sem
conserto nenhum.

O que se ganha: chapa aproveitada e uma OS a menos por cliente por dia.
O que entra junto é o risco da armadilha 16 — alguém salvar por cima —,
e ele **não tem prevenção**. Então:

| | |
|---|---|
| `completar_os()` | depois de gravar, **anota** o que escreveu em `_os_completadas.json`, na `PASTA_CONTROLE` |
| `conferir_completadas()` | **relê** passados 10 minutos, procurando o título nas **quatro** vagas — quem salvou por cima pode ter reorganizado a OS, e o que importa é o serviço estar lançado em algum lugar, não estar na vaga 2 |
| o laço do `monitor` | chama a conferência a cada volta; ela **só vai ao banco quando há vaga vencida**, e nunca escreve lá |

Sobreviveu, sai da lista passadas 8 horas — senão seria relida para
sempre. **Sumiu, vira pendência** com o número da OS, a vaga e a hora, e
o recado de que o serviço já saiu e precisa ser lançado à mão, ou a
gravação fica sem cobrança.

**Os dois números — 10 minutos e 8 horas — são palpite, e estão
marcados como tal no código.** Não há medida por trás deles; é o tempo
plausível de alguém terminar de mexer numa OS e salvar. Aparecendo caso
de gente salvando muito depois, sobem.

Há seis testes nisso em `tests/test_gerempre.py`, e um deles é o que
mais importa: **a conferência não pode escrever no banco** — ela é uma
releitura, e um `UPDATE` ali mexeria em estoque.

## Onde está o resto

| | |
|---|---|
| skill `fechamento-arquivos-ctp` | de onde vem a OS: como a chapa é fechada e quantas o serviço gasta |
| `references/banco.md` | a planta: as 16 tabelas, os 6 gatilhos, os geradores, o que está morto — e o **zeramento com saldo de abertura**, o molde de mexer muito sem mudar nada |
| `references/os.md` | a OS campo a campo: as quatro vagas, o que é obrigatório, como se conta chapa |
| `references/producao.md` | o portão da virada para o banco de verdade |
| `references/servidor.md` | **onde o banco mora**: os dois Firebird, o `config.txt` que comanda todas as máquinas, ler o log do servidor pela rede, a mudança de máquina de 15/09/2026 e a rotina de backup |
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
