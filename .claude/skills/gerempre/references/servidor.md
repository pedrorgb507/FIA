# A máquina embaixo do banco

Onde o GEREMPRE mora, como se olha para ele por fora, e as duas mudanças
de casa de 15 e 16/09/2026.

## Onde cada coisa está

```
EUDSON-PC     192.168.15.134   Firebird 1.5.6.5026    <- o banco, HOJE
   instalação   C:\GEREMPRE FIA TESTE\firebird\Firebird_1_5\
   serviço      FirebirdServerDefaultInstance, Automatic, 0.0.0.0:3050
   banco        C:\NeoGerempre\bdados\neobdados.fdb
   compartilh.  \\EUDSON-PC\NeoGerempre  (Todos / Controle Total)
   backup       C:\BKP-GS  +  espelho em \\servidor\TRABALHO\BKP-GS
   rotinas      C:\Finart\_rotina\  (backup as 03:00, vigia de 1 em 1 min)

SERVIDOR      192.168.15.150   Firebird 2.0.7.13318   <- 15/09, durou um dia
   instalação   C:\Program Files (x86)\Firebird\Firebird_2_0\
   programa     \\servidor\NeoGerempre\neogerempre.exe   <- continua aqui
   O 2.0 recusa o INSERT do Delphi (armadilha 26). Serviço parado.

ARTE-JUNIOR   192.168.15.27    Firebird 1.5.6.5026    <- até 15/09/2026
   instalação   C:\Program Files (x86)\Firebird\Firebird_1_5\
```

Repare no **`(x86)`** nos dois primeiros: quem procura em
`C:\Program Files` não acha nada e conclui que o Firebird não está
instalado.

**O EUDSON-PC é provisório e é a máquina errada** — é estação de
trabalho, não servidor. Se ela for desligada, a gráfica para. O certo é
instalar o Firebird **1.5** no SERVIDOR e voltar para lá. O que o
16/09/2026 ensinou é que a versão importa mais que a máquina: 2.0 não
serve a este programa, 1.5 serve.

## O `config.txt` comanda todas as máquinas

Esta é a peça mais útil deste arquivo. Todas as estações leem o mesmo

```
\\servidor\NeoGerempre\config.txt     seções [os] e [cep], linha Database=
\\servidor\NeoGerempre\config2.txt    três linhas: servidor, porta, caminho
```

Trocar `Database=` nesses dois arquivos reposiciona a empresa inteira de
uma vez — não há nada a fazer em máquina nenhuma. Foi assim que a virada
de 15/09/2026 se deu, e é assim que se volta atrás: as versões antigas
ficaram ao lado, como `config.txt.ANTES-15-09-2026`.

Esse mesmo arquivo guarda **credencial de banco em texto puro**, numa
pasta aberta à rede. É o irmão da armadilha 8 e continua por resolver —
vale tratar antes de qualquer coisa que amplie o alcance da rede. Quem
for mexer, olhe o arquivo; não está escrito aqui de propósito.

## Ler o log do servidor sem sair do lugar

Não é preciso pedir a ninguém que copie arquivo: a API de serviços
entrega o `firebird.log` do servidor pela rede.

```python
import fdb, fdb.services
fdb.load_api(config.GEREMPRE_CLIENTE_DLL)
svc = fdb.services.connect(host="servidor", user=..., password=...)
print(svc.get_home_directory())      # onde o Firebird está instalado
linhas = []
svc.get_log(callback=linhas.append)  # get_log() sem callback devolve None
svc.close()
```

`get_log()` **não devolve o texto** — ela transmite linha a linha e só
enche quem passar `callback`. Sem ele volta `None`, e o erro parece
outro.

**Cuidado com qual log você está lendo.** Há dois, e eles contam coisas
diferentes:

| | |
|---|---|
| `\\servidor\NeoGerempre\firebird.log` | é do **cliente**. 39 máquinas escrevem nele pela `fbclient.dll` da pasta compartilhada. Só tem erro de rede |
| o da pasta de instalação, no servidor | é do **servidor**. É o que diz se o banco caiu, subiu ou se corrompeu |

Distinguem-se pela marca de cada linha: `(Client)` ou `(Server)`. O do
cliente tem **zero** linhas `(Server)` — em dezesseis anos, de 2010 a
2026, só erros de soquete: `10054`, `10060`, `10061`, e
`gethostbyname failed 11004`.

