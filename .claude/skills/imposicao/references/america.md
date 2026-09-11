# A AMÉRICA — o cliente que a FIA monta

Combinado com o operador em 10/09/2026.

## Por que ela é diferente de todos os outros

Os seis clientes que a FIA já atende **mandam o arquivo pronto**: já
montado, já imposto, no tamanho da chapa. A FIA só faz o fechamento
final — confere, abre a OS, imprime a prova e grava.

**Na AMÉRICA não.** O arquivo chega **por montar**, e quem monta é a
casa. Então o arquivo que cai na pasta do dia **não é um serviço pronto —
é matéria-prima**. Mandá-lo para o CTP como se fosse pronto seria gravar
chapa de arquivo não montado.

## O portão: a pasta `PARA CTP`

```
V:\AMERICA\<Mês>\<Dia>\              <- o arquivo chega aqui. NAO tocar.
V:\AMERICA\<Mês>\<Dia>\PARA CTP\     <- só o que está aqui segue o fluxo
```

**A FIA só olha a `PARA CTP`.** O que estiver na pasta do dia, fora dela,
é arquivo esperando montagem — e esperar é o certo.

## O caminho, a quatro mãos

| | quem | o quê |
|---|---|---|
| 1 | cliente | põe o arquivo em `V:\AMERICA\<Mês>\<Dia>\` |
| 2 | **operador** | passa à FIA as informações da montagem (chapa, pinça, arranjo, vão) |
| 3 | **FIA** | monta e grava `<mesmo nome>_MONTAGEM.pdf`, **na pasta do dia** |
| 4 | **operador** | **revisa** e, aprovando, move para `PARA CTP` |
| 5 | **FIA** | dali em diante é o fluxo normal: OS, prova, chapa no CTP |

O passo 4 é humano de propósito. A montagem é decisão, não conta: quem
diz que está certa é quem vai rodar.

"Será inicialmente um trabalho a quatro mãos" — palavras do operador. O
que a FIA aprender de cada montagem entra nesta skill, e a mão dela
cresce.

## A regra do nome

**`<mesmo nome do arquivo>_MONTAGEM`** — sufixo, no fim.

Não é invenção: a pasta da AMÉRICA de 10/09/2026 já trazia
`CRISTÃOS.pdf` ao lado de `CRISTÃOS_MONTAGEM.cdr`, e as OS do GEREMPRE
guardam títulos como `SANTINHO LUIS E LULA_MONTAGEM` e
`CARTAO DE RETORNO CBCO_MONTAGE`. A casa já fazia assim.

O nome de origem vai **inteiro**, sem limpeza — é ele que amarra a
montagem ao arquivo que a gerou.

## Os números da AMÉRICA, lidos do GEREMPRE

Conferidos em 10/09/2026, em leitura travada, nas OS que a casa abriu
esta semana:

Cliente **58** — `AMERICA (GRAFICA E EDITORA AMERICA LTDA)`. As chapas
são **do cliente** (`RBCHAPA = 1`), e são **três máquinas**:

| máquina | chapa | medida | preço | pinça |
|---|---|---|---|---|
| **PM 52** | 90 `PM_52` | 525 × 459 | R$ 8,00 | 60 mm |
| **MOZP** | 91 `MOZP_FT2` | 650 × 550 | R$ 12,00 | 60 mm |
| **SM 74** | 89 `SM_74` | 745 × 605 | R$ 12,00 | 62 mm |

**Os preços saíram dos usos MAIS RECENTES, não do que aparece mais
vezes.** A MOZP tem 272 lançamentos a R$ 10,00 e 112 a R$ 12,00 — mas
tudo desde agosto está em 12, então 10 é preço velho. Contar frequência
teria cobrado a menos.

### Qual máquina recebe o trabalho

Regra do operador: **até o formato 4** (maior lado ≤ 560 mm) vai na
**PM 52**; acima dele, **colorido** vai na **SM 74** e **preto-e-branco**
vai na **MOZP**.

Os 560 mm são a mesma linha que o GEREMPRE usa para separar `F4` de `F2`
na OS — agora num lugar só, `MAIOR_LADO_F4` no `config.py`.

O operador disse "geralmente". Então quando a regra não bate com o
tamanho do arquivo que chegou, **manda o arquivo** — ele já está montado
e revisado —, mas fica um aviso no log: é fora do geralmente que vale um
olho.

**Atenção:** existe também uma chapa **15**, chamada `525X459`, de dono
`0` (própria da Finart). **Não é a da AMÉRICA.** A da AMÉRICA é a 90. Usar
a 15 baixaria estoque no lugar errado.

A AMÉRICA tem outras máquinas: a `SM_74` (chapa 89, 745 × 605, R$ 12,00)
aparece nas OS de revista. Ao montar, saiba em qual delas o trabalho vai
correr — a pinça e o preço mudam.

## O nome da chapa no CTP

Lido do que já está gravado em `W:\CTP\SETEMBRO\10\`:

```
525x459_CMYK_AMERICA_Panfleto RAImundo
525x459_GREY_AMERICA_El Shaday
525x459_AMERICA_CRISTAOS
```

É o mesmo feitio dos outros clientes de formato no nome —
`<formato>_<cores>_AMERICA_<nome>`.

Cada operador tem a sua pasta dentro do dia (`FIA`, `JOAOZ`, `PEDRO`,
`eudson`); a FIA grava na dela.

## O que acontece depois do portão

`ferramentas/fechar_america.py`, na ordem:

| | passo |
|---|---|
| **0** | **"já fechei este?"** — pergunta ao registro **antes de tudo** |
| 1 | **guarda cópia** na pasta do dia |
| 2 | **abre a OS** no GEREMPRE — mexe em estoque |
| 3 | **imprime a prova**, com a OS no verso |
| 4 | **grava a chapa no CTP** e confere que chegou inteira |
| **5** | **anota no registro** — o trabalho está feito aqui |
| 6 | **apaga da `PARA CTP`** |

### O passo 0 e o passo 5 custaram três folhas de papel

Em 10/09/2026 o portão imprimiu a **mesma prova três vezes**. O caminho:
o apagar recusou por um detalhe; o arquivo ficou no portão; o vigia
voltou cinco segundos depois e **refez tudo**, prova inclusive.

É o mesmo defeito do `02020 - CHAPA ZIMI` do EMPORIO, em outra roupa:

> **Falha depois da impressão vira laço de impressão.**
> Quem imprime tem de deixar dito que imprimiu — na hora, antes de
> fazer mais qualquer coisa.

O trabalho está **feito** quando a chapa está no CTP conferida. O apagar
que vem depois é **faxina**. Anotar só depois da faxina fazia faxina que
falha custar trabalho refeito.

E quando o portão encontra um arquivo já fechado, ele **termina a
faxina** — guarda a cópia e tira do portão — sem abrir OS, sem imprimir
e sem gravar chapa. Senão o arquivo ficaria ali para sempre, pulado em
silêncio.

O que salvou a conta naquele dia foi o `ja_esta_em_os`: as três voltas
acharam a OS 19635 e **não recobraram**. Razão intacto, saldo em 110,
uma OS só. O estrago foi papel.

O nome no CTP sai pelo protocolo da casa —
`<formato>_<cores>_AMERICA_<descrição>`, com o `finalizar()` tirando
acento. O **`_MONTAGEM` cai** aqui: ele serve para separar a montagem do
original dentro da pasta do cliente, e no CTP não há original com que
confundir. Foi assim que os operadores fizeram `CRISTÃOS.pdf` virar
`525x459_AMERICA_CRISTAOS`.

Mas o **título da OS mantém** o `_MONTAGEM` — as OS da casa guardam
`CRISTAOS_MONTAGEM` e `SANTINHO LUIS E LULA_MONTAGEM`. Os dois nomes
são diferentes de propósito.

### Sobre apagar da `PARA CTP`

Pedido do operador, e a razão dele é boa: **caixa de entrada que acumula
vira depósito**, e o servidor enche.

Mas apagar é para sempre. Então o apagar só acontece com **três coisas
provadas antes**:

1. a chapa está no CTP, do mesmo tamanho em bytes, e **abre como PDF**;
2. existe cópia na pasta do dia — e se o operador tiver **movido** em vez
   de copiado, o programa **devolve a cópia para lá antes** de apagar;
3. nada estourou nos passos anteriores.

E se a pasta do dia já tiver uma montagem **com o mesmo nome e conteúdo
diferente** — que foi o que travou tudo naquele dia —, quem manda é a do
**portão**: é a que o operador revisou. A antiga é posta de lado com a
data no nome, porque não se joga fora montagem de ninguém.

Faltando qualquer uma, **o arquivo fica**. Pesar o disco é problema;
perder montagem revisada é pior.

A `PARA CTP` é caixa de entrada; a **pasta do dia é o arquivo da casa**;
o CTP é a entrega. Cada uma com um papel.

## O que ainda não está ligado

Desde 10/09/2026 o portão é **automático**: `america.rodada()` é chamada
a cada volta do laço do vigia, logo depois da ponte do Teams.

**Ela não entra na lista de `clientes()`**, e é de propósito — o caminho
da AMÉRICA é outro. O que se vigia não é a pasta do dia, e sim a
subpasta `PARA CTP`; o arquivo que chega ali já é chapa pronta, não arte
por montar; e no fim ele é apagado, o que nenhum outro cliente faz.

A rodada **não estoura para cima**: o portão da AMÉRICA quebrando não
pode derrubar o vigia dos outros seis.

E ela espera o arquivo terminar de chegar (`arquivo_estavel`) — uma
chapa tem megabytes, e ler pela metade daria chapa cortada no CTP.

Para rodar fora do vigia, `ferramentas/fechar_america.py`, com `--olhar`
para conferir sem escrever nada.
