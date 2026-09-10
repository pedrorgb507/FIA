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

| | |
|---|---|
| **cliente** | **58** — `AMERICA (GRAFICA E EDITORA AMERICA LTDA)` |
| **chapa** | **90**, `PM_52`, 525 × 459 |
| **preço** | **R$ 8,00** a chapa |
| **de quem é a chapa** | do **cliente** (`RBCHAPA = 1`, `RBCHAPAPRO = 0`) |
| quadricromia | `OSLAN = 4` |
| pinça | **60 mm** |

Quatro OS desta semana usam exatamente isso: 19633, 19623, 19601, 19553,
19546 — todas `4 × 8,00 = 32,00`.

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
| 1 | **guarda cópia** na pasta do dia, antes de tudo |
| 2 | **abre a OS** no GEREMPRE — mexe em estoque |
| 3 | **imprime a prova**, com a OS no verso |
| 4 | **grava a chapa no CTP** e confere que chegou inteira |
| 5 | **apaga da `PARA CTP`** |

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

Faltando qualquer uma, **o arquivo fica**. Pesar o disco é problema;
perder montagem revisada é pior.

A `PARA CTP` é caixa de entrada; a **pasta do dia é o arquivo da casa**;
o CTP é a entrega. Cada uma com um papel.

## O que ainda não está ligado

Desde 10/09/2026 a AMÉRICA **está** no `config.py`, mas só o que o
GEREMPRE precisa: `GEREMPRE_CLIENTES["AMERICA"] = 58` e a chapa
`("AMERICA", (525, 459))`.

**Não há `BASE_ENTRADA_AMERICA`, e é de propósito.** O vigia monta a
lista de quem varrer a partir dessas variáveis — sem ela, ele não olha
`V:\AMERICA` nem por engano. O fechamento da AMÉRICA é chamado à mão,
pela ferramenta, depois que o operador põe o arquivo no portão.

Só a 525 × 459 está cadastrada. A `SM_74` (745 × 605) da AMÉRICA
**não** — se aparecer, vira pendência em vez de OS com preço chutado.