### O que o log do servidor já respondeu

15/09/2026, o GEREMPRE saiu do ar por treze minutos e ninguém sabia por
quê. O log do servidor de ARTE-JUNIOR resolveu por **ausência**:

```
Wed Sep 09 09:57:34 2026   Guardian starting: ...\fbserver.exe
Tue Sep 15 14:35:37 2026   ...\fbserver.exe: normal shutdown
```

Nada entre as duas. O Firebird não caiu, não reiniciou e não registrou
erro nenhum na hora da queda — **estava de pé o tempo todo**. Logo a
queda foi de rede, não de banco, e o que a recuperou não foi reiniciar
serviço nenhum. O `Win32 error 10060` da tela confirma: tempo esgotado,
pacote que saiu e não voltou. Fosse o Firebird recusando, seria `10061`.

E o log contou outra coisa, por acumulação: **129 partidas do Guardian
entre junho/2024 e setembro/2026** — uma a cada seis dias. O banco da
empresa morava numa estação que reiniciava toda semana. Foi o argumento
que decidiu a mudança.

## A mudança de máquina, 15/09/2026

O medo era o `gbak`: a migração *correta* de Firebird é backup no velho,
restore no novo, e o `gbak` não roda neste banco (armadilha 22). Sem
ele, parecia não haver caminho.

**Havia, e é mais simples: o Firebird 2.0 abre e grava no arquivo ODS
10.3 sem restore nenhum.** Ensaiado antes de decidir, numa cópia velha
que já existia no servidor:

| ensaio | resultado |
|---|---|
| ler | abriu, 19.122 OS |
| gravar | `UPDATE` casou 1 linha; desfeito com rollback |
| gatilhos | 40, intactos |
| razão | 36 chapas vivas, 0 divergências |
| a página corrompida | **continua lá**, mesmo erro, mesma página 73787 |

A corrupção viaja com o arquivo e continua inofensiva: só morde ao ler
`RDB$PROCEDURE_PARAMETERS` ou ao preparar o `SP_ESTOQUE`. `MOV`, `CHA` e
`OS` passam limpas.

### O roteiro que funcionou

1. **parar o Firebird da máquina velha** — cópia a quente não abre;
2. copiar `neobdados.fdb` e `neocep` para lugar guardado, com a data no
   nome. *Este é o primeiro backup que a empresa teve;*
3. parar o Firebird do destino, renomear o que houver lá para `.VELHO`
   (não apagar), copiar os dois arquivos, subir;
4. trocar `config.txt` e `config2.txt` no compartilhamento;
5. trocar `GEREMPRE_DSN` no `config_local.py` da FIA;
6. **deixar o Firebird da máquina velha parado, em Manual, e renomear o
   arquivo lá.** Este passo não é zelo: se uma estação qualquer voltar a
   apontar para a máquina velha, ela abre um segundo banco e o trabalho
   se parte em dois — e isso só aparece dias depois;
7. conferir: contagem de OS, razão dos dois lados, e uma pessoa abrindo
   o programa na tela antes de liberar as outras.

O que se ganhou, medido: a ligação caiu de **84 s** (pelo nome, ver
armadilha 19) para **0,126 s**, e o `ja_esta_em_os` para **0,194 s**.

**A cópia que já estava no servidor estava 588 OS atrasada** — 19.122
contra 19.710 — apesar de a data do arquivo dizer "ontem". Data de
arquivo diz quando foi copiado, não de quando é o conteúdo. Confira
sempre pelo `MAX(OSCOD)`, nunca pelo `mtime`.

## O backup, daqui em diante

O `gbak` continua barrado, então **cópia a frio é o único backup que
este banco admite**. A rotina mora hoje em
`C:\Finart\_rotina\backup_gerempre.ps1`, no EUDSON-PC, às 03:00, como
**SISTEMA** e nível **Highest** — sem isso ela não consegue parar o
serviço. Versionada em `ferramentas/backup_gerempre_eudson.ps1`.

**Dois destinos, e a ordem importa:**

```
1. LOCAL    C:\BKP-GS                      sempre acontece
2. ESPELHO  \\servidor\TRABALHO\BKP-GS     melhor esforço
```

O local vem primeiro porque tarefa agendada roda como SYSTEM, e o SYSTEM
de uma máquina **não tem identidade em outra**. Falhando o espelho, o
backup do dia ainda existe — só não saiu da máquina —, e isso é
registrado como AVISO, não como erro.

**Passe UNC ou caminho local, nunca letra mapeada.** `Y:` não existe
para o SYSTEM: mapeamento de letra é por usuário, não por máquina. É o
mesmo defeito da armadilha 27, visto de outro ângulo. O script converte
sozinho a UNC da própria máquina no caminho de disco dela
(`Get-SmbShare`, com `Win32_Share` de reserva).

### A conferência não pega cópia a quente — por isso ela para antes

Defeito encontrado em 16/09/2026, ao registrar a tarefa: o Windows só
deixou criá-la em nível **Limitado**, e ali o `Stop-Service` falha com
"acesso negado". O erro era anotado e a vida seguia — **copiando o banco
em funcionamento**.

E a conferência não pegaria: o tamanho do `.fdb` não muda com o servidor
no ar, e o cabeçalho continua legível. Guardaria uma cópia rasgada como
boa e apagaria as boas na rotação.

→ Agora o script **confere se os serviços pararam de fato** e recusa
copiar se algum continuar de pé. Conferir o produto não bastava; era
preciso conferir a **condição**.

## O vigia

`ferramentas/vigia_firebird.ps1`, instalado em `C:\Finart\_rotina\`,
tarefa **Vigia GEREMPRE** de minuto em minuto, como SISTEMA e nível
Highest — reiniciar serviço exige administrador.

Nasceu de dois travões em dois dias (armadilha 28). Ele não pergunta se o
processo existe; pergunta se o **banco atende**:

```
1. abre a porta 3050                               (5 s de prazo)
2. abrindo, faz uma consulta de verdade pelo isql  (20 s de prazo)
3. duas falhas SEGUIDAS -> reinicia o serviço e anota
4. no máximo 3 reinícios por hora
```

**O passo 2 é o que justifica o vigia existir.** Porta aberta não é banco
vivo: existe o caso em que ela aceita e a engine está parada atrás dela.
A consulta devolve um número ou não devolve — não há meio-termo.

**O passo 4 é o que impede o vigia de virar o problema.** Banco que não
sobe de jeito nenhum daria um laço de reinícios a cada dois minutos.
Estourado o teto, ele escreve *"precisa de gente"* e para.

Ele lê usuário e senha do `config.txt`, e não de uma cópia própria: dois
lugares guardando a mesma senha envelhecem separados, e o segundo é
sempre o que ninguém lembra de trocar.

### O vigia e o backup se atrapalhariam

A rotina das 03:00 **para o Firebird de propósito**. Sem aviso, o vigia
veria o banco fora por nossa causa e o levantaria no meio da cópia —
estragando justamente a única rede de segurança que existe.

→ O backup põe `C:\Finart\_rotina\backup_em_curso.lock` ao começar e
solta num `finally`, mesmo dando errado. O vigia pula enquanto ela
existir e for recente; passados 15 minutos ele a ignora, porque trava
esquecida é vigia cego.

### Três defeitos que só o teste pegou

Valem por si, e os três são da mesma família: **o que parece sucesso e
não é.**

**O vigia deu falso positivo.** A primeira versão usava
`Start-Process -PassThru` e lia `$p.ExitCode` — que vem **vazio**. Vazio
não é zero, então ele anunciou "banco não respondeu" com o banco sadio.
Duas dessas e teria reiniciado um banco que estava bem. Passou a julgar
**pela resposta**: a consulta tem de imprimir um número.

**O instalador quebrou no XML.** Pedir repetição infinita pelo
`Register-ScheduledTask` exige `RepetitionDuration`, e
`[TimeSpan]::MaxValue` vira `P99999999DT23H59M59S`, que o Agendador
recusa. O `schtasks /SC MINUTE` já quer dizer "para sempre", sem duração
a preencher.

**E a conferência da tarefa mentiu para mim.** Sem elevação,
`schtasks /Query /TN "Vigia GEREMPRE"` responde **"Acesso negado"**, e
`Get-ScheduledTask` simplesmente não a lista — tarefa criada pelo SYSTEM
tem ACL restrita. Li "não encontrei" como "não existe" e disse ao
operador que a instalação tinha falhado, quando estava certa.

→ A prova que vale, sem elevação, é o **rastro**: o vigia grava
`vigia_estado.txt` a cada passada. Vendo o carimbo avançar de minuto em
minuto, ele está rodando. Com o banco no ar o `vigia.log` fica vazio —
**silêncio ali é boa notícia**, e é de propósito.

A rotação só apaga pasta com nome `aaaa-mm-dd_hhmm`. As cópias feitas à
mão pela casa — `15_09_26`, `jan_2020`, `GEREMPRE JAN_22` — não casam
com esse desenho e **nunca são tocadas**, de propósito.

### Parar o Firebird com alguém dentro derruba o servidor

A primeira execução, 15/09/2026 às 19:38, ensinou isto caro. Havia **uma
conexão aberta** — alguém com o `neogerempre.exe` na tela, conferindo a
migração. O log do servidor:

```
Shutting down the Firebird service with 1 active connection(s) to 1 database(s)
The database C:\NEOGEREMPRE\BDADOS\NEOBDADOS.FDB was being accessed when
   the server was shutdown
internal gds software consistency check
   (Attempt to call GlobalRWLock::unlock() while not holding a valid lock)
SCH_validate -- not entered
```

O Firebird 2.0 **bateu numa verificação interna ao descer** e não subiu
de primeira. O banco não se estragou — razão conferido logo depois, 96
chapas, zero divergências —, mas o backup não saiu e o GEREMPRE ficou
fora por um minuto e meio.

→ A rotina agora **conta as conexões estabelecidas na porta 3050 antes
de encostar no serviço**, e desiste com `exit 2` se houver alguma.
Backup que faltou aparece no log; backup que derrubou o banco aparece no
telefone.

→ E às 03:00 não deve haver ninguém — é metade da razão de ser desse
horário. A outra metade é a cópia levar segundos.

### Suba só o Guardian, nunca os dois

Na mesma execução o script tentou levantar `FirebirdServerDefaultInstance`
e escreveu `NAO CONSEGUI SUBIR` — mensagem assustadora e **falsa**:
quando chegou a vez dele, o Guardian já o tinha levantado.

Os serviços desta instalação são `FirebirdGuardianDefaultInstance` e
`FirebirdServerDefaultInstance`. Parar o Guardian já derruba o servidor
junto, e subir o Guardian já levanta o servidor junto. Então: **parar os
dois (tolerando que o segundo já esteja parado), subir só o Guardian.**

→ E um aviso que ficou: às 19:39 o **Guardian não estava no ar** no
SERVIDOR, só o servidor. Sem ele, Firebird que morre fica morto até
alguém reparar.

A ordem dela importa e não deve ser afrouxada:

```
para  ->  copia  ->  sobe  ->  CONFERE  ->  só então apaga backup velho
```

- o serviço **sempre** volta a subir, num `finally` — banco parado por
  causa do backup é estrago maior que o backup;
- acha o serviço procurando por `*irebird*` em vez de adivinhar o nome,
  e para o **Guardian primeiro**: ele existe justamente para levantar o
  servidor de volta, e o faria no meio da cópia;
- confere tamanho igual ao original e lê o ODS no cabeçalho do arquivo
  copiado (bytes 18..21 da página 0);
- **nunca deixa menos de dois** backups, mesmo que todos estejam
  vencidos. Backup ruim que apaga os bons é pior que backup nenhum.

São ~246 MB por vez. O tempo de serviço parado é o tempo da cópia local:
segundos.

→ O ideal ainda não está feito: os backups ficam **na mesma máquina** do
banco. Isso protege de engano e de corrupção, não de perda do disco.
Falta uma cópia em outra máquina.

## O que continua faltando

- **o arquivo não encolhe.** Firebird só devolve espaço em restore, e
  restore é justamente o que não temos. As 105.848 linhas apagadas no
  zeramento liberaram páginas que serão reaproveitadas, mas os 153 MB
  continuam 153 MB;
- **a página 73787 continua corrompida**, e com ela o `SP_ESTOQUE` e
  qualquer `gbak`. Ver armadilha 22;
- **o estoque das chapas da própria Finart continua falso** — a chapa 12
  em −93.667 — porque as *compras* nunca foram lançadas. Isso não é
  problema de máquina nem de história: conserta-se contando fisicamente
  e lançando um ajuste por chapa, e depende de gente contar.
